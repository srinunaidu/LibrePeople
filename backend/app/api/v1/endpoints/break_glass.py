"""Break-glass emergency access endpoints.

``POST /break-glass/access`` creates a time-boxed grant (SuperAdmin + MFA).
``GET /break-glass/grants`` lists grants. ``DELETE /break-glass/grants/{id}``
revokes one.

A grant is never usable for the grantor's own tenant, and break-glass is
never honored for FSM or registry modification — those endpoints require
SuperAdmin directly and never accept a grant.

:func:`require_break_glass` is a dependency data endpoints can use to enforce
that a cross-tenant read is covered by an active, unexpired grant; it raises
``403 break_glass_expired`` or ``403 break_glass_not_granted``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user, require_mfa, require_roles
from app.core.audit import record_audit
from app.core.errors import ApiError, ErrorCategory, conflict
from app.core.tenancy import tenant_id_for
from app.models.break_glass import BreakGlassGrant, DEFAULT_TTL_MINUTES, MAX_TTL_MINUTES
from app.models.user import User

router = APIRouter()


class BreakGlassGrantCreate(BaseModel):
    actor_id: int
    target_tenant_id: str = Field(min_length=1, max_length=60)
    purpose: str = Field(min_length=1, max_length=1000)
    ttl_minutes: int = Field(default=DEFAULT_TTL_MINUTES, ge=1, le=MAX_TTL_MINUTES)


class BreakGlassGrantOut(BaseModel):
    id: int
    actor_id: int
    target_tenant_id: str
    purpose: str
    ttl_minutes: int
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    granted_by: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True


# --------------------------------------------------------------------------- #
# Enforcement dependency — used by data endpoints that allow break-glass access
# --------------------------------------------------------------------------- #


def require_break_glass(target_tenant_id: str):
    """Dependency: the current actor must hold an active grant on ``target_tenant_id``.

    Raises ``403 break_glass_expired`` when the most recent grant for this
    actor on the target has passed its TTL, and ``403 break_glass_not_granted``
    when no active grant exists. Break-glass is never usable for the actor's
    own tenant.
    """

    def _dependency(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> BreakGlassGrant:
        now = datetime.now(timezone.utc)
        own_tenant = tenant_id_for(db)
        if own_tenant and own_tenant == target_tenant_id:
            raise ApiError(
                "break_glass_not_granted",
                "Break-glass is not usable for your own tenant.",
                ErrorCategory.PERMISSION,
                details={"actor": current_user.username, "target": target_tenant_id},
            )
        grant = (
            db.query(BreakGlassGrant)
            .filter(
                BreakGlassGrant.actor_id == current_user.id,
                BreakGlassGrant.target_tenant_id == target_tenant_id,
                BreakGlassGrant.revoked_at.is_(None),
                BreakGlassGrant.expires_at > now,
            )
            .first()
        )
        if grant is not None:
            return grant
        expired = (
            db.query(BreakGlassGrant)
            .filter(
                BreakGlassGrant.actor_id == current_user.id,
                BreakGlassGrant.target_tenant_id == target_tenant_id,
                BreakGlassGrant.expires_at <= now,
            )
            .order_by(BreakGlassGrant.expires_at.desc())
            .first()
        )
        if expired is not None:
            raise ApiError(
                "break_glass_expired",
                "The break-glass grant has passed its TTL and can no longer be "
                "used.",
                ErrorCategory.PERMISSION,
                details={"grant_id": expired.id, "ttl_minutes": expired.ttl_minutes},
            )
        raise ApiError(
            "break_glass_not_granted",
            "No active break-glass grant exists for this actor on the target "
            "tenant.",
            ErrorCategory.PERMISSION,
            details={"actor": current_user.username, "target": target_tenant_id},
        )

    return _dependency


# --------------------------------------------------------------------------- #
# Grant management
# --------------------------------------------------------------------------- #


@router.post(
    "/access",
    response_model=BreakGlassGrantOut,
    status_code=status.HTTP_201_CREATED,
    operation_id="breakGlassCreateBreakGlassAccess",
)
def create_grant(
    payload: BreakGlassGrantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
    _mfa: User = Depends(require_mfa),
) -> BreakGlassGrantOut:
    """Grant an actor break-glass access to a target tenant for a TTL window.

    Refused ``403 break_glass_not_granted`` when the target is the grantor's
    own tenant. TTL is capped at 480 minutes (default 240).
    """
    own_tenant = tenant_id_for(db)
    if own_tenant and own_tenant == payload.target_tenant_id:
        raise ApiError(
            "break_glass_not_granted",
            "Break-glass is not usable for your own tenant.",
            ErrorCategory.PERMISSION,
            details={"actor": current_user.username, "target": payload.target_tenant_id},
        )

    actor = db.get(User, payload.actor_id)
    if not actor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actor not found")

    now = datetime.now(timezone.utc)
    grant = BreakGlassGrant(
        actor_id=payload.actor_id,
        target_tenant_id=payload.target_tenant_id,
        purpose=payload.purpose,
        ttl_minutes=payload.ttl_minutes,
        expires_at=now + timedelta(minutes=payload.ttl_minutes),
        granted_by=current_user.id,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    record_audit(
        db,
        current_user,
        "create_break_glass_grant",
        "BreakGlassGrant",
        grant.id,
        break_glass_grant_id=grant.id,
        details=f"actor={payload.actor_id} target={payload.target_tenant_id} ttl={payload.ttl_minutes}m",
    )
    db.commit()
    return grant


@router.get(
    "/grants",
    response_model=list[BreakGlassGrantOut],
    operation_id="breakGlassListBreakGlassGrants",
)
def list_grants(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
    active_only: bool = Query(default=False),
) -> list[BreakGlassGrantOut]:
    """List break-glass grants. SuperAdmin only."""
    now = datetime.now(timezone.utc)
    query = db.query(BreakGlassGrant).order_by(BreakGlassGrant.granted_at.desc())
    if active_only:
        query = query.filter(
            BreakGlassGrant.revoked_at.is_(None),
            BreakGlassGrant.expires_at > now,
        )
    return query.all()


@router.delete(
    "/grants/{grant_id}",
    operation_id="breakGlassRevokeBreakGlassGrant",
)
def revoke_grant(
    grant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SuperAdmin")),
) -> dict:
    """Revoke a break-glass grant. SuperAdmin only."""
    grant = db.get(BreakGlassGrant, grant_id)
    if not grant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")
    grant.revoked_at = datetime.now(timezone.utc)
    db.add(grant)
    db.commit()
    record_audit(
        db,
        current_user,
        "revoke_break_glass_grant",
        "BreakGlassGrant",
        grant_id,
        break_glass_grant_id=grant_id,
        details=f"target={grant.target_tenant_id} actor={grant.actor_id}",
    )
    db.commit()
    return {"msg": "revoked"}
