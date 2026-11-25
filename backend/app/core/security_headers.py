"""Security headers middleware.

Sets the HTTP security headers that protect the application's frontend from
common client-side attacks:

* ``Content-Security-Policy`` — restricts where the browser may load scripts,
  styles, images, and other resources from. Prevents XSS and data injection.
* ``Strict-Transport-Security`` — tells the browser to only use HTTPS for this
  origin, preventing protocol downgrade attacks.
* ``X-Content-Type-Options: nosniff`` — stops the browser from MIME-sniffing
  responses away from the declared content type.
* ``X-Frame-Options: DENY`` — prevents the app from being embedded in an
  iframe (clickjacking protection).
* ``Referrer-Policy: strict-origin-when-cross-origin`` — limits referrer
  information sent to external sites.

All headers are applied to every response, including error responses, so there
is no unprotected surface.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

#: Default CSP. Adjust as the frontend adds trusted sources (e.g. the
#: self-hosted font, analytics endpoint, or OCI object storage for document
#: previews).
DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "media-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)


def _csp_value() -> str:
    """Return the Content-Security-Policy value.

    Honours ``CONTENT_SECURITY_POLICY`` from the environment when set, so an
    operator can tighten or loosen the policy without changing code.
    """
    return (settings.CONTENT_SECURITY_POLICY or "").strip() or DEFAULT_CSP


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # HSTS — only when the connection is secure (HTTPS). On plain HTTP
        # (local development, or behind a TLS-terminating proxy) the header is
        # omitted to avoid telling the browser to refuse future plain-HTTP
        # connections.
        from app.core.trusted_proxy import forwarded_proto

        is_secure = (
            request.url.scheme == "https"
            or forwarded_proto(request) == "https"
        )
        if settings.is_production and is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault("Content-Security-Policy", _csp_value())

        return response
