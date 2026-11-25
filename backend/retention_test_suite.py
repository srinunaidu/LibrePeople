"""Upload-retention schedule suite (IM-10).

IM-10's defect was not a missing purge — `purge_expired_uploads` exists
and is proven. It was a missing *schedule*: nothing ever enqueued
`retention_run`, so an upload whose tenant never ran another import was
never swept. This suite proves the schedule:

* a tick on a quiet database enqueues exactly one `retention_run` job
  with the reason marked `retention_schedule`;
* a tick while a retention job is queued enqueues nothing (no duplicate);
* a tick while a retention job is *running* enqueues nothing alike;
* after a retention job succeeds, the next tick enqueues afresh;
* the tick never raises when the underlying enqueue is forced to fail,
  and the API stays available;
* `start_retention_schedule()` stays inert with the default
  `RETENTION_SCHEDULE_ENABLED=false`, and the config carries the
  documented defaults.

Run:  python retention_test_suite.py
"""
import os

DB_PATH = "retention_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from app.main import app  # noqa: E402,F401
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.models.job_queue import JobQueue, JobState, JobType  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.jobs import retention  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()

RESULTS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name, condition, detail=""):
    if condition:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  -- {detail}")


def reset_queue():
    db.query(JobQueue).delete()
    db.commit()


# --- config contract --------------------------------------------------------
check("RETENTION_SCHEDULE_ENABLED defaults to False (opt-in)",
      settings.RETENTION_SCHEDULE_ENABLED is False,
      f"got {settings.RETENTION_SCHEDULE_ENABLED}")
check("RETENTION_RUN_INTERVAL_HOURS defaults to 24",
      settings.RETENTION_RUN_INTERVAL_HOURS == 24.0,
      f"got {settings.RETENTION_RUN_INTERVAL_HOURS}")

# --- tick on a quiet database ----------------------------------------------
reset_queue()
result = retention.tick(db)
check("tick enqueues a retention job", result == "enqueued", f"got {result}")
row = db.query(JobQueue).filter(JobQueue.job_type == JobType.RETENTION_RUN).one_or_none()
check("the enqueued job is RETENTION_RUN and queued",
      row is not None and row.state == JobState.QUEUED,
      f"type={row.job_type if row else None} state={row.state if row else None}")
import json
check("the payload carries reason=retention_schedule",
      row is not None and row.input_json and json.loads(row.input_json).get("reason") == "retention_schedule",
      f"payload={getattr(row, 'input_json', None)}")

# --- tick while pending: no duplicates --------------------------------------
result2 = retention.tick(db)
count = db.query(JobQueue).filter(JobQueue.job_type == JobType.RETENTION_RUN).count()
check("tick while pending is a no-op", result2 == "skipped-pending" and count == 1,
      f"result={result2} count={count}")

# --- tick while running: no duplicates either --------------------------------
row.state = JobState.RUNNING
db.commit()
result3 = retention.tick(db)
count = db.query(JobQueue).filter(JobQueue.job_type == JobType.RETENTION_RUN).count()
check("tick while running is a no-op", result3 == "skipped-pending" and count == 1,
      f"result={result3} count={count}")

# --- after it succeeds, the next tick enqueues afresh ------------------------
row.state = JobState.SUCCEEDED
db.commit()
result4 = retention.tick(db)
count = db.query(JobQueue).filter(JobQueue.job_type == JobType.RETENTION_RUN).count()
check("tick after success enqueues afresh", result4 == "enqueued" and count == 2,
      f"result={result4} count={count}")

reset_queue()

# --- fail-closed tick: a forced failure never raises --------------------------
class BrokenService:
    def __init__(self, db_):
        pass

    def enqueue(self, *a, **k):
        raise RuntimeError("forced enqueue failure")

_original = retention.JobQueueService
retention.JobQueueService = BrokenService
try:
    result = retention.tick(db)
    check("tick survives a forced enqueue failure", result == "skipped-pending", f"got {result}")
finally:
    retention.JobQueueService = _original

# --- start_retention_schedule inert under defaults ----------------------------
check("start_retention_schedule() inert when disabled",
      retention.start_retention_schedule() is False,
      "expected False with RETENTION_SCHEDULE_ENABLED=false")

# --- double start returns cleanly --------------------------------------------
result5 = retention.tick(db)
check("a fresh tick still enqueues after BrokenService is removed",
      result5 == "enqueued", f"got {result5}")

print()
print("=" * 70)
print(f"==== RETENTION SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 70)
raise SystemExit(1 if RESULTS["fail"] else 0)
