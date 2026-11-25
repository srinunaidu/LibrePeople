"""Idempotency and optimistic concurrency.

Two failure modes this addresses, both raised by the mission brief:

*"Retries must not duplicate employees, payroll operations, payments,
notifications, or other side effects."*
    -> :func:`IdempotencyGuard` / the ``Idempotency-Key`` dependency.

*"Conflicting updates"* — two people editing the same employee at once.
    -> :func:`require_unmodified` / the ``If-Unmodified-Since`` check.

Why a database table rather than an in-process dict
----------------------------------------------------
The process can restart or run more than one replica. An in-memory cache would
silently forget a key and let a duplicate through. The request fingerprint is
stored alongside the key so a *different* payload reusing the same key is
rejected rather than silently returning the wrong cached response.

Behaviour
---------
* First call with a key: no row -> the endpoint runs -> a row records the key,
  the request fingerprint and the response.
* Repeat call, same key, same payload: the stored response is replayed with
  ``Idempotent-Replay: true``. No second side effect.
* Repeat call, same key, **different** payload: 409 ``idempotency_key_reuse``.
  This is a client bug; silently replaying would be worse than failing.
* Same call while the first is still in flight: 409 ``request_in_flight``.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import Depends, Header, Request, status
from sqlalchemy import (
    Column,
    DateTime,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.errors import ApiError, ErrorCategory, conflict, concurrency_conflict
from app.core.observability import get_logger

log = get_logger("karmathy.idempotency")


class IdempotencyRecord(Base):
    """Bookkeeping for a completed or in-flight idempotent operation.

    Uses ``Identity()`` rather than ``autoincrement=True`` to match every other
    model in this codebase. On Oracle, a plain autoincrement integer primary key
    raises ORA-01408 ("column may not be implicitly specified") and the table is
    silently never created by ``create_all`` -- which would leave the
    idempotency guard broken on the primary database.
    """

    __tablename__ = "idempotency_records"
    __table_args__ = (
        # The database-level guard against two concurrent identical requests
        # claiming the same key.
        UniqueConstraint("key", name="uq_idempotency_key"),
    )

    id = Column(Integer, Identity(), primary_key=True)
    key = Column(String(200), nullable=False)
    endpoint = Column(String(300), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="in_progress")
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


def fingerprint_request(method: str, path: str, body: Any) -> str:
    """Stable hash of the request payload.

    Falls back to the raw body when it is not JSON-serialisable, so a
    fingerprint is always computable.
    """
    try:
        serialised = json.dumps(body, sort_keys=True, default=str)
    except (TypeError, ValueError):
        serialised = str(body)
    raw = f"{method.upper()} {path} {serialised}"
    return hashlib.sha256(raw.encode()).hexdigest()


class IdempotencyGuard:
    """Context manager wrapping a mutating operation."""

    def __init__(
        self,
        db: Session,
        key: str | None,
        endpoint: str,
        payload: Any,
        method: str = "POST",
    ) -> None:
        self.db = db
        self.key = key
        self.endpoint = endpoint
        self.fingerprint = fingerprint_request(method, endpoint, payload)
        self.replayed = False
        self._stored_response: str | None = None
        self._to_store: str | None = None

    def store(self, payload: Any) -> None:
        """Record what to replay on a duplicate call.

        Call inside the ``with`` block with a small, replay-safe summary (e.g.
        the created record's id) — not a full response body, which may contain
        data the caller is not entitled to fetch twice.
        """
        try:
            self._to_store = json.dumps(payload, default=str)
        except (TypeError, ValueError):
            self._to_store = None

    def __enter__(self) -> "IdempotencyGuard":
        if not self.key:
            return self

        existing = (
            self.db.query(IdempotencyRecord)
            .filter(IdempotencyRecord.key == self.key)
            .first()
        )

        if existing:
            if existing.fingerprint != self.fingerprint:
                # Same key, different payload: the client reused a key by
                # mistake. Refusing is safer than replaying the wrong result.
                raise conflict(
                    "idempotency_key_reuse",
                    "This idempotency key was already used with a different "
                    "request payload. Use a new key.",
                    endpoint=self.endpoint,
                )
            if existing.status == "in_progress":
                # The original is still running. Another 409 is friendlier than
                # blocking, and prevents a concurrent duplicate.
                raise conflict(
                    "request_in_flight",
                    "An identical request is still being processed. "
                    "Wait for it to finish before retrying.",
                )
            self.replayed = True
            self._stored_response = existing.response_body
            return self

        # Claim the key. The unique index is the real guard against a race.
        self.db.add(
            IdempotencyRecord(
                key=self.key,
                endpoint=self.endpoint,
                fingerprint=self.fingerprint,
                status="in_progress",
            )
        )
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            # Lost the race against a concurrent identical request.
            raise conflict(
                "request_in_flight",
                "An identical request is already being processed.",
            ) from None
        return self

    @property
    def stored_response(self) -> str | None:
        return self._stored_response

    def __exit__(self, exc_type, exc, tb) -> bool:
        if not self.key or self.replayed:
            return False
        try:
            if exc_type is not None:
                # Failed: release the key so a genuine retry can proceed.
                self.db.query(IdempotencyRecord).filter(
                    IdempotencyRecord.key == self.key
                ).delete()
                self.db.commit()
            else:
                self.db.query(IdempotencyRecord).filter(
                    IdempotencyRecord.key == self.key
                ).update(
                    {"status": "completed", "response_body": self._to_store}
                )
                self.db.commit()
        except Exception:  # noqa: BLE001
            self.db.rollback()
            log.warning("failed to finalise idempotency record", key=self.key)
        return False


async def idempotency_key(
    request: Request,
    idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key"),
) -> str | None:
    """Dependency returning the caller's idempotency key, if supplied."""
    if idempotency_key_header is None:
        return None
    key = idempotency_key_header.strip()
    if not key or len(key) > 200:
        raise ApiError(
            "invalid_idempotency_key",
            "Idempotency-Key must be 1-200 characters",
            ErrorCategory.VALIDATION,
        )
    # Scope the key by user + path so two users cannot collide, and a client
    # cannot probe another user's operation by guessing a key.
    user = getattr(request.state, "user", None)
    user_id = getattr(user, "id", None) or "anon"
    return f"{user_id}:{request.method}:{request.url.path}:{key}"


# --- Optimistic concurrency ------------------------------------------------ #


def require_unmodified(record, expected_updated_at, field: str = "record") -> None:
    """Raise 409 if the record changed since the caller read it.

    Pass the ``updated_at`` value the client last saw. A mismatch means someone
    else saved first, and silently overwriting their work is exactly the lost
    update this prevents.
    """
    if expected_updated_at is None:
        return  # client did not opt in
    current = getattr(record, "updated_at", None)
    if current is None:
        return
    if _as_utc(current) != _as_utc(expected_updated_at):
        raise concurrency_conflict(
            f"This {field} was modified by someone else after you opened it. "
            "Reload to see the latest values, then reapply your change.",
        )


def _as_utc(value: datetime) -> datetime:
    """Naive datetimes (SQLite) vs aware (Oracle) must compare equal."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)