"""Refresh token storage for rotating, revocable sessions.

Why this table exists
---------------------
Access tokens are short-lived and cannot be revoked once issued — that is the
trade-off that makes them cheap to verify. A session that must be ended
immediately (a password change, a compromised account, a user being
deactivated) needs a second, revocable credential. That credential is the
refresh token.

How rotation works
-------------------
Each refresh token belongs to a *family*: the chain of tokens descended from
one original login. On every refresh:

* the presented token is marked ``rotated_at`` and revoked, and
* a new token is issued in the same family.

Presenting an already-rotated token is a **reuse** signal: either the token
was stolen, or the client is buggy. Either way the safe response is to revoke
the entire family, which ends every session derived from that login. Reuse
detection is the property that makes rotation worth the extra write.

Storage
-------
Only a SHA-256 hash of the token is stored. The token itself is 256 bits of
``secrets.token_urlsafe`` output, so a fast hash is appropriate here (unlike
a user password, which is low-entropy and needs bcrypt). A database leak does
not yield usable refresh tokens.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.security import create_access_token


class RefreshToken(Base):
    """A single issued refresh token.

    ``family_id`` links every token descended from one login, so a reuse
    event can revoke the whole chain.
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_token_hash"),
    )

    id = Column(Integer, Identity(), primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String(64), nullable=False)
    family_id = Column(String(64), nullable=False, index=True)

    issued_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(String(60), nullable=True)

    # Hashed client context. Kept for incident investigation: "which device
    # signed in?". Stored hashed because the raw user agent is fingerprinting.
    user_agent_hash = Column(String(64), nullable=True)
    ip_hash = Column(String(64), nullable=True)

    def is_active(self, now: datetime | None = None) -> bool:
        """True when this token may still be exchanged for a new pair."""
        if self.revoked_at is not None or self.rotated_at is not None:
            return False
        now = now or datetime.now(timezone.utc)
        expires = self.expires_at
        if expires is None:
            return False
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires > now

    def revoke(self, reason: str) -> None:
        self.revoked_at = datetime.now(timezone.utc)
        self.revoked_reason = reason[:60]


def hash_token(token: str) -> str:
    """SHA-256 hex digest of a refresh token."""
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _client_context(request) -> tuple[str | None, str | None]:
    """Hashed user-agent and client IP for the token row."""
    import hashlib

    ua = None
    ip = None
    if request is not None:
        ua_header = request.headers.get("user-agent")
        if ua_header:
            ua = hashlib.sha256(ua_header.encode("utf-8")).hexdigest()
        from app.core.trusted_proxy import client_ip as _trusted_client_ip

        ip = _trusted_client_ip(request)
        if ip == "unknown":
            ip = None
        if ip:
            ip = hashlib.sha256(ip.encode("utf-8")).hexdigest()
    return ua, ip


def issue_refresh_token(
    db: Session,
    user_id: int,
    family_id: str | None = None,
    request=None,
) -> tuple[str, RefreshToken]:
    """Create a refresh token and return ``(plaintext, row)``.

    The plaintext is returned to the caller once and never stored.
    """
    import secrets
    from datetime import timedelta

    from app.core.config import settings

    plaintext = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    ua_hash, ip_hash = _client_context(request)

    row = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(plaintext),
        family_id=family_id or secrets.token_hex(16),
        issued_at=now,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent_hash=ua_hash,
        ip_hash=ip_hash,
    )
    db.add(row)
    return plaintext, row


def revoke_family(db: Session, family_id: str, reason: str) -> int:
    """Revoke every live token in a family. Returns the number revoked."""
    now = datetime.now(timezone.utc)
    rows = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
        )
        .all()
    )
    for row in rows:
        row.revoked_at = now
        row.revoked_reason = reason[:60]
    return len(rows)


def revoke_all_for_user(db: Session, user_id: int, reason: str) -> int:
    """Revoke every live refresh token belonging to a user."""
    now = datetime.now(timezone.utc)
    rows = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .all()
    )
    for row in rows:
        row.revoked_at = now
        row.revoked_reason = reason[:60]
    return len(rows)


def build_token_pair(
    db: Session,
    user,
    request=None,
    family_id: str | None = None,
) -> dict:
    """Issue an access token and a refresh token for ``user``.

    Returns the JSON body shape the auth endpoints return.
    """
    from app.core.config import settings

    access_token = create_access_token(subject=user.username)
    refresh_plaintext, refresh_row = issue_refresh_token(
        db, user.id, family_id=family_id, request=request
    )
    db.add(refresh_row)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": refresh_plaintext,
        "role": user.role,
        "username": user.username,
        "must_change_password": bool(getattr(user, "must_change_password", False)),
        "mfa_enabled": bool(getattr(user, "mfa_enabled", False)),
    }
