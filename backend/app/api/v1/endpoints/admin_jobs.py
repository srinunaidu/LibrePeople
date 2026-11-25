"""The background-jobs monitor (PS-10).

The operator surface the contract designs in
`contracts/openapi/admin.yaml` under `/admin/jobs`: the paged listing
(dead rows never hidden), one job, the retry of a failed or dead job
and the discard of a job the deployment no longer wants to run.

Every call — the reads as well as the writes — is written to the audit
log, which is what the `admin` tag promises. The audit row is staged on
the request session *before* the state transition is applied, so the
single commit at the end carries the change and its audit entry
together (AN-06 lesson). The state-transition validation runs *before*
the audit row is staged: a refused call writes no audit entry, because
nothing happened.

Role gate: SuperAdmin and HR only (`ADMIN_ROLES`); everyone else gets
the shared 403 envelope before the handler ever runs.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.errors import ApiError, ErrorCategory
from app.models.user import User
from app.schemas.job_admin import JobOut, PaginatedJobs
from app.schemas.pagination import page_meta
from app.services import job_admin

router = APIRouter()

#: The `state` filter speaks the contract's `JobStatus` vocabulary. The
#: service translates `pending` to the stored `queued`; `discarded` is
#: written by :func:`job_admin.apply_discard`; `cancelled` has no writer
#: yet and honestly returns an empty page.
JobStateFilter = Literal[
    "pending",
    "running",
    "succeeded",
    "failed",
    "dead",
    "cancelled",
    "discarded",
]




def _job_or_404(db: Session, job_id: str):
    job = job_admin.get_job(db, job_id)
    if job is None:
        raise ApiError("job_not_found", "Job not found", ErrorCategory.NOT_FOUND)
    return job


@router.get("", response_model=PaginatedJobs, operation_id="adminListJobs")
def admin_list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    page: int = Query(1, ge=1, description="1-based page number."),
    page_size: int = Query(
        50, ge=1, le=200, description="Rows per page (at most 200)."
    ),
    state: Optional[JobStateFilter] = Query(
        None, description="Only the jobs in this state."
    ),
    type: Optional[str] = Query(None, description="Only the jobs of this type."),
    include_payload: bool = Query(
        False,
        description=(
            "Include the stored input of the job. Off by default, because "
            "the input can carry a confirmation token — an authorisation. "
            "The stored result is served by every read either way."
        ),
    ),
) -> Any:
    """List the background jobs, newest first, dead rows always visible."""
    rows, total = job_admin.list_jobs(
        db,
        page=page,
        page_size=page_size,
        state=state,
        job_type=type,
    )
    record_audit(
        db,
        current_user,
        "list_jobs",
        "JobQueue",
        None,
        details=f"page={page} page_size={page_size} state={state or 'all'} type={type or 'all'}",
    )
    db.commit()
    return {
        "items": [
            job_admin.serialise(job, include_payload=include_payload) for job in rows
        ],
        "meta": page_meta(total, page, page_size).model_dump(),
    }


@router.get("/{job_id}", response_model=JobOut, operation_id="adminGetJob")
def admin_get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    include_payload: bool = Query(False),
) -> Any:
    """Read one background job with its attempts and, when it failed, its error."""
    job = _job_or_404(db, job_id)
    record_audit(
        db,
        current_user,
        "get_job",
        "JobQueue",
        job.id,
        details=f"type={job.job_type} state={job_admin.contract_state(job.state)}",
    )
    db.commit()
    return job_admin.serialise(job, include_payload=include_payload)


@router.post("/{job_id}/retry", response_model=JobOut, status_code=202, operation_id="adminRetryJob")
def admin_retry_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Put a failed or dead job back into the queue.

    The attempt counter is not reset, so the configured maximum still
    applies. A still-running job answers 409; a succeeded job is a no op.
    """
    job = _job_or_404(db, job_id)
    from_state = job_admin.contract_state(job.state)
    job_admin.validate_retry(job)
    requeues = job_admin.is_retry_target(job)
    record_audit(
        db,
        current_user,
        "retry_job",
        "JobQueue",
        job.id,
        details=f"from_state={from_state}" + ("" if requeues else " no_op"),
    )
    if requeues:
        job_admin.apply_retry(job)
    db.commit()
    db.refresh(job)
    return job_admin.serialise(job)


@router.post("/{job_id}/discard", response_model=JobOut, operation_id="adminDiscardJob")
def admin_discard_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    reason: Optional[str] = Query(
        None,
        max_length=500,
        description="Why the job is discarded. Stored on the audit log.",
    ),
) -> Any:
    """Discard a job so it is not picked up again.

    The record of the job is kept: discarding removes the work, never
    the evidence. The reason, when given, is written to the audit log.
    """
    job = _job_or_404(db, job_id)
    from_state = job_admin.contract_state(job.state)
    job_admin.validate_discard(job)
    discards = job_admin.is_discard_target(job)
    record_audit(
        db,
        current_user,
        "discard_job",
        "JobQueue",
        job.id,
        details=f"from_state={from_state}"
        + (f" reason={reason}" if reason else "")
        + ("" if discards else " no_op"),
    )
    if discards:
        job_admin.apply_discard(job)
    db.commit()
    db.refresh(job)
    return job_admin.serialise(job)
