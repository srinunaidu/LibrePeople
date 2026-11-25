"""The background job worker.

Why this exists
---------------
The queue was durable from the day it was written: `enqueue`, `claim_next`,
`heartbeat`, `complete`, `fail` and `release_expired_leases` were all there,
with a suite proving each of them. Nothing called `claim_next`, and nothing
called a handler outside a test. A large import was accepted with `202` —
"queued for a background job" — and then never applied, because no process
ever picked the job up.

That is the worst shape a missing feature can take: the product told the
operator the work was accepted, and the only thing missing was the thing that
would do it.

What a pass does
----------------
1. Release leases that have expired. A worker that died mid-job left its row
   ``running``; the lease is the proof it is gone, and the job returns to the
   queue for the next worker.
2. Claim one job with a conditional update, so two workers cannot both take
   it.
3. Decode the payload the job was enqueued with. A job queued before
   `0024_job_input_payload` has no payload and is dead-lettered rather than
   guessed at.
4. Find the handler. A type with no handler is dead-lettered.
5. Heartbeat the lease while the handler runs, so a long import is not
   stolen from under the worker applying it.
6. Complete or fail. A deliberate, permanent refusal
   (:class:`~app.jobs.errors.JobNotImplemented`,
   :class:`~app.jobs.errors.JobInputInvalid`) goes straight to ``dead``;
   anything else is retried with backoff until its attempts are spent.

The worker runs in the web process, off by default (`JOB_WORKER_ENABLED`).
One instance is the deployment model, so one worker is enough; the conditional
claim means a second one would be safe but would not add throughput.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import threading
import uuid
from typing import Any, Optional

from app.core.database import SessionLocal
from app.jobs.errors import JobCancelled, JobInputInvalid, JobNotImplemented
from app.jobs.queue import JobQueueService
from app.jobs.registry import get_handler
from app.models.job_queue import JobQueue, JobType

# Importing the handlers populates the registry through their decorators.
import app.jobs.handlers  # noqa: F401,E402

log = logging.getLogger("karmathy.jobs.worker")

#: The longest error message stored on a job. The column is Text, but an
#: operator reads this in a table; a stack trace pasted into it helps nobody.
MAX_ERROR_MESSAGE = 2000


def decode_input(job: JobQueue) -> dict[str, Any]:
    """Return the payload the job was enqueued with.

    Raises :class:`JobInputInvalid` when there is nothing usable to execute.
    A hash is one-way: a job queued before the payload was stored cannot be
    reconstructed, and inventing parameters would be worse than refusing.
    """
    if not job.input_json:
        raise JobInputInvalid(
            f"job {job.id} was queued before its payload was stored and cannot "
            "be executed; enqueue it again"
        )
    try:
        payload = json.loads(job.input_json)
    except (TypeError, ValueError) as exc:
        raise JobInputInvalid(
            f"job {job.id} has a payload that is not valid JSON: {exc}"
        ) from None
    if not isinstance(payload, dict):
        raise JobInputInvalid(
            f"job {job.id} has a payload that is not an object "
            f"({type(payload).__name__})"
        )
    return payload


class JobWorker:
    """Claims and executes queued jobs until it is told to stop."""

    def __init__(
        self,
        *,
        poll_seconds: float = 2.0,
        lease_seconds: int = 300,
        worker_id: Optional[str] = None,
    ) -> None:
        self.worker_id = worker_id or (
            f"{socket.gethostname()[:40]}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        )
        self.poll_seconds = max(0.05, float(poll_seconds))
        self.lease_seconds = max(1, int(lease_seconds))
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> threading.Thread:
        """Start the worker on a daemon thread. Returns the thread."""
        if self._thread is not None and self._thread.is_alive():
            return self._thread
        self._stop.clear()
        self._thread = threading.Thread(
            target=self.run_forever,
            name="karmathy-job-worker",
            daemon=True,
        )
        self._thread.start()
        return self._thread

    def stop(self, timeout: float = 15.0) -> bool:
        """Ask the worker to stop and wait for the job in flight to finish.

        Returns True when the thread has stopped. The current job is allowed
        to finish: interrupting a handler half-way through an import would
        leave the transaction to be rolled back by the connection closing,
        which is a worse outcome than waiting for it.
        """
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
            return not thread.is_alive()
        return True

    def run_forever(self) -> None:
        """The loop. Never raises out of the thread."""
        self._release_expired()
        while not self._stop.is_set():
            try:
                worked = self.run_once()
            except Exception:  # noqa: BLE001
                # A database that is briefly unreachable, or a schema that is
                # still migrating, must not kill the worker: the queue is
                # durable, and the next pass will find the job again.
                log.exception("job worker pass failed")
                worked = False
            if not worked:
                self._stop.wait(self.poll_seconds)

    # ------------------------------------------------------------------
    # One pass
    # ------------------------------------------------------------------

    def run_once(self) -> bool:
        """Claim and process at most one job. True if a job was processed."""
        db = SessionLocal()
        try:
            service = JobQueueService(db)
            released = service.release_expired_leases()
            if released:
                log.warning("released %s expired job lease(s)", released)
            job = service.claim_next(
                self.worker_id, lease_seconds=self.lease_seconds
            )
            if job is None:
                return False
            # The handler runs outside this session. Detaching keeps the row
            # readable and closes the read transaction, so a handler that
            # writes cannot deadlock against the worker's own connection.
            db.expunge(job)
        finally:
            db.close()

        self._execute(job)
        return True

    def _release_expired(self) -> None:
        db = SessionLocal()
        try:
            released = JobQueueService(db).release_expired_leases()
            if released:
                log.warning("released %s expired job lease(s) at start", released)
        except Exception:  # noqa: BLE001
            log.exception("could not release expired job leases")
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def _execute(self, job: JobQueue) -> None:
        job_id = job.id
        job_type = str(job.job_type)

        try:
            handler = get_handler(JobType(job_type))
        except ValueError:
            handler = None
        if handler is None:
            self._fail(
                job_id,
                "job_type_not_registered",
                f"no handler is registered for job type {job_type!r}",
                permanent=True,
            )
            return

        try:
            payload = decode_input(job)
        except JobInputInvalid as exc:
            self._fail(job_id, "job_input_invalid", str(exc), permanent=True)
            return

        stop_heartbeat = threading.Event()
        beat = threading.Thread(
            target=self._heartbeat,
            args=(job_id, stop_heartbeat),
            name=f"karmathy-job-heartbeat-{job_id}",
            daemon=True,
        )
        beat.start()
        try:
            result = handler(job, payload)
        except JobNotImplemented as exc:
            self._fail(
                job_id, "job_not_implemented", str(exc), permanent=True
            )
        except JobInputInvalid as exc:
            self._fail(job_id, "job_input_invalid", str(exc), permanent=True)
        except JobCancelled as exc:
            # A cancellation is a decision, not a fault: it cannot be cured
            # by running the work again.
            self._fail(job_id, "job_cancelled", str(exc), permanent=True)
        except Exception as exc:  # noqa: BLE001
            log.exception("job %s (%s) failed", job_id, job_type)
            self._fail(
                job_id,
                "job_failed",
                f"{type(exc).__name__}: {exc}",
                permanent=False,
            )
        else:
            self._complete(job_id, result)
        finally:
            stop_heartbeat.set()
            beat.join(timeout=1.0)

    def _heartbeat(self, job_id: int, stop: threading.Event) -> None:
        """Extend the lease until the job is finished or the lease is lost."""
        interval = max(1.0, self.lease_seconds / 3.0)
        db = SessionLocal()
        try:
            service = JobQueueService(db)
            while not stop.wait(interval):
                if not service.heartbeat(
                    job_id, self.worker_id, lease_seconds=self.lease_seconds
                ):
                    log.warning(
                        "job %s is no longer leased to %s; stopping its heartbeat",
                        job_id,
                        self.worker_id,
                    )
                    return
        except Exception:  # noqa: BLE001
            log.exception("heartbeat for job %s failed", job_id)
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Record the outcome
    # ------------------------------------------------------------------

    def _complete(self, job_id: int, result: Any) -> None:
        db = SessionLocal()
        try:
            payload = result if isinstance(result, dict) else None
            job = JobQueueService(db).complete(
                job_id, self.worker_id, payload
            )
            if job is None:
                log.warning(
                    "job %s finished but its lease had already been lost", job_id
                )
        except Exception:  # noqa: BLE001
            log.exception("could not record completion of job %s", job_id)
        finally:
            db.close()

    def _fail(
        self,
        job_id: int,
        error_code: str,
        error_message: str,
        *,
        permanent: bool,
    ) -> None:
        db = SessionLocal()
        try:
            job = JobQueueService(db).fail(
                job_id,
                self.worker_id,
                error_code,
                error_message[:MAX_ERROR_MESSAGE],
                permanent=permanent,
            )
            if job is None:
                log.warning(
                    "job %s failed but its lease had already been lost", job_id
                )
            else:
                log.info(
                    "job %s failed (%s) -> %s", job_id, error_code, job.state
                )
        except Exception:  # noqa: BLE001
            log.exception("could not record failure of job %s", job_id)
        finally:
            db.close()


__all__ = ["JobWorker", "decode_input"]
