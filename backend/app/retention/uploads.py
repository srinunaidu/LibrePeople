"""Retention of uploaded files.

What this covers
----------------
Only the *uploads*: the CSV an operator uploaded for an import, and the
documents the HR module keeps. Erasure of a person's data from the system
belongs to the security lane, not to this one, and is not implemented here.

The rule
--------
An uploaded file contains whatever personal data the operator put in it. It
is kept for as short a time as it can be:

* it is deleted as soon as the import it belongs to is committed;
* if the import is never committed, it is deleted when the retention period
  expires (seven days by default).

The dry-run row itself is kept. It holds counts, hashes and a file name —
no row data — so the audit trail survives the file that produced it.

The sweep
---------
:func:`purge_expired_uploads` is called opportunistically: at the start of
an import, it removes anything that has already expired. That keeps the
retention promise without needing a scheduler for it. The job queue's
``retention_run`` type is the place a periodic sweep belongs once the
durable worker is in place.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.observability import get_logger
from app.imports.config import settings
from app.models.imports import ImportDryRun, ImportStatus

log = get_logger("karmathy.retention")


def retention_days() -> int:
    """How long an uploaded file is kept before it is deleted."""
    return max(0, int(settings.UPLOAD_RETENTION_DAYS))


def expiry_from_now(now: datetime | None = None) -> datetime:
    """When a file uploaded now should be deleted."""
    moment = now or datetime.now(timezone.utc)
    return moment + timedelta(days=retention_days())


def delete_upload(db: Session, dry_run: ImportDryRun) -> bool:
    """Delete the file behind a dry run.

    The database row is left alone: it is the record that an import was
    validated, and it holds no row data.
    """
    from app.storage import get_storage

    storage = get_storage()
    key = dry_run.storage_key
    try:
        deleted = storage.delete(key)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "could not delete an uploaded file",
            exc_type=type(exc).__name__,
        )
        return False
    if deleted:
        log.info("uploaded file deleted", entity=dry_run.entity)
    return deleted


def purge_expired_uploads(db: Session, now: datetime | None = None) -> int:
    """Delete the files behind dry runs whose retention period has passed.

    The retention period is the upload's, not the token's: an upload that
    was validated and then never committed is kept for
    ``UPLOAD_RETENTION_DAYS`` and then deleted.

    Returns the number of files deleted.
    """
    moment = now or datetime.now(timezone.utc)
    expired = (
        db.query(ImportDryRun)
        .filter(
            ImportDryRun.status == ImportStatus.PENDING,
            ImportDryRun.upload_expires_at <= moment,
        )
        .all()
    )
    deleted = 0
    for dry_run in expired:
        if delete_upload(db, dry_run):
            deleted += 1
        dry_run.status = ImportStatus.EXPIRED
        dry_run.failure_reason = "retention period expired"
        db.add(dry_run)
    if expired:
        db.commit()
        log.info("expired uploads purged", count=deleted)
    return deleted
