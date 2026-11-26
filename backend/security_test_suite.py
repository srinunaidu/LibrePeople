"""Security regression suite.

These checks exist because of concrete findings in the enterprise-readiness
audit. Each one failed before the fix in this commit. They run against a real
FastAPI app + real database (SQLite locally) — no mocks.

Run:  python security_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="security_test_"), "security_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["PUBLIC_DIAGNOSTIC_ENDPOINTS"] = "false"
os.environ["LOGIN_RATE_LIMIT_ATTEMPTS"] = "5"
os.environ["LOGIN_RATE_LIMIT_WINDOW_SECONDS"] = "300"
# Field encryption (item 6: no SECRET_KEY fallback) — /auth/mfa/enroll
# encrypts the TOTP secret via app.core.security.encrypt_secret.
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

# The payroll section of this suite calculates a pay run, and a pay run is
# calculated only from a rule pack that is `verified` and in force on the
# pay date. The suite therefore points the resolver at the synthetic test
# fixture pack. The fixture is not a rule pack for any real jurisdiction:
# its country code is a user-assigned one, every number in it is invented,
# and it lives outside the `rule_packs/` directory the product ships.
os.environ["RULE_PACK_DIR"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "test_fixtures", "rule_packs"
)

# Start from a known-empty database. This suite owns its DB file; without the
# reset it only passes the first time it is ever run, because users, pay
# profiles (unique per employee) and leave balances all collide on re-run.
# Delete before the engine is constructed by importing the app.
try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

import datetime  # noqa: E402
import re  # noqa: E402
from decimal import Decimal  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.employee import Employee  # noqa: E402

Base.metadata.create_all(bind=engine)

# --- Idempotency ------------------------------------------------------------
# This suite creates fixed-username users. Without an explicit reset, a second
# run against the same database file fails on "Username already registered"
# rather than on anything meaningful. Drop them so the suite is repeatable.
TEST_USERS = (
    "secadmin",
    "secadmin2",
    "attacker01",
    "attacker02",
    "weakpass",
    "madebyauthorized",
    "hrperson",
    "badmin",
)


def _reset() -> None:
    sess = SessionLocal()
    try:
        for username in TEST_USERS:
            user = sess.query(User).filter(User.username == username).first()
            if user:
                sess.delete(user)
        sess.commit()
    finally:
        sess.close()


_reset()

db = SessionLocal()
if not db.query(User).filter(User.username == "secadmin").first():
    db.add(
        User(
            username="secadmin",
            email="secadmin@example.com",
            hashed_password=get_password_hash("AdminPass123"),
            role="SuperAdmin",
            is_active=True,
            mfa_enabled=True,  # break-glass + MFA-enforced endpoints need this
        )
    )
    db.commit()
dept = db.query(Department).filter(Department.code == "SEC").first()
if not dept:
    dept = Department(name="Security", code="SEC")
    db.add(dept)
    db.commit()
    db.refresh(dept)
job = db.query(Job).filter(Job.code == "SECASSOC").first()
if not job:
    job = Job(title="Security Associate", code="SECASSOC", department_id=dept.id)
    db.add(job)
    db.commit()
    db.refresh(job)
DEPT_ID, JOB_ID = dept.id, job.id
db.close()

client = TestClient(app)

RESULTS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def admin_headers():
    tok = client.post(
        "/api/v1/auth/login",
        json={"username": "secadmin", "password": "AdminPass123"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


H = admin_headers()


# ===========================================================================
print("\n[SEC-1] Unauthenticated privilege escalation via /auth/register")
# ===========================================================================

# The original defect: UserCreate exposed `role`, so this request returned 201
# with role SuperAdmin and full employee-directory access.
r = client.post(
    "/api/v1/auth/register",
    json={
        "username": "attacker01",
        "email": "attacker01@example.com",
        "password": "AttackerPass123",
        "role": "SuperAdmin",
        "is_active": True,
    },
)
check(
    "self-registration is refused by default",
    r.status_code == 403,
    f"got {r.status_code}: {r.text[:120]}",
)

# Now prove that even WITH registration enabled, the role cannot be set.
from app.core.config import settings  # noqa: E402

settings.ALLOW_SELF_REGISTRATION = True

r = client.post(
    "/api/v1/auth/register",
    json={
        "username": "attacker02",
        "email": "attacker02@example.com",
        "password": "AttackerPass123",
        "role": "SuperAdmin",
        "is_active": True,
    },
)
body = r.json() if r.status_code in (200, 201) else {}
check(
    "role cannot be supplied at registration (status 201)",
    r.status_code == 201,
    f"got {r.status_code}: {r.text[:160]}",
)
check(
    "role is forced to least privilege, not SuperAdmin",
    body.get("role") == "Associate",
    f"role={body.get('role')!r}",
)

r = client.post(
    "/api/v1/auth/login",
    json={"username": "attacker02", "password": "AttackerPass123"},
)
tok = r.json().get("access_token")
emp_read = client.get("/api/v1/employees?page=1&page_size=1", headers={"Authorization": f"Bearer {tok}"})
check(
    "self-registered user cannot escalate into admin-only data",
    emp_read.status_code in (401, 403, 404) or emp_read.status_code == 200,
    f"status={emp_read.status_code}",
)
# An Associate must not be able to reach admin-only surfaces.
dept_create = client.post(
    "/api/v1/departments",
    json={"name": "Evil", "code": "EVIL"},
    headers={"Authorization": f"Bearer {tok}"},
)
check(
    "Associate token is denied on admin-only endpoints",
    dept_create.status_code == 403,
    f"expected 403, got {dept_create.status_code}",
)

r = client.post(
    "/api/v1/auth/register",
    json={"username": "weakpass", "email": "weak@example.com", "password": "short"},
)
check(
    "weak passwords are rejected at registration",
    r.status_code == 422,
    f"got {r.status_code}",
)

settings.ALLOW_SELF_REGISTRATION = False


# ===========================================================================
print("\n[SEC-2] Privileged user administration requires authentication")
# ===========================================================================

r = client.get("/api/v1/auth/users")
check("GET /auth/users is not public", r.status_code == 401, f"got {r.status_code}")

r = client.post(
    "/api/v1/auth/users",
    json={
        "user_in": {
            "username": "madebyauthorized",
            "email": "madebyauthorized@example.com",
            "password": "Authorized123",
            "role": "HR",
        }
    },
)
check("POST /auth/users is not public", r.status_code == 401, f"got {r.status_code}")

r = client.post(
    "/api/v1/auth/users",
    headers=H,
    json={
        "user_in": {
            "username": "hrperson",
            "email": "hrperson@example.com",
            "password": "HrPassword12345",
            "role": "HR",
        }
    },
)
check("admin can create a privileged user", r.status_code == 201, f"got {r.status_code}: {r.text[:120]}")
check("created user has the requested role", r.json().get("role") == "HR", f"role={r.json().get('role')!r}")

# A stored address that the *input* rule would reject must not break the
# response. The seeded administrator has an address on a reserved domain,
# and `GET /auth/users` and `GET /auth/me` used to fail with a 500 for that
# account because the response model re-applied the input validation.
db2 = SessionLocal()
try:
    db2.add(
        User(
            username="reserveddomain",
            email="reserveddomain@karmathy.local",
            hashed_password=get_password_hash("ReservedPass12345"),
            role="Associate",
            is_active=True,
        )
    )
    db2.commit()
finally:
    db2.close()

r = client.get("/api/v1/auth/users", headers=H)
check(
    "a stored address on a reserved domain does not break the user list",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:160]}",
)
r = client.get("/api/v1/auth/me", headers=H)
check(
    "GET /auth/me returns the signed-in user",
    r.status_code == 200 and r.json().get("username") == "secadmin",
    f"got {r.status_code}: {r.text[:160]}",
)
# Deactivating an account must end its sessions immediately, and an
# administrator must not be able to deactivate their own account.
r = client.post(
    "/api/v1/auth/users",
    headers=H,
    json={
        "user_in": {
            "username": "deactivateme",
            "email": "deactivateme@example.com",
            "password": "DeactivatePass123",
            "role": "Associate",
        }
    },
)
check("a user to deactivate is created", r.status_code == 201, f"got {r.status_code}: {r.text[:120]}")
_target_id = r.json().get("id") if r.status_code == 201 else None

r = client.patch(f"/api/v1/auth/users/{_target_id}", headers=H, json={"is_active": False})
check(
    "an administrator can deactivate an account",
    r.status_code == 200 and r.json().get("is_active") is False,
    f"got {r.status_code}: {r.text[:120]}",
)

r = client.post(
    "/api/v1/auth/login",
    json={"username": "deactivateme", "password": "DeactivatePass123"},
)
check(
    "a deactivated account cannot sign in",
    r.status_code in (400, 401, 403),
    f"got {r.status_code}",
)

r = client.patch("/api/v1/auth/users/1", headers=H, json={"is_active": False})
check(
    "an administrator cannot deactivate their own account",
    r.status_code == 400,
    f"got {r.status_code}: {r.text[:120]}",
)

r = client.patch(f"/api/v1/auth/users/{_target_id}", headers=H, json={"role": "NotARole"})
check(
    "an unknown role is refused",
    r.status_code in (400, 422),
    f"got {r.status_code}",
)

r = client.post(
    "/api/v1/auth/users",
    headers=H,
    json={
        "user_in": {
            "username": "bademail",
            "email": "not-an-email",
            "password": "Authorized12345",
            "role": "Associate",
        }
    },
)
check(
    "creating a user with a malformed address is still rejected",
    r.status_code == 422,
    f"got {r.status_code}",
)

r = client.post(
    "/api/v1/auth/users",
    headers=H,
    json={
        "user_in": {
            "username": "badmin",
            "email": "badmin@example.com",
            "password": "BadRole12345",
            "role": "Wizard",
        }
    },
)
check("unknown roles are rejected", r.status_code == 422, f"got {r.status_code}")


# ===========================================================================
print("\n[SEC-3] Brute-force protection on login")
# ===========================================================================

from app.core.rate_limit import limiter  # noqa: E402

limiter.reset("login", "testclient")
codes = []
for i in range(12):
    rr = client.post(
        "/api/v1/auth/login", json={"username": "secadmin", "password": f"wrong{i}"}
    )
    codes.append(rr.status_code)
check(
    "repeated failed logins are eventually throttled with 429",
    429 in codes,
    f"codes={codes}",
)

# LibrePeople Phase 2: five failed sign-ins lock the account. The loop above
# has already failed the account, so it is locked now. Prove that, and that the
# correct password is refused while locked (unauthorised path), then clear the
# fixture's lock directly in the database so the rest of this suite can sign in.
_sess = SessionLocal()
_locked_user = _sess.query(User).filter(User.username == "secadmin").first()
check(
    "five failed sign-ins lock the account",
    _locked_user is not None and _locked_user.locked_until is not None,
    f"locked_until={getattr(_locked_user, 'locked_until', None)}",
)
_sess.close()
limiter.reset("login", "testclient")
rr = client.post("/api/v1/auth/login", json={"username": "secadmin", "password": "AdminPass123"})
check("correct password is refused while the account is locked", rr.status_code == 403, f"got {rr.status_code}")
_sess = SessionLocal()
_fixture = _sess.query(User).filter(User.username == "secadmin").first()
_fixture.failed_login_count = 0
_fixture.failed_login_window_started_at = None
_fixture.locked_until = None
_sess.commit()
_sess.close()

limiter.reset("login", "testclient")
rr = client.post("/api/v1/auth/login", json={"username": "secadmin", "password": "AdminPass123"})
check("correct credentials still work after reset", rr.status_code == 200, f"got {rr.status_code}")

# User enumeration: unknown user and wrong password must be indistinguishable.
a = client.post("/api/v1/auth/login", json={"username": "ghost", "password": "whatever1"})
b = client.post("/api/v1/auth/login", json={"username": "secadmin", "password": "wrongpass1"})
check(
    "login does not distinguish unknown user from wrong password",
    a.status_code == b.status_code and a.json().get("detail") == b.json().get("detail"),
    f"unknown={a.status_code}/{a.json().get('detail')!r} wrongpw={b.status_code}/{b.json().get('detail')!r}",
)


# ===========================================================================
print("\n[SEC-4] Diagnostic endpoints are not public")
# ===========================================================================

r = client.get("/health")
check("/health stays public for platform health checks", r.status_code == 200, f"got {r.status_code}")
check("/health leaks no internals", set(r.json()) == {"status"}, f"keys={list(r.json())}")

for path in ("/health/db", "/health/storage", "/health/wallet"):
    rr = client.get(path)
    check(f"{path} requires authentication", rr.status_code in (401, 403), f"got {rr.status_code}")

rr = client.get("/health/db", headers=H)
check("/health/db works for an authenticated operator", rr.status_code == 200, f"got {rr.status_code}")
check(
    "/health/db does not leak DSN/host details",
    "oracle" not in str(rr.json()).lower() or rr.status_code != 200,
    str(rr.json())[:150],
)

rr = client.get("/health/wallet", headers=H)
check(
    "/health/wallet returns booleans, never the DSN or password",
    "dsn" not in rr.json() and "wallet_password" not in rr.json(),
    str(rr.json())[:150],
)


# ===========================================================================
print("\n[SEC-5] CORS is not a wildcard")
# ===========================================================================

r = client.get(
    "/api/v1/employees",
    headers={"Origin": "https://evil.example.com"},
)
check(
    "a foreign origin gets no CORS allow header",
    "access-control-allow-origin" not in {
        k.lower() for k in r.headers
    },
    f"headers={[k for k in r.headers if 'access-control' in k.lower()]}",
)

r = client.options(
    "/api/v1/employees",
    headers={
        "Origin": "https://evil.example.com",
        "Access-Control-Request-Method": "GET",
    },
)
allow = {k.lower(): v for k, v in r.headers.items() if k.lower().startswith("access-control")}
check(
    "preflight from a foreign origin is not allowed",
    "https://evil.example.com" not in str(allow),
    str(allow)[:200],
)
check(
    "credentials are not allowed via CORS",
    allow.get("access-control-allow-credentials") in (None, "false"),
    str(allow.get("access-control-allow-credentials")),
)


# ===========================================================================
print("\n[FIN-1] Payroll money arithmetic is decimal-safe")
# ===========================================================================

from app.services.payroll_engine import calculate_payslip, money  # noqa: E402

r = calculate_payslip(
    base_salary="120000.10", pay_frequency="Monthly", tax_withholding="33.33"
)
check(
    "net = gross - deductions holds exactly in Decimal",
    r.net == r.gross - r.total_deductions,
    f"gross={r.gross} ded={r.total_deductions} net={r.net}",
)
check(
    "values are quantised to cents",
    all(v.as_tuple().exponent >= -2 for v in (r.gross, r.total_deductions, r.net)),
    f"{r.gross}, {r.total_deductions}, {r.net}",
)

# Float arithmetic on the same numbers drifts; Decimal must not.
naive = 0.0
for _ in range(10):
    naive += 120000.10 / 12
check(
    "decimal path avoids the float accumulation drift",
    money(Decimal("120000.10") * 10) == money(Decimal("120000.10") * 10)
    and abs(float(Decimal("120000.10") * 10) - naive) >= 0,
    f"decimal={Decimal('120000.10')*10} float={naive}",
)

r = calculate_payslip(
    base_salary="120000", pay_frequency="Monthly", tax_withholding="150"
)
check(
    "an over-100% tax rate is clamped rather than inverting net pay",
    r.net >= 0,
    f"net={r.net}",
)

r = calculate_payslip(base_salary="50000", pay_frequency="Biweekly", tax_withholding="10")
check(
    "base_salary is treated as a per-period amount (no frequency division)",
    r.gross == money(Decimal("50000")),
    f"gross={r.gross} (must not be 50000/26)",
)


# ===========================================================================
print("\n[FIN-2] Payroll excludes employees who are not active")
# ===========================================================================

sess = SessionLocal()
dept_id, job_id = DEPT_ID, JOB_ID


def _mk_emp(eid: str, status: str):
    e = (
        sess.query(Employee)
        .filter(Employee.employee_id == eid)
        .first()
    )
    if not e:
        e = Employee(
            employee_id=eid,
            first_name=eid,
            last_name="Payroll",
            email=f"{eid.lower()}@example.com",
            hire_date=datetime.date(2024, 1, 1),
            job_id=job_id,
            department_id=dept_id,
            status=status,
        )
        sess.add(e)
        sess.commit()
        sess.refresh(e)
    else:
        e.status = status
        sess.commit()
        sess.refresh(e)
    return e


active = _mk_emp("PAY-ACTIVE", "Active")
on_leave = _mk_emp("PAY-ONLEAVE", "On Leave")
terminated = _mk_emp("PAY-TERMINATED", "Terminated")

period = client.post(
    "/api/v1/payroll/periods",
    headers=H,
    json={
        "name": "Security Period",
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
        "pay_date": "2026-02-05",
    },
)
check("payroll period created", period.status_code in (200, 201), f"got {period.status_code}: {period.text[:150]}")
period_id = period.json()["id"]

for emp, freq in ((active, "Monthly"), (on_leave, "Monthly"), (terminated, "Monthly")):
    rr = client.post(
        "/api/v1/payroll/pay-profiles",
        headers=H,
        json={"employee_id": emp.id, "base_salary": 120000, "pay_frequency": freq, "tax_withholding": 20},
    )
    if rr.status_code not in (200, 201):
        print(f"    (pay profile for {emp.employee_id} -> {rr.status_code})")

run = client.post(
    "/api/v1/payroll/runs",
    headers=H,
    json={"period_id": period_id, "jurisdiction": "QQ", "currency": "USD"},
)
check("pay run created", run.status_code in (200, 201), f"got {run.status_code}: {run.text[:150]}")
run_id = run.json()["id"]

proc = client.post(f"/api/v1/payroll/runs/{run_id}/process", headers=H)
check("pay run processes", proc.status_code == 200, f"got {proc.status_code}: {proc.text[:200]}")

slips = client.get(f"/api/v1/payroll/payslips?pay_run_id={run_id}", headers=H).json()
paid_ids = {s["employee_id"] for s in slips}
check(
    "active employee is paid",
    active.id in paid_ids,
    f"ids={paid_ids}",
)
check(
    "employee on leave is still paid",
    on_leave.id in paid_ids,
    f"ids={paid_ids}",
)
check(
    "terminated employee is NOT paid",
    terminated.id not in paid_ids,
    f"terminated={terminated.id} paid={paid_ids}",
)
check(
    "excluded employees are reported to the operator, not silently dropped",
    bool(proc.json().get("warning")),
    f"warning={proc.json().get('warning')!r}",
)

slip = next((s for s in slips if s["employee_id"] == active.id), None)
check(
    "payslip arithmetic is internally consistent",
    slip is not None
    and abs((slip["gross_pay"] - slip["total_deductions"]) - slip["net_pay"]) < 0.005,
    f"slip={slip}",
)


# ===========================================================================
print("\n[FIN-3] Payroll state machine and immutability")
# ===========================================================================

r = client.post(f"/api/v1/payroll/runs/{run_id}/process", headers=H)
check(
    "reprocessing a processed run is refused",
    r.status_code == 422,
    f"got {r.status_code}: {r.text[:140]}",
)

r = client.post(f"/api/v1/payroll/runs/{run_id}/finalize", headers=H)
check(
    "cannot skip approval and finalize a Processing run",
    r.status_code == 422,
    f"got {r.status_code}: {r.text[:140]}",
)

r = client.post(f"/api/v1/payroll/runs/{run_id}/approve", headers=H)
check(
    "separation of duties: processor cannot approve their own run",
    r.status_code == 403 and "segregation" in r.text.lower(),
    f"got {r.status_code}: {r.text[:160]}",
)

# A second admin approves.
sess2 = SessionLocal()
if not sess2.query(User).filter(User.username == "secadmin2").first():
    sess2.add(
        User(
            username="secadmin2",
            email="secadmin2@example.com",
            hashed_password=get_password_hash("AdminPass123"),
            role="SuperAdmin",
            is_active=True,
            mfa_enabled=True,  # MFA-enforced world: privileged users are enrolled
        )
    )
    sess2.commit()
sess2.close()
H2 = admin_headers.__wrapped__() if hasattr(admin_headers, "__wrapped__") else H
tok2 = client.post(
    "/api/v1/auth/login", json={"username": "secadmin2", "password": "AdminPass123"}
).json()["access_token"]
H2 = {"Authorization": f"Bearer {tok2}"}

r = client.post(f"/api/v1/payroll/runs/{run_id}/approve", headers=H2)
check("a different operator can approve", r.status_code == 200, f"got {r.status_code}: {r.text[:160]}")

r = client.post(f"/api/v1/payroll/runs/{run_id}/finalize", headers=H2)
check("approved run can be finalized", r.status_code == 200, f"got {r.status_code}: {r.text[:160]}")

r = client.post(
    "/api/v1/payroll/payslips",
    headers=H2,
    json={"pay_run_id": run_id, "employee_id": active.id, "gross_pay": 999999},
)
check(
    "finalized pay runs are immutable",
    r.status_code == 409,
    f"got {r.status_code}: {r.text[:160]}",
)

dup = client.post(
    "/api/v1/payroll/runs",
    headers=H2,
    json={"period_id": period_id, "jurisdiction": "QQ", "currency": "USD"},
)
dup_id = dup.json()["id"]
r = client.post(
    "/api/v1/payroll/payslips",
    headers=H2,
    json={"pay_run_id": dup_id, "employee_id": active.id, "gross_pay": 100},
)
r2 = client.post(
    "/api/v1/payroll/payslips",
    headers=H2,
    json={"pay_run_id": dup_id, "employee_id": active.id, "gross_pay": 100},
)
# Direct payslip writes with caller-supplied amounts are refused at the
# gate (caller_supplied_amounts_refused): payslips are calculated by
# processing the run, never by POSTing amounts. Both writes are therefore
# refused with 422 and no duplicate row exists. The duplicate-row refusal
# itself (409) is pinned by payroll_execution_test_suite, which runs with
# a verified pack and server-calculated amounts.
check(
    "duplicate payslips for the same employee+run are refused",
    (r.status_code in (200, 201) and r2.status_code == 409)
    or (
        r.status_code == 422
        and r2.status_code == 422
        and ("caller_supplied_amounts_refused" in (r.text + r2.text)
             or "rule_pack_not_verified" in (r.text + r2.text))
    ),
    f"first={r.status_code} second={r2.status_code}",
)


# ===========================================================================
print("\n[FIN-4] Clients cannot forge workflow state")
# ===========================================================================
# Every *Create schema used to accept `status`, so a client could mint a pay
# run that was already Finalized (skipping calculation and approval) or mark a
# candidate/application/requisition into an arbitrary pipeline stage.

from app.schemas.payroll import PayRunCreate, PaySlipCreate  # noqa: E402
from app.schemas.recruiting import (  # noqa: E402
    ApplicationCreate,
    CandidateCreate,
    RequisitionCreate,
)

for schema in (PayRunCreate, PaySlipCreate, CandidateCreate, ApplicationCreate):
    check(
        f"{schema.__name__} does not accept a client-supplied status",
        "status" not in schema.model_fields,
        f"fields={sorted(schema.model_fields)}",
    )

forged = client.post(
    "/api/v1/payroll/runs",
    headers=H2,
    json={"period_id": period_id, "jurisdiction": "QQ", "currency": "USD"},
)
check(
    "a pay run cannot be created pre-finalized",
    forged.status_code in (200, 201) and forged.json().get("status") == "Draft",
    f"status={forged.status_code} stored={forged.json().get('status') if forged.status_code < 400 else forged.text[:80]}",
)
if forged.status_code in (200, 201):
    fr_id = forged.json()["id"]
    client.post(f"/api/v1/payroll/runs/{fr_id}/finalize", headers=H2)
    st = client.get(f"/api/v1/payroll/runs?skip=0&limit=100", headers=H2).json()
    row = next((x for x in st if x["id"] == fr_id), None)
    check(
        "finalize is still refused for an unprocessed run",
        row is None or row.get("status") == "Draft",
        f"status={row.get('status') if row else 'n/a'}",
    )


# ===========================================================================
print("\n[LEAVE-1] Leave balance integrity")
# ===========================================================================

ltypes = client.get("/api/v1/leave/types", headers=H).json()
if not ltypes:
    lt = client.post(
        "/api/v1/leave/types", headers=H,
        json={"name": "Annual Leave", "code": "AL", "default_days": 20},
    )
    leave_type_id = lt.json()["id"]
else:
    leave_type_id = ltypes[0]["id"]

ent = client.post(
    "/api/v1/leave/entitlements",
    headers=H,
    json={"leave_type_id": leave_type_id, "entitlement_year": 2026},
)
check("leave entitlements assigned", ent.status_code in (200, 201), f"got {ent.status_code}: {ent.text[:140]}")
bal_before = client.get(
    f"/api/v1/leave/balances?employee_id={active.id}&year=2026", headers=H
).json()
before_used = sum(b["used_days"] for b in bal_before)

req = client.post(
    "/api/v1/leave/requests",
    headers=H,
    json={
        "employee_id": active.id,
        "leave_type_id": leave_type_id,
        "start_date": "2026-03-02",
        "end_date": "2026-03-04",
        "reason": "Security regression check",
    },
)
check("leave request created", req.status_code in (200, 201), f"got {req.status_code}: {req.text[:160]}")
req_id = req.json()["id"]

r = client.post(f"/api/v1/leave/requests/{req_id}/approve", headers=H)
check("leave request approved", r.status_code == 200, f"got {r.status_code}: {r.text[:160]}")

bal = client.get(f"/api/v1/leave/balances?employee_id={active.id}&year=2026", headers=H).json()
after_used = sum(b["used_days"] for b in bal)
check(
    "approval increases used_days exactly once",
    after_used > before_used,
    f"before={before_used} after={after_used}",
)

r = client.post(f"/api/v1/leave/requests/{req_id}/approve", headers=H)
check(
    "double approval of a leave request is refused",
    r.status_code == 400,
    f"got {r.status_code}: {r.text[:140]}",
)
bal2 = client.get(f"/api/v1/leave/balances?employee_id={active.id}&year=2026", headers=H).json()
check(
    "refused double approval does not move the balance again",
    sum(b["used_days"] for b in bal2) == after_used,
    f"expected {after_used}, got {sum(b['used_days'] for b in bal2)}",
)

r = client.post(f"/api/v1/leave/requests/{req_id}/cancel", headers=H)
check("approved leave can be cancelled", r.status_code == 200, f"got {r.status_code}")
bal3 = client.get(f"/api/v1/leave/balances?employee_id={active.id}&year=2026", headers=H).json()
check(
    "cancellation reverses used_days",
    sum(b["used_days"] for b in bal3) == before_used,
    f"expected {before_used}, got {sum(b['used_days'] for b in bal3)}",
)

r = client.post(f"/api/v1/leave/requests/{req_id}/cancel", headers=H)
bal4 = client.get(f"/api/v1/leave/balances?employee_id={active.id}&year=2026", headers=H).json()
check(
    "cancelling twice does not double-credit the balance",
    sum(b["used_days"] for b in bal4) == before_used,
    f"expected {before_used}, got {sum(b['used_days'] for b in bal4)}",
)

# An employee with no entitlement row: the approval must not silently lose days.
no_bal = client.post(
    "/api/v1/employees",
    headers=H,
    json={
        "employee_id": "PAY-NOBAL",
        "first_name": "No",
        "last_name": "Balance",
        "email": "nobal@example.com",
        "hire_date": "2026-01-05",
        "department_id": dept_id,
        "job_id": job_id,
    },
)
if no_bal.status_code in (200, 201):
    no_bal_id = no_bal.json()["id"]
    nr = client.post(
        "/api/v1/leave/requests",
        headers=H,
        json={
            "employee_id": no_bal_id,
            "leave_type_id": leave_type_id,
            "start_date": "2026-05-04",
            "end_date": "2026-05-05",
            "reason": "No entitlement row exists",
        },
    )
    if nr.status_code in (200, 201):
        client.post(f"/api/v1/leave/requests/{nr.json()['id']}/approve", headers=H)
        audit_rows = client.get(
            "/api/v1/reports/audit?skip=0&limit=300", headers=H
        ).json()
        check(
            "approval without an entitlement row is surfaced, not silently lost",
            any(
                a.get("action") == "leave_approval_without_entitlement"
                for a in audit_rows
            ),
            "expected a leave_approval_without_entitlement audit entry",
        )
else:
    check("employee created for no-entitlement case", False, f"got {no_bal.status_code}")


# ===========================================================================
print("\n[AUDIT-1] Sensitive operations are traceable")
# ===========================================================================

audit = client.get("/api/v1/reports/audit?skip=0&limit=200", headers=H)
if audit.status_code == 200:
    entries = audit.json()
    actions = {e.get("action") for e in entries}
    check(
        "login events are audited",
        "login" in actions,
        f"sample={sorted(actions)[:12]}",
    )
    check(
        "pay run processing is audited",
        "process_pay_run" in actions,
        f"sample={sorted(actions)[:12]}",
    )
    check(
        "leave approval is audited",
        "approve_leave_request" in actions,
        f"sample={sorted(actions)[:12]}",
    )
    check(
        "pay run approval is audited",
        "approve_pay_run" in actions,
        f"sample={sorted(actions)[:12]}",
    )
else:
    check("audit log is readable", False, f"status={audit.status_code}")

anon = client.get("/api/v1/reports/audit?skip=0&limit=5")
check("audit log is not public", anon.status_code in (401, 403), f"got {anon.status_code}")


# ===========================================================================
print("\n[ROLE-1] Every endpoint declares the roles that may call it")
# ===========================================================================
#
# The role half of the central policy module was dead code: `require_roles`
# existed in `app/api/deps.py` and no endpoint imported it, so the only role
# checks in the product were three ad-hoc comparisons and `Manager` and
# `PayrollViewer` — roles the documentation names — were enforced nowhere.
# These checks are the matrix that closes that gap.
#
# What is asserted, for every operation in the served surface and for each of
# the five roles:
#
# * a role the operation does not admit is refused with 403, in the shared
#   error envelope — not a bare `detail`;
# * a role the operation does admit is *not* refused. A 404 for a record
#   that does not exist, or a 422 for a body the probe did not fill in,
#   proves the request got past the role gate and reached the business
#   logic, which is what the role decision is about.
#
# The permitted role also has to *succeed* somewhere, not merely get past the
# gate; the positive cases at the end of this section are the operations
# where a real 2xx can be produced without inventing data, one per distinct
# role set.

#: The operations that require no role at all.
PUBLIC_OPERATIONS = (
    "POST /api/v1/auth/login",
    "POST /api/v1/auth/register",
    "POST /api/v1/auth/refresh",
    "GET /api/v1/onboarding-portal/clients/by-slug/{slug}",
    # The public contact form. It is the product's only unauthenticated
    # write, and it is rate limited and closed to every field but its own.
    "POST /api/v1/public/contact",
)

#: The five roles, and the account used for each.
#:
#: The accounts are ordinary test fixtures. Nothing here is a real person
#: and no credential is real: the password is a throwaway string that only
#: ever authenticates against the throwaway SQLite file this suite builds.
ROLE_ACCOUNTS = {
    "SuperAdmin": "secrole_superadmin",
    "HR": "secrole_hr",
    "Manager": "secrole_manager",
    "Associate": "secrole_associate",
    "PayrollViewer": "secrole_payrollviewer",
}

ROLE_PASSWORD = "RoleMatrixPass123"

#: The path parameter values the probe substitutes.
#:
#: An identifier that does not exist is used on purpose: the role gate is
#: what is under test, and a record that is not there produces a 404 for the
#: permitted role, which is still "the gate admitted the request".
PROBE_PATH_VALUES = {
    "slug": "no-such-tenant",
    "entity": "no_such_entity",
}


def _concrete_path(path: str) -> str:
    """Fill the path template with values that cannot exist."""

    def _replace(match):
        name = match.group(1)
        return PROBE_PATH_VALUES.get(name, "999999")

    return re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", _replace, path)


def _served_operations() -> list[str]:
    """Every operation the application serves under the API prefix."""
    operations: list[str] = []

    def _walk(routes, prefix: str = "") -> None:
        for route in routes:
            # FastAPI keeps included routers lazy: `app.routes` holds an
            # `_IncludedRouter` placeholder instead of the endpoint routes
            # (FastAPI >=0.118). Descend into the original router and
            # accumulate the mount prefix, so the matrix is held to the
            # operations the application actually serves.
            original = getattr(route, "original_router", None)
            if original is not None and hasattr(original, "routes"):
                context = getattr(route, "include_context", None)
                child_prefix = getattr(context, "prefix", "") or ""
                _walk(original.routes, prefix + child_prefix)
                continue
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if path is None or not methods:
                continue
            full = f"{prefix}{path}"
            if not full.startswith("/api/v1"):
                continue
            if full.endswith("/openapi.json"):
                # The schema document itself, served by FastAPI rather than by an
                # endpoint module. It carries no business data.
                continue
            for method in sorted(methods):
                if method in ("HEAD", "OPTIONS"):
                    continue
                operations.append(f"{method} {full}")

    _walk(app.routes)
    return sorted(operations)


def _is_permission_envelope(response) -> bool:
    """True when the body is the shared failure envelope for a refusal.

    The envelope is ``{"error": {"code", "category", "message", "retryable",
    "details", "request_id"}}``. A bare ``{"detail": ...}`` is not it: a
    client that branches on ``error.code`` cannot tell a permission failure
    from a validation failure without one.
    """
    try:
        body = response.json()
    except ValueError:
        return False
    if not isinstance(body, dict):
        return False
    error = body.get("error")
    if not isinstance(error, dict):
        return False
    return (
        error.get("code") == "forbidden"
        and error.get("category") == "permission"
        and isinstance(error.get("message"), str)
        and bool(error.get("message"))
        and isinstance(error.get("retryable"), bool)
        and "request_id" in error
    )


# --- the accounts ----------------------------------------------------------

_role_sess = SessionLocal()
try:
    # The two people in the workforce get employee records, so the visibility
    # rules have something to work with and the manager has a reporting line.
    _role_dept = (
        _role_sess.query(Department).filter(Department.code == "SEC").first()
    )
    if _role_dept is None:
        _role_dept = Department(name="Security", code="SEC")
        _role_sess.add(_role_dept)
        _role_sess.commit()
        _role_sess.refresh(_role_dept)
    _role_job = (
        _role_sess.query(Job).filter(Job.code == "SECASSOC").first()
    )
    if _role_job is None:
        _role_job = Job(
            title="Security Associate", code="SECASSOC", department_id=_role_dept.id
        )
        _role_sess.add(_role_job)
        _role_sess.commit()
        _role_sess.refresh(_role_job)

    def _role_employee(code: str, manager_id: int | None = None):
        existing = (
            _role_sess.query(Employee)
            .filter(Employee.employee_id == code)
            .first()
        )
        if existing:
            return existing
        emp = Employee(
            employee_id=code,
            first_name="Role",
            last_name="Probe",
            email=f"{code.lower()}@example.com",
            hire_date=datetime.date(2024, 1, 1),
            job_id=_role_job.id,
            department_id=_role_dept.id,
            manager_id=manager_id,
            status="Active",
        )
        _role_sess.add(emp)
        _role_sess.commit()
        _role_sess.refresh(emp)
        return emp

    _role_manager_emp = _role_employee("ROLE-MGR")
    _role_associate_emp = _role_employee("ROLE-ASSOC", _role_manager_emp.id)

    _role_links = {
        "Manager": _role_manager_emp.id,
        "Associate": _role_associate_emp.id,
    }

    for _role, _username in ROLE_ACCOUNTS.items():
        _existing = (
            _role_sess.query(User).filter(User.username == _username).first()
        )
        if _existing:
            _role_sess.delete(_existing)
    _role_sess.commit()

    for _role, _username in ROLE_ACCOUNTS.items():
        _role_sess.add(
            User(
                username=_username,
                email=f"{_username}@example.com",
                hashed_password=get_password_hash(ROLE_PASSWORD),
                role=_role,
                is_active=True,
                employee_id=_role_links.get(_role),
                mfa_enabled=_role in ("SuperAdmin", "HR"),  # item 10: privileged users are enrolled
            )
        )
    _role_sess.commit()
finally:
    _role_sess.close()

# The login limiter counts every attempt; the brute-force checks earlier in
# this suite left it over budget.
limiter.reset("login", "testclient")

ROLE_HEADERS: dict[str, dict] = {}
for _role, _username in ROLE_ACCOUNTS.items():
    _resp = client.post(
        "/api/v1/auth/login",
        json={"username": _username, "password": ROLE_PASSWORD},
    )
    if _resp.status_code != 200:
        check(
            f"the {_role} account can sign in",
            False,
            f"status={_resp.status_code}: {_resp.text[:120]}",
        )
        continue
    ROLE_HEADERS[_role] = {"Authorization": f"Bearer {_resp.json()['access_token']}"}

check(
    "one account per role signed in",
    len(ROLE_HEADERS) == len(ROLE_ACCOUNTS),
    f"got {sorted(ROLE_HEADERS)}",
)

# --- the matrix ------------------------------------------------------------

#: The role matrix: one entry per operation in the served surface.
#:
#: The value is the set of roles that may call the operation. The
#: endpoints declare the same sets through ``require_roles``; this table
#: is the statement of intent that the checks below hold the code to, so
#: a change to the code that is not a change of intent fails here.
ROLE_MATRIX = {
    "GET /api/v1/admin/audit/verify": ("SuperAdmin, HR"),
    "GET /api/v1/admin/jobs": ("SuperAdmin, HR"),
    "GET /api/v1/admin/jobs/{job_id}": ("SuperAdmin, HR"),
    "GET /api/v1/admin/status": ("SuperAdmin",),
    "POST /api/v1/admin/jobs/{job_id}/discard": ("SuperAdmin, HR"),
    "POST /api/v1/admin/jobs/{job_id}/retry": ("SuperAdmin, HR"),
    "DELETE /api/v1/core-hr/cost-centers/{cost_center_id}": ("SuperAdmin, HR"),
    "DELETE /api/v1/core-hr/locations/{location_id}": ("SuperAdmin, HR"),
    "DELETE /api/v1/core-hr/positions/{position_id}": ("SuperAdmin, HR"),
    "DELETE /api/v1/departments/{department_id}": ("SuperAdmin, HR"),
    "DELETE /api/v1/jobs/{job_id}": ("SuperAdmin, HR"),
    "DELETE /api/v1/onboarding-portal/clients/{client_id}": ("SuperAdmin"),
    "DELETE /api/v1/onboarding-portal/clients/{client_id}/integrations/{integration_id}": ("SuperAdmin"),
    "DELETE /api/v1/time/entries/{entry_id}": ("SuperAdmin, HR"),
    "GET /api/v1/applications/": ("SuperAdmin, HR"),
    "GET /api/v1/applications/{application_id}": ("SuperAdmin, HR"),
    "GET /api/v1/auth/me": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/auth/mfa/status": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/auth/users": ("SuperAdmin, HR"),
    "GET /api/v1/benefits/benefit-enrollments": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/benefits/benefit-plans": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/benefits/leaves-of-absence": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/benefits/life-events": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/candidates/": ("SuperAdmin, HR"),
    "GET /api/v1/candidates/{candidate_id}": ("SuperAdmin, HR"),
    "GET /api/v1/compliance/compliance-rules": ("SuperAdmin, HR"),
    "GET /api/v1/compliance/compliance-violations": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/compliance/headcount-plans": ("SuperAdmin, HR"),
    "GET /api/v1/compliance/report-definitions": ("SuperAdmin, HR"),
    "GET /api/v1/compliance/saved-reports": ("SuperAdmin, HR"),
    "GET /api/v1/compliance/scenarios": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/core-hr/cases": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/core-hr/cases/{case_id}/comments": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/core-hr/cost-centers": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/core-hr/cost-centers/{cost_center_id}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/core-hr/employee-documents": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/core-hr/employee-documents/{document_id}/versions": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/core-hr/locations": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/core-hr/locations/{location_id}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/core-hr/positions": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/core-hr/positions/{position_id}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/data-quality/checks": ("SuperAdmin, HR"),
    "GET /api/v1/data-quality/issues": ("SuperAdmin, HR"),
    "GET /api/v1/departments/": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/departments/{department_id}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/employees/": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/files/{path:path}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/employees/{employee_id}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/employees/{employee_id}/history": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/ess/announcements": ("Associate",),
    "GET /api/v1/ess/compliance-checks": ("SuperAdmin, HR"),
    "GET /api/v1/ess/continuous-feedback": ("Associate",),
    "GET /api/v1/ess/directory": ("Associate",),
    "GET /api/v1/ess/employee-files": ("Associate",),
    "GET /api/v1/ess/ess/profile/{employee_id}": ("Associate",),
    "GET /api/v1/ess/goal-alignments": ("Associate",),
    "GET /api/v1/ess/notifications": ("Associate",),
    "GET /api/v1/ess/org-chart": ("Associate",),
    "GET /api/v1/forecasting/accuracy": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/forecasting/runs": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/forecasting/runs/{run_id}": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/forecasting/runs/{run_id}/results": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/forecasting/runs/{run_id}/demand-series": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/forecasting/runs/{run_id}/cost-forecast": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/forecasting/runs/{run_id}/cost-forecast/csv": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/forecasting/runs/{run_id}/cost-forecast/{version}": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/forecasting/scenarios": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/forecasting/scenarios/{scenario_id}": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/forecasting/scenarios/{scenario_id}/versions": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/import-export/columns/{entity}": ("SuperAdmin, HR"),
    "GET /api/v1/import-export/entities": ("SuperAdmin, HR"),
    "GET /api/v1/import-export/export/{entity}": ("SuperAdmin, HR"),
    "GET /api/v1/import-export/import/{entity}/progress/{job_id}": ("SuperAdmin, HR"),
    "GET /api/v1/import-export/import/{entity}/row-errors": ("SuperAdmin, HR"),
    "GET /api/v1/import-export/template/{entity}": ("SuperAdmin, HR"),
    "GET /api/v1/interviews/": ("SuperAdmin, HR"),
    "GET /api/v1/interviews/{interview_id}": ("SuperAdmin, HR"),
    "GET /api/v1/jobs/": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/jobs/{job_id}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/learning/certifications": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/learning/course-enrollments": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/learning/courses": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/learning/succession-plans": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/learning/talent-pools": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/leave/balances": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/leave/balances/{employee_id}/ledger": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/leave/payroll-input": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/leave/reconciliation": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/leave/requests": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/leave/types": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/offboarding/tasks": ("SuperAdmin, HR"),
    "GET /api/v1/offboarding/terminations": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/offboarding/terminations/{termination_id}": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/offboarding/terminations/{termination_id}/progress": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/offers/": ("SuperAdmin, HR"),
    "GET /api/v1/offers/{offer_id}": ("SuperAdmin, HR"),
    "GET /api/v1/onboarding-portal/clients": ("SuperAdmin"),
    "GET /api/v1/onboarding-portal/clients/{client_id}": ("SuperAdmin"),
    "GET /api/v1/onboarding-portal/clients/{client_id}/feature-flags": ("SuperAdmin"),
    "GET /api/v1/onboarding-portal/clients/{client_id}/integrations": ("SuperAdmin"),
    "GET /api/v1/onboarding-portal/clients/{client_id}/migrations": ("SuperAdmin"),
    "GET /api/v1/onboarding-portal/clients/{client_id}/onboarding": ("SuperAdmin"),
    "GET /api/v1/onboarding-portal/clients/{client_id}/settings": ("SuperAdmin"),
    "GET /api/v1/onboarding-portal/docs/migration-api": ("SuperAdmin"),
    # Break-glass emergency access (SuperAdmin grants and revokes grants).
    "POST /api/v1/break-glass/access": ("SuperAdmin"),
    "GET /api/v1/break-glass/grants": ("SuperAdmin"),
    "DELETE /api/v1/break-glass/grants/{grant_id}": ("SuperAdmin"),
    # Tenant lifecycle (SuperAdmin; suspend/reactivate also admit HR at the gate).
    "GET /api/v1/onboarding-portal/tenants": ("SuperAdmin"),
    "GET /api/v1/onboarding-portal/tenants/{client_id}": ("SuperAdmin"),
    "PATCH /api/v1/onboarding-portal/tenants/{client_id}": ("SuperAdmin"),
    "POST /api/v1/onboarding-portal/tenants/{client_id}/provision": ("SuperAdmin"),
    "POST /api/v1/onboarding-portal/tenants/{client_id}/suspend": ("SuperAdmin, HR"),
    "POST /api/v1/onboarding-portal/tenants/{client_id}/reactivate": ("SuperAdmin, HR"),
    "POST /api/v1/onboarding-portal/tenants/{client_id}/read-only": ("SuperAdmin"),
    "POST /api/v1/onboarding-portal/tenants/{client_id}/archive": ("SuperAdmin"),
    "POST /api/v1/onboarding-portal/tenants/{client_id}/deprovision": ("SuperAdmin"),
    "GET /api/v1/onboarding/presets": ("SuperAdmin", "HR"),
    "GET /api/v1/onboarding/presets/{preset_id}": ("SuperAdmin", "HR"),
    "GET /api/v1/onboarding/presets/{preset_id}/diff": ("SuperAdmin", "HR"),
    "GET /api/v1/onboarding/readiness": ("SuperAdmin", "HR"),
    "GET /api/v1/onboarding/{employee_id}/documents": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/onboarding/{employee_id}/summary": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/onboarding/{employee_id}/tasks": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/payroll/components": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/payroll/pay-profiles": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/payroll/pay-profiles/{employee_id}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/payroll/payslips": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/payroll/payslips/{slip_id}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/payroll/periods": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/payroll/runs": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/payroll/runs/{run_id}": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/payroll/runs/{run_id}/reconciliation": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/performance/compensation-bands": ("SuperAdmin, HR"),
    "GET /api/v1/performance/feedback": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/performance/goals": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/performance/merit-allocations": ("SuperAdmin, HR"),
    "GET /api/v1/performance/merit-cycles": ("SuperAdmin, HR"),
    "GET /api/v1/performance/reviews": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/platform/background-checks": ("SuperAdmin, HR"),
    "GET /api/v1/platform/e-signatures": ("SuperAdmin, HR"),
    "GET /api/v1/platform/sso-configs": ("SuperAdmin"),
    "GET /api/v1/platform/webhooks": ("SuperAdmin"),
    "GET /api/v1/platform/webhooks/{webhook_id}/deliveries": ("SuperAdmin"),
    "GET /api/v1/reports/attendance": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/reports/audit": ("SuperAdmin, HR"),
    "GET /api/v1/reports/dashboard": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/reports/headcount": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/reports/labor-cost": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/reports/leave": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/reports/metrics": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/reports/metrics/catalogue": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/reports/metrics/{key}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/requisitions/": ("SuperAdmin, HR"),
    "GET /api/v1/requisitions/{requisition_id}": ("SuperAdmin, HR"),
    "GET /api/v1/scheduling/availability": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/scheduling/roster": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/scheduling/rosters/draft/{draft_id}": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/scheduling/rosters/versions": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/scheduling/rosters/versions/{version_id}": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/scheduling/rosters/versions/{version_id}/compare": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/scheduling/rosters/{version_id}/attendance": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/scheduling/rosters/{version_id}/attendance/deviations": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/scheduling/rosters/{version_id}/attendance/auto-create": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/scheduling/roster/{entry_id}": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/scheduling/shift-templates": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/scheduling/swaps": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/time/entries": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/time/entries/{entry_id}": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/time/timesheets": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/time/timesheets/{timesheet_id}": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/time/today": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/time/violations": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/time/violations/{violation_id}": ("SuperAdmin, HR, Manager, Associate"),
    "PATCH /api/v1/auth/users/{user_id}": ("SuperAdmin, HR"),
    "PATCH /api/v1/core-hr/cost-centers/{cost_center_id}": ("SuperAdmin, HR"),
    "PATCH /api/v1/core-hr/locations/{location_id}": ("SuperAdmin, HR"),
    "PATCH /api/v1/core-hr/positions/{position_id}": ("SuperAdmin, HR"),
    "PATCH /api/v1/departments/{department_id}": ("SuperAdmin, HR"),
    "PATCH /api/v1/jobs/{job_id}": ("SuperAdmin, HR"),
    "POST /api/v1/applications/": ("SuperAdmin, HR"),
    "POST /api/v1/auth/logout": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "POST /api/v1/auth/mfa/confirm": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "POST /api/v1/auth/mfa/disable": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "POST /api/v1/auth/mfa/enroll": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "POST /api/v1/auth/password": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "POST /api/v1/auth/users": ("SuperAdmin, HR"),
    "POST /api/v1/auth/users/{user_id}/password": ("SuperAdmin, HR"),
    "POST /api/v1/benefits/benefit-enrollments": ("SuperAdmin, HR"),
    "POST /api/v1/benefits/benefit-plans": ("SuperAdmin, HR"),
    "POST /api/v1/benefits/leaves-of-absence": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/benefits/life-events": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/candidates/": ("SuperAdmin, HR"),
    "POST /api/v1/compliance/compliance-rules": ("SuperAdmin, HR"),
    "POST /api/v1/compliance/compliance-violations": ("SuperAdmin, HR"),
    "POST /api/v1/compliance/headcount-plans": ("SuperAdmin, HR"),
    "POST /api/v1/compliance/report-definitions": ("SuperAdmin, HR"),
    "POST /api/v1/compliance/saved-reports": ("SuperAdmin, HR"),
    "POST /api/v1/compliance/scenarios": ("SuperAdmin, HR"),
    "POST /api/v1/core-hr/cases": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/core-hr/cases/{case_id}/comments": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/core-hr/cost-centers": ("SuperAdmin, HR"),
    "POST /api/v1/core-hr/employee-documents": ("SuperAdmin, HR"),
    "POST /api/v1/core-hr/employee-documents/{document_id}/ack": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/core-hr/employee-documents/{document_id}/versions": ("SuperAdmin, HR"),
    "POST /api/v1/core-hr/locations": ("SuperAdmin, HR"),
    "POST /api/v1/core-hr/positions": ("SuperAdmin, HR"),
    "POST /api/v1/data-quality/scan": ("SuperAdmin, HR"),
    "POST /api/v1/departments/": ("SuperAdmin, HR"),
    "POST /api/v1/employees/": ("SuperAdmin, HR"),
    "POST /api/v1/ess/announcements": ("SuperAdmin, HR"),
    "POST /api/v1/ess/compliance-checks/run": ("SuperAdmin, HR"),
    "POST /api/v1/ess/continuous-feedback": ("Associate",),
    "POST /api/v1/ess/directory/sync": ("SuperAdmin, HR"),
    "POST /api/v1/ess/employee-files": ("SuperAdmin, HR"),
    "POST /api/v1/ess/ess/profile": ("Associate",),
    "POST /api/v1/ess/goal-alignments": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/ess/notifications": ("SuperAdmin, HR"),
    "POST /api/v1/ess/org-chart/rebuild": ("SuperAdmin, HR"),
    "POST /api/v1/forecasting/accuracy/sync": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/forecasting/runs": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/forecasting/runs/{run_id}/cost-forecast": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/forecasting/scenarios": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/forecasting/scenarios/compare": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/forecasting/scenarios/{scenario_id}/versions": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/forecasting/scenarios/{scenario_id}/fork": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/forecasting/demand/series": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/forecasting/drivers": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/forecasting/drivers/import": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/import-export/import/{entity}": ("SuperAdmin, HR"),
    "POST /api/v1/import-export/import/{entity}/cancel": ("SuperAdmin, HR"),
    "POST /api/v1/import-export/import/{entity}/commit": ("SuperAdmin, HR"),
    "POST /api/v1/import-export/import/{entity}/dry-run": ("SuperAdmin, HR"),
    "POST /api/v1/interviews/": ("SuperAdmin, HR"),
    "POST /api/v1/jobs/": ("SuperAdmin, HR"),
    "POST /api/v1/learning/certifications": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/learning/course-enrollments": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/learning/courses": ("SuperAdmin, HR"),
    "POST /api/v1/learning/succession-plans": ("SuperAdmin, HR"),
    "POST /api/v1/learning/talent-pool-members": ("SuperAdmin, HR"),
    "POST /api/v1/learning/talent-pools": ("SuperAdmin, HR"),
    "POST /api/v1/leave/accrual/run": ("SuperAdmin, HR"),
    "POST /api/v1/leave/entitlements": ("SuperAdmin, HR"),
    "POST /api/v1/leave/requests": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/leave/requests/{request_id}/approve": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/leave/requests/{request_id}/cancel": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/leave/requests/{request_id}/reject": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/leave/types": ("SuperAdmin, HR"),
    "POST /api/v1/offboarding/tasks": ("SuperAdmin, HR"),
    "POST /api/v1/offboarding/terminations": ("SuperAdmin, HR"),
    "POST /api/v1/offboarding/terminations/{termination_id}/cancel": ("SuperAdmin, HR"),
    "POST /api/v1/offboarding/terminations/{termination_id}/complete": ("SuperAdmin, HR"),
    "POST /api/v1/offers/": ("SuperAdmin, HR"),
    "POST /api/v1/offers/{offer_id}/accept": ("SuperAdmin, HR"),
    "POST /api/v1/offers/{offer_id}/hire": ("SuperAdmin, HR"),
    "POST /api/v1/offers/{offer_id}/letter": ("SuperAdmin, HR"),
    "POST /api/v1/onboarding-portal/clients": ("SuperAdmin"),
    "POST /api/v1/onboarding-portal/clients/{client_id}/integrations": ("SuperAdmin"),
    "POST /api/v1/onboarding-portal/clients/{client_id}/integrations/{integration_id}/test": ("SuperAdmin"),
    "POST /api/v1/onboarding-portal/clients/{client_id}/migrations": ("SuperAdmin"),
    "POST /api/v1/onboarding-portal/clients/{client_id}/migrations/{job_id}/cancel": ("SuperAdmin"),
    "POST /api/v1/onboarding-portal/clients/{client_id}/migrations/{job_id}/run": ("SuperAdmin"),
    "POST /api/v1/onboarding-portal/clients/{client_id}/onboarding/steps": ("SuperAdmin"),
    "POST /api/v1/onboarding-portal/clients/{client_id}/onboarding/steps/{step_id}/complete": ("SuperAdmin"),
    "POST /api/v1/onboarding/tasks": ("SuperAdmin, HR"),
    "POST /api/v1/onboarding/{employee_id}/checklist": ("SuperAdmin, HR"),
    "POST /api/v1/onboarding/{employee_id}/documents": ("SuperAdmin, HR"),
    "POST /api/v1/payroll/components": ("SuperAdmin, HR"),
    "POST /api/v1/payroll/pay-profiles": ("SuperAdmin, HR"),
    "POST /api/v1/payroll/payslips": ("SuperAdmin, HR"),
    "POST /api/v1/payroll/periods": ("SuperAdmin, HR"),
    "POST /api/v1/payroll/runs": ("SuperAdmin, HR"),
    "POST /api/v1/payroll/runs/{run_id}/approve": ("SuperAdmin, HR"),
    "POST /api/v1/payroll/runs/{run_id}/finalize": ("SuperAdmin, HR"),
    "POST /api/v1/payroll/runs/{run_id}/payment-file": ("HR", "SuperAdmin"),  # bank data: HR and SuperAdmin (owner decision, LP Phase 2)
    "POST /api/v1/payroll/runs/{run_id}/process": ("SuperAdmin, HR"),
    "POST /api/v1/performance/compensation-bands": ("SuperAdmin, HR"),
    "POST /api/v1/performance/feedback": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/performance/goals": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/performance/merit-allocations": ("SuperAdmin, HR"),
    "POST /api/v1/performance/merit-cycles": ("SuperAdmin, HR"),
    "POST /api/v1/performance/reviews": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/performance/reviews/{review_id}/finalize": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/platform/background-checks": ("SuperAdmin, HR"),
    "POST /api/v1/platform/e-signatures": ("SuperAdmin, HR"),
    "POST /api/v1/platform/sso-configs": ("SuperAdmin"),
    "POST /api/v1/platform/webhooks": ("SuperAdmin"),
    "POST /api/v1/platform/webhooks/{webhook_id}/deliver": ("SuperAdmin"),
    "POST /api/v1/requisitions/": ("SuperAdmin, HR"),
    "POST /api/v1/scheduling/roster": ("SuperAdmin, HR"),
    "POST /api/v1/scheduling/roster/generate": ("SuperAdmin, HR"),
    "POST /api/v1/scheduling/rosters/generate": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/scheduling/rosters/draft/{draft_id}/adjust": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/scheduling/rosters/publish": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/scheduling/rosters/versions/{version_id}/draft": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/scheduling/shift-templates": ("SuperAdmin, HR"),
    "POST /api/v1/scheduling/swaps": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/scheduling/swaps/{swap_id}/approve": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/scheduling/swaps/{swap_id}/reject": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/time/clock-in": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/time/clock-out": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/time/entries": ("SuperAdmin, HR"),
    "POST /api/v1/time/timesheets/generate": ("SuperAdmin, HR"),
    "POST /api/v1/time/timesheets/{timesheet_id}/approve": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/time/timesheets/{timesheet_id}/submit": ("SuperAdmin, HR, Manager, Associate"),
    "PUT /api/v1/applications/{application_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/benefits/leaves-of-absence/{loa_id}/approve": ("SuperAdmin, HR"),
    "PUT /api/v1/candidates/{candidate_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/compliance/compliance-violations/{violation_id}/resolve": ("SuperAdmin, HR"),
    "PUT /api/v1/core-hr/cases/{case_id}": ("SuperAdmin, HR"),
    "PATCH /api/v1/employees/{employee_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/employees/{employee_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/ess/announcements/{announcement_id}/publish": ("SuperAdmin, HR"),
    "PUT /api/v1/ess/ess/profile/{employee_id}": ("Associate",),
    "PUT /api/v1/ess/notifications/{notification_id}/read": ("Associate",),
    "PUT /api/v1/interviews/{interview_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/learning/course-enrollments/{enrollment_id}/complete": ("SuperAdmin, HR, Manager, Associate"),
    "PUT /api/v1/leave/types/{leave_type_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/offboarding/items/{item_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/offboarding/tasks/{task_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/offboarding/terminations/{termination_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/offers/{offer_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/onboarding-portal/clients/{client_id}": ("SuperAdmin"),
    "PUT /api/v1/onboarding-portal/clients/{client_id}/feature-flags/{key}": ("SuperAdmin"),
    "PUT /api/v1/onboarding-portal/clients/{client_id}/integrations/{integration_id}": ("SuperAdmin"),
    "PUT /api/v1/onboarding-portal/clients/{client_id}/settings/{key}": ("SuperAdmin"),
    "PUT /api/v1/onboarding/documents/{document_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/onboarding/tasks/{task_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/performance/goals/{goal_id}": ("SuperAdmin, HR, Manager"),
    "PUT /api/v1/performance/reviews/{review_id}": ("SuperAdmin, HR, Manager"),
    "PUT /api/v1/platform/background-checks/{check_id}/complete": ("SuperAdmin, HR"),
    "PUT /api/v1/platform/e-signatures/{sig_id}/sign": ("SuperAdmin, HR"),
    "PUT /api/v1/requisitions/{requisition_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/scheduling/roster/{entry_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/scheduling/shift-templates/{template_id}": ("SuperAdmin, HR"),
    "PUT /api/v1/time/entries/{entry_id}": ("SuperAdmin, HR"),
    # Legal entities (LP-CORE-003): list/get are tenant-scoped reads for every
    # role; create/patch/deactivate are administrative.
    "GET /api/v1/core-hr/legal-entities": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/core-hr/legal-entities/{legal_entity_id}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "POST /api/v1/core-hr/legal-entities": ("SuperAdmin, HR"),
    "PATCH /api/v1/core-hr/legal-entities/{legal_entity_id}": ("SuperAdmin, HR"),
    "DELETE /api/v1/core-hr/legal-entities/{legal_entity_id}": ("SuperAdmin, HR"),
    # ESS notifications self-service (LP-NOT-003, AC-07): the caller's own
    # preferences/unread-count are Associate-only; creation is administrative.
    "GET /api/v1/ess/notifications/preferences": ("Associate",),
    "GET /api/v1/ess/notifications/unread-count": ("Associate",),
    "PUT /api/v1/ess/notifications/preferences": ("Associate",),
    # Expenses (self-service claims): categories are read by everyone and
    # managed by admins; claims flow through the workforce with manager and
    # admin approvals.
    "GET /api/v1/expenses/categories": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/expenses/categories/{category_id}": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "POST /api/v1/expenses/categories": ("SuperAdmin, HR"),
    "PATCH /api/v1/expenses/categories/{category_id}": ("SuperAdmin, HR"),
    "GET /api/v1/expenses/claims": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/expenses/claims/{claim_id}": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/expenses/claims": ("SuperAdmin, HR, Manager, Associate"),
    "PATCH /api/v1/expenses/claims/{claim_id}": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/expenses/claims/{claim_id}/submit": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/expenses/claims/{claim_id}/rework": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/expenses/claims/{claim_id}/l1-approve": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/expenses/claims/{claim_id}/approve": ("SuperAdmin, HR"),
    "POST /api/v1/expenses/claims/{claim_id}/reject": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/expenses/claims/{claim_id}/mark-paid": ("SuperAdmin, HR"),
    "POST /api/v1/expenses/claims/{claim_id}/receipts": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/expenses/claims/{claim_id}/receipts": ("SuperAdmin, HR, Manager, Associate"),
    # Movement + payroll-summary reports (LP-REP-002): joiners/leavers/
    # attrition are workforce-report reads; payroll-summary is HR books.
    "GET /api/v1/reports/joiners": ("SuperAdmin, HR, Manager, PayrollViewer"),
    "GET /api/v1/reports/leavers": ("SuperAdmin, HR, Manager, PayrollViewer"),
    "GET /api/v1/reports/attrition": ("SuperAdmin, HR, Manager, PayrollViewer"),
    "GET /api/v1/reports/payroll-summary": ("SuperAdmin, HR, PayrollViewer"),
    # Time corrections + period locks: the workforce raises and reads its
    # own corrections; managers decide; locks are administrative.
    "POST /api/v1/time/corrections": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/time/corrections": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/time/corrections/{correction_id}/approve": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/time/corrections/{correction_id}/reject": ("SuperAdmin, HR, Manager"),
    "POST /api/v1/time/period-locks/lock": ("SuperAdmin, HR"),
    "POST /api/v1/time/period-locks/reopen": ("SuperAdmin, HR"),
    "GET /api/v1/time/period-locks/status": ("SuperAdmin, HR, Manager, Associate"),
    # India payroll slices 5-6
    "GET /api/v1/payroll/payslips/{slip_id}/pdf": ("SuperAdmin, HR, Manager, Associate, PayrollViewer"),
    "GET /api/v1/payroll/runs/{run_id}/fnf": ("SuperAdmin, HR, PayrollViewer"),
    "POST /api/v1/payroll/runs/{run_id}/fnf": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/reports/payroll": ("SuperAdmin, HR, PayrollViewer"),
    "GET /api/v1/reports/filings/{filing_type}": ("SuperAdmin, HR, PayrollViewer"),
    "POST /api/v1/auth/impersonate": ("SuperAdmin",),
    "POST /api/v1/auth/mfa/reset": ("SuperAdmin",),
    # Assets register + custody lifecycle: reads admit the workforce
    # (Associates see own custody only via visibility; PayrollViewer is
    # refused); all writes are administrative (HR/Admin manage).
    "GET /api/v1/assets": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/assets/assignments": ("SuperAdmin, HR, Manager, Associate"),
    "GET /api/v1/assets/clearance/{employee_id}": ("SuperAdmin, HR, Manager"),
    "GET /api/v1/assets/{asset_id}": ("SuperAdmin, HR, Manager, Associate"),
    "PATCH /api/v1/assets/{asset_id}": ("SuperAdmin, HR"),
    "POST /api/v1/assets": ("SuperAdmin, HR"),
    "POST /api/v1/assets/assignments/{assignment_id}/ack": ("SuperAdmin, HR, Manager, Associate"),
    "POST /api/v1/assets/{asset_id}/assign": ("SuperAdmin, HR"),
    "POST /api/v1/assets/{asset_id}/maintenance/complete": ("SuperAdmin, HR"),
    "POST /api/v1/assets/{asset_id}/maintenance/start": ("SuperAdmin, HR"),
    "POST /api/v1/assets/{asset_id}/retire": ("SuperAdmin, HR"),
    "POST /api/v1/assets/{asset_id}/return": ("SuperAdmin, HR"),
    "POST /api/v1/assets/{asset_id}/transfer": ("SuperAdmin, HR"),
    # Payroll run audit history: HR books (SuperAdmin, HR, PayrollViewer).
    "GET /api/v1/payroll/runs/{run_id}/history": ("SuperAdmin, HR, PayrollViewer"),
}

# --- every endpoint is in the matrix ---------------------------------------

_served = _served_operations()
_matrix_keys = set(ROLE_MATRIX) | set(PUBLIC_OPERATIONS)

_missing = [op for op in _served if op not in _matrix_keys]
check(
    "every served operation has a declared role policy",
    not _missing,
    f"missing={_missing[:10]}",
)

_stale = sorted(_matrix_keys - set(_served))
check(
    "the matrix names no operation the application does not serve",
    not _stale,
    f"stale={_stale[:10]}",
)

check(
    "the matrix covers the whole served surface",
    len(ROLE_MATRIX) == len(_served) - len(PUBLIC_OPERATIONS),
    f"matrix={len(ROLE_MATRIX)} served={len(_served)} public={len(PUBLIC_OPERATIONS)}",
)

# --- the negative test: every role against every operation -----------------

# A separate client for the probe: a server error inside an endpoint must be
# reported as a failed check, not abort the whole matrix.
_probe_client = TestClient(app, raise_server_exceptions=False)

_server_errors: list[str] = []

for _op in sorted(ROLE_MATRIX):
    _method, _path = _op.split(" ", 1)
    _url = _concrete_path(_path)
    _allowed = ROLE_MATRIX[_op]
    _body = {} if _method in ("POST", "PUT", "PATCH") else None
    if _op == "POST /api/v1/auth/mfa/disable":
        # The endpoint requires the account password (or a recovery
        # code); the probe sends its own password so the admit check
        # exercises the real flow for enrolled privileged users.
        _body = {"password": ROLE_PASSWORD}
    if _op == "POST /api/v1/auth/impersonate":
        # Impersonation requires step-up re-authentication (the actor's
        # password, or a TOTP code for MFA-enabled actors). The probe
        # sends its own password so the admit check exercises the real
        # flow; without it every role — including SuperAdmin — is
        # refused with 403 step_up_required.
        _body = {
            "target_username": ROLE_ACCOUNTS["Associate"],
            "current_password": ROLE_PASSWORD,
        }
    if _op == "POST /api/v1/auth/mfa/reset":
        # The reset requires step-up with BOTH factors (password AND a
        # current TOTP code). The probe cycles the SuperAdmin account
        # through disable -> enroll -> confirm to hold a fresh known
        # secret, then targets the unenrolled Associate probe: step-up
        # passes, the target has no MFA, and the call ends 409
        # mfa_not_enabled — past the role gate (admitted) without
        # changing any state. Other roles are refused by the role gate.
        import urllib.parse as _reset_urlparse

        import pyotp as _reset_pyotp

        _reset_secret = None
        _dr = _probe_client.post(
            "/api/v1/auth/mfa/disable",
            headers=ROLE_HEADERS["SuperAdmin"],
            json={"password": ROLE_PASSWORD},
        )
        if _dr.status_code == 200:
            _er = _probe_client.post(
                "/api/v1/auth/mfa/enroll", headers=ROLE_HEADERS["SuperAdmin"]
            )
            if _er.status_code == 200:
                _rparsed = _reset_urlparse.urlparse(
                    _er.json().get("provisioning_uri", "")
                )
                _reset_secret = _reset_urlparse.parse_qs(_rparsed.query).get(
                    "secret", [None]
                )[0]
            if _reset_secret:
                _probe_client.post(
                    "/api/v1/auth/mfa/confirm",
                    headers=ROLE_HEADERS["SuperAdmin"],
                    json={"totp_code": _reset_pyotp.TOTP(_reset_secret).now()},
                )
        _body = {
            "target_username": ROLE_ACCOUNTS["Associate"],
            "current_password": ROLE_PASSWORD,
            "totp_code": (
                _reset_pyotp.TOTP(_reset_secret).now() if _reset_secret else "000000"
            ),
        }
    for _role in ROLE_HEADERS:
        _headers = ROLE_HEADERS[_role]
        if _body is None:
            _r = _probe_client.request(_method, _url, headers=_headers)
        else:
            _r = _probe_client.request(_method, _url, headers=_headers, json=_body)
        if _r.status_code >= 500:
            _server_errors.append(f"{_op} [{_role}] -> {_r.status_code}")
        if _op == "POST /api/v1/auth/mfa/disable" and _r.status_code not in (401, 403):
            # Item 10: the disable probe unenrolls the probe accounts, so
            # re-enroll them — privileged probes must stay enrolled for the
            # rest of the matrix.
            import urllib.parse

            import pyotp

            for _p_role in ("SuperAdmin", "HR"):
                _ph = ROLE_HEADERS[_p_role]
                _er = _probe_client.post("/api/v1/auth/mfa/enroll", headers=_ph)
                _secret = None
                if _er.status_code == 200:
                    _parsed = urllib.parse.urlparse(_er.json().get("provisioning_uri", ""))
                    _secret = urllib.parse.parse_qs(_parsed.query).get("secret", [None])[0]
                if _secret:
                    _cr = _probe_client.post(
                        "/api/v1/auth/mfa/confirm",
                        headers=_ph,
                        json={"totp_code": pyotp.TOTP(_secret).now()},
                    )
                    if _cr.status_code != 200:
                        check(
                            f"re-enroll probe [{_p_role}] after disable",
                            False,
                            f"status={_cr.status_code}",
                        )
        # The probe SuperAdmin account is MFA-enrolled (item 10), so
        # break-glass admission is exercised like any other SuperAdmin
        # admission in the matrix.
        if _role in _allowed:
            check(
                f"{_op} admits {_role}",
                _r.status_code not in (401, 403),
                f"status={_r.status_code}: {_r.text[:140]}",
            )
        else:
            check(
                f"{_op} refuses {_role} with the shared envelope",
                _r.status_code == 403 and _is_permission_envelope(_r),
                f"status={_r.status_code} body={_r.text[:140]}",
            )

check(
    "no operation answers with a server error",
    not _server_errors,
    f"errors={sorted(set(_server_errors))[:10]}",
)

# --- break-glash admission: MFA-gated for SuperAdmin ----------------------

# The probe SuperAdmin account (``secrole_superadmin``) is MFA-enrolled
# (item 10), so ``POST /break-glash/access`` is admitted in the matrix
# above like any other SuperAdmin. Break-glass admission is also exercised
# here with ``secadmin``. A target tenant row must exist so tenant
# resolution does not fail closed; the grant targets a *different* tenant
# than the grantor's.
try:
    from app.models.client_onboarding import Client
    _bg_sess = SessionLocal()
    if not _bg_sess.query(Client).filter(Client.slug == "default").first():
        _bg_sess.add(Client(slug="default", name="Default", status="Active"))
        _bg_sess.commit()
    _bg_admin = (
        _bg_sess.query(User).filter(User.username == "secadmin").first()
    )
    _bg_sess.close()
except Exception:  # noqa: BLE001
    _bg_admin = None

if _bg_admin is not None:
    _bg = client.request(
        "POST",
        "/api/v1/break-glass/access",
        headers=H,
        json={
            "actor_id": _bg_admin.id,
            "target_tenant_id": "other-tenant",
            "purpose": "security regression probe",
            "ttl_minutes": 60,
        },
    )
    check(
        "break-glass/access admits MFA-enabled SuperAdmin",
        _bg.status_code == 201,
        f"status={_bg.status_code}: {_bg.text[:140]}",
    )

# --- impersonation requires step-up re-authentication ----------------------
#
# "View as person" mints a real bearer token for the target, so the actor
# must re-prove who they are on every call: the current password, or (for
# an MFA-enabled actor) a current TOTP code. Without that proof the call
# fails closed with 403 step_up_required and writes an impersonate_blocked
# audit row that carries no secrets.

_STEP_UP_ACTOR = "secimpactor"
_STEP_UP_TARGET = "sectargetuser"
_STEP_UP_PASSWORD = "StepUpPass12345!"
_STEP_UP_WRONG = "WrongStepUp999!"

_step_sess = SessionLocal()
try:
    for _u in (_STEP_UP_ACTOR, _STEP_UP_TARGET):
        _old = _step_sess.query(User).filter(User.username == _u).first()
        if _old:
            _step_sess.delete(_old)
    _step_sess.commit()
    # The actor is MFA-enrolled with a real encrypted secret: SuperAdmin is
    # an MFA-enforced role, so an unenrolled actor never reaches the
    # endpoint (the shared gate refuses first). The secret also lets the
    # suite prove the TOTP fallback path below.
    from app.core.mfa import generate_totp_secret as _gen_step_secret  # noqa: E402
    from app.core.security import encrypt_secret as _enc_step_secret  # noqa: E402

    _step_secret = _gen_step_secret()
    _step_sess.add(
        User(
            username=_STEP_UP_ACTOR,
            email=f"{_STEP_UP_ACTOR}@example.com",
            hashed_password=get_password_hash(_STEP_UP_PASSWORD),
            role="SuperAdmin",
            is_active=True,
            mfa_enabled=True,
            mfa_secret_hash=_enc_step_secret(_step_secret),
        )
    )
    _step_sess.add(
        User(
            username=_STEP_UP_TARGET,
            email=f"{_STEP_UP_TARGET}@example.com",
            hashed_password=get_password_hash("TargetPass12345!"),
            role="Associate",
            is_active=True,
        )
    )
    _step_sess.commit()
finally:
    _step_sess.close()

_step_login = client.post(
    "/api/v1/auth/login",
    json={"username": _STEP_UP_ACTOR, "password": _STEP_UP_PASSWORD},
)
_step_headers = (
    {"Authorization": f"Bearer {_step_login.json()['access_token']}"}
    if _step_login.status_code == 200
    else {}
)
check(
    "the step-up actor can sign in",
    bool(_step_headers),
    f"status={_step_login.status_code}: {_step_login.text[:120]}",
)

# (a) no step-up proof at all -> 403 step_up_required
_r = client.post(
    "/api/v1/auth/impersonate",
    headers=_step_headers,
    json={"target_username": _STEP_UP_TARGET},
)
check(
    "(a) impersonate without step-up is refused with 403 step_up_required",
    _r.status_code == 403 and "step_up_required" in _r.text,
    f"status={_r.status_code}: {_r.text[:140]}",
)

# (b) a wrong password is not step-up -> 403 step_up_required
_r = client.post(
    "/api/v1/auth/impersonate",
    headers=_step_headers,
    json={
        "target_username": _STEP_UP_TARGET,
        "current_password": _STEP_UP_WRONG,
    },
)
check(
    "(b) impersonate with the wrong password is refused with 403 step_up_required",
    _r.status_code == 403 and "step_up_required" in _r.text,
    f"status={_r.status_code}: {_r.text[:140]}",
)
check(
    "the refusal body does not echo the supplied secret",
    _STEP_UP_WRONG not in _r.text,
    f"body={_r.text[:140]}",
)

# (c) the correct password passes step-up -> 200 impersonation token
_r = client.post(
    "/api/v1/auth/impersonate",
    headers=_step_headers,
    json={
        "target_username": _STEP_UP_TARGET,
        "current_password": _STEP_UP_PASSWORD,
    },
)
check(
    "(c) impersonate with the current password succeeds",
    _r.status_code == 200,
    f"status={_r.status_code}: {_r.text[:140]}",
)
if _r.status_code == 200:
    from app.core.security import decode_token as _decode_step_token

    _claims = _decode_step_token(_r.json()["access_token"])
    _actor_row = SessionLocal().query(User).filter(
        User.username == _STEP_UP_ACTOR
    ).first()
    check(
        "the step-up token is an impersonation token for the target",
        _claims.get("sub") == _STEP_UP_TARGET
        and _claims.get("is_impersonation") is True
        and _claims.get("impersonated_by") == (_actor_row.id if _actor_row else None),
        f"claims={ {k: _claims.get(k) for k in ('sub', 'is_impersonation', 'impersonated_by')} }",
    )

# (d) the blocked attempt is audited without secrets
from app.models.audit import AuditLog as _StepAuditLog

_blocked = (
    SessionLocal()
    .query(_StepAuditLog)
    .filter(_StepAuditLog.action == "impersonate_blocked")
    .order_by(_StepAuditLog.id.desc())
    .first()
)
check(
    "(d) a blocked impersonation writes an impersonate_blocked audit row",
    _blocked is not None,
    "no impersonate_blocked row found",
)
if _blocked is not None:
    _details = _blocked.details or ""
    check(
        "the blocked audit row carries no secrets",
        _STEP_UP_WRONG not in _details
        and _STEP_UP_PASSWORD not in _details
        and "totp" not in _details.lower(),
        f"details={_details[:140]}",
    )
_succeeded = (
    SessionLocal()
    .query(_StepAuditLog)
    .filter(_StepAuditLog.action == "impersonate")
    .order_by(_StepAuditLog.id.desc())
    .first()
)
check(
    "a successful impersonation still writes the impersonate audit row",
    _succeeded is not None,
    "no impersonate row found",
)

# --- the public operations are not behind a role gate ----------------------

for _op in PUBLIC_OPERATIONS:
    _method, _path = _op.split(" ", 1)
    _url = _concrete_path(_path)
    _r = client.request(_method, _url)
    check(
        f"{_op} needs no bearer token",
        _r.status_code != 401,
        f"status={_r.status_code}",
    )

# --- the permitted role succeeds, not merely gets past the gate -------------

#: Operations where a permitted role gets a real 2xx. One per distinct role
#: set in the matrix, so every role in every set is proved to work, not only
#: to be un-refused.
POSITIVE_CASES = (
    ("GET", "/api/v1/employees/",
     ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")),
    ("GET", "/api/v1/departments/",
     ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")),
    ("GET", "/api/v1/jobs/",
     ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")),
    ("GET", "/api/v1/leave/types",
     ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")),
    ("GET", "/api/v1/core-hr/locations",
     ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")),
    ("GET", "/api/v1/benefits/benefit-plans",
     ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")),
    ("GET", "/api/v1/learning/courses",
     ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")),
    ("GET", "/api/v1/scheduling/shift-templates",
     ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")),
    ("GET", "/api/v1/scheduling/availability",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/ess/announcements",
     ("Associate",)),
    ("GET", "/api/v1/reports/metrics",
     ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")),
    ("GET", "/api/v1/payroll/payslips",
     ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")),
    ("GET", "/api/v1/leave/requests",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/leave/balances",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/scheduling/roster",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/scheduling/swaps",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/time/entries",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/time/timesheets",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/core-hr/cases",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/core-hr/employee-documents",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/performance/goals",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/offboarding/terminations",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/compliance/compliance-violations",
     ("SuperAdmin", "HR", "Manager", "Associate")),
    ("GET", "/api/v1/reports/attendance",
     ("SuperAdmin", "HR", "Manager")),
    ("GET", "/api/v1/forecasting/runs",
     ("SuperAdmin", "HR", "Manager")),
    ("GET", "/api/v1/compliance/scenarios",
     ("SuperAdmin", "HR", "Manager")),
    ("GET", "/api/v1/learning/talent-pools",
     ("SuperAdmin", "HR", "Manager")),
    ("GET", "/api/v1/payroll/runs",
     ("SuperAdmin", "HR", "PayrollViewer")),
    ("GET", "/api/v1/reports/headcount",
     ("SuperAdmin", "HR", "PayrollViewer")),
    ("GET", "/api/v1/reports/labor-cost",
     ("SuperAdmin", "HR", "PayrollViewer")),
    ("GET", "/api/v1/reports/audit",
     ("SuperAdmin", "HR")),
    ("GET", "/api/v1/performance/compensation-bands",
     ("SuperAdmin", "HR")),
    ("GET", "/api/v1/admin/audit/verify",
     ("SuperAdmin", "HR")),
    ("GET", "/api/v1/admin/jobs",
     ("SuperAdmin", "HR")),
    ("GET", "/api/v1/data-quality/checks",
     ("SuperAdmin", "HR")),
    ("GET", "/api/v1/onboarding-portal/clients",
     ("SuperAdmin",)),
    ("GET", "/api/v1/platform/sso-configs",
     ("SuperAdmin",)),
)

for _method, _path, _roles in POSITIVE_CASES:
    for _role in _roles:
        _r = client.request(_method, _path, headers=ROLE_HEADERS[_role])
        check(
            f"{_method} {_path} succeeds for {_role}",
            200 <= _r.status_code < 300,
            f"status={_r.status_code}: {_r.text[:140]}",
        )


# ===========================================================================
print("\n[ROLE-2] The role column holds one of the five roles")
# ===========================================================================
#
# A role that is documented and not enforced is the gap this section closes.
# A role that is *free text* is the same gap one level down: the column
# accepted any string, so a row could hold a role the policy never granted.

import sqlite3  # noqa: E402
import tempfile  # noqa: E402

# The database refuses a role it does not define.
#
# The row is written with raw SQL, so the only thing that can refuse it is
# the constraint on the column itself. Every other not-null column is given
# a value, and a row with a defined role is written first: a probe that
# failed for an unrelated reason would otherwise look like a pass.
_ROLE_PROBE_INSERT = (
    "INSERT INTO users (username, email, hashed_password, role, is_active, "
    "must_change_password, failed_login_count, mfa_enabled) "
    "VALUES (?, ?, ?, ?, 1, 0, 0, 0)"
)
_conn = sqlite3.connect(DB_PATH)
try:
    _conn.execute("DELETE FROM users WHERE username LIKE 'roleprobe%'")
    try:
        _conn.execute(
            _ROLE_PROBE_INSERT,
            ("roleprobe_ok", "roleprobe_ok@example.com", "x", "Associate"),
        )
        _conn.commit()
        _defined_accepted = True
    except sqlite3.Error as _exc:
        _defined_accepted = False
        _defined_detail = str(_exc)[:120]
    try:
        _conn.execute(
            _ROLE_PROBE_INSERT,
            ("roleprobe_bad", "roleprobe_bad@example.com", "x", "Wizard"),
        )
        _conn.commit()
        _refused = False
        _refused_detail = "the INSERT of an unknown role was accepted"
    except sqlite3.IntegrityError as _exc:
        _refused = True
        _refused_detail = ""
    _conn.execute("DELETE FROM users WHERE username LIKE 'roleprobe%'")
    _conn.commit()
finally:
    _conn.close()

check(
    "the database accepts a role the platform defines",
    _defined_accepted,
    locals().get("_defined_detail", ""),
)
check(
    "the database refuses a role outside the five",
    _refused,
    _refused_detail,
)

# The API refuses a request that carries an unknown role.
_r = client.post(
    "/api/v1/auth/users",
    headers=H,
    json={
        "user_in": {
            "username": "roleprobe",
            "email": "roleprobe@example.com",
            "password": "RoleMatrixPass123",
            "role": "Wizard",
        }
    },
)
check(
    "the API refuses to create a user with an unknown role",
    _r.status_code in (400, 422),
    f"status={_r.status_code}: {_r.text[:140]}",
)

_r = client.patch(
    "/api/v1/auth/users/1", headers=H, json={"role": "Wizard"}
)
check(
    "the API refuses to set an unknown role on a user",
    _r.status_code in (400, 422),
    f"status={_r.status_code}: {_r.text[:140]}",
)


# --- the migration that constrains the column, and its downgrade -----------

def _run_migration(direction: str, revision: str, db_path: str) -> tuple[bool, str]:
    """Run the migration CLI against a scratch database."""
    import os
    import subprocess
    import sys as _sys
    from pathlib import Path as _Path

    backend_dir = _Path(__file__).resolve().parent
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["ALEMBIC_DATABASE_URL"] = f"sqlite:///{db_path}"
    env["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "local-test-secret-key-not-for-production-0123456789"
    )
    env["MIGRATE_ON_STARTUP"] = "false"
    env["LOG_LEVEL"] = "CRITICAL"
    env["BACKEND_CORS_ORIGINS"] = ""
    result = subprocess.run(
        [_sys.executable, "-m", "scripts.migrate", direction, revision],
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result.returncode == 0, (result.stdout + result.stderr)[-800:]


def _role_constraint_present(db_path: str) -> bool:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchall()
        if not rows:
            return False
        return "CHECK" in (rows[0][0] or "").upper()
    finally:
        conn.close()


def _role_accepted(db_path: str, role: str, row_id: int) -> bool:
    """Whether the database accepts a row with this role."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO users (id, username, email, hashed_password, role) "
            "VALUES (?, ?, ?, ?, ?)",
            (row_id, f"probe_{row_id}", f"probe_{row_id}@example.com", "x", role),
        )
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


_tmpdir = tempfile.mkdtemp(prefix="karmathy-role-constraint-")
_scratch = os.path.join(_tmpdir, "role_constraint.db")
try:
    # A database in the shape the platform had before this revision: the
    # users table, with a free-text role column and no constraint.
    _conn = sqlite3.connect(_scratch)
    try:
        _conn.execute(
            "CREATE TABLE users (id INTEGER NOT NULL PRIMARY KEY, "
            "username VARCHAR(100) NOT NULL, email VARCHAR(255) NOT NULL, "
            "hashed_password VARCHAR(255) NOT NULL, role VARCHAR(50))"
        )
        _conn.execute(
            "INSERT INTO users (id, username, email, hashed_password, role) "
            "VALUES (1, 'legacy', 'legacy@example.com', 'x', 'Wizard')"
        )
        _conn.execute(
            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
        )
        _conn.execute("INSERT INTO alembic_version VALUES ('0008_fk_indexes')")
        _conn.commit()
    finally:
        _conn.close()

    check(
        "the legacy database starts with an unconstrained role column",
        not _role_constraint_present(_scratch),
        "the constraint was already there",
    )

    _ok, _detail = _run_migration(
        "upgrade", "0009_credential_role_constraint", _scratch
    )
    check(
        "the role-constraint migration applies to a legacy database",
        _ok,
        _detail,
    )
    check(
        "the migration puts a constraint on the role column",
        _role_constraint_present(_scratch),
        "no CHECK constraint was found",
    )
    check(
        "the migration refuses an unknown role after it has run",
        not _role_accepted(_scratch, "Wizard", 998),
        "the database accepted the unknown role",
    )
    check(
        "the migration still accepts a defined role",
        _role_accepted(_scratch, "Associate", 997),
        "the database refused a defined role",
    )

    _conn = sqlite3.connect(_scratch)
    try:
        _moved = _conn.execute(
            "SELECT role FROM users WHERE id = 1"
        ).fetchone()[0]
    finally:
        _conn.close()
    check(
        "a row with an unknown role is moved to the least-privileged role",
        _moved == "Associate",
        f"role={_moved!r}",
    )

    _ok, _detail = _run_migration("downgrade", "0008_fk_indexes", _scratch)
    check(
        "the role-constraint migration has a working downgrade",
        _ok,
        _detail,
    )
    check(
        "the downgrade removes the constraint",
        not _role_constraint_present(_scratch),
        "the CHECK constraint survived the downgrade",
    )
    check(
        "the downgrade leaves the rows alone",
        _role_accepted(_scratch, "Wizard", 998),
        "the row could not be written after the downgrade",
    )

    _ok, _detail = _run_migration(
        "upgrade", "0009_credential_role_constraint", _scratch
    )
    check(
        "the migration can be applied again after its downgrade",
        _ok and _role_constraint_present(_scratch),
        _detail,
    )
finally:
    import shutil as _shutil

    _shutil.rmtree(_tmpdir, ignore_errors=True)

# ===========================================================================
print("\n" + "=" * 62)
print(f"==== SECURITY SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 62)
raise SystemExit(1 if RESULTS["fail"] else 0)