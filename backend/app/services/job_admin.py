"""Operator actions over the background job queue (PS-10).

Implements the contract promise of `contracts/openapi/admin.yaml`
(paths `/admin/jobs*`) against the queue the product already runs
(`app/jobs/queue.py`, table `job_queue` from migration `0004_job_queue`).

The functions here are deliberately small and side-effect safe:

* read functions never commit;
* the state-transition functions mutate the row they were handed and
  never commit. The endpoint stages the audit row (``record_audit``)
  on the same session *before* calling them, so the single
  ``db.commit()`` the endpoint makes carries the state change and its
  audit entry together, atomically. (AN-06 lesson: a service that
  commits inside itself eats an audit row staged after it.)

State vocabulary
----------------
The contract's `JobStatus` enum is
``pending | running | succeeded | failed | dead | cancelled | discarded``
while the table stores ``queued`` for what the contract calls
``pending``. Everything the operator sends or reads goes through
:func:`contract_state` / :func:`stored_state`, so the API speaks the
contract vocabulary on both sides of the wire.

Retry semantics (contract, verbatim): "The attempt counter is not
reset, so the configured maximum still applies." Re-queuing a failed or
dead job therefore resets the *state* — worker, lease, error fields,
timeline — but keeps ``attempts``. A dead job that is retried runs one
more time; if it fails again it is immediately dead again, because
``fail()`` moves it to dead once ``attempts >= max_attempts``.

Discard semantics (contract, verbatim): "The record of the job is kept:
discarding removes the work, never the evidence." Discarding therefore
sets the row's state to ``discarded``; the row is never deleted. (The
queue's own ``discard_dead`` deletes dead rows — that predates the
contract and is not used here.)

Dead-letter honesty: no listing filter hides dead rows. They are always
in the default page, filtered or not.
"""
from __future__ import annotations

import json

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCategory
from app.core.tenancy import tenant_column_criterion, tenant_id_for
from app.models.job_queue import JobQueue, JobState

#: What the contract's `state` filter values mean in the stored column.
#: The contract lists pending/cancelled/discarded; the table stores
#: queued, and discarded is written by this module. `cancelled` has no
#: writer yet — filtering by it returns an honest empty page.
CONTRACT_TO_STORED: dict[str, str] = {
    "pending": JobState.QUEUED,
    "running": JobState.RUNNING,
    "succeeded": JobState.SUCCEEDED,
    "failed": JobState.FAILED,
    "dead": JobState.DEAD,
    "cancelled": "cancelled",
    "discarded": "discarded",
}

#: The state a discarded job carries.
DISCARDED_STATE = "discarded"


def contract_state(stored: str | JobState) -> str:
    """Translate a stored state into the contract's `JobStatus` value.

    Accepts the raw column value or the ``JobState`` member a session
    still holds for a freshly created row.
    """
    if isinstance(stored, JobState):
        stored = stored.value
    return "pending" if stored == JobState.QUEUED else stored


def stored_state(contract: str) -> str:
    """Translate a contract `JobStatus` value into the stored state."""
    return CONTRACT_TO_STORED.get(contract, contract)


def _state_of(job: JobQueue) -> str:
    """The row's state as a plain string.

    The column is a plain ``String(20)``, but a session that created the
    row holds a ``JobState`` enum member until it is refreshed, so both
    shapes have to normalise to the stored value.
    """
    state = job.state
    if isinstance(state, JobState):
        return state.value
    return str(state)


def parse_job_id(raw: str) -> int:
    """Turn a path parameter into a job id.

    The contract types the path value as a string; job ids are integers.
    Anything that cannot be an integer cannot be an existing job, so it
    answers the same 404 `job_not_found` an unknown integer would.
    """
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ApiError(
            "job_not_found",
            "Job not found",
            ErrorCategory.NOT_FOUND,
        )


def _lease_is_live(job: JobQueue) -> bool:
    lease = job.lease_expires_at
    if lease is None:
        return False
    if lease.tzinfo is None:
        # SQLite drops the offset on the way out (AN-06's type trap on a
        # narrower hand), and the queue always writes UTC, so give the
        # value its zone back before comparing.
        lease = lease.replace(tzinfo=timezone.utc)
    return lease > datetime.now(timezone.utc)


def _stored_object(raw: str | None) -> dict | None:
    """Decode one stored JSON object, or None when there is not one.

    Three different things read the same way here, and all three are
    honestly "nothing stored": a row written before the column existed
    (`0024`/`0025`), an empty value, and a value that is not a JSON
    object. One unreadable row must not take the listing down with it.
    """
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def serialise(
    job: JobQueue,
    *,
    include_payload: bool = False,
) -> dict:
    """Render one job row in the contract's `Job` shape.

    `updated_at` is required by the contract but the table has no such
    column; the most recent activity of the job stands in for it —
    exactly one of finished, started, created is set for any state the
    queue can reach, in the order the job lived.

    `result` is business evidence: it is what the job produced, and the
    queue stores it beside its hash (`0025_job_result_payload`), so it is
    served by every read. `payload` is different — the stored input can
    carry a confirmation token, which is an authorisation — so it is
    served only when the caller asks for it with `include_payload`.
    """
    payload: dict = {
        "id": str(job.id),
        "type": job.job_type,
        "state": contract_state(_state_of(job)),
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "created_at": job.created_at,
        "updated_at": job.finished_at or job.started_at or job.created_at,
        "started_at": job.started_at,
        "last_error_at": job.last_error_at,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "result": _stored_object(job.result_json),
    }
    if include_payload:
        payload["payload"] = _stored_object(job.input_json)
    return payload


def list_jobs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    state: str | None = None,
    job_type: str | None = None,
) -> tuple[list[JobQueue], int]:
    """A page of jobs, newest first.

    Every row is a candidate for the page, in every state: dead rows are
    never filtered out of the listing, because a dead job is never
    silently discarded.
    """
    query = db.query(JobQueue)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        query = query.filter(tenant_column_criterion(JobQueue.tenant_id, tenant_id))
    if state is not None:
        query = query.filter(JobQueue.state == stored_state(state))
    if job_type is not None:
        query = query.filter(JobQueue.job_type == job_type)

    # Newest first: what the operator wants at the top is what happened
    # last, and the id breaks ties so two rows created in the same tick
    # keep a stable order.
    total = query.count()
    rows = (
        query.order_by(JobQueue.created_at.desc(), JobQueue.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def get_job(db: Session, raw_job_id: str) -> JobQueue | None:
    """One job by its path id. ``None`` means the caller answers 404."""
    return (
        db.query(JobQueue)
        .filter(JobQueue.id == parse_job_id(raw_job_id))
        .first()
    )


def validate_retry(job: JobQueue) -> None:
    """409 for any state the contract does not let an operator retry.

    Contract: retry puts a failed or dead job back into the queue; a job
    a worker is still processing answers 409; a job a worker has taken
    over answers 409 `lease_lost`; retrying a succeeded job is a no op.
    Anything else (queued, discarded) is not a retry target and answers
    409 `invalid_state_transition`.
    """
    state = _state_of(job)
    if state == JobState.SUCCEEDED:
        return  # no op, per contract
    if state == JobState.RUNNING:
        if _lease_is_live(job):
            # Another worker holds the lease: the takeover the contract
            # names. The queue's own lease release will return the job
            # to the queue if the worker is gone.
            raise ApiError(
                "lease_lost",
                "The job is being processed by another worker",
                ErrorCategory.CONFLICT,
            )
        raise ApiError(
            "invalid_state_transition",
            "The job is still running",
            ErrorCategory.CONFLICT,
        )
    if state not in (JobState.FAILED, JobState.DEAD):
        raise ApiError(
            "invalid_state_transition",
            "Only a failed or dead job can be retried",
            ErrorCategory.CONFLICT,
        )


def is_retry_target(job: JobQueue) -> bool:
    """Whether a retried job actually re-queues.

    A succeeded job is a no op per the contract: nothing to re-queue, so
    the transition is skipped, the call still answers 202 and is still
    audited — "a no op", not "not allowed".
    """
    return _state_of(job) in (JobState.FAILED, JobState.DEAD)


def is_discard_target(job: JobQueue) -> bool:
    """Whether a discarded job still has a transition to make.

    An already-discarded job answers the discard again as a no op: the
    state is already where the operator asked it to go, so the call
    still answers 200 and is still audited, but nothing changes.
    """
    return _state_of(job) != DISCARDED_STATE


def apply_retry(job: JobQueue) -> None:
    """Re-queue a failed or dead job. No commit; see the module docstring.

    The attempt counter is NOT reset — the configured maximum still
    applies, per the contract — so the worker's next failure for this
    job counts against the budget it had left, and a dead job that fails
    again is dead again at once.
    """
    job.state = JobState.QUEUED
    job.worker_id = None
    job.lease_expires_at = None
    job.started_at = None
    job.finished_at = None
    job.error_code = None
    job.error_message = None
    job.last_error_at = None


def validate_discard(job: JobQueue) -> None:
    """409 for any state the contract does not let an operator discard.

    Contract: discard stops a job from being picked up again; a running
    job answers 409 `invalid_state_transition`. A succeeded job is
    evidence of finished work and is refused for the same reason; a
    discarded job is already stopped, and answering the discard again is
    a no op.
    """
    state = _state_of(job)
    if state in (JobState.QUEUED, JobState.FAILED, JobState.DEAD, DISCARDED_STATE):
        return
    if state == JobState.RUNNING:
        raise ApiError(
            "invalid_state_transition",
            "The job is still running",
            ErrorCategory.CONFLICT,
        )
    raise ApiError(
        "invalid_state_transition",
        "Only a job that is waiting, failed, dead or already discarded can be discarded",
        ErrorCategory.CONFLICT,
    )


def apply_discard(job: JobQueue) -> None:
    """Mark a job discarded. No commit; see the module docstring.

    The row is kept — the work is removed, never the evidence.
    """
    job.state = DISCARDED_STATE
    job.worker_id = None
    job.lease_expires_at = None
