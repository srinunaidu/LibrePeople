"""ESS hub contract tests.

Covers the employee self-service surface completed by the karmathy-ess-hub
feature: own profile/employment view, own payslips, leave request flow and
balances, own documents, announcement audience filtering, RBAC and the
structured error envelope.

Run:  python ess_hub_test_suite.py
"""
import datetime
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="ess_hub_test_"), "ess_hub_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
# The deployed backend/.env names an Oracle DSN, which database.py prefers
# over DATABASE_URL. Override it to empty so this suite runs on SQLite.
for _oracle_var in (
    "ORACLE_DSN",
    "ORACLE_WALLET_DIR",
    "ORACLE_USER",
    "ORACLE_PASSWORD",
    "ORACLE_WALLET_PASSWORD",
):
    os.environ[_oracle_var] = ""

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from decimal import Decimal  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.ess_hr import Announcement, EmployeeDirectory, EmployeeFile, EmployeeSelfService  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.leave import LeaveBalance, LeaveRequest, LeaveType  # noqa: E402
from app.models.payroll import PayRun, PaySlip, PayrollPeriod  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

PASSWORD = "EssHubPass123"
YEAR = 2026

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


# --- fixtures ---------------------------------------------------------------

db = SessionLocal()

dept_eng = Department(name="Engineering", code="ENG")
dept_sales = Department(name="Sales", code="SAL")
db.add_all([dept_eng, dept_sales])
db.commit()
db.refresh(dept_eng)
db.refresh(dept_sales)

job_dev = Job(title="Developer", code="DEV", department_id=dept_eng.id)
job_sales = Job(title="Sales Rep", code="SREP", department_id=dept_sales.id)
db.add_all([job_dev, job_sales])
db.commit()
db.refresh(job_dev)
db.refresh(job_sales)


def _employee(code: str, department, job, manager=None, status="Active"):
    emp = (
        db.query(Employee).filter(Employee.employee_id == code).first()
    )
    if emp:
        return emp
    emp = Employee(
        employee_id=code,
        first_name="Ess",
        last_name=code,
        email=f"{code.lower()}@example.com",
        hire_date=datetime.date(2024, 1, 1),
        job_id=job.id,
        department_id=department.id,
        manager_id=manager.id if manager else None,
        status=status,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


mgr_emp = _employee("ESS-MGR", dept_eng, job_dev)
assoc_emp = _employee("ESS-ASSOC", dept_eng, job_dev, manager=mgr_emp)
other_emp = _employee("ESS-OTHER", dept_sales, job_sales)

# Capture plain ids while the session is still open: commit expires ORM
# attributes, and we close this session before the API calls begin.
ASSOC_EMP_ID = assoc_emp.id
OTHER_EMP_ID = other_emp.id
MGR_EMP_ID = mgr_emp.id


def _user(username: str, role: str, employee_id: int | None) -> int:
    u = (
        db.query(User).filter(User.username == username).first()
    )
    if u:
        return u.id
    u = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash(PASSWORD),
        role=role,
        is_active=True,
        employee_id=employee_id,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u.id


mgr_user_id = _user("ess_mgr", "Manager", MGR_EMP_ID)
assoc_user_id = _user("ess_assoc", "Associate", ASSOC_EMP_ID)
hr_user_id = _user("ess_hr", "HR", OTHER_EMP_ID)
super_user_id = _user("ess_super", "SuperAdmin", None)
db.close()

client = TestClient(app)


def _headers(username: str) -> dict:
    r = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    assert r.status_code == 200, f"login {username}: {r.status_code} {r.text[:120]}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


H_ASSOC = _headers("ess_assoc")
H_MGR = _headers("ess_mgr")
H_HR = _headers("ess_hr")
H_SUPER = _headers("ess_super")


def _error_envelope(response) -> bool:
    """True when the body is the shared structured failure envelope."""
    try:
        body = response.json()
    except ValueError:
        return False
    error = body.get("error") if isinstance(body, dict) else None
    return isinstance(error, dict) and "code" in error and "message" in error


# ===========================================================================
print("\n[ESS-01] Own profile / employment view (AC-01)")
# ===========================================================================

db2 = SessionLocal()
db2.add(
    EmployeeSelfService(
        employee_id=ASSOC_EMP_ID,
        preferred_name="Essie",
        language="en",
    )
)
# Directory rows give employment status / department / job / manager for self.
db2.add_all(
    [
        EmployeeDirectory(
            employee_id=ASSOC_EMP_ID,
            full_name="Ess ESS-ASSOC",
            email="ess-assoc@example.com",
            department="Engineering",
            job_title="Developer",
            is_active=True,
        ),
        EmployeeDirectory(
            employee_id=OTHER_EMP_ID,
            full_name="Ess ESS-OTHER",
            email="ess-other@example.com",
            department="Sales",
            job_title="Sales Rep",
            is_active=True,
        ),
    ]
)
db2.commit()
db2.close()

r = client.get(f"/api/v1/ess/ess/profile/{ASSOC_EMP_ID}", headers=H_ASSOC)
check("associate reads own ESS profile", r.status_code == 200, f"got {r.status_code}: {r.text[:120]}")
if r.status_code == 200:
    check("own profile carries employee_id", r.json().get("employee_id") == ASSOC_EMP_ID)

# Cross-employee profile is refused.
r = client.get(f"/api/v1/ess/ess/profile/{OTHER_EMP_ID}", headers=H_ASSOC)
check(
    "associate cannot read another employee's profile",
    r.status_code in (403, 404),
    f"got {r.status_code}: {r.text[:120]}",
)

# Directory row gives employment status / department / job / manager for self.
r = client.get("/api/v1/ess/directory", headers=H_ASSOC)
check(
    "directory is readable by the associate",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)
if r.status_code == 200:
    me = next((d for d in r.json() if d.get("employee_id") == ASSOC_EMP_ID), None)
    check(
        "directory entry shows department/job for self",
        me is not None
        and me.get("department") == "Engineering"
        and me.get("job_title") == "Developer",
        f"me={me}",
    )


# ===========================================================================
print("\n[ESS-02] Payslip viewing (AC-02)")
# ===========================================================================

db3 = SessionLocal()
period = PayrollPeriod(
    name="March 2026",
    start_date=datetime.date(2026, 3, 1),
    end_date=datetime.date(2026, 3, 31),
    pay_date=datetime.date(2026, 4, 5),
    status="Approved",
)
db3.add(period)
db3.commit()
db3.refresh(period)

run = PayRun(period_id=period.id, jurisdiction="US", currency="USD", status="Finalized")
db3.add(run)
db3.commit()
db3.refresh(run)

slip_self = PaySlip(
    pay_run_id=run.id,
    employee_id=ASSOC_EMP_ID,
    gross_pay=Decimal("6000.00"),
    total_deductions=Decimal("800.00"),
    net_pay=Decimal("5200.00"),
    currency="USD",
    status="Final",
)
slip_other = PaySlip(
    pay_run_id=run.id,
    employee_id=OTHER_EMP_ID,
    gross_pay=Decimal("4000.00"),
    total_deductions=Decimal("600.00"),
    net_pay=Decimal("3400.00"),
    currency="USD",
    status="Final",
)
db3.add_all([slip_self, slip_other])
db3.commit()
db3.close()

r = client.get(f"/api/v1/payroll/payslips?employee_id={ASSOC_EMP_ID}", headers=H_ASSOC)
check(
    "associate reads own payslip",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)
if r.status_code == 200:
    slips = r.json()
    own = [s for s in slips if s.get("employee_id") == ASSOC_EMP_ID]
    check(
        "own payslip carries gross/deductions/net/pay date/period fields",
        len(own) >= 1
        and "gross_pay" in own[0]
        and "total_deductions" in own[0]
        and "net_pay" in own[0]
        and "pay_run_id" in own[0],
        f"own={own[:1]}",
    )
    check(
        "own payslip net = gross - deductions",
        abs((own[0]["gross_pay"] - own[0]["total_deductions"]) - own[0]["net_pay"]) < 0.01,
        f"slip={own[0]}",
    )

# Cross-employee payslip is refused.
r = client.get(f"/api/v1/payroll/payslips?employee_id={OTHER_EMP_ID}", headers=H_ASSOC)
check(
    "associate cannot read another employee's payslip",
    r.status_code in (403, 404),
    f"got {r.status_code}: {r.text[:120]}",
)

# Unfiltered list is visibility-scoped to self for an associate.
r = client.get("/api/v1/payroll/payslips", headers=H_ASSOC)
check(
    "unfiltered payslip list is scoped to self",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)
if r.status_code == 200:
    check(
        "unfiltered list contains only own slips",
        all(s.get("employee_id") == ASSOC_EMP_ID for s in r.json()),
        f"ids={[s.get('employee_id') for s in r.json()]}",
    )


# ===========================================================================
print("\n[ESS-03] Leave request flow (AC-03)")
# ===========================================================================

db4 = SessionLocal()
from app.models.leave import LeaveLedgerEntryType  # noqa: E402
from app.services import leave as ledger  # noqa: E402
lt_annual = LeaveType(name="Annual Leave", code="AL", is_paid=True, max_days_per_year=20)
db4.add(lt_annual)
db4.commit()
db4.refresh(lt_annual)
LT_ANNUAL_ID = lt_annual.id

# A balance so an approval can be decided against it, with a ledger
# entitlement row so the derived available balance is non-zero.
bal = LeaveBalance(
    employee_id=ASSOC_EMP_ID,
    leave_type_id=LT_ANNUAL_ID,
    entitlement_year=YEAR,
    entitled_days=Decimal("20"),
    carried_over_days=Decimal("0"),
    used_days=Decimal("0"),
)
db4.add(bal)
db4.flush()
db4.refresh(bal)
ledger.post_entry(
    db4,
    bal,
    LeaveLedgerEntryType.ENTITLEMENT,
    Decimal("20"),
    reference_type="entitlement",
    reference_id=None,
    description="Entitlement for AL in 2026",
)
db4.commit()
db4.close()

r = client.post(
    "/api/v1/leave/requests",
    headers=H_ASSOC,
    json={
        "employee_id": ASSOC_EMP_ID,
        "leave_type_id": LT_ANNUAL_ID,
        "start_date": "2026-06-01",
        "end_date": "2026-06-03",
        "reason": "Personal leave",
    },
)
check(
    "associate submits a leave request",
    r.status_code in (200, 201),
    f"got {r.status_code}: {r.text[:160]}",
)
req_id = None
if r.status_code in (200, 201):
    req_id = r.json().get("id")
    check("request is created in Pending state", r.json().get("status") == "Pending")

# The employee sees their request status.
r = client.get(f"/api/v1/leave/requests?employee_id={ASSOC_EMP_ID}", headers=H_ASSOC)
check(
    "associate lists their own leave requests",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)
if r.status_code == 200 and req_id is not None:
    mine = [x for x in r.json() if x.get("id") == req_id]
    check(
        "own request shows Pending status",
        len(mine) == 1 and mine[0].get("status") == "Pending",
        f"mine={mine}",
    )

# Manager approves; employee sees the decision.
if req_id is not None:
    r = client.post(f"/api/v1/leave/requests/{req_id}/approve", headers=H_MGR)
    check(
        "manager can approve the reporttee's request",
        r.status_code == 200,
        f"got {r.status_code}: {r.text[:160]}",
    )
    if r.status_code == 200:
        check("request moves to Approved", r.json().get("status") == "Approved")
        r = client.get(f"/api/v1/leave/requests?employee_id={ASSOC_EMP_ID}", headers=H_ASSOC)
        mine = [x for x in r.json() if x.get("id") == req_id]
        check(
            "employee sees the Approved decision",
            len(mine) == 1 and mine[0].get("status") == "Approved",
            f"mine={mine}",
        )


# ===========================================================================
print("\n[ESS-04] Leave balances (AC-04)")
# ===========================================================================

r = client.get(f"/api/v1/leave/balances?employee_id={ASSOC_EMP_ID}&year={YEAR}", headers=H_ASSOC)
check(
    "associate reads own leave balances",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)
if r.status_code == 200:
    annual = [b for b in r.json() if b.get("leave_type_id") == LT_ANNUAL_ID]
    check(
        "balance shows entitled / used / remaining",
        len(annual) == 1
        and "entitled_days" in annual[0]
        and "used_days" in annual[0]
        and "available_days" in annual[0],
        f"annual={annual}",
    )
    if annual:
        check(
            "remaining = entitled + carried - used",
            abs(
                annual[0]["available_days"]
                - (annual[0]["entitled_days"] + annual[0]["carried_over_days"] - annual[0]["used_days"])
            )
            < 0.01,
            f"bal={annual[0]}",
        )


# ===========================================================================
print("\n[ESS-05] Document viewing (AC-05)")
# ===========================================================================

db5 = SessionLocal()
db5.add_all(
    [
        EmployeeFile(
            employee_id=ASSOC_EMP_ID,
            document_type="Contract",
            file_name="offer_letter.pdf",
            storage_url="https://storage.example.com/ess-assoc/offer.pdf",
            version=1,
            status="Active",
        ),
        EmployeeFile(
            employee_id=OTHER_EMP_ID,
            document_type="Contract",
            file_name="other_offer.pdf",
            storage_url="https://storage.example.com/ess-other/offer.pdf",
            version=1,
            status="Active",
        ),
    ]
)
db5.commit()
db5.close()

r = client.get(f"/api/v1/ess/employee-files?employee_id={ASSOC_EMP_ID}", headers=H_ASSOC)
check(
    "associate reads own employment documents",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)
if r.status_code == 200:
    check(
        "own document carries type/name/url/version/status",
        any(
            f.get("document_type") == "Contract"
            and f.get("file_name") == "offer_letter.pdf"
            and f.get("storage_url")
            and f.get("version") == 1
            and f.get("status") == "Active"
            for f in r.json()
        ),
        f"files={r.json()}",
    )

# Cross-employee documents are refused.
r = client.get(f"/api/v1/ess/employee-files?employee_id={OTHER_EMP_ID}", headers=H_ASSOC)
check(
    "associate cannot read another employee's documents",
    r.status_code in (403, 404),
    f"got {r.status_code}: {r.text[:120]}",
)


# ===========================================================================
print("\n[ESS-06] Announcements targeted to role/tenant (AC-06)")
# ===========================================================================

db6 = SessionLocal()
now = datetime.datetime.now(datetime.timezone.utc)
future = (now + datetime.timedelta(days=30)).isoformat()
past = (now - datetime.timedelta(days=30)).isoformat()

db6.add_all(
    [
        Announcement(
            title="All hands",
            content="Everyone",
            target_audience="All",
            published=True,
            published_at=now,
            expires_at=datetime.datetime.fromisoformat(future),
        ),
        Announcement(
            title="Associate only",
            content="Associates",
            target_audience="Role",
            target_value="Associate",
            published=True,
            published_at=now,
            expires_at=datetime.datetime.fromisoformat(future),
        ),
        Announcement(
            title="Engineering dept",
            content="Eng",
            target_audience="Department",
            target_value="Engineering",
            published=True,
            published_at=now,
            expires_at=datetime.datetime.fromisoformat(future),
        ),
        Announcement(
            title="Sales dept (hidden)",
            content="Sales",
            target_audience="Department",
            target_value="Sales",
            published=True,
            published_at=now,
            expires_at=datetime.datetime.fromisoformat(future),
        ),
        Announcement(
            title="Expired",
            content="Old",
            target_audience="All",
            published=True,
            published_at=now,
            expires_at=datetime.datetime.fromisoformat(past),
        ),
        Announcement(
            title="Draft",
            content="Not published",
            target_audience="All",
            published=False,
            published_at=None,
            expires_at=datetime.datetime.fromisoformat(future),
        ),
    ]
)
db6.commit()
db6.close()

r = client.get("/api/v1/ess/announcements", headers=H_ASSOC)
check(
    "associate reads announcements",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)
if r.status_code == 200:
    titles = {a.get("title") for a in r.json()}
    check("All-audience announcement visible", "All hands" in titles, f"titles={titles}")
    check("Role-matched announcement visible", "Associate only" in titles, f"titles={titles}")
    check("Department-matched announcement visible", "Engineering dept" in titles, f"titles={titles}")
    check("Other department hidden", "Sales dept (hidden)" not in titles, f"titles={titles}")
    check("Expired hidden", "Expired" not in titles, f"titles={titles}")
    check("Draft hidden", "Draft" not in titles, f"titles={titles}")


# ===========================================================================
print("\n[ESS-07] RBAC on ESS endpoints (AC-07)")
# ===========================================================================

# An Associate may reach the ESS read surface.
r = client.get(f"/api/v1/ess/ess/profile/{ASSOC_EMP_ID}", headers=H_ASSOC)
check(
    "associate can access an ESS read endpoint",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)

# AC-07: ESS endpoints are Associate-accessible only; HR/SuperAdmin/Manager
# must receive 403 so they cannot use ESS endpoints to bypass role restrictions.
for _label, _headers in (("manager", H_MGR), ("hr", H_HR), ("superadmin", H_SUPER)):
    r = client.get(f"/api/v1/ess/ess/profile/{ASSOC_EMP_ID}", headers=_headers)
    check(
        f"{_label} is refused (403) on an ESS read endpoint",
        r.status_code == 403 and _error_envelope(r),
        f"status={r.status_code} body={r.text[:120]}",
    )


# ===========================================================================
print("\n[ESS-08] Structured error envelopes (AC-08)")
# ===========================================================================

r = client.get(f"/api/v1/ess/ess/profile/{OTHER_EMP_ID}", headers=H_ASSOC)
check(
    "cross-employee refusal returns the structured envelope",
    r.status_code in (403, 404) and _error_envelope(r),
    f"status={r.status_code} body={r.text[:160]}",
)

r = client.get(f"/api/v1/payroll/payslips?employee_id={OTHER_EMP_ID}", headers=H_ASSOC)
check(
    "cross-employee payslip refusal returns the structured envelope",
    r.status_code in (403, 404) and _error_envelope(r),
    f"status={r.status_code} body={r.text[:160]}",
)


print("\n" + "=" * 62)
print(f"==== ESS HUB SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 62)
raise SystemExit(1 if RESULTS["fail"] else 0)
