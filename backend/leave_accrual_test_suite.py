"""Leave accrual and carry-over (LP-LEAVE accrual gap).

What this suite proves
----------------------
* one month's run posts ``round(max_days_per_year / 12, 2)`` per active
  employee and leave type, and the derived balance moves by exactly that;
* a second run for the same month posts nothing: every balance is skipped
  as a duplicate and the balances do not move (double-run safe);
* the January run carries the prior year's unused balance forward in full
  (no cap field exists on the leave type), and an empty or fully-used
  prior year carries nothing;
* the ``leave_accrual`` job type is registered on the worker's registry, a
  bad payload is refused as invalid input, and the handler executes the
  same math end to end;
* POST /leave/accrual/run enqueues the job (202) and enqueuing the same
  month twice returns the same job (queue-level idempotency).

The formula is documented in app/services/leave_accrual.py; these tests
pin it: monthly accrual = max_days_per_year / 12, carry-over = the whole
unused prior-year balance.

Run:  python leave_accrual_test_suite.py
"""
import datetime
import os
import tempfile
from decimal import Decimal

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="leave_accrual_test_suite_"), "leave_accrual_test_suite.db")
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
from app.jobs.errors import JobInputInvalid  # noqa: E402
from app.jobs.registry import get_handler  # noqa: E402
from app.main import app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.job_queue import JobType  # noqa: E402
from app.models.leave import LeaveLedgerEntryType, LeaveType  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import leave as ledger  # noqa: E402
from app.services import leave_accrual as accrual  # noqa: E402

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

PASSWORD = "LeaveAccrPass123"

db = SessionLocal()
dept = Department(name="Accrual", code="ACC")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Accrual Analyst", code="ACCRUAL", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def _employee(code: str) -> Employee:
    person = Employee(
        employee_id=code,
        first_name="Accrue",
        last_name=code,
        email=f"{code.lower()}@example.com",
        hire_date=datetime.date(2024, 1, 1),
        job_id=job.id,
        department_id=dept.id,
        status="Active",
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


emp_a = _employee("ACC-A")
emp_b = _employee("ACC-B")

annual = LeaveType(name="Annual", code="ANN-ACCR", max_days_per_year=12)
zero_grant = LeaveType(name="Unpaid", code="UNP-ACCR", max_days_per_year=0)
db.add_all([annual, zero_grant])
db.commit()
db.refresh(annual)
db.refresh(zero_grant)
ANNUAL_ID = annual.id

db.add(
    User(
        username="accr_hr",
        email="accr_hr@example.com",
        hashed_password=get_password_hash(PASSWORD),
        role="SuperAdmin",
        is_active=True,
        mfa_enabled=True,
    )
)
db.commit()

# Prior year: A has 12 entitled and 2 used (10 unused); B has no balance.
from app.models.leave import LeaveBalance  # noqa: E402

prior_a = LeaveBalance(
    employee_id=emp_a.id,
    leave_type_id=annual.id,
    entitlement_year=2025,
    entitled_days=Decimal("0"),
    carried_over_days=Decimal("0"),
    used_days=Decimal("0"),
)
db.add(prior_a)
ledger.post_entry(db, prior_a, LeaveLedgerEntryType.ENTITLEMENT, Decimal("12"),
                  reference_type="entitlement", reference_id=None,
                  description="prior year grant")
ledger.post_entry(db, prior_a, LeaveLedgerEntryType.USAGE, Decimal("-2"),
                  reference_type="leave_request", reference_id=1,
                  description="prior year leave taken")
db.commit()
EMP_A_ID = emp_a.id
EMP_B_ID = emp_b.id
db.close()

client = TestClient(app, raise_server_exceptions=False)
H_HR = {"Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'username': 'accr_hr', 'password': PASSWORD}).json()['access_token']}"}


def _derived(employee_id: int, year: int) -> Decimal:
    s = SessionLocal()
    try:
        bal = ledger.find_balance(s, employee_id, ANNUAL_ID, year)
        return ledger.derived_available_days(s, bal) if bal else Decimal("-999")
    finally:
        s.close()


# ===========================================================================
print("\n[ACCR-1] Monthly accrual moves the balance by max_days/12")
# ===========================================================================
s = SessionLocal()
report = accrual.run_accrual(s, 2026, 3)
s.commit()
s.close()
check("march run posts two accruals (one per employee)", report["accruals_posted"] == 2, f"{report}")
check("zero-grant type accrues nothing", report["accruals_skipped_zero_grant"] == 2, f"{report}")
check("A's 2026 balance is exactly 1.00", _derived(EMP_A_ID, 2026) == Decimal("1.00"), f"got {_derived(EMP_A_ID, 2026)}")
check("B's 2026 balance is exactly 1.00", _derived(EMP_B_ID, 2026) == Decimal("1.00"), f"got {_derived(EMP_B_ID, 2026)}")

# ===========================================================================
print("\n[ACCR-2] Double-run safe: the same month posts nothing twice")
# ===========================================================================
s = SessionLocal()
again = accrual.run_accrual(s, 2026, 3)
s.commit()
s.close()
check("re-run posts nothing", again["accruals_posted"] == 0, f"{again}")
check("re-run skips both as duplicates", again["accruals_skipped_duplicate"] == 2, f"{again}")
check("balances unchanged after re-run", _derived(EMP_A_ID, 2026) == Decimal("1.00") and _derived(EMP_B_ID, 2026) == Decimal("1.00"), "")

# ===========================================================================
print("\n[ACCR-3] January carry-over: full unused balance, empty stays empty")
# ===========================================================================
s = SessionLocal()
jan = accrual.run_accrual(s, 2026, 1)
s.commit()
s.close()
check("one carry-over posted (A's unused 10)", jan["carry_overs_posted"] == 1, f"{jan}")
check("B with no prior balance carries nothing", jan["carry_overs_skipped_empty"] == 1, f"{jan}")
check("A's 2026 balance is mar 1.00 + jan 1.00 accrual + 10.00 carried = 12.00", _derived(EMP_A_ID, 2026) == Decimal("12.00"), f"got {_derived(EMP_A_ID, 2026)}")
check("B's 2026 balance is the two monthly accruals = 2.00", _derived(EMP_B_ID, 2026) == Decimal("2.00"), f"got {_derived(EMP_B_ID, 2026)}")

s = SessionLocal()
jan2 = accrual.run_accrual(s, 2026, 1)
s.commit()
s.close()
check("january re-run is fully duplicate-safe", jan2["accruals_posted"] == 0 and jan2["carry_overs_posted"] == 0, f"{jan2}")
check("balances unchanged after january re-run", _derived(EMP_A_ID, 2026) == Decimal("12.00"), f"got {_derived(EMP_A_ID, 2026)}")

# ===========================================================================
print("\n[ACCR-4] Fully-used prior year carries nothing (boundary)")
# ===========================================================================
s = SessionLocal()
prior_b = LeaveBalance(employee_id=EMP_B_ID, leave_type_id=ANNUAL_ID, entitlement_year=2024,
                        entitled_days=Decimal("0"), carried_over_days=Decimal("0"), used_days=Decimal("0"))
s.add(prior_b)
ledger.post_entry(s, prior_b, LeaveLedgerEntryType.ENTITLEMENT, Decimal("12"),
                  reference_type="entitlement", reference_id=None, description="grant")
ledger.post_entry(s, prior_b, LeaveLedgerEntryType.USAGE, Decimal("-12"),
                  reference_type="leave_request", reference_id=2, description="all used")
s.commit()
feb25 = accrual.run_accrual(s, 2025, 1)
s.commit()
s.close()
check("fully-used prior year posts no carry-over", feb25["carry_overs_posted"] == 0, f"{feb25}")
s2 = SessionLocal()
from app.models.leave import LeaveLedger  # noqa: E402
rows = s2.query(LeaveLedger).join(LeaveBalance).filter(
    LeaveBalance.employee_id == EMP_B_ID, LeaveBalance.entitlement_year == 2025,
    LeaveLedger.entry_type == LeaveLedgerEntryType.CARRY_OVER).all()
s2.close()
check("no carry-over row written for the used-up year", rows == [], f"{rows}")

# ===========================================================================
print("\n[ACCR-5] Job type registered; handler runs; bad input refused")
# ===========================================================================
handler = get_handler(JobType.LEAVE_ACCRUAL)
check("leave_accrual handler is registered on the worker registry", handler is not None, "")


class _StubJob:
    id = 4242
    attempts = 0
    max_attempts = 5


report = handler(_StubJob(), {"year": 2026, "month": 4})
check("handler executes and reports the month", report.get("accruals_posted") == 2 and report.get("job_id") == 4242, f"{report}")
check("handler's accrual lands in the ledger", _derived(EMP_A_ID, 2026) == Decimal("13.00"), f"got {_derived(EMP_A_ID, 2026)}")

try:
    handler(_StubJob(), {"year": 2026, "month": 13})
    check("month 13 is refused", False, "no exception raised")
except JobInputInvalid:
    check("month 13 is refused", True, "")
except Exception as exc:  # noqa: BLE001
    check("month 13 is refused", False, f"wrong exception: {type(exc).__name__}: {exc}")

# ===========================================================================
print("\n[ACCR-6] POST /leave/accrual/run enqueues; same month dedups")
# ===========================================================================
r = client.post("/api/v1/leave/accrual/run", headers=H_HR, json={"year": 2026, "month": 5})
check("enqueue answers 202 with the job", r.status_code == 202 and r.json().get("job_type") == "leave_accrual", f"{r.status_code} {r.text[:200]}")
first_id = r.json().get("job_id") if r.status_code == 202 else None
# The queue dedups on (job_type, input_hash) once the job has succeeded:
# complete the month's job, then enqueuing the same month must return it.
s = SessionLocal()
from app.models.job_queue import JobQueue  # noqa: E402
row = s.query(JobQueue).filter(JobQueue.id == first_id).first()
row.state = "succeeded"
s.commit()
s.close()
r = client.post("/api/v1/leave/accrual/run", headers=H_HR, json={"year": 2026, "month": 5})
check("same month re-enqueue after success is a no-op", r.status_code == 202 and r.json().get("job_id") == first_id, f"{r.status_code} {r.text[:200]}")
r = client.post("/api/v1/leave/accrual/run", headers=H_HR, json={"year": 2026, "month": 99})
check("month 99 is a 422", r.status_code == 422, f"{r.status_code} {r.text[:200]}")

# ===========================================================================
print()
print("----------------------------------------------------------------")
print(f"leave accrual tests: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("----------------------------------------------------------------")
raise SystemExit(1 if RESULTS["fail"] else 0)
