"""Error classification and a consistent failure envelope.

The mission requirement this satisfies: *"Do not hide failures by silently
returning empty data or zero metrics. Provide appropriate user-facing messages
and preserve technical diagnostics in secure logs."*

Design
------
Every failure the API returns deliberately carries three separable parts:

``code``
    A stable machine-readable identifier clients can branch on. Never prose.
``message``
    Safe to show a user. No stack traces, no SQL, no hostnames, no ids that
    would confirm a record exists.
``retryable``
    Whether the *same* request could succeed later. Drives client backoff and
    lets the UI offer "Retry" rather than a dead end.
``request_id``
    Echoed so a user can quote it to support and an operator can find the
    exact server-side log line.

The technical detail (exception text, SQL, DSN) is written to the structured
log — redacted — and deliberately *not* returned. That is the whole point of
the split: the operator gets the detail, the user does not leak it.

Classification
--------------
Errors are grouped into categories so the frontend can react uniformly:
``validation``, ``auth``, ``permission``, ``not_found``, ``conflict``,
``concurrency``, ``dependency``, ``rate_limit``, ``internal``.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.observability import get_logger, get_request_id

log = get_logger("librepeople.errors")


def _cors_headers(request) -> dict[str, str]:
    """Return CORS response headers for an allowed request origin.

    Only origins explicitly listed in ``settings.cors_origins`` receive an
    ``Access-Control-Allow-Origin`` header. An empty list means no browser
    origin may read responses, which is the safe default for a token API.

    Preflight (OPTIONS) responses are produced by Starlette's CORSMiddleware
    before the exception handlers run, so this helper only needs to cover
    error responses. It is applied to every JSONResponse returned by the
    handlers below so that a rejected request still carries the header the
    browser expects.
    """
    from app.core.config import settings

    headers: dict[str, str] = {}
    origin = request.headers.get("origin")
    allowed = settings.cors_origins or []
    if origin and allowed:
        if "*" in allowed:
            headers["Access-Control-Allow-Origin"] = "*"
            headers["Vary"] = "Origin"
        elif origin in allowed:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Vary"] = "Origin"
    return headers


class ErrorCategory:
    VALIDATION = "validation"
    AUTH = "auth"
    PERMISSION = "permission"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    CONCURRENCY = "concurrency"
    DEPENDENCY = "dependency"
    RATE_LIMIT = "rate_limit"
    INTERNAL = "internal"


#: category -> default HTTP status
_STATUS_FOR = {
    ErrorCategory.VALIDATION: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCategory.AUTH: status.HTTP_401_UNAUTHORIZED,
    ErrorCategory.PERMISSION: status.HTTP_403_FORBIDDEN,
    ErrorCategory.NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCategory.CONFLICT: status.HTTP_409_CONFLICT,
    ErrorCategory.CONCURRENCY: status.HTTP_409_CONFLICT,
    ErrorCategory.DEPENDENCY: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCategory.RATE_LIMIT: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCategory.INTERNAL: status.HTTP_500_INTERNAL_SERVER_ERROR,
}

#: Categories where retrying the identical request may succeed.
_RETRYABLE = {ErrorCategory.DEPENDENCY, ErrorCategory.RATE_LIMIT, ErrorCategory.INTERNAL}


class ApiError(HTTPException):
    """An HTTPException that renders the structured failure envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        category: str = ErrorCategory.VALIDATION,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        retryable: bool | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.category = category
        self.details = details or {}
        self.retryable = _RETRYABLE.__contains__(category) if retryable is None else retryable
        super().__init__(
            status_code=status_code or _STATUS_FOR.get(category, 500),
            detail=message,
        )

    def envelope(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "category": self.category,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details,
                "request_id": get_request_id(),
            }
        }


# --- Constructors for the cases we actually raise ------------------------- #


def validation(code: str, message: str, **details: Any) -> ApiError:
    return ApiError(code, message, ErrorCategory.VALIDATION, details=details or None)


def not_found(what: str) -> ApiError:
    return ApiError("not_found", f"{what} not found", ErrorCategory.NOT_FOUND)


def forbidden(message: str = "You do not have access to this resource") -> ApiError:
    return ApiError("forbidden", message, ErrorCategory.PERMISSION)


def conflict(code: str, message: str, **details: Any) -> ApiError:
    """409 — the request conflicts with current state (duplicate, bad transition)."""
    return ApiError(code, message, ErrorCategory.CONFLICT, details=details or None)


def concurrency_conflict(
    message: str = "This record was changed by someone else. Reload and try again.",
    **details: Any,
) -> ApiError:
    return ApiError("concurrent_update", message, ErrorCategory.CONCURRENCY, details=details or None)


def unavailable(code: str, message: str, **details: Any) -> ApiError:
    """503 — a dependency is down. Retryable; the UI should offer a retry."""
    return ApiError(code, message, ErrorCategory.DEPENDENCY, details=details or None)


def internal(code: str, message: str = "An unexpected error occurred", **details: Any) -> ApiError:
    return ApiError(code, message, ErrorCategory.INTERNAL, details=details or None)


def _is_dependency_failure(exc: Exception) -> bool:
    """Recognise database/storage outages without importing optional drivers."""
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    return (
        "operationalerror" in name
        or "interfaceerror" in name
        or "databaseerror" in name
        or "apierror" in name
        or "connection" in text
        or "timeout" in text
        or "tns" in text
        or "ora-" in text
    )


async def unhandled_exception_handler(request, exc: Exception) -> JSONResponse:
    """Last-resort handler.

    Logs the technical detail server-side and returns a safe envelope. The raw
    exception text never reaches the client.
    """
    # The middleware that normally echoes X-Request-ID may not have produced a
    # response when this handler runs, so fall back to the inbound header and,
    # failing that, a fresh id. The value stays a string either way.
    from uuid import uuid4

    rid = get_request_id() or request.headers.get("x-request-id") or uuid4().hex
    rid = str(rid)
    if _is_dependency_failure(exc):
        code, category = "dependency_unavailable", ErrorCategory.DEPENDENCY
        message = (
            "A required service is temporarily unavailable. "
            "Please try again in a moment."
        )
        status_code = 503
    else:
        code, category = "internal_error", ErrorCategory.INTERNAL
        message = "An unexpected error occurred. Please try again."
        status_code = 500

    log.error(
        "unhandled exception",
        request_id=rid,
        path=str(getattr(request, "url", "")),
        method=getattr(request, "method", ""),
        exc_type=type(exc).__name__,
    )

    headers = {"X-Request-ID": rid}
    if category == ErrorCategory.DEPENDENCY:
        headers["Retry-After"] = "5"

    # This handler is registered for ``Exception``, so Starlette runs it inside
    # ServerErrorMiddleware — outside CORSMiddleware. Without this, a 5xx
    # reaches the browser with no Access-Control-Allow-Origin and is reported
    # as a CORS failure rather than a server error. ``allow_credentials`` is
    # false, so echoing the origin is sufficient.
    from app.core.config import settings

    origin = request.headers.get("origin")
    allowed = settings.cors_origins
    if origin and allowed:
        if "*" in allowed:
            headers["Access-Control-Allow-Origin"] = "*"
            headers["Vary"] = "Origin"
        elif origin in allowed:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Vary"] = "Origin"

    return JSONResponse(
        status_code=status_code,
        content=ApiError(code, message, category).envelope(),
        headers=headers,
    )


async def api_error_handler(request, exc: ApiError) -> JSONResponse:
    """Render an ApiError with its envelope, logging server-side context."""
    headers: dict[str, str] = _cors_headers(request)
    if exc.category == ErrorCategory.RATE_LIMIT and isinstance(exc.headers, dict):
        headers = exc.headers
        # Re-apply CORS if rate-limit handler overwrote it.
        headers.update(_cors_headers(request))
    if exc.category == ErrorCategory.AUTH:
        headers.setdefault("WWW-Authenticate", "Bearer")
    if exc.retryable and exc.category == ErrorCategory.DEPENDENCY:
        headers.setdefault("Retry-After", "5")

    log.info(
        "api error",
        code=exc.code,
        category=exc.category,
        status=exc.status_code,
        path=str(getattr(request, "url", "")),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.envelope(),
        headers=headers,
    )


async def http_exception_handler(request, exc: HTTPException) -> JSONResponse:
    """Render ordinary HTTPExceptions in the same envelope as ApiError."""
    if isinstance(exc, ApiError):
        # Starlette consults the status-code handlers (404, 405) before the
        # class handlers, so an ApiError with one of those statuses lands
        # here. It carries its own code (job_not_found, ...), which the
        # contract promises; only plain HTTPExceptions from unmatched routes
        # render the generic code.
        return await api_error_handler(request, exc)
    detail = exc.detail
    if isinstance(detail, str):
        message = detail
        details: dict[str, Any] = {}
    else:
        message = "Request could not be processed"
        details = {"reason": detail}

    category = {
        401: ErrorCategory.AUTH,
        403: ErrorCategory.PERMISSION,
        404: ErrorCategory.NOT_FOUND,
        409: ErrorCategory.CONFLICT,
        422: ErrorCategory.VALIDATION,
        429: ErrorCategory.RATE_LIMIT,
    }.get(exc.status_code, ErrorCategory.INTERNAL)

    code = {
        401: "unauthenticated",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
    }.get(exc.status_code, "error")

    headers = dict(exc.headers or {})
    headers.update(_cors_headers(request))
    if exc.status_code == 429:
        headers.setdefault("Retry-After", "60")
    # A denied request writes no audit row: the audit trail records changes to
    # data, and a denial changes nothing. It is recorded here instead, with
    # the request id, so an incident can be reconstructed from the logs. The
    # decision is DEC-026 in agents/DECISIONS.md.
    if exc.status_code in (401, 403, 429):
        log.warning(
            "request refused",
            request_id=get_request_id(),
            path=str(getattr(request, "url", "")),
            method=getattr(request, "method", ""),
            status=exc.status_code,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiError(code, message, category, details=details).envelope(),
        headers=headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Render Pydantic validation errors as the structured error envelope.

    FastAPI's default handler returns ``{"detail": [...]}``; the contract
    requires the shared envelope on every non-2xx response.
    """
    from app.core.observability import get_request_id

    def _serialise(errors: list[dict]) -> list[dict]:
        out = []
        for err in errors:
            item = dict(err)
            ctx = item.get("ctx")
            if isinstance(ctx, dict):
                item["ctx"] = {
                    k: str(v) if not isinstance(v, (str, int, float, bool, type(None)))
                    else v
                    for k, v in ctx.items()
                }
            out.append(item)
        return out

    errors = _serialise(exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ApiError(
            code="validation_error",
            message="Request validation failed",
            category=ErrorCategory.VALIDATION,
            status_code=422,
            details={"fields": errors},
            retryable=False,
        ).envelope(),
        headers=_cors_headers(request),
    )


def install_handlers(app) -> None:
    """Register the handlers and the correlation-id middleware."""
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from starlette.middleware.base import BaseHTTPMiddleware

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    # Unmatched routes raise starlette.exceptions.HTTPException, not
    # fastapi.exceptions.HTTPException. FastAPI's subclass handler does
    # not match the base class via MRO lookup, so register the base
    # class and status-code handlers as well.
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(404, http_exception_handler)
    app.add_exception_handler(405, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    class CorrelationMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            from app.core.observability import set_client_ip, set_request_id

            rid = set_request_id(request.headers.get("x-request-id"))
            # The audit trail records the hashed source address of a write.
            # Forwarded addresses are believed only from a trusted proxy.
            from app.core.trusted_proxy import client_ip as _trusted_client_ip

            client = _trusted_client_ip(request)
            set_client_ip(client)
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response

    # Added last so it wraps everything, including other middleware.
    app.add_middleware(CorrelationMiddleware)