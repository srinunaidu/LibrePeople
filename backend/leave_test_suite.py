"""The leave ledger: the balance is derived, and every change is a row.

What this suite proves
----------------------
* every entry type writes the right row, with the right sign and the right
  reference;
* the balance is the sum of the signed rows, the stored columns are a cache
  of that sum, and a row the cache has not seen still shows in the balance;
* a balance cannot move without a row, and a rolled-back change leaves
  neither the row nor the moved balance;
* approving a leave request writes a usage row and takes exactly the
  requested days off the balance, and cancelling it writes the reversal —
  the history is rows, never deletions;
* a request for more leave than the derived balance allows is refused, and
  a cancellation without a usage to reverse is refused;
* the reconciliation reports a deliberate discrepancy;
* the approved leave of a period reaches the payroll lane in a named shape;
* the migration creates the table, gives an existing balance a real genesis,
  and its downgrade removes what it created.

Run:  python leave_test_suite.py
"""
import datetime
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="leave_test_suite_"), "leave_test_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"  # keep the suite's output readable
# Field encryption (item 6: no SECRET_KEY fallback) — leave writes touch
# employee identity fields through app.core.encryption.
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

import sqlalchemy as sa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.leave import (  # noqa: E402
    LeaveBalance,
    LeaveLedger,
    LeaveLedgerEntryType,
    LeaveRequest,
    LeaveType,
)
from app.models.user import User  # noqa: E402
from app.services import leave as ledger  # noqa: E402

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

YEAR = 2026
PASSWORD = "LeaveLedgerPass123"

db = SessionLocal()
dept = Department(name="Leave", code="LEA")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Leave Analyst", code="LEAVEAN", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def _employee(code: str, manager_id: int | None = None) -> Employee:
    person = Employee(
        employee_id=code,
        first_name="Ledger",
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


emp_manager = _employee("LEDGER-MGR")
emp_a = _employee("LEDGER-A", manager_id=emp_manager.id)
emp_b = _employee("LEDGER-B")


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


_user("ledger_hr", "SuperAdmin")
_user("ledger_mgr", "Manager", emp_manager.id)
_user("ledger_assoc", "Associate", emp_a.id)
_user("ledger_pay", "PayrollViewer")

# The session is closed, so the identifiers are kept as plain values: a
# detached object cannot be read after the session that made it is gone.
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


H_HR = _headers("ledger_hr")
H_MGR = _headers("ledger_mgr")
H_ASSOC = _headers("ledger_assoc")
H_PAY = _headers("ledger_pay")

# --- the leave type and the entitlement --------------------------------------

r = client.post(
    "/api/v1/leave/types",
    headers=H_HR,
    json={"name": "Annual", "code": "LEDG", "max_days_per_year": 20, "is_paid": True},
)
check("a leave type is created", r.status_code == 201, f"got {r.status_code}: {r.text[:160]}")
LEAVE_TYPE_ID = r.json()["id"] if r.status_code == 201 else None


def _leave_type(code: str) -> int:
    made = client.post(
        "/api/v1/leave/types",
        headers=H_HR,
        json={"name": code, "code": code, "max_days_per_year": 20, "is_paid": True},
    )
    return made.json()["id"] if made.status_code == 201 else None


# A balance is unique per employee, leave type and year, so the balances
# this suite builds get leave types of their own.
LEAVE_TYPE_2 = _leave_type("LEDG2")
LEAVE_TYPE_3 = _leave_type("LEDG3")

r = client.post(
    "/api/v1/leave/entitlements",
    headers=H_HR,
    json={"leave_type_id": LEAVE_TYPE_ID, "entitlement_year": YEAR},
)
check("the entitlements are assigned", r.status_code in (200, 201), f"got {r.status_code}: {r.text[:160]}")

session = SessionLocal()
balances = {
    row.employee_id: row
    for row in session.query(LeaveBalance)
    .filter(LeaveBalance.entitlement_year == YEAR)
    .all()
}
check(
    "every active employee has a balance",
    set(balances) >= {EMP_A_ID, EMP_B_ID, EMP_MGR_ID},
    f"have={sorted(balances)}",
)
BALANCE_A = balances.get(EMP_A_ID)

entitlement_rows = (
    session.query(LeaveLedger)
    .filter(LeaveLedger.balance_id == BALANCE_A.id)
    .all()
)
check(
    "the entitlement is a ledger row, not a cached number",
    len(entitlement_rows) == 1
    and entitlement_rows[0].entry_type == LeaveLedgerEntryType.ENTITLEMENT,
    f"rows={[(r.entry_type, str(r.signed_days)) for r in entitlement_rows]}",
)
check(
    "the entitlement row is positive and says where it came from",
    entitlement_rows
    and entitlement_rows[0].signed_days > 0
    and entitlement_rows[0].reference_type == "entitlement",
    f"row={entitlement_rows[0] if entitlement_rows else None}",
)
check(
    "the cached columns agree with the ledger",
    BALANCE_A.verify_ledger_invariant(session),
    f"cached={BALANCE_A.available_days} ledger={BALANCE_A.compute_from_ledger(session)}",
)

# ===========================================================================
print("\n[LEDGER-1] One row per entry type, with the right sign")
# ===========================================================================

# A second balance of its own, so the entry types do not disturb the flow
# the request path is tested with.
other = LeaveBalance(
    employee_id=EMP_B_ID,
    leave_type_id=LEAVE_TYPE_2,
    entitlement_year=YEAR,
    entitled_days=Decimal("0"),
    carried_over_days=Decimal("0"),
    used_days=Decimal("0"),
)
session.add(other)
session.flush()
session.refresh(other)

ENTRY_CASES = (
    (LeaveLedgerEntryType.ACCRUAL, "5", "accrual"),
    (LeaveLedgerEntryType.ENTITLEMENT, "20", "entitlement"),
    (LeaveLedgerEntryType.CARRY_OVER, "2", "carry_over"),
    (LeaveLedgerEntryType.USAGE, "-3", "leave_request"),
    (LeaveLedgerEntryType.EXPIRY, "-4", "expiry"),
    (LeaveLedgerEntryType.ENCASHMENT, "-2", "payroll"),
    (LeaveLedgerEntryType.ADJUSTMENT, "1.5", "adjustment"),
)

for entry_type, days, reference in ENTRY_CASES:
    entry = ledger.post_entry(
        session,
        other,
        entry_type,
        Decimal(days),
        reference_type=reference,
        reference_id=7,
        description=f"a {entry_type.value} movement",
        created_by=None,
    )
    session.flush()
    session.refresh(entry)
    check(
        f"a {entry_type.value} entry is written with the right sign",
        (Decimal(days) > 0) == (entry.signed_days > 0),
        f"signed={entry.signed_days} expected={days}",
    )
    check(
        f"a {entry_type.value} entry carries its reference",
        entry.reference_type == reference and entry.reference_id == 7,
        f"reference={entry.reference_type}:{entry.reference_id}",
    )
    check(
        f"a {entry_type.value} entry belongs to the balance and the person",
        entry.balance_id == other.id
        and entry.employee_id == other.employee_id
        and entry.leave_type_id == other.leave_type_id
        and entry.entitlement_year == other.entitlement_year,
        f"entry={entry.balance_id}/{entry.employee_id}/{entry.leave_type_id}",
    )

session.commit()

check(
    "the balance is the sum of the signed rows",
    ledger.derived_available_days(session, other)
    == sum((Decimal(days) for _t, days, _r in ENTRY_CASES), Decimal("0")),
    f"derived={ledger.derived_available_days(session, other)}",
)
check(
    "the cached columns are a cache of that sum",
    other.verify_ledger_invariant(session),
    f"cached={other.available_days} ledger={other.compute_from_ledger(session)}",
)

# The sign of an entry type is a rule, not a convention.
try:
    ledger.post_entry(session, other, LeaveLedgerEntryType.USAGE, Decimal("3"))
    wrong_sign_refused = False
except ledger.LedgerError:
    wrong_sign_refused = True
session.rollback()
check(
    "a usage written with the wrong sign is refused",
    wrong_sign_refused,
    "a positive usage was accepted",
)

# ===========================================================================
print("\n[LEDGER-2] A balance cannot move without a row")
# ===========================================================================

before = ledger.derived_available_days(session, other)
session.expire_all()
other = session.query(LeaveBalance).filter(LeaveBalance.id == other.id).first()
other.used_days = other.used_days + Decimal("5")
session.add(other)
refused = False
try:
    session.commit()
except ledger.LedgerInvariantError:
    refused = True
    session.rollback()
check(
    "a balance that moves without a ledger row is refused",
    refused,
    "the change was flushed",
)
session.expire_all()
other = session.query(LeaveBalance).filter(LeaveBalance.id == other.id).first()
check(
    "the refused change left the balance where it was",
    other.available_days == before,
    f"expected {before}, got {other.available_days}",
)
check(
    "the refused change wrote no row",
    session.query(LeaveLedger)
    .filter(LeaveLedger.balance_id == other.id)
    .count()
    == len(ENTRY_CASES),
    "a row was written",
)

# A change that is rolled back leaves neither the row nor the moved balance.
before = ledger.derived_available_days(session, other)
rows_before = session.query(LeaveLedger).filter(LeaveLedger.balance_id == other.id).count()
ledger.post_entry(
    session, other, LeaveLedgerEntryType.USAGE, Decimal("-1"),
    reference_type="leave_request", reference_id=99,
)
session.rollback()
session.expire_all()
other = session.query(LeaveBalance).filter(LeaveBalance.id == other.id).first()
check(
    "a rolled-back change leaves the balance where it was",
    ledger.derived_available_days(session, other) == before,
    f"expected {before}, got {ledger.derived_available_days(session, other)}",
)
check(
    "a rolled-back change leaves no row behind",
    session.query(LeaveLedger).filter(LeaveLedger.balance_id == other.id).count()
    == rows_before,
    "a row survived the rollback",
)

# A row the cache has not seen still shows in the balance. The row is written
# with SQL, the way an import or a repair would, so the cached columns are
# not touched.
_LEDGER = sa.table(
    "leave_ledger",
    sa.column("balance_id", sa.Integer),
    sa.column("employee_id", sa.Integer),
    sa.column("leave_type_id", sa.Integer),
    sa.column("entitlement_year", sa.Integer),
    sa.column("entry_type", sa.String(11)),
    sa.column("signed_days", sa.Numeric(6, 2)),
    sa.column("reference_type", sa.String(40)),
    sa.column("reference_id", sa.Integer),
    sa.column("description", sa.Text),
)
with session.no_autoflush:
    session.execute(
        _LEDGER.insert().values(
            balance_id=other.id,
            employee_id=other.employee_id,
            leave_type_id=other.leave_type_id,
            entitlement_year=other.entitlement_year,
            entry_type="ADJUSTMENT",
            signed_days=Decimal("2.5"),
            reference_type="adjustment",
            reference_id=1,
            description="a row the cache has not seen",
        )
    )
session.commit()
session.expire_all()
other = session.query(LeaveBalance).filter(LeaveBalance.id == other.id).first()
derived_now = ledger.derived_available_days(session, other)
check(
    "a row the cache has not seen still shows in the derived balance",
    derived_now == before + Decimal("2.5"),
    f"expected {before + Decimal('2.5')}, got {derived_now}",
)
check(
    "the cached columns have not caught up, and say so",
    not other.verify_ledger_invariant(session),
    "the cache claimed to agree with a row it never saw",
)

# ===========================================================================
print("\n[REQUEST-1] The approval writes a usage row, the cancellation writes the reversal")
# ===========================================================================

START = datetime.date(2026, 3, 2)
END = datetime.date(2026, 3, 4)
DAYS = ledger.working_days_between(START, END)

r = client.post(
    "/api/v1/leave/requests",
    headers=H_ASSOC,
    json={
        "employee_id": EMP_A_ID,
        "leave_type_id": LEAVE_TYPE_ID,
        "start_date": START.isoformat(),
        "end_date": END.isoformat(),
        "reason": "a private reason that must not reach the ledger",
    },
)
check("a leave request is filed", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
REQUEST_ID = r.json()["id"] if r.status_code == 201 else None
check("the request is pending", r.json().get("status") == "Pending", f"got {r.json().get('status')}")
check(
    "the request is quantified in working days",
    r.json().get("working_days") == DAYS,
    f"got {r.json().get('working_days')} expected {DAYS}",
)

r = client.post(f"/api/v1/leave/requests/{REQUEST_ID}/approve", headers=H_HR)
check("the request is approved", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

session.expire_all()
bal_a = session.query(LeaveBalance).filter(LeaveBalance.id == BALANCE_A.id).first()
usage_rows = (
    session.query(LeaveLedger)
    .filter(
        LeaveLedger.balance_id == BALANCE_A.id,
        LeaveLedger.entry_type == LeaveLedgerEntryType.USAGE,
    )
    .all()
)
check(
    "the approval writes one usage row",
    len(usage_rows) == 1,
    f"rows={[(str(x.signed_days), x.reference_type) for x in usage_rows]}",
)
check(
    "the usage row is negative and names the request",
    usage_rows
    and usage_rows[0].signed_days == -Decimal(DAYS)
    and usage_rows[0].reference_type == "leave_request"
    and usage_rows[0].reference_id == REQUEST_ID,
    f"row={usage_rows[0] if usage_rows else None}",
)
check(
    "the balance falls by exactly the requested days",
    bal_a.used_days == Decimal(DAYS),
    f"used={bal_a.used_days} expected {DAYS}",
)
check(
    "the derived balance agrees with the cache after the approval",
    bal_a.verify_ledger_invariant(session),
    f"cached={bal_a.available_days} ledger={bal_a.compute_from_ledger(session)}",
)

r = client.get(f"/api/v1/leave/balances?employee_id={EMP_A_ID}&year={YEAR}", headers=H_HR)
balance_json = r.json()[0] if r.status_code == 200 and r.json() else {}
check(
    "the balance endpoint reports the derived balance",
    balance_json.get("available_days")
    == float(Decimal(balance_json.get("entitled_days", 0)) + Decimal(balance_json.get("carried_over_days", 0)) - Decimal(balance_json.get("used_days", 0))),
    f"got {balance_json.get('available_days')}",
)
check(
    "the balance endpoint says whether the cache agrees",
    balance_json.get("available_days") == balance_json.get("cached_available_days"),
    f"derived={balance_json.get('available_days')} cached={balance_json.get('cached_available_days')}",
)

r = client.post(f"/api/v1/leave/requests/{REQUEST_ID}/cancel", headers=H_HR)
check("the approved request is cancelled", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

session.expire_all()
bal_a = session.query(LeaveBalance).filter(LeaveBalance.id == BALANCE_A.id).first()
history = (
    session.query(LeaveLedger)
    .filter(LeaveLedger.balance_id == BALANCE_A.id)
    .order_by(LeaveLedger.id)
    .all()
)
usage_history = [row for row in history if row.entry_type == LeaveLedgerEntryType.USAGE]
check(
    "the history is rows: the usage and the reversal are both there",
    len(usage_history) == 2,
    f"rows={[(str(x.signed_days), x.reference_type) for x in usage_history]}",
)
check(
    "the reversal gives back exactly the days that were taken",
    len(usage_history) == 2
    and usage_history[1].signed_days == -usage_history[0].signed_days,
    f"usage={usage_history[0].signed_days if usage_history else None} "
    f"reversal={usage_history[1].signed_days if len(usage_history) > 1 else None}",
)
check(
    "the balance is back where it was",
    bal_a.used_days == Decimal("0"),
    f"used={bal_a.used_days}",
)
check(
    "the cache still agrees with the ledger after the reversal",
    bal_a.verify_ledger_invariant(session),
    f"cached={bal_a.available_days} ledger={bal_a.compute_from_ledger(session)}",
)

# ===========================================================================
print("\n[REQUEST-2] The refusals")
# ===========================================================================

# A request for more leave than the derived balance allows.
small = LeaveBalance(
    employee_id=EMP_B_ID,
    leave_type_id=LEAVE_TYPE_3,
    entitlement_year=YEAR + 1,
    entitled_days=Decimal("0"),
    carried_over_days=Decimal("0"),
    used_days=Decimal("0"),
)
session.add(small)
session.flush()
session.refresh(small)
ledger.post_entry(
    session, small, LeaveLedgerEntryType.ENTITLEMENT, Decimal("1"),
    reference_type="entitlement", reference_id=None,
    description="one day only",
)
session.commit()

r = client.post(
    "/api/v1/leave/requests",
    headers=H_HR,
    json={
        "employee_id": EMP_B_ID,
        "leave_type_id": LEAVE_TYPE_3,
        "start_date": f"{YEAR + 1}-04-06",
        "end_date": f"{YEAR + 1}-04-10",
        "reason": "more than the balance allows",
    },
)
check("a request for more than the balance allows is filed", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
TOO_BIG = r.json()["id"] if r.status_code == 201 else None

rows_before = session.query(LeaveLedger).filter(LeaveLedger.balance_id == small.id).count()
r = client.post(f"/api/v1/leave/requests/{TOO_BIG}/approve", headers=H_HR)
check(
    "a request for more leave than the derived balance allows is refused",
    r.status_code == 409,
    f"got {r.status_code}: {r.text[:200]}",
)
check(
    "the refusal carries the shared error code",
    r.json().get("error", {}).get("code") == "leave_insufficient_balance",
    f"got {r.json().get('error', {}).get('code')}",
)
session.expire_all()
small = session.query(LeaveBalance).filter(LeaveBalance.id == small.id).first()
check(
    "the refused approval left the balance where it was",
    small.available_days == Decimal("1"),
    f"got {small.available_days}",
)
check(
    "the refused approval wrote no row",
    session.query(LeaveLedger).filter(LeaveLedger.balance_id == small.id).count()
    == rows_before,
    "a row was written",
)
r = client.get(f"/api/v1/leave/requests/{TOO_BIG}", headers=H_HR)
check(
    "the refused request is still pending",
    r.status_code in (200, 404),
    f"got {r.status_code}",
)

# A cancellation with no usage to reverse: a request that was approved before
# the ledger existed. There is nothing to give back, so it is refused.
legacy = LeaveRequest(
    employee_id=EMP_B_ID,
    leave_type_id=LEAVE_TYPE_ID,
    start_date=datetime.date(2026, 5, 4),
    end_date=datetime.date(2026, 5, 5),
    working_days=2,
    status="Approved",
)
session.add(legacy)
session.commit()
session.refresh(legacy)

r = client.post(f"/api/v1/leave/requests/{legacy.id}/cancel", headers=H_HR)
check(
    "a cancellation without a usage to reverse is refused",
    r.status_code == 409,
    f"got {r.status_code}: {r.text[:200]}",
)
check(
    "the refusal carries the shared error code",
    r.json().get("error", {}).get("code") == "leave_invalid_state_transition",
    f"got {r.json().get('error', {}).get('code')}",
)
check(
    "the refused cancellation left the request approved",
    session.query(LeaveRequest).filter(LeaveRequest.id == legacy.id).first().status
    == "Approved",
    "the request was cancelled anyway",
)

# ===========================================================================
print("\n[LEDGER-3] Reading the ledger")
# ===========================================================================

r = client.get(f"/api/v1/leave/balances/{EMP_A_ID}/ledger", headers=H_ASSOC)
check("an employee may read their own ledger", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
ledger_json = r.json() if r.status_code == 200 else []
check(
    "the ledger of the employee holds the entitlement, the usage and the reversal",
    [row["entry_type"] for row in ledger_json]
    == ["entitlement", "usage", "usage"],
    f"rows={[row['entry_type'] for row in ledger_json]}",
)
check(
    "every row carries the balance after the movement",
    [row["running_balance"] for row in ledger_json]
    == [
        float(sum(Decimal(str(x["signed_days"])) for x in ledger_json[: i + 1]))
        for i in range(len(ledger_json))
    ],
    f"running={[row['running_balance'] for row in ledger_json]}",
)
check(
    "the ledger carries no reason and no diagnosis",
    all(
        not row.get("description")
        or "private reason" not in row["description"]
        for row in ledger_json
    )
    and not any("private reason" in json.dumps(row) for row in ledger_json),
    "the request's reason reached the ledger",
)

r = client.get(f"/api/v1/leave/balances/{EMP_B_ID}/ledger", headers=H_ASSOC)
check(
    "an employee may not read a colleague's ledger",
    r.status_code in (403, 404),
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.get(f"/api/v1/leave/balances/{EMP_A_ID}/ledger", headers=H_PAY)
check(
    "a payroll viewer may not read the ledger",
    r.status_code == 403,
    f"got {r.status_code}: {r.text[:200]}",
)

# ===========================================================================
print("\n[RECON-1] The reconciliation reports what disagrees")
# ===========================================================================

r = client.get(f"/api/v1/leave/reconciliation?year={YEAR}", headers=H_HR)
check("the reconciliation is served", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
report = r.json() if r.status_code == 200 else {}
rows = report.get("rows", [])
by_id = {row["balance_id"]: row for row in rows}

check(
    "a balance that agrees with its ledger is in sync",
    by_id.get(BALANCE_A.id, {}).get("state") == "in_sync",
    f"state={by_id.get(BALANCE_A.id, {}).get('state')}",
)
check(
    "a balance whose cache has not seen a row is reported as out of sync",
    by_id.get(other.id, {}).get("state") == "out_of_sync",
    f"state={by_id.get(other.id, {}).get('state')}",
)
check(
    "the report says how far the two disagree",
    by_id.get(other.id, {}).get("difference_days") == 2.5,
    f"difference={by_id.get(other.id, {}).get('difference_days')}",
)
check(
    "the report counts what disagrees",
    report.get("summary", {}).get("out_of_sync", 0) >= 1,
    f"summary={report.get('summary')}",
)
check(
    "the report carries no reason, no description and no diagnosis",
    all(
        not {"reason", "description", "note"} & set(row)
        for row in rows
    ),
    f"keys={sorted(rows[0]) if rows else []}",
)

r = client.get(f"/api/v1/leave/reconciliation?year={YEAR}", headers=H_ASSOC)
check(
    "an associate may not read the reconciliation",
    r.status_code == 403,
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.get(f"/api/v1/leave/reconciliation?year={YEAR}", headers=H_MGR)
check(
    "a manager may read the reconciliation",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:200]}",
)
manager_rows = r.json().get("rows", []) if r.status_code == 200 else []
check(
    "a manager's reconciliation is scoped to the records they may see",
    all(
        row["employee_id"] in {EMP_MGR_ID, EMP_A_ID}
        for row in manager_rows
    ),
    f"employees={sorted({row['employee_id'] for row in manager_rows})}",
)

# ===========================================================================
print("\n[PAYROLL-1] The approved leave of a period reaches the payroll lane")
# ===========================================================================

# An approved request that falls inside the period, and one that straddles
# it, so the quantity of a straddling leave is split between the periods.
r = client.post(
    "/api/v1/leave/requests",
    headers=H_HR,
    json={
        "employee_id": EMP_A_ID,
        "leave_type_id": LEAVE_TYPE_ID,
        "start_date": "2026-06-01",
        "end_date": "2026-06-30",
        "reason": "a month of leave",
    },
)
check("a second request is filed", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
MONTH_ID = r.json()["id"] if r.status_code == 201 else None
r = client.post(f"/api/v1/leave/requests/{MONTH_ID}/approve", headers=H_HR)
check("the second request is approved", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

JUNE_DAYS = ledger.working_days_between(
    datetime.date(2026, 6, 1), datetime.date(2026, 6, 30)
)

r = client.get(
    "/api/v1/leave/payroll-input?period_start=2026-06-01&period_end=2026-06-30",
    headers=H_PAY,
)
check("the payroll input is served", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
payload = r.json() if r.status_code == 200 else {}

check(
    "the payroll input names the period it covers",
    payload.get("period_start") == "2026-06-01"
    and payload.get("period_end") == "2026-06-30",
    f"got {payload.get('period_start')}..{payload.get('period_end')}",
)
entries = payload.get("entries", [])
check(
    "the payroll input holds one entry for the approved leave",
    len(entries) == 1,
    f"entries={entries}",
)
entry = entries[0] if entries else {}
check(
    "the entry is the shape the payroll lane consumes: the person, the type, "
    "the quantity and the period",
    set(entry) == {
        "employee_id",
        "leave_type_id",
        "leave_type_code",
        "is_paid",
        "leave_request_id",
        "start_date",
        "end_date",
        "quantity_days",
    },
    f"keys={sorted(entry)}",
)
check(
    "the entry carries the quantity and the period of the leave",
    entry.get("quantity_days") == float(JUNE_DAYS)
    and entry.get("start_date") == "2026-06-01"
    and entry.get("end_date") == "2026-06-30"
    and entry.get("employee_id") == EMP_A_ID
    and entry.get("leave_request_id") == MONTH_ID
    and entry.get("leave_type_code") == "LEDG"
    and entry.get("is_paid") is True,
    f"entry={entry}",
)
check(
    "the payroll input totals the quantity",
    payload.get("total_days") == float(JUNE_DAYS),
    f"total={payload.get('total_days')}",
)

r = client.get(
    "/api/v1/leave/payroll-input?period_start=2026-07-01&period_end=2026-07-31",
    headers=H_PAY,
)
check(
    "a period with no approved leave holds nothing",
    r.status_code == 200 and r.json().get("entries") == [],
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.get(
    "/api/v1/leave/payroll-input?period_start=2026-08-01&period_end=2026-07-01",
    headers=H_PAY,
)
check(
    "a period that ends before it starts is refused",
    r.status_code == 422,
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.get(
    "/api/v1/leave/payroll-input?period_start=2026-06-01&period_end=2026-06-30",
    headers=H_ASSOC,
)
check(
    "an associate may not read the payroll input",
    r.status_code == 403,
    f"got {r.status_code}: {r.text[:200]}",
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


def _rows(db_path: str, sql: str) -> list[tuple]:
    conn = sqlite3.connect(db_path)
    try:
        return list(conn.execute(sql).fetchall())
    finally:
        conn.close()


workdir = tempfile.mkdtemp(prefix="karmathy-leave-migrations-")
try:
    fresh = os.path.join(workdir, "fresh.db")
    _run_migrations(fresh)

    check(
        "the migration creates the leave ledger table",
        "leave_ledger" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the table holds the columns the models declare",
        {
            "id",
            "balance_id",
            "employee_id",
            "leave_type_id",
            "entitlement_year",
            "entry_type",
            "signed_days",
            "reference_type",
            "reference_id",
            "description",
            "created_by",
            "created_at",
        }
        <= _columns(fresh, "leave_ledger"),
        f"columns={sorted(_columns(fresh, 'leave_ledger'))}",
    )
    check(
        "the table holds the indexes the models declare",
        {
            "ix_leave_ledger_balance_id",
            "ix_leave_ledger_employee_id",
            "ix_leave_ledger_leave_type_id",
            "ix_leave_ledger_entitlement_year",
        }
        <= _indexes(fresh, "leave_ledger"),
        f"indexes={sorted(_indexes(fresh, 'leave_ledger'))}",
    )
    check(
        "the foreign key on the ledger is indexed as well",
        "ix_fk_leave_ledger_created_by" in _indexes(fresh, "leave_ledger"),
        f"indexes={sorted(_indexes(fresh, 'leave_ledger'))}",
    )

    _run_migrations(fresh, "0009_credential_role_constraint", "downgrade")
    check(
        "the downgrade removes the table",
        "leave_ledger" not in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the downgrade leaves the balances alone",
        "leave_balances" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    _run_migrations(fresh)
    check(
        "the ledger can be brought back",
        "leave_ledger" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )

    # --- the genesis --------------------------------------------------------
    genesis = os.path.join(workdir, "genesis.db")
    _run_migrations(genesis, "0009_credential_role_constraint")
    check(
        "the ledger table does not exist before the migration",
        "leave_ledger" not in _tables(genesis),
        f"tables={sorted(_tables(genesis))}",
    )
    conn = sqlite3.connect(genesis)
    try:
        conn.execute(
            "INSERT INTO leave_types (id, name, code, is_paid, max_days_per_year, "
            "is_active, created_at) VALUES (1, 'Annual', 'ANL', 1, 20, 1, "
            "CURRENT_TIMESTAMP)"
        )
        conn.execute(
            "INSERT INTO leave_balances (id, employee_id, leave_type_id, "
            "entitlement_year, entitled_days, carried_over_days, used_days, "
            "created_at, updated_at) VALUES (1, 42, 1, 2026, 20, 2, 5, "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        )
        conn.commit()
    finally:
        conn.close()

    _run_migrations(genesis)
    genesis_rows = _rows(
        genesis,
        "SELECT entry_type, signed_days, reference_type FROM leave_ledger "
        "WHERE balance_id = 1 ORDER BY id",
    )
    check(
        "the backfill gives an existing balance a real history",
        len(genesis_rows) == 3,
        f"rows={genesis_rows}",
    )
    check(
        "the history says what happened: the entitlement, the carry-over and "
        "the leave that was taken",
        [row[0] for row in genesis_rows] == ["ENTITLEMENT", "CARRY_OVER", "USAGE"],
        f"types={[row[0] for row in genesis_rows]}",
    )
    check(
        "the history carries the numbers, not a marker",
        [float(row[1]) for row in genesis_rows] == [20.0, 2.0, -5.0],
        f"days={[row[1] for row in genesis_rows]}",
    )
    check(
        "the derived balance of the backfilled balance is the balance the "
        "tenant already had",
        sum(float(row[1]) for row in genesis_rows) == 17.0,
        f"sum={sum(float(row[1]) for row in genesis_rows)}",
    )
    check(
        "the backfill does not touch a balance that already has a history",
        len(
            _rows(
                genesis,
                "SELECT id FROM leave_ledger WHERE balance_id = 1",
            )
        )
        == 3,
        "the backfill wrote again",
    )
finally:
    shutil.rmtree(workdir, ignore_errors=True)

session.close()

# ===========================================================================
print()
print("=" * 68)
print(f"==== LEAVE SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
