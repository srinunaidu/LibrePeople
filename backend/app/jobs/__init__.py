"""Background job queue package.

Provides a database-backed job queue with leases, heartbeat, retry with
exponential backoff and jitter, maximum attempts, and a dead-letter view
for admins with retry and discard actions.

Job types: csv_import, forecast_run, roster_solve, payroll_process,
document_render, webhook_deliver, retention_run, erasure_run, leave_accrual.
"""
from __future__ import annotations

from app.models.job_queue import JobState, JobType, JobQueue

# Import handlers to trigger registration via decorators.
# Imported here (rather than in registry.py) to avoid a circular import:
# handlers.py imports register from registry.py.
from app.jobs.handlers import (  # noqa: F401
    csv_import,
    forecast_run,
    roster_solve,
    payroll_process,
    document_render,
    webhook_deliver,
    retention_run,
    erasure_run,
    leave_accrual,
)

__all__ = ["JobState", "JobType", "JobQueue"]
