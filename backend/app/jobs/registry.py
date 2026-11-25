"""Job type registry and handler registration.

Job types are registered here with their handler callables. A handler
receives a :class:`JobQueue` instance and a dict of input parameters (the
payload stored on the job as JSON, beside its hash) and returns a result
dict. Handlers should raise exceptions on failure so the queue can mark the
job as failed; a handler that cannot do the work raises
:class:`~app.jobs.errors.JobNotImplemented` so the job is dead-lettered
rather than retried.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

from app.models.job_queue import JobQueue, JobType

#: Registry mapping JobType -> handler callable
#: Handler signature: (job: JobQueue, input_data: dict) -> dict
HANDLER_REGISTRY: Dict[JobType, Callable] = {}


def register(job_type: JobType):
    """Decorator to register a job handler for a job type."""

    def decorator(func: Callable) -> Callable:
        HANDLER_REGISTRY[job_type] = func
        return func

    return decorator


def get_handler(job_type: JobType) -> Optional[Callable]:
    """Get the handler for a job type, or None if not registered."""
    return HANDLER_REGISTRY.get(job_type)


def is_registered(job_type: JobType) -> bool:
    """Check if a job type has a registered handler."""
    return job_type in HANDLER_REGISTRY


# Import handlers to trigger registration via decorators
# These are imported here so their @register decorators run at import time.
# NOTE: Imported from app/jobs/__init__.py to avoid circular import with
# app/jobs/handlers.py (which imports register from here).
