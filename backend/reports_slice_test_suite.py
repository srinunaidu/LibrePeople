"""Workforce reports slice suite — LP-REP-001..004.

Joiners / leavers / attrition queries with entity, department and location
filters plus per-caller visibility; endpoints with from/to/year/format
validation (422) and role gating (403); payroll-summary reads stored
payslip rows only (a distinctive stored figure the engine could never
produce is returned verbatim); CSV/XLSX exports mask identifiers per role
and are audit-logged. No payroll engine call, no migration, no demo
numbers — every row below is a fixture fact this file creates.

Run:  python reports_slice_test_suite.py
"""
import io
import os
import tempfile
import zipfile
from datetime import date

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="reports_slice_test_"), "reports_slice_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.core_hr import LegalEntity, Location, Position  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.payroll import PayRun, PayrollPeriod, PaySlip  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()

eng = Department(name="SliceEng", code="SLENG")
sales = Department(name="SliceSales", code="SLSALES")
db.add_all([eng, sales])
db.commit()
db.refresh(eng)
db.refresh(sales)

ent = LegalEntity(name="Slice Entity", code="SLENT", country="US")
db.add(ent)
db.commit()
db.refresh(ent)

loc = Location(name="Slice Site", code="SLLOC", country="US")
db.add(loc)
db.commit()
db.refresh(loc)

jeng = Job(title="Slice Eng Role", code="SLJENG", department_id=eng.id)
jsales = Job(title="Slice Sales Role", code="SLJSALES", department_id=sales.id)
db.add_all([jeng, jsales])
db.commit()
db.refresh(jeng)
db.refresh(jsales)

# The location filter resolves through positions: SliceEng holds a position
# at Slice Site, SliceSales holds none.
db.add(Position(code="SLPOS1", title="Eng slot", job_id=jeng.id, department_id=eng.id, location_id=loc.id))
db.commit()


def mk_emp(code, first, dept, job, hire, status="Active", termination=None, manager_id=None, entity_id=None):
    e = Employee(
        employee_id=code, first_name=first, last_name="Slicer",
        email=f"{code.lower()}@example.com", hire_date=hire,
        job_id=job.id, department_id=dept.id, manager_id=manager_id,
        status=status, termination_date=termination,
        legal_entity_id=entity_id, salary=50000,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


mgr = mk_emp("SL-MGR", "Moe", eng, jeng, date(2024, 6, 1))
rep_a = mk_emp("SL-A", "Ann", eng, jeng, date(2026, 2, 10), manager_id=mgr.id)
rep_b = mk_emp("SL-B", "Ben", sales, jsales, date(2025, 5, 1), status="Terminated",
               termination=date(2026, 3, 15), manager_id=mgr.id)
outsider = mk_emp("SL-OUT", "Oli", sales, jsales, date(2026, 4, 1), entity_id=ent.id)
oldtimer = mk_emp("SL-OLD", "Otto", eng, jeng, date(2023, 1, 1), status="Terminated",
                  termination=date(2025, 12, 31))

# Identifiers for the masking checks: a PAN HR may read and PayrollViewer
# may not, plus a masked Aadhaar display both roles may see.
outsider.pan_number = "ABCDE1234F"
outsider.aadhaar_masked = "****-****-4321"
outsider.aadhaar_last4 = "4321"
db.commit()

# One stored pay run + slip. The gross is deliberately distinctive: no rule
# pack would ever compute 876543.21, so the response echoing it proves the
# endpoint read the stored row rather than recalculating.
period = PayrollPeriod(name="Slice 2026-05", start_date=date(2026, 5, 1),
                       end_date=date(2026, 5, 31), pay_date=date(2026, 5, 15))
db.add(period)
db.commit()
db.refresh(period)
run = PayRun(period_id=period.id, jurisdiction="US", rule_pack_id="test-only",
             status="Finalized", currency="USD",
             total_gross=876543.21, total_net=700000.00, total_deductions=176543.21,
             headcount=1)
db.add(run)
db.commit()
db.refresh(run)
db.add(PaySlip(pay_run_id=run.id, employee_id=outsider.id,
               gross_pay=876543.21, net_pay=700000.00, total_deductions=176543.21,
               currency="USD", status="Paid"))
db.commit()


def mk_user(username, role, employee_id=None):
    db.add(User(username=username, email=f"{username}@example.com",
                hashed_password=get_password_hash("SlicePass12345"),
                role=role, is_active=True, employee_id=employee_id))
    db.commit()


mk_user("sl_hr", "HR")
mk_user("sl_pay", "PayrollViewer")
mk_user("sl_mgr", "Manager", mgr.id)
mk_user("sl_assoc", "Associate", rep_a.id)
# HR is an MFA-enforced role: the account-state gate refuses unenrolled
# HR accounts before any endpoint logic runs. Enroll the fixture account
# the way a real HR account is enrolled — no grace period, no bypass.
sl_hr_row = db.query(User).filter(User.username == "sl_hr").first()
sl_hr_row.mfa_enabled = True
db.commit()
SALES_ID = sales.id
ENT_ID = ent.id
LOC_ID = loc.id
db.close()

client = TestClient(app, raise_server_exceptions=False)

RESULTS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name, ok, detail=""):
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def tok(username):
    r = client.post("/api/v1/auth/login",
                    json={"username": username, "password": "SlicePass12345"})
    return r.json().get("access_token", "")


HR = {"Authorization": f"Bearer {tok('sl_hr')}"}
PAY = {"Authorization": f"Bearer {tok('sl_pay')}"}
MGR = {"Authorization": f"Bearer {tok('sl_mgr')}"}
ASSOC = {"Authorization": f"Bearer {tok('sl_assoc')}"}
RANGE = {"from": "2026-01-01", "to": "2026-12-31"}

print("=" * 66)
print("REPORTS SLICE: joiners / leavers / attrition / payroll-summary")
print("=" * 66)

# --- Joiners -------------------------------------------------------------
r = client.get("/api/v1/reports/joiners", headers=HR, params=RANGE)
body = r.json()
codes = {row["employee_id"] for row in body.get("rows", [])}
check("joiners 200 with count", r.status_code == 200 and body.get("count") == 2,
      f"got {r.status_code} {body}")
check("joiners are hires in range only", codes == {"SL-A", "SL-OUT"}, f"got {codes}")

r = client.get("/api/v1/reports/joiners", headers=HR,
               params={"from": "2026-03-01", "to": "2026-12-31"})
codes = {row["employee_id"] for row in r.json().get("rows", [])}
check("joiners from/to narrows the range", codes == {"SL-OUT"}, f"got {codes}")

r = client.get("/api/v1/reports/joiners", headers=HR,
               params={**RANGE, "department_id": SALES_ID})
codes = {row["employee_id"] for row in r.json().get("rows", [])}
check("joiners department filter", codes == {"SL-OUT"}, f"got {codes}")

r = client.get("/api/v1/reports/joiners", headers=HR, params={**RANGE, "entity_id": ENT_ID})
codes = {row["employee_id"] for row in r.json().get("rows", [])}
check("joiners entity filter", codes == {"SL-OUT"}, f"got {codes}")

r = client.get("/api/v1/reports/joiners", headers=HR, params={**RANGE, "location_id": LOC_ID})
codes = {row["employee_id"] for row in r.json().get("rows", [])}
check("joiners location filter via positions", codes == {"SL-A"}, f"got {codes}")

# --- Leavers -------------------------------------------------------------
r = client.get("/api/v1/reports/leavers", headers=HR, params=RANGE)
body = r.json()
codes = {row["employee_id"] for row in body.get("rows", [])}
check("leavers are terminations in range only", codes == {"SL-B"}, f"got {codes}")
check("leavers carry termination_date",
      body["rows"] and body["rows"][0]["termination_date"] == "2026-03-15",
      f"got {body}")

# --- Attrition -----------------------------------------------------------
r = client.get("/api/v1/reports/attrition", headers=HR, params={"year": 2026})
body = r.json()
check("attrition 200 for 2026", r.status_code == 200 and body.get("year") == 2026,
      f"got {r.status_code} {body}")
# Jan 1 headcount: SL-MGR + SL-B = 2. Dec 31: SL-MGR + SL-A + SL-OUT = 3.
# leavers = 1 -> 1 / 2.5 * 100 = 40.0
check("attrition counts", body.get("joiners") == 2 and body.get("leavers") == 1,
      f"got {body}")
check("attrition pct", body.get("attrition_pct") == 40.0, f"got {body}")
check("attrition states its definition", bool(body.get("definition")), f"got {body}")

# --- Visibility: manager sees the team, associate sees nothing -----------
r = client.get("/api/v1/reports/joiners", headers=MGR, params=RANGE)
codes = {row["employee_id"] for row in r.json().get("rows", [])}
check("manager joiners scoped to reporting line", codes == {"SL-A"}, f"got {codes}")

r = client.get("/api/v1/reports/leavers", headers=MGR, params=RANGE)
codes = {row["employee_id"] for row in r.json().get("rows", [])}
check("manager leavers scoped to reporting line", codes == {"SL-B"}, f"got {codes}")

for path, params in (("/api/v1/reports/joiners", RANGE),
                     ("/api/v1/reports/leavers", RANGE),
                     ("/api/v1/reports/attrition", {"year": 2026}),
                     ("/api/v1/reports/payroll-summary", RANGE)):
    r = client.get(path, headers=ASSOC, params=params)
    check(f"associate 403 on {path}", r.status_code == 403, f"got {r.status_code}")

r = client.get("/api/v1/reports/payroll-summary", headers=MGR, params=RANGE)
check("manager 403 on payroll-summary (HR figures, not team figures)",
      r.status_code == 403, f"got {r.status_code}")

# --- Validation: 422s -----------------------------------------------------
r = client.get("/api/v1/reports/joiners", headers=HR,
               params={"from": "not-a-date", "to": "2026-12-31"})
check("joiners bad from date is 422", r.status_code == 422, f"got {r.status_code}")

r = client.get("/api/v1/reports/leavers", headers=HR,
               params={"from": "2026-12-31", "to": "2026-01-01"})
check("leavers from>to is 422", r.status_code == 422, f"got {r.status_code}")

r = client.get("/api/v1/reports/attrition", headers=HR, params={"year": 1800})
check("attrition bad year is 422", r.status_code == 422, f"got {r.status_code}")

r = client.get("/api/v1/reports/joiners", headers=HR, params={**RANGE, "format": "pdf"})
check("joiners bad format is 422", r.status_code == 422, f"got {r.status_code}")

# --- Payroll summary: stored rows only, masked ---------------------------
r = client.get("/api/v1/reports/payroll-summary", headers=HR, params=RANGE)
body = r.json()
check("payroll-summary 200 with one stored slip",
      r.status_code == 200 and body.get("count") == 1, f"got {r.status_code} {body}")
row = (body.get("rows") or [{}])[0]
check("payroll-summary echoes the stored gross verbatim",
      row.get("gross") == "876543.21", f"got {row}")
check("payroll-summary shows PAN to HR", row.get("pan_number") == "ABCDE1234F",
      f"got {row}")

r = client.get("/api/v1/reports/payroll-summary", headers=PAY, params=RANGE)
prow = (r.json().get("rows") or [{}])[0]
check("payroll-summary masks PAN for PayrollViewer",
      prow.get("pan_number") is None, f"got {prow}")
check("payroll-summary keeps masked aadhaar for PayrollViewer",
      prow.get("aadhaar") == "****-****-4321", f"got {prow}")
check("payroll-summary still shows figures to PayrollViewer",
      prow.get("gross") == "876543.21", f"got {prow}")

r = client.get("/api/v1/reports/payroll-summary", headers=HR,
               params={"from": "2026-06-01", "to": "2026-12-31"})
check("payroll-summary from/to scopes by pay date",
      r.json().get("count") == 0, f"got {r.json()}")

# --- Exports: CSV/XLSX content, masking, audit ---------------------------
r = client.get("/api/v1/reports/joiners", headers=HR, params={**RANGE, "format": "csv"})
check("joiners CSV downloads", r.status_code == 200 and "text/csv" in r.headers.get("content-type", ""),
      f"got {r.status_code} {r.headers.get('content-type')}")
check("joiners CSV has header + fixture rows",
      "employee_id" in r.text and "SL-A" in r.text, f"got {r.text[:200]!r}")

r = client.get("/api/v1/reports/payroll-summary", headers=PAY,
               params={**RANGE, "format": "xlsx"})
ct = r.headers.get("content-type", "")
check("payroll XLSX downloads", r.status_code == 200 and "spreadsheetml" in ct,
      f"got {r.status_code} {ct}")
check("payroll XLSX is a zip package", r.content[:2] == b"PK", f"got {r.content[:2]!r}")
sheet = zipfile.ZipFile(io.BytesIO(r.content)).read("xl/worksheets/sheet1.xml").decode()
check("payroll XLSX carries masked aadhaar", "****-****-4321" in sheet, f"got {sheet[:200]!r}")
check("payroll XLSX never carries raw PAN", "ABCDE1234F" not in sheet, "raw PAN leaked")

session = SessionLocal()
exported = session.query(AuditLog).filter(
    AuditLog.action == "export",
    AuditLog.entity_type.in_(["report_joiners", "report_payroll_summary"]),
).all()
session.close()
check("CSV/XLSX exports are audit-logged", len(exported) >= 2,
      f"got {len(exported)} export rows")

print()
print("=" * 66)
print(f"==== REPORTS SLICE SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 66)
raise SystemExit(1 if RESULTS["fail"] else 0)
