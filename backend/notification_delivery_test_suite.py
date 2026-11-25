"""Notification delivery: queued tracking + background send (LP-NOT-003).

What this suite proves
-----------------------
* **Migration 0042** adds ``delivery_status``/``delivery_attempts``/
  ``delivery_error`` to a pre-0042 ``notifications`` table, backfills
  existing rows as ``queued``/``0``/``NULL``, and downgrades cleanly.
* **Emission** still writes one row, now stamped ``queued``/``0``.
* **enqueue_delivery** is idempotent: re-enqueueing while a job for the
  row is queued, running or failed returns the same job; after success
  the queue itself returns the succeeded job.
* **The handler** delivers end to end through the worker: the job
  succeeds and the row reads ``sent`` with one attempt and the
  email-channel intent recorded. Re-delivering a sent row is a no-op.
  No vendor is called anywhere.
* **Unknown ids** are refused permanently: the job goes straight to
  ``dead`` with ``job_input_invalid``.
* **Transient failures** mark the row ``failed`` with the error kept,
  and a retry after the fix delivers it.
* **Spent attempts** mark the row ``dead``: with ``max_attempts=1`` a
  single transient failure dead-letters both the job and the row (the
  five-attempt default is the same machinery with a larger budget).
* **Backoff** grows per attempt and is capped.
* **PUT preferences** writes only the caller's own flags (partial
  updates keep omitted flags), refuses a login with no employee, and
  never touches another caller's flags.
* **Reads** expose delivery: the list and mark-read payloads carry
  ``delivery_status``/``delivery_attempts``/``delivery_error``.

Run:  python notification_delivery_test_suite.py
"""
import os
import sqlite3
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="notification_delivery_test_suite_"), "notification_delivery_test_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_OPRIGINS"] = ""
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"  # keep the suite's output readable
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

import datetime  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.ess_hr import EmployeeSelfService, Notification  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.job_queue import JobState, JobType  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import notifications as notify  # noqa: E402
import app.jobs.handlers as handlers  # noqa: E402
from app.jobs.queue import (  # noqa: E402
    BACKOFF_MAX_SECONDS,
    JobQueueService,
    compute_backoff_seconds,
)
from app.jobs.worker import JobWorker  # noqa: E402

Base.metadata.create_all(bind=engine)

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def _load_revision(filename: str):
    """A revision module, loaded by path (names start with a digit)."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parent / "migrations" / "versions" / filename
    spec = importlib.util.spec_from_file_location("mig_" + filename[:4], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _apply_revision(db_path: str, filename: str, direction: str = "upgrade") -> None:
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration = _load_revision(filename)
    eng = sa.create_engine(f"sqlite:///{db_path}")
    try:
        with eng.begin() as conn:
            context = MigrationContext.configure(conn)
            with Operations.context(context):
                getattr(migration, direction)()
    finally:
        eng.dispose()


def _columns(db_path: str, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


# ===========================================================================
print("\n[DEL-01] Migration 0042 expands a pre-delivery notifications table")
# ===========================================================================
legacy_path = os.path.join(tempfile.mkdtemp(prefix="notif-delivery-mig-"), "legacy.db")
conn = sqlite3.connect(legacy_path)
conn.execute(
    "CREATE TABLE notifications ("
    "id INTEGER NOT NULL PRIMARY KEY, "
    "recipient_id INTEGER NOT NULL, "
    "title VARCHAR(200) NOT NULL, "
    "message TEXT NOT NULL, "
    "notification_type VARCHAR(40) NOT NULL, "
    "category VARCHAR(40), "
    "entity_type VARCHAR(60), "
    "entity_id INTEGER, "
    "is_read BOOLEAN NOT NULL DEFAULT 0, "
    "read_at DATETIME, "
    "email_sent BOOLEAN NOT NULL DEFAULT 0, "
    "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
)
conn.execute(
    "INSERT INTO notifications (id, recipient_id, title, message, notification_type)"
    " VALUES (1, 7, 'legacy', 'before delivery', 'info')"
)
conn.commit()
conn.close()
check("legacy table starts without delivery columns",
      _columns(legacy_path, "notifications") == {
          "id", "recipient_id", "title", "message", "notification_type",
          "category", "entity_type", "entity_id", "is_read", "read_at",
          "email_sent", "created_at",
      })
_apply_revision(legacy_path, "0042_notification_delivery.py")
check("upgrade adds the three delivery columns",
      {"delivery_status", "delivery_attempts", "delivery_error"}
      <= _columns(legacy_path, "notifications"),
      f"columns={sorted(_columns(legacy_path, 'notifications'))}")
conn = sqlite3.connect(legacy_path)
legacy_row = conn.execute(
    "SELECT delivery_status, delivery_attempts, delivery_error"
    " FROM notifications WHERE id = 1"
).fetchone()
conn.close()
check("existing rows backfill as queued/0/NULL",
      legacy_row == ("queued", 0, None), f"row={legacy_row!r}")
_apply_revision(legacy_path, "0042_notification_delivery.py", "downgrade")
check("downgrade removes the delivery columns",
      not ({"delivery_status", "delivery_attempts", "delivery_error"}
           & _columns(legacy_path, "notifications")))
_apply_revision(legacy_path, "0042_notification_delivery.py")
check("upgrade restores the delivery columns",
      {"delivery_status", "delivery_attempts", "delivery_error"}
      <= _columns(legacy_path, "notifications"))


# --- fixtures -----------------------------------------------------------------
db = SessionLocal()

dept = Department(name="Delivery", code="DLV")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Courier", code="DLVJOB", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def _employee(code: str) -> Employee:
    emp = Employee(
        employee_id=code, first_name="Deliv", last_name=code,
        email=f"{code.lower()}@example.com", hire_date=datetime.date(2024, 1, 1),
        job_id=job.id, department_id=dept.id, status="Active",
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


emp_a = _employee("DLV-A")
emp_b = _employee("DLV-B")
EMP_A_ID, EMP_B_ID = emp_a.id, emp_b.id


def _user(username: str, employee_id: int | None, password: str) -> int:
    u = User(username=username, email=f"{username}@example.com",
             hashed_password=get_password_hash(password), role="Associate",
             is_active=True, employee_id=employee_id, mfa_enabled=False)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u.id


assoc_id = _user("dlv_assoc", EMP_A_ID, "AssocPass12345")
assoc2_id = _user("dlv_assoc2", EMP_B_ID, "Assoc2Pass12345")
lonely_id = _user("dlv_lonely", None, "LonelyPass12345")
db.close()

client = TestClient(app, raise_server_exceptions=False)


def _headers(username: str, password: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"login {username}: {r.status_code} {r.text[:160]}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


H_A = _headers("dlv_assoc", "AssocPass12345")
H_B = _headers("dlv_assoc2", "Assoc2Pass12345")
H_LONELY = _headers("dlv_lonely", "LonelyPass12345")

worker = JobWorker(poll_seconds=0.05, lease_seconds=30, worker_id="delivery-suite-worker")


def _drain(max_passes: int = 20) -> None:
    for _ in range(max_passes):
        if not worker.run_once():
            return


def _fresh_job(job_id: int):
    with SessionLocal() as s:
        return s.query(handlers.JobQueue).filter(handlers.JobQueue.id == job_id).first()


def _fresh_notif(notif_id: int):
    with SessionLocal() as s:
        return s.query(Notification).filter(Notification.id == notif_id).first()


# ===========================================================================
print("\n[DEL-02] Emission stamps the row queued with zero attempts")
# ===========================================================================
with SessionLocal() as s:
    row = notify.emit(s, recipient_user_id=assoc_id, title="Delivery probe",
                      message="will be delivered", notification_type="info",
                      category="system", entity_type="probe", entity_id=9001)
    s.commit()
    nid = row.id
row = _fresh_notif(nid)
check("emission stamps queued/0/NULL",
      row.delivery_status == "queued" and row.delivery_attempts == 0
      and row.delivery_error is None,
      f"status={row.delivery_status} attempts={row.delivery_attempts}")


# ===========================================================================
print("\n[DEL-03] enqueue_delivery is idempotent while work is in flight")
# ===========================================================================
with SessionLocal() as s:
    first = notify.enqueue_delivery(s, nid)
    first_id = first.id
    second = notify.enqueue_delivery(s, nid)
check("re-enqueue returns the same job",
      second.id == first_id, f"first={first_id} second={second.id}")
check("the job carries the notification id",
      first.job_type == JobType.NOTIFICATION_DELIVER
      and first.input_json is not None and str(nid) in first.input_json,
      f"type={first.job_type} payload={first.input_json!r}")


# ===========================================================================
print("\n[DEL-04] The worker delivers: job succeeds, row reads sent")
# ===========================================================================
_drain()
job_row = _fresh_job(first_id)
row = _fresh_notif(nid)
check("the job succeeded",
      job_row is not None and job_row.state == JobState.SUCCEEDED,
      f"state={job_row.state if job_row else None}")
check("the row reads sent after one attempt",
      row.delivery_status == "sent" and row.delivery_attempts == 1
      and row.delivery_error is None,
      f"status={row.delivery_status} attempts={row.delivery_attempts}")
check("the email-channel intent is recorded, no vendor involved",
      row.email_sent is True)
with SessionLocal() as s:
    again = notify.enqueue_delivery(s, nid)
check("enqueue after success returns the succeeded job, not a duplicate",
      again.id == first_id and again.state == JobState.SUCCEEDED)
before_attempts = _fresh_notif(nid).delivery_attempts
_drain()
check("re-running delivery of a sent row changes nothing",
      _fresh_notif(nid).delivery_attempts == before_attempts
      and _fresh_notif(nid).delivery_status == "sent")


# ===========================================================================
print("\n[DEL-05] Unknown ids are refused permanently, not retried")
# ===========================================================================
with SessionLocal() as s:
    svc = JobQueueService(s)
    ghost = svc.enqueue(JobType.NOTIFICATION_DELIVER, {"notification_id": 999999})
    ghost_id = ghost.id
_drain()
ghost = _fresh_job(ghost_id)
check("the ghost job goes straight to dead",
      ghost is not None and ghost.state == JobState.DEAD,
      f"state={ghost.state if ghost else None}")
check("the refusal names the unusable input",
      ghost is not None and ghost.error_code == "job_input_invalid",
      f"code={ghost.error_code if ghost else None}")


# ===========================================================================
print("\n[DEL-06] Transient failure marks failed, retry delivers")
# ===========================================================================
with SessionLocal() as s:
    flaky = notify.emit(s, recipient_user_id=assoc_id, title="Flaky probe",
                        message="fails once", notification_type="info",
                        category="system", entity_type="probe", entity_id=9002)
    s.commit()
    flaky_id = flaky.id
    flaky_job = notify.enqueue_delivery(s, flaky_id)
    flaky_job_id = flaky_job.id

real_deliver = handlers._deliver_channels


def _boom_once(db, notification):
    handlers._deliver_channels = real_deliver
    raise RuntimeError("smtp unreachable (simulated)")


handlers._deliver_channels = _boom_once
_drain()
handlers._deliver_channels = real_deliver
flaky_job = _fresh_job(flaky_job_id)
flaky_row = _fresh_notif(flaky_id)
check("the transient failure leaves the job failed, not dead",
      flaky_job is not None and flaky_job.state == JobState.FAILED,
      f"state={flaky_job.state if flaky_job else None}")
check("the row reads failed with the attempt and error kept",
      flaky_row.delivery_status == "failed" and flaky_row.delivery_attempts == 1
      and flaky_row.delivery_error is not None
      and "smtp unreachable" in flaky_row.delivery_error,
      f"status={flaky_row.delivery_status} error={flaky_row.delivery_error!r}")
with SessionLocal() as s:
    same = notify.enqueue_delivery(s, flaky_id)
check("enqueue while failed returns the same job for retry",
      same.id == flaky_job_id)
with SessionLocal() as s:
    JobQueueService(s).retry_failed(flaky_job_id)
_drain()
flaky_job = _fresh_job(flaky_job_id)
flaky_row = _fresh_notif(flaky_id)
check("the retry succeeds",
      flaky_job is not None and flaky_job.state == JobState.SUCCEEDED,
      f"state={flaky_job.state if flaky_job else None}")
check("the row reads sent with the error cleared",
      flaky_row.delivery_status == "sent" and flaky_row.delivery_error is None
      and flaky_row.delivery_attempts == 2,
      f"status={flaky_row.delivery_status} attempts={flaky_row.delivery_attempts}")


# ===========================================================================
print("\n[DEL-07] Spent attempts dead-letter both the job and the row")
# ===========================================================================
with SessionLocal() as s:
    doomed = notify.emit(s, recipient_user_id=assoc_id, title="Doomed probe",
                         message="always fails", notification_type="info",
                         category="system", entity_type="probe", entity_id=9003)
    s.commit()
    doomed_id = doomed.id
    doomed_job = notify.enqueue_delivery(s, doomed_id, max_attempts=1)
    doomed_job_id = doomed_job.id


def _always_boom(db, notification):
    raise RuntimeError("provider down (simulated)")


handlers._deliver_channels = _always_boom
_drain()
handlers._deliver_channels = real_deliver
doomed_job = _fresh_job(doomed_job_id)
doomed_row = _fresh_notif(doomed_id)
check("the job is dead after its last attempt",
      doomed_job is not None and doomed_job.state == JobState.DEAD,
      f"state={doomed_job.state if doomed_job else None}")
check("the row reads dead with the attempt and error kept",
      doomed_row.delivery_status == "dead" and doomed_row.delivery_attempts == 1
      and doomed_row.delivery_error is not None,
      f"status={doomed_row.delivery_status}")
with SessionLocal() as s:
    defaulted = notify.enqueue_delivery(s, doomed_id)
check("the default budget is five attempts",
      defaulted.max_attempts == 5, f"max={defaulted.max_attempts}")


# ===========================================================================
print("\n[DEL-08] Backoff grows per attempt and is capped")
# ===========================================================================
b1, b2, b3 = (compute_backoff_seconds(1), compute_backoff_seconds(2),
              compute_backoff_seconds(3))
check("backoff grows with the attempt number", b1 < b2 < b3,
      f"b1={b1:.1f} b2={b2:.1f} b3={b3:.1f}")
check("backoff never exceeds the cap",
      compute_backoff_seconds(100) <= BACKOFF_MAX_SECONDS)


# ===========================================================================
print("\n[DEL-09] PUT preferences writes only the caller's own flags")
# ===========================================================================
r = client.get("/api/v1/ess/notifications/preferences", headers=H_A)
check("preferences read answers with defaults for a profile-less caller",
      r.status_code == 200 and r.json().get("email") is True,
      f"got {r.status_code}: {r.text[:120]}")
r = client.put("/api/v1/ess/notifications/preferences", headers=H_A,
               json={"sms": True})
check("partial update answers", r.status_code == 200,
      f"got {r.status_code}: {r.text[:160]}")
check("only the supplied flag changed",
      r.json() == {"email": True, "sms": True, "push": True},
      f"got {r.text[:160]}")
r = client.put("/api/v1/ess/notifications/preferences", headers=H_A,
               json={"email": False, "sms": False, "push": False})
check("opt-out stored", r.status_code == 200 and r.json() == {
    "email": False, "sms": False, "push": False}, f"got {r.text[:160]}")
r = client.get("/api/v1/ess/notifications/preferences", headers=H_B)
check("the other caller's flags are untouched by my update",
      r.status_code == 200 and r.json() == {"email": True, "sms": False, "push": True},
      f"got {r.status_code}: {r.text[:160]}")
with SessionLocal() as s:
    mine = (s.query(EmployeeSelfService)
            .filter(EmployeeSelfService.employee_id == EMP_A_ID).first())
    theirs = (s.query(EmployeeSelfService)
              .filter(EmployeeSelfService.employee_id == EMP_B_ID).first())
check("only my profile row exists",
      mine is not None and theirs is None)
r = client.put("/api/v1/ess/notifications/preferences", headers=H_LONELY,
               json={"sms": True})
check("a login with no employee is refused (404)",
      r.status_code == 404, f"got {r.status_code}: {r.text[:120]}")
# Restore the flags so later suites sharing this file's shape are unaffected.
r = client.put("/api/v1/ess/notifications/preferences", headers=H_A,
               json={"email": True, "sms": False, "push": True})
check("flags restore", r.status_code == 200)


# ===========================================================================
print("\n[DEL-10] Reads expose delivery")
# ===========================================================================
r = client.get("/api/v1/ess/notifications", headers=H_A)
rows = r.json() if r.status_code == 200 else []
probe = next((n for n in rows if n.get("entity_id") == 9001), None)
check("the list answers", r.status_code == 200 and bool(rows),
      f"got {r.status_code}: {r.text[:120]}")
check("the list carries delivery tracking",
      probe is not None and probe.get("delivery_status") == "sent"
      and probe.get("delivery_attempts") == 1
      and "delivery_error" in probe,
      f"probe={probe}")
target_id = probe["id"] if probe else None
r = client.put(f"/api/v1/ess/notifications/{target_id}/read", headers=H_A)
check("mark-read answers", r.status_code == 200,
      f"got {r.status_code}: {r.text[:120]}")
check("mark-read carries delivery tracking",
      r.json().get("delivery_status") == "sent"
      and r.json().get("delivery_attempts") == 1,
      f"got {r.text[:160]}")


print("\n" + "=" * 62)
print(f"==== NOTIFICATION DELIVERY SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 62)
raise SystemExit(1 if RESULTS["fail"] else 0)
