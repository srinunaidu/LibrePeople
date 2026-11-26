"""Working time violation reads (LP-TIME violations surface).

What this suite proves
----------------------
* GET /time/violations lists within the caller's visibility: an associate
  sees only their own rows, a manager sees their reporting line, HR sees all;
* the list is filterable by employee_id and by work-date range;
* GET /time/violations/{id} returns the row for a visible employee and 404
  for an out-of-scope employee's row (same convention as the other time
  reads: 404 rather than 403, so the record's existence is not confirmed);
* an unknown id is 404, and anonymous callers are refused with 401.

Run:  python time_violations_test_suite.py
"""
import datetime
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="time_violations_test_suite_"), "time_violations_test_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"  # keep the suite's output readable
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
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.time_attendance import (  # noqa: E402
    ViolationKind,
    ViolationSeverity,
    WorkingTimeViolation,
)
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

PASSWORD = "TimeViolPass123"

db = SessionLocal()
dept = Department(name="TimeViol", code="TVI")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="TimeViol Analyst", code="TIMEVIOL", department_id=dept.id)
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


emp_manager = _employee("TVI-MGR")
emp_a = _employee("TVI-A", manager_id=emp_manager.id)
emp_b = _employee("TVI-B")


def _violation(employee_id: int, day: datetime.date) -> WorkingTimeViolation:
    row = WorkingTimeViolation(
        employee_id=employee_id,
        work_date=day,
        kind=ViolationKind.LATE_ARRIVAL,
        severity=ViolationSeverity.WARNING,
        minutes=12,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


viol_a1 = _violation(emp_a.id, datetime.date(2026, 11, 3))
viol_a2 = _violation(emp_a.id, datetime.date(2026, 11, 10))
viol_b1 = _violation(emp_b.id, datetime.date(2026, 11, 3))


def _user(username: str, role: str, employee_id: int | None = None) -> None:
    db.add(
        User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role=role,
            is_active=True,
            employee_id=employee_id,
            mfa_enabled=role in ("SuperAdmin", "HR"),
        )
    )
    db.commit()


_user("tvi_hr", "SuperAdmin")
_user("tvi_mgr", "Manager", emp_manager.id)
_user("tvi_assoc", "Associate", emp_a.id)

EMP_A_ID = emp_a.id
EMP_B_ID = emp_b.id
VIOL_A1 = viol_a1.id
VIOL_B1 = viol_b1.id
db.close()

client = TestClient(app, raise_server_exceptions=False)


def _headers(username: str) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


H_HR = _headers("tvi_hr")
H_MGR = _headers("tvi_mgr")
H_ASSOC = _headers("tvi_assoc")

LIST = "/api/v1/time/violations"

# ===========================================================================
print("\n[VIOL-1] List scoping: own vs others vs HR")
# ===========================================================================
r = client.get(LIST, headers=H_ASSOC)
check("associate lists only their own rows", r.status_code == 200 and {v["employee_id"] for v in r.json()} == {EMP_A_ID}, f"{r.status_code} {r.text[:200]}")
check("associate sees both of their rows", r.status_code == 200 and len(r.json()) == 2, f"{r.status_code} {r.text[:200]}")

r = client.get(LIST, headers=H_MGR)
ids = {v["employee_id"] for v in r.json()} if r.status_code == 200 else set()
check("manager sees the reporting line, not the outsider", r.status_code == 200 and EMP_A_ID in ids and EMP_B_ID not in ids, f"{r.status_code} {r.text[:200]}")

r = client.get(LIST, headers=H_HR)
all_ids = {v["employee_id"] for v in r.json()} if r.status_code == 200 else set()
check("HR sees every row", r.status_code == 200 and len(r.json()) == 3 and all_ids == {EMP_A_ID, EMP_B_ID}, f"{r.status_code} {r.text[:200]}")

# ===========================================================================
print("\n[VIOL-2] Filters: employee_id and work-date range")
# ===========================================================================
r = client.get(LIST, headers=H_HR, params={"employee_id": EMP_A_ID})
check("HR filters by employee", r.status_code == 200 and len(r.json()) == 2, f"{r.status_code} {r.text[:200]}")

r = client.get(LIST, headers=H_HR, params={"start": "2026-11-10", "end": "2026-11-10"})
got = r.json() if r.status_code == 200 else []
check("date range narrows to one day", r.status_code == 200 and len(got) == 1 and got[0]["work_date"] == "2026-11-10", f"{r.status_code} {r.text[:200]}")

r = client.get(LIST, headers=H_ASSOC, params={"employee_id": EMP_B_ID})
check("associate filtering by an outsider gets 404, not the rows", r.status_code == 404, f"{r.status_code} {r.text[:200]}")

# ===========================================================================
print("\n[VIOL-3] Single read: visible 200, out-of-scope 404, unknown 404")
# ===========================================================================
r = client.get(f"{LIST}/{VIOL_A1}", headers=H_ASSOC)
check("associate reads their own violation", r.status_code == 200 and r.json()["id"] == VIOL_A1, f"{r.status_code} {r.text[:200]}")

r = client.get(f"{LIST}/{VIOL_B1}", headers=H_ASSOC)
check("associate reading an outsider's violation gets 404", r.status_code == 404, f"{r.status_code} {r.text[:200]}")

r = client.get(f"{LIST}/{VIOL_B1}", headers=H_MGR)
check("manager outside the line gets 404 for the row", r.status_code == 404, f"{r.status_code} {r.text[:200]}")

r = client.get(f"{LIST}/{VIOL_B1}", headers=H_HR)
check("HR reads any violation", r.status_code == 200 and r.json()["id"] == VIOL_B1, f"{r.status_code} {r.text[:200]}")

r = client.get(f"{LIST}/999999", headers=H_HR)
check("unknown id is 404", r.status_code == 404, f"{r.status_code} {r.text[:200]}")

r = client.get(LIST)
check("anonymous list is refused", r.status_code in (401, 403), f"{r.status_code} {r.text[:200]}")

r = client.get(f"{LIST}/{VIOL_A1}")
check("anonymous single read is refused", r.status_code in (401, 403), f"{r.status_code} {r.text[:200]}")

# ===========================================================================
print()
print("----------------------------------------------------------------")
print(f"time violations tests: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("----------------------------------------------------------------")
raise SystemExit(1 if RESULTS["fail"] else 0)
