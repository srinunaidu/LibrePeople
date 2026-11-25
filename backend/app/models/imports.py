"""The record of a CSV import that has been validated but not yet committed.

Why this is a table and not a dictionary
----------------------------------------
The previous implementation kept dry-run results in a module-level
dictionary. That had three consequences, all of them bad:

* it was **unbounded**, so a long-running process leaked memory;
* it did not **survive a restart**, so a confirmation token became
  unusable when the process was redeployed between the dry run and the
  commit — and, worse, a token that *was* still in memory was the only
  evidence that a file had been validated;
* it was **not scoped to the user who asked for it**, so one operator could
  commit another operator's import.

A row in this table fixes all three. The token is unique, the row records
who asked for the dry run, and the file the dry run examined is kept in
object storage so that the commit can re-examine exactly those bytes.

The token is bound to the *result* hash
--------------------------------------
The row stores the hash of the dry-run outcome. The commit re-analyses the
stored bytes and recomputes the hash. If the outcome has changed — because
the database changed underneath the operator, or because the file was
tampered with in storage — the commit is refused with a 409 and the
operator is told to run the dry run again. The token is not a promise the
client makes; it is a statement about a specific outcome.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Identity, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class ImportStatus:
    """The lifecycle of a dry run."""

    PENDING = "pending"
    COMMITTED = "committed"
    EXPIRED = "expired"
    FAILED = "failed"
    #: The import was cancelled before it finished. A cancelled import
    #: applies nothing: it is one transaction, so the rows it had written
    #: are taken back with it.
    CANCELLED = "cancelled"


class ImportDryRun(Base):
    """A validated import waiting to be committed."""

    __tablename__ = "import_dry_runs"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    #: The confirmation token handed to the operator.
    #:
    #: The column is unique and it is *not* also indexed. A unique
    #: constraint already has an index behind it, so a second index over
    #: the same column list is refused by Oracle with ORA-01408 ("such
    #: column list already indexed") — the error that failed the
    #: deployment of the import feature. The uniqueness is expressed as a
    #: constraint rather than as a bare index, because an index is an
    #: optimisation and a constraint is the promise that a token may not
    #: be used twice.
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    #: The entity the file was validated against.
    entity: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    #: Hash of the uploaded bytes. Binds the token to one exact file.
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    #: Hash of the dry-run outcome. Binds the token to one exact result.
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    #: Where the uploaded file is kept in object storage.
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)

    #: The name of the file the operator uploaded, for the audit trail.
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    #: Who asked for the dry run. Only that user may commit it.
    user_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )

    #: The deployment the import belongs to. Under the one-customer-per-
    #: deployment model this is one value per deployment, but it is recorded
    #: on every row so that a misconfigured deployment is visible in the
    #: data rather than inferred.
    tenant_id: Mapped[str] = mapped_column(String(60), nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ImportStatus.PENDING, index=True
    )

    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    create_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    update_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reject_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    #: When the confirmation token stops being usable. Fifteen minutes by
    #: default: long enough for an operator to read a preview, short enough
    #: that a forgotten preview is not a stale one.
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    #: When the uploaded file is deleted if the import is never committed.
    #: Seven days by default. It is longer than the token's life because
    #: the file is the operator's data, and the retention rule for it is
    #: the retention rule, not the token's.
    upload_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    committed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    #: Why a commit was refused, when it was.
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    def is_expired(self, now: datetime | None = None) -> bool:
        moment = now or datetime.now(timezone.utc)
        expires = self.expires_at
        if expires is None:
            return False
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires <= moment

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ImportDryRun(id={self.id}, entity={self.entity!r}, "
            f"status={self.status!r})>"
        )
