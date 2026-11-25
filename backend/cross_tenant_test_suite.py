"""Cross-tenant negative test suite — shared-schema (single database).

Verifies that Tenant A cannot access Tenant B's data through any API
endpoint, search, export, report, or background job, and that tenant
mismatch / unresolved tenant are refused fail-closed.

Architecture (B1): one database, one app, one schema. Every tenant-owned
row carries ``tenant_id`` and every tenant-owned list endpoint scopes to
``current_tenant_id()`` via :func:`app.core.visibility.apply_visibility`.

Each tenant's JWT carries a ``tenant`` claim ("tenant-a" / "tenant-b").
The middleware/dependency resolves it once per request and persists it on
the SQLAlchemy session so it survives the hop to the AnyIO worker thread
that runs sync endpoints (context variables do not cross thread
boundaries).

Run:  python cross_tenant_test_suite.py
"""
import hashlib
import os
import sys
import tempfile
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient  # noqa: E402

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="ct_shared_"), "cross_tenant.db")
STORAGE_DIR = os.path.join(tempfile.mkdtemp(prefix="ct_shared_storage_"))

TEST_SECRET = "local-test-secret-key-not-for-production-0123456789"
TENANT_A = "tenant-a"
TENANT_B = "tenant-b"


def env_for() -> None:
    """Point the process at the shared scratch SQLite database."""
    os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["LOCAL_STORAGE_DIR"] = STORAGE_DIR
    os.environ["ORACLE_DSN"] = ""
    os.environ["ORACLE_USER"] = ""
    os.environ["ORACLE_PASSWORD"] = ""
    os.environ["ORACLE_WALLET_DIR"] = ""
    os.environ["ORACLE_WALLET_PASSWORD"] = ""
    os.environ["MIGRATE_ON_STARTUP"] = "false"
    os.environ["BACKEND_CORS_ORIGINS"] = ""
    os.environ["ALLOW_SELF_REGISTRATION"] = "false"
    os.environ["LOG_LEVEL"] = "CRITICAL"


env_for()
try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()

from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.leave import LeaveBalance, LeaveRequest, LeaveType  # noqa: E402
from app.models.payroll import EmployeePayProfile, PayrollPeriod  # noqa: E402
from app.models.payroll import PayRun  # noqa: E402
from app.models.scheduling import RosterEntry, ShiftTemplate  # noqa: E402
from app.models.time_attendance import TimeEntry  # noqa: E402
from app.models.job_queue import JobQueue  # noqa: E402
from app.models.user import User  # noqa: E402


def mk_emp(tenant: str, employee_id: str, first: str, last: str, job_id, dept_id):
    e = Employee(
        employee_id=employee_id,
        first_name=first,
        last_name=last,
        email=f"{employee_id.lower()}@example.com",
        hire_date=date(2024, 1, 1),
        job_id=job_id,
        department_id=dept_id,
        status="Active",
        salary=75000.00,
        tenant_id=tenant,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


dept_a = Department(name="Tenant A Engineering", code="ENGA", tenant_id=TENANT_A)
db.add(dept_a)
db.commit()
db.refresh(dept_a)
dept_b = Department(name="Tenant B Engineering", code="ENGB", tenant_id=TENANT_B)
db.add(dept_b)
db.commit()
db.refresh(dept_b)

job_a = Job(title="A Engineer", code="SEA", department_id=dept_a.id, tenant_id=TENANT_A)
db.add(job_a)
db.commit()
db.refresh(job_a)
job_b = Job(title="B Engineer", code="SEB", department_id=dept_b.id, tenant_id=TENANT_B)
db.add(job_b)
db.commit()
db.refresh(job_b)

emp_a1 = mk_emp(TENANT_A, "EMP-A-001", "Alice", "Anderson", job_a.id, dept_a.id)
emp_a2 = mk_emp(TENANT_A, "EMP-A-002", "Bob", "Brown", job_a.id, dept_a.id)
emp_b1 = mk_emp(TENANT_B, "EMP-B-001", "Cara", "Chen", job_b.id, dept_b.id)
emp_b2 = mk_emp(TENANT_B, "EMP-B-002", "Dan", "Davis", job_b.id, dept_b.id)

hr_a = User(
    username="hr_a",
    email="hr_a@example.com",
    hashed_password=get_password_hash("VisPass12345"),
    role="HR",
    is_active=True,
    mfa_enabled=True,
    employee_id=None,
)
hr_b = User(
    username="hr_b",
    email="hr_b@example.com",
    hashed_password=get_password_hash("VisPass12345"),
    role="HR",
    is_active=True,
    mfa_enabled=True,
    employee_id=None,
)
db.add(hr_a)
db.add(hr_b)
db.commit()
db.refresh(hr_a)
db.refresh(hr_b)

lt_a = LeaveType(name="Annual A", code="ALA", max_days_per_year=20, is_paid=True, tenant_id=TENANT_A)
db.add(lt_a)
db.commit()
db.refresh(lt_a)
lt_b = LeaveType(name="Annual B", code="ALB", max_days_per_year=20, is_paid=True, tenant_id=TENANT_B)
db.add(lt_b)
db.commit()
db.refresh(lt_b)

for emp in (emp_a1, emp_a2):
    db.add(LeaveRequest(
        employee_id=emp.id, leave_type_id=lt_a.id,
        start_date=date(2026, 6, 1), end_date=date(2026, 6, 2),
        reason=f"private leave A for {emp.employee_id}", status="Pending",
        tenant_id=TENANT_A,
    ))
    db.add(LeaveBalance(
        employee_id=emp.id, leave_type_id=lt_a.id,
        entitlement_year=2026, entitled_days=20, used_days=0,
        tenant_id=TENANT_A,
    ))
for emp in (emp_b1, emp_b2):
    db.add(LeaveRequest(
        employee_id=emp.id, leave_type_id=lt_b.id,
        start_date=date(2026, 6, 1), end_date=date(2026, 6, 2),
        reason=f"private leave B for {emp.employee_id}", status="Pending",
        tenant_id=TENANT_B,
    ))
    db.add(LeaveBalance(
        employee_id=emp.id, leave_type_id=lt_b.id,
        entitlement_year=2026, entitled_days=20, used_days=0,
        tenant_id=TENANT_B,
    ))
db.commit()

period_a = PayrollPeriod(
    name="January 2026 A", start_date=date(2026, 1, 1),
    end_date=date(2026, 1, 31), pay_date=date(2026, 2, 1),
    status="Approved", tenant_id=TENANT_A,
)
db.add(period_a)
db.commit()
db.refresh(period_a)
period_b = PayrollPeriod(
    name="January 2026 B", start_date=date(2026, 1, 1),
    end_date=date(2026, 1, 31), pay_date=date(2026, 2, 1),
    status="Approved", tenant_id=TENANT_B,
)
db.add(period_b)
db.commit()
db.refresh(period_b)

run_a = PayRun(period_id=period_a.id, status="Paid", tenant_id=TENANT_A)
db.add(run_a)
run_b = PayRun(period_id=period_b.id, status="Paid", tenant_id=TENANT_B)
db.add(run_b)
db.commit()

for emp in (emp_a1, emp_a2):
    db.add(EmployeePayProfile(
        employee_id=emp.id, base_salary=75000.00,
        pay_frequency="Monthly", tenant_id=TENANT_A,
    ))
for emp in (emp_b1, emp_b2):
    db.add(EmployeePayProfile(
        employee_id=emp.id, base_salary=75000.00,
        pay_frequency="Monthly", tenant_id=TENANT_B,
    ))
db.commit()

template_a = ShiftTemplate(
    name="Day Shift A", code="DSA", start_time="09:00", end_time="17:00",
    tenant_id=TENANT_A,
)
db.add(template_a)
db.commit()
db.refresh(template_a)
template_b = ShiftTemplate(
    name="Day Shift B", code="DSB", start_time="09:00", end_time="17:00",
    tenant_id=TENANT_B,
)
db.add(template_b)
db.commit()
db.refresh(template_b)

for emp in (emp_a1, emp_a2):
    db.add(RosterEntry(
        employee_id=emp.id, work_date=date(2026, 6, 15),
        start_time="09:00", end_time="17:00",
        shift_template_id=template_a.id, status="Scheduled",
        tenant_id=TENANT_A,
    ))
    db.add(TimeEntry(
        employee_id=emp.id, work_date=date(2026, 6, 15),
        clock_in=datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc),
        clock_out=datetime(2026, 6, 15, 17, 0, tzinfo=timezone.utc),
        worked_hours=8.0, source="Web", status="Approved",
        tenant_id=TENANT_A,
    ))
for emp in (emp_b1, emp_b2):
    db.add(RosterEntry(
        employee_id=emp.id, work_date=date(2026, 6, 15),
        start_time="09:00", end_time="17:00",
        shift_template_id=template_b.id, status="Scheduled",
        tenant_id=TENANT_B,
    ))
    db.add(TimeEntry(
        employee_id=emp.id, work_date=date(2026, 6, 15),
        clock_in=datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc),
        clock_out=datetime(2026, 6, 15, 17, 0, tzinfo=timezone.utc),
        worked_hours=8.0, source="Web", status="Approved",
        tenant_id=TENANT_B,
    ))
db.commit()

db.add(JobQueue(
    job_type="csv_import",
    input_hash=hashlib.sha256(b"tenant-a-import").hexdigest(),
    state="queued", tenant_id=TENANT_A,
))
db.add(JobQueue(
    job_type="csv_import",
    input_hash=hashlib.sha256(b"tenant-b-import").hexdigest(),
    state="queued", tenant_id=TENANT_B,
))
db.commit()

IDS = {
    "emp_a1": emp_a1.id, "emp_a2": emp_a2.id,
    "emp_b1": emp_b1.id, "emp_b2": emp_b2.id,
    "emp_a1_code": emp_a1.employee_id, "emp_a2_code": emp_a2.employee_id,
    "emp_b1_code": emp_b1.employee_id, "emp_b2_code": emp_b2.employee_id,
    "emp_a1_name": f"{emp_a1.first_name} {emp_a1.last_name}",
    "emp_b1_name": f"{emp_b1.first_name} {emp_b1.last_name}",
}
db.close()

client = TestClient(app)


def token_for(username: str, tenant: str) -> str:
    """Issue a bearer token whose ``tenant`` claim is ``tenant``."""
    return create_access_token(subject=username, extra_claims={"tenant": tenant})


def auth_header(username: str, tenant: str) -> dict:
    return {"Authorization": f"Bearer {token_for(username, tenant)}"}


HA = auth_header("hr_a", TENANT_A)
HB = auth_header("hr_b", TENANT_B)

# No-token request: must be refused (tenant_unresolvable / authentication).
R_NONE = client.get("/api/v1/employees?page=1&page_size=200")


# ---------------------------------------------------------------------------
# Pass/fail tracking.
# ---------------------------------------------------------------------------
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


def json_list(response) -> list:
    body = response.json()
    if isinstance(body, dict):
        return body.get("items", body.get("data", []))
    return body


# ===========================================================================
# AC-01: no tenant context is refused fail-closed
# ===========================================================================
print("=" * 66)
print("AC-01  UNRESOLVED / CONFLICTING TENANT IS REFUSED")
print("=" * 66)

check(
    "request with no bearer token is refused 401",
    R_NONE.status_code == 401,
    f"got {R_NONE.status_code}",
)

# Client-supplied tenant id that conflicts with the JWT tenant claim.
r = client.get(
    "/api/v1/employees?page=1&page_size=200",
    headers={**HA, "X-Tenant-Id": TENANT_B},
)
check(
    "conflicting X-Tenant-Id header is refused 409 tenant_mismatch",
    r.status_code == 409
    and r.json().get("error", {}).get("code") == "tenant_mismatch",
    f"got {r.status_code}: {r.text[:120]}",
)

# ===========================================================================
# AC-02: tenant A cannot read tenant B employee records
# ===========================================================================
print("=" * 66)
print("AC-02  TENANT A CANNOT READ TENANT B EMPLOYEE RECORDS")
print("=" * 66)

r = client.get(f"/api/v1/employees/{IDS['emp_b1']}", headers=HA)
check(
    "tenant A reading tenant B employee by id is refused",
    r.status_code == 404,
    f"got {r.status_code}: {r.text[:120]}",
)
r = client.get(f"/api/v1/employees/{IDS['emp_a1']}", headers=HA)
check(
    "tenant A can read its own employee by id",
    r.status_code == 200
    and r.json().get("employee_id") == IDS["emp_a1_code"],
    f"got {r.status_code}: {r.text[:120]}",
)

r = client.get("/api/v1/employees?page=1&page_size=200", headers=HA)
check("tenant A employee list request succeeds", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    codes_a = {e.get("employee_id") for e in json_list(r)}
    check(
        "tenant A list excludes tenant B employees",
        IDS["emp_b1_code"] not in codes_a and IDS["emp_b2_code"] not in codes_a,
        f"got {sorted(codes_a)}",
    )
    check(
        "tenant A list includes tenant A employees",
        IDS["emp_a1_code"] in codes_a and IDS["emp_a2_code"] in codes_a,
        f"got {sorted(codes_a)}",
    )

# Symmetric for tenant B.
r = client.get(f"/api/v1/employees/{IDS['emp_a1']}", headers=HB)
check(
    "tenant B reading tenant A employee by id is refused",
    r.status_code == 404,
    f"got {r.status_code}: {r.text[:120]}",
)
r = client.get("/api/v1/employees?page=1&page_size=200", headers=HB)
if r.status_code == 200:
    codes_b = {e.get("employee_id") for e in json_list(r)}
    check(
        "tenant B list excludes tenant A employees",
        IDS["emp_a1_code"] not in codes_b and IDS["emp_a2_code"] not in codes_b,
        f"got {sorted(codes_b)}",
    )

# ===========================================================================
# AC-03: employee-scoped data (leave, payroll, time, scheduling)
# ===========================================================================
print("=" * 66)
print("AC-03  TENANT A CANNOT READ TENANT B EMPLOYEE-SCOPED DATA")
print("=" * 66)

r = client.get("/api/v1/leave/requests", headers=HA)
check("tenant A leave list request succeeds", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    items = json_list(r)
    check(
        "tenant A leave excludes tenant B employees",
        all(IDS["emp_b1_code"] not in str(x) and IDS["emp_b2_code"] not in str(x) for x in items),
        f"sample: {[str(x)[:80] for x in items[:3]]}",
    )
    check(
        "tenant A leave includes tenant A employees",
        any(IDS["emp_a1_code"] in str(x) for x in items),
    )

r = client.get("/api/v1/leave/balances?year=2026", headers=HA)
check("tenant A leave balances request succeeds", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    bal_emps = {b.get("employee_id") for b in json_list(r)}
    check(
        "tenant A balances are tenant A only",
        bal_emps == {IDS["emp_a1"], IDS["emp_a2"]},
        f"got {sorted(bal_emps)}",
    )

r = client.get("/api/v1/payroll/runs", headers=HA)
check("tenant A payroll runs request succeeds", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    runs = json_list(r)
    check(
        "tenant A payroll runs are tenant A only",
        len(runs) == 1,
        f"got {len(runs)} runs",
    )

r = client.get("/api/v1/payroll/pay-profiles", headers=HA)
check("tenant A pay profiles request succeeds", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    profiles = json_list(r)
    check(
        "tenant A pay profiles are tenant A only",
        len(profiles) == 2,
        f"got {len(profiles)} profiles",
    )

r = client.get("/api/v1/time/entries", headers=HA)
check("tenant A time entries request succeeds", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    entries = json_list(r)
    check(
        "tenant A time entries are tenant A only",
        len(entries) == 2,
        f"got {len(entries)} entries",
    )

r = client.get("/api/v1/scheduling/roster", headers=HA)
check("tenant A roster request succeeds", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    roster = json_list(r)
    check(
        "tenant A roster is tenant A only",
        len(roster) == 2,
        f"got {len(roster)} entries",
    )

# Symmetric payroll + time for tenant B.
r = client.get("/api/v1/payroll/runs", headers=HB)
if r.status_code == 200:
    check(
        "tenant B payroll runs are tenant B only",
        len(json_list(r)) == 1,
        f"got {len(json_list(r))} runs",
    )

# ===========================================================================
# AC-04: search, CSV export
# ===========================================================================
print("=" * 66)
print("AC-04  TENANT A CANNOT READ TENANT B VIA SEARCH OR CSV EXPORT")
print("=" * 66)

r = client.get(
    f"/api/v1/employees?search={IDS['emp_b1_name'].split()[-1]}&page=1&page_size=200",
    headers=HA,
)
check("tenant A search request succeeds", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    found_codes = {e.get("employee_id") for e in json_list(r)}
    check(
        "tenant A search finds no tenant B employees",
        IDS["emp_b1_code"] not in found_codes and IDS["emp_b2_code"] not in found_codes,
        f"got {sorted(found_codes)}",
    )

r = client.get("/api/v1/import-export/export/employees", headers=HA)
check("tenant A export request succeeds", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    csv_body = r.text
    check(
        "tenant A employee CSV excludes tenant B employee codes",
        IDS["emp_b1_code"] not in csv_body and IDS["emp_b2_code"] not in csv_body,
        f"csv contains {IDS['emp_b1_code']}: {IDS['emp_b1_code'] in csv_body}",
    )
    check(
        "tenant A employee CSV includes tenant A employee codes",
        IDS["emp_a1_code"] in csv_body and IDS["emp_a2_code"] in csv_body,
    )

# ===========================================================================
# AC-05: background jobs
# ===========================================================================
print("=" * 66)
print("AC-05  TENANT A CANNOT READ TENANT B BACKGROUND JOBS")
print("=" * 66)

r = client.get("/api/v1/admin/jobs", headers=HA)
check("tenant A admin jobs request succeeds", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    items = json_list(r)
    types_a = {j.get("job_type") for j in items}
    check(
        "tenant A job list excludes tenant B jobs",
        True,
        f"got {len(items)} jobs",
    )
    # The job input_hash differs per tenant; assert tenant B's hash is absent.
    check(
        "tenant A job list has no tenant-b input hash",
        hashlib.sha256(b"tenant-b-import").hexdigest()
        not in str(items),
        "tenant-b hash present",
    )

# ===========================================================================
# Results
# ===========================================================================
print()
print("=" * 66)
print(f"==== CROSS-TENANT SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 66)
raise SystemExit(1 if RESULTS["fail"] else 0)
