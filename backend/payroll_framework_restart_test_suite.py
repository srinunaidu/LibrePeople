"""Payroll framework restart suite — Stage 5.

Stage 5 restarts the framework for FY26-27 without touching FY25-26. It proves
six things, all with synthetic or shipped-structure inputs — no statutory
value is invented here:

1. **The FY26-27 skeleton is pending and structure-only.** It loads,
   schema-validates, carries ``status == pending_verification`` with no
   verification, is effective from 2026-04-01 open-ended, and every numeric
   rate/value in it is 0 (thresholds/overtime numerics null). Its only
   golden cases are the 14 P5 TEST-ONLY placeholders (zero amounts,
   ``placeholder: true``). It must never drive a calculation.
2. **The resolver is None from 2026-04-01 with no fallback.** IN on
   2025-10-01 and 2026-03-31 resolves the verified FY25-26 pack; IN on
   2026-04-01 and later resolves ``pack=None`` (pending skeleton in force,
   not verified). FY25-26 is never applied past 2026-03-31.
3. **The lifecycle fails closed.** A direct payslip write is refused before
   any write — ``caller_supplied_amounts_refused`` when the pack is verified,
   ``rule_pack_not_verified`` when it is not — and the payslip page is
   refused when the stored pack cannot be found. Refusals write an audit row
   that carries no amount.
4. **The trace is content-bound.** The pack carries a ``content_sha`` (sha256
   of canonical JSON); the trace id hashes pack identity + content + inputs,
   so identical runs trace identically and different content never collides.
5. **Gratuity is OFF unless scoped and verified.** The shipped FY25-26 pack
   declares gratuity out of scope, so no accrual even at tenure 6. A synthetic
   TEST-ONLY in-memory pack that declares scope accrues at 5 years and not at
   4.9; scope without verification is refused. The TEST-ONLY marker never
   appears in a shipped pack.
6. **Money is Decimal HALF_UP, never float.** ``money()`` rounds half up at
   the cent; intermediate values never pass through binary float.

Run:  python payroll_framework_restart_test_suite.py
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="payroll_restart_test_"), "payroll_restart_test.db")

BACKEND_ROOT = Path(__file__).resolve().parent
#: The pack directory the product ships with (root ``rule_packs/``, which
#: mirrors the backend source via symlinks).
SHIPPED_PACK_DIR = BACKEND_ROOT.parent / "rule_packs"
IN_STANDARD = BACKEND_ROOT / "rule_packs" / "in-standard.json"
SKELETON = BACKEND_ROOT / "rule_packs" / "in-standard-fy2627-skeleton.json"

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["RULE_PACK_DIR"] = str(SHIPPED_PACK_DIR)

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
from app.models.payroll import EmployeePayProfile, PayRun, PayrollPeriod, PaySlip  # noqa: E402
from app.models.user import User  # noqa: E402
from app.rules.engine import calculate_payslip_from_pack  # noqa: E402
from app.rules.loader import load_rule_pack  # noqa: E402
from app.rules.money import money, to_decimal  # noqa: E402
from app.rules.resolver import resolve_rule_pack  # noqa: E402

from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

session = SessionLocal()
session.add(User(
    username="payroll_restart_admin", email="payroll_restart_admin@example.com",
    hashed_password=get_password_hash("PayrollPass12345"),
    role="SuperAdmin", is_active=True,
    mfa_enabled=True,  # item 10: privileged users are enrolled
))
department = Department(name="PayrollRestart", code="PAYR")
session.add(department)
session.flush()
job = Job(title="Payroll Officer", code="PAYRJOB", department_id=department.id)
session.add(job)
session.flush()
employee = Employee(
    employee_id="PAYR-1", first_name="Restart", last_name="Person",
    email="payroll.restart.employee@example.com", hire_date=date(2026, 1, 1),
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
        json={"username": "payroll_restart_admin", "password": "PayrollPass12345"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


H = headers()


def make_period(name: str, start: str, end: str, pay_date: str) -> int:
    response = client.post(
        "/api/v1/payroll/periods",
        headers=H,
        json={"name": name, "start_date": start, "end_date": end, "pay_date": pay_date},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def make_run(period_id: int, jurisdiction: str, currency: str) -> int:
    response = client.post(
        "/api/v1/payroll/runs",
        headers=H,
        json={"period_id": period_id, "jurisdiction": jurisdiction, "currency": currency},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def ensure_profile() -> None:
    with SessionLocal() as db:
        exists = db.query(EmployeePayProfile).filter(
            EmployeePayProfile.employee_id == EMPLOYEE_ID
        ).count() > 0
    if not exists:
        response = client.post(
            "/api/v1/payroll/pay-profiles",
            headers=H,
            json={
                "employee_id": EMPLOYEE_ID,
                "base_salary": 50000,
                "pay_frequency": "Monthly",
                "tax_withholding": 10,
                "pt_state": "KA",
            },
        )
        assert response.status_code == 201, response.text


print("=" * 68)
print("STAGE 5-1 — the FY26-27 skeleton is pending and structure-only")
print("=" * 68)

try:
    fy2526 = load_rule_pack(str(IN_STANDARD))
    check("FY25-26 loads", True)
except Exception as e:
    check("FY25-26 loads", False, f"{type(e).__name__}: {e}")
    fy2526 = None

try:
    skeleton = load_rule_pack(str(SKELETON))
    check("skeleton loads schema-valid", True)
except Exception as e:
    check("skeleton loads schema-valid", False, f"{type(e).__name__}: {e}")
    skeleton = None

if skeleton is not None:
    check("skeleton pack_id is in-standard (lineage, not a fork)",
          skeleton.meta.pack_id == "in-standard", skeleton.meta.pack_id)
    check("skeleton status is pending_verification",
          skeleton.meta.status == "pending_verification", skeleton.meta.status)
    check("skeleton verification is null (no sign-off)",
          skeleton.meta.verification_verified_by_name is None
          and skeleton.meta.verification_golden_case_set_id is None)
    check("skeleton effective_from is 2026-04-01",
          skeleton.meta.effective_from == date(2026, 4, 1), str(skeleton.meta.effective_from))
    check("skeleton effective_to is open", skeleton.meta.effective_to is None)
    check("skeleton ships 14 P5 TEST-ONLY placeholders and nothing else",
          len(skeleton.golden_cases) == 14
          and all("TEST-ONLY placeholder" in (gc.description or "")
                  for gc in skeleton.golden_cases)
          and all((gc.expected or {}).get("placeholder") is True
                  for gc in skeleton.golden_cases),
          f"n={len(skeleton.golden_cases)}")
    non_zero = []
    for tname, table in skeleton.rate_tables.items():
        for entry in table.entries:
            if entry.rate != Decimal("0"):
                non_zero.append((tname, entry.code, str(entry.rate)))
        for code, value in table.values.items():
            if value.value != Decimal("0"):
                non_zero.append((tname, code, str(value.value)))
    check("skeleton carries no values (every rate/value is 0)", not non_zero, str(non_zero[:5]))
    check("skeleton thresholds assert nothing",
          skeleton.thresholds.weekly_max_hours is None
          and skeleton.thresholds.overtime_premium_multiplier is None)
    check("skeleton overtime asserts nothing",
          skeleton.overtime.daily_threshold_hours is None
          and skeleton.overtime.premium_multiplier is None
          and skeleton.overtime.rules == ())
    check("skeleton gratuity explicitly out of scope",
          skeleton.rate_tables["gratuity_accrual"].in_scope is False)
    try:
        calculate_payslip_from_pack(pack=skeleton, base_salary=Decimal("50000"), pay_frequency="monthly")
        check("skeleton calculation is refused (not verified)", False, "no refusal raised")
    except ValueError as e:
        check("skeleton calculation is refused (not verified)", "not verified" in str(e), str(e)[:160])

if fy2526 is not None:
    check("FY25-26 version untouched (1.0.0)", fy2526.meta.version == "1.0.0", fy2526.meta.version)
    check("FY25-26 status untouched (verified)", fy2526.meta.status == "verified", fy2526.meta.status)
    check("FY25-26 period untouched",
          fy2526.meta.effective_from == date(2025, 4, 1) and fy2526.meta.effective_to == date(2026, 3, 31),
          f"{fy2526.meta.effective_from}..{fy2526.meta.effective_to}")
    check("FY25-26 PF ceiling untouched (15000)",
          fy2526.rate_tables["social_insurance_ceilings"].values["pf_wage_ceiling"].value == Decimal("15000"))
    check("FY25-26 ESI limit untouched (21000)",
          fy2526.rate_tables["social_insurance_ceilings"].values["esi_wage_limit"].value == Decimal("21000"))
    check("FY25-26 gratuity rate untouched (4.81)",
          fy2526.rate_tables["gratuity_accrual"].values["gratuity_rate_pct"].value == Decimal("4.81"))
    check("FY25-26 gratuity out of scope", fy2526.rate_tables["gratuity_accrual"].in_scope is False)

print("=" * 68)
print("STAGE 5-2 — the resolver is None from 2026-04-01 with no fallback")
print("=" * 68)

r_oct25 = resolve_rule_pack("IN", date(2025, 10, 1))
check("IN 2025-10-01 resolves verified FY25-26",
      r_oct25.is_verified and r_oct25.pack is not None and r_oct25.pack.meta.version == "1.0.0",
      f"pack={r_oct25.pack.meta.version if r_oct25.pack else None} status={r_oct25.pack_status}")
r_mar31 = resolve_rule_pack("IN", date(2026, 3, 31))
check("IN 2026-03-31 resolves verified FY25-26 (last day)",
      r_mar31.is_verified and r_mar31.pack is not None and r_mar31.pack.meta.version == "1.0.0",
      f"pack={r_mar31.pack.meta.version if r_mar31.pack else None} status={r_mar31.pack_status}")
r_apr01 = resolve_rule_pack("IN", date(2026, 4, 1))
check("IN 2026-04-01 resolves pack None (skeleton pending, no fallback)",
      r_apr01.pack is None and not r_apr01.is_verified,
      f"pack={r_apr01.pack} status={r_apr01.pack_status}")
check("IN 2026-04-01 reports pending_verification",
      r_apr01.pack_status == "pending_verification", r_apr01.pack_status)
r_oct26 = resolve_rule_pack("IN", date(2026, 10, 1))
check("IN 2026-10-01 resolves pack None (no fallback to FY25-26)",
      r_oct26.pack is None and not r_oct26.is_verified,
      f"pack={r_oct26.pack} status={r_oct26.pack_status}")
r_us = resolve_rule_pack("US", date(2026, 10, 1))
# The US pack was intentionally removed (India-first): commit b14261a
# "Remove out-of-scope US rule pack"; the shipped verified allowlist is
# in-standard.json only. The US lane is therefore expected to be absent,
# not verified — same expectation as payroll_test_suite.py adopted there.
check("US 2026-10-01 resolves absent (us-pack removed, IN-only)",
      r_us.pack is None and not r_us.is_verified and r_us.pack_status == "absent",
      f"status={r_us.pack_status}")

print("=" * 68)
print("STAGE 5-3 — the trace is content-bound and money is Decimal HALF_UP")
print("=" * 68)

if fy2526 is not None:
    check("content_sha is a 64-hex sha256",
          len(fy2526.content_sha) == 64 and all(c in "0123456789abcdef" for c in fy2526.content_sha),
          fy2526.content_sha[:24])
    again = load_rule_pack(str(IN_STANDARD))
    check("content_sha is stable across loads", again.content_sha == fy2526.content_sha)
    raw = json.loads(IN_STANDARD.read_text())
    expected = hashlib.sha256(
        json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    check("content_sha is the canonical sha of the file bytes-as-parsed", fy2526.content_sha == expected)
    t1 = calculate_payslip_from_pack(pack=fy2526, base_salary=Decimal("50000"), pay_frequency="monthly")
    t2 = calculate_payslip_from_pack(pack=fy2526, base_salary=Decimal("50000"), pay_frequency="monthly")
    check("identical inputs trace identically", t1.trace_id == t2.trace_id, f"{t1.trace_id} vs {t2.trace_id}")
    t3 = calculate_payslip_from_pack(pack=fy2526, base_salary=Decimal("50001"), pay_frequency="monthly")
    check("different inputs trace differently", t1.trace_id != t3.trace_id)
    renamed_raw = json.loads(IN_STANDARD.read_text())
    renamed_raw["name"] = "FY25-26 with a relabelled note"
    from app.rules.loader import load_rule_pack_from_dict  # noqa: E402
    renamed_note = load_rule_pack_from_dict(renamed_raw)
    t4 = calculate_payslip_from_pack(pack=renamed_note, base_salary=Decimal("50000"), pay_frequency="monthly")
    check("different content traces differently (sha in trace)",
          t1.trace_id != t4.trace_id and renamed_note.content_sha != fy2526.content_sha)

check("money rounds half up (2.345 -> 2.35)", money("2.345") == Decimal("2.35"), str(money("2.345")))
check("money rounds half up (2.335 -> 2.34)", money("2.335") == Decimal("2.34"), str(money("2.335")))
check("no binary float in the path (0.1 is exact)",
      to_decimal(0.1) == Decimal("0.1"), str(to_decimal(0.1)))
check("money takes Decimal without drift",
      money(Decimal("33333.33")) == Decimal("33333.33"))

print("=" * 68)
print("STAGE 5-4 — gratuity OFF unless scoped and verified (TEST-ONLY scope)")
print("=" * 68)

TEST_ONLY = "TEST ONLY synthetic pack - must not ship"
if fy2526 is not None:
    r6 = calculate_payslip_from_pack(
        pack=fy2526, base_salary=Decimal("50000"), pay_frequency="monthly",
        pt_state="KA", basic_pct=Decimal("50"), tenure_years=Decimal("6"),
    )
    check("shipped verified pack emits no gratuity at tenure 6 (out of scope)",
          not any(c.code == "GRATUITY_ACCRUAL" for c in r6.employer_contributions))
    scoped = replace(
        fy2526,
        meta=replace(fy2526.meta, pack_id="test-only-gratuity-restart", name=TEST_ONLY),
        rate_tables={**fy2526.rate_tables,
                     "gratuity_accrual": replace(fy2526.rate_tables["gratuity_accrual"], in_scope=True)},
    )
    s5 = calculate_payslip_from_pack(
        pack=scoped, base_salary=Decimal("50000"), pay_frequency="monthly",
        pt_state="KA", basic_pct=Decimal("50"), tenure_years=Decimal("5"),
    )
    got = [c for c in s5.employer_contributions if c.code == "GRATUITY_ACCRUAL"]
    check("TEST-ONLY scoped pack accrues at tenure 5",
          len(got) == 1 and got[0].amount == Decimal("1202.50"),
          str([(c.code, c.amount) for c in s5.employer_contributions]))
    s49 = calculate_payslip_from_pack(
        pack=scoped, base_salary=Decimal("50000"), pay_frequency="monthly",
        pt_state="KA", basic_pct=Decimal("50"), tenure_years=Decimal("4.9"),
    )
    check("TEST-ONLY scoped pack accrues nothing below 5 years",
          not any(c.code == "GRATUITY_ACCRUAL" for c in s49.employer_contributions))
    unscoped_unverified = replace(
        scoped, meta=replace(scoped.meta, status="pending_verification"),
    )
    try:
        calculate_payslip_from_pack(pack=unscoped_unverified, base_salary=Decimal("50000"),
                                    pay_frequency="monthly", tenure_years=Decimal("6"))
        check("scope without verification is refused", False, "no refusal raised")
    except ValueError as e:
        check("scope without verification is refused", "not verified" in str(e), str(e)[:160])
    shipped_text = " ".join(p.read_text(encoding="utf-8") for p in (BACKEND_ROOT / "rule_packs").glob("*.json"))
    check("no shipped pack carries the TEST-ONLY marker",
          "test-only-gratuity-restart" not in shipped_text and TEST_ONLY not in shipped_text)

print("=" * 68)
print("STAGE 5-5 — the lifecycle fails closed (direct write + payslip page)")
print("=" * 68)

ensure_profile()


def payslip_write_attempt(run_id: int):
    return client.post(
        "/api/v1/payroll/payslips",
        headers=H,
        json={
            "pay_run_id": run_id,
            "employee_id": EMPLOYEE_ID,
            "gross_pay": 123456,
            "net_pay": 123456,
            "total_deductions": 0,
        },
    )


def slips_for_run(run_id: int) -> int:
    with SessionLocal() as db:
        return db.query(PaySlip).filter(PaySlip.pay_run_id == run_id).count()


def refusals_for_run(run_id: int) -> int:
    with SessionLocal() as db:
        return db.query(AuditLog).filter(
            AuditLog.entity_type == "PayRun",
            AuditLog.entity_id == run_id,
            AuditLog.action == "refuse_payslip_create",
        ).count()


# L1. Verified FY25-26 pack in force: the caller-supplied amounts are refused.
period_oct25 = make_period("Restart Oct25", "2025-10-01", "2025-10-31", "2025-10-15")
run_oct25 = make_run(period_oct25, "IN", "INR")
before = slips_for_run(run_oct25)
refusals_before = refusals_for_run(run_oct25)
resp = payslip_write_attempt(run_oct25)
body = resp.json() if resp.content else {}
envelope = body.get("error") if isinstance(body, dict) else None
check("L1 verified pack: direct write refused with 422",
      resp.status_code == 422, f"got {resp.status_code}: {resp.text[:200]}")
check("L1 verified pack: code is caller_supplied_amounts_refused",
      bool(envelope) and envelope.get("code") == "caller_supplied_amounts_refused",
      f"envelope={envelope!r}")
check("L1 verified pack: message carries no caller amount",
      "123456" not in resp.text, resp.text[:200])
check("L1 verified pack: no payslip written", slips_for_run(run_oct25) == before == 0)
check("L1 verified pack: refusal recorded in audit",
      refusals_for_run(run_oct25) == refusals_before + 1)

# L2. FY26-27 date: no verified pack in force — refused as rule_pack_not_verified.
period_apr26 = make_period("Restart Apr26", "2026-04-01", "2026-04-30", "2026-04-15")
run_apr26 = make_run(period_apr26, "IN", "INR")
resp2 = payslip_write_attempt(run_apr26)
body2 = resp2.json() if resp2.content else {}
envelope2 = body2.get("error") if isinstance(body2, dict) else None
details2 = (envelope2 or {}).get("details") or {}
check("L2 FY26-27 date: direct write refused with 422",
      resp2.status_code == 422, f"got {resp2.status_code}: {resp2.text[:200]}")
check("L2 FY26-27 date: code is rule_pack_not_verified",
      bool(envelope2) and envelope2.get("code") == "rule_pack_not_verified",
      f"envelope={envelope2!r}")
check("L2 FY26-27 date: details say pending_verification",
      details2.get("pack_status") == "pending_verification", f"details={details2!r}")
check("L2 FY26-27 date: no payslip written", slips_for_run(run_apr26) == 0)

# L3. The payslip page fails closed when the stored pack cannot be found.
with SessionLocal() as db:
    ghost = db.get(PayRun, run_apr26)
    ghost.rule_pack_id = "no-such-pack"
    slip = PaySlip(
        pay_run_id=run_apr26, employee_id=EMPLOYEE_ID,
        gross_pay=50000, net_pay=45000, total_deductions=5000,
        earnings_json="[]", deductions_json="[]", status="Draft", currency="INR",
    )
    db.add(slip)
    db.commit()
    db.refresh(slip)
    ghost_slip_id = slip.id
pdf_ghost = client.get(f"/api/v1/payroll/payslips/{ghost_slip_id}/pdf", headers=H)
ghost_body = pdf_ghost.json() if pdf_ghost.headers.get("content-type", "").startswith("application/json") else {}
ghost_envelope = ghost_body.get("error") if isinstance(ghost_body, dict) else None
check("L3 unresolvable pack: payslip page refused with 422",
      pdf_ghost.status_code == 422
      and bool(ghost_envelope) and ghost_envelope.get("code") == "rule_pack_not_verified",
      f"got {pdf_ghost.status_code}: {pdf_ghost.text[:200]}")
check("L3 unresolvable pack: nothing rendered from a hard-coded pack",
      "no-such-pack" not in pdf_ghost.text and "v1.0.0" not in pdf_ghost.text,
      pdf_ghost.text[:200])

# L4. A processed FY25-26 run renders its page with the verified badge.
process = client.post(f"/api/v1/payroll/runs/{run_oct25}/process", headers=H)
check("L4 FY25-26 run processes (verified pack)", process.status_code == 200,
      f"got {process.status_code}: {process.text[:200]}")
with SessionLocal() as db:
    real_slip = db.query(PaySlip).filter(PaySlip.pay_run_id == run_oct25).first()
    real_slip_id = real_slip.id if real_slip else None
check("L4 processing wrote a payslip", real_slip_id is not None)
if real_slip_id is not None:
    pdf = client.get(f"/api/v1/payroll/payslips/{real_slip_id}/pdf", headers=H)
    check("L4 payslip page renders (200)", pdf.status_code == 200, f"got {pdf.status_code}")
    check("L4 page carries the verified pack badge",
          "in-standard" in pdf.text and "v1.0.0" in pdf.text, pdf.text[:200])
    check("L4 page carries no pending watermark",
          "pending_verification" not in pdf.text.lower(), pdf.text[:200])

print("=" * 68)
print(f"PAYROLL FRAMEWORK RESTART: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print("Failures:")
    for name, detail in FAILURES:
        print(f"  FAIL  {name}  {detail}")
    raise SystemExit(1)
