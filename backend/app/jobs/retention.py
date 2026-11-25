"""The upload-retention schedule — the IM-10 defect.

``purge_expired_uploads`` exists and is proven; ``retention_run`` exists and
is proven; nothing ever enqueued it. IM-10 was not a missing purge, it was a
missing schedule. This module is the schedule.

Design rules:

* Opt-in (``RETENTION_SCHEDULE_ENABLED``) — a deployment must choose
  maintenance, not discover it, and only when the worker can execute it.
  When the worker is disabled this module stays inert.
* Enqueue-only. The retention job does the work; the schedule never runs
  the purge itself in the API process.
* At most one pending or running retention job at a time. A tick while one
  is in flight enqueues nothing — never a pile of duplicate purge jobs.
* Failures are logged and swallowed — retention is maintenance, and a
  maintenance failure must never take the API down.
"""
import logging
import threading

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.job_queue import JobQueue, JobState, JobType
from app.jobs.queue import JobQueueService

logger = logging.getLogger(__name__)

_PENDING = (JobState.QUEUED, JobState.RUNNING)


def retention_pending(db) -> bool:
    """True when a retention job is already queued or running."""
    return (
        db.query(JobQueue.id)
        .filter(
            JobQueue.job_type == JobType.RETENTION_RUN,
            JobQueue.state.in_(_PENDING),
        )
        .first()
        is not None
    )


def tick(db=None) -> str:
    """One scheduling tick — returns 'enqueued' or 'skipped-pending'."""
    close = db is None
    session = db or SessionLocal()
    try:
        if retention_pending(session):
            return "skipped-pending"
        # A fresh timestamp per tick: the queue returns the existing job
        # when the payload hash matches a succeeded one, so an identical
        # payload would make every periodic tick a no-op forever.
        from datetime import datetime, timezone

        JobQueueService(session).enqueue(
            JobType.RETENTION_RUN,
            {"reason": "retention_schedule", "run_at": datetime.now(timezone.utc).isoformat()},
        )
        return "enqueued"
    except Exception:  # noqa: BLE001 — maintenance must never take the API down
        logger.warning("retention tick failed", exc_info=True)
        return "skipped-pending" if close else "skipped-pending"
    finally:
        if close:
            session.close()


def start_retention_schedule() -> bool:
    """Start the periodic enqueues. Returns True when started."""
    if not settings.RETENTION_SCHEDULE_ENABLED:
        print(
            "[startup] RETENTION_SCHEDULE_ENABLED is disabled; uploads remain "
            "until a retention run is triggered or the setting is enabled."
        )
        return False

    interval = settings.RETENTION_RUN_INTERVAL_HOURS * 3600
    if interval <= 0:
        print("[startup] RETENTION_RUN_INTERVAL_HOURS is 0; no periodic loop.")
        return False

    tick()  # one immediately on boot (deduped while one is pending)

    def _loop() -> None:
        while True:
            import time

            time.sleep(interval)
            tick()

    threading.Thread(target=_loop, daemon=True, name="retention-schedule").start()
    print(f"[startup] upload-retention schedule enabled (every {settings.RETENTION_RUN_INTERVAL_HOURS}h).")
    return True
