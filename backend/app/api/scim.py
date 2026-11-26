"""SCIM 2.0 Users subset (scim-provisioning slice).

Routes (mounted at ``/scim/v2`` in ``app.main``):

* ``GET /Users`` — SCIM ListResponse; ``?filter=userName eq "x"`` narrows
  to one user. ``startIndex``/``count`` paginate.
* ``POST /Users`` — create. ``externalId`` is the idempotency key: a
  repeat with a known ``externalId`` returns the existing user (200),
  a new user returns 201. Created users are ``Associate`` with
  ``must_change_password=true`` (contract decision D2).
* ``GET /Users/{id}`` — one user.
* ``PUT /Users/{id}`` — full replace. ``PATCH /Users/{id}`` — SCIM
  ``Operations`` (or a plain ``{"active": ...}`` body); ``active=false``
  deactivates (``is_active=false``).
* ``DELETE /Users/{id}`` — always 404: hard delete is disabled.
* ``POST /Tokens`` — mint a bearer token. JWT ``SuperAdmin`` only
  (contract decision D3); without it no token could ever exist.

Auth is the SCIM bearer token alone (``verify_scim_token``: sha256 hex
compare against ``scim_tokens`` + expiry check). A JWT — even a valid
one — is not a SCIM token and is refused 401. Every route resolves the
request tenant via ``resolve_tenant`` (fail-closed + audit attribution;
there is no per-user tenant column by contract decision D1) and is
rate-limited through ``app.core.rate_limit`` (``scim`` bucket).

Every mutation writes an audit row via ``record_audit``. No Groups write,
no bulk, no enterprise extensions.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.audit import record_audit
from app.core.rate_limit import limiter
from app.core.security import get_password_hash
from app.core.tenancy import resolve_tenant
from app.models.integrations_platform import SCIMToken
from app.models.user import User

router = APIRouter()

#: Abuse budget for the SCIM surface: N requests per minute per token.
#: The contract acceptance test exceeds N and expects 429.
SCIM_RATE_LIMIT = 30
SCIM_RATE_WINDOW_SECONDS = 60
limiter.set_policy("scim", SCIM_RATE_LIMIT, SCIM_RATE_WINDOW_SECONDS)

USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"

_FILTER_RE = re.compile(r'^\s*userName\s+eq\s+"([^"]*)"\s*$', re.IGNORECASE)


def _scim_error(status_code: int, detail: str) -> JSONResponse:
    """A SCIM error body (the status code is what callers branch on)."""
    return JSONResponse(
        status_code=status_code,
        content={"schemas": [ERROR_SCHEMA], "detail": detail, "status": str(status_code)},
    )


def _unauthorized(detail: str = "Missing or invalid SCIM bearer token.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_scim_token(request: Request, db: Session = Depends(get_db)) -> SCIMToken:
    """The single auth gate for the SCIM surface (no JWT fallback).

    A JWT — even one for a live user — is opaque here: it never matches a
    stored ``token_hash``, so it is refused 401 like any unknown bearer.
    The request tenant is resolved (fail-closed) so every SCIM call is
    tenant-attributed, and the call counts against the ``scim`` budget.
    """
    auth = request.headers.get("authorization") or ""
    scheme, _, token = auth.partition(" ")
    if not token.strip() or scheme.lower() != "bearer":
        raise _unauthorized()
    presented = token.strip()
    # Resolve the tenant before touching the token table: a request that
    # cannot be attributed to a tenant is refused before any lookup.
    resolve_tenant(db, request)
    limiter.check("scim", request, key=f"scim:{hashlib.sha256(presented.encode()).hexdigest()}")
    digest = hashlib.sha256(presented.encode()).hexdigest()
    row = db.query(SCIMToken).filter(SCIMToken.token_hash == digest).first()
    if row is None:
        raise _unauthorized()
    if row.expires_at is not None:
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc):
            raise _unauthorized("SCIM bearer token has expired.")
    return row


def _emails_of(payload: dict[str, Any]) -> list[dict[str, Any]]:
    emails = payload.get("emails")
    if isinstance(emails, list):
        return [e for e in emails if isinstance(e, dict) and e.get("value")]
    return []


def _primary_email(payload: dict[str, Any], user_name: str) -> str:
    emails = _emails_of(payload)
    if emails:
        primaries = [e for e in emails if e.get("primary")]
        return str((primaries[0] if primaries else emails[0])["value"])
    if "@" in user_name:
        return user_name
    return f"{user_name}@scim.provisioned"


def _user_resource(user: User) -> dict[str, Any]:
    return {
        "schemas": [USER_SCHEMA],
        "id": str(user.id),
        "userName": user.username,
        "emails": [{"value": user.email, "primary": True}],
        "externalId": user.external_id,
        "active": bool(user.is_active),
        "meta": {"resourceType": "User"},
    }


def _list_response(resources: list[dict[str, Any]], start: int, total: int) -> dict[str, Any]:
    return {
        "schemas": [LIST_SCHEMA],
        "totalResults": total,
        "startIndex": start,
        "itemsPerPage": len(resources),
        "Resources": resources,
    }


@router.get("/Users")
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    _token: SCIMToken = Depends(verify_scim_token),
    filter: str | None = None,  # noqa: A002 (SCIM names the parameter `filter`)
    startIndex: int = 1,  # noqa: N803 (SCIM names the parameter `startIndex`)
    count: int = 100,  # noqa: N803
) -> dict[str, Any]:
    """SCIM ListResponse, optionally narrowed by ``userName eq``."""
    query = db.query(User)
    if filter is not None:
        match = _FILTER_RE.match(filter)
        if match is None:
            return _scim_error(400, 'Unsupported filter; use userName eq "value".')  # type: ignore[return-value]
        query = query.filter(User.username == match.group(1))
    total = query.count()
    start = max(startIndex, 1)
    limit = max(min(count, 200), 0)
    rows = query.order_by(User.id).offset(start - 1).limit(limit).all()
    return _list_response([_user_resource(u) for u in rows], start, total)


@router.post("/Users", status_code=201)
def create_user(
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    _token: SCIMToken = Depends(verify_scim_token),
) -> Any:
    """Create a user; a known ``externalId`` returns the existing row (200)."""
    user_name = payload.get("userName")
    if not user_name or not isinstance(user_name, str):
        return _scim_error(400, "userName is required.")  # type: ignore[return-value]
    external_id = payload.get("externalId")
    if external_id is not None and not isinstance(external_id, str):
        return _scim_error(400, "externalId must be a string.")  # type: ignore[return-value]
    if external_id:
        existing = db.query(User).filter(User.external_id == external_id).first()
        if existing is not None:
            return JSONResponse(status_code=200, content=_user_resource(existing))
    if db.query(User).filter(User.username == user_name).first() is not None:
        return _scim_error(409, "A user with that userName already exists.")  # type: ignore[return-value]
    email = _primary_email(payload, user_name)
    if db.query(User).filter(User.email == email).first() is not None:
        return _scim_error(409, "A user with that email already exists.")  # type: ignore[return-value]
    user = User(
        username=user_name,
        email=email,
        hashed_password=get_password_hash(secrets.token_urlsafe(48)),
        role="Associate",
        is_active=bool(payload.get("active", True)),
        must_change_password=True,
        external_id=external_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit(db, None, "scim_create_user", "User", user.id, details=f"userName={user_name}")
    db.commit()
    return JSONResponse(status_code=201, content=_user_resource(user))


@router.get("/Users/{user_id}")
def get_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _token: SCIMToken = Depends(verify_scim_token),
) -> Any:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return _scim_error(404, "User not found.")  # type: ignore[return-value]
    return _user_resource(user)


@router.put("/Users/{user_id}")
def replace_user(
    user_id: int,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    _token: SCIMToken = Depends(verify_scim_token),
) -> Any:
    """Full replace of the SCIM-mapped fields."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return _scim_error(404, "User not found.")  # type: ignore[return-value]
    user_name = payload.get("userName")
    if not user_name or not isinstance(user_name, str):
        return _scim_error(400, "userName is required.")  # type: ignore[return-value]
    clash = db.query(User).filter(User.username == user_name, User.id != user.id).first()
    if clash is not None:
        return _scim_error(409, "A user with that userName already exists.")  # type: ignore[return-value]
    external_id = payload.get("externalId")
    if external_id is not None and not isinstance(external_id, str):
        return _scim_error(400, "externalId must be a string.")  # type: ignore[return-value]
    if external_id:
        clash = db.query(User).filter(User.external_id == external_id, User.id != user.id).first()
        if clash is not None:
            return _scim_error(409, "A user with that externalId already exists.")  # type: ignore[return-value]
    email = _primary_email(payload, user_name)
    clash = db.query(User).filter(User.email == email, User.id != user.id).first()
    if clash is not None:
        return _scim_error(409, "A user with that email already exists.")  # type: ignore[return-value]
    user.username = user_name
    user.email = email
    user.external_id = external_id
    user.is_active = bool(payload.get("active", True))
    db.commit()
    record_audit(db, None, "scim_update_user", "User", user.id, details=f"userName={user_name}")
    db.commit()
    return _user_resource(user)


def _apply_patch(user: User, payload: dict[str, Any]) -> str | None:
    """Apply a SCIM PATCH body. Returns an error detail, or None on success."""
    if "Operations" in payload:
        operations = payload.get("Operations")
        if not isinstance(operations, list):
            return "Operations must be a list."
        for operation in operations:
            if not isinstance(operation, dict):
                return "Each operation must be an object."
            op = str(operation.get("op", "")).lower()
            path = str(operation.get("path", "") or "")
            value = operation.get("value")
            err = _apply_patch_value(user, op, path, value)
            if err is not None:
                return err
        return None
    # Plain {"active": false, ...} body (lenient shape some clients send).
    for key, value in payload.items():
        if key in ("schemas", "meta", "id"):
            continue
        err = _apply_patch_value(user, "replace", key, value)
        if err is not None:
            return err
    return None


def _apply_patch_value(user: User, op: str, path: str, value: Any) -> str | None:
    """Apply one patch assignment. Returns an error detail, or None."""
    name = path.split(":")[-1].strip()
    if op == "remove":
        return f"Remove is not supported for {name or 'this resource'}."
    if op not in ("add", "replace"):
        return f"Unsupported op {op!r}."
    if name == "active":
        if not isinstance(value, bool):
            return "active must be a boolean."
        user.is_active = value
        return None
    if name in ("userName",):
        if not value or not isinstance(value, str):
            return "userName must be a non-empty string."
        user.username = value
        return None
    if name in ("emails",):
        if isinstance(value, list) and value and isinstance(value[0], dict) and value[0].get("value"):
            user.email = str(value[0]["value"])
            return None
        if isinstance(value, str) and "@" in value:
            user.email = value
            return None
        return "emails must carry a value."
    if name in ("externalId",):
        if value is not None and not isinstance(value, str):
            return "externalId must be a string."
        user.external_id = value
        return None
    return f"Unsupported path {path!r}."


@router.patch("/Users/{user_id}")
def patch_user(
    user_id: int,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    _token: SCIMToken = Depends(verify_scim_token),
) -> Any:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return _scim_error(404, "User not found.")  # type: ignore[return-value]
    was_active = bool(user.is_active)
    err = _apply_patch(user, payload)
    if err is not None:
        db.rollback()
        return _scim_error(400, err)  # type: ignore[return-value]
    clash = db.query(User).filter(User.username == user.username, User.id != user.id).first()
    if clash is not None:
        db.rollback()
        return _scim_error(409, "A user with that userName already exists.")  # type: ignore[return-value]
    clash = db.query(User).filter(User.email == user.email, User.id != user.id).first()
    if clash is not None:
        db.rollback()
        return _scim_error(409, "A user with that email already exists.")  # type: ignore[return-value]
    if user.external_id:
        clash = (
            db.query(User).filter(User.external_id == user.external_id, User.id != user.id).first()
        )
        if clash is not None:
            db.rollback()
            return _scim_error(409, "A user with that externalId already exists.")  # type: ignore[return-value]
    db.commit()
    action = "scim_deactivate_user" if was_active and not user.is_active else "scim_update_user"
    record_audit(db, None, action, "User", user.id, details=f"userName={user.username}")
    db.commit()
    return _user_resource(user)


@router.delete("/Users/{user_id}", status_code=404)
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _token: SCIMToken = Depends(verify_scim_token),
) -> Any:
    """Hard delete is disabled: deprovision via ``active=false`` instead."""
    return _scim_error(404, "Hard delete is disabled; set active=false to deactivate.")  # type: ignore[return-value]


class TokenMint(BaseModel):
    label: str | None = Field(default=None, max_length=80)
    client_id: int | None = None
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


@router.post("/Tokens", status_code=201)
def mint_token(
    payload: TokenMint,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("SuperAdmin")),
) -> dict[str, Any]:
    """Mint a SCIM bearer token. JWT ``SuperAdmin`` only.

    Returns the plaintext exactly once; only the sha256 digest is stored.
    """
    plaintext = secrets.token_urlsafe(32)
    digest = hashlib.sha256(plaintext.encode()).hexdigest()
    expires_at: datetime | None = None
    if payload.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    row = SCIMToken(
        token_hash=digest,
        client_id=payload.client_id,
        label=payload.label,
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    record_audit(db, admin, "scim_mint_token", "SCIMToken", row.id, details=payload.label)
    db.commit()
    return {
        "token": plaintext,
        "id": row.id,
        "label": row.label,
        "client_id": row.client_id,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }
