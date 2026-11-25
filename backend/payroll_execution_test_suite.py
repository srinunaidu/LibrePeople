"""Payroll execution suite - karmathy-payroll-execution.

Covers AC-01 through AC-09 of the payroll execution contract:

* AC-01 Pay run approval: HR/SuperAdmin approve Draft->Approved; 403 on
  SuperAdmin-only surfaces for HR; segregation of duties (creator != approver).
* AC-02 Pay run lock/finalize: Approved->Finalized; payslips become Final;
  locked runs refuse modification (409 pay_run_already_finalised /
  422 invalid_state_transition).
* AC-03 Off-cycle corrections: separate pay runs with their own period,
  pay_date and currency.
* AC-04 Proration: mid-period employment history changes prorate base salary
  by days worked; the basis is traceable in inputs_json.
* AC-05 Explicit currency: ISO 4217 currency on pay run and payslip.
* AC-06 Bank-ready payment file: NACHA-equivalent export from approved runs.
* AC-07 Segregation of duties: same user cannot create AND approve (403).
* AC-08 Rule pack verification: process refuses without verified pack (422).
* AC-09 Structured error envelopes on all payroll endpoints.

Run:
    DATABASE_URL="sqlite:////tmp/payroll_exec.db" \
    SECRET_KEY="test-secret-key-123456789012345678901234" \
    MIGRATE_ON_STARTUP="false" ORACLE_DSN="" ORACLE_WALLET_DIR="" \
    .venv/bin/python payroll_execution_test_suite.py
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="payroll_exec_test_"), "payroll_exec_test.db")

BACKEND_ROOT = Path(__file__).resolve().parent

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["ORACLE_DSN"] = ""
os.environ["ORACLE_WALLET_DIR"] = ""
os.environ["ORACLE_WALLET_PASSWORD"] = ""
os.environ["ORACLE_USER"] = ""
os.environ["ORACLE_PASSWORD"] = ""

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee, EmployeeHistory  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.payroll import (  # noqa: E402
    EmployeePayProfile,
    PayRun,
    PaySlip,
    PayrollPeriod,
)
from app.models.time_attendance import TimeEntry  # noqa: E402
from app.models.user import User  # noqa: E402

from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

session = SessionLocal()

# --- Users ------------------------------------------------------------------
session.add(User(
    username="sa_admin", email="sa@example.com",
    hashed_password=get_password_hash("SuperAdminPass12345"),
    role="SuperAdmin", is_active=True, mfa_enabled=True,
))
session.add(User(
    username="hr_user", email="hr@example.com",
    hashed_password=get_password_hash("HRPass12345"),
    role="HR", is_active=True, mfa_enabled=True,
))
session.add(User(
    username="associate", email="associate@example.com",
    hashed_password=get_password_hash("AssocPass12345"),
    role="Associate", is_active=True,
))

department = Department(name="Payroll", code="PAY")
session.add(department)
session.flush()
job = Job(title="Payroll Officer", code="PAYJOB", department_id=department.id)
session.add(job)
session.flush()
employee = Employee(
    employee_id="PAY-1", first_name="Test", last_name="Person",
    email="payroll.employee@example.com", hire_date=date(2026, 1, 1),
    job_id=job.id, department_id=department.id,
)
session.add(employee)
session.flush()
EMPLOYEE_ID = employee.id
session.commit()
session.close()

client = TestClient(app, raise_server_exceptions=False)

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


def envelope(response) -> dict | None:
    try:
        body = response.json()
    except ValueError:
        return None
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return body["error"]
    return None


def assert_envelope(response, expected_code: str | None = None,
                    expected_status: int | None = None) -> dict:
    check("response is JSON",
          response.headers.get("content-type", "").startswith("application/json"),
          f"ct={response.headers.get('content-type')}")
    env = envelope(response)
    check("envelope has error key", isinstance(env, dict),
          f"body={response.text[:200]}")
    if env is None:
        return {}
    for key in ("code", "category", "message", "retryable", "request_id"):
        check(f"envelope has {key}", key in env,
              f"env={env}")
    if expected_code is not None:
        check(f"code is {expected_code}", env.get("code") == expected_code,
              f"code={env.get('code')!r}")
    if expected_status is not None:
        check(f"status is {expected_status}", response.status_code == expected_status,
              f"status={response.status_code}")
    return env


def login(username: str, password: str) -> dict:
    r = client.post("/api/v1/auth/login",
                    json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


SA = login("sa_admin", "SuperAdminPass12345")
HR = login("hr_user", "HRPass12345")
ASSOC = login("associate", "AssocPass12345")


def make_period(pay_date: str = "2026-03-31") -> int:
    # Period starts on the 1st of the month of pay_date and ends on pay_date.
    year, month, _ = pay_date.split("-")
    start_date = f"{year}-{month}-01"
    r = client.post("/api/v1/payroll/periods", headers=SA,
                    json={"name": f"Period {pay_date}",
                          "start_date": start_date,
                          "end_date": pay_date,
                          "pay_date": pay_date})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def make_run(period_id: int, jurisdiction: str = "QQ",
             currency: str = "USD", headers: dict = SA) -> int:
    r = client.post("/api/v1/payroll/runs", headers=headers,
                    json={"period_id": period_id,
                          "jurisdiction": jurisdiction,
                          "currency": currency})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def run_currency(run_id: int) -> str | None:
    with SessionLocal() as db:
        run = db.get(PayRun, run_id)
        return run.currency if run else None


def slip_currency(slip_id: int) -> str | None:
    with SessionLocal() as db:
        slip = db.get(PaySlip, slip_id)
        return slip.currency if slip else None


def run_status(run_id: int) -> str | None:
    with SessionLocal() as db:
        run = db.get(PayRun, run_id)
        return run.status if run else None


def ensure_profile(employee_id: int, base_salary: float = 50000) -> None:
    """Ensure a pay profile exists for the employee (idempotent)."""
    r = client.post("/api/v1/payroll/pay-profiles", headers=SA,
                    json={"employee_id": employee_id,
                          "base_salary": base_salary,
                          "pay_frequency": "Monthly",
                          "tax_withholding": 10})
    if r.status_code not in (201, 409):
        raise AssertionError(f"profile create: {r.status_code} {r.text}")


# ---- rule pack directory ----------------------------------------------------
FIXTURE_PACK = (
    BACKEND_ROOT
    / "test_fixtures"
    / "rule_packs"
    / "qq-test-fixture-synthetic-not-a-statute.json"
)


def write_pack_directory(packs: list[dict]) -> Path:
    directory = Path(tempfile.mkdtemp(prefix="karmathy-payroll-packs-"))
    for index, pack in enumerate(packs):
        path = directory / f"{index:02d}-{pack['pack_id']}.json"
        path.write_text(json.dumps(pack, indent=2))
    os.environ["RULE_PACK_DIR"] = str(directory)
    return directory


def pack_from_fixture(**changes) -> dict:
    data = json.loads(FIXTURE_PACK.read_text())
    for key, value in changes.items():
        if key in ("pack_id", "version", "status", "effective_from", "effective_to"):
            data[key] = value
        elif key == "country":
            data["jurisdiction"]["country"] = value
        elif key == "verification":
            data["verification"] = value
        else:
            raise KeyError(key)
    return data


def ensure_verified_pack() -> Path:
    """Point the resolver at a directory holding a verified QQ pack."""
    return write_pack_directory([
        pack_from_fixture(pack_id="fixture-verified", status="verified")
    ])


# ============================================================================
print()
print("=" * 68)
print("PAYROLL EXECUTION SUITE - karmathy-payroll-execution")
print("=" * 68)

# --- Shared fixture: verified pack for QQ -----------------------------------
verified_directory = ensure_verified_pack()
ensure_profile(EMPLOYEE_ID, base_salary=50000)

try:
    # ------------------------------------------------------------------
    # AC-05: explicit ISO 4217 currency on run and slip
    # ------------------------------------------------------------------
    print()
    print("-" * 68)
    print("AC-05: explicit ISO 4217 currency on run and slip")
    print("-" * 68)

    period_id = make_period()
    run_id = make_run(period_id, "QQ", "USD", SA)
    check("run currency stored as USD", run_currency(run_id) == "USD",
          f"currency={run_currency(run_id)!r}")

    r = client.post(f"/api/v1/payroll/runs/{run_id}/process", headers=SA)
    check("run processes with verified pack", r.status_code == 200,
          f"got {r.status_code}: {r.text[:160]}")

    with SessionLocal() as db:
        slips = db.query(PaySlip).filter(PaySlip.pay_run_id == run_id).all()
    check("one payslip written", len(slips) == 1, f"slips={len(slips)}")
    if slips:
        check("payslip currency matches run currency",
              slips[0].currency == "USD",
              f"slip.currency={slips[0].currency!r}")
        slip_id = slips[0].id
        check("slip currency stored as USD", slip_currency(slip_id) == "USD",
              f"currency={slip_currency(slip_id)!r}")

    # ------------------------------------------------------------------
    # AC-08: rule pack verification gate
    # ------------------------------------------------------------------
    print()
    print("-" * 68)
    print("AC-08: rule pack verification - 422 rule_pack_not_verified")
    print("-" * 68)

    no_pack_directory = write_pack_directory([])
    try:
        period_id2 = make_period("2026-04-30")
        run_id2 = make_run(period_id2, "QQ", "USD", SA)
        before = client.get(f"/api/v1/payroll/runs/{run_id2}", headers=SA).json()

        r = client.post(f"/api/v1/payroll/runs/{run_id2}/process", headers=SA)
        env = assert_envelope(r, "rule_pack_not_verified", 422)
        check("refusal details carry jurisdiction/pay_date/pack_status/required",
              isinstance(env, dict)
              and set((env.get("details") or {})) == {"jurisdiction", "pay_date", "pack_status", "required"},
              f"details={(env or {}).get('details')!r}")
        check("refusal writes nothing: run unchanged",
              client.get(f"/api/v1/payroll/runs/{run_id2}", headers=SA).json() == before,
              "run changed after refused process")
        with SessionLocal() as db:
            count = db.query(PaySlip).filter(PaySlip.pay_run_id == run_id2).count()
        check("refusal writes nothing: no payslip", count == 0,
              f"payslips={count}")
    finally:
        shutil.rmtree(no_pack_directory, ignore_errors=True)
    # Restore verified pack for the rest of the suite.
    ensure_verified_pack()

    # ------------------------------------------------------------------
    # AC-01 / AC-07: approval transition + segregation of duties
    # ------------------------------------------------------------------
    print()
    print("-" * 68)
    print("AC-01/AC-07: approval transition + segregation of duties")
    print("-" * 68)

    # HR creates and processes a run.
    period_id3 = make_period("2026-05-31")
    run_id3 = make_run(period_id3, "QQ", "GBP", HR)
    ensure_profile(EMPLOYEE_ID, base_salary=50000)

    r = client.post(f"/api/v1/payroll/runs/{run_id3}/process", headers=HR)
    check("HR processes run to Processing", r.status_code == 200,
          f"got {r.status_code}: {r.text[:160]}")
    check("run is Processing", run_status(run_id3) == "Processing",
          f"status={run_status(run_id3)!r}")

    # Same user (HR) cannot approve their own run: 403 separation_of_duties.
    r = client.post(f"/api/v1/payroll/runs/{run_id3}/approve", headers=HR)
    env = assert_envelope(r, "separation_of_duties", 403)
    check("SoD details name conflicting role",
          isinstance(env, dict) and (env.get("details") or {}).get("conflicting_role") == "HR",
          f"details={(env or {}).get('details')!r}")

    # A different user (SuperAdmin) approves.
    r = client.post(f"/api/v1/payroll/runs/{run_id3}/approve", headers=SA)
    check("SuperAdmin approves run", r.status_code == 200,
          f"got {r.status_code}: {r.text[:160]}")
    body = r.json()
    check("run is Approved", body.get("status") == "Approved",
          f"status={body.get('status')!r}")
    check("approved_by set", body.get("approved_by") is not None,
          f"approved_by={body.get('approved_by')!r}")
    check("approved_at set", body.get("approved_at") is not None,
          f"approved_at={body.get('approved_at')!r}")

    # Associate cannot approve: 403.
    r = client.post(f"/api/v1/payroll/runs/{run_id3}/approve", headers=ASSOC)
    assert_envelope(r, expected_status=403)
    check("Associate cannot approve", r.status_code == 403,
          f"got {r.status_code}")

    # ------------------------------------------------------------------
    # AC-02: finalize / lock
    # ------------------------------------------------------------------
    print()
    print("-" * 68)
    print("AC-02: finalize/lock - Approved -> Finalized, immutable")
    print("-" * 68)

    r = client.post(f"/api/v1/payroll/runs/{run_id3}/finalize", headers=SA)
    check("SuperAdmin finalizes run", r.status_code == 200,
          f"got {r.status_code}: {r.text[:160]}")
    body = r.json()
    check("run is Finalized", body.get("status") == "Finalized",
          f"status={body.get('status')!r}")
    check("finalized_by set", body.get("finalized_by") is not None,
          f"finalized_by={body.get('finalized_by')!r}")

    with SessionLocal() as db:
        slips = db.query(PaySlip).filter(PaySlip.pay_run_id == run_id3).all()
    check("payslips are Final",
          all(s.status == "Final" for s in slips),
          f"statuses={[s.status for s in slips]}")

    # Creating a payslip on a finalized run: 409 pay_run_already_finalised.
    r = client.post("/api/v1/payroll/payslips", headers=SA,
                    json={"pay_run_id": run_id3, "employee_id": EMPLOYEE_ID,
                          "gross_pay": 100, "net_pay": 100, "total_deductions": 0})
    env = assert_envelope(r, "pay_run_already_finalised", 409)
    check("409 details carry pay_run_id",
          isinstance(env, dict) and (env.get("details") or {}).get("pay_run_id") == run_id3,
          f"details={(env or {}).get('details')!r}")

    # Reprocessing a finalized run: 409 pay_run_already_finalised (pipeline
    # lock; 409/422 both mean locked — the pipeline refines the code to 409
    # so corrections go through adjustment runs with reversal_of_run_id).
    r = client.post(f"/api/v1/payroll/runs/{run_id3}/process", headers=SA)
    assert_envelope(r, "pay_run_already_finalised", 409)
    check("reprocess of finalized run is 409", r.status_code == 409,
          f"got {r.status_code}")

    # ------------------------------------------------------------------
    # AC-03: off-cycle correction run
    # ------------------------------------------------------------------
    print()
    print("-" * 68)
    print("AC-03: off-cycle correction run with separate period")
    print("-" * 68)

    period_id4 = make_period("2026-06-15")  # off-cycle mid-month
    run_id4 = make_run(period_id4, "QQ", "EUR", SA)
    check("off-cycle run has its own currency", run_currency(run_id4) == "EUR",
          f"currency={run_currency(run_id4)!r}")
    check("off-cycle run is Draft", run_status(run_id4) == "Draft",
          f"status={run_status(run_id4)!r}")

    # Process and approve the off-cycle run (SA processes, HR approves - different users).
    ensure_profile(EMPLOYEE_ID, base_salary=30000)
    r = client.post(f"/api/v1/payroll/runs/{run_id4}/process", headers=SA)
    check("off-cycle run processes", r.status_code == 200,
          f"got {r.status_code}: {r.text[:160]}")
    r = client.post(f"/api/v1/payroll/runs/{run_id4}/approve", headers=HR)
    check("off-cycle run approves (different user)", r.status_code == 200,
          f"got {r.status_code}: {r.text[:160]}")

    # ------------------------------------------------------------------
    # AC-04: proration traceable in inputs_json
    # ------------------------------------------------------------------
    print()
    print("-" * 68)
    print("AC-04: proration by days worked, traceable in inputs_json")
    print("-" * 68)

    period_id5 = make_period("2026-07-31")
    run_id5 = make_run(period_id5, "QQ", "USD", SA)

    # Add an employment history row: salary changes mid-period (effective 2026-07-11).
    session = SessionLocal()
    session.add(EmployeeHistory(
        employee_id=EMPLOYEE_ID,
        field="base_salary",
        previous_value="60000",
        new_value="72000",
        effective_from=date(2026, 7, 11),
        effective_to=None,
        reason="mid-period raise",
        changed_by="sa_admin",
    ))
    session.commit()
    session.close()

    r = client.post(f"/api/v1/payroll/runs/{run_id5}/process", headers=SA)
    check("prorated run processes", r.status_code == 200,
          f"got {r.status_code}: {r.text[:160]}")

    with SessionLocal() as db:
        slips = db.query(PaySlip).filter(PaySlip.pay_run_id == run_id5).all()
    check("one payslip", len(slips) == 1, f"slips={len(slips)}")
    if slips:
        inputs = json.loads(slips[0].inputs_json or "{}")
        check("inputs_json records proration basis",
              "period_start" in inputs and "period_end" in inputs
              and "days_worked" in inputs and "period_days" in inputs
              and "salary_effective_date" in inputs
              and "prorated_base" in inputs,
              f"inputs={inputs}")
        check("prorated_base differs from original base",
              inputs.get("prorated_base") != inputs.get("original_base"),
              f"inputs={inputs}")
        check("days_worked is less than period_days",
              Decimal(str(inputs.get("days_worked", 0))) < Decimal(str(inputs.get("period_days", 0))),
              f"inputs={inputs}")

    # ------------------------------------------------------------------
    # AC-06: bank-ready payment file from approved run
    # ------------------------------------------------------------------
    print()
    print("-" * 68)
    print("AC-06: bank-ready payment file from approved run")
    print("-" * 68)

    # Use run_id4 (EUR) which is Approved but not Finalized.
    r = client.post(f"/api/v1/payroll/runs/{run_id4}/payment-file", headers=HR)
    check("payment file generated", r.status_code == 200,
          f"got {r.status_code}: {r.text[:200]}")
    check("payment file is downloadable attachment",
          "attachment" in (r.headers.get("content-disposition") or ""),
          f"cd={r.headers.get('content-disposition')!r}")
    check("payment file has deterministic filename",
          "payroll_run_" in (r.headers.get("content-disposition") or ""),
          f"cd={r.headers.get('content-disposition')!r}")
    content = r.text
    check("payment file contains run reference",
          f"RUN_ID={run_id4}" in content,
          f"content={content[:200]}")
    check("payment file contains currency",
          "CURRENCY=EUR" in content,
          f"content={content[:200]}")
    check("payment file contains employee reference",
          "PAY-1" in content,
          f"content={content[:200]}")
    check("payment file contains net amount",
          "TOTAL_NET=" in content,
          f"content={content[:200]}")

    # Payment file on non-approved run: 422 invalid_state_transition.
    r = client.post(f"/api/v1/payroll/runs/{run_id5}/payment-file", headers=HR)
    assert_envelope(r, "invalid_state_transition", 422)
    check("payment file refused on non-approved run", r.status_code == 422,
          f"got {r.status_code}")

    # ------------------------------------------------------------------
    # AC-09: structured error envelopes on all payroll endpoints
    # ------------------------------------------------------------------
    print()
    print("-" * 68)
    print("AC-09: structured error envelopes on all payroll endpoints")
    print("-" * 68)

    # 404 on unknown run.
    r = client.post("/api/v1/payroll/runs/999999/approve", headers=SA)
    assert_envelope(r, expected_status=404)
    check("404 returns envelope", r.status_code == 404,
          f"got {r.status_code}")

    # 403 for Associate on approve.
    r = client.post(f"/api/v1/payroll/runs/{run_id3}/approve", headers=ASSOC)
    assert_envelope(r, expected_status=403)
    check("403 returns envelope", r.status_code == 403,
          f"got {r.status_code}")

    # 422 on bad currency.
    r = client.post("/api/v1/payroll/runs", headers=SA,
                    json={"period_id": period_id, "jurisdiction": "QQ",
                          "currency": "USDD"})
    assert_envelope(r, expected_status=422)
    check("bad currency returns 422 envelope", r.status_code == 422,
          f"got {r.status_code}")

finally:
    shutil.rmtree(verified_directory, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("=" * 68)
total = RESULTS["pass"] + RESULTS["fail"]
print(f"RESULTS: {RESULTS['pass']} passed, {RESULTS['fail']} failed ({total} total)")
if FAILURES:
    print()
    print("FAILURES:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
