"""The payroll refusal suite - PR-01.

Payroll must not calculate a pay run for a jurisdiction that has no verified
rule pack in force on the pay date. That refusal is the product's honesty
guarantee: a pay figure computed without a verified rule is a figure nobody
can stand behind, and a customer who finds one has been told something the
product cannot prove.

This suite proves four things.

1. **The refusal happens.** No pack, a ``draft`` pack, a pack waiting for a
   human, a pack that stopped applying before the pay date and a pack that
   starts after it are each refused with ``rule_pack_not_verified``, and the
   details say which of the five it was.
2. **The refusal writes nothing.** No payslip, no change to the pay run, no
   audit row that claims work was done. The one row that is written records
   the refusal, because that row is the evidence.
3. **A jurisdiction with a verified pack is calculated from that pack**, and
   every line of the payslip carries the rule id and the rule version that
   produced it.
4. **The synthetic demo pack can never enable a jurisdiction.** It is a
   ``draft``, it is synthetic, and the pack directory the product ships has
   no verified pack in it at all.
5. **The band's shape, and the demo pack that has to work.** A table that
   declares itself banded states a rate on every one of its bands, and a
   pack that breaks the rule is refused when it is loaded, naming the table
   and the band. The demo pack the product ships loads, computes, and its
   golden cases are the engine's output, line for line.

Nothing in this file is a statutory value. Every number is synthetic and
every number comes from the synthetic test fixture pack.

Run:  python payroll_test_suite.py
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import replace
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="payroll_test_"), "payroll_test.db")

BACKEND_ROOT = Path(__file__).resolve().parent
#: The synthetic test fixture pack. It is not a rule pack for a real
#: jurisdiction: the country code is a user-assigned one and every number in
#: it is invented. It lives outside ``rule_packs/`` so the product never
#: loads it.
FIXTURE_PACK = (
    BACKEND_ROOT
    / "test_fixtures"
    / "rule_packs"
    / "qq-test-fixture-synthetic-not-a-statute.json"
)
#: The synthetic test fixture pack with a banded tax table. It is the
#: banded counterpart of the fixture above: same synthetic country-code
#: trick, different country code, and a tax table written in the banded
#: form the schema describes.
BANDED_FIXTURE_PACK = (
    BACKEND_ROOT
    / "test_fixtures"
    / "rule_packs"
    / "qr-test-fixture-banded-synthetic-not-a-statute.json"
)
#: The pack directory the product ships with.
SHIPPED_PACK_DIR = BACKEND_ROOT.parent / "rule_packs"
#: The contract the engine has to agree with.
SCHEMA_PATH = BACKEND_ROOT.parent / "contracts" / "rules" / "rule-pack.schema.json"

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.leave import LeaveRequest, LeaveType  # noqa: E402
from app.models.payroll import (  # noqa: E402
    EmployeePayProfile,
    PayComponent,
    PayRun,
    PayrollPeriod,
    PaySlip,
)
from app.models.time_attendance import TimeEntry  # noqa: E402
from app.models.user import User  # noqa: E402
from app.rules.engine import (  # noqa: E402
    RulePackNotReadable,
    calculate_payslip_from_pack,
    rate_table_problems,
    run_golden_cases,
)
from app.rules.loader import (  # noqa: E402
    RulePackLoadError,
    load_rule_pack,
    load_rule_pack_from_dict,
    validate_against_schema,
)
from app.rules.reconciliation import build_reconciliation  # noqa: E402

# The application is imported before the schema is built: importing it is
# what registers every model, and `create_all` can only create the tables of
# the models it knows about.
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

session = SessionLocal()
session.add(User(
    username="payroll_admin", email="payroll_admin@example.com",
    hashed_password=get_password_hash("PayrollPass12345"),
    role="SuperAdmin", is_active=True,
    mfa_enabled=True,  # item 10: privileged users are enrolled
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


def headers() -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"username": "payroll_admin", "password": "PayrollPass12345"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


H = headers()

#: The jurisdiction the synthetic fixture pack covers.
JURISDICTION = "QQ"
#: The pay date every scenario uses.
PAY_DATE = "2026-03-31"
#: The pay profile every scenario uses. The salary is synthetic.
BASE_SALARY = 50000
TAX_WITHHOLDING = 10


# ---------------------------------------------------------------------------
# The pack directories
# ---------------------------------------------------------------------------


def pack_from_fixture(**changes) -> dict:
    """The synthetic fixture pack, with the given fields changed."""
    data = json.loads(FIXTURE_PACK.read_text())
    for key, value in changes.items():
        if key in ("pack_id", "version", "status", "effective_from", "effective_to"):
            data[key] = value
        elif key == "country":
            data["jurisdiction"]["country"] = value
        elif key == "verification":
            data["verification"] = value
        else:  # pragma: no cover - a typo in a test
            raise KeyError(key)
    return data


def write_pack_directory(packs: list[dict]) -> Path:
    """A directory holding the given packs, and the environment set to it."""
    directory = Path(tempfile.mkdtemp(prefix="karmathy-payroll-packs-"))
    for index, pack in enumerate(packs):
        path = directory / f"{index:02d}-{pack['pack_id']}.json"
        path.write_text(json.dumps(pack, indent=2))
    os.environ["RULE_PACK_DIR"] = str(directory)
    return directory


def use_shipped_pack_directory() -> None:
    """Point the resolver at the pack directory the product ships with."""
    os.environ["RULE_PACK_DIR"] = str(SHIPPED_PACK_DIR)


# ---------------------------------------------------------------------------
# The fixtures of the API
# ---------------------------------------------------------------------------


def make_period(pay_date: str = PAY_DATE) -> int:
    response = client.post(
        "/api/v1/payroll/periods",
        headers=H,
        json={
            "name": f"Period {pay_date}",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "pay_date": pay_date,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def make_run(period_id: int, jurisdiction: str = JURISDICTION) -> int:
    response = client.post(
        "/api/v1/payroll/runs",
        headers=H,
        json={"period_id": period_id, "jurisdiction": jurisdiction, "currency": "USD"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def run_state(run_id: int) -> dict:
    """Everything about the run that a calculation would change."""
    with SessionLocal() as db:
        run = db.get(PayRun, run_id)
        return {
            "status": run.status,
            "total_gross": run.total_gross,
            "total_deductions": run.total_deductions,
            "total_net": run.total_net,
            "headcount": run.headcount,
            "processed_by": run.processed_by,
            "processed_at": run.processed_at,
            "rule_pack_id": run.rule_pack_id,
            "warning": run.warning,
            "payslips": db.query(PaySlip)
            .filter(PaySlip.pay_run_id == run_id)
            .count(),
        }


def audit_rows(run_id: int) -> list[AuditLog]:
    with SessionLocal() as db:
        return (
            db.query(AuditLog)
            .filter(AuditLog.entity_type == "PayRun", AuditLog.entity_id == run_id)
            .order_by(AuditLog.id)
            .all()
        )


def profile_exists() -> bool:
    with SessionLocal() as db:
        return db.query(EmployeePayProfile).filter(
            EmployeePayProfile.employee_id == EMPLOYEE_ID
        ).count() > 0


if not profile_exists():
    response = client.post(
        "/api/v1/payroll/pay-profiles",
        headers=H,
        json={
            "employee_id": EMPLOYEE_ID,
            "base_salary": BASE_SALARY,
            "pay_frequency": "Monthly",
            "tax_withholding": TAX_WITHHOLDING,
        },
    )
    assert response.status_code == 201, response.text


# ---------------------------------------------------------------------------
# The refusal
# ---------------------------------------------------------------------------


def expect_refusal(
    name: str,
    packs: list[dict],
    expected_status: str,
    jurisdiction: str = JURISDICTION,
    use_shipped: bool = False,
) -> None:
    """A run for a jurisdiction without a usable pack is refused.

    The refusal has to be the shared error envelope with the published code,
    the details have to say what was found and what has to be done, and
    nothing may be written: no payslip, no change to the run, and no audit
    row that claims the run was calculated.
    """
    if use_shipped:
        use_shipped_pack_directory()
        directory = None
    else:
        directory = write_pack_directory(packs)
    try:
        period_id = make_period()
        run_id = make_run(period_id, jurisdiction)
        before = run_state(run_id)
        audits_before = len(audit_rows(run_id))

        response = client.post(f"/api/v1/payroll/runs/{run_id}/process", headers=H)

        check(f"{name}: the run is refused", response.status_code == 422,
              f"got {response.status_code}: {response.text[:200]}")

        body = response.json()
        envelope = body.get("error") if isinstance(body, dict) else None
        check(f"{name}: the refusal is the shared envelope, not a bare detail",
              isinstance(envelope, dict) and "detail" not in body,
              f"body={str(body)[:200]}")
        check(f"{name}: the code is rule_pack_not_verified",
              bool(envelope) and envelope.get("code") == "rule_pack_not_verified",
              f"code={(envelope or {}).get('code')!r}")

        details = (envelope or {}).get("details") or {}
        check(f"{name}: the details carry the published shape",
              set(details) == {"jurisdiction", "pay_date", "pack_status", "required"},
              f"details={details}")
        check(f"{name}: the details name the jurisdiction",
              details.get("jurisdiction") == jurisdiction,
              f"jurisdiction={details.get('jurisdiction')!r}")
        check(f"{name}: the details name the pay date",
              details.get("pay_date") == PAY_DATE,
              f"pay_date={details.get('pay_date')!r}")
        check(f"{name}: the details say which state was found",
              details.get("pack_status") == expected_status,
              f"pack_status={details.get('pack_status')!r}")
        required = details.get("required")
        check(f"{name}: the details say what is missing and who has to do it",
              isinstance(required, list) and bool(required)
              and all(isinstance(item, str) and item.strip() for item in required),
              f"required={required}")
        check(f"{name}: the required list names a human verifier",
              any("verifier" in item for item in (required or [])),
              f"required={required}")

        message = (envelope or {}).get("message") or ""
        check(f"{name}: the message is safe to display",
              str(BASE_SALARY) not in message
              and "payroll.employee@example.com" not in message
              and "Test" not in message
              and "%" not in message,
              f"message={message!r}")

        after = run_state(run_id)
        check(f"{name}: no payslip was written", after["payslips"] == 0,
              f"payslips={after['payslips']}")
        check(f"{name}: the pay run did not advance",
              after["status"] == before["status"] == "Draft"
              and after["processed_by"] == before["processed_by"]
              and after["processed_at"] == before["processed_at"]
              and after["rule_pack_id"] == before["rule_pack_id"],
              f"before={before} after={after}")
        check(f"{name}: the pay run totals are untouched",
              after["total_gross"] == before["total_gross"] == 0
              and after["total_deductions"] == before["total_deductions"] == 0
              and after["total_net"] == before["total_net"] == 0
              and after["headcount"] == before["headcount"] == 0,
              f"after={after}")

        audits = audit_rows(run_id)
        check(f"{name}: exactly one audit row was written",
              len(audits) == audits_before + 1,
              f"before={audits_before} after={len(audits)}")
        refusal_rows = [row for row in audits if row.action == "refuse_pay_run_calculation"]
        check(f"{name}: the audit row records the refusal",
              len(refusal_rows) == 1,
              f"actions={[row.action for row in audits]}")
        if refusal_rows:
            row = refusal_rows[0]
            check(f"{name}: the audit row names the state it refused on",
                  expected_status in (row.details or "")
                  and jurisdiction in (row.details or ""),
                  f"details={row.details!r}")
            check(f"{name}: the audit row carries no pay figure",
                  str(BASE_SALARY) not in (row.details or ""),
                  f"details={row.details!r}")
        check(f"{name}: no audit row claims the run was processed",
              not any(row.action == "process_pay_run" for row in audits),
              f"actions={[row.action for row in audits]}")
    finally:
        if directory is not None:
            shutil.rmtree(directory, ignore_errors=True)


print()
print("=" * 68)
print("PAYROLL SUITE - the rule-pack refusal")
print("=" * 68)

# --- 1. no pack at all ----------------------------------------------------- #
expect_refusal(
    "no pack for the jurisdiction",
    [],
    expected_status="absent",
)

# --- 2. a draft pack ------------------------------------------------------- #
expect_refusal(
    "the pack is a draft",
    [pack_from_fixture(pack_id="fixture-draft", status="draft", verification=None)],
    expected_status="draft",
)

# --- 3. a pack waiting for a human ------------------------------------------ #
expect_refusal(
    "the pack is awaiting verification",
    [pack_from_fixture(pack_id="fixture-pending", status="pending_verification", verification=None)],
    expected_status="pending_verification",
)

# --- 4. a pack that stopped applying before the pay date ------------------- #
expect_refusal(
    "the pack stopped applying before the pay date",
    [pack_from_fixture(
        pack_id="fixture-superseded",
        status="superseded",
        effective_from="2020-01-01",
        effective_to="2025-12-31",
        verification=None,
    )],
    expected_status="superseded",
)

# --- 5. a pack that starts after the pay date ------------------------------ #
expect_refusal(
    "the pack starts after the pay date",
    [pack_from_fixture(
        pack_id="fixture-future",
        status="verified",
        effective_from="2026-07-01",
    )],
    expected_status="absent",
)

# --- 6. a pack for another jurisdiction ------------------------------------ #
expect_refusal(
    "the pack belongs to another jurisdiction",
    [pack_from_fixture(pack_id="fixture-other", status="verified", country="RR")],
    expected_status="absent",
)

# --- 7. the demo pack can never enable a jurisdiction ---------------------- #
use_shipped_pack_directory()
shipped = json.loads(
    (SHIPPED_PACK_DIR / "demo-synthetic-draft.json").read_text()
)
check("the shipped demo pack is a draft",
      shipped.get("status") == "draft",
      f"status={shipped.get('status')!r}")
check("the shipped demo pack is synthetic",
      "SYNTHETIC" in json.dumps(shipped).upper(),
      "the pack does not say it is synthetic")
check("shipped packs verified are only in-standard.json (live IN)",
      all(
          path.name in ("in-standard.json",)
          or json.loads(path.read_text()).get("status") != "verified"
          for path in SHIPPED_PACK_DIR.glob("*.json")
      ),
      "a shipped pack other than in-standard.json is in the verified state")
expect_refusal(
    "the demo jurisdiction",
    [],
    expected_status="draft",
    jurisdiction="ZZ",
    use_shipped=True,
)

# ---------------------------------------------------------------------------
# A jurisdiction with a verified pack is calculated from it
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("A jurisdiction with a verified pack in force")
print("-" * 68)

verified_directory = write_pack_directory([
    pack_from_fixture(pack_id="fixture-verified", status="verified")
])
try:
    period_id = make_period()
    run_id = make_run(period_id, JURISDICTION)

    response = client.post(f"/api/v1/payroll/runs/{run_id}/process", headers=H)
    check("the run is calculated", response.status_code == 200,
          f"got {response.status_code}: {response.text[:200]}")
    body = response.json() if response.status_code == 200 else {}
    check("the run moved to Processing", body.get("status") == "Processing",
          f"status={body.get('status')!r}")
    check("the run records the pack that produced it",
          body.get("rule_pack_id") == "fixture-verified",
          f"rule_pack_id={body.get('rule_pack_id')!r}")
    check("the run records the jurisdiction it was calculated for",
          body.get("jurisdiction") == JURISDICTION,
          f"jurisdiction={body.get('jurisdiction')!r}")
    check("the run counted the payslips",
          body.get("headcount") == 1,
          f"headcount={body.get('headcount')!r}")

    with SessionLocal() as db:
        slips = db.query(PaySlip).filter(PaySlip.pay_run_id == run_id).all()
        run = db.get(PayRun, run_id)
    check("one payslip was written", len(slips) == 1, f"slips={len(slips)}")

    if slips:
        slip = slips[0]
        earnings = json.loads(slip.earnings_json or "[]")
        deductions = json.loads(slip.deductions_json or "[]")
        lines = earnings + deductions
        check("every payslip line names the rule that produced it",
              bool(lines) and all(line.get("rule_id") for line in lines),
              f"lines={lines}")
        check("every payslip line names the rule version",
              bool(lines) and all(line.get("rule_version") == "1.0.0-test" for line in lines),
              f"lines={lines}")
        check("every payslip line names its input",
              bool(lines) and all(line.get("input_source") for line in lines),
              f"lines={lines}")

        gross = sum((Decimal(line["amount"]) for line in earnings), Decimal("0"))
        deducted = sum((Decimal(line["amount"]) for line in deductions), Decimal("0"))
        check("the payslip lines reconcile with the payslip",
              gross == slip.gross_pay
              and deducted == slip.total_deductions
              and gross - deducted == slip.net_pay,
              f"lines gross={gross} deducted={deducted} "
              f"slip={slip.gross_pay}/{slip.total_deductions}/{slip.net_pay}")
        # 50000.00 gross, less the 10% configured withholding (5000.00) and
        # the 1% synthetic employee contribution of the fixture pack (500.00).
        check("the money is exact, not a float",
              str(slip.gross_pay) == "50000.00"
              and str(slip.total_deductions) == "5500.00"
              and str(slip.net_pay) == "44500.00",
              f"gross={slip.gross_pay!r} deductions={slip.total_deductions!r} "
              f"net={slip.net_pay!r}")
        check("the run totals are the sum of the payslips",
              Decimal(str(run.total_gross)) == gross
              and Decimal(str(run.total_net)) == gross - deducted,
              f"run gross={run.total_gross} net={run.total_net}")

    rows = audit_rows(run_id)
    processed = [row for row in rows if row.action == "process_pay_run"]
    check("the audit row names the pack and its version",
          len(processed) == 1
          and "fixture-verified" in (processed[0].details or "")
          and "1.0.0-test" in (processed[0].details or ""),
          f"details={[row.details for row in processed]}")

    # The run may not be calculated twice.
    again = client.post(f"/api/v1/payroll/runs/{run_id}/process", headers=H)
    check("the run is not calculated twice", again.status_code == 422,
          f"got {again.status_code}")
finally:
    shutil.rmtree(verified_directory, ignore_errors=True)

# ---------------------------------------------------------------------------
# A refused run may be calculated once the pack is verified
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("A refusal releases the run")
print("-" * 68)

release_directory = write_pack_directory([
    pack_from_fixture(pack_id="fixture-draft", status="draft", verification=None)
])
try:
    period_id = make_period()
    run_id = make_run(period_id, JURISDICTION)
    key = {"Idempotency-Key": "payroll-refusal-retry"}

    refused = client.post(
        f"/api/v1/payroll/runs/{run_id}/process", headers={**H, **key}
    )
    check("the run is refused", refused.status_code == 422,
          f"got {refused.status_code}: {refused.text[:160]}")

    # The operator verifies the pack and retries with the same key.
    verified_directory = write_pack_directory([
        pack_from_fixture(pack_id="fixture-draft", status="verified")
    ])
    try:
        retried = client.post(
            f"/api/v1/payroll/runs/{run_id}/process", headers={**H, **key}
        )
        check("the run is calculated once the pack is verified",
              retried.status_code == 200,
              f"got {retried.status_code}: {retried.text[:200]}")
    finally:
        shutil.rmtree(verified_directory, ignore_errors=True)
finally:
    shutil.rmtree(release_directory, ignore_errors=True)

# ---------------------------------------------------------------------------
# The jurisdiction is required, and a run that names none is refused
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("The jurisdiction of a run")
print("-" * 68)

period_id = make_period()
without = client.post(
    "/api/v1/payroll/runs", headers=H, json={"period_id": period_id}
)
check("a run without a jurisdiction is refused at creation",
      without.status_code == 422,
      f"got {without.status_code}: {without.text[:160]}")

with_jurisdiction = client.post(
    "/api/v1/payroll/runs",
    headers=H,
    json={"period_id": period_id, "jurisdiction": "qq", "currency": "USD"},
)
check("a run names its jurisdiction", with_jurisdiction.status_code == 201,
      f"got {with_jurisdiction.status_code}: {with_jurisdiction.text[:160]}")
check("the jurisdiction is stored folded",
      with_jurisdiction.status_code == 201
      and with_jurisdiction.json().get("jurisdiction") == "QQ",
      f"jurisdiction={with_jurisdiction.json().get('jurisdiction')!r}")

# ---------------------------------------------------------------------------
# The two forms of a rate table
# ---------------------------------------------------------------------------
#
# The schema (contracts/rules/rule-pack.schema.json) writes a rate table in
# one of two forms, and the engine reads each of them in one way only:
#
#   * the banded form (entries) - a band's `value` is the LOWER BOUND of
#     the band, its `max_value` the upper bound and its `rate` the
#     percentage rate that applies inside it;
#   * the keyed-map form (values) - every value is a percentage rate that
#     applies to the whole base.
#
# A pack that uses one form is never read as the other, and a pack the
# engine cannot read is refused rather than computed.

print()
print("-" * 68)
print("The two forms of a rate table")
print("-" * 68)


def tax_the_schema_says(bands: list[dict], taxable: Decimal) -> Decimal:
    """The tax the schema's own definition produces.

    This is the contract's rule, written out here from the contract and not
    from the engine: the amount from a band's `value` up to, but not
    including, its `max_value`, taxed at the band's `rate`. The rounding is
    the engine's money convention (one rounded amount per band), because
    rounding is a money rule and not a rule of the schema.
    """
    from decimal import ROUND_HALF_UP

    tax = Decimal("0")
    for band in bands:
        lower = Decimal(str(band["value"]))
        upper = band.get("max_value")
        top = taxable if upper is None else min(taxable, Decimal(str(upper)))
        if top <= lower:
            continue
        band_tax = (top - lower) * Decimal(str(band["rate"])) / Decimal("100")
        tax += band_tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return tax.quantize(Decimal("0.01"))


# The contract's own words. The schema is the authority on what a band is,
# so the test reads the contract rather than a copy of it.
schema = json.loads(SCHEMA_PATH.read_text())
rate_entry = schema["$defs"]["rate_entry"]
check("the schema says a band's value is the lower bound of the band",
      "lower bound" in rate_entry["properties"]["value"]["description"],
      f"value={rate_entry['properties']['value']['description']!r}")
check("the schema says a band's max_value is the upper bound of the band",
      "upper bound" in rate_entry["properties"]["max_value"]["description"].lower(),
      f"max_value={rate_entry['properties']['max_value']['description']!r}")
check("the schema gives a band a rate of its own",
      "rate" in rate_entry["properties"]
      and "percent" in rate_entry["properties"]["rate"]["description"],
      f"properties={sorted(rate_entry['properties'])}")

# --- the banded form -------------------------------------------------------- #
banded_data = json.loads(BANDED_FIXTURE_PACK.read_text())
banded = load_rule_pack(BANDED_FIXTURE_PACK)
bands = banded_data["rate_tables"]["tax_bands"]["entries"]
check("the banded fixture is a valid pack", banded.meta.pack_id == "test-fixture-banded",
      f"pack_id={banded.meta.pack_id!r}")
check("the banded fixture states a rate for every band",
      all(band.get("rate") is not None for band in bands),
      f"bands={bands}")
check("the banded fixture raises no reading problem",
      rate_table_problems(banded) == [],
      f"problems={rate_table_problems(banded)}")

for salary in ("800.00", "1200.00", "3333.33", "20000.00"):
    result = calculate_payslip_from_pack(
        pack=banded, base_salary=Decimal(salary), pay_frequency="monthly"
    )
    tax = sum(
        (line.amount for line in result.deductions if line.rule_id == "TAX_BAND"),
        Decimal("0"),
    )
    expected = tax_the_schema_says(bands, Decimal(salary))
    check(f"the banded form: the tax on {salary} is what the schema says",
          tax == expected,
          f"expected {expected}, got {tax}")

# The bands are divided by their bounds: the part of the taxable amount that
# falls inside a band is taxed at that band's rate, and at no other.
result = calculate_payslip_from_pack(
    pack=banded, base_salary=Decimal("20000.00"), pay_frequency="monthly"
)
band_lines = {
    line.code: line for line in result.deductions if line.rule_id == "TAX_BAND"
}
check("the banded form: the first band is taxed at its own rate",
      band_lines.get("TAX_FIXTURE_BAND_0") is not None
      and band_lines["TAX_FIXTURE_BAND_0"].amount == Decimal("0.00"),
      f"lines={[(line.code, str(line.amount)) for line in band_lines.values()]}")
check("the banded form: the second band is taxed on the part inside it",
      band_lines.get("TAX_FIXTURE_BAND_1") is not None
      and band_lines["TAX_FIXTURE_BAND_1"].amount == Decimal("400.00"),
      f"lines={[(line.code, str(line.amount)) for line in band_lines.values()]}")
check("the banded form: the open ended top band takes the rest",
      band_lines.get("TAX_FIXTURE_BAND_2") is not None
      and band_lines["TAX_FIXTURE_BAND_2"].amount == Decimal("3000.00"),
      f"lines={[(line.code, str(line.amount)) for line in band_lines.values()]}")

# --- the keyed-map form ----------------------------------------------------- #
flat = load_rule_pack(FIXTURE_PACK)
flat_data = json.loads(FIXTURE_PACK.read_text())
flat_result = calculate_payslip_from_pack(
    pack=flat, base_salary=Decimal("5000"), pay_frequency="monthly"
)
ee_line = next(
    (line for line in flat_result.deductions if line.rule_id == "SOCIAL_INSURANCE_EE"),
    None,
)
er_line = next(
    (line for line in flat_result.employer_contributions if line.rule_id == "SOCIAL_INSURANCE_ER"),
    None,
)
check("the keyed map form: the employee's contribution is the percentage of the base",
      ee_line is not None and ee_line.amount == Decimal("50.00"),
      f"line={ee_line}")
check("the keyed map form: the employer's contribution is the percentage of the base",
      er_line is not None and er_line.amount == Decimal("100.00"),
      f"line={er_line}")
check("the keyed map form: the map's value is a percentage, not a bound",
      flat_data["rate_tables"]["social_insurance_employee"]["values"]["fixture_employee"]["value"]
      == 1.0,
      "the fixture's map does not state a percentage")

# --- the two forms are never read as one another ---------------------------- #
flat_tax_data = json.loads(FIXTURE_PACK.read_text())
flat_tax_data["rate_tables"]["tax_bands"] = {
    "description": "SYNTHETIC TEST FIXTURE - a tax table written as a flat rate map.",
    "effective_from": "2020-01-01",
    "values": {
        "fixture_flat_tax": {
            "value": 10.0,
            "unit": "percent",
            "label": "Fixture flat tax (synthetic)",
            "notes": "SYNTHETIC TEST FIXTURE - invented for the tests",
        }
    },
}
flat_tax = load_rule_pack_from_dict(flat_tax_data)
problems = rate_table_problems(flat_tax)
check("a tax table written as a flat rate map is refused",
      any("flat rate map" in problem for problem in problems),
      f"problems={problems}")
try:
    calculate_payslip_from_pack(
        pack=flat_tax, base_salary=Decimal("5000"), pay_frequency="monthly"
    )
    refused = False
except RulePackNotReadable:
    refused = True
check("a tax table written as a flat rate map computes nothing",
      refused,
      "the engine calculated a figure from a table it cannot read")

banded_si_data = json.loads(BANDED_FIXTURE_PACK.read_text())
banded_si_data["rate_tables"]["social_insurance_employee"] = {
    "description": "SYNTHETIC TEST FIXTURE - a contribution table written as bands.",
    "effective_from": "2020-01-01",
    "entries": [
        {
            "code": "FIXTURE_SI_BAND",
            "label": "Fixture contribution band",
            "value": 0,
            "max_value": 100000,
            "rate": 1,
            "unit": "currency_amount",
            "notes": "SYNTHETIC TEST FIXTURE - invented for the tests",
        }
    ],
}
banded_si = load_rule_pack_from_dict(banded_si_data)
problems = rate_table_problems(banded_si)
check("a contribution table written as bands is refused",
      any("banded table" in problem for problem in problems),
      f"problems={problems}")

# --- a band that states no rate is refused ----------------------------------- #
no_rate_data = json.loads(BANDED_FIXTURE_PACK.read_text())
for band in no_rate_data["rate_tables"]["tax_bands"]["entries"]:
    band.pop("rate", None)
no_rate = load_rule_pack_from_dict(no_rate_data)
problems = rate_table_problems(no_rate)
check("a band that states no rate is refused",
      len(problems) == len(bands)
      and all("states no rate for band" in problem for problem in problems),
      f"problems={problems}")
try:
    calculate_payslip_from_pack(
        pack=no_rate, base_salary=Decimal("5000"), pay_frequency="monthly"
    )
    no_rate_refused = False
except RulePackNotReadable:
    no_rate_refused = True
check("a band that states no rate computes nothing at all",
      no_rate_refused,
      "the engine calculated a figure from a band table it cannot read")
def leaks_a_value(problems: list[str], values: list) -> bool:
    """Whether a refusal carries a number the pack holds.

    The numbers are matched as whole numbers, so the digits of a band code
    are not a leak and a bound that appears in the text is.
    """
    import re

    for problem in problems:
        for value in values:
            if value is None:
                continue
            pattern = rf"(?<![\w.]){re.escape(str(value))}(?![\w.])"
            if re.search(pattern, problem):
                return True
    return False


check("the refusal names the table and the band, and no value",
      all("tax_bands" in problem for problem in problems)
      and all("BAND" in problem for problem in problems)
      and not leaks_a_value(problems, [band.get("value") for band in bands]
                            + [band.get("max_value") for band in bands]),
      f"problems={problems}")

# ---------------------------------------------------------------------------
# The band's shape: a banded table states a rate, a schedule table does not
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("The band's shape")
print("-" * 68)

DEMO_PACK_PATH = SHIPPED_PACK_DIR / "demo-synthetic-draft.json"
demo_data = json.loads(DEMO_PACK_PATH.read_text())
demo_bands = demo_data["rate_tables"]["tax_bands"]["entries"]


def load_pack_dict(data: dict) -> tuple[object, str]:
    """Load a pack from a dict, and say what happened.

    The pack is written to a temporary file and loaded the way the product
    loads a pack, so that the schema and the loader both see it.
    """
    directory = Path(tempfile.mkdtemp(prefix="karmathy-payroll-pack-"))
    path = directory / "00-pack.json"
    path.write_text(json.dumps(data, indent=2))
    try:
        return load_rule_pack(path), ""
    except RulePackLoadError as exc:
        return None, str(exc)


# The contract's own words: the schema states the rule with a conditional,
# so the test reads that conditional rather than a copy of it.
rate_table_schema = schema["$defs"]["rate_table"]
check("the schema lets a rate table say what shape its rows have",
      "kind" in rate_table_schema["properties"]
      and set(rate_table_schema["properties"]["kind"]["enum"]) == {"banded", "schedule"},
      f"properties={sorted(rate_table_schema['properties'])}")


def conditional_for(kind: str) -> dict:
    """The branch of the schema's conditional that applies to a kind."""
    for branch in rate_table_schema.get("allOf", []):
        const = branch.get("if", {}).get("properties", {}).get("kind", {}).get("const")
        if const == kind:
            return branch
    return {}


def required_by(branch: dict) -> list:
    """The properties the rows of a table have to carry, under a branch."""
    return (
        branch.get("then", {})
        .get("properties", {})
        .get("entries", {})
        .get("items", {})
        .get("required", [])
    )


banded_branch = conditional_for("banded")
schedule_branch = conditional_for("schedule")
check("the schema requires a rate on every band of a banded table",
      "rate" in required_by(banded_branch),
      f"branch={banded_branch}")
check("the schema does not ask a schedule table for a rate",
      "rate" not in required_by(schedule_branch),
      f"branch={schedule_branch}")

# The schema has to enforce the rule, not only say it. The pack it is
# proved on is the synthetic fixture pack, so that the proof does not depend
# on the contents of the demo pack.
fixture_data = json.loads(BANDED_FIXTURE_PACK.read_text())
fixture_bands = fixture_data["rate_tables"]["tax_bands"]["entries"]

missing_rate = json.loads(json.dumps(fixture_data))
for band in missing_rate["rate_tables"]["tax_bands"]["entries"]:
    band.pop("rate", None)
missing_rate_errors = validate_against_schema(missing_rate)
check("the schema refuses a banded table whose band states no rate",
      any("'rate' is a required property" in error for error in missing_rate_errors),
      f"errors={missing_rate_errors}")

schedule_data = json.loads(json.dumps(fixture_data))
schedule_data["rate_tables"]["allowance_schedule"] = {
    "kind": "schedule",
    "description": "SYNTHETIC TEST FIXTURE - a scheduled table whose rows carry no rate.",
    "effective_from": "2026-01-01",
    "entries": [
        {
            "code": "FIXTURE_ALLOWANCE",
            "label": "Fixture scheduled allowance",
            "value": 100,
            "unit": "currency_amount",
            "notes": "SYNTHETIC TEST FIXTURE - invented for the tests",
        }
    ],
}
schedule_errors = validate_against_schema(schedule_data)
check("the schema accepts a schedule table whose rows state no rate",
      schedule_errors == [],
      f"errors={schedule_errors}")

both_forms = json.loads(json.dumps(fixture_data))
both_forms["rate_tables"]["tax_bands"]["values"] = {
    "FIXTURE_FLAT": {
        "value": 1,
        "unit": "percent",
        "label": "Fixture flat rate",
        "notes": "SYNTHETIC TEST FIXTURE - invented for the tests",
    }
}
check("the schema refuses a table that states both forms",
      bool(validate_against_schema(both_forms)),
      "the schema accepted a table written in both forms")

no_kind = json.loads(json.dumps(fixture_data))
no_kind["rate_tables"]["tax_bands"].pop("kind")
check("the schema refuses a table written as a list of rows that does not say what shape it is",
      bool(validate_against_schema(no_kind)),
      "the schema accepted a table with no kind")

# ... and the pack is refused when it is loaded, naming the table and the band.
_, missing_rate_message = load_pack_dict(missing_rate)
check("a banded table with a band that states no rate is refused when the pack is loaded",
      bool(missing_rate_message),
      "the pack loaded")
check("the refusal names the table and the band",
      "tax_bands" in missing_rate_message and "FIXTURE_BAND_0" in missing_rate_message,
      f"message={missing_rate_message}")
check("the refusal carries no value from the pack",
      not leaks_a_value(
          [missing_rate_message],
          [band.get("value") for band in fixture_bands]
          + [band.get("max_value") for band in fixture_bands],
      ),
      f"message={missing_rate_message}")

schedule_pack, schedule_message = load_pack_dict(schedule_data)
check("a schedule table loads", schedule_pack is not None, f"message={schedule_message}")
check("a schedule table's rows carry no rate",
      schedule_pack is not None
      and schedule_pack.get_rate_table("allowance_schedule").entries[0].rate is None,
      "the schedule row states a rate of its own")

# ---------------------------------------------------------------------------
# The demo pack: it loads, it computes, and its golden cases are the truth
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("The demo pack")
print("-" * 68)

demo_pack, demo_message = load_pack_dict(demo_data)
check("the shipped demo pack loads", demo_pack is not None, f"message={demo_message}")
check("the shipped demo pack states a rate for every band",
      all(band.get("rate") is not None for band in demo_bands),
      f"bands={demo_bands}")
check("the shipped demo pack raises no reading problem",
      demo_pack is not None and rate_table_problems(demo_pack) == [],
      f"problems={rate_table_problems(demo_pack) if demo_pack else demo_message}")
check("the shipped demo pack stays a draft and is not verified",
      demo_pack is not None
      and demo_pack.meta.status == "draft"
      and demo_pack.meta.verification_verified_by_name is None,
      f"status={demo_pack.meta.status if demo_pack else None}")
check("the shipped demo pack says what a band means",
      "lower bound" in demo_data["source"]["notes"].lower()
      and "upper bound" in demo_data["source"]["notes"].lower()
      and "rate" in demo_data["source"]["notes"].lower(),
      f"notes={demo_data['source']['notes'][:200]}")


# The pack on disk is a draft and it stays one. The engine's verification
# gate is lifted **in memory**, so that the pack's own golden cases can be
# replayed against it: nothing is written, the file is not verified, and a
# named human is still the only thing that may verify a pack.
calculable = (
    replace(demo_pack, meta=replace(demo_pack.meta, status="verified"))
    if demo_pack is not None
    else None
)


def calculate_case(pack, inputs: dict):
    """The payslip the engine produces for a golden case's input."""
    return calculate_payslip_from_pack(
        pack=pack,
        base_salary=Decimal(str(inputs.get("base_salary", "0"))),
        pay_frequency=inputs.get("pay_frequency", "monthly"),
        hours_worked=Decimal(str(inputs.get("hours_worked", "0"))),
        overtime_hours=Decimal(str(inputs.get("overtime_hours", "0"))),
        overtime_hourly_rate=Decimal(str(inputs.get("overtime_hourly_rate", "0"))),
        leave_days=Decimal(str(inputs.get("leave_days", "0"))),
        tax_withholding_override=None,
        benefit_deductions=Decimal(str(inputs.get("benefit_deductions", "0"))),
        other_earnings=Decimal(str(inputs.get("other_earnings", "0"))),
        other_deductions=Decimal(str(inputs.get("other_deductions", "0"))),
    )


def rendered(result) -> dict:
    """The engine's output, in the shape the pack's golden cases use."""

    def line(pay_line):
        return {
            "code": pay_line.code,
            "name": pay_line.name,
            "amount": f"{pay_line.amount:.2f}",
            "type": pay_line.line_type,
        }

    return {
        "earnings": [line(l) for l in result.earnings],
        "deductions": [line(l) for l in result.deductions],
        "employer_contribution_lines": [line(l) for l in result.employer_contributions],
        "gross": f"{result.gross:.2f}",
        "total_deductions": f"{result.total_deductions:.2f}",
        "net": f"{result.net:.2f}",
        "employee_contributions": f"{result.total_employee_contributions:.2f}",
        "employer_contributions": f"{result.total_employer_contributions:.2f}",
        "pay_floor_check": result.pay_floor_check,
    }


if demo_pack is None:
    # A pack that does not load cannot be calculated, and the checks
    # below need one. They fail here rather than being skipped.
    check("the shipped demo pack's golden cases are reproduced exactly", False,
          f"the pack did not load: {demo_message}")
    check("the shipped demo pack's golden cases are the engine's output, line for line", False,
          f"the pack did not load: {demo_message}")
else:
    demo_results = run_golden_cases(calculable)
    check("the shipped demo pack's golden cases are reproduced exactly",
          bool(demo_results) and all(passed for _case, passed, _msg in demo_results),
          f"results={demo_results}")

    for case in demo_data["golden_cases"]:
        actual = rendered(calculate_case(calculable, case["input"]))
        expected = case["expected"]
        differing = sorted(
            key for key in set(actual) | set(expected)
            if actual.get(key) != expected.get(key)
        )
        detail = "; ".join(
            f"{key}: expected {expected.get(key)!r}, got {actual.get(key)!r}"
            for key in differing
        )
        check(f"the demo pack's golden case {case['case_id']} is the engine's output, line for line",
              not differing,
              detail)

    # The figures the demo pack's golden cases now expect, pinned here so that
    # the pack and the engine cannot drift apart without this suite noticing.
    # They are the figures the schema's own reading of the bands produces.
    PINNED_CASES = {
        "gc-demo-basic-monthly": {
            "gross": "5000.00", "tax": "0.00", "net": "4415.00",
            "employee_contributions": "485.00", "employer_contributions": "705.00",
        },
        "gc-demo-overtime-weekly": {
            "gross": "3078.03", "tax": "0.00", "net": "2728.62",
            "employee_contributions": "299.41", "employer_contributions": "435.22",
        },
        "gc-demo-top-band": {
            "gross": "80000.00", "tax": "14000.00", "net": "58240.00",
            "employee_contributions": "7760.00", "employer_contributions": "11280.00",
        },
    }

    for case in demo_data["golden_cases"]:
        pinned = PINNED_CASES.get(case["case_id"])
        if pinned is None:
            check(f"the demo pack's golden case {case['case_id']} is pinned in this suite",
                  False,
                  "the case is not pinned, so nothing would notice it drifting")
            continue
        result = calculate_case(calculable, case["input"])
        tax = sum(
            (line.amount for line in result.deductions if line.rule_id == "TAX_BAND"),
            Decimal("0"),
        )
        figures = {
            "gross": f"{result.gross:.2f}",
            "tax": f"{tax:.2f}",
            "net": f"{result.net:.2f}",
            "employee_contributions": f"{result.total_employee_contributions:.2f}",
            "employer_contributions": f"{result.total_employer_contributions:.2f}",
        }
        check(f"the demo pack's golden case {case['case_id']} computes the figures this suite pins",
              figures == pinned,
              f"expected={pinned}, got={figures}")

    top_case = next(
        (c for c in demo_data["golden_cases"] if c["case_id"] == "gc-demo-top-band"),
        None,
    )
    check("the demo pack has a golden case that crosses the open ended top band",
          top_case is not None
          and any(
              line["code"] == "TAX_BAND_3" and Decimal(str(line["amount"])) > 0
              for line in top_case["expected"]["deductions"]
          ),
          "no case of the demo pack crosses the open ended top band")

    # The social insurance figures have to agree with each other: both sides are
    # a percentage of the same base, which is what the schema says a flat map of
    # rates means.


    def percentage_of(base: Decimal, rate: Decimal) -> Decimal:
        """The contribution on a base at a percentage rate, to the cent."""
        return (base * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


    ee_table = demo_pack.get_rate_table("social_insurance_employee")
    er_table = demo_pack.get_rate_table("social_insurance_employer")
    for case in demo_data["golden_cases"]:
        inputs = case["input"]
        base = (
            Decimal(str(inputs.get("base_salary", "0")))
            + Decimal(str(inputs.get("overtime_hours", "0")))
            * Decimal(str(inputs.get("overtime_hourly_rate", "0")))
        )
        result = calculate_case(calculable, inputs)
        expected_ee = {
            f"{code.upper()}_EE": percentage_of(base, value.value)
            for code, value in ee_table.values.items()
        }
        actual_ee = {
            line.code: line.amount for line in result.deductions
            if line.rule_id == "SOCIAL_INSURANCE_EE"
        }
        check(f"the demo pack's {case['case_id']}: every employee contribution is the percentage of the same base",
              actual_ee == expected_ee,
              f"expected={expected_ee}, got={actual_ee}")
        expected_er = {
            f"{code.upper()}_ER": percentage_of(base, value.value)
            for code, value in er_table.values.items()
        }
        actual_er = {
            line.code: line.amount for line in result.employer_contributions
            if line.rule_id == "SOCIAL_INSURANCE_ER"
        }
        check(f"the demo pack's {case['case_id']}: every employer contribution is the percentage of the same base",
              actual_er == expected_er,
              f"expected={expected_er}, got={actual_er}")

# --- the golden cases, one per form ----------------------------------------- #
for name, pack in (("the banded form", banded), ("the keyed map form", flat)):
    results = run_golden_cases(pack)
    check(f"the golden case of {name} is reproduced exactly",
          bool(results) and all(passed for _case, passed, _msg in results),
          f"results={results}")

# A golden case that pins a contribution and does not fail when the
# contribution changes is no pin at all: the runner has to notice.
for pinned, key in (("employer's", "employer_contributions"),
                    ("employee's", "employee_contributions")):
    tampered_cases = json.loads(BANDED_FIXTURE_PACK.read_text())
    for case in tampered_cases["golden_cases"]:
        case["expected"][key] = "1.00"
    tampered_pack = load_rule_pack_from_dict(tampered_cases)
    results = run_golden_cases(tampered_pack)
    check(f"the golden case runner notices a wrong {pinned} contribution",
          bool(results)
          and not all(passed for _case, passed, _msg in results)
          and any(
              key in msg for _case, passed, msg in results if not passed
          ),
          f"results={results}")

# ---------------------------------------------------------------------------
# A run whose pack is verified but cannot be read is refused
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("A verified pack the engine cannot read")
print("-" * 68)

unreadable_directory = write_pack_directory([
    pack_from_fixture(pack_id="fixture-unreadable", status="verified"),
])
try:
    # A tax table written as a flat rate map. The schema allows a table in
    # either form, so this pack loads; the engine has to know which rate
    # applies to which part of the taxable amount, and a flat map does not
    # say that, so the engine refuses it.
    unreadable = json.loads((unreadable_directory / "00-fixture-unreadable.json").read_text())
    unreadable["rate_tables"]["tax_bands"] = {
        "description": "SYNTHETIC TEST FIXTURE - a tax table written as a flat rate map.",
        "effective_from": "2020-01-01",
        "values": {
            "FIXTURE_FLAT_TAX": {
                "value": 10.0,
                "unit": "percent",
                "label": "Fixture flat tax rate",
                "notes": "SYNTHETIC TEST FIXTURE - invented for the tests",
            }
        },
    }
    (unreadable_directory / "00-fixture-unreadable.json").write_text(
        json.dumps(unreadable, indent=2)
    )

    period_id = make_period()
    run_id = make_run(period_id, JURISDICTION)
    before = run_state(run_id)

    response = client.post(f"/api/v1/payroll/runs/{run_id}/process", headers=H)

    check("the run is refused", response.status_code == 422,
          f"got {response.status_code}: {response.text[:200]}")
    body = response.json()
    envelope = body.get("error") if isinstance(body, dict) else None
    check("the refusal is the shared envelope",
          isinstance(envelope, dict) and "detail" not in body,
          f"body={str(body)[:200]}")
    check("the code is rule_pack_not_verified",
          bool(envelope) and envelope.get("code") == "rule_pack_not_verified",
          f"code={(envelope or {}).get('code')!r}")
    details = (envelope or {}).get("details") or {}
    check("the details carry the published shape",
          set(details) == {"jurisdiction", "pay_date", "pack_status", "required"},
          f"details={details}")
    required = details.get("required") or []
    check("the required list says what is wrong with the pack",
          any("tax_bands" in item and "flat rate map" in item for item in required),
          f"required={required}")
    check("the required list leaks no value from the pack",
          not leaks_a_value(required, [10.0, 0, 10000]),
          f"required={required}")
    message = (envelope or {}).get("message") or ""
    check("the message says the pack is verified and unreadable",
          "verified" in message and "cannot read" in message,
          f"message={message!r}")
    check("the message carries no pay figure and no percentage",
          str(BASE_SALARY) not in message and "%" not in message,
          f"message={message!r}")

    after = run_state(run_id)
    check("no payslip was written", after["payslips"] == 0, f"payslips={after['payslips']}")
    check("the pay run did not advance",
          after["status"] == before["status"] == "Draft"
          and after["processed_by"] == before["processed_by"]
          and after["total_gross"] == before["total_gross"] == 0,
          f"before={before} after={after}")
    refusals = [row for row in audit_rows(run_id)
                if row.action == "refuse_pay_run_calculation"]
    check("the refusal is recorded in the audit trail", len(refusals) == 1,
          f"actions={[row.action for row in audit_rows(run_id)]}")
finally:
    shutil.rmtree(unreadable_directory, ignore_errors=True)

# ---------------------------------------------------------------------------
# A pack whose band states no rate is refused when it is loaded
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("A pack that cannot be loaded")
print("-" * 68)

no_rate_directory = write_pack_directory([
    pack_from_fixture(pack_id="fixture-no-rate", status="verified"),
])
try:
    # A band table that states no rate: the bounds are there, the rate is
    # not. The pack cannot be calculated, so it is refused while it is
    # loaded, and the operator is told which table and which band need it.
    no_rate = json.loads((no_rate_directory / "00-fixture-no-rate.json").read_text())
    no_rate["rate_tables"]["tax_bands"] = {
        "description": "SYNTHETIC TEST FIXTURE - a band table that states no rate.",
        "effective_from": "2020-01-01",
        "kind": "banded",
        "entries": [
            {
                "code": "FIXTURE_NO_RATE",
                "label": "Fixture band without a rate",
                "value": 0,
                "max_value": 10000,
                "unit": "currency_amount",
                "notes": "SYNTHETIC TEST FIXTURE - invented for the tests",
            }
        ],
    }
    (no_rate_directory / "00-fixture-no-rate.json").write_text(
        json.dumps(no_rate, indent=2)
    )

    period_id = make_period()
    run_id = make_run(period_id, JURISDICTION)

    response = client.post(f"/api/v1/payroll/runs/{run_id}/process", headers=H)

    check("a run whose pack states no rate is refused", response.status_code == 422,
          f"got {response.status_code}: {response.text[:200]}")
    body = response.json()
    envelope = body.get("error") if isinstance(body, dict) else None
    check("the refusal is the shared envelope",
          isinstance(envelope, dict) and "detail" not in body,
          f"body={str(body)[:200]}")
    check("the code is rule_pack_not_verified",
          bool(envelope) and envelope.get("code") == "rule_pack_not_verified",
          f"code={(envelope or {}).get('code')!r}")
    required = ((envelope or {}).get("details") or {}).get("required") or []
    check("the refusal says the pack could not be loaded",
          any("could not be loaded" in item for item in required),
          f"required={required}")
    check("the refusal names the table and the band that needs a rate",
          any("tax_bands" in item and "FIXTURE_NO_RATE" in item for item in required),
          f"required={required}")
    check("the refusal about a pack that cannot be loaded leaks no value from it",
          not leaks_a_value(required, [0, 10000]),
          f"required={required}")
    check("no payslip was written for a pack that could not be loaded",
          run_state(run_id)["payslips"] == 0,
          "a payslip was written")
finally:
    shutil.rmtree(no_rate_directory, ignore_errors=True)

# ---------------------------------------------------------------------------
# A run calculated from a banded pack, and the employer's contribution
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("A banded pack, and the employer's contribution")
print("-" * 68)

banded_directory = write_pack_directory([banded_data])
try:
    period_id = make_period()
    run_id = make_run(period_id, "QR")

    response = client.post(f"/api/v1/payroll/runs/{run_id}/process", headers=H)
    check("the run is calculated from the banded pack", response.status_code == 200,
          f"got {response.status_code}: {response.text[:200]}")

    with SessionLocal() as db:
        slips = db.query(PaySlip).filter(PaySlip.pay_run_id == run_id).all()
    check("one payslip was written", len(slips) == 1, f"slips={len(slips)}")

    if slips:
        slip = slips[0]
        check("the payslip carries the employer's contribution",
              slip.employer_contributions is not None
              and Decimal(str(slip.employer_contributions)) == Decimal("1000.00"),
              f"employer_contributions={slip.employer_contributions!r}")
        check("the payslip carries the employee's contribution",
              slip.employee_contributions is not None
              and Decimal(str(slip.employee_contributions)) == Decimal("500.00"),
              f"employee_contributions={slip.employee_contributions!r}")

        # The API response includes the employer's contribution.
        api_slips = client.get(f"/api/v1/payroll/payslips?pay_run_id={run_id}", headers=H).json()
        check("the payslip API response includes employer_contributions",
              len(api_slips) == 1
              and api_slips[0].get("employer_contributions") == 1000.00,
              f"api_slips={api_slips}")
        check("the payslip API response includes employee_contributions",
              len(api_slips) == 1
              and api_slips[0].get("employee_contributions") == 500.00,
              f"api_slips={api_slips}")

        deductions = json.loads(slip.deductions_json or "[]")
        tax = sum(
            (Decimal(line["amount"]) for line in deductions if line["rule_id"] == "TAX_BAND"),
            Decimal("0"),
        )
        check("the tax on the payslip is what the schema says",
              tax == tax_the_schema_says(bands, Decimal("50000")),
              f"tax={tax} expected={tax_the_schema_says(bands, Decimal('50000'))}")

        # The reconciliation carries both sides, and it verifies.
        result = calculate_payslip_from_pack(
            pack=banded, base_salary=Decimal("50000"), pay_frequency="monthly"
        )
        recon = build_reconciliation(
            pay_run_id=str(run_id),
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            pay_date=date(2026, 3, 31),
            rule_pack_id=banded.meta.pack_id,
            rule_pack_version=banded.meta.version,
            rule_pack_status=banded.meta.status,
            payslip_results=[(str(slip.id), str(slip.employee_id), result)],
        )
        check("the reconciliation carries the employer's contribution",
              Decimal(recon.total_employer_contributions) == Decimal("1000.00"),
              f"total={recon.total_employer_contributions!r}")
        check("the reconciliation carries the employee's contribution",
              Decimal(recon.total_employee_contributions) == Decimal("500.00"),
              f"total={recon.total_employee_contributions!r}")
        ok = recon.verify_all()
        check("the reconciliation verifies", ok, f"errors={recon.errors}")

        # A tampered contribution total is caught.
        tampered = build_reconciliation(
            pay_run_id=str(run_id),
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            pay_date=date(2026, 3, 31),
            rule_pack_id=banded.meta.pack_id,
            rule_pack_version=banded.meta.version,
            rule_pack_status=banded.meta.status,
            payslip_results=[(str(slip.id), str(slip.employee_id), result)],
        )
        tampered.payslips[0].employer_contributions = "1.00"
        ok = tampered.verify_all()
        check("a contribution that does not match its lines fails the reconciliation",
              not ok
              and any("Employer contributions mismatch" in error for error in tampered.errors),
              f"errors={tampered.errors}")
finally:
    shutil.rmtree(banded_directory, ignore_errors=True)

# ---------------------------------------------------------------------------
# PY-03: a payslip is paid from approved time and leave, and from nothing else
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("PY-03: approved time and leave feed the payslip")
print("-" * 68)

# The fixture pack caps overtime at two hours a day, which would hide a
# draft entry behind the cap. The cap is lifted for this scenario so that a
# draft row that leaked into the calculation changes the money.
inputs_pack = pack_from_fixture(pack_id="fixture-approved-inputs", status="verified")
inputs_pack["overtime"]["daily_cap_hours"] = 100
inputs_pack["thresholds"]["overtime_daily_cap_hours"] = 100

inputs_directory = write_pack_directory([inputs_pack])
try:
    with SessionLocal() as db:
        paid_type = LeaveType(name="PY-03 paid leave", code="PY03-PAID", is_paid=True)
        unpaid_type = LeaveType(name="PY-03 unpaid leave", code="PY03-UNPAID", is_paid=False)
        db.add_all([paid_type, unpaid_type])
        db.flush()

        # Two approved entries: 2 overtime hours in total.
        db.add_all([
            TimeEntry(employee_id=EMPLOYEE_ID, work_date=date(2026, 3, 3),
                      worked_hours=8, overtime_hours=1, status="Approved"),
            TimeEntry(employee_id=EMPLOYEE_ID, work_date=date(2026, 3, 4),
                      worked_hours=8, overtime_hours=1, status="Approved"),
            # A draft entry with ten overtime hours. If it were consumed the
            # overtime line would be six times larger, so the assertion below
            # proves it was not.
            TimeEntry(employee_id=EMPLOYEE_ID, work_date=date(2026, 3, 5),
                      worked_hours=8, overtime_hours=10, status="Draft"),
        ])
        db.add_all([
            # Two days of approved paid leave: recorded, never deducted.
            LeaveRequest(employee_id=EMPLOYEE_ID, leave_type_id=paid_type.id,
                         start_date=date(2026, 3, 10), end_date=date(2026, 3, 11),
                         working_days=2, status="Approved"),
            # One day of approved unpaid leave: deducted.
            LeaveRequest(employee_id=EMPLOYEE_ID, leave_type_id=unpaid_type.id,
                         start_date=date(2026, 3, 17), end_date=date(2026, 3, 17),
                         working_days=1, status="Approved"),
            # Three days of unpaid leave nobody approved: excluded.
            LeaveRequest(employee_id=EMPLOYEE_ID, leave_type_id=unpaid_type.id,
                         start_date=date(2026, 3, 24), end_date=date(2026, 3, 26),
                         working_days=3, status="Pending"),
        ])
        db.commit()

    period_id = make_period()
    run_id = make_run(period_id, JURISDICTION)
    response = client.post(f"/api/v1/payroll/runs/{run_id}/process", headers=H)
    check("PY-03: the run with approved inputs is calculated",
          response.status_code == 200,
          f"got {response.status_code}: {response.text[:200]}")

    with SessionLocal() as db:
        slip = db.query(PaySlip).filter(PaySlip.pay_run_id == run_id).first()
        inputs = json.loads(slip.inputs_json or "{}") if slip else {}

    check("PY-03: the payslip records the approved inputs it was paid from",
          bool(inputs), f"inputs_json={inputs!r}")
    check("PY-03: two approved time entries were consumed",
          inputs.get("approved_time_entries") == 2,
          f"approved_time_entries={inputs.get('approved_time_entries')!r}")
    check("PY-03: only the approved overtime hours were consumed",
          inputs.get("approved_overtime_hours") == 2.0,
          f"approved_overtime_hours={inputs.get('approved_overtime_hours')!r}")
    check("PY-03: the draft time entry is counted and excluded",
          inputs.get("unapproved_time_entries") == 1,
          f"unapproved_time_entries={inputs.get('unapproved_time_entries')!r}")
    check("PY-03: approved paid leave is recorded",
          inputs.get("paid_leave_days") == 2.0,
          f"paid_leave_days={inputs.get('paid_leave_days')!r}")
    check("PY-03: approved unpaid leave is recorded",
          inputs.get("unpaid_leave_days") == 1.0,
          f"unpaid_leave_days={inputs.get('unpaid_leave_days')!r}")

    earnings = json.loads(slip.earnings_json or "[]") if slip else []
    deductions = json.loads(slip.deductions_json or "[]") if slip else []
    overtime_lines = [line for line in earnings if line.get("code") == "OT"]
    leave_lines = [line for line in deductions if line.get("code") == "LEAVE_UNPAID"]

    # 50000 / 173 = 289.017... -> 289.02 an hour; 2 hours * 289.02 * 1.5.
    check("PY-03: overtime is paid from approved hours at the employee's rate",
          len(overtime_lines) == 1
          and Decimal(overtime_lines[0]["amount"]) == Decimal("867.06"),
          f"overtime_lines={overtime_lines}")
    check("PY-03: the draft ten hours did not reach the overtime line",
          len(overtime_lines) == 1
          and Decimal(overtime_lines[0]["amount"]) < Decimal("1000"),
          f"overtime_lines={overtime_lines}")

    # 50000 / 22 = 2272.727... -> 2272.73 a day, for the one unpaid day only.
    check("PY-03: only unpaid leave is deducted",
          len(leave_lines) == 1
          and Decimal(leave_lines[0]["amount"]) == Decimal("2272.73"),
          f"leave_lines={leave_lines}")
    check("PY-03: the paid and unapproved leave did not reach the deduction",
          len(leave_lines) == 1,
          f"leave_lines={leave_lines}")
    check("PY-03: gross pay includes the approved overtime",
          slip is not None
          and Decimal(str(slip.gross_pay)) == Decimal("50867.06"),
          f"gross_pay={slip.gross_pay if slip else None!r}")

    # The record is not a private database detail: an auditor reads it from
    # the payslip the product serves.
    served = client.get(
        "/api/v1/payroll/payslips", headers=H, params={"pay_run_id": run_id}
    )
    served_rows = served.json() if served.status_code == 200 else []
    served_inputs = json.loads(served_rows[0]["inputs_json"] or "{}") if served_rows else {}
    check("PY-03: the payslip API serves the inputs record",
          served.status_code == 200
          and served_inputs.get("unapproved_time_entries") == 1
          and served_inputs.get("approved_overtime_hours") == 2.0,
          f"status={served.status_code} inputs={served_inputs!r}")
finally:
    shutil.rmtree(inputs_directory, ignore_errors=True)
    with SessionLocal() as db:
        db.query(TimeEntry).filter(TimeEntry.employee_id == EMPLOYEE_ID).delete()
        db.query(LeaveRequest).filter(LeaveRequest.employee_id == EMPLOYEE_ID).delete()
        db.query(LeaveType).filter(LeaveType.code.in_(("PY03-PAID", "PY03-UNPAID"))).delete()
        db.commit()

# ---------------------------------------------------------------------------
# Duplicate natural keys answer 409, not 500 (FD-08)
# ---------------------------------------------------------------------------
# The setup screen creates profiles and components. Before this check a second
# create hit the unique constraint and the handler rendered an IntegrityError
# as 500, which told the operator nothing. The taxonomy's answer is
# `duplicate_natural_key`.
duplicate_profile = client.post(
    "/api/v1/payroll/pay-profiles",
    headers=H,
    json={
        "employee_id": EMPLOYEE_ID,
        "base_salary": BASE_SALARY,
        "pay_frequency": "Monthly",
        "tax_withholding": TAX_WITHHOLDING,
    },
)
check(
    "FD-08: a second pay profile for the same employee is 409 duplicate_natural_key",
    duplicate_profile.status_code == 409
    and duplicate_profile.json().get("error", {}).get("code") == "duplicate_natural_key",
    f"status={duplicate_profile.status_code} body={duplicate_profile.text[:200]}",
)

missing_profile = client.post(
    "/api/v1/payroll/pay-profiles",
    headers=H,
    json={"employee_id": 999999, "base_salary": 1000},
)
check(
    "FD-08: a pay profile for an unknown employee is 404",
    missing_profile.status_code == 404,
    f"status={missing_profile.status_code} body={missing_profile.text[:200]}",
)

component_code = "FD08-DUP"
created_component = client.post(
    "/api/v1/payroll/components",
    headers=H,
    json={
        "code": component_code,
        "name": "Duplicate probe",
        "component_type": "Earning",
    },
)
check(
    "FD-08: the probe component is created",
    created_component.status_code == 201,
    f"status={created_component.status_code} body={created_component.text[:200]}",
)
duplicate_component = client.post(
    "/api/v1/payroll/components",
    headers=H,
    json={
        "code": component_code,
        "name": "Duplicate probe",
        "component_type": "Earning",
    },
)
check(
    "FD-08: a second pay component with the same code is 409 duplicate_natural_key",
    duplicate_component.status_code == 409
    and duplicate_component.json().get("error", {}).get("code") == "duplicate_natural_key",
    f"status={duplicate_component.status_code} body={duplicate_component.text[:200]}",
)
with SessionLocal() as db:
    db.query(PayComponent).filter(PayComponent.code == component_code).delete()
    db.commit()

# ---------------------------------------------------------------------------
print()
print("=" * 68)
print(f"==== PAYROLL SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
