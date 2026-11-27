"""Break-glass emergency access endpoints.

``POST /break-glass/access`` creates a time-boxed grant (SuperAdmin + MFA).
``GET /break-glass/grants`` lists grants. ``DELETE /break-glass/grants/{id}``
revokes one.

A grant is never usable for the grantor's own tenant, and break-glass is
never honored for FSM or registry modification — those endpoints require
SuperAdmin directly and never accept a grant.

Single-tenant install: the cross-tenant grant-scope enforcement dependency
was removed (no data endpoint accepts a grant to reach another tenant).
The grant ledger itself stays — every grant is created with SuperAdmin +
step-up MFA, is time-boxed, and is fully audited. The ``target_tenant_id``
column is retained unchanged (no schema change, no migration).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_mfa, require_roles
from app.core.audit import record_audit
from app.core.errors import ApiError, ErrorCategory
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
