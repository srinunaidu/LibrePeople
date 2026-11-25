"""Data-quality detection suite.

Each check is exercised by deliberately creating the defect it exists to find.
A check that never fires is indistinguishable from a check that does not work,
so every rule here is proven against real bad data.

Run:  python data_quality_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="data_quality_test_"), "data_quality_test.db")
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

import datetime  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.employee import Employee  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()

d1 = Department(name="Eng", code="DQENG")
d2 = Department(name="Sales", code="DQSALES")
db.add_all([d1, d2]); db.commit(); db.refresh(d1); db.refresh(d2)
job_eng = Job(title="Eng Role", code="DQJENG", department_id=d1.id)
job_sales = Job(title="Sales Role", code="DQSALESJ", department_id=d2.id)
db.add_all([job_eng, job_sales]); db.commit(); db.refresh(job_eng); db.refresh(job_sales)

TODAY = datetime.date.today()

def emp(code, first, last, email, *, dept, job, manager=None, status="Active",
        hire=TODAY - datetime.timedelta(days=400), salary=None, phone=None):
    e = Employee(employee_id=code, first_name=first, last_name=last, email=email,
                 hire_date=hire, job_id=job.id, department_id=dept.id,
                 manager_id=manager, status=status, phone=phone)
    db.add(e); db.commit(); db.refresh(e)
    return e

# --- Deliberate defects ---------------------------------------------------
boss   = emp("DQ-BOSS", "Boss", "Man", "boss@example.com", dept=d1, job=job_eng)
# 1. duplicate email that the UNIQUE constraint does NOT catch (case + whitespace)
emp("DQ-DUP1", "Dup", "One", "Same@Example.com", dept=d1, job=job_eng)
emp("DQ-DUP2", "Dup", "Two", "same@example.com ", dept=d1, job=job_eng)
# 2. missing phone (info)
emp("DQ-NOPHONE", "No", "Phone", "nophone@example.com", dept=d1, job=job_eng)
# 3. future hire date
emp("DQ-FUTURE", "Future", "Hire", "future@example.com", dept=d1, job=job_eng,
    hire=TODAY + datetime.timedelta(days=60))
# 4. department/job mismatch
emp("DQ-MISMATCH", "Mis", "Match", "mismatch@example.com", dept=d1, job=job_sales)
# 5. manager cycle: x manages y, y manages x
x = emp("DQ-CYCX", "Cy", "X", "cycx@example.com", dept=d1, job=job_eng)
y = emp("DQ-CYCY", "Cy", "Y", "cycy@example.com", dept=d1, job=job_eng)
x.manager_id = y.id; y.manager_id = x.id
db.commit()
# 6. active employee with no pay profile, and one with a zero salary
from app.models.payroll import EmployeePayProfile, PayRun, PayrollPeriod, PaySlip
no_profile = emp("DQ-NOPROFILE", "No", "Profile", "noprofile@example.com",
                 dept=d1, job=job_eng)
zero_pay = emp("DQ-ZERO", "Zero", "Pay", "zero@example.com", dept=d1, job=job_eng)
db.add(EmployeePayProfile(employee_id=zero_pay.id, base_salary=0,
                          pay_frequency="Monthly", tax_withholding=0))
db.commit()
# 7. payslip that does not balance
period = PayrollPeriod(name="DQ-P", start_date=TODAY.replace(day=1),
                       end_date=TODAY, pay_date=TODAY)
db.add(period); db.commit(); db.refresh(period)
run = PayRun(period_id=period.id, status="Processing")
db.add(run); db.commit(); db.refresh(run)
db.add(PaySlip(pay_run_id=run.id, employee_id=boss.id,
               gross_pay=1000.00, total_deductions=200.00, net_pay=999.99))
db.commit()
# 8. overdrawn leave balance + balance/requests mismatch
from app.models.leave import LeaveType, LeaveBalance, LeaveRequest
lt = LeaveType(name="Annual DQ", code="DQANN", is_paid=True, max_days_per_year=10)
db.add(lt); db.commit(); db.refresh(lt)
db.add(LeaveBalance(employee_id=no_profile.id, leave_type_id=lt.id,
                    entitlement_year=TODAY.year, entitled_days=5,
                    carried_over_days=0, used_days=12))
db.commit()

db.add(User(username="dq_admin", email="dq_admin@example.com",
            hashed_password=get_password_hash("DqPass12345"),
            role="SuperAdmin", is_active=True, mfa_enabled=True))
db.add(User(username="dq_assoc", email="dq_assoc@example.com",
            hashed_password=get_password_hash("DqPass12345"),
            role="Associate", is_active=True, employee_id=boss.id))
db.commit()
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


def H(u="dq_admin"):
    t = client.post("/api/v1/auth/login",
                    json={"username": u, "password": "DqPass12345"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


r = client.get("/api/v1/data-quality/issues", headers=H())
check("issues endpoint works", r.status_code == 200, f"got {r.status_code}")
body = r.json()
issues = body.get("issues", [])
codes = {i["code"] for i in issues}

print()
print("=" * 68)
print("DETECTION — each rule must fire on real bad data")
print("=" * 68)

expected = {
    "employee.duplicate_email": "critical",
    "employee.future_hire_date": "warning",
    "employee.department_job_mismatch": "warning",
    "employee.manager_cycle": "critical",
    "employee.missing_contact": "info",
    "payroll.active_without_profile": "critical",
    "payroll.zero_salary": "critical",
    "payroll.payslip_arithmetic": "critical",
    "leave.balance_overdrawn": "critical",
    "leave.balance_mismatch": "critical",
}
for code, sev in expected.items():
    check(f"detects {code}", code in codes, f"codes seen: {sorted(codes)}")
    if code in codes:
        found = next(i for i in issues if i["code"] == code)
        check(f"  {code} severity is {sev}", found["severity"] == sev,
              f"got {found['severity']}")

print()
print("=" * 68)
print("REPORT SHAPE — actionable, not just a list")
print("=" * 68)

sample = issues[0]
for field in ("code", "severity", "title", "entity_type", "explanation",
              "source", "owner_role", "recommendation"):
    check(f"issue carries '{field}'", field in sample and sample[field],
          f"missing/empty: {list(sample)}")

owners = {i["owner_role"] for i in issues}
check("issues are assigned to an owner role", len(owners) > 1, str(owners))
check("issues are sorted worst-first",
      issues[0]["severity"] == "critical", issues[0]["severity"])

r = client.get("/api/v1/data-quality/issues?severity=critical", headers=H())
check("severity filter works",
      r.status_code == 200 and all(i["severity"] == "critical" for i in r.json()["issues"]),
      str(r.json())[:160])

r = client.get("/api/v1/data-quality/issues?code=employee.duplicate_email", headers=H())
check("code filter works",
      r.status_code == 200 and len(r.json()["issues"]) == 1, str(r.json())[:160])

r = client.get("/api/v1/data-quality/issues?severity=nonsense", headers=H())
check("invalid severity is rejected", r.status_code == 422, f"got {r.status_code}")

r = client.get("/api/v1/data-quality/issues", headers=H())
check("summary is returned", "summary" in r.json() and "by_severity" in r.json()["summary"],
      str(r.json().get("summary"))[:160])

r = client.get("/api/v1/data-quality/issues?limit=1", headers=H())
check("limit is honoured and truncation is declared",
      len(r.json()["issues"]) == 1 and r.json()["truncated"] is True,
      str(r.json())[:160])

print()
print("=" * 68)
print("SAFETY AND ACCESS")
print("=" * 68)

r = client.get("/api/v1/data-quality/issues")
check("unauthenticated access is refused", r.status_code == 401, f"got {r.status_code}")

r = client.get("/api/v1/data-quality/issues", headers=H("dq_assoc"))
check("Associate cannot read the data-quality report", r.status_code == 403,
      f"got {r.status_code}")

r = client.get("/api/v1/data-quality/checks", headers=H())
check("rule catalogue is exposed", r.status_code == 200 and len(r.json()["checks"]) >= 9,
      str(r.json())[:200])

r = client.post("/api/v1/data-quality/scan", headers=H())
check("scan runs and is audited", r.status_code == 200 and r.json().get("scanned") is True,
      f"got {r.status_code}")
entries = client.get("/api/v1/reports/audit?limit=200", headers=H()).json()
check("the scan is recorded in the audit trail",
      any(e.get("action") == "data_quality_scan" for e in entries))

# Nothing should have been modified by running checks.
db2 = SessionLocal()
try:
    check("running the checks did not modify the overdrawn balance",
          db2.query(LeaveBalance).filter(LeaveBalance.used_days == 12).count() == 1,
          "the balance was altered")
    check("running the checks did not fix the payslip",
          db2.query(PaySlip).filter(PaySlip.net_pay == 999.99).count() == 1,
          "the payslip was altered")
    check("running the checks did not break the manager cycle",
          db2.query(Employee).filter(Employee.employee_id == "DQ-CYCX").one().manager_id
          == db2.query(Employee).filter(Employee.employee_id == "DQ-CYCY").one().id,
          "the cycle was altered")
finally:
    db2.close()

print()
print("=" * 68)
print(f"==== DATA QUALITY SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for n, d in FAILURES:
        print(f"  - {n}: {d}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)