"""The background job worker suite (DI-03 follow-up, PS-11).

Why this suite exists
---------------------
The queue had a complete lifecycle and a suite proving every transition, and
nothing executed it: `claim_next` and `get_handler` were never called outside
a test. A file over `IMPORT_JOB_ROW_THRESHOLD` was answered with `202` —
"queued for a background job" — and never applied. The product told the
operator the work was accepted; the only thing missing was the thing that
would do it.

What is proven here
-------------------
* `enqueue` stores the payload, not only its hash. A hash is one-way, so
  before `0024_job_input_payload` no worker could recover the parameters.
* A real `csv_import` job runs end to end through the worker: the previewed
  import is applied, the job is `succeeded`, and running the worker again
  does not apply it twice.
* A job with no payload is dead-lettered with a message that says so.
* A job whose type has no handler is dead-lettered.
* A handler that refuses permanently (`JobNotImplemented`) goes straight to
  `dead` on its first attempt — five retries would only delay the truth.
* Every handler that has no work behind it refuses; none of them returns a
  success result.
* A transient failure is retried: `failed` with the error recorded, then
  `retry_failed` and a second pass succeeds.
* The heartbeat keeps the lease alive while a handler runs longer than the
  lease.
* `stop()` waits for the job in flight and claims nothing after it.
* An expired lease is released and the job runs under the new worker.
* `retention_run` does the real work — the expired upload is deleted and the
  dry run is marked expired — rather than reporting a constant zero.

Run:  python job_worker_test_suite.py
"""
import json
import os
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="job_worker_"), "worker.db")
STORAGE_DIR = os.path.join(tempfile.mkdtemp(prefix="job_worker_storage_"), "files")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOCAL_STORAGE_DIR"] = STORAGE_DIR

from app.core.database import Base, SessionLocal, engine  # noqa: E402
import app.main as app_main  # noqa: E402  (registers every model with the mappers)
from app.jobs import registry  # noqa: E402
from app.jobs.errors import JobInputInvalid, JobNotImplemented  # noqa: E402
from app.jobs.queue import JobQueueService, compute_input_hash  # noqa: E402
from app.jobs.worker import JobWorker, decode_input  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.imports import ImportDryRun, ImportStatus  # noqa: E402
from app.models.job_queue import JobQueue, JobState, JobType  # noqa: E402

Base.metadata.create_all(bind=engine)

RESULTS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def as_utc(value):
    """SQLite returns naive datetimes; treat them as UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def refresh(job_id: int) -> JobQueue | None:
    db = SessionLocal()
    try:
        return db.query(JobQueue).filter(JobQueue.id == job_id).first()
    finally:
        db.close()


def sha(value: str) -> str:
    return compute_input_hash({"probe": value})


db = SessionLocal()
service = JobQueueService(db)
worker = JobWorker(poll_seconds=0.05, lease_seconds=30, worker_id="suite-worker")

print("=" * 68)
print("JOB WORKER SUITE")
print("=" * 68)

# ---------------------------------------------------------------------------
# The payload
# ---------------------------------------------------------------------------
payload = {"entity": "departments", "confirmation_token": "tok-1", "user_id": 1}
job = service.enqueue(JobType.CSV_IMPORT, payload)
check(
    "enqueue stores the payload beside its hash",
    job.input_json is not None and json.loads(job.input_json) == payload,
    f"got {job.input_json!r}",
)
check(
    "the hash is still the hash of the same payload",
    job.input_hash == compute_input_hash(payload),
)
try:
    decoded = decode_input(job)
except JobInputInvalid:
    decoded = None
check(
    "decode_input returns the stored payload",
    decoded == payload,
)

# The payload probe is not work to run: remove it so the first job the worker
# claims in the next section is the one that section is about.
db.delete(job)
db.commit()

# A row written before the payload column existed (or by hand) cannot be run.
missing = JobQueue(
    job_type=JobType.CSV_IMPORT.value,
    input_hash=sha("no-payload"),
    input_json=None,
    state=JobState.QUEUED,
    attempts=0,
    max_attempts=5,
    priority=10,
)
db.add(missing)
db.commit()
missing_id = missing.id

check("the worker processes the job with no payload", worker.run_once() is True)
row = refresh(missing_id)
check(
    "a job with no payload is dead-lettered, not guessed at",
    row is not None and row.state == JobState.DEAD,
    f"state={row.state if row else None}",
)
check(
    "the dead job says the payload is missing",
    row is not None
    and row.error_code == "job_input_invalid"
    and "payload" in (row.error_message or ""),
    f"code={row.error_code if row else None} msg={row.error_message if row else None}",
)
check(
    "a missing payload is not retried",
    row is not None and row.attempts == 1,
    f"attempts={row.attempts if row else None}",
)

# ---------------------------------------------------------------------------
# A type with no handler
# ---------------------------------------------------------------------------
unknown = JobQueue(
    job_type="not_a_job",
    input_hash=sha("unknown-type"),
    input_json=json.dumps({"anything": True}),
    state=JobState.QUEUED,
    attempts=0,
    max_attempts=5,
    priority=10,
)
db.add(unknown)
db.commit()
unknown_id = unknown.id
worker.run_once()
row = refresh(unknown_id)
check(
    "a job type with no handler is dead-lettered",
    row is not None
    and row.state == JobState.DEAD
    and row.error_code == "job_type_not_registered",
    f"state={row.state if row else None} code={row.error_code if row else None}",
)
check(
    "the message names the type",
    row is not None and "not_a_job" in (row.error_message or ""),
    f"msg={row.error_message if row else None}",
)

# ---------------------------------------------------------------------------
# A permanent refusal is not retried
# ---------------------------------------------------------------------------
refused = service.enqueue(JobType.PAYROLL_PROCESS, {"pay_run_id": 42})
worker.run_once()
row = refresh(refused.id)
check(
    "a handler that refuses permanently is dead on its first attempt",
    row is not None
    and row.state == JobState.DEAD
    and row.attempts == 1
    and row.error_code == "job_not_implemented",
    f"state={row.state if row else None} attempts={row.attempts if row else None} "
    f"code={row.error_code if row else None}",
)
check(
    "the refusal names what actually calculates a pay run",
    row is not None and "/payroll/runs" in (row.error_message or ""),
    f"msg={row.error_message if row else None}",
)

# ---------------------------------------------------------------------------
# A cancelled job is not retried
# ---------------------------------------------------------------------------
# A cancelled import refuses every later attempt at the same token, so a
# retry cannot succeed. The import handler raises JobCancelled for that, and
# the worker's contract — that it is not retried — is what this suite owns;
# the handler is stood in so the check is about the worker, not the import.
from app.jobs import worker as worker_module  # noqa: E402
from app.jobs.errors import JobCancelled  # noqa: E402


def cancelled_handler(job, payload):
    raise JobCancelled("The import was cancelled before it finished.")


real_get_handler = worker_module.get_handler
worker_module.get_handler = lambda job_type: cancelled_handler
try:
    cancelled = service.enqueue(JobType.RETENTION_RUN, {"reason": "cancel probe"})
    worker.run_once()
finally:
    worker_module.get_handler = real_get_handler

row = refresh(cancelled.id)
check(
    "a cancelled job is dead on its first attempt",
    row is not None
    and row.state == JobState.DEAD
    and row.attempts == 1
    and row.error_code == "job_cancelled",
    f"state={row.state if row else None} attempts={row.attempts if row else None} "
    f"code={row.error_code if row else None}",
)
check(
    "a cancelled job says it was cancelled",
    row is not None and "cancel" in (row.error_message or "").lower(),
    f"msg={row.error_message if row else None}",
)

# ---------------------------------------------------------------------------
# No handler reports success it did not achieve
# ---------------------------------------------------------------------------
UNBUILT = (
    JobType.FORECAST_RUN,
    JobType.PAYROLL_PROCESS,
    JobType.DOCUMENT_RENDER,
    JobType.WEBHOOK_DELIVER,
    JobType.ERASURE_RUN,
)
for job_type in UNBUILT:
    handler = registry.get_handler(job_type)
    if handler is None:
        check(f"{job_type.value} has a registered handler", False, "no handler")
        continue
    try:
        handler(job, {})
    except JobNotImplemented as exc:
        check(
            f"{job_type.value} refuses instead of reporting success",
            bool(str(exc)),
        )
    except Exception as exc:  # noqa: BLE001
        check(
            f"{job_type.value} refuses instead of reporting success",
            False,
            f"raised {type(exc).__name__}: {exc}",
        )
    else:
        check(
            f"{job_type.value} refuses instead of reporting success",
            False,
            "returned a success result",
        )

# ---------------------------------------------------------------------------
# A real csv import, end to end
# ---------------------------------------------------------------------------
from app.imports import runner  # noqa: E402
from app.storage import get_storage  # noqa: E402

csv_bytes = b"name,code\nWorker Import,WKIMP\n"
preview = runner.dry_run(db, "departments", csv_bytes, file_name="worker.csv")
import_job = runner.queue_job(db, "departments", preview.token)
check(
    "the queued import carries its confirmation token",
    import_job.input_json is not None
    and json.loads(import_job.input_json).get("confirmation_token")
    == preview.token,
)

worker.run_once()
row = refresh(import_job.id)
check(
    "the worker applies the queued import and succeeds",
    row is not None and row.state == JobState.SUCCEEDED,
    f"state={row.state if row else None} error={row.error_message if row else None}",
)
db.expire_all()
department = db.query(Department).filter(Department.code == "WKIMP").first()
check(
    "the import's row is in the database",
    department is not None and department.name == "Worker Import",
    f"got {department!r}",
)
dry_run_row = (
    db.query(ImportDryRun).filter(ImportDryRun.token == preview.token).first()
)
check(
    "the import record is committed, not left pending",
    dry_run_row is not None and dry_run_row.status == ImportStatus.COMMITTED,
    f"status={dry_run_row.status if dry_run_row else None}",
)
check(
    "the worker does not claim the finished job again",
    worker.run_once() is False,
)
check(
    "the import was applied once, not twice",
    db.query(Department).filter(Department.code == "WKIMP").count() == 1,
)

# ---------------------------------------------------------------------------
# A transient failure is retried
# ---------------------------------------------------------------------------
ORIGINAL_WEBHOOK = registry.HANDLER_REGISTRY[JobType.WEBHOOK_DELIVER]


def failing_webhook(job, payload):
    raise RuntimeError("the upstream endpoint timed out")


registry.HANDLER_REGISTRY[JobType.WEBHOOK_DELIVER] = failing_webhook
retry_job = service.enqueue(
    JobType.WEBHOOK_DELIVER, {"url": "https://example.invalid/hook", "probe": "retry"}
)
worker.run_once()
row = refresh(retry_job.id)
check(
    "a transient failure leaves the job failed for retry",
    row is not None
    and row.state == JobState.FAILED
    and row.error_code == "job_failed",
    f"state={row.state if row else None} code={row.error_code if row else None}",
)
check(
    "the error records the exception",
    row is not None and "RuntimeError" in (row.error_message or ""),
    f"msg={row.error_message if row else None}",
)


def working_webhook(job, payload):
    return {"delivered": True, "url": payload.get("url")}


registry.HANDLER_REGISTRY[JobType.WEBHOOK_DELIVER] = working_webhook
# The worker writes through its own session; this suite's session still has
# the pre-run row in its identity map. Refresh it before asking the queue to
# act on the row the worker actually wrote.
db.expire_all()
requeued = service.retry_failed(retry_job.id)
check(
    "retry_failed returns the job to the queue",
    requeued is not None and requeued.state == JobState.QUEUED,
    f"state={requeued.state if requeued else None}",
)
worker.run_once()
row = refresh(retry_job.id)
check(
    "the retried job succeeds on its second attempt",
    row is not None and row.state == JobState.SUCCEEDED and row.attempts == 2,
    f"state={row.state if row else None} attempts={row.attempts if row else None}",
)
registry.HANDLER_REGISTRY[JobType.WEBHOOK_DELIVER] = ORIGINAL_WEBHOOK

# ---------------------------------------------------------------------------
# The heartbeat keeps the lease alive
# ---------------------------------------------------------------------------
ORIGINAL_RENDER = registry.HANDLER_REGISTRY[JobType.DOCUMENT_RENDER]
seen = {}


def slow_handler(job, payload):
    session = SessionLocal()
    try:
        seen["first"] = session.query(JobQueue).filter(JobQueue.id == job.id).first().lease_expires_at
    finally:
        session.close()
    time.sleep(2.5)
    session = SessionLocal()
    try:
        seen["last"] = session.query(JobQueue).filter(JobQueue.id == job.id).first().lease_expires_at
    finally:
        session.close()
    seen["now"] = datetime.now(timezone.utc)
    return {"ok": True}


registry.HANDLER_REGISTRY[JobType.DOCUMENT_RENDER] = slow_handler
short_lease = JobWorker(
    poll_seconds=0.05, lease_seconds=1, worker_id="heartbeat-worker"
)
heartbeat_job = service.enqueue(JobType.DOCUMENT_RENDER, {"probe": "heartbeat"})
short_lease.run_once()
row = refresh(heartbeat_job.id)
check(
    "a handler that outlives its lease still succeeds",
    row is not None and row.state == JobState.SUCCEEDED,
    f"state={row.state if row else None} error={row.error_message if row else None}",
)
check(
    "the heartbeat extended the lease past the moment the handler finished",
    as_utc(seen.get("last")) is not None
    and as_utc(seen.get("last")) > as_utc(seen.get("now")),
    f"last={seen.get('last')} now={seen.get('now')}",
)
check(
    "the lease was renewed, not left at the first value",
    as_utc(seen.get("last")) is not None
    and as_utc(seen.get("first")) is not None
    and as_utc(seen.get("last")) > as_utc(seen.get("first")),
    f"first={seen.get('first')} last={seen.get('last')}",
)
registry.HANDLER_REGISTRY[JobType.DOCUMENT_RENDER] = ORIGINAL_RENDER

# ---------------------------------------------------------------------------
# A clean stop finishes the job in flight and claims nothing more
# ---------------------------------------------------------------------------
ORIGINAL_WEBHOOK = registry.HANDLER_REGISTRY[JobType.WEBHOOK_DELIVER]
started = threading.Event()


def slow_stop_handler(job, payload):
    started.set()
    time.sleep(0.4)
    return {"finished": True}


registry.HANDLER_REGISTRY[JobType.WEBHOOK_DELIVER] = slow_stop_handler
stop_job = service.enqueue(JobType.WEBHOOK_DELIVER, {"probe": "clean-stop"})
stopping = JobWorker(poll_seconds=0.05, lease_seconds=30, worker_id="stop-worker")
stopping.start()
check(
    "the worker started and claimed the job",
    started.wait(10),
)
check("stop returns when the worker has stopped", stopping.stop(timeout=10))
row = refresh(stop_job.id)
check(
    "the job in flight finished rather than being abandoned",
    row is not None and row.state == JobState.SUCCEEDED,
    f"state={row.state if row else None} error={row.error_message if row else None}",
)
check(
    "the stopped worker claims nothing afterwards",
    stopping._thread is not None and not stopping._thread.is_alive(),
)
registry.HANDLER_REGISTRY[JobType.WEBHOOK_DELIVER] = ORIGINAL_WEBHOOK

# ---------------------------------------------------------------------------
# An expired lease is released and the job runs
# ---------------------------------------------------------------------------
ORIGINAL_WEBHOOK = registry.HANDLER_REGISTRY[JobType.WEBHOOK_DELIVER]


def lease_webhook(job, payload):
    return {"delivered": True}


registry.HANDLER_REGISTRY[JobType.WEBHOOK_DELIVER] = lease_webhook
lease_job = service.enqueue(
    JobType.WEBHOOK_DELIVER, {"url": "https://example.invalid/lease", "probe": "lease"}
)
claimed = service.claim_next("dead-worker", lease_seconds=60)
check(
    "a first worker claims the job",
    claimed is not None and claimed.id == lease_job.id,
    f"claimed={claimed.id if claimed else None}",
)
claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=30)
db.add(claimed)
db.commit()
worker.run_once()
row = refresh(lease_job.id)
check(
    "an expired lease is released and the job runs under the new worker",
    row is not None
    and row.state == JobState.SUCCEEDED
    and row.worker_id == worker.worker_id,
    f"state={row.state if row else None} worker={row.worker_id if row else None}",
)
registry.HANDLER_REGISTRY[JobType.WEBHOOK_DELIVER] = ORIGINAL_WEBHOOK

# ---------------------------------------------------------------------------
# retention_run does the real work
# ---------------------------------------------------------------------------
retention_preview = runner.dry_run(
    db, "departments", b"name,code\nRetention Import,RTIMP\n", file_name="retention.csv"
)
retention_row = (
    db.query(ImportDryRun)
    .filter(ImportDryRun.token == retention_preview.token)
    .first()
)
storage_key = retention_row.storage_key
storage = get_storage()
check(
    "the upload to be purged is in storage",
    storage.exists(storage_key),
)
retention_row.upload_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
db.add(retention_row)
db.commit()

retention_job = service.enqueue(JobType.RETENTION_RUN, {"probe": "retention"})
worker.run_once()
db.expire_all()
retention_row = (
    db.query(ImportDryRun)
    .filter(ImportDryRun.token == retention_preview.token)
    .first()
)
check(
    "retention_run deletes the expired upload",
    not storage.exists(storage_key),
)
check(
    "retention_run marks the dry run expired",
    retention_row is not None and retention_row.status == ImportStatus.EXPIRED,
    f"status={retention_row.status if retention_row else None}",
)
row = refresh(retention_job.id)
check(
    "the retention job succeeds because it did the work",
    row is not None and row.state == JobState.SUCCEEDED,
    f"state={row.state if row else None} error={row.error_message if row else None}",
)

# ---------------------------------------------------------------------------
# The deployment switch
# ---------------------------------------------------------------------------
from app.core.config import settings  # noqa: E402

# Reset the module-level worker and the deployment switch so this suite's
# assertions are not affected by a worker a previous suite (or the .env file)
# left enabled (test isolation).
settings.JOB_WORKER_ENABLED = False
app_main._job_worker = None
app_main.on_startup()
check(
    "the worker is off unless the deployment enables it",
    app_main._job_worker is None,
)

settings.JOB_WORKER_ENABLED = True
app_main.on_startup()
check(
    "the worker starts when JOB_WORKER_ENABLED is set",
    app_main._job_worker is not None,
)
app_main.on_shutdown()
check(
    "shutdown stops the worker and clears it",
    app_main._job_worker is None,
)
settings.JOB_WORKER_ENABLED = False

print()
print("=" * 68)
print(f"JOB WORKER SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print()
    print("Failures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
db.close()
raise SystemExit(1 if RESULTS["fail"] else 0)
