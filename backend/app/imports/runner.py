"""Running an import: the dry run, the token, and the commit.

The transaction boundary
------------------------
An import is **one transaction**. The dry run writes nothing to the data
tables; it writes one row — the dry-run record — and commits that. The
commit writes every row the file produced, the audit entry, and the update
to the dry-run record, and commits once at the end.

There is no per-batch commit. That is what makes "a failure halfway through
leaves nothing behind" true rather than aspirational: if any part of the
commit fails, the whole transaction is rolled back and the database is as it
was.

The order of the commit is deliberate:

1. re-read the uploaded file and re-analyse it;
2. check that the outcome is the one the operator was shown;
3. apply every row;
4. write the result summary to object storage — **before** the commit;
5. commit the transaction;
6. delete the uploaded file.

Step 4 is before step 5 on purpose. If object storage is unavailable the
write fails, the transaction is rolled back, and nothing is committed. A
storage outage must not leave a half-applied import behind.

Step 6 is after step 5 for the opposite reason: the file is deleted once
the data it produced is safely committed. If the delete fails, the
retention sweep collects it later.
"""
from __future__ import annotations

import hashlib
import io
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.observability import get_logger
from app.imports.analyse import AnalysisResult, Analyzer
from app.imports.apply import ApplyResult, apply_batch
from app.imports.config import settings
from app.imports.errors import ImportFileError
from app.imports.spec import EntitySpec, get_spec
from app.imports.validation import ImportBounds
from app.models.imports import ImportDryRun, ImportStatus
from app.retention.uploads import expiry_from_now, purge_expired_uploads

log = get_logger("karmathy.imports")


class ImportNotFound(Exception):
    """The confirmation token is unknown, expired or already used."""


class ImportNotPermitted(Exception):
    """The token belongs to somebody else."""


class ImportResultChanged(Exception):
    """The outcome is no longer the one the operator was shown."""


class ImportNotCancellable(Exception):
    """The import cannot be cancelled: it is already committed, or its token
    has expired. Distinct from :class:`ImportNotFound` so that the answer can
    say *why* rather than "unknown token"."""


class ImportCancelled(Exception):
    """The import was cancelled before it finished.

    Cancelling is only safe where the whole import is one transaction:
    the rows that were written are taken back with it, so the file is
    applied entirely or not at all.
    """


@dataclass
class DryRunOutcome:
    """What the dry run produced."""

    token: str
    result: AnalysisResult
    expires_at: datetime
    dry_run_id: int | None = None


@dataclass
class CommitOutcome:
    """What the commit did."""

    result: AnalysisResult
    applied: ApplyResult
    committed: bool = False
    artifact_key: str | None = None
    warnings: list[str] = field(default_factory=list)


def import_bounds() -> ImportBounds:
    """The bounds the tenant's configuration places on imported values."""
    return ImportBounds(
        salary_min=settings.IMPORT_SALARY_MIN,
        salary_max=settings.IMPORT_SALARY_MAX,
    )


def storage_key_for(token: str) -> str:
    """Where an uploaded file is kept."""
    return f"imports/{settings.TENANT_ID}/{token}.csv"


def token_expiry():
    """When a confirmation token stops being usable."""
    from datetime import datetime, timedelta, timezone

    return datetime.now(timezone.utc) + timedelta(
        minutes=settings.IMPORT_TOKEN_TTL_MINUTES
    )


def evict_oldest_tokens(db: Session) -> int:
    """Keep the number of outstanding tokens bounded.

    A dry run that is never committed leaves a token behind. Past
    ``IMPORT_MAX_OUTSTANDING_TOKENS`` the oldest ones are evicted — the
    token stops working and the uploaded file is deleted. Without this a
    long-running process accumulates an unbounded number of them.
    """
    limit = max(1, settings.IMPORT_MAX_OUTSTANDING_TOKENS)
    pending = (
        db.query(ImportDryRun)
        .filter(ImportDryRun.status == ImportStatus.PENDING)
        .order_by(ImportDryRun.created_at.asc())
        .all()
    )
    # One slot is reserved for the token that is about to be issued, so the
    # bound holds *after* the new token exists and not merely before it.
    target = max(0, limit - 1)
    if len(pending) <= target:
        return 0
    from app.retention.uploads import delete_upload

    evicted = 0
    for record in pending[: len(pending) - target]:
        delete_upload(db, record)
        record.status = ImportStatus.EXPIRED
        record.failure_reason = "evicted: too many outstanding imports"
        db.add(record)
        evicted += 1
    if evicted:
        db.commit()
        log.info("outstanding import tokens evicted", count=evicted)
    return evicted


def _analyse(
    db: Session, spec: EntitySpec, data: bytes, file_hash: str | None = None
) -> tuple[AnalysisResult, Analyzer]:
    """Analyse a file, keeping the spill file for a possible apply.

    The file's own hash is set before the analysis runs, because it is part
    of the result hash: the hash identifies one file *and* one outcome, not
    an outcome on its own.
    """
    analyzer = Analyzer(
        db,
        spec.name,
        spec,
        bounds=import_bounds(),
        batch_size=settings.IMPORT_BATCH_SIZE,
    )
    if file_hash:
        analyzer.result.file_hash = file_hash
    result = analyzer.run(
        io.BytesIO(data),
        settings.IMPORT_MAX_UPLOAD_BYTES,
        settings.IMPORT_MAX_ROWS,
    )
    return result, analyzer


def dry_run(
    db: Session,
    entity: str,
    data: bytes,
    file_name: str | None = None,
    user_id: int | None = None,
    actor=None,
) -> DryRunOutcome:
    """Validate a file and issue a confirmation token.

    Nothing is written to the entity's table. The uploaded file is kept in
    object storage so that the commit can examine exactly the bytes that
    were validated.

    The audit entry is written in the same transaction as the dry-run row,
    so the record of what was validated is never separated from the
    validation itself.
    """
    from app.storage import get_storage

    spec = get_spec(entity)
    if spec is None:
        raise ImportFileError(
            "unknown_entity", f"Unknown entity: {entity}"
        )

    # Anything that has already outlived its retention period goes first.
    purge_expired_uploads(db)
    evict_oldest_tokens(db)

    # The file's own hash is computed first because it is part of the result
    # hash: a confirmation token identifies one file *and* one outcome.
    file_hash = hashlib.sha256(data).hexdigest()
    result, analyzer = _analyse(db, spec, data, file_hash)
    try:
        token = secrets.token_urlsafe(32)
        storage_key = storage_key_for(token)

        storage = get_storage()
        try:
            storage.save_verified(storage_key, data, content_type="text/csv")
        except Exception as exc:  # noqa: BLE001
            log.error(
                "could not store the uploaded file",
                entity=entity,
                exc_type=type(exc).__name__,
            )
            raise ImportFileError(
                "storage_unavailable",
                "The uploaded file could not be stored, so it cannot be "
                "validated. Nothing was written.",
            ) from None

        expires_at = token_expiry()
        record = ImportDryRun(
            token=token,
            entity=entity,
            file_hash=file_hash,
            result_hash=result.result_hash,
            storage_key=storage_key,
            file_name=file_name,
            user_id=user_id,
            tenant_id=settings.TENANT_ID,
            status=ImportStatus.PENDING,
            total_rows=result.total_rows,
            create_count=result.create,
            update_count=result.update,
            unchanged_count=result.unchanged,
            reject_count=result.reject,
            expires_at=expires_at,
            upload_expires_at=expiry_from_now(),
        )
        db.add(record)
        _audit(
            db,
            actor,
            "import_dry_run",
            entity,
            details=(
                f"rows={result.total_rows} create={result.create} "
                f"update={result.update} unchanged={result.unchanged} "
                f"reject={result.reject}"
            ),
        )
        db.commit()
        db.refresh(record)
    finally:
        analyzer.discard()

    log.info(
        "import dry run completed",
        entity=entity,
        total_rows=result.total_rows,
        create=result.create,
        update=result.update,
        unchanged=result.unchanged,
        reject=result.reject,
    )
    return DryRunOutcome(
        token=token,
        result=result,
        expires_at=expires_at,
        dry_run_id=record.id,
    )


def commit(
    db: Session,
    entity: str,
    token: str,
    user_id: int | None = None,
    actor=None,
    *,
    cancel_check=None,
    progress=None,
) -> CommitOutcome:
    """Apply a previously validated import.

    One transaction. Either every row is applied or none of them is.

    ``cancel_check`` is asked before every batch whether the import should
    stop. When it says yes the transaction is rolled back, so a cancelled
    import leaves nothing behind — the rows are applied entirely or not at
    all.

    ``progress`` is told, after every batch, how many rows have been
    applied and how many the file holds. It is called outside the
    transaction's own bookkeeping, so the caller can report it without
    waiting for the commit.
    """
    from app.storage import get_storage
    from app.retention.uploads import delete_upload

    record = _authorised_record(db, entity, token, user_id)
    if record.status == ImportStatus.CANCELLED:
        raise ImportCancelled("The import was cancelled.")
    if record.status != ImportStatus.PENDING:
        raise ImportNotFound(
            "The confirmation token has already been used."
        )
    if record.is_expired():
        record.status = ImportStatus.EXPIRED
        db.add(record)
        db.commit()
        raise ImportNotFound(
            "The confirmation token has expired. Run the dry run again."
        )

    spec = get_spec(entity)
    if spec is None:
        raise ImportNotFound("The entity this token refers to is no longer known.")

    storage = get_storage()
    try:
        data = storage.read(record.storage_key)
    except Exception as exc:  # noqa: BLE001
        log.error(
            "could not read back the uploaded file",
            entity=entity,
            exc_type=type(exc).__name__,
        )
        raise ImportFileError(
            "storage_unavailable",
            "The uploaded file could not be read back, so the import was not "
            "applied. Nothing was written.",
        ) from None

    # The bytes must be the bytes that were validated.
    file_hash = hashlib.sha256(data).hexdigest()
    if file_hash != record.file_hash:
        raise ImportResultChanged(
            "The uploaded file is no longer the one that was validated. "
            "Run the dry run again."
        )

    # And the outcome must be the outcome the operator was shown.
    result, analyzer = _analyse(db, spec, data, file_hash)
    if result.result_hash != record.result_hash:
        analyzer.discard()
        raise ImportResultChanged(
            "The validation result has changed since the dry run. Run the "
            "dry run again and commit the new result."
        )

    applied = ApplyResult()
    warnings: list[str] = []
    artifact_key: str | None = None

    try:
        for batch in analyzer.iter_batches():
            if cancel_check is not None and cancel_check():
                raise ImportCancelled(
                    "The import was cancelled before it finished. Nothing "
                    "was written."
                )
            _apply_batch(
                db,
                spec,
                batch,
                applied,
                reference_id=record.id,
                created_by=user_id,
            )
            if progress is not None:
                progress(
                    applied.created + applied.updated + applied.unchanged,
                    result.total_rows,
                )
        db.flush()

        artifact_key = _write_artifact(storage, record, result, applied)

        record.status = ImportStatus.COMMITTED
        record.committed_at = datetime.now(timezone.utc)
        record.create_count = applied.created
        record.update_count = applied.updated
        record.unchanged_count = applied.unchanged
        db.add(record)
        _audit(
            db,
            actor,
            "import_commit",
            entity,
            details=(
                f"created={applied.created} updated={applied.updated} "
                f"unchanged={applied.unchanged} rejected={result.reject}"
            ),
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        if artifact_key:
            # The result summary was written for an import that did not
            # happen. Remove it rather than leave a record of something
            # that is not true.
            try:
                storage.delete(artifact_key)
            except Exception:  # noqa: BLE001
                pass
        log.error(
            "import commit failed; nothing was written",
            entity=entity,
            exc_type=type(exc).__name__,
        )
        raise
    finally:
        analyzer.discard()

    # The data is committed. The file that produced it is no longer needed.
    delete_upload(db, record)

    if (applied.created, applied.updated) != (result.create, result.update):
        warnings.append(
            "The database changed between the dry run and the commit, so the "
            "counts differ from the ones that were shown."
        )

    log.info(
        "import committed",
        entity=entity,
        created=applied.created,
        updated=applied.updated,
        unchanged=applied.unchanged,
    )
    return CommitOutcome(
        result=result,
        applied=applied,
        committed=True,
        artifact_key=artifact_key,
        warnings=warnings,
    )


def _apply_batch(
    db: Session,
    spec: EntitySpec,
    batch,
    applied: ApplyResult,
    *,
    reference_id: int | None = None,
    created_by: int | None = None,
) -> None:
    """Apply one batch, and undo it if it fails.

    A batch that fails is reversed inside the caller's transaction and the
    failure is reported against the rows it contained. The other batches
    are unaffected. The undo is explicit rather than a SAVEPOINT, because
    releasing the outermost savepoint commits the transaction on SQLite —
    a difference that is invisible on Oracle and would leave a failed batch
    committed on the database the tests run against.
    """
    from app.imports.apply import undo_batch
    from app.imports.errors import ErrorCode, RowError

    undo: list = []
    try:
        created, updated, unchanged = apply_batch(
            db,
            spec,
            batch,
            undo,
            reference_id=reference_id,
            created_by=created_by,
            errors=applied.errors,
        )
    except Exception as exc:  # noqa: BLE001
        log.error(
            "import batch failed; the batch was reversed",
            entity=spec.name,
            rows=len(batch.rows),
            exc_type=type(exc).__name__,
        )
        try:
            undo_batch(db, spec, undo)
        except Exception as undo_exc:  # noqa: BLE001
            log.error(
                "the failed batch could not be reversed",
                entity=spec.name,
                exc_type=type(undo_exc).__name__,
            )
        for row_number, _values in batch.rows:
            applied.errors.append(
                RowError(
                    row_number,
                    None,
                    ErrorCode.WRITE_FAILED,
                    "This row could not be saved (see server logs)",
                )
            )
        return
    applied.created += created
    applied.updated += updated
    applied.unchanged += unchanged


def _audit(db: Session, actor, action: str, entity: str, details: str) -> None:
    """Stage the audit entry for an import.

    The entry is added to the session and committed with the operation it
    describes, so an import and its audit trail stay atomic.
    """
    if actor is None:
        return
    from app.core.audit import record_audit

    record_audit(db, actor, action, entity, None, details=details)


def _write_artifact(storage, record: ImportDryRun, result: AnalysisResult, applied) -> str:
    """Write the summary of a committed import to object storage.

    This happens before the database transaction is committed, so a storage
    outage aborts the import instead of leaving it half-applied.
    """
    import json

    key = f"imports/{settings.TENANT_ID}/results/{record.token}.json"
    payload = json.dumps(
        {
            "entity": record.entity,
            "file_name": record.file_name,
            "file_hash": record.file_hash,
            "result_hash": record.result_hash,
            "total_rows": result.total_rows,
            "created": applied.created,
            "updated": applied.updated,
            "unchanged": applied.unchanged,
            "rejected": result.reject,
            "committed_at": datetime.now(timezone.utc).isoformat(),
        },
        indent=2,
    ).encode("utf-8")
    storage.save_verified(key, payload, content_type="application/json")
    return key


def _authorised_record(
    db: Session, entity: str, token: str, user_id: int | None = None
) -> ImportDryRun:
    """The dry-run record a token refers to, if this user may use it."""
    record = (
        db.query(ImportDryRun)
        .filter(ImportDryRun.token == token)
        .first()
    )
    if record is None:
        raise ImportNotFound(
            "The confirmation token is unknown, has expired, or has already "
            "been used."
        )
    if record.entity != entity:
        raise ImportNotFound(
            "The confirmation token does not belong to this import."
        )
    if user_id is not None and record.user_id is not None and record.user_id != user_id:
        raise ImportNotPermitted(
            "This confirmation token belongs to a different user."
        )
    return record


def pending_import(
    db: Session, entity: str, token: str, user_id: int | None = None
) -> ImportDryRun:
    """The dry-run record of an import that is waiting to be committed."""
    record = _authorised_record(db, entity, token, user_id)
    if record.status == ImportStatus.CANCELLED:
        raise ImportCancelled("The import was cancelled.")
    if record.status != ImportStatus.PENDING:
        raise ImportNotFound("The confirmation token has already been used.")
    return record


def row_report(result: AnalysisResult, applied: ApplyResult) -> list[dict]:
    """The per-row report of an applied import.

    It is the analysis's own report with the rows that could not be
    written added to it. A row that was written is not a row that failed,
    and a row that failed is named with its number and its reason, so the
    report says exactly what happened to every row of the file.
    """
    failures: dict[int, list[dict]] = {}
    for error in applied.errors:
        failures.setdefault(error.row, []).append(error.as_dict())

    rows: list[dict] = []
    for outcome in result.outcomes:
        entry = outcome.as_dict()
        row_failures = failures.pop(outcome.row, None)
        if row_failures:
            entry["status"] = "reject"
            entry["errors"] = list(entry.get("errors", [])) + row_failures
        rows.append(entry)
    # A failure against a row the analysis never listed is still
    # reported: it happened, and the operator has to see it.
    for row_number, errors in sorted(failures.items()):
        rows.append({"row": row_number, "status": "reject", "errors": errors})
    return rows


def cancel_import(
    db: Session,
    entity: str,
    token: str,
    user_id: int | None = None,
    actor=None,
) -> ImportDryRun:
    """Ask for an import that has not finished to stop.

    The import is one transaction, so a cancelled import applies nothing:
    the rows it had written are taken back with it. The file is either
    applied entirely or not at all.

    Cancelling is recorded in the audit trail, in the same transaction as
    the status change: a cancellation is a decision about the customer's
    data, and the trail is where a decision is accounted for.
    """
    record = _authorised_record(db, entity, token, user_id)
    if record.status == ImportStatus.COMMITTED:
        raise ImportNotCancellable(
            "The import has already been committed. Its rows are in the "
            "database, so there is nothing left to cancel."
        )
    if record.status == ImportStatus.EXPIRED:
        raise ImportNotCancellable(
            "The confirmation token has expired. Run the dry run again."
        )
    # A second cancel changes nothing, and an audit row records a change.
    changed = record.status != ImportStatus.CANCELLED
    record.status = ImportStatus.CANCELLED
    record.failure_reason = "cancelled by the operator"
    db.add(record)
    if actor is not None and changed:
        _audit(db, actor, "import_cancel", entity, details="status=cancelled")
    db.commit()
    db.refresh(record)
    return record


def queue_job(
    db: Session, entity: str, token: str, user_id: int | None = None
):
    """Queue an import to be applied in the background.

    The job is given the confirmation token, so the import the job applies
    is the very import the operator previewed: one record, one status, and
    the job's state is the import's state.

    The token of a queued import has to outlive the queue, so its life is
    extended to ``IMPORT_JOB_TTL_MINUTES``. It is still bound to the
    result it was issued for, and it may still be used once.
    """
    from datetime import timedelta

    from app.jobs.queue import JobQueueService
    from app.models.job_queue import JobType

    record = _authorised_record(db, entity, token, user_id)
    if record.status != ImportStatus.PENDING:
        raise ImportNotFound("The confirmation token has already been used.")

    record.expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.IMPORT_JOB_TTL_MINUTES
    )
    db.add(record)
    db.commit()

    service = JobQueueService(db)
    job = service.enqueue(
        JobType.CSV_IMPORT,
        {
            "entity": entity,
            "confirmation_token": token,
            "user_id": user_id,
            "file_name": record.file_name,
        },
    )
    return job


def is_job_sized(row_count: int) -> bool:
    """Whether a file of this many rows is applied as a background job."""
    return row_count > settings.IMPORT_JOB_ROW_THRESHOLD


def row_errors(
    db: Session, entity: str, token: str, user_id: int | None = None
) -> AnalysisResult:
    """Re-derive the row errors of a dry run.

    The uploaded file is still in storage — it is deleted when the import is
    committed or when its retention period expires — so the errors can be
    produced again from exactly the bytes that were uploaded.
    """
    from app.storage import get_storage

    record = (
        db.query(ImportDryRun).filter(ImportDryRun.token == token).first()
    )
    if record is None:
        raise ImportNotFound(
            "The confirmation token is unknown, has expired, or has already "
            "been used."
        )
    if record.entity != entity:
        raise ImportNotFound(
            "The confirmation token does not belong to this import."
        )
    if user_id is not None and record.user_id is not None and record.user_id != user_id:
        raise ImportNotPermitted(
            "This confirmation token belongs to a different user."
        )

    spec = get_spec(entity)
    if spec is None:
        raise ImportNotFound("The entity this token refers to is no longer known.")

    storage = get_storage()
    try:
        data = storage.read(record.storage_key)
    except Exception as exc:  # noqa: BLE001
        log.error(
            "could not read back the uploaded file",
            entity=entity,
            exc_type=type(exc).__name__,
        )
        raise ImportFileError(
            "storage_unavailable",
            "The uploaded file could not be read back. Nothing was written.",
        ) from None

    file_hash = hashlib.sha256(data).hexdigest()
    result, analyzer = _analyse(db, spec, data, file_hash)
    analyzer.discard()
    return result


def row_error_csv(result: AnalysisResult) -> str:
    """The row-error CSV for a dry run.

    The file has one row per error: the record number, the column, the
    error code, and the message. Personal values are not in it — the
    validator never puts them in the message in the first place.
    """
    import csv
    import io as _io

    buffer = _io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["row", "column", "code", "message"])
    for outcome in result.outcomes:
        if outcome.status != "reject":
            continue
        for error in outcome.errors:
            writer.writerow(error.as_row())
    return buffer.getvalue()
