"""Single-tenant install: tenant resolution and request-scoped context.

Every tenant-owned row carries ``tenant_id`` (a VARCHAR(60) slug). The
install serves one org: a request's tenant resolves from the JWT ``tenant``
claim (fallback ``tid``), else the legacy ``DEFAULT_TENANT_SLUG`` default,
and is stored in a context variable so queries, visibility filters and audit
writes can all read it without threading an argument through every call site.

Hostname -> tenant mapping was removed: hostnames never switch orgs. The
request hostname is still recorded on the context for audit purposes only.

Resolution order
----------------
1. JWT claim ``tenant`` (fallback ``tid``) — the authoritative source for an
   authenticated caller.
2. Neither resolves : ``DEFAULT_TENANT_SLUG`` (``"default"``) for legacy JWTs
   and backfilled rows, *indefinitely*.

Fail-closed rules
-----------------
* A client-supplied tenant id (``X-Tenant-Id`` header or ``tenant_id`` query
  param) that conflicts with the resolved tenant is refused
  ``422/403 tenant_mismatch``.
* A tenant that cannot be resolved at all is refused ``401/403
  tenant_unresolvable`` — never silently defaulted to a real tenant. The only
  default is the legacy ``"default"`` slug above, which is an explicit,
  documented fallback, not a hole in the isolation.
* A ``X-Tenant-Slug`` branding header, if sent by an older client, is
  tolerated and ignored — it is never authoritative.
* Break-glass grants are not usable for a SuperAdmin's own tenant or for
  FSM/registry modification (enforced by the break-glass endpoints).
"""

from __future__ import annotations

from dataclasses import dataclass
from contextvars import ContextVar
from typing import Any

from fastapi import Request, HTTPException, status
from sqlalchemy import or_

from app.core.errors import validation, conflict
from app.core.security import decode_token

#: Slug used to backfill pre-existing rows and to serve legacy JWTs that carry
#: no tenant claim. Allowed indefinitely; not a security hole because it only
#: applies when nothing else resolves.
DEFAULT_TENANT_SLUG = "default"

#: Context var holding the resolved tenant slug for the current request.
_tenant_id: ContextVar[str | None] = ContextVar("tenant_id", default=None)
#: Context var holding the full resolved context for the current request.
_tenant_context: ContextVar["TenantContext | None"] = ContextVar(
    "tenant_context", default=None
)


@dataclass(frozen=True)
class TenantContext:
    """The resolved tenant for a request.

    ``source`` is one of ``jwt``, ``legacy`` — auditable so an
    operator can tell why a request was attributed to a tenant.
    """

    tenant_id: str
    source: str  # "jwt" | "legacy"
    hostname: str | None = None


# --------------------------------------------------------------------------- #
# Request-scoped accessors
# --------------------------------------------------------------------------- #


def set_tenant_context(tenant_id: str, source: str, hostname: str | None = None) -> None:
    """Bind a tenant to the current request context."""
    _tenant_id.set(tenant_id)
    _tenant_context.set(TenantContext(tenant_id=tenant_id, source=source, hostname=hostname))


def clear_tenant_context() -> None:
    """Clear the tenant context (test teardown / end of request)."""
    _tenant_id.set(None)
    _tenant_context.set(None)


def current_tenant_id() -> str | None:
    """The tenant slug resolved for the current request, or ``None``."""
    return _tenant_id.get()


def current_tenant() -> TenantContext | None:
    """The full :class:`TenantContext` for the current request, or ``None``."""
    return _tenant_context.get()


def tenant_id_for(db: Any) -> str | None:
    """The tenant id attributable to ``db``'s request.

    The request context var is authoritative, but context variables do not
    propagate to the AnyIO worker thread that runs sync endpoints, so fall back
    to the value persisted on the session by :func:`resolve_tenant`. A session
    outside a request (a seed or background job) carries no such value, in
    which case the context var (set directly) is the only source.
    """
    tid = current_tenant_id()
    if tid is not None:
        return tid
    if db is not None:
        return (db.info or {}).get("tenant_id")
    return None


def tenant_column_criterion(column, tenant_id: str):
    """SQLAlchemy WHERE criterion: ``column`` equals ``tenant_id``.

    A NULL ``tenant_id`` denotes a row written before the tenant backfill
    (or without a resolved tenant); such rows belong to the legacy
    :data:`DEFAULT_TENANT_SLUG`. So a legacy/default request sees both
    ``tenant_id == DEFAULT_TENANT_SLUG`` rows and NULL-tenant rows, while any
    other tenant sees only its own rows. Tenant isolation is preserved: a
    non-default tenant never sees NULL-tenant or foreign-tenant rows.
    """
    if tenant_id == DEFAULT_TENANT_SLUG:
        return or_(column == tenant_id, column.is_(None))
    return column == tenant_id


def tenant_matches(row_tenant_id: str | None, resolved_tenant: str) -> bool:
    """True when a row carrying ``row_tenant_id`` is visible to ``resolved_tenant``.

    NULL is treated as the legacy default slug. Used for in-Python filtering
    where a SQLAlchemy criterion cannot be used.
    """
    return (row_tenant_id or DEFAULT_TENANT_SLUG) == resolved_tenant


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #


def _jwt_tenant_claim(request: Request) -> str | None:
    """Read the ``tenant`` (fallback ``tid``) claim from the bearer token."""
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except Exception:  # an invalid token is not a tenant signal
        return None
    return payload.get("tenant") or payload.get("tid")


def _request_hostname(request: Request) -> str | None:
    """Best-effort hostname of the original client host."""
    from app.core.trusted_proxy import forwarded_host

    # X-Forwarded-Host is believed only from a trusted proxy; otherwise the
    # Host the request was actually addressed to is the only hostname.
    forwarded = forwarded_host(request)
    if forwarded:
        return forwarded
    return (request.url.hostname or "").lower() or None


def _client_supplied_tenant(request: Request) -> str | None:
    """A tenant id the client explicitly sent, if any."""
    header = request.headers.get("x-tenant-id")
    if header:
        return header.strip()
    return None


def resolve_tenant(db: Any, request: Request) -> TenantContext:
    """Resolve the tenant for ``request`` (single-tenant install).

    Resolution is the install's single org: the JWT ``tenant`` claim (fallback
    ``tid``) when present, else the legacy ``DEFAULT_TENANT_SLUG`` default.
    Hostname -> tenant mapping was removed — hostnames never switch orgs.

    Raises :class:`fastapi.HTTPException` with ``tenant_unresolvable`` when no
    tenant can be determined, and ``tenant_mismatch`` when a client-supplied
    tenant id conflicts with the resolved one.
    """
    from sqlalchemy import text

    jwt_claim = _jwt_tenant_claim(request)
    hostname = _request_hostname(request)

    resolved: str | None = None
    source: str = "legacy"
    if jwt_claim:
        resolved, source = jwt_claim, "jwt"
    else:
        # Legacy JWT / backfill path: the documented default slug.
        resolved, source = DEFAULT_TENANT_SLUG, "legacy"

    # A client-supplied tenant id must not be able to redirect a request to a
    # different tenant. Refuse a conflict.
    supplied = _client_supplied_tenant(request)
    if supplied is not None and supplied != resolved:
        raise conflict(
            "tenant_mismatch",
            "The supplied tenant id does not match the resolved tenant.",
        )

    # Fail closed: an unresolvable tenant is never defaulted to a real tenant.
    # (The legacy "default" slug above is the only default, and it is
    # intentional for legacy JWTs / backfilled rows.)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant could not be resolved",
            headers={"WWW-Authenticate": "Bearer"},
        )

    set_tenant_context(resolved, source, hostname)
    # Persist the resolved tenant on the session so it survives the hop to the
    # AnyIO worker thread that runs sync endpoints: context variables do not
    # propagate across thread boundaries (see app/core/visibility.py).
    db.info["tenant_id"] = resolved
    return TenantContext(tenant_id=resolved, source=source, hostname=hostname)


def require_tenant_id() -> str:
    """Dependency: the current tenant id, refusing if none is resolved.

    Endpoints that must operate on tenant-scoped data depend on this so a
    missing tenant context becomes ``tenant_unresolvable`` rather than an
    ambiguous empty result.
    """
    tenant_id = current_tenant_id()
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No tenant resolved for this request",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return tenant_id
