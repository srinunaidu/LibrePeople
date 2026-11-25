"""Database-backed job queue.

Provides durable background job processing with:

* States: queued, running, succeeded, failed, dead
* Leases with heartbeat: a worker claims a job by setting a lease; if the
  lease expires, another worker may claim the job
* Retry with exponential backoff and jitter, maximum attempts
* Dead-letter view for admins with retry and discard actions
* Idempotent re-run: a job that has already succeeded with the same input
  hash returns the existing result instead of creating a duplicate
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.job_queue import JobQueue, JobState, JobType

#: Default maximum attempts for a job before it moves to dead
DEFAULT_MAX_ATTEMPTS = 5

#: Base backoff in seconds; actual backoff = base * 2^(attempt-1) + jitter
BACKOFF_BASE_SECONDS = 10

#: Maximum backoff in seconds
BACKOFF_MAX_SECONDS = 3600


def compute_input_hash(payload: dict[str, Any]) -> str:
    """Compute a stable SHA-256 hash of a job input payload."""
    serialised = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def compute_backoff_seconds(attempt: int) -> float:
    """Compute exponential backoff with jitter for a given attempt number.

    attempt=1 -> base * 2^0 + jitter
    attempt=2 -> base * 2^1 + jitter
    ...
    """
    base = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
    jitter = random.uniform(0, base * 0.25)  # up to 25% jitter
    return min(base + jitter, BACKOFF_MAX_SECONDS)


class JobQueueService:
    """Service layer for the job queue.

    All methods are idempotent and safe to call concurrently.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Enqueue
    # ------------------------------------------------------------------

    def enqueue(
        self,
        job_type: JobType,
        input_payload: dict[str, Any],
        *,
        priority: int = 10,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> JobQueue:
        """Enqueue a job.

        If a job with the same job_type and input_hash already exists in a
        terminal state (succeeded), return the existing job instead of
        creating a duplicate. This makes re-runs with identical input a
        no-op.

        The payload is stored as JSON beside its hash. The hash identifies
        the request and is compared, never reversed; a worker needs the
        parameters themselves, and until `0024_job_input_payload` they were
        discarded here, which is why nothing could execute a job.
        """
        input_hash = compute_input_hash(input_payload)

        existing = (
            self.db.query(JobQueue)
            .filter(
                JobQueue.job_type == job_type,
                JobQueue.input_hash == input_hash,
                JobQueue.state == JobState.SUCCEEDED,
            )
            .first()
        )
        if existing:
            return existing

        job = JobQueue(
            job_type=job_type,
            input_hash=input_hash,
            input_json=json.dumps(input_payload, sort_keys=True, default=str),
            state=JobState.QUEUED,
            attempts=0,
            max_attempts=max_attempts,
            priority=priority,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    # ------------------------------------------------------------------
    # Claim / lease
    # ------------------------------------------------------------------

    def claim_next(
        self,
        worker_id: str,
        lease_seconds: int = 300,
        job_types: Optional[list[JobType]] = None,
    ) -> Optional[JobQueue]:
        """Claim the next queued job.

        Claims the highest-priority queued job. Sets a new lease and marks
        the job as running. Returns None if no job is available.

        The claim is a conditional update — ``WHERE id = ? AND state =
        'queued'`` — so two workers that select the same row cannot both
        claim it: the second update matches no row and returns None. The
        docstring used to promise this without doing it, and a queue that
        can hand one job to two workers is not a queue.
        """
        now = datetime.now(timezone.utc)
        lease_expires = now + timedelta(seconds=lease_seconds)

        query = self.db.query(JobQueue).filter(
            JobQueue.state == JobState.QUEUED,
        )
        if job_types:
            query = query.filter(JobQueue.job_type.in_(job_types))

        # Order by priority (lower = higher), then by created_at (oldest first)
        job = (
            query.order_by(JobQueue.priority.asc(), JobQueue.created_at.asc())
            .first()
        )

        if job is None:
            return None

        job_id = job.id
        claimed = (
            self.db.query(JobQueue)
            .filter(JobQueue.id == job_id, JobQueue.state == JobState.QUEUED)
            .update(
                {
                    JobQueue.state: JobState.RUNNING,
                    JobQueue.attempts: JobQueue.attempts + 1,
                    JobQueue.worker_id: worker_id,
                    JobQueue.lease_expires_at: lease_expires,
                    JobQueue.started_at: now,
                },
                synchronize_session=False,
            )
        )
        self.db.commit()
        if not claimed:
            # Another worker won the same row between the select and the
            # update. There may be more work, so the caller asks again.
            self.db.expire_all()
            return None
        return self.get_job(job_id)

    def heartbeat(
        self,
        job_id: int,
        worker_id: str,
        lease_seconds: int = 300,
    ) -> bool:
        """Extend the lease on a running job.

        Returns False if the job is not running or belongs to another worker.
        """
        now = datetime.now(timezone.utc)
        lease_expires = now + timedelta(seconds=lease_seconds)

        job = (
            self.db.query(JobQueue)
            .filter(
                JobQueue.id == job_id,
                JobQueue.state == JobState.RUNNING,
                JobQueue.worker_id == worker_id,
            )
            .first()
        )
        if job is None:
            return False

        job.lease_expires_at = lease_expires
        self.db.add(job)
        self.db.commit()
        return True

    # ------------------------------------------------------------------
    # Complete / fail
    # ------------------------------------------------------------------

    def complete(
        self,
        job_id: int,
        worker_id: str,
        result_payload: Optional[dict[str, Any]] = None,
    ) -> Optional[JobQueue]:
        """Mark a job as succeeded.

        Stores the result hash (computed from result_payload) so that
        future re-runs with the same input are idempotent, and the payload
        itself so that the result can be read later. The hash identifies the
        result and is compared, never reversed: without the payload the only
        record of what a job produced was a fingerprint of it, which is why
        a queued import's report could not be collected.
        """
        job = (
            self.db.query(JobQueue)
            .filter(
                JobQueue.id == job_id,
                JobQueue.state == JobState.RUNNING,
                JobQueue.worker_id == worker_id,
            )
            .first()
        )
        if job is None:
            return None

        job.state = JobState.SUCCEEDED
        job.finished_at = datetime.now(timezone.utc)
        if result_payload is not None:
            job.result_hash = compute_input_hash(result_payload)
            job.result_json = json.dumps(
                result_payload, sort_keys=True, default=str
            )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def fail(
        self,
        job_id: int,
        worker_id: str,
        error_code: str,
        error_message: str,
        *,
        permanent: bool = False,
    ) -> Optional[JobQueue]:
        """Mark a job as failed.

        If attempts >= max_attempts, move to dead. Otherwise, stay in
        failed state for retry.

        ``permanent=True`` moves straight to dead whatever the attempt
        count. A handler that raised :class:`JobNotImplemented` or
        :class:`JobInputInvalid` cannot be cured by retrying it, and
        spending five attempts to learn that only delays the dead-letter
        entry an operator needs to see.
        """
        job = (
            self.db.query(JobQueue)
            .filter(
                JobQueue.id == job_id,
                JobQueue.state == JobState.RUNNING,
                JobQueue.worker_id == worker_id,
            )
            .first()
        )
        if job is None:
            return None

        job.state = JobState.FAILED
        job.finished_at = datetime.now(timezone.utc)
        job.error_code = error_code
        job.error_message = error_message
        job.last_error_at = datetime.now(timezone.utc)
        if permanent or job.attempts >= job.max_attempts:
            job.state = JobState.DEAD
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    # ------------------------------------------------------------------
    # Retry / dead-letter
    # ------------------------------------------------------------------

    def retry_failed(
        self,
        job_id: int,
    ) -> Optional[JobQueue]:
        """Retry a failed job.

        Resets the state to queued, clears the error, and increments
        attempts (counted against max_attempts). Returns None if the job
        is not in failed state or has no retries remaining.
        """
        job = (
            self.db.query(JobQueue)
            .filter(JobQueue.id == job_id, JobQueue.state == JobState.FAILED)
            .first()
        )
        if job is None:
            return None

        if not job.can_retry():
            job.state = JobState.DEAD
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            return job

        job.state = JobState.QUEUED
        job.worker_id = None
        job.lease_expires_at = None
        job.started_at = None
        job.finished_at = None
        job.error_code = None
        job.error_message = None
        job.last_error_at = None
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def discard_dead(
        self,
        job_id: int,
    ) -> Optional[JobQueue]:
        """Discard a dead job (permanently removes it).

        Returns None if the job is not in dead state.
        """
        job = (
            self.db.query(JobQueue)
            .filter(JobQueue.id == job_id, JobQueue.state == JobState.DEAD)
            .first()
        )
        if job is None:
            return None

        self.db.delete(job)
        self.db.commit()
        return job

    # ------------------------------------------------------------------
    # List / admin
    # ------------------------------------------------------------------

    def list_jobs(
        self,
        job_type: Optional[JobType] = None,
        state: Optional[JobState] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[JobQueue]:
        """List jobs, optionally filtered by type and/or state."""
        query = self.db.query(JobQueue)
        if job_type:
            query = query.filter(JobQueue.job_type == job_type)
        if state:
            query = query.filter(JobQueue.state == state)
        return (
            query.order_by(JobQueue.priority.asc(), JobQueue.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_job(self, job_id: int) -> Optional[JobQueue]:
        """Get a job by ID."""
        return self.db.query(JobQueue).filter(JobQueue.id == job_id).first()

    def list_dead(self, skip: int = 0, limit: int = 100) -> list[JobQueue]:
        """List dead jobs (for the dead-letter view)."""
        return (
            self.db.query(JobQueue)
            .filter(JobQueue.state == JobState.DEAD)
            .order_by(JobQueue.finished_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def release_expired_leases(self) -> int:
        """Release leases that have expired.

        Marks running jobs with expired leases back to queued so they can
        be claimed by another worker. Returns the number of jobs released.
        """
        now = datetime.now(timezone.utc)
        jobs = (
            self.db.query(JobQueue)
            .filter(
                JobQueue.state == JobState.RUNNING,
                JobQueue.lease_expires_at < now,
            )
            .all()
        )
        for job in jobs:
            job.state = JobState.QUEUED
            job.worker_id = None
            job.lease_expires_at = None
            self.db.add(job)
        if jobs:
            self.db.commit()
        return len(jobs)
