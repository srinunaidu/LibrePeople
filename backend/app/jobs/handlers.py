"""Job handlers.

The handlers are registered in the job type registry so the queue can
process them. A handler receives a :class:`JobQueue` instance and a dict of
input parameters, and returns a result dict. A handler raises on failure,
so the queue marks the job failed and retries it.

The ``csv_import`` handler does the real work: it applies the import the
operator previewed, in one transaction, and reports what happened.
``roster_solve`` runs the solver, and ``retention_run`` purges uploads whose
retention period has passed. The remaining handlers have no work behind them
yet, and they **refuse** with :class:`~app.jobs.errors.JobNotImplemented`
rather than returning a success result. A handler that reports work it did
not do is a defect, not a stub: the queue would record the job as succeeded
and the dead-letter view — the one place an operator looks for work that did
not happen — would stay empty.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from app.jobs.errors import JobCancelled, JobInputInvalid, JobNotImplemented
from app.jobs.registry import register
from app.models.job_queue import JobQueue, JobState, JobType


@register(JobType.CSV_IMPORT)
def csv_import(job: JobQueue, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a CSV import in the background.

    The input carries the entity to import and the confirmation token of
    the dry run the operator previewed. The job applies that very import:
    one record, one status, and the job's state is the import's state.

    What the job does:

    * it applies the import in **one transaction**, so the file is applied
      entirely or not at all;
    * it reports its **progress** after every batch, so an operator can
      see how far a long import has got;
    * it **stops** when the import is cancelled or when the job loses its
      lease, and the transaction is rolled back with it;
    * it returns the **same report the dry run produced**, plus what was
      actually applied, and every row that failed is named in it.

    The handler raises when it cannot do the work — a missing token, an
    entity that does not exist, an import that was cancelled. A job that
    cannot be done must fail, so that the queue retries it and the
    dead-letter view shows it, rather than reporting a success that did
    not happen.
    """
    from app.core.database import SessionLocal
    from app.imports import runner
    from app.imports.runner import ImportCancelled
    from app.imports.spec import get_spec
    from app.models.imports import ImportStatus
    from app.models.user import User
    from app.storage import get_storage

    entity = input_data.get("entity")
    token = input_data.get("confirmation_token") or input_data.get("token")
    storage_key = input_data.get("storage_key") or input_data.get("file")
    user_id = input_data.get("user_id")

    if not entity:
        raise ValueError("a csv import needs an 'entity'")
    if get_spec(entity) is None:
        raise ValueError(f"unknown entity: {entity}")
    if not token and not storage_key:
        raise ValueError(
            "a csv import needs a 'confirmation_token' or a 'storage_key'"
        )

    db = SessionLocal()
    try:
        actor = None
        if user_id is not None:
            actor = db.query(User).filter(User.id == user_id).first()

        try:
            if token:
                outcome = _commit_token(
                    db,
                    job,
                    entity,
                    token,
                    user_id=user_id,
                    actor=actor,
                )
            else:
                outcome = _commit_storage_key(
                    db,
                    job,
                    entity,
                    storage_key,
                    user_id=user_id,
                    actor=actor,
                    file_name=input_data.get("file_name"),
                )
        except ImportCancelled as exc:
            # A cancelled import is a decision, and the token refuses every
            # later attempt: a retry cannot succeed. Refusing it permanently
            # puts it in the dead-letter view, which is where an operator
            # looks for work that did not happen.
            raise JobCancelled(str(exc)) from None

        report = outcome.result.summary()
        report.update(
            {
                "committed": True,
                "created": outcome.applied.created,
                "updated": outcome.applied.updated,
                "unchanged": outcome.applied.unchanged,
                "failed": len(outcome.applied.errors),
                "rows": runner.row_report(outcome.result, outcome.applied),
                "job_id": job.id,
                "state": JobState.SUCCEEDED,
            }
        )
        _write_progress(job, entity, outcome, state=JobState.SUCCEEDED)
        return report
    finally:
        db.close()


def _commit_token(db, job, entity, token, *, user_id, actor):
    """Apply the import a confirmation token refers to."""
    from app.imports import runner

    def cancel_check() -> bool:
        return _stop_requested(job, token)

    def progress(rows_done: int, rows_total: int) -> None:
        _write_progress_counts(job, entity, rows_done, rows_total)

    return runner.commit(
        db,
        entity,
        token,
        user_id=user_id,
        actor=actor,
        cancel_check=cancel_check,
        progress=progress,
    )


def _commit_storage_key(db, job, entity, storage_key, *, user_id, actor, file_name):
    """Apply a file that is in object storage but was never previewed.

    The file is validated and applied in one go: a dry run first, so that
    the operator's rule — nothing is written that was not previewed — is
    kept even when there is no operator to preview it.
    """
    from app.imports import runner
    from app.storage import get_storage

    storage = get_storage()
    data = storage.read(storage_key)

    preview = runner.dry_run(
        db,
        entity,
        data,
        file_name=file_name,
        user_id=user_id,
        actor=actor,
    )

    def cancel_check() -> bool:
        return _stop_requested(job, preview.token)

    def progress(rows_done: int, rows_total: int) -> None:
        _write_progress_counts(job, entity, rows_done, rows_total)

    return runner.commit(
        db,
        entity,
        preview.token,
        user_id=user_id,
        actor=actor,
        cancel_check=cancel_check,
        progress=progress,
    )


def _stop_requested(job: JobQueue, token: str | None) -> bool:
    """Whether the import should stop where it is.

    Two things can stop it. The operator may have cancelled the import,
    and the job may have lost its lease — another worker may have taken
    it, and two workers must not apply the same file.

    The state is read through a **separate session**, so that what another
    worker or another request has committed is seen. The session that is
    applying the import is inside its own transaction and would otherwise
    read its own snapshot.
    """
    from app.core.database import SessionLocal
    from app.models.imports import ImportDryRun, ImportStatus
    from app.models.job_queue import JobQueue as JobRow

    other = SessionLocal()
    try:
        if token:
            record = (
                other.query(ImportDryRun)
                .filter(ImportDryRun.token == token)
                .first()
            )
            if record is not None and record.status == ImportStatus.CANCELLED:
                return True
        row = other.query(JobRow).filter(JobRow.id == job.id).first()
        if row is None:
            return True
        if row.state != JobState.RUNNING:
            return True
        if row.lease_expires_at is not None:
            expires = row.lease_expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                return True
        return False
    finally:
        other.close()


def _write_progress_counts(job: JobQueue, entity: str, done: int, total: int) -> None:
    """Record how far the import has got.

    The write itself lives in :mod:`app.imports.progress`, which also owns
    the key and the read: the progress endpoint has to read exactly what the
    handler wrote, and two copies of a storage key are two things to keep in
    step. The progress is a report, not a promise, so a storage outage there
    is swallowed and the reader falls back to the job's own state.
    """
    from app.imports.progress import write_counts

    write_counts(job.id, entity, done, total)


def _write_progress(job: JobQueue, entity: str, outcome, state: str) -> None:
    """Record the end of the import."""
    _write_progress_counts(
        job,
        entity,
        outcome.applied.created + outcome.applied.updated + outcome.applied.unchanged,
        outcome.result.total_rows,
    )


@register(JobType.FORECAST_RUN)
def forecast_run(job: JobQueue, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Refuse: a forecast is computed and stored in the request.

    ``POST /forecasting/runs`` runs the engine and writes the
    ``ForecastRun`` and its result rows before it answers. There is no
    background forecast to run and nothing enqueues this type, so the
    honest answer is that the job is not implemented — not a success
    result with a null accuracy.
    """
    raise JobNotImplemented(
        "forecast_run is not implemented as a background job: "
        "POST /forecasting/runs computes the forecast and stores the run "
        "in the request"
    )


@register(JobType.ROSTER_SOLVE)
def roster_solve(job: JobQueue, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run the roster solver in the background."""
    from app.services.solver import RosterSolver
    problem = input_data.get("problem") or input_data
    solver = RosterSolver(time_limit_seconds=input_data.get("time_limit_seconds", 60))
    result = solver.solve(problem)
    return {
        "status": result.get("status", "FEASIBLE"),
        "solver_status": result.get("status"),
        "objective_value": result.get("objective_value"),
        "weight_breakdown": result.get("weight_breakdown"),
        "unfilled": result.get("unfilled_slots", []),
        "assignments": len(result.get("assignments", [])),
        "job_id": job.id,
    }


@register(JobType.PAYROLL_PROCESS)
def payroll_process(job: JobQueue, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Refuse: a pay run is calculated, not queued.

    ``POST /payroll/runs/{id}/process`` calculates the run inside the
    request against a verified rule pack, and refuses with
    ``rule_pack_not_verified`` when there is none. A background handler
    that returned ``payslips: 0`` would tell an operator a payroll had run
    when no money had been calculated at all.
    """
    raise JobNotImplemented(
        "payroll_process is not implemented: pay runs are calculated by "
        "POST /payroll/runs/{id}/process against a verified rule pack"
    )


@register(JobType.DOCUMENT_RENDER)
def document_render(job: JobQueue, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Refuse: no document template or renderer exists in the product."""
    raise JobNotImplemented(
        "document_render is not implemented: the product has no document "
        "template or renderer to call"
    )


@register(JobType.WEBHOOK_DELIVER)
def webhook_deliver(job: JobQueue, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Refuse: no webhook subscription or delivery path exists."""
    raise JobNotImplemented(
        "webhook_deliver is not implemented: the product has no webhook "
        "subscription or delivery path"
    )


@register(JobType.NOTIFICATION_DELIVER)
def notification_deliver(job: JobQueue, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Deliver one notification row (LP-NOT-003 + LP-NOT-002 provider).

    The payload carries only ``notification_id``. Delivery is a local
    state change plus, when the recipient still has the email channel
    on, one send through the configured email provider
    (:mod:`app.services.email_provider`: ``log`` by default, ``smtp``
    when ``EMAIL_PROVIDER=smtp``). There is no SMS/push provider behind
    this — that is a later slice, not this one.

    The handler is idempotent: a row that already reads ``sent`` is
    reported as delivered without touching it, so a retried emission or
    a re-queued job never double-delivers. ``email_sent`` is set only
    when the provider returns; a provider failure propagates so the row
    is marked ``failed`` (or ``dead`` on the last attempt) and the queue
    retries with backoff.

    Failures split the way the queue splits them. A payload without a
    usable id, or an id with no row behind it, raises
    :class:`~app.jobs.errors.JobInputInvalid`: retrying cannot grow the
    row back, so the worker dead-letters it at once. Anything raised
    while recording delivery is transient: the row is marked ``failed``
    (or ``dead`` when this was the last attempt the job allows) and the
    error is re-raised, so the queue retries with backoff and the job
    itself goes dead after its attempts are spent (five by default).
    """
    from app.core.database import SessionLocal
    from app.jobs.errors import JobInputInvalid
    from app.models.ess_hr import Notification

    notification_id = input_data.get("notification_id")
    if isinstance(notification_id, bool) or not isinstance(notification_id, int):
        raise JobInputInvalid(
            "a notification delivery needs an integer 'notification_id', "
            f"got {notification_id!r}"
        )

    db = SessionLocal()
    try:
        row = (
            db.query(Notification)
            .filter(Notification.id == notification_id)
            .first()
        )
        if row is None:
            raise JobInputInvalid(
                f"notification {notification_id} does not exist; "
                "it cannot be delivered, enqueue it again after it exists"
            )
        if row.delivery_status == "sent":
            return {
                "notification_id": notification_id,
                "delivery": "already_sent",
                "delivery_status": "sent",
                "job_id": job.id,
            }
        row.delivery_status = "sending"
        row.delivery_attempts = (row.delivery_attempts or 0) + 1
        db.add(row)
        db.commit()
        try:
            channels = _deliver_channels(db, row)
        except Exception as exc:  # noqa: BLE001
            row.delivery_error = f"{type(exc).__name__}: {exc}"[:1000]
            if job.attempts >= job.max_attempts:
                row.delivery_status = "dead"
            else:
                row.delivery_status = "failed"
            db.add(row)
            db.commit()
            raise
        row.delivery_status = "sent"
        row.delivery_error = None
        db.add(row)
        db.commit()
        return {
            "notification_id": notification_id,
            "delivery": "sent",
            "delivery_status": "sent",
            "delivery_attempts": row.delivery_attempts,
            "channels": channels,
            "job_id": job.id,
        }
    finally:
        db.close()


def _deliver_channels(db, notification) -> Dict[str, bool]:
    """Deliver across the recipient's enabled channels (LP-NOT-002).

    The in-app row *is* the delivery; email goes through the configured
    provider only when the recipient still has the email channel on.
    ``email_sent`` is set only after the provider returns, so a failed
    send leaves it ``False`` and the failure propagates to the retry
    path. SMS and push have no sender yet, so they are reported, not
    sent. Kept as a separate function so the retry path in tests can
    force the transient failure without touching the row bookkeeping.
    """
    from app.services import notifications as notify

    prefs = notify.recipient_preferences(db, notification.recipient_id)
    email_pref = bool(prefs.get("email"))
    email = False
    if email_pref:
        from app.models.user import User

        from app.services.email_provider import get_provider

        user = db.query(User).filter(User.id == notification.recipient_id).first()
        to_addr = (user.email if user is not None else "") or ""
        if to_addr:
            get_provider().send(to_addr, notification.title, notification.message)
            notification.email_sent = True
            db.add(notification)
            db.commit()
            email = True
    return {
        "in_app": True,
        "email": email,
        "sms": bool(prefs.get("sms")),
        "push": bool(prefs.get("push")),
    }


@register(JobType.RETENTION_RUN)
def retention_run(job: JobQueue, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Purge uploads whose retention period has passed.

    This is the one handler behind a placeholder that could be made real
    without inventing a product decision: ``purge_expired_uploads`` is the
    product's existing retention path, and a retention run is exactly a
    call to it. The count it returns is what was deleted, not a constant.
    """
    from app.core.database import SessionLocal
    from app.retention.uploads import purge_expired_uploads

    db = SessionLocal()
    try:
        deleted = purge_expired_uploads(db)
    finally:
        db.close()
    return {
        "status": "retention_complete",
        "records_affected": deleted,
        "job_id": job.id,
    }


@register(JobType.ERASURE_RUN)
def erasure_run(job: JobQueue, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Refuse: erasure, retention schedules and legal hold are not built.

    The request that owns this work is ``HR-12``. Reporting
    ``records_anonymised: 0`` would be indistinguishable from a successful
    erasure of nothing, which is the one answer a data subject must never
    be given.
    """
    raise JobNotImplemented(
        "erasure_run is not implemented: erasure, retention schedules and "
        "legal hold are not built (HR-12)"
    )


@register(JobType.LEAVE_ACCRUAL)
def leave_accrual(job: JobQueue, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Post one month's leave accrual (and January carry-over).

    The input carries ``year`` and ``month``, optionally ``leave_type_id``
    to accrue a single type, and ``created_by`` for the ledger rows. The
    math lives in :mod:`app.services.leave_accrual` — this handler only
    opens the session, commits the staged rows, and reports the counts —
    so the endpoint path and the queue path cannot disagree about what an
    accrual is. A bad payload raises
    :class:`~app.jobs.errors.JobInputInvalid` (retrying cannot fix it),
    anything else propagates so the queue retries with backoff.
    """
    from app.core.database import SessionLocal
    from app.services import leave_accrual as accrual

    year = input_data.get("year")
    month = input_data.get("month")
    if (
        isinstance(year, bool)
        or isinstance(month, bool)
        or not isinstance(year, int)
        or not isinstance(month, int)
        or not 1 <= month <= 12
    ):
        raise JobInputInvalid(
            "a leave accrual needs an integer 'year' and a 'month' "
            f"between 1 and 12, got year={year!r} month={month!r}"
        )
    leave_type_id = input_data.get("leave_type_id")
    if leave_type_id is not None and (
        isinstance(leave_type_id, bool) or not isinstance(leave_type_id, int)
    ):
        raise JobInputInvalid(
            "a leave accrual's 'leave_type_id' must be an integer, "
            f"got {leave_type_id!r}"
        )

    db = SessionLocal()
    try:
        try:
            report = accrual.run_accrual(
                db,
                year,
                month,
                leave_type_id=leave_type_id,
                created_by=input_data.get("created_by"),
            )
        except ValueError as exc:
            raise JobInputInvalid(str(exc)) from None
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    report.update({"job_id": job.id, "state": JobState.SUCCEEDED})
    return report
