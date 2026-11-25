"""Break-glass emergency access grants.

A break-glass grant lets an actor access another tenant's data for a limited,
emergency window. Grants are created by a SuperAdmin (with MFA), audited, and
expire after a TTL (default 240 minutes, hard cap 480 minutes).

A grant is never usable for the SuperAdmin's own tenant, and break-glass is
never accepted for FSM or registry modification (those endpoints require
SuperAdmin directly and never honor a grant).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Identity, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.user import User

#: Default break-glass TTL in minutes.
DEFAULT_TTL_MINUTES = 240
#: Hard cap on the break-glass TTL in minutes.
MAX_TTL_MINUTES = 480


class BreakGlassGrant(Base):
    """A time-boxed break-glass authorization.

    ``actor`` is the user granted access; ``target_tenant_id`` is the tenant
    they may reach into. ``purpose`` records the emergency justification.
    The grant is active while it is not revoked and ``expires_at`` is in the
    future.
    """

    __tablename__ = "break_glass_grants"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    actor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    target_tenant_id: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    ttl_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_TTL_MINUTES
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    granted_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    actor = relationship("User", foreign_keys=[actor_id])
    grantor = relationship("User", foreign_keys=[granted_by])

    @property
    def is_active(self) -> bool:
        """True when the grant is live: not revoked and not past its TTL."""
        if self.revoked_at is not None:
            return False
        expires = self.expires_at
        now = datetime.now(timezone.utc)
        if expires.tzinfo is None:
            # SQLite strips tz info on round trip; compare naive UTC values.
            return now.replace(tzinfo=None) < expires
        return now < expires

    @property
    def is_expired(self) -> bool:
        """True when the grant's TTL has passed (whether or not revoked)."""
        expires = self.expires_at
        now = datetime.now(timezone.utc)
        if expires.tzinfo is None:
            return now.replace(tzinfo=None) >= expires
        return now >= expires
