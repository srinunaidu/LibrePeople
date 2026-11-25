"""Time corrections and attendance period locks (LP-TIME-004+005).

What this suite proves
----------------------
* an associate files a correction for their own work day, and a manager
  approves it: the entry carries the requested times and the hours are
  recomputed;
* a rejection leaves the entry untouched and records who decided;
* a correction that is no longer pending cannot be decided again;
* role guards hold: an associate cannot approve, a payroll viewer cannot
  file, and a manager cannot decide a correction outside their line;
* a locked period refuses every write inside it (correction create,
  correction approve, clock-in, manual entry create) with the shared
  ``attendance_period_locked`` code, and reopening lets the writes
  through again;
* the lock check is overlap-based: a sub-range inside a lock, and a
  range spanning a lock, both read locked, and a timesheet whose range
  merely spans a lock is refused;
* an approval persists the overwritten clock times into its audit
  details, so the before-snapshot stays reviewable;
* reopening distinguishes a missing lock (404) from an already-open
  period (400);
* the migration creates both tables with the columns and indexes the
  models declare, and its downgrade removes what it created.

Run:  python time_corrections_test_suite.py
"""
import datetime
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="time_corrections_test_suite_"), "time_corrections_test_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"  # keep the suite's output readable
# Field encryption (item 6: no SECRET_KEY fallback) — time writes touch
# employee identity fields through app.core.encryption.
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402

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


# --- the fixtures ------------------------------------------------------------

PASSWORD = "TimeCorrPass123"

db = SessionLocal()
dept = Department(name="Time", code="TIM")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Time Analyst", code="TIMEAN", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def _employee(code: str, manager_id: int | None = None) -> Employee:
    person = Employee(
        employee_id=code,
        first_name="Clock",
        last_name=code,
        email=f"{code.lower()}@example.com",
        hire_date=datetime.date(2024, 1, 1),
        job_id=job.id,
        department_id=dept.id,
        manager_id=manager_id,
        status="Active",
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


emp_manager = _employee("TIME-MGR")
emp_a = _employee("TIME-A", manager_id=emp_manager.id)
emp_b = _employee("TIME-B")


def _user(username: str, role: str, employee_id: int | None = None) -> None:
    db.add(
        User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role=role,
            is_active=True,
            employee_id=employee_id,
            # MFA-enforced world: privileged roles are enrolled, otherwise
            # every call below is refused before the handler runs.
            mfa_enabled=role in ("SuperAdmin", "HR"),
        )
    )
    db.commit()


_user("time_hr", "SuperAdmin")
_user("time_mgr", "Manager", emp_manager.id)
_user("time_assoc", "Associate", emp_a.id)
_user("time_pay", "PayrollViewer")

EMP_MGR_ID = emp_manager.id
EMP_A_ID = emp_a.id
EMP_B_ID = emp_b.id
db.close()

client = TestClient(app, raise_server_exceptions=False)


def _headers(username: str) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


H_HR = _headers("time_hr")
H_MGR = _headers("time_mgr")
H_ASSOC = _headers("time_assoc")
H_PAY = _headers("time_pay")


def _entry(employee_id: int, day: str, clock_in: str, clock_out: str) -> int:
    r = client.post(
        "/api/v1/time/entries",
        headers=H_HR,
        json={
            "employee_id": employee_id,
            "work_date": day,
            "clock_in": f"{day}T{clock_in}:00",
            "clock_out": f"{day}T{clock_out}:00",
        },
    )
    assert r.status_code == 201, f"setup entry failed: {r.status_code} {r.text[:200]}"
    return r.json()["id"]


# ===========================================================================
print("\n[CORRECTION-1] The approval applies the requested times")
# ===========================================================================

ENTRY_ID = _entry(EMP_A_ID, "2026-03-02", "09:00", "17:00")

r = client.post(
    "/api/v1/time/corrections",
    headers=H_ASSOC,
    json={
        "employee_id": EMP_A_ID,
        "time_entry_id": ENTRY_ID,
        "work_date": "2026-03-02",
        "requested_clock_in": "2026-03-02T08:00:00",
        "requested_clock_out": "2026-03-02T18:00:00",
        "reason": "missed the real start",
    },
)
check("an associate files a correction for their own work day", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
CORRECTION_ID = r.json()["id"] if r.status_code == 201 else None
check("the correction is pending", r.json().get("status") == "Pending", f"got {r.json().get('status')}")

r = client.post(f"/api/v1/time/corrections/{CORRECTION_ID}/approve", headers=H_MGR)
check("the manager approves the correction", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
check("the approval records the decision", r.json().get("status") == "Approved", f"got {r.json().get('status')}")

r = client.get(f"/api/v1/time/entries/{ENTRY_ID}", headers=H_HR)
entry = r.json()
check(
    "the entry carries the requested times",
    entry.get("clock_in", "").startswith("2026-03-02T08:00")
    and entry.get("clock_out", "").startswith("2026-03-02T18:00"),
    f"got {entry.get('clock_in')}..{entry.get('clock_out')}",
)
check(
    "the hours are recomputed from the requested times",
    entry.get("worked_hours") == 10.0 and entry.get("overtime_hours") == 2.0,
    f"got {entry.get('worked_hours')}h + {entry.get('overtime_hours')}h OT",
)

# ===========================================================================
print("\n[CORRECTION-2] The rejection leaves the entry alone")
# ===========================================================================

ENTRY_2 = _entry(EMP_A_ID, "2026-03-03", "09:00", "17:00")
r = client.post(
    "/api/v1/time/corrections",
    headers=H_ASSOC,
    json={
        "employee_id": EMP_A_ID,
        "time_entry_id": ENTRY_2,
        "work_date": "2026-03-03",
        "requested_clock_in": "2026-03-03T06:00:00",
        "requested_clock_out": "2026-03-03T22:00:00",
    },
)
REJECT_ID = r.json()["id"] if r.status_code == 201 else None
check("a second correction is filed", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

r = client.post(f"/api/v1/time/corrections/{REJECT_ID}/reject", headers=H_MGR)
check("the correction is rejected", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
check("the rejection records who decided", r.json().get("status") == "Rejected", f"got {r.json().get('status')}")

r = client.get(f"/api/v1/time/entries/{ENTRY_2}", headers=H_HR)
entry2 = r.json()
check(
    "the rejected correction moved nothing on the entry",
    entry2.get("clock_in", "").startswith("2026-03-02") is False
    and entry2.get("worked_hours") == 8.0,
    f"got {entry2.get('clock_in')} / {entry2.get('worked_hours')}h",
)

r = client.post(f"/api/v1/time/corrections/{REJECT_ID}/approve", headers=H_MGR)
check(
    "a correction that is no longer pending cannot be approved",
    r.status_code == 400,
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.post("/api/v1/time/corrections/999999/approve", headers=H_MGR)
check("an unknown correction is not found", r.status_code == 404, f"got {r.status_code}")

# ===========================================================================
print("\n[CORRECTION-3] The role guards")
# ===========================================================================

r = client.post(
    "/api/v1/time/corrections",
    headers=H_PAY,
    json={"employee_id": EMP_A_ID, "work_date": "2026-03-04"},
)
check("a payroll viewer cannot file a correction", r.status_code == 403, f"got {r.status_code}")

r = client.post(
    "/api/v1/time/corrections",
    headers=H_ASSOC,
    json={"employee_id": EMP_A_ID, "work_date": "2026-03-04"},
)
PENDING_ID = r.json()["id"] if r.status_code == 201 else None
check("a correction without times is filed", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

r = client.post(f"/api/v1/time/corrections/{PENDING_ID}/approve", headers=H_ASSOC)
check("an associate cannot approve", r.status_code == 403, f"got {r.status_code}")

r = client.get("/api/v1/time/corrections", headers=H_PAY)
check("a payroll viewer cannot list corrections", r.status_code == 403, f"got {r.status_code}")

r = client.get("/api/v1/time/corrections", headers=H_ASSOC)
check("an associate lists the queue", r.status_code == 200, f"got {r.status_code}")

# A correction for somebody outside the manager's line.
r = client.post(
    "/api/v1/time/corrections",
    headers=H_HR,
    json={"employee_id": EMP_B_ID, "work_date": "2026-03-05"},
)
OUTSIDER_ID = r.json()["id"] if r.status_code == 201 else None
check("hr files for an employee outside the manager's line", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
r = client.post(f"/api/v1/time/corrections/{OUTSIDER_ID}/approve", headers=H_MGR)
check(
    "a manager cannot decide a correction outside their line",
    r.status_code == 403,
    f"got {r.status_code}: {r.text[:200]}",
)

# ===========================================================================
print("\n[LOCK-1] A locked period refuses every write inside it")
# ===========================================================================

r = client.get(
    "/api/v1/time/period-locks/status?period_start=2026-04-01&period_end=2026-04-30",
    headers=H_ASSOC,
)
check("the status is served", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
check("an unlocked period reads open", r.json().get("is_locked") is False, f"got {r.json()}")

r = client.post(
    "/api/v1/time/period-locks/lock",
    headers=H_ASSOC,
    json={"period_start": "2026-04-01", "period_end": "2026-04-30"},
)
check("an associate cannot lock a period", r.status_code == 403, f"got {r.status_code}")

r = client.post(
    "/api/v1/time/period-locks/lock",
    headers=H_HR,
    json={"period_start": "2026-04-30", "period_end": "2026-04-01"},
)
check("a period that ends before it starts is refused", r.status_code == 400, f"got {r.status_code}")

r = client.post(
    "/api/v1/time/period-locks/lock",
    headers=H_HR,
    json={"period_start": "2026-04-01", "period_end": "2026-04-30"},
)
check("hr locks the period", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

r = client.get(
    "/api/v1/time/period-locks/status?period_start=2026-04-01&period_end=2026-04-30",
    headers=H_ASSOC,
)
check("the period now reads locked", r.json().get("is_locked") is True, f"got {r.json()}")

r = client.post(
    "/api/v1/time/corrections",
    headers=H_ASSOC,
    json={"employee_id": EMP_A_ID, "work_date": "2026-04-02"},
)
check(
    "a correction inside a locked period is refused",
    r.status_code == 409,
    f"got {r.status_code}: {r.text[:200]}",
)
check(
    "the refusal carries the shared error code",
    r.json().get("error", {}).get("code") == "attendance_period_locked",
    f"got {r.text[:200]}",
)

r = client.post(
    "/api/v1/time/clock-in",
    headers=H_ASSOC,
    json={"employee_id": EMP_A_ID, "work_date": "2026-04-02"},
)
check(
    "a clock-in inside a locked period is refused",
    r.status_code == 409,
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.post(
    "/api/v1/time/entries",
    headers=H_HR,
    json={
        "employee_id": EMP_A_ID,
        "work_date": "2026-04-03",
        "clock_in": "2026-04-03T09:00:00",
        "clock_out": "2026-04-03T17:00:00",
    },
)
check(
    "a manual entry inside a locked period is refused",
    r.status_code == 409,
    f"got {r.status_code}: {r.text[:200]}",
)

# A pending correction whose work day gets locked cannot be approved either.
r = client.post(
    "/api/v1/time/corrections",
    headers=H_ASSOC,
    json={"employee_id": EMP_A_ID, "work_date": "2026-05-02"},
)
MAY_ID = r.json()["id"] if r.status_code == 201 else None
check("a correction is filed before the lock", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
r = client.post(
    "/api/v1/time/period-locks/lock",
    headers=H_HR,
    json={"period_start": "2026-05-01", "period_end": "2026-05-31"},
)
check("the second period is locked", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
r = client.post(f"/api/v1/time/corrections/{MAY_ID}/approve", headers=H_MGR)
check(
    "approving into a locked period is refused",
    r.status_code == 409,
    f"got {r.status_code}: {r.text[:200]}",
)

# A write outside every locked period still goes through.
r = client.post(
    "/api/v1/time/corrections",
    headers=H_ASSOC,
    json={"employee_id": EMP_A_ID, "work_date": "2026-06-02"},
)
check("a correction outside the locked periods is filed", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

# ===========================================================================
print("\n[LOCK-2] Reopening lets the writes through again")
# ===========================================================================

r = client.post(
    "/api/v1/time/period-locks/reopen",
    headers=H_MGR,
    json={"period_start": "2026-04-01", "period_end": "2026-04-30"},
)
check("a manager cannot reopen a period", r.status_code == 403, f"got {r.status_code}")

r = client.post(
    "/api/v1/time/period-locks/reopen",
    headers=H_HR,
    json={"period_start": "2026-07-01", "period_end": "2026-07-31"},
)
check("reopening a period that was never locked is not found", r.status_code == 404, f"got {r.status_code}")

r = client.post(
    "/api/v1/time/period-locks/reopen",
    headers=H_HR,
    json={"period_start": "2026-04-01", "period_end": "2026-04-30"},
)
check("hr reopens the period", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
check("the reopened row reads unlocked", r.json().get("is_locked") is False, f"got {r.json()}")

r = client.get(
    "/api/v1/time/period-locks/status?period_start=2026-04-01&period_end=2026-04-30",
    headers=H_ASSOC,
)
check("the status reads open again", r.json().get("is_locked") is False, f"got {r.json()}")

r = client.post(
    "/api/v1/time/corrections",
    headers=H_ASSOC,
    json={"employee_id": EMP_A_ID, "work_date": "2026-04-02"},
)
check("a correction in the reopened period is filed", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

# The lock history is kept: locking the same period again reuses the row.
r = client.post(
    "/api/v1/time/period-locks/lock",
    headers=H_HR,
    json={"period_start": "2026-04-01", "period_end": "2026-04-30"},
)
check("the period locks again", r.status_code == 201 and r.json().get("is_locked") is True, f"got {r.status_code}: {r.text[:200]}")

# ===========================================================================
print("\n[LOCK-3] The lock check is overlap-based, not exact-match")
# ===========================================================================

r = client.post(
    "/api/v1/time/period-locks/lock",
    headers=H_HR,
    json={"period_start": "2026-08-10", "period_end": "2026-08-12"},
)
check("hr locks a mid-month sub-range", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")


def _is_locked(start: str, end: str) -> tuple[int, dict]:
    r = client.get(
        f"/api/v1/time/period-locks/status?period_start={start}&period_end={end}",
        headers=H_ASSOC,
    )
    return r.status_code, r.json()


code, body = _is_locked("2026-08-10", "2026-08-12")
check("the exact locked range reads locked", code == 200 and body.get("is_locked") is True, f"got {code}: {body}")

code, body = _is_locked("2026-08-11", "2026-08-11")
check("a single day inside the lock reads locked", code == 200 and body.get("is_locked") is True, f"got {code}: {body}")

code, body = _is_locked("2026-08-01", "2026-08-31")
check("a month spanning the lock reads locked", code == 200 and body.get("is_locked") is True, f"got {code}: {body}")

code, body = _is_locked("2026-08-13", "2026-08-31")
check("a range clear of the lock reads open", code == 200 and body.get("is_locked") is False, f"got {code}: {body}")

r = client.post(
    "/api/v1/time/timesheets/generate",
    headers=H_HR,
    json={"employee_id": EMP_A_ID, "period_start": "2026-08-01", "period_end": "2026-08-31"},
)
check(
    "a timesheet spanning a locked sub-range is refused",
    r.status_code == 409,
    f"got {r.status_code}: {r.text[:200]}",
)
check(
    "the spanning refusal carries the shared error code",
    r.json().get("error", {}).get("code") == "attendance_period_locked",
    f"got {r.text[:200]}",
)

r = client.post(
    "/api/v1/time/timesheets/generate",
    headers=H_HR,
    json={"employee_id": EMP_A_ID, "period_start": "2026-08-13", "period_end": "2026-08-31"},
)
check("a timesheet clear of the lock is generated", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

r = client.post(
    "/api/v1/time/period-locks/reopen",
    headers=H_HR,
    json={"period_start": "2026-08-10", "period_end": "2026-08-12"},
)
check("hr reopens the sub-range", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

r = client.post(
    "/api/v1/time/period-locks/reopen",
    headers=H_HR,
    json={"period_start": "2026-08-10", "period_end": "2026-08-12"},
)
check("reopening an already-open period is refused", r.status_code == 400, f"got {r.status_code}: {r.text[:200]}")

r = client.post(
    "/api/v1/time/timesheets/generate",
    headers=H_HR,
    json={"employee_id": EMP_A_ID, "period_start": "2026-08-01", "period_end": "2026-08-31"},
)
check("the spanning timesheet flows once reopened", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

# ===========================================================================
print("\n[CORRECTION-4] The approval keeps the before-snapshot in audit")
# ===========================================================================

_audit_db = SessionLocal()
_audit_rows = (
    _audit_db.query(AuditLog)
    .filter(
        AuditLog.action == "approve_time_correction",
        AuditLog.entity_type == "TimeCorrectionRequest",
        AuditLog.entity_id == CORRECTION_ID,
    )
    .all()
)
_audit_db.close()
_audit_details = " ".join((row.details or "") for row in _audit_rows)
check(
    "the approval wrote an audit row",
    len(_audit_rows) >= 1,
    f"got {len(_audit_rows)} rows for correction {CORRECTION_ID}",
)
check(
    "the audit details carry the overwritten clock times",
    "before_clock_in" in _audit_details
    and "before_clock_out" in _audit_details
    and "09:00" in _audit_details
    and "17:00" in _audit_details,
    f"got {(_audit_details[:200] or '<empty>')}",
)

# ===========================================================================
print("\n[MIGRATION-1] The migration, and its downgrade")
# ===========================================================================


def _run_migrations(db_path: str, target: str = "head", direction: str = "upgrade") -> None:
    """Run the migration CLI against a specific database.

    The CLI is invoked as a subprocess, so each run starts from a clean
    module state and the operator-facing entry point is what is exercised.
    """
    backend = Path(__file__).resolve().parent
    env = dict(os.environ)
    # Both variables are set: the application reads DATABASE_URL and the
    # migration CLI reads ALEMBIC_DATABASE_URL. Setting only one would let
    # the other win and migrate the wrong database.
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["ALEMBIC_DATABASE_URL"] = f"sqlite:///{db_path}"
    env["SECRET_KEY"] = os.environ["SECRET_KEY"]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.migrate", direction, target],
        cwd=str(backend),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"migration {direction} {target} failed for {db_path}:\n"
            f"{result.stdout}\n{result.stderr}"
        )


def _tables(db_path: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def _columns(db_path: str, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def _indexes(db_path: str, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{table}'"
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


workdir = tempfile.mkdtemp(prefix="karmathy-time-migrations-")
try:
    fresh = os.path.join(workdir, "fresh.db")
    _run_migrations(fresh)

    check(
        "the migration creates the correction table",
        "time_correction_requests" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the migration creates the lock table",
        "attendance_period_locks" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the correction table holds the columns the models declare",
        {
            "id",
            "tenant_id",
            "employee_id",
            "time_entry_id",
            "work_date",
            "requested_clock_in",
            "requested_clock_out",
            "reason",
            "status",
            "requested_by",
            "decided_by",
            "decided_at",
            "created_at",
            "updated_at",
        }
        <= _columns(fresh, "time_correction_requests"),
        f"columns={sorted(_columns(fresh, 'time_correction_requests'))}",
    )
    check(
        "the lock table holds the columns the models declare",
        {
            "id",
            "tenant_id",
            "period_start",
            "period_end",
            "is_locked",
            "locked_by",
            "locked_at",
            "reopened_by",
            "reopened_at",
            "created_at",
        }
        <= _columns(fresh, "attendance_period_locks"),
        f"columns={sorted(_columns(fresh, 'attendance_period_locks'))}",
    )
    check(
        "the correction table holds the indexes the models declare",
        {
            "ix_time_correction_requests_tenant_id",
            "ix_time_correction_requests_employee_id",
            "ix_time_correction_requests_work_date",
        }
        <= _indexes(fresh, "time_correction_requests"),
        f"indexes={sorted(_indexes(fresh, 'time_correction_requests'))}",
    )
    check(
        "the lock table holds the indexes the models declare",
        {
            "ix_attendance_period_locks_tenant_id",
            "ix_attendance_period_locks_period_start",
            "ix_attendance_period_locks_period_end",
        }
        <= _indexes(fresh, "attendance_period_locks"),
        f"indexes={sorted(_indexes(fresh, 'attendance_period_locks'))}",
    )

    _run_migrations(fresh, "0034_pg_foundations", "downgrade")
    check(
        "the downgrade removes the correction table",
        "time_correction_requests" not in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the downgrade removes the lock table",
        "attendance_period_locks" not in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the downgrade leaves the entries alone",
        "time_entries" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    _run_migrations(fresh)
    check(
        "both tables come back",
        {"time_correction_requests", "attendance_period_locks"} <= _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
finally:
    shutil.rmtree(workdir, ignore_errors=True)

# ===========================================================================
print()
print("----------------------------------------------------------------")
print(f"time corrections tests: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("----------------------------------------------------------------")
raise SystemExit(1 if RESULTS["fail"] else 0)
