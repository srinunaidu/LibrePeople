"""Background job queue model.

Represents a unit of asynchronous work processed by the job queue.
Each job carries an input hash and (on completion) a result hash, making
re-runs with identical input a no-op (idempotent by content).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Index, Identity, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


#: The two vocabularies below are ``str`` enums on purpose: the columns are
#: plain ``String`` so a row read back is a plain string, and a member is equal
#: to its value, which keeps every comparison and query in the queue working.
#:
#: They used to inherit ``sqlalchemy.Enum`` (imported as ``Enum`` from
#: ``sqlalchemy``), which does not create an enum at all: each member was just
#: a plain ``str``, so ``JobState.DEAD.value`` raised ``AttributeError`` and
#: ``isinstance(row.state, JobState)`` was never true. The ``enum.Enum`` import
#: is what makes the vocabulary a vocabulary.
class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD = "dead"


class JobType(str, Enum):
    CSV_IMPORT = "csv_import"
    FORECAST_RUN = "forecast_run"
    ROSTER_SOLVE = "roster_solve"
    PAYROLL_PROCESS = "payroll_process"
    DOCUMENT_RENDER = "document_render"
    WEBHOOK_DELIVER = "webhook_deliver"
    NOTIFICATION_DELIVER = "notification_deliver"
    RETENTION_RUN = "retention_run"
    ERASURE_RUN = "erasure_run"
    LEAVE_ACCRUAL = "leave_accrual"
    #: Scheduled report delivery (reporting-personalization Part F). The
    #: payload carries ``schedule_id``; the handler runs as the schedule
    #: owner and notifies explicit recipients. No new queue, no cron.
    REPORT_RUN = "report_run"


class JobQueue(Base):
    """A background job tracked through its lifecycle.

    State machine::

        queued -> running -> succeeded
        queued -> running -> failed -> (retry) -> running -> ...
        running -> failed -> dead (after max_attempts)
        failed -> dead (when no retries remain)

    A job that has already succeeded with the same input hash is a no-op
    when re-queued: the queue returns the existing succeeded job instead of
    creating a duplicate.
    """

    __tablename__ = "job_queue"
    __table_args__ = (
        Index("ix_job_queue_state_type", "state", "job_type"),
        Index("ix_job_queue_lease_expires", "lease_expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    #: What the job was asked to do, as JSON. `input_hash` identifies the
    #: request (and makes a re-run with identical input a no-op); a hash is
    #: one-way, so this column is what a worker actually executes. Nullable
    #: because rows enqueued before `0024_job_input_payload` have no payload
    #: — a worker refuses those rather than guessing.
    input_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: What the job produced, as JSON. `result_hash` identifies the result
    #: (and makes a re-run with identical input a no-op); a hash is one-way,
    #: so this column is what an operator can actually read. Nullable
    #: because jobs that completed before `0025_job_result_payload` have no
    #: stored result — it cannot be reconstructed, and the reader is told so
    #: rather than shown an empty success.
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    state: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    # Lease for worker claiming. A worker must heartbeat before this expires
    # or another worker may steal the job.
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Error information for failed/dead jobs
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Priority: lower number = higher priority
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    def is_terminal(self) -> bool:
        return self.state in (JobState.SUCCEEDED, JobState.DEAD)

    def can_retry(self) -> bool:
        return self.state == JobState.FAILED and self.attempts < self.max_attempts

    def is_lease_expired(self) -> bool:
        if self.lease_expires_at is None:
            return False
        return self.lease_expires_at < datetime.now(timezone.utc)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<JobQueue(id={self.id}, type={self.job_type}, state={self.state})>"
