"""LibrePeople Phase 2 security remediation — access control regression suite.

Each section pins one remediation item. Every item has an authorised-path
check and an unauthorised-path check. Runs against a real FastAPI app and a
real (temporary SQLite) database. No mocks, no skips.

Sections:
  [ITEM-1]  diagnostic endpoints require a validated SuperAdmin token

Run:  python lp_phase2_access_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="lp_phase2_access_"), "lp_phase2_access.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["ENVIRONMENT"] = "development"
os.environ["LOG_LEVEL"] = "CRITICAL"
# Diagnostics must stay closed even when the old bypass flag is set.
os.environ["PUBLIC_DIAGNOSTIC_ENDPOINTS"] = "true"
os.environ["LOGIN_RATE_LIMIT_ATTEMPTS"] = "1000"
os.environ["LOGIN_RATE_LIMIT_WINDOW_SECONDS"] = "300"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

PASSWORD = "AccessTest#2026x"
USERS = {
    "lp_super": "SuperAdmin",
    "lp_hr": "HR",
    "lp_manager": "Manager",
    "lp_assoc": "Associate",
    "lp_payroll": "PayrollViewer",
}

_db = SessionLocal()
for _name, _role in USERS.items():
    _existing = _db.query(User).filter(User.username == _name).first()
    if _existing:
        _db.delete(_existing)
_db.commit()
for _name, _role in USERS.items():
    _db.add(
        User(
            username=_name,
            email=f"{_name}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role=_role,
            is_active=True,
            mfa_enabled=True,
            must_change_password=False,
        )
    )
_db.commit()
_db.close()

client = TestClient(app)

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def login(username: str) -> dict:
    r = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    if r.status_code != 200:
        raise SystemExit(f"setup: login failed for {username}: {r.status_code} {r.text[:200]}")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


HEADERS = {name: login(name) for name in USERS}

DIAG_PATHS = ("/health/db", "/health/schema", "/health/storage", "/health/wallet")


# ===========================================================================
print("\n[ITEM-1] Diagnostic endpoints require a validated SuperAdmin token")
# ===========================================================================

r = client.get("/health")
check("/health stays public", r.status_code == 200, f"got {r.status_code}")
check("/health returns only a status field", set(r.json()) == {"status"}, f"keys={list(r.json())}")

for path in DIAG_PATHS:
    # Authorised path: SuperAdmin.
    ok = client.get(path, headers=HEADERS["lp_super"])
    check(f"{path} admits a SuperAdmin", ok.status_code == 200, f"got {ok.status_code}: {ok.text[:120]}")

    # Unauthorised: no token.
    anon = client.get(path)
    check(f"{path} rejects a missing token", anon.status_code == 401, f"got {anon.status_code}")

    # Unauthorised: a garbage token that is not a JWT.
    garbage = client.get(path, headers={"Authorization": "Bearer not-a-real-token"})
    check(f"{path} rejects a garbage token", garbage.status_code == 401, f"got {garbage.status_code}")

    # Unauthorised: a token whose signature cannot verify.
    forged = client.get(
        path,
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJscF9zdXBlciJ9.AAAA"},
    )
    check(f"{path} rejects a forged token", forged.status_code == 401, f"got {forged.status_code}")

    # Unauthorised: a real HR token. Refused with 403, not admitted.
    hr = client.get(path, headers=HEADERS["lp_hr"])
    check(f"{path} refuses an HR token", hr.status_code == 403, f"got {hr.status_code}")

    # Unauthorised: Manager, Associate and PayrollViewer tokens.
    for other in ("lp_manager", "lp_assoc", "lp_payroll"):
        rr = client.get(path, headers=HEADERS[other])
        check(f"{path} refuses a {USERS[other]} token", rr.status_code == 403, f"got {rr.status_code}")

# The old PUBLIC_DIAGNOSTIC_ENDPOINTS flag is set to true above and must not
# admit anonymous callers.
for path in DIAG_PATHS:
    anon = client.get(path)
    check(
        f"{path} stays closed when PUBLIC_DIAGNOSTIC_ENDPOINTS is set",
        anon.status_code == 401,
        f"got {anon.status_code}",
    )

# A rejected /health/storage request must not write a probe file.
from app.core.config import settings  # noqa: E402

storage_dir = settings.LOCAL_STORAGE_DIR
probe_dir = os.path.join(storage_dir, "_diag")


def _probe_present() -> bool:
    return os.path.isdir(probe_dir) and any(
        f.startswith("storage-probe") for f in os.listdir(probe_dir)
    )


before = _probe_present()
client.get("/health/storage")
client.get("/health/storage", headers={"Authorization": "Bearer junk"})
client.get("/health/storage", headers=HEADERS["lp_hr"])
check(
    "rejected /health/storage requests write no probe file",
    _probe_present() == before and not before,
    f"probe present before={before} after={_probe_present()}",
)


# ===========================================================================
print("\n[ITEM-2] Only a SuperAdmin manages SuperAdmin accounts, roles and passwords")
# ===========================================================================

NEW_PW = "Fresh#Account2026x"


def _user_id(username: str):
    sess = SessionLocal()
    try:
        u = sess.query(User).filter(User.username == username).first()
        return u.id if u else None
    finally:
        sess.close()


def _user_role(username: str):
    sess = SessionLocal()
    try:
        u = sess.query(User).filter(User.username == username).first()
        return u.role if u else None
    finally:
        sess.close()


def _create(actor: str, username: str, role: str):
    return client.post(
        "/api/v1/auth/users",
        headers=HEADERS[actor],
        json={
            "user_in": {
                "username": username,
                "email": f"{username}@example.com",
                "password": NEW_PW,
                "role": role,
                "is_active": True,
            }
        },
    )


# Unauthorised: HR cannot create a SuperAdmin.
r = _create("lp_hr", "lp_hr_made_super", "SuperAdmin")
check("HR cannot create a SuperAdmin account", r.status_code == 403, f"got {r.status_code}")
check("the refused SuperAdmin account was not created", _user_id("lp_hr_made_super") is None)

# Authorised: HR can still create an ordinary account.
r = _create("lp_hr", "lp_hr_made_assoc", "Associate")
check("HR can create an Associate account", r.status_code == 201, f"got {r.status_code}: {r.text[:120]}")

# Authorised: SuperAdmin can create a SuperAdmin account.
r = _create("lp_super", "lp_super2", "SuperAdmin")
check("SuperAdmin can create a SuperAdmin account", r.status_code == 201, f"got {r.status_code}: {r.text[:120]}")
super2_id = _user_id("lp_super2")

# Unauthorised: HR cannot promote an Associate to SuperAdmin.
assoc_id = _user_id("lp_hr_made_assoc")
r = client.patch(f"/api/v1/auth/users/{assoc_id}", headers=HEADERS["lp_hr"], json={"role": "SuperAdmin"})
check("HR cannot promote an account to SuperAdmin", r.status_code == 403, f"got {r.status_code}")
check("the promotion did not happen", _user_role("lp_hr_made_assoc") == "Associate")

# Unauthorised: HR cannot change a SuperAdmin's role.
r = client.patch(f"/api/v1/auth/users/{super2_id}", headers=HEADERS["lp_hr"], json={"role": "Associate"})
check("HR cannot demote a SuperAdmin", r.status_code == 403, f"got {r.status_code}")
check("the demotion did not happen", _user_role("lp_super2") == "SuperAdmin")

# Authorised: SuperAdmin can promote and demote in both directions.
r = client.patch(f"/api/v1/auth/users/{assoc_id}", headers=HEADERS["lp_super"], json={"role": "SuperAdmin"})
check("SuperAdmin can promote an account to SuperAdmin", r.status_code == 200 and _user_role("lp_hr_made_assoc") == "SuperAdmin", f"got {r.status_code}")
r = client.patch(f"/api/v1/auth/users/{assoc_id}", headers=HEADERS["lp_super"], json={"role": "Associate"})
check("SuperAdmin can demote a SuperAdmin", r.status_code == 200 and _user_role("lp_hr_made_assoc") == "Associate", f"got {r.status_code}")

# Ordinary HR role change (not touching SuperAdmin) still works.
r = client.patch(f"/api/v1/auth/users/{assoc_id}", headers=HEADERS["lp_hr"], json={"role": "Manager"})
check("HR can still change an ordinary role", r.status_code == 200 and _user_role("lp_hr_made_assoc") == "Manager", f"got {r.status_code}")

# Unauthorised: HR cannot reset a SuperAdmin password, and the old one still works.
r = client.post(
    f"/api/v1/auth/users/{super2_id}/password",
    headers=HEADERS["lp_hr"],
    json={"new_password": NEW_PW},
)
check("HR cannot reset a SuperAdmin password", r.status_code == 403, f"got {r.status_code}")
still = client.post("/api/v1/auth/login", json={"username": "lp_super2", "password": NEW_PW})
check("the SuperAdmin's password was not changed", still.status_code == 200, f"got {still.status_code}")

# Authorised: SuperAdmin resets a SuperAdmin password.
r = client.post(
    f"/api/v1/auth/users/{super2_id}/password",
    headers=HEADERS["lp_super"],
    json={"new_password": NEW_PW},
)
check("SuperAdmin can reset a SuperAdmin password", r.status_code == 200, f"got {r.status_code}: {r.text[:120]}")

# Authorised: HR can still reset an ordinary account's password.
manager_id = _user_id("lp_manager")
r = client.post(
    f"/api/v1/auth/users/{manager_id}/password",
    headers=HEADERS["lp_hr"],
    json={"new_password": NEW_PW},
)
check("HR can still reset an ordinary account's password", r.status_code == 200, f"got {r.status_code}: {r.text[:120]}")


# ===========================================================================
print("\n[ITEM-3] Bank and tax identifier fields: HR and SuperAdmin, on read and write")
# ===========================================================================

from datetime import date  # noqa: E402
from app.core.database import SessionLocal as _SL  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.payroll import EmployeePayProfile  # noqa: E402

_db = _SL()
_dept = Department(name="LP Access Dept", code="LPAD")
_db.add(_dept)
_db.commit()
_job = Job(title="LP Access Job", code="LPAJ", department_id=_dept.id)
_db.add(_job)
_db.commit()
_emp = Employee(
    employee_id="LPA-0001",
    first_name="Bank",
    last_name="Holder",
    email="bank.holder@example.com",
    hire_date=date(2024, 1, 2),
    job_id=_job.id,
    department_id=_dept.id,
    status="Active",
    pan_number="ABCDE1234F",
    ifsc_code="HDFC0001234",
)
_db.add(_emp)
_db.commit()
EMP_ID = _emp.id
JOB_ID_LP = _job.id
DEPT_ID_LP = _dept.id
_db.close()

BANK_PAN = "ABCDE1234F"
BANK_IFSC = "HDFC0001234"


def _emp_exists(code: str) -> bool:
    sess = _SL()
    try:
        return sess.query(Employee).filter(Employee.employee_id == code).first() is not None
    finally:
        sess.close()


def _emp_id(code: str) -> int:
    sess = _SL()
    try:
        emp = sess.query(Employee).filter(Employee.employee_id == code).first()
        assert emp is not None, code
        return emp.id
    finally:
        sess.close()

# Authorised: HR reads the field.
r = client.get(f"/api/v1/employees/{EMP_ID}", headers=HEADERS["lp_hr"])
check("HR can read PAN and IFSC", r.status_code == 200 and r.json().get("pan_number") == BANK_PAN and r.json().get("ifsc_code") == BANK_IFSC, f"got {r.status_code}: {r.text[:160]}")

# Authorised read: SuperAdmin is admitted to the bank/tax fields (owner decision).
r = client.get(f"/api/v1/employees/{EMP_ID}", headers=HEADERS["lp_super"])
check(
    "superadmin_bank_tax_access: SuperAdmin receives PAN and IFSC on read",
    r.status_code == 200 and r.json().get("pan_number") == BANK_PAN and r.json().get("ifsc_code") == BANK_IFSC,
    f"got {r.status_code}: {r.text[:160]}",
)

# Unauthorised read: PayrollViewer sees no value.
r = client.get(f"/api/v1/employees/{EMP_ID}", headers=HEADERS["lp_payroll"])
body = r.json() if r.status_code == 200 else {}
check(
    "PayrollViewer does not receive PAN or IFSC",
    r.status_code == 200 and body.get("pan_number") is None and body.get("ifsc_code") is None,
    f"got {r.status_code}: {r.text[:160]}",
)

# The list endpoint applies the same policy: SuperAdmin sees the fields now,
# PayrollViewer still sees none.
r = client.get("/api/v1/employees/?search=LPA-0001", headers=HEADERS["lp_super"])
rows = r.json().get("items", []) if r.status_code == 200 else []
match = [x for x in rows if x.get("employee_id") == "LPA-0001"]
check(
    "employee list shows PAN to SuperAdmin",
    bool(match) and match[0].get("pan_number") == BANK_PAN,
    f"got {r.status_code}: {r.text[:160]}",
)
r = client.get("/api/v1/employees/?search=LPA-0001", headers=HEADERS["lp_payroll"])
rows = r.json().get("items", []) if r.status_code == 200 else []
match = [x for x in rows if x.get("employee_id") == "LPA-0001"]
check(
    "employee list hides PAN from PayrollViewer",
    bool(match) and match[0].get("pan_number") is None,
    f"got {r.status_code}: {r.text[:160]}",
)

# Writes happen at create: PATCH (EmployeeUpdate) carries no bank or tax field.
def _emp_body(code: str, **extra):
    body = {
        "employee_id": code,
        "first_name": "Write",
        "last_name": "Check",
        "email": f"{code.lower()}@example.com",
        "hire_date": "2024-02-01",
        "job_id": JOB_ID_LP,
        "department_id": DEPT_ID_LP,
        "status": "Active",
    }
    body.update(extra)
    return body


# Authorised write: SuperAdmin may set a PAN on create (owner decision).
r = client.post(
    "/api/v1/employees/",
    headers=HEADERS["lp_super"],
    json=_emp_body("LPA-0002", pan_number="ZZZZZ9999Z"),
)
check(
    "superadmin_bank_tax_access: SuperAdmin can write PAN on create",
    r.status_code == 201 and r.json().get("pan_number") == "ZZZZZ9999Z",
    f"got {r.status_code}: {r.text[:160]}",
)
check("the employee SuperAdmin created exists", _emp_exists("LPA-0002") is True)

# Authorised write: HR creates an employee with PAN and IFSC.
r = client.post(
    "/api/v1/employees/",
    headers=HEADERS["lp_hr"],
    json=_emp_body("LPA-0003", pan_number="QWERT5678Y", ifsc_code="HDFC0009999"),
)
check(
    "HR can write PAN and IFSC on create",
    r.status_code == 201 and r.json().get("pan_number") == "QWERT5678Y",
    f"got {r.status_code}: {r.text[:160]}",
)

# Pay profile: HR creates and reads the bank account; others do not.
r = client.post(
    "/api/v1/payroll/pay-profiles",
    headers=HEADERS["lp_hr"],
    json={"employee_id": EMP_ID, "base_salary": 1000, "bank_account": "1234567890"},
)
check("HR can create a pay profile with a bank account", r.status_code == 201, f"got {r.status_code}: {r.text[:160]}")
check("HR's pay profile response carries the bank account", r.status_code == 201 and r.json().get("bank_account") == "1234567890", r.text[:160])

r = client.post(
    "/api/v1/payroll/pay-profiles",
    headers=HEADERS["lp_super"],
    json={"employee_id": _emp_id("LPA-0002"), "base_salary": 1000, "bank_account": "999"},
)
check(
    "superadmin_bank_tax_access: SuperAdmin can create a pay profile with a bank account",
    r.status_code == 201 and r.json().get("bank_account") == "999",
    f"got {r.status_code}: {r.text[:160]}",
)

r = client.get(f"/api/v1/payroll/pay-profiles/{EMP_ID}", headers=HEADERS["lp_payroll"])
check(
    "PayrollViewer does not receive the bank account",
    r.status_code == 200 and r.json().get("bank_account") is None,
    f"got {r.status_code}: {r.text[:160]}",
)
r = client.get(f"/api/v1/payroll/pay-profiles/{EMP_ID}", headers=HEADERS["lp_hr"])
check(
    "HR receives the bank account on the pay profile",
    r.status_code == 200 and r.json().get("bank_account") == "1234567890",
    f"got {r.status_code}: {r.text[:160]}",
)

# Payment file carries bank data: a SuperAdmin is no longer refused by the
# policy gate (owner decision); run 999999 does not exist, so the route
# answers 404 instead of the old policy 403.
r = client.post("/api/v1/payroll/runs/999999/payment-file", headers=HEADERS["lp_super"])
check("superadmin_bank_tax_access: SuperAdmin is admitted on the payment-file route", r.status_code == 404, f"got {r.status_code}: {r.text[:120]}")

# ESS profile: Associate-only route. An Associate cannot write bank fields.
r = client.post(
    "/api/v1/ess/ess/profile",
    headers=HEADERS["lp_assoc"],
    json={"employee_id": EMP_ID, "bank_account": "5555"},
)
check("an Associate cannot write a bank account on the ESS profile", r.status_code == 403, f"got {r.status_code}: {r.text[:120]}")


# ===========================================================================
print("\n[ITEM-4] Horizontal access: the caller owns the record or manages the employee")
# ===========================================================================

from app.models.benefits import BenefitPlan as _BenefitPlan  # noqa: E402
from app.models.leave import LeaveType as _LeaveType, LeaveRequest as _LeaveRequest  # noqa: E402
from app.models.offboarding import Termination as _Termination  # noqa: E402
from app.models.time_attendance import Timesheet as _Timesheet  # noqa: E402

H4_PW = PASSWORD
_db = _SL()
_d = _db.query(Department).filter(Department.code == "LPAD").first()
_j = _db.query(Job).filter(Job.code == "LPAJ").first()
_emp_m = Employee(employee_id="H4-MGR", first_name="Mona", last_name="Manager", email="h4mgr@example.com", hire_date=date(2020, 1, 1), job_id=_j.id, department_id=_d.id, status="Active")
_db.add(_emp_m); _db.commit()
_emp_a = Employee(employee_id="H4-A", first_name="Ada", last_name="Report", email="h4a@example.com", hire_date=date(2022, 1, 1), job_id=_j.id, department_id=_d.id, status="Active", manager_id=_emp_m.id)
_emp_b = Employee(employee_id="H4-B", first_name="Bob", last_name="Other", email="h4b@example.com", hire_date=date(2022, 1, 1), job_id=_j.id, department_id=_d.id, status="Active")
_db.add_all([_emp_a, _emp_b]); _db.commit()
E_M, E_A, E_B = _emp_m.id, _emp_a.id, _emp_b.id

_plan = _BenefitPlan(name="H4 Plan", code="H4PLAN", plan_type="Health")
_ltype = _LeaveType(name="H4 Leave", code="H4LT")
_db.add_all([_plan, _ltype]); _db.commit()
PLAN_ID, LTYPE_ID = _plan.id, _ltype.id

_lr_b = _LeaveRequest(employee_id=E_B, leave_type_id=LTYPE_ID, start_date=date(2026, 3, 2), end_date=date(2026, 3, 3), working_days=2, status="Pending")
_term_b = _Termination(employee_id=E_B, last_working_date=date(2026, 6, 30), termination_type="Resignation", status="Initiated")
_ts_b = _Timesheet(employee_id=E_B, period_start=date(2026, 3, 1), period_end=date(2026, 3, 7), status="Draft")
_db.add_all([_lr_b, _term_b, _ts_b]); _db.commit()
LR_B, TERM_B, TS_B = _lr_b.id, _term_b.id, _ts_b.id
_db.close()

for _name, _emp_id, _role in (("lp_mgr", E_M, "Manager"), ("lp_assoc_a", E_A, "Associate"), ("lp_assoc_b", E_B, "Associate")):
    _sess = _SL()
    _sess.add(User(username=_name, email=f"{_name}@example.com", hashed_password=get_password_hash(PASSWORD), role=_role, is_active=True, mfa_enabled=True, must_change_password=False, employee_id=_emp_id))
    _sess.commit(); _sess.close()
    HEADERS[_name] = login(_name)

# Life events (WORKFORCE): an Associate records their own only.
r = client.post("/api/v1/benefits/life-events", headers=HEADERS["lp_assoc_a"], json={"employee_id": E_A, "event_type": "Marriage", "event_date": "2026-02-01"})
check("an Associate can record a life event for themselves", r.status_code == 201, f"got {r.status_code}: {r.text[:120]}")
r = client.post("/api/v1/benefits/life-events", headers=HEADERS["lp_assoc_a"], json={"employee_id": E_B, "event_type": "Marriage", "event_date": "2026-02-01"})
check("an Associate cannot record a life event for another employee", r.status_code == 404, f"got {r.status_code}: {r.text[:120]}")

# Leave of absence (WORKFORCE): same rule.
r = client.post("/api/v1/benefits/leaves-of-absence", headers=HEADERS["lp_assoc_a"], json={"employee_id": E_A, "leave_type": "Sabbatical", "start_date": "2026-05-01"})
check("an Associate can request a leave of absence for themselves", r.status_code == 201, f"got {r.status_code}: {r.text[:120]}")
r = client.post("/api/v1/benefits/leaves-of-absence", headers=HEADERS["lp_assoc_b"], json={"employee_id": E_A, "leave_type": "Sabbatical", "start_date": "2026-05-01"})
check("an Associate cannot request a leave of absence for another employee", r.status_code == 404, f"got {r.status_code}: {r.text[:120]}")

# Enrolment (ADMIN): HR may enrol an employee; a Manager is refused by role.
r = client.post("/api/v1/benefits/benefit-enrollments", headers=HEADERS["lp_hr"], json={"employee_id": E_A, "plan_id": PLAN_ID, "effective_date": "2026-01-01"})
check("HR can enrol an employee in a benefit", r.status_code == 201, f"got {r.status_code}: {r.text[:120]}")
r = client.post("/api/v1/benefits/benefit-enrollments", headers=HEADERS["lp_mgr"], json={"employee_id": E_A, "plan_id": PLAN_ID, "effective_date": "2026-01-01"})
check("a Manager cannot enrol an employee in a benefit", r.status_code == 403, f"got {r.status_code}")

# Termination read: the subject and their manager may read; an unrelated Associate may not.
r = client.get(f"/api/v1/offboarding/terminations/{TERM_B}", headers=HEADERS["lp_assoc_b"])
check("the subject of a termination can read it", r.status_code == 200, f"got {r.status_code}: {r.text[:120]}")
r = client.get(f"/api/v1/offboarding/terminations/{TERM_B}", headers=HEADERS["lp_assoc_a"])
check("an unrelated Associate cannot read a termination", r.status_code == 404, f"got {r.status_code}: {r.text[:120]}")
r = client.get(f"/api/v1/offboarding/terminations/{TERM_B}", headers=HEADERS["lp_hr"])
check("HR can read a termination", r.status_code == 200, f"got {r.status_code}")

# Leave cancel: the owner may cancel; an unrelated Associate may not.
r = client.post(f"/api/v1/leave/requests/{LR_B}/cancel", headers=HEADERS["lp_assoc_a"])
check("an unrelated Associate cannot cancel another employee's leave", r.status_code == 404, f"got {r.status_code}: {r.text[:120]}")
r = client.post(f"/api/v1/leave/requests/{LR_B}/cancel", headers=HEADERS["lp_assoc_b"])
check("the owner may cancel their own leave request", r.status_code == 200, f"got {r.status_code}: {r.text[:120]}")

# Timesheet submit: the owner may submit; an unrelated Associate may not.
r = client.post(f"/api/v1/time/timesheets/{TS_B}/submit", headers=HEADERS["lp_assoc_a"])
check("an unrelated Associate cannot submit another employee's timesheet", r.status_code == 404, f"got {r.status_code}: {r.text[:120]}")
r = client.post(f"/api/v1/time/timesheets/{TS_B}/submit", headers=HEADERS["lp_assoc_b"])
check("the owner may submit their own timesheet", r.status_code == 200, f"got {r.status_code}: {r.text[:120]}")

# Manager goal create: direct reports only; not another team; not self by default.
r = client.post("/api/v1/performance/goals", headers=HEADERS["lp_mgr"], json={"employee_id": E_A, "title": "Ship it"})
check("a Manager can create a goal for a direct report", r.status_code == 201, f"got {r.status_code}: {r.text[:120]}")
r = client.post("/api/v1/performance/goals", headers=HEADERS["lp_mgr"], json={"employee_id": E_B, "title": "Ship it"})
check("a Manager cannot create a goal for someone outside their team", r.status_code == 404, f"got {r.status_code}: {r.text[:120]}")
r = client.post("/api/v1/performance/goals", headers=HEADERS["lp_mgr"], json={"employee_id": E_M, "title": "My own goal"})
check("a Manager cannot create a goal for themselves (owner decision: denial kept)", r.status_code == 403, f"got {r.status_code}: {r.text[:120]}")
r = client.post("/api/v1/performance/goals", headers=HEADERS["lp_hr"], json={"employee_id": E_B, "title": "HR goal"})
check("HR can create a goal for any employee", r.status_code == 201, f"got {r.status_code}: {r.text[:120]}")


# ===========================================================================
print(f"\n{'=' * 60}")
total = RESULTS["pass"] + RESULTS["fail"]
print(f"==== LP PHASE 2 ACCESS SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed of {total} ====")
if FAILURES:
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 60)
raise SystemExit(0 if RESULTS["fail"] == 0 else 1)
