"""The progress of a queued import.

Why this exists
---------------
A file over ``IMPORT_JOB_ROW_THRESHOLD`` is applied by a background job. The
job takes the operator's confirmation token, applies the import in one
transaction, and records how far it has got after every batch. Until this
module existed, **none of that was readable**: the 202 told the operator the
work was accepted and there was no way to ask what happened next. A job that
cannot be watched is a job that is trusted on faith.

Two sources, and why both
-------------------------
* **The job row** says whether the work is queued, running, done, failed or
  dead, and when it started and finished. It is authoritative for *state*.
* **The progress file** says how many rows have been applied so far. It is a
  file in object storage rather than a database row because the import is one
  transaction: a progress row written inside it would be taken back with the
  import when it fails, and the record of the work would be lost exactly when
  an operator needs it.
* **The dry-run record** says how many rows the file holds and how many were
  rejected, because those were known before the job started.

The endpoint reports all three, and it never guesses: when the job failed,
the transaction rolled back, so the rows it had applied are **not** in the
database. Reporting "312 rows applied" for a failed import would be a lie
that an operator would act on, so the count is reported as zero and the
number reached before the failure is reported separately, with the reason.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.imports.config import settings
from app.models.imports import ImportDryRun, ImportStatus
from app.models.job_queue import JobQueue, JobState, JobType


class ImportProgressNotFound(Exception):
    """The job is not this entity's import, or not this operator's.

    One exception for both cases on purpose. A job id is a small integer, so
    answering 403 for another operator's job would confirm that the job
    exists; 404 says nothing an attacker can use.
    """


# --------------------------------------------------------------------------
# The progress file
# --------------------------------------------------------------------------


def progress_key(job_id: int, entity: str) -> str:
    """Where the handler records how far an import has got."""
    return f"imports/{settings.TENANT_ID}/progress/{entity}/{job_id}.json"


def write_counts(job_id: int, entity: str, done: int, total: int) -> None:
    """Record how far the import has got.

    A storage outage must not stop the import that is being applied: the
    progress is a report, not a promise, so a failure here is swallowed and
    the reader falls back to the job's own state.
    """
    from app.storage import get_storage

    payload = {
        "entity": entity,
        "job_id": job_id,
        "rows_applied": done,
        "total_rows": total,
        "percent": int((done * 100) / total) if total else 100,
        "state": JobState.RUNNING,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": settings.TENANT_ID,
    }
    try:
        get_storage().save_verified(
            progress_key(job_id, entity),
            json.dumps(payload, indent=2).encode("utf-8"),
            content_type="application/json",
        )
    except Exception:  # noqa: BLE001
        pass


def read_counts(job_id: int, entity: str) -> Optional[dict[str, Any]]:
    """The last progress the handler recorded, or None."""
    from app.storage import get_storage

    try:
        raw = get_storage().read(progress_key(job_id, entity))
    except Exception:  # noqa: BLE001
        return None
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------


def _payload(job: JobQueue) -> Optional[dict[str, Any]]:
    """The parameters the job was enqueued with, or None.

    A job queued before `0024_job_input_payload` has no payload. It cannot be
    matched to an entity or to an operator, so it is not served: guessing
    which import it was would be worse than saying it is unknown.
    """
    if not job.input_json:
        return None
    try:
        payload = json.loads(job.input_json)
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _iso(moment: Optional[datetime]) -> Optional[str]:
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.isoformat()


def _batches(rows: int, batch_size: int) -> int:
    if rows <= 0 or batch_size <= 0:
        return 0
    return math.ceil(rows / batch_size)


def _report(job: JobQueue) -> Optional[dict[str, Any]]:
    """The stored result of a finished job, or None.

    A job that succeeded before `0025_job_result_payload` has a result hash
    and no result. ``result_stored: false`` says so, rather than letting an
    empty object read as "it produced nothing".
    """
    if not job.result_json:
        return None
    try:
        report = json.loads(job.result_json)
    except (TypeError, ValueError):
        return None
    return report if isinstance(report, dict) else None


def job_progress(
    db: Session,
    entity: str,
    job_id: int,
    user_id: Optional[int] = None,
) -> dict[str, Any]:
    """The progress of one queued import, as the job and the import agree it."""
    job = db.query(JobQueue).filter(JobQueue.id == job_id).first()
    if job is None or str(job.job_type) != JobType.CSV_IMPORT.value:
        raise ImportProgressNotFound(
            f"No import job {job_id} exists for this entity."
        )

    payload = _payload(job)
    if payload is None or payload.get("entity") != entity:
        raise ImportProgressNotFound(
            f"No import job {job_id} exists for this entity."
        )

    owner = payload.get("user_id")
    if owner is not None and user_id is not None and owner != user_id:
        raise ImportProgressNotFound(
            f"No import job {job_id} exists for this entity."
        )

    token = payload.get("confirmation_token") or payload.get("token")
    record = None
    if token:
        record = (
            db.query(ImportDryRun)
            .filter(ImportDryRun.token == token)
            .first()
        )

    state = str(job.state)
    finished = state == JobState.SUCCEEDED
    failed = state in (JobState.FAILED, JobState.DEAD)

    counts = read_counts(job_id, entity) or {}
    report = _report(job) if finished else None

    # The file's size and its rejects were known before the job started.
    total = record.total_rows if record is not None else counts.get("total_rows")
    total = int(total or 0)
    rejected = record.reject_count if record is not None else 0
    rejected = int(rejected or 0)
    accepted = max(total - rejected, 0)

    before_failure = int(counts.get("rows_applied") or 0)

    if finished and report is not None:
        applied = int(
            (report.get("created") or 0)
            + (report.get("updated") or 0)
            + (report.get("unchanged") or 0)
        )
        rejected = int(report.get("reject") or rejected)
        accepted = max(int(report.get("total_rows") or total) - rejected, 0)
    elif failed:
        # The import is one transaction. A failed job rolled it back, so no
        # row it had reached is in the database.
        applied = 0
    else:
        applied = before_failure

    pending = max(accepted - applied, 0)
    percent = 100 if finished else (0 if accepted == 0 else int(applied * 100 / accepted))
    if failed:
        percent = 0

    batch_size = settings.IMPORT_BATCH_SIZE
    batches_total = _batches(accepted, batch_size)
    batches_done = 0 if failed else min(_batches(applied, batch_size), batches_total)

    import_status = record.status if record is not None else None

    return {
        "entity": entity,
        "job": {
            "id": job.id,
            "type": str(job.job_type),
            "state": state,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "created_at": _iso(job.created_at),
            "started_at": _iso(job.started_at),
            "finished_at": _iso(job.finished_at),
        },
        "state": state,
        "import_status": import_status,
        "committed": import_status == ImportStatus.COMMITTED,
        "rows_total": total,
        "rows_accepted": accepted,
        "rows_applied": applied,
        "rows_rejected": rejected,
        "rows_pending": pending,
        "rows_applied_before_failure": before_failure if failed else 0,
        "batches_done": batches_done,
        "batches_total": batches_total,
        "batch_size": batch_size,
        "percent": percent,
        "updated_at": counts.get("updated_at") or _iso(job.finished_at or job.started_at),
        "result": report,
        "result_stored": report is not None,
        "failure": (
            {"code": job.error_code, "message": job.error_message}
            if job.error_code
            else None
        ),
        "note": _note(state, import_status, failed),
    }


def _note(state: str, import_status: Optional[str], failed: bool) -> str:
    """One sentence an operator can act on."""
    if import_status == ImportStatus.CANCELLED:
        return (
            "The import was cancelled. Nothing was written: the import is one "
            "transaction, so the rows it had applied were taken back with it."
        )
    if failed:
        return (
            "The import failed and its transaction was rolled back, so no row "
            "was written. The failure below names the reason."
        )
    if state == JobState.SUCCEEDED:
        return "The import finished. The report below is what was applied."
    if state == JobState.RUNNING:
        return (
            "The import is being applied. Its rows are written in one "
            "transaction, so none of them is visible until it finishes."
        )
    return (
        "The import is queued. A background job will apply it; the job's "
        "status is the import's status."
    )


__all__ = [
    "ImportProgressNotFound",
    "job_progress",
    "progress_key",
    "read_counts",
    "write_counts",
]
