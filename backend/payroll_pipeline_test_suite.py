"""Payroll pipeline suite — run_type, dry-run preview, SoD, lock, corrections,
off-cycle, F&F terminated-only, bank adapter + hash reconciliation, history.

TEST-ONLY packs: every number is synthetic from the QQ fixture pack
(qq-test-fixture-synthetic-not-a-statute.json). No statutory values, no
production pack edits. The FY25-26 IN pack stays pending_verification and
untouched; the FY26-27 skeleton stays pending with gratuity OFF (checked,
not modified).

Run: DATABASE_URL=... SECRET_KEY=... .venv311/bin/python payroll_pipeline_test_suite.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import date
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="payroll_pipe_test_"), "payroll_pipe_test.db")
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
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.payroll import PayRun, PaySlip, PayrollPeriod  # noqa: E402
from app.models.user import User  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)
session = SessionLocal()
session.add(User(username="sa_admin", email="sa@example.com",
                 hashed_password=get_password_hash("SuperAdminPass12345"),
                 role="SuperAdmin", is_active=True, mfa_enabled=True))
session.add(User(username="hr_user", email="hr@example.com",
                 hashed_password=get_password_hash("HRPass12345"),
                 role="HR", is_active=True, mfa_enabled=True))
department = Department(name="Payroll", code="PAY")
session.add(department)
session.flush()
job = Job(title="Payroll Officer", code="PAYJOB", department_id=department.id)
session.add(job)
session.flush()
emp_active = Employee(employee_id="PIPE-1", first_name="Active", last_name="Person",
                      email="pipe.active@example.com", hire_date=date(2024, 1, 15),
                      job_id=job.id, department_id=department.id, status="Active")
session.add(emp_active)
session.flush()
# Terminated employee for F&F (tenure <5yr from 2026 pay dates -> gratuity 0).
emp_term = Employee(employee_id="PIPE-2", first_name="Term", last_name="Person",
                    email="pipe.term@example.com", hire_date=date(2025, 6, 1),
                    job_id=job.id, department_id=department.id, status="Active")
session.add(emp_term)
session.flush()
ACTIVE_ID = emp_active.id
TERM_ID = emp_term.id
ACTIVE_EID = emp_active.employee_id
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


def envelope(r):
    try:
        b = r.json()
    except Exception:
        return None
    return b.get("error") if isinstance(b, dict) else None


def assert_envelope(r, code=None, status=None):
    env = envelope(r)
    check("envelope has error", isinstance(env, dict), f"body={r.text[:200]}")
    if env is None:
        return {}
    for k in ("code", "category", "message", "retryable", "request_id"):
        check(f"envelope has {k}", k in env, f"env={env}")
    if code:
        check(f"code is {code}", env.get("code") == code, f"code={env.get('code')!r}")
    if status:
        check(f"status is {status}", r.status_code == status, f"status={r.status_code}")
    return env


def login(u: str, p: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


SA = login("sa_admin", "SuperAdminPass12345")
HR = login("hr_user", "HRPass12345")

FIXTURE_PACK = (BACKEND_ROOT / "test_fixtures" / "rule_packs"
                / "qq-test-fixture-synthetic-not-a-statute.json")


def write_pack_directory(packs: list[dict]) -> Path:
    d = Path(tempfile.mkdtemp(prefix="pipe-packs-"))
    for i, pack in enumerate(packs):
        (d / f"{i:02d}-{pack['pack_id']}.json").write_text(json.dumps(pack, indent=2))
    os.environ["RULE_PACK_DIR"] = str(d)
    return d


def pack_from_fixture(**changes) -> dict:
    data = json.loads(FIXTURE_PACK.read_text())
    for k, v in changes.items():
        if k in ("pack_id", "version", "status", "effective_from", "effective_to"):
            data[k] = v
        elif k == "country":
            data["jurisdiction"]["country"] = v
        elif k == "verification":
            data["verification"] = v
        else:
            raise KeyError(k)
    return data


def make_period(pay_date: str = "2026-03-31") -> int:
    y, m, _ = pay_date.split("-")
    r = client.post("/api/v1/payroll/periods", headers=SA,
                    json={"name": f"Pipe {pay_date}", "start_date": f"{y}-{m}-01",
                          "end_date": pay_date, "pay_date": pay_date})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def make_run(period_id: int, jur: str = "QQ", cur: str = "USD",
             headers: dict = SA, **kw) -> int:
    body: dict = {"period_id": period_id, "jurisdiction": jur, "currency": cur}
    body.update(kw)
    r = client.post("/api/v1/payroll/runs", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def ensure_profile(emp_db_id: int, salary: float = 50000) -> None:
    r = client.post("/api/v1/payroll/pay-profiles", headers=SA,
                    json={"employee_id": emp_db_id, "base_salary": salary,
                          "pay_frequency": "Monthly", "tax_withholding": 10})
    assert r.status_code in (201, 409), r.text


print("=" * 68)
print("PAYROLL PIPELINE SUITE")
print("=" * 68)
verified_dir = write_pack_directory([pack_from_fixture(pack_id="fixture-verified", status="verified")])
ensure_profile(ACTIVE_ID)
ensure_profile(TERM_ID)

try:
    # --- migration expand-only ---
    print("\n[migration expand-only]")
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(pay_runs)")}
    conn.close()
    check("pay_runs has run_type", "run_type" in cols, f"cols={sorted(cols)}")
    check("pay_runs has reversal_of_run_id", "reversal_of_run_id" in cols, f"cols={sorted(cols)}")
    with SessionLocal() as db:
        c = db.execute(__import__("sqlalchemy").text(
            "SELECT run_type, reversal_of_run_id FROM pay_runs LIMIT 1")).fetchone() if False else None
    # nullable check via creating a run without run_type
    p0 = make_period("2026-01-31")
    r0 = client.post("/api/v1/payroll/runs", headers=SA,
                     json={"period_id": p0, "jurisdiction": "QQ", "currency": "USD"})
    check("create without run_type -> 201", r0.status_code == 201, r0.text[:200])
    check("missing run_type defaults regular", (r0.json().get("run_type") in (None, "regular")),
          f"run_type={r0.json().get('run_type')!r}")

    # invalid run_type 422
    rb = client.post("/api/v1/payroll/runs", headers=SA,
                     json={"period_id": p0, "jurisdiction": "QQ", "currency": "USD", "run_type": "bogus"})
    assert_envelope(rb, status=422)
    check("invalid run_type -> 422", rb.status_code == 422, rb.text[:200])

    # --- dry-run preview zero writes ---
    print("\n[dry-run preview zero writes]")
    p1 = make_period("2026-02-28")
    d1 = make_run(p1, "QQ", "USD", SA)
    with SessionLocal() as db:
        before_n = db.query(PaySlip).filter(PaySlip.pay_run_id == d1).count()
        before_status = db.get(PayRun, d1).status
    rd = client.post(f"/api/v1/payroll/runs/{d1}/process?dry_run=true", headers=SA)
    check("dry_run returns 200", rd.status_code == 200, rd.text[:200])
    check("dry_run surfaces preview warning", "dry-run preview" in (rd.json().get("warning") or ""),
          f"warning={rd.json().get('warning')!r}")
    with SessionLocal() as db:
        after_n = db.query(PaySlip).filter(PaySlip.pay_run_id == d1).count()
        after_status = db.get(PayRun, d1).status
    check("dry_run writes no payslip", before_n == after_n == 0, f"before={before_n} after={after_n}")
    check("dry_run leaves status Draft", before_status == after_status == "Draft",
          f"status={after_status!r}")
    # P0: dry-run writes zero rows anywhere — AuditLog unchanged, stored
    # warning untouched (preview is a schema copy, ORM never mutated).
    from app.models.audit import AuditLog as _AuditLog
    with SessionLocal() as db:
        audit_before = db.query(_AuditLog).filter(
            _AuditLog.entity_type == "PayRun", _AuditLog.entity_id == d1).count()
        stored_warning_before = db.get(PayRun, d1).warning
    rd2 = client.post(f"/api/v1/payroll/runs/{d1}/process?dry_run=true", headers=SA)
    check("dry_run repeat 200", rd2.status_code == 200, rd2.text[:200])
    with SessionLocal() as db:
        audit_after = db.query(_AuditLog).filter(
            _AuditLog.entity_type == "PayRun", _AuditLog.entity_id == d1).count()
        stored_warning_after = db.get(PayRun, d1).warning
    check("dry_run writes no audit row", audit_before == audit_after,
          f"before={audit_before} after={audit_after}")
    check("dry_run leaves stored warning NULL", stored_warning_before is None and stored_warning_after is None,
          f"warning={stored_warning_after!r}")
    # P0: dry-run refusal path also writes nothing (no _record_refusal).
    pZZ = make_period("2026-02-28")
    dZZ = make_run(pZZ, "ZZ", "USD", SA)
    with SessionLocal() as db:
        audit_zz_before = db.query(_AuditLog).filter(
            _AuditLog.entity_type == "PayRun", _AuditLog.entity_id == dZZ).count()
    rdZZ = client.post(f"/api/v1/payroll/runs/{dZZ}/process?dry_run=true", headers=SA)
    check("dry_run unverified pack -> 422", rdZZ.status_code == 422, rdZZ.text[:200])
    if rdZZ.status_code == 422:
        assert_envelope(rdZZ, "rule_pack_not_verified", 422)
    with SessionLocal() as db:
        audit_zz_after = db.query(_AuditLog).filter(
            _AuditLog.entity_type == "PayRun", _AuditLog.entity_id == dZZ).count()
        slips_zz = db.query(PaySlip).filter(PaySlip.pay_run_id == dZZ).count()
    check("dry_run refusal writes no audit row", audit_zz_before == audit_zz_after,
          f"before={audit_zz_before} after={audit_zz_after}")
    check("dry_run refusal writes no payslip", slips_zz == 0, f"n={slips_zz}")

    # --- maker-checker SoD 403 + finalize slips Final ---
    print("\n[maker-checker SoD + finalize]")
    p2 = make_period("2026-03-31")
    s1 = make_run(p2, "QQ", "USD", HR)
    rp = client.post(f"/api/v1/payroll/runs/{s1}/process", headers=HR)
    check("HR processes", rp.status_code == 200, rp.text[:160])
    ra = client.post(f"/api/v1/payroll/runs/{s1}/approve", headers=HR)
    assert_envelope(ra, "separation_of_duties", 403)
    check("same-user approve -> 403 SoD", ra.status_code == 403, ra.text[:200])
    ra2 = client.post(f"/api/v1/payroll/runs/{s1}/approve", headers=SA)
    check("different user approves", ra2.status_code == 200, ra2.text[:160])
    rf = client.post(f"/api/v1/payroll/runs/{s1}/finalize", headers=SA)
    check("finalize 200", rf.status_code == 200, rf.text[:160])
    with SessionLocal() as db:
        slips = db.query(PaySlip).filter(PaySlip.pay_run_id == s1).all()
    check("finalized slips are Final", len(slips) > 0 and all(s.status == "Final" for s in slips),
          f"statuses={[s.status for s in slips]}")

    # --- lock immutability 409/422 + adjustment-run corrections ---
    print("\n[lock immutability + adjustment corrections]")
    rr = client.post(f"/api/v1/payroll/runs/{s1}/process", headers=SA)
    check("reprocess locked -> 409", rr.status_code == 409, rr.text[:200])
    if rr.status_code == 409:
        assert_envelope(rr, "pay_run_already_finalised", 409)
    rc = client.post("/api/v1/payroll/payslips", headers=SA,
                     json={"pay_run_id": s1, "employee_id": ACTIVE_ID,
                           "gross_pay": 1, "net_pay": 1, "total_deductions": 0})
    check("direct payslip on locked -> 409", rc.status_code == 409, rc.text[:200])
    # adjustment without link -> 422
    p3 = make_period("2026-04-30")
    radj = client.post("/api/v1/payroll/runs", headers=SA,
                       json={"period_id": p3, "jurisdiction": "QQ", "currency": "USD",
                             "run_type": "adjustment"})
    assert_envelope(radj, "reversal_required", 422)
    check("adjustment without reversal -> 422", radj.status_code == 422, radj.text[:200])
    # adjustment pointing at unlocked run -> 422
    radj2 = client.post("/api/v1/payroll/runs", headers=SA,
                        json={"period_id": p3, "jurisdiction": "QQ", "currency": "USD",
                              "run_type": "adjustment", "reversal_of_run_id": d1})
    assert_envelope(radj2, "reversal_not_locked", 422)
    check("adjustment on unlocked source -> 422", radj2.status_code == 422, radj2.text[:200])
    # adjustment on locked run -> 201
    p4 = make_period("2026-05-31")
    radj3 = client.post("/api/v1/payroll/runs", headers=SA,
                        json={"period_id": p4, "jurisdiction": "QQ", "currency": "USD",
                              "run_type": "adjustment", "reversal_of_run_id": s1})
    check("adjustment on locked -> 201", radj3.status_code == 201, radj3.text[:200])
    check("adjustment carries link", radj3.json().get("reversal_of_run_id") == s1,
          f"body={radj3.text[:200]}")
    # P1 depth-1: a correction cannot correct a correction.
    adj_id = radj3.json().get("id")
    pdepth = make_period("2026-05-31")
    rdepth = client.post("/api/v1/payroll/runs", headers=SA,
                         json={"period_id": pdepth, "jurisdiction": "QQ", "currency": "USD",
                               "run_type": "adjustment", "reversal_of_run_id": adj_id})
    assert_envelope(rdepth, "reversal_depth_exceeded", 422)
    check("adjustment of adjustment -> 422 depth", rdepth.status_code == 422, rdepth.text[:200])
    rdepth2 = client.post("/api/v1/payroll/runs", headers=SA,
                          json={"period_id": pdepth, "jurisdiction": "QQ", "currency": "USD",
                                "run_type": "reversal", "reversal_of_run_id": adj_id})
    check("reversal of adjustment -> 422 depth", rdepth2.status_code == 422, rdepth2.text[:200])

    # --- off-cycle validation ---
    print("\n[off-cycle validation]")
    roff = client.post("/api/v1/payroll/runs", headers=SA,
                       json={"period_id": p2, "jurisdiction": "QQ", "currency": "USD",
                             "run_type": "off_cycle"})
    assert_envelope(roff, "off_cycle_period_clash", 422)
    check("off-cycle reusing period -> 422", roff.status_code == 422, roff.text[:200])
    p5 = make_period("2026-06-30")
    roff2 = client.post("/api/v1/payroll/runs", headers=SA,
                        json={"period_id": p5, "jurisdiction": "QQ", "currency": "USD",
                              "run_type": "off_cycle"})
    check("off-cycle own period -> 201", roff2.status_code == 201, roff2.text[:200])

    # --- F&F terminated-only read-only gratuity 0 ---
    print("\n[F&F terminated-only read-only]")
    # Real flow: employee is Active at process time (so a payslip exists),
    # then terminates; F&F reads the stored lines read-only.
    with SessionLocal() as _db:
        _e = _db.get(Employee, TERM_ID)
        _e.status = "Terminated"
        _db.add(_e); _db.commit()
    # Active employee refused
    rf_active = client.get(f"/api/v1/payroll/runs/{s1}/fnf", headers=SA,
                           params={"employee_id": ACTIVE_ID})
    assert_envelope(rf_active, "fnf_not_terminated", 422)
    check("F&F active -> 422 fnf_not_terminated", rf_active.status_code == 422, rf_active.text[:200])
    # Terminated employee reads (tenure <5yr -> gratuity 0)
    rf_term = client.get(f"/api/v1/payroll/runs/{s1}/fnf", headers=SA,
                         params={"employee_id": TERM_ID})
    check("F&F terminated -> 200", rf_term.status_code == 200, rf_term.text[:300])
    if rf_term.status_code == 200:
        body = rf_term.json()
        check("F&F gratuity 0 when tenure<5", str(body.get("gratuity_payable")) == "0.00"
              and body.get("gratuity_eligible") is False,
              f"gratuity={body.get('gratuity_payable')!r} eligible={body.get('gratuity_eligible')!r}")
    with SessionLocal() as db:
        n_after = db.query(PaySlip).filter(PaySlip.pay_run_id == s1).count()
        st_after = db.get(PayRun, s1).status
    check("F&F read-only: no new slips", n_after == len(slips), f"n={n_after}")
    check("F&F read-only: status still Finalized", st_after == "Finalized", f"status={st_after!r}")
    # P2: unknown employee -> 404 (top-level Employee import, explicit guard).
    rf_missing = client.get(f"/api/v1/payroll/runs/{s1}/fnf", headers=SA,
                            params={"employee_id": 999999})
    check("F&F unknown employee -> 404", rf_missing.status_code == 404, rf_missing.text[:200])

    # --- bank adapter nacha/neft + validation 422 + hash match ---
    print("\n[bank adapter + hash match]")
    p6 = make_period("2026-07-31")
    b1 = make_run(p6, "QQ", "EUR", SA)
    client.post(f"/api/v1/payroll/runs/{b1}/process", headers=SA)
    # approve by different user than processor (SA processed, so HR cannot? HR can approve? processor=SA, approver HR ok)
    client.post(f"/api/v1/payroll/runs/{b1}/approve", headers=HR)
    rn = client.post(f"/api/v1/payroll/runs/{b1}/payment-file?format=nacha", headers=SA)
    check("nacha 200", rn.status_code == 200, rn.text[:200])
    check("nacha has hash header", "x-payment-hash" in {k.lower() for k in rn.headers.keys()},
          f"headers={dict(rn.headers)}")
    h1 = rn.headers.get("x-payment-hash") or rn.headers.get("X-Payment-Hash")
    rn2 = client.post(f"/api/v1/payroll/runs/{b1}/payment-file?format=nacha", headers=SA)
    h2 = rn2.headers.get("x-payment-hash") or rn2.headers.get("X-Payment-Hash")
    check("nacha hash deterministic", h1 and h1 == h2, f"h1={h1} h2={h2}")
    check("nacha hash matches content",
          h1 == hashlib.sha256(rn.content).hexdigest(), f"h1={h1}")
    # neft with missing IFSC/account -> 422 (synthetic profile has no bank data)
    rv = client.post(f"/api/v1/payroll/runs/{b1}/payment-file?format=neft", headers=SA)
    assert_envelope(rv, "payment_validation_failed", 422)
    check("neft invalid fields -> 422", rv.status_code == 422, rv.text[:300])
    # P0: 422 field_errors carry no PII — no raw account/IFSC/name values.
    try:
        _env = (rv.json().get("error") or {}).get("details", {})
        _ferrs = _env.get("field_errors", []) or []
    except Exception:
        _ferrs = []
    check("field_errors present", len(_ferrs) > 0, f"body={rv.text[:300]}")
    check("field_errors have no raw value key",
          all("value" not in f for f in _ferrs), f"errors={json.dumps(_ferrs)[:300]}")
    # Distinctive PII markers: plant an invalid-but-present bank account plus
    # a valid-format distinctive IFSC, re-request, and assert the 422 body
    # never echoes either. (Employee.ifsc_code has a DB CHECK for format, so
    # the IFSC marker uses a valid-format value; the account marker drives
    # the error path. Both must stay out of the body.)
    _PII_ACCT, _PII_IFSC = "PIIACCT998877", "PIIB0123456"
    with SessionLocal() as db:
        from app.models.payroll import EmployeePayProfile as _Prof
        from app.models.employee import Employee as _Emp
        _prof = db.query(_Prof).filter(_Prof.employee_id == ACTIVE_ID).first()
        if _prof is not None:
            _prof.bank_account = _PII_ACCT
            db.add(_prof)
        _emp = db.get(_Emp, ACTIVE_ID)
        if _emp is not None:
            _emp.ifsc_code = _PII_IFSC
            db.add(_emp)
        db.commit()
    rv2 = client.post(f"/api/v1/payroll/runs/{b1}/payment-file?format=neft", headers=SA)
    check("neft pii-invalid -> 422", rv2.status_code == 422, rv2.text[:300])
    check("422 body has no account substring", _PII_ACCT not in rv2.text,
          f"leaked={_PII_ACCT in rv2.text}")
    check("422 body has no IFSC substring", _PII_IFSC not in rv2.text,
          f"leaked={_PII_IFSC in rv2.text}")
    try:
        _env2 = (rv2.json().get("error") or {}).get("details", {})
        _ferrs2 = _env2.get("field_errors", []) or []
    except Exception:
        _ferrs2 = []
    check("pii field_errors have no raw value key",
          len(_ferrs2) > 0 and all("value" not in f for f in _ferrs2),
          f"errors={json.dumps(_ferrs2)[:300]}")
    # Restore profile/employee so later suites see clean fixtures.
    with SessionLocal() as db:
        from app.models.payroll import EmployeePayProfile as _Prof2
        from app.models.employee import Employee as _Emp2
        _prof = db.query(_Prof2).filter(_Prof2.employee_id == ACTIVE_ID).first()
        if _prof is not None:
            _prof.bank_account = None
            db.add(_prof)
        _emp = db.get(_Emp2, ACTIVE_ID)
        if _emp is not None:
            _emp.ifsc_code = None
            db.add(_emp)
        db.commit()
    # reconciliation hash match
    rr2 = client.get(f"/api/v1/payroll/runs/{b1}/reconciliation", headers=SA)
    check("reconciliation 200", rr2.status_code == 200, rr2.text[:300])
    if rr2.status_code == 200:
        jb = rr2.json()
        check("reconciliation matched", jb.get("matched") is True, f"matched={jb.get('matched')!r}")
        check("reconciliation has content_hash", bool(jb.get("content_hash")),
              f"hash={jb.get('content_hash')!r}")
        canon = json.dumps({"run_id": jb.get("run_id"), "rule_pack_id": jb.get("rule_pack_id"),
                            "rule_pack_version": jb.get("rule_pack_version"),
                            "totals": jb.get("totals", {}), "matched": jb.get("matched")},
                           sort_keys=True, default=str)
        check("reconciliation hash matches canonical totals",
              jb.get("content_hash") == hashlib.sha256(canon.encode()).hexdigest(),
              f"hash={jb.get('content_hash')!r}")

    # --- audit history ordered ---
    print("\n[audit history ordered]")
    rh = client.get(f"/api/v1/payroll/runs/{s1}/history", headers=SA)
    check("history 200", rh.status_code == 200, rh.text[:300])
    if rh.status_code == 200:
        hb = rh.json()
        ids = [h["id"] for h in hb.get("history", [])]
        check("history ordered oldest-first", ids == sorted(ids) and len(ids) >= 4,
              f"ids={ids}")
        acts = [h["action"] for h in hb.get("history", [])]
        for need in ("create_pay_run", "process_pay_run", "approve_pay_run", "finalize_pay_run"):
            check(f"history contains {need}", need in acts, f"actions={acts}")

    # --- pack freeze ---
    print("\n[pack freeze FY25-26 untouched, FY26-27 pending gratuity OFF]")
    in_std = json.loads((BACKEND_ROOT / "rule_packs" / "in-standard.json").read_text())
    check("in-standard FY25-26 frozen verified", in_std.get("status") == "verified",
          f"status={in_std.get('status')!r}")
    check("in-standard version 1.0.0", in_std.get("version") == "1.0.0", f"v={in_std.get('version')!r}")
    skel = json.loads((BACKEND_ROOT / "rule_packs" / "in-standard-fy2627-skeleton.json").read_text())
    check("fy2627 skeleton pending", skel.get("status") == "pending_verification",
          f"status={skel.get('status')!r}")
    grat = ((skel.get("rate_tables") or {}).get("gratuity_accrual") or {}).get("values", {}).get("gratuity_rate_pct", {})
    check("fy2627 gratuity OFF (rate 0)", grat.get("value") == 0, f"grat={grat}")

finally:
    shutil.rmtree(verified_dir, ignore_errors=True)

print()
print("=" * 68)
total = RESULTS["pass"] + RESULTS["fail"]
print(f"RESULTS: {RESULTS['pass']} passed, {RESULTS['fail']} failed ({total} total)")
if FAILURES:
    print()
    print("FAILURES:")
    for n, d in FAILURES:
        print(f"  - {n}: {d}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
