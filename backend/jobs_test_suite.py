"""Job queue regression suite.

Covers the background job queue (J-04/J-05/J-06/J-07):

* Job enqueue with input hash deduplication
* Claim/lease with heartbeat
* Complete/fail lifecycle
* Retry with exponential backoff, max attempts, dead-letter
* Discard dead jobs
* List/filter jobs by type and state

Run:  python jobs_test_suite.py
"""
import os
import tempfile
import sys

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="jobs_test_"), "jobs_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from datetime import datetime, timezone, timedelta  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.models.job_queue import JobQueue, JobState, JobType  # noqa: E402
from app.jobs.queue import JobQueueService  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
client = TestClient(app, raise_server_exceptions=False)

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


print("=" * 68)
print("JOB QUEUE SUITE")
print("=" * 68)

# --- The vocabulary is a real enum ---------------------------------------
# The model once inherited ``sqlalchemy.Enum`` by mistake, so these names were
# plain strings: ``JobState.DEAD.value`` raised AttributeError and an
# ``isinstance`` guard was silently never true. The columns stay plain strings
# and a member still compares equal to its value, so the queue is unchanged.
check(
    "the state vocabulary is a str enum",
    isinstance(JobState.QUEUED, JobState) and isinstance(JobState.QUEUED, str),
    f"got {type(JobState.QUEUED).__name__}",
)
check(
    "the type vocabulary is a str enum",
    isinstance(JobType.CSV_IMPORT, JobType) and isinstance(JobType.CSV_IMPORT, str),
    f"got {type(JobType.CSV_IMPORT).__name__}",
)
check(
    "a member equals its stored value",
    JobState.DEAD.value == "dead"
    and JobState.DEAD == "dead"
    and JobType.FORECAST_RUN.value == "forecast_run"
    and JobType.FORECAST_RUN == "forecast_run",
    f"state={JobState.DEAD!r}, type={JobType.FORECAST_RUN!r}",
)

# --- Enqueue --------------------------------------------------------------
service = JobQueueService(db)

job1 = service.enqueue(JobType.CSV_IMPORT, {"entity": "employees", "file": "emp.csv"})
check(
    "enqueue creates queued job",
    job1.state == JobState.QUEUED and job1.job_type == JobType.CSV_IMPORT,
    f"got state={job1.state}, type={job1.job_type}",
)
check(
    "enqueue computes input hash",
    bool(job1.input_hash) and len(job1.input_hash) == 64,
    f"got hash={job1.input_hash}",
)

# --- Idempotent re-enqueue ------------------------------------------------
# Complete job1 first, then re-enqueue same input → should return existing job
claimed1 = service.claim_next("worker-1", lease_seconds=300)
if claimed1:
    service.complete(claimed1.id, "worker-1", {"result": "done"})
job1_dup = service.enqueue(JobType.CSV_IMPORT, {"entity": "employees", "file": "emp.csv"})
check(
    "re-enqueue same input returns existing job (idempotent)",
    job1_dup.id == job1.id,
    f"got id={job1_dup.id}, expected {job1.id}",
)

# --- Different input creates new job --------------------------------------
job2 = service.enqueue(JobType.CSV_IMPORT, {"entity": "employees", "file": "emp2.csv"})
check(
    "different input creates new job",
    job2.id != job1.id and job2.state == JobState.QUEUED,
    f"got id={job2.id}, state={job2.state}",
)

# --- Claim / lease --------------------------------------------------------
claimed = service.claim_next("worker-1", lease_seconds=300)
check(
    "claim_next returns a queued job",
    claimed is not None and claimed.state == JobState.RUNNING,
    f"got {claimed}",
)
if claimed:
    check(
        "claimed job has worker_id and lease",
        claimed.worker_id == "worker-1" and claimed.lease_expires_at is not None,
        f"worker={claimed.worker_id}, lease={claimed.lease_expires_at}",
    )

# --- Heartbeat ------------------------------------------------------------
if claimed:
    ok = service.heartbeat(claimed.id, "worker-1", lease_seconds=300)
    check(
        "heartbeat extends lease",
        ok is True,
        f"got {ok}",
    )

# --- Complete -------------------------------------------------------------
if claimed:
    completed = service.complete(claimed.id, "worker-1", {"result": "ok"})
    check(
        "complete marks job succeeded",
        completed is not None
        and completed.state == JobState.SUCCEEDED
        and completed.result_hash is not None,
        f"got state={completed.state if completed else None}",
    )

# --- Fail ----------------------------------------------------------------
job3 = service.enqueue(JobType.FORECAST_RUN, {"series": "demand", "weeks": 8})
claimed3 = service.claim_next("worker-2", lease_seconds=300)
if claimed3:
    failed = service.fail(claimed3.id, "worker-2", "timeout", "Solver timed out")
    check(
        "fail marks job failed",
        failed is not None and failed.state == JobState.FAILED,
        f"got state={failed.state if failed else None}",
    )
    check(
        "failed job has error code and message",
        failed.error_code == "timeout"
        and failed.error_message == "Solver timed out",
        f"got code={failed.error_code}, msg={failed.error_message}",
    )

# --- Retry ----------------------------------------------------------------
if claimed3:
    retried = service.retry_failed(claimed3.id)
    check(
        "retry moves failed job back to queued",
        retried is not None and retried.state == JobState.QUEUED,
        f"got state={retried.state if retried else None}",
    )
    check(
        "retry clears worker and lease",
        retried.worker_id is None and retried.lease_expires_at is None,
        f"worker={retried.worker_id}, lease={retried.lease_expires_at}",
    )

# --- Max attempts -> dead -------------------------------------------------
job4 = service.enqueue(JobType.ROSTER_SOLVE, {"period": "2026-11"})
# Set attempts to max_attempts - 1 so the next fail exhausts retries
job4.attempts = job4.max_attempts - 1
db.add(job4)
db.commit()
# Claim the specific job by ID directly
claimed4 = db.query(JobQueue).filter(
    JobQueue.id == job4.id, JobQueue.state == JobState.QUEUED
).first()
if claimed4:
    claimed4.state = JobState.RUNNING
    claimed4.attempts += 1
    claimed4.worker_id = "worker-3"
    claimed4.lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=300)
    db.add(claimed4)
    db.commit()
    service.fail(claimed4.id, "worker-3", "error", "boom")
    job4_refresh = db.query(JobQueue).filter(JobQueue.id == job4.id).first()
    check(
        "max attempts moves job to dead",
        job4_refresh is not None and job4_refresh.state == JobState.DEAD,
        f"got state={job4_refresh.state if job4_refresh else None}, attempts={job4_refresh.attempts if job4_refresh else None}",
    )

# --- List / filter --------------------------------------------------------
all_jobs = service.list_jobs()
check(
    "list_jobs returns all jobs",
    len(all_jobs) >= 4,
    f"got {len(all_jobs)} jobs",
)

queued_jobs = service.list_jobs(state=JobState.QUEUED)
check(
    "list_jobs filters by state",
    all(j.state == JobState.QUEUED for j in queued_jobs),
    f"got states={[j.state for j in queued_jobs]}",
)

csv_jobs = service.list_jobs(job_type=JobType.CSV_IMPORT)
check(
    "list_jobs filters by type",
    all(j.job_type == JobType.CSV_IMPORT for j in csv_jobs),
    f"got types={[j.job_type for j in csv_jobs]}",
)

# --- Dead letter ----------------------------------------------------------
dead_jobs = service.list_dead()
check(
    "list_dead returns dead jobs",
    len(dead_jobs) >= 1,
    f"got {len(dead_jobs)} dead jobs",
)

# --- Discard dead ---------------------------------------------------------
if dead_jobs:
    discarded = service.discard_dead(dead_jobs[0].id)
    check(
        "discard removes dead job",
        discarded is not None,
        f"got {discarded}",
    )
    discarded_again = service.discard_dead(dead_jobs[0].id)
    check(
        "discard non-existent dead job returns None",
        discarded_again is None,
        f"got {discarded_again}",
    )

# --- Release expired leases -----------------------------------------------
job5 = service.enqueue(JobType.PAYROLL_PROCESS, {"period": "2026-10"})
claimed5 = service.claim_next("worker-4", lease_seconds=1)  # 1 second lease
if claimed5:
    # Manually expire the lease by setting it to the past
    claimed5.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db.add(claimed5)
    db.commit()
    released = service.release_expired_leases()
    check(
        "release_expired_leases releases expired lease",
        released >= 1,
        f"released {released} jobs",
    )
    job5_refresh = db.query(JobQueue).filter(JobQueue.id == job5.id).first()
    check(
        "released job is back to queued",
        job5_refresh is not None and job5_refresh.state == JobState.QUEUED,
        f"got state={job5_refresh.state if job5_refresh else None}",
    )

print()
print("=" * 68)
print(f"JOB QUEUE SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print()
    print("Failures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
db.close()
raise SystemExit(1 if RESULTS["fail"] else 0)
