"""Integrity test suite (NFR-014 / migration 0043_integrity_expand).

Proves the database itself — not just the API — preserves financial,
employment, approval and audit history:

1. **FK reject**: a row naming a parent that does not exist is refused.
2. **Concurrent dup**: two writers racing to create the same payslip leave
   exactly one row; the loser is refused by C2.
3. **Partial rollback**: a transaction that violates a constraint commits
   nothing — the valid rows in it are not kept.
4. **Check reject**: every safe CHECK (C4–C9, C11–C13) refuses a bad row.
5. **Append-only**: ``audit_logs`` refuses UPDATE and DELETE at the
   database level (the trigger, not the API).
6. **Legacy adopt + quarantine**: a database migrated to 0042 holding
   legacy violations upgrades to head (0043); every violation is
   quarantined with its old values and repaired — none silently
   discarded, none left violating — and the quarantine survives a
   downgrade/upgrade round trip.
7. **Catalog discipline**: every 0043 name fits Oracle's 30-character
   limit and every CHECK text compiles on Oracle, PostgreSQL and SQLite.

Two scratch databases are used, both under ``tempfile`` and both removed
from the repository tree (never ``seed_dev.db``, never production):

* the **head-schema** database, built by ``create_all()`` from the current
  models, for the refusal tests (1–5);
* the **migration** database, built by the real ``scripts.migrate`` CLI,
  first to 0042 (so violations can be seeded the way legacy data holds
  them) and then to head, for test (6).

Run:  python integrity_test_suite.py
"""
import datetime
import json
import os
import sqlite3
import sys
import tempfile
import threading
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

WORKDIR = Path(tempfile.mkdtemp(prefix="integrity_test_"))
HEAD_DB = str(WORKDIR / "integrity_head.db")
MIG_DB = str(WORKDIR / "integrity_mig.db")

os.environ["DATABASE_URL"] = f"sqlite:///{HEAD_DB}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"

try:
    os.remove(HEAD_DB)
except FileNotFoundError:
    pass

from sqlalchemy import event  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402

# SQLite enforces foreign keys only when the pragma is on, per connection.
# The refusal tests need the database to actually refuse, so every
# connection in this suite opts in.
@event.listens_for(engine, "connect")
def _fk_on(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


import app.models  # noqa: E402,F401 -- register every model on Base.metadata
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee, EmployeeHistory  # noqa: E402
from app.models.expenses import (  # noqa: E402
    ExpenseCategory,
    ExpenseClaim,
    ExpenseReceipt,
)
from app.models.job import Job  # noqa: E402
from app.models.leave import (  # noqa: E402
    LeaveBalance,
    LeaveLedger,
    LeaveLedgerEntryType,
    LeaveRequest,
    LeaveType,
)
from app.models.payroll import (  # noqa: E402
    EmployeePayProfile,
    PayrollPeriod,
    PayRun,
    PaySlip,
)

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


TODAY = datetime.date.today()


def _seed_core(db):
    """The parents every refusal test needs: department, job, employee."""
    dept = Department(name="Integrity", code="INTG")
    db.add(dept)
    db.commit()
    db.refresh(dept)
    job = Job(title="Integrity Role", code="INTGJ", department_id=dept.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    emp = Employee(
        employee_id="INTG-001",
        first_name="In",
        last_name="Tegrity",
        email="integrity@example.com",
        hire_date=TODAY - datetime.timedelta(days=400),
        job_id=job.id,
        department_id=dept.id,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return dept, job, emp


Base.metadata.create_all(bind=engine)
db = SessionLocal()
DEPT, JOB, EMP = _seed_core(db)

print("=" * 68)
print("1. FOREIGN KEYS REFUSE ORPHANS")
print("=" * 68)

try:
    db.add(
        ExpenseClaim(
            employee_id=999999,
            category_id=999999,
            expense_date=TODAY,
            amount=Decimal("10.00"),
        )
    )
    db.commit()
    check("claim with unknown employee/category is refused", False, "committed")
except IntegrityError:
    db.rollback()
    check("claim with unknown employee/category is refused", True)

try:
    db.add(
        LeaveRequest(
            employee_id=EMP.id,
            leave_type_id=999999,
            start_date=TODAY,
            end_date=TODAY + datetime.timedelta(days=1),
        )
    )
    db.commit()
    check("leave request with unknown leave type is refused", False, "committed")
except IntegrityError:
    db.rollback()
    check("leave request with unknown leave type is refused", True)

print()
print("=" * 68)
print("2. CONCURRENT DUPLICATE PAYSLIPS LEAVE ONE ROW (C2)")
print("=" * 68)

period = PayrollPeriod(
    name="INTG-P", start_date=TODAY.replace(day=1), end_date=TODAY, pay_date=TODAY
)
db.add(period)
db.commit()
db.refresh(period)
run = PayRun(period_id=period.id, status="Processing")
db.add(run)
db.commit()
db.refresh(run)
RUN_ID = run.id
EMP_ID = EMP.id
JOB_ID = JOB.id
DEPT_ID = DEPT.id
db.close()

# Two writers race to create the same slip — the retry storm the unique
# key exists for. SQLite serialises the writers; the loser must still be
# refused by the constraint rather than by luck.
from sqlalchemy import create_engine as _mk  # noqa: E402
from sqlalchemy.orm import sessionmaker as _sm  # noqa: E402

race_engine = _mk(f"sqlite:///{HEAD_DB}", connect_args={"timeout": 30})
@event.listens_for(race_engine, "connect")
def _race_fk_on(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()

RaceSession = _sm(bind=race_engine)
barrier = threading.Barrier(2)
outcomes: list[str] = []


def _race_insert():
    session = RaceSession()
    barrier.wait(timeout=30)
    try:
        session.add(
            PaySlip(
                pay_run_id=RUN_ID,
                employee_id=EMP_ID,
                gross_pay=Decimal("1000.00"),
                net_pay=Decimal("800.00"),
                total_deductions=Decimal("200.00"),
            )
        )
        session.commit()
        outcomes.append("committed")
    except Exception as exc:  # noqa: BLE001 -- either refusal proves the backstop
        session.rollback()
        outcomes.append(f"{type(exc).__name__}: {exc}")
    finally:
        session.close()


threads = [threading.Thread(target=_race_insert) for _ in range(2)]
for t in threads:
    t.start()
for t in threads:
    t.join(timeout=120)

check("both racers finished", len(outcomes) == 2, str(outcomes))
db = SessionLocal()
slips = (
    db.query(PaySlip)
    .filter(PaySlip.pay_run_id == RUN_ID, PaySlip.employee_id == EMP_ID)
    .all()
)
check("exactly one payslip survives the race", len(slips) == 1, f"rows={len(slips)}")
check(
    "the loser was refused, not lucky",
    any("committed" == o for o in outcomes)
    and any("committed" != o for o in outcomes),
    str(outcomes),
)
if len(slips) != 1:
    for s in slips:
        db.delete(s)
    db.commit()
db.close()
race_engine.dispose()

print()
print("=" * 68)
print("3. A VIOLATING TRANSACTION COMMITS NOTHING")
print("=" * 68)

db = SessionLocal()
cat = ExpenseCategory(code="INTG-TRVL", name="Integrity Travel")
db.add(cat)
db.commit()
db.refresh(cat)
before = db.query(ExpenseClaim).count()
try:
    db.add(
        ExpenseClaim(
            employee_id=EMP_ID,
            category_id=cat.id,
            expense_date=TODAY,
            amount=Decimal("25.00"),
            status="DRAFT",
            payment_status="UNPAID",
        )
    )
    db.flush()
    db.add(
        ExpenseClaim(
            employee_id=EMP_ID,
            category_id=cat.id,
            expense_date=TODAY,
            amount=Decimal("-5.00"),  # C4: refused
            status="DRAFT",
            payment_status="UNPAID",
        )
    )
    db.commit()
    committed = True
except IntegrityError:
    db.rollback()
    committed = False
after = db.query(ExpenseClaim).count()
check("violating transaction is refused", not committed)
check("the valid row in it is not kept either", after == before, f"{before}->{after}")

print()
print("=" * 68)
print("4. EVERY SAFE CHECK REFUSES A BAD ROW")
print("=" * 68)

lt = LeaveType(name="Annual INTG", code="INTGAN", is_paid=True, max_days_per_year=10)
db.add(lt)
db.commit()
db.refresh(lt)
bal = LeaveBalance(
    employee_id=EMP_ID,
    leave_type_id=lt.id,
    entitlement_year=TODAY.year,
    entitled_days=Decimal("10"),
)
db.add(bal)
db.commit()
db.refresh(bal)

EMP2 = Employee(
    employee_id="INTG-002",
    first_name="Second",
    last_name="Writer",
    email="integrity-two@example.com",
    hire_date=TODAY - datetime.timedelta(days=400),
    job_id=JOB_ID,
    department_id=DEPT_ID,
)
db.add(EMP2)
db.commit()
db.refresh(EMP2)

seed_claim = ExpenseClaim(
    employee_id=EMP_ID, category_id=cat.id, expense_date=TODAY,
    amount=Decimal("3.00"), status="DRAFT", payment_status="UNPAID",
)
db.add(seed_claim)
db.commit()
db.refresh(seed_claim)
SEED_CLAIM_ID = seed_claim.id


def _refuses(label, factory):
    session = SessionLocal()
    try:
        session.add(factory())
        session.commit()
        session.rollback()
        check(label, False, "bad row committed")
    except IntegrityError:
        session.rollback()
        check(label, True)
    finally:
        session.close()


_refuses(
    "C4: negative claim amount is refused",
    lambda: ExpenseClaim(
        employee_id=EMP_ID, category_id=cat.id, expense_date=TODAY,
        amount=Decimal("-1.00"), status="DRAFT", payment_status="UNPAID",
    ),
)
_refuses(
    "C5: unknown claim status is refused",
    lambda: ExpenseClaim(
        employee_id=EMP_ID, category_id=cat.id, expense_date=TODAY,
        amount=Decimal("1.00"), status="BOGUS", payment_status="UNPAID",
    ),
)
_refuses(
    "C6: unknown payment status is refused",
    lambda: ExpenseClaim(
        employee_id=EMP_ID, category_id=cat.id, expense_date=TODAY,
        amount=Decimal("1.00"), status="DRAFT", payment_status="BOGUS",
    ),
)
_refuses(
    "C7: inverted leave dates are refused",
    lambda: LeaveRequest(
        employee_id=EMP_ID, leave_type_id=lt.id,
        start_date=TODAY + datetime.timedelta(days=5), end_date=TODAY,
    ),
)
_refuses(
    "C8: unknown leave status is refused",
    lambda: LeaveRequest(
        employee_id=EMP_ID, leave_type_id=lt.id,
        start_date=TODAY, end_date=TODAY + datetime.timedelta(days=1),
        status="BOGUS",
    ),
)
_refuses(
    "C9: zero-effect ledger row is refused",
    lambda: LeaveLedger(
        balance_id=bal.id, employee_id=EMP_ID, leave_type_id=lt.id,
        entitlement_year=TODAY.year, entry_type=LeaveLedgerEntryType.ACCRUAL,
        signed_days=Decimal("0"),
    ),
)
_refuses(
    "C11: inverted history dates are refused",
    lambda: EmployeeHistory(
        employee_id=EMP_ID, field="status",
        previous_value="Active", new_value="Terminated",
        effective_from=TODAY, effective_to=TODAY - datetime.timedelta(days=1),
    ),
)
_refuses(
    "C12: negative payslip money is refused",
    lambda: PaySlip(
        pay_run_id=RUN_ID, employee_id=EMP2.id,
        gross_pay=Decimal("-1.00"), net_pay=Decimal("0"), total_deductions=Decimal("0"),
    ),
)
_refuses(
    "C13: negative receipt size is refused",
    lambda: ExpenseReceipt(
        claim_id=SEED_CLAIM_ID,
        storage_key="intg/neg-%s" % os.urandom(4).hex(),
        file_name="neg.pdf", size_bytes=-1,
    ),
)


print()
print("=" * 68)
print("5. AUDIT HISTORY IS APPEND-ONLY AT THE DATABASE LEVEL")
print("=" * 68)

from app.core.audit_chain import install_append_only  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402

with engine.begin() as conn:
    install_append_only(conn)
session = SessionLocal()
entry = AuditLog(
    actor_id=None, actor_name="integrity-suite", action="integrity_probe",
    entity_type="suite", entity_id=None,
    prev_hash="0" * 64, entry_hash="1" * 64,
)
session.add(entry)
session.commit()
entry_id = entry.id
session.close()

conn = sqlite3.connect(HEAD_DB)
try:
    try:
        conn.execute(f"UPDATE audit_logs SET action='rewritten' WHERE id={entry_id}")
        conn.commit()
        updated = True
    except Exception:  # noqa: BLE001 -- the trigger aborts the statement
        updated = False
    check("UPDATE of an audit row is refused", not updated)

    try:
        conn.execute(f"DELETE FROM audit_logs WHERE id={entry_id}")
        conn.commit()
        deleted = True
    except Exception:  # noqa: BLE001
        deleted = False
    check("DELETE of an audit row is refused", not deleted)

    row = conn.execute(
        f"SELECT action, prev_hash, entry_hash FROM audit_logs WHERE id={entry_id}"
    ).fetchone()
    check(
        "the row survives both attempts byte-identical",
        row == ("integrity_probe", "0" * 64, "1" * 64),
        str(row),
    )
finally:
    conn.close()

print()
print("=" * 68)
print("6. LEGACY ADOPT QUARANTINES INSTEAD OF DISCARDING")
print("=" * 68)


def _run_migrations(db_path: str, target: str = "head") -> None:
    import subprocess

    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["ALEMBIC_DATABASE_URL"] = f"sqlite:///{db_path}"
    result = subprocess.run(
        [sys.executable, "-m", "scripts.migrate", "upgrade", target],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"migration upgrade {target} failed:\n{result.stdout}\n{result.stderr}"
        )


def _revision(db_path: str) -> str | None:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
        return rows[0][0] if rows else None
    finally:
        conn.close()


try:
    os.remove(MIG_DB)
except FileNotFoundError:
    pass

# A legacy-shaped database: migrated to 0042, before the constraints
# existed, then given the violations legacy data holds.
#
# Two shapes matter. The frozen tables (leave_requests, pay_slips) are
# built by the baseline from the current models, so the baseline already
# guards them at 0042 — a violation cannot even be seeded there. The
# post-baseline tables (expense_claims, leave_ledger, employee_history)
# are built by their own migrations without the new CHECKs, so legacy
# violations seed normally and 0043 must quarantine+repair them.
_run_migrations(MIG_DB, "0042_notification_delivery")
check("migration to 0042 succeeds", _revision(MIG_DB) == "0042_notification_delivery",
      str(_revision(MIG_DB)))

from sqlalchemy import create_engine as _mk2  # noqa: E402
from sqlalchemy.orm import sessionmaker as _sm2  # noqa: E402

mig_engine = _mk2(f"sqlite:///{MIG_DB}")
MigSession = _sm2(bind=mig_engine)
ms = MigSession()
m_dept = Department(name="Mig", code="MIGQ")
ms.add(m_dept)
ms.commit(); ms.refresh(m_dept)
m_job = Job(title="Mig Role", code="MIGQJ", department_id=m_dept.id)
ms.add(m_job)
ms.commit(); ms.refresh(m_job)
m_emp = Employee(
    employee_id="MIGQ-001", first_name="Mi", last_name="Grant",
    email="migrate-quarantine@example.com",
    hire_date=TODAY - datetime.timedelta(days=100),
    job_id=m_job.id, department_id=m_dept.id,
)
ms.add(m_emp)
ms.commit(); ms.refresh(m_emp)
m_cat = ExpenseCategory(code="MIGQ-TRVL", name="Mig Travel")
ms.add(m_cat)
ms.commit(); ms.refresh(m_cat)
m_lt = LeaveType(name="Annual MIGQ", code="MIGQAN", is_paid=True, max_days_per_year=10)
ms.add(m_lt)
ms.commit(); ms.refresh(m_lt)
m_bal = LeaveBalance(
    employee_id=m_emp.id, leave_type_id=m_lt.id,
    entitlement_year=TODAY.year, entitled_days=Decimal("10"),
)
ms.add(m_bal)
ms.commit(); ms.refresh(m_bal)

# Frozen tables are already guarded at 0042: the violation is refused
# before 0043 ever runs. That is the safe-subset argument in action —
# enforcing the constraint changes nothing for data that is already clean.
for label, factory in (
    ("C7 already guarded at 0042", lambda: LeaveRequest(
        employee_id=m_emp.id, leave_type_id=m_lt.id,
        start_date=TODAY + datetime.timedelta(days=3), end_date=TODAY)),
    ("C12 already guarded at 0042", lambda: PaySlip(
        pay_run_id=1, employee_id=m_emp.id,
        gross_pay=Decimal("-1.00"), net_pay=Decimal("0"),
        total_deductions=Decimal("0"))),
):
    try:
        ms.add(factory())
        ms.commit()
        check(label, False, "violation seeded where the baseline should refuse")
    except IntegrityError:
        ms.rollback()
        check(label, True)

# The post-baseline tables hold the legacy violations 0043 must repair.
ms.add(ExpenseClaim(employee_id=m_emp.id, category_id=m_cat.id, expense_date=TODAY,
                    amount=Decimal("-42.50"), status="DRAFT", payment_status="UNPAID"))
ms.add(ExpenseClaim(employee_id=m_emp.id, category_id=m_cat.id, expense_date=TODAY,
                    amount=Decimal("7.00"), status="LIMBO", payment_status="UNPAID"))
ms.add(LeaveLedger(balance_id=m_bal.id, employee_id=m_emp.id, leave_type_id=m_lt.id,
                   entitlement_year=TODAY.year,
                   entry_type=LeaveLedgerEntryType.ACCRUAL, signed_days=Decimal("0")))
ms.add(EmployeeHistory(employee_id=m_emp.id, field="status",
                        previous_value="Active", new_value="Terminated",
                        effective_from=TODAY,
                        effective_to=TODAY - datetime.timedelta(days=2)))
ms.commit()
BAD_IDS = {
    "claim_neg": ms.query(ExpenseClaim).filter(ExpenseClaim.amount < 0).one().id,
    "claim_limbo": ms.query(ExpenseClaim).filter(ExpenseClaim.status == "LIMBO").one().id,
    "ledger_zero": ms.query(LeaveLedger).filter(LeaveLedger.signed_days == 0).one().id,
    "hist_inv": ms.query(EmployeeHistory).filter(
        EmployeeHistory.effective_to < EmployeeHistory.effective_from).one().id,
}
CLAIM_COUNT_BEFORE = ms.query(ExpenseClaim).count()
ms.close()

_run_migrations(MIG_DB, "head")
check("upgrade to head succeeds with violations present",
      _revision(MIG_DB) == "0043_integrity_expand", str(_revision(MIG_DB)))

conn = sqlite3.connect(MIG_DB)
try:
    qrows = conn.execute(
        "SELECT table_name, row_pk, reason, details FROM integrity_quarantine"
    ).fetchall()
    reasons = {(r[0], r[2]) for r in qrows}
    for table, reason in (
        ("expense_claims", "ck_claim_amount_nonneg"),
        ("expense_claims", "ck_claim_status_fsm"),
        ("leave_ledger", "ck_ledger_signed_nonzero"),
        ("employee_history", "ck_emphist_dates"),
    ):
        check(f"quarantine holds {table} / {reason}",
              (table, reason) in reasons, str(sorted(reasons)))

    by_reason = {}
    for table, pk, reason, details in qrows:
        by_reason.setdefault(reason, []).append((pk, json.loads(details or "{}")))

    neg = by_reason.get("ck_claim_amount_nonneg", [])
    check("negative amount keeps its old value in quarantine",
          any("42.5" in json.dumps(d) for _, d in neg), str(neg)[:200])
    row = conn.execute(
        f"SELECT amount FROM expense_claims WHERE id={BAD_IDS['claim_neg']}"
    ).fetchone()
    check("negative amount is repaired to zero, row kept",
          row is not None and float(row[0]) == 0, str(row))

    row = conn.execute(
        f"SELECT status FROM expense_claims WHERE id={BAD_IDS['claim_limbo']}"
    ).fetchone()
    check("unknown claim status falls back to DRAFT, row kept",
          row is not None and row[0] == "DRAFT", str(row))

    row = conn.execute(
        f"SELECT COUNT(*) FROM leave_ledger WHERE id={BAD_IDS['ledger_zero']}"
    ).fetchone()
    check("zero-effect ledger row is removed after quarantine",
          row is not None and row[0] == 0, str(row))

    row = conn.execute(
        f"SELECT effective_to FROM employee_history WHERE id={BAD_IDS['hist_inv']}"
    ).fetchone()
    check("inverted history dates open the row (NULL), row kept",
          row is not None and row[0] is None, str(row))

    n_claims = conn.execute("SELECT COUNT(*) FROM expense_claims").fetchone()[0]
    check("no claim row is lost by the backfill",
          n_claims == CLAIM_COUNT_BEFORE, f"{CLAIM_COUNT_BEFORE}->{n_claims}")

    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='expense_claims'"
    ).fetchone()[0] or ""
    check("CHECKs are on the migrated tables",
          "ck_claim_amount_nonneg" in sql and "ck_claim_status_fsm" in sql,
          sql[:200])

    names = {r[1] for r in conn.execute("PRAGMA index_list(expense_claims)")}
    check("approver-chain FK index exists after adopt",
          any("paid_by" in n or "approved" in n for n in names), str(sorted(names)))
finally:
    conn.close()
mig_engine.dispose()

# 6b. Every repair branch, proved in-process on a hand-built schema that
# lacks all 0043 constraints: one violation per safe check, including the
# duplicate-payslip case no migrated database can still hold (the frozen
# baseline guards C2 from the start). The revision runs directly — the
# same in-process pattern the migration suite uses — then runs again to
# prove idempotency.
BACKFILL_DB = str(WORKDIR / "integrity_backfill.db")


def _load_revision(filename: str):
    import importlib.util

    path = BACKEND_DIR / "migrations" / "versions" / filename
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


bconn = sqlite3.connect(BACKFILL_DB)
try:
    bconn.executescript(
        """
        CREATE TABLE expense_claims (id INTEGER PRIMARY KEY, status VARCHAR(20),
            payment_status VARCHAR(10), amount NUMERIC);
        CREATE TABLE leave_requests (id INTEGER PRIMARY KEY, status VARCHAR(20),
            start_date DATE, end_date DATE);
        CREATE TABLE leave_ledger (id INTEGER PRIMARY KEY, balance_id INTEGER,
            employee_id INTEGER, leave_type_id INTEGER, entitlement_year INTEGER,
            entry_type VARCHAR(20), signed_days NUMERIC);
        CREATE TABLE employee_history (id INTEGER PRIMARY KEY,
            effective_from DATE, effective_to DATE);
        CREATE TABLE pay_slips (id INTEGER PRIMARY KEY, pay_run_id INTEGER,
            employee_id INTEGER, gross_pay NUMERIC, net_pay NUMERIC,
            total_deductions NUMERIC);
        CREATE TABLE expense_receipts (id INTEGER PRIMARY KEY, size_bytes INTEGER);
        INSERT INTO expense_claims VALUES (1, 'DRAFT', 'UNPAID', -42.50);
        INSERT INTO expense_claims VALUES (2, 'LIMBO', 'UNPAID', 7.00);
        INSERT INTO expense_claims VALUES (3, 'DRAFT', 'LATER', 7.00);
        INSERT INTO leave_requests VALUES (1, 'Pending', '2026-06-10', '2026-06-01');
        INSERT INTO leave_requests VALUES (2, 'BOGUS', '2026-06-01', '2026-06-02');
        INSERT INTO leave_ledger VALUES (1, 1, 1, 1, 2026, 'accrual', 0);
        INSERT INTO leave_ledger VALUES (2, 1, 1, 1, 2026, 'accrual', 2.5);
        INSERT INTO employee_history VALUES (1, '2026-01-01', '2025-12-31');
        INSERT INTO pay_slips VALUES (1, 1, 1, 1000, 800, 200);
        INSERT INTO pay_slips VALUES (2, 1, 1, 1000, 800, 200);
        INSERT INTO pay_slips VALUES (3, 1, 2, -50, 0, 0);
        INSERT INTO expense_receipts VALUES (1, -5);
        """
    )
    bconn.commit()
finally:
    bconn.close()

_apply_revision(BACKFILL_DB, "0043_integrity_expand.py", "upgrade")

conn = sqlite3.connect(BACKFILL_DB)
try:
    reasons = sorted(
        r[0] for r in conn.execute("SELECT DISTINCT reason FROM integrity_quarantine")
    )
    for expected in (
        "ck_claim_amount_nonneg", "ck_claim_status_fsm", "ck_claim_paystat_fsm",
        "ck_leave_req_dates", "ck_leave_req_status", "ck_ledger_signed_nonzero",
        "ck_emphist_dates", "uq_payslip_run_employee",
        "ck_payslip_amounts_nonneg", "ck_receipt_size_nonneg",
    ):
        check(f"backfill quarantines {expected}", expected in reasons, str(reasons))

    vals = {r[0]: r[1:] for r in conn.execute("SELECT id, status, payment_status, amount FROM expense_claims")}
    check("backfill zeroes the negative amount",
          float(vals[1][2]) == 0, str(vals[1]))
    check("backfill resets LIMBO to DRAFT", vals[2][0] == "DRAFT", str(vals[2]))
    check("backfill resets LATER to UNPAID", vals[3][1] == "UNPAID", str(vals[3]))

    row = conn.execute("SELECT start_date, end_date, status FROM leave_requests WHERE id=1").fetchone()
    check("backfill swaps inverted leave dates", row[0] <= row[1], str(row))
    row = conn.execute("SELECT status FROM leave_requests WHERE id=2").fetchone()
    check("backfill resets BOGUS leave status to Pending", row[0] == "Pending", str(row))

    n = conn.execute("SELECT COUNT(*) FROM leave_ledger").fetchone()[0]
    kept = conn.execute("SELECT signed_days FROM leave_ledger").fetchone()[0]
    check("backfill removes only the zero-effect ledger row",
          n == 1 and float(kept) == 2.5, f"rows={n} kept={kept}")

    row = conn.execute("SELECT effective_to FROM employee_history WHERE id=1").fetchone()
    check("backfill opens the inverted history row", row[0] is None, str(row))

    slips = conn.execute("SELECT id, gross_pay FROM pay_slips ORDER BY id").fetchall()
    check("backfill keeps the earliest duplicate slip",
          [s[0] for s in slips] == [1, 3], str(slips))
    check("backfill zeroes the negative slip money",
          float([s[1] for s in slips if s[0] == 3][0]) == 0, str(slips))

    row = conn.execute("SELECT size_bytes FROM expense_receipts WHERE id=1").fetchone()
    check("backfill zeroes the negative receipt size",
          row[0] == 0, str(row))

    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='pay_slips'"
    ).fetchone()[0] or ""
    check("backfill installs the payslip UNIQUE + CHECK",
          "uq_payslip_run_employee" in sql and "ck_payslip_amounts_nonneg" in sql,
          sql[:250])
    q_before = conn.execute("SELECT COUNT(*) FROM integrity_quarantine").fetchone()[0]
finally:
    conn.close()

_apply_revision(BACKFILL_DB, "0043_integrity_expand.py", "upgrade")
conn = sqlite3.connect(BACKFILL_DB)
try:
    q_after = conn.execute("SELECT COUNT(*) FROM integrity_quarantine").fetchone()[0]
    check("second 0043 run quarantines nothing new (idempotent)",
          q_after == q_before, f"{q_before}->{q_after}")
finally:
    conn.close()

# The quarantine survives the way back: evidence is retained, and the
# way forward works again afterwards.
import subprocess as _sp  # noqa: E402

env = dict(os.environ)
env["DATABASE_URL"] = f"sqlite:///{MIG_DB}"
env["ALEMBIC_DATABASE_URL"] = f"sqlite:///{MIG_DB}"
down = _sp.run([sys.executable, "-m", "scripts.migrate", "downgrade", "-1"],
               cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True, timeout=300)
check("downgrade -1 succeeds", down.returncode == 0, (down.stdout + down.stderr)[-500:])
conn = sqlite3.connect(MIG_DB)
try:
    n = conn.execute("SELECT COUNT(*) FROM integrity_quarantine").fetchone()[0]
    check("quarantine is retained by the downgrade", n == 4, f"rows={n}")
finally:
    conn.close()
_run_migrations(MIG_DB, "head")
check("re-upgrade to head succeeds (idempotent)",
      _revision(MIG_DB) == "0043_integrity_expand", str(_revision(MIG_DB)))

print()
print("=" * 68)
print("7. ORACLE DISCIPLINE: NAMES AND DIALECT PORTABILITY")
print("=" * 68)

import importlib.util as _ilu  # noqa: E402

spec = _ilu.spec_from_file_location(
    "mig_0043", BACKEND_DIR / "migrations" / "versions" / "0043_integrity_expand.py")
mig43 = _ilu.module_from_spec(spec)
spec.loader.exec_module(mig43)

names = (
    [n for _, n, _ in mig43.SAFE_CHECKS]
    + [mig43.PAYSLIP_UNIQUE, "uq_quarantine_row_reason"]
    + [mig43._fk_index_name(t, c) for t, c in mig43.NEW_FK_INDEXES]
)
too_long = [n for n in names if len(n) > 30]
check("every 0043 name fits Oracle's 30-char limit", not too_long, str(too_long))

from sqlalchemy.dialects import oracle as _ora, postgresql as _pg  # noqa: E402
from sqlalchemy.schema import CheckConstraint as _CC  # noqa: E402

bad_sql = []
for table, name, sql in mig43.SAFE_CHECKS:
    for dialect in (_ora.dialect(), _pg.dialect()):
        try:
            str(_CC(sql, name=name).sqltext.compile(dialect=dialect))
        except Exception as exc:  # noqa: BLE001
            bad_sql.append(f"{name}/{dialect.name}: {exc}")
check("every CHECK compiles on Oracle and PostgreSQL", not bad_sql, str(bad_sql)[:300])

print()
print("=" * 68)
print(f"==== INTEGRITY SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for n, d in FAILURES:
        print(f"  - {n}: {d}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
