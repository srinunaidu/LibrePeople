"""Metric definition + correctness suite.

A metric that is computed but not *defined* is how organisations end up with
three different "headcount" numbers. These checks assert both halves:

  * every metric carries a definition with the fields the brief requires
  * every metric computes the value it claims to, from real seeded data

It also pins the reconciliation defect: labor.monthly_cost used to filter on
employee status for the total but not for the department breakdown.

Run:  python metrics_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="metrics_test_"), "metrics_test.db")
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
from app.models.leave import LeaveType, LeaveBalance  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()
TODAY = datetime.date.today()

eng = Department(name="Eng", code="MENG")
sales = Department(name="Sales", code="MSALES")
db.add_all([eng, sales]); db.commit(); db.refresh(eng); db.refresh(sales)
jeng = Job(title="Eng Role", code="MJENG", department_id=eng.id)
jsales = Job(title="Sales Role", code="MJSALES", department_id=sales.id)
db.add_all([jeng, jsales]); db.commit(); db.refresh(jeng); db.refresh(jsales)

def emp(code, dept, job, status, salary):
    e = Employee(employee_id=code, first_name=code, last_name="X",
                 email=f"{code.lower()}@example.com",
                 hire_date=TODAY - datetime.timedelta(days=500),
                 job_id=job.id, department_id=dept.id, status=status, salary=salary)
    db.add(e); db.commit(); db.refresh(e)
    return e

a1 = emp("M-A1", eng, jeng, "Active", 100000.0)
a2 = emp("M-A2", eng, jeng, "On Leave", 120000.0)
s1 = emp("M-S1", sales, jsales, "Active", 80000.0)
gone = emp("M-GONE", eng, jeng, "Terminated", 90000.0)  # must NOT count anywhere

lt = LeaveType(name="Annual", code="MANN", is_paid=True, max_days_per_year=25)
db.add(lt); db.commit(); db.refresh(lt)
# Deliberately create entitlements in TWO years: the old leave_report summed
# them together, which is the defect under test.
for year, entitled, used in ((TODAY.year, 25, 4), (TODAY.year - 1, 20, 19)):
    db.add(LeaveBalance(employee_id=a1.id, leave_type_id=lt.id,
                        entitlement_year=year, entitled_days=entitled,
                        carried_over_days=0, used_days=used))
db.commit()

db.add(User(username="m_admin", email="m_admin@example.com",
            hashed_password=get_password_hash("MetricsPass123"),
            role="SuperAdmin", is_active=True, mfa_enabled=True))
db.add(User(username="m_assoc", email="m_assoc@example.com",
            hashed_password=get_password_hash("MetricsPass123"),
            role="Associate", is_active=True, employee_id=a1.id))
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


def H(u="m_admin"):
    t = client.post("/api/v1/auth/login",
                    json={"username": u, "password": "MetricsPass123"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


print("=" * 68)
print("DEFINITIONS — every metric must be defined")
print("=" * 68)

r = client.get("/api/v1/reports/metrics/catalogue", headers=H())
check("catalogue endpoint works", r.status_code == 200, f"got {r.status_code}")
ms = r.json().get("metrics", [])
check("catalogue is populated", len(ms) >= 10, f"{len(ms)} metrics")

required_fields = ("key", "name", "business_meaning", "calculation", "source",
                   "reporting_period", "refresh_behaviour", "permissions",
                   "limitations")
for m in ms:
    missing = [f for f in required_fields if not m.get(f)]
    check(f"{m['key']} is fully defined", not missing, f"missing {missing}")

r = client.get("/api/v1/reports/metrics/headcount.active", headers=H())
check("metric value is served with its definition", r.status_code == 200
      and r.json().get("definition") is not None, f"got {r.status_code}")
check("metric reports when it was computed", bool(r.json().get("computed_at")))

r = client.get("/api/v1/reports/metrics/no.such.metric", headers=H())
check("unknown metric is 404, not a silent zero", r.status_code == 404, f"got {r.status_code}")

print()
print("=" * 68)
print("CORRECTNESS — values match the seeded data")
print("=" * 68)

r = client.get("/api/v1/reports/metrics/headcount.active", headers=H())
v = r.json()["value"]
check("active headcount = 3 employed (terminated excluded)", v == 3, f"got {v}")

r = client.get("/api/v1/reports/metrics/headcount.terminated", headers=H())
check("terminated headcount = 1", r.json()["value"] == 1, f"got {r.json()['value']}")

r = client.get("/api/v1/reports/metrics/headcount.by_department", headers=H())
rows = r.json()["value"]
eng_row = next(x for x in rows if x["department"] == "Eng")
sales_row = next(x for x in rows if x["department"] == "Sales")
check("Eng headcount = 2 (terminated excluded from the breakdown)",
      eng_row["employees"] == 2, f"got {eng_row['employees']}")
check("Sales headcount = 1", sales_row["employees"] == 1, f"got {sales_row['employees']}")
check("departments with no employees still appear (as 0)",
      len(rows) == 2, str(rows))

print()
print("=" * 68)
print("RECONCILIATION — the labour-cost defect")
print("=" * 68)

r = client.get("/api/v1/reports/metrics/labor.monthly_cost", headers=H())
v = r.json()["value"]
check("monthly cost = 300000 (terminated salary excluded)",
      abs(v["monthly_cost"] - 300000.0) < 0.01, f"got {v['monthly_cost']}")
check("breakdown sums to the total", v["reconciles"] is True, str(v))
check("metric declares its own reconciliation",
      abs(v["breakdown_total"] - v["monthly_cost"]) < 0.01,
      f"{v['breakdown_total']} vs {v['monthly_cost']}")

print()
print("=" * 68)
print("PERIOD SCOPING — the leave year defect")
print("=" * 68)

r = client.get(f"/api/v1/reports/metrics/leave.entitled_days?year={TODAY.year}", headers=H())
v = r.json()["value"]
check("leave entitlement is scoped to ONE year",
      v["entitlement_year"] == TODAY.year and v["entitled_days"] == 25.0, str(v))

r = client.get(f"/api/v1/reports/metrics/leave.entitled_days?year={TODAY.year - 1}", headers=H())
v = r.json()["value"]
check("a different year returns a different figure",
      v["entitled_days"] == 20.0, str(v))

r = client.get(f"/api/v1/reports/metrics/leave.used_days?year={TODAY.year}", headers=H())
check("leave usage is scoped to one year too",
      r.json()["value"]["used_days"] == 4.0, str(r.json()["value"]))

r = client.get("/api/v1/reports/metrics/leave.entitled_days", headers=H())
check("defaults to the current year",
      r.json()["value"]["entitlement_year"] == TODAY.year, str(r.json()["value"]))

print()
print("=" * 68)
print("SUMMARY + ACCESS")
print("=" * 68)

r = client.get("/api/v1/reports/metrics", headers=H())
body = r.json()
check("summary endpoint works", r.status_code == 200, f"got {r.status_code}")
check("summary contains several metrics", len(body.get("metrics", {})) >= 6,
      str(list(body.get("metrics", {}))[:6]))
check("each summary entry carries its definition",
      all(v.get("definition") for v in body["metrics"].values()))

r = client.get("/api/v1/reports/metrics/labor.monthly_cost", headers=H("m_assoc"))
check("Associate cannot read compensation metrics", r.status_code == 403,
      f"got {r.status_code}")

r = client.get("/api/v1/reports/metrics", headers=H("m_assoc"))
body = r.json()
check("Associate summary omits compensation metrics",
      r.status_code == 200 and "labor.monthly_cost" not in body.get("metrics", {}),
      str(list(body.get("metrics", {}))[:8]))
check("Associate summary says what was withheld rather than showing zero",
      "labor.monthly_cost" in body.get("withheld", []), str(body.get("withheld")))

r = client.get("/api/v1/reports/metrics", headers={})
check("unauthenticated access is refused", r.status_code == 401, f"got {r.status_code}")

# Limitations must be honest, not boilerplate.
cat = {m["key"]: m for m in ms}
check(
    "labour cost declares that it is not a payroll figure",
    "not a payroll figure" in cat["labor.monthly_cost"]["business_meaning"].lower(),
    cat["labor.monthly_cost"]["business_meaning"],
)
check(
    "labour cost declares that overtime/benefits are excluded",
    any("overtime" in l.lower() for l in cat["labor.monthly_cost"]["limitations"]),
    str(cat["labor.monthly_cost"]["limitations"]),
)
check(
    "leave usage declares it reads the cached balance",
    any("cached" in l.lower() for l in cat["leave.used_days"]["limitations"]),
    str(cat["leave.used_days"]["limitations"]),
)
check(
    "turnover declares it does not split voluntary/involuntary",
    any("voluntary" in l.lower() for l in cat["turnover.rate"]["limitations"]),
    str(cat["turnover.rate"]["limitations"]),
)
check(
    "overtime declares it does not feed payroll",
    any("not currently fed into payroll" in l.lower()
        for l in cat["attendance.overtime_hours"]["limitations"]),
    str(cat["attendance.overtime_hours"]["limitations"]),
)

print()
print("=" * 68)
print(f"==== METRICS SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for n, d in FAILURES:
        print(f"  - {n}: {d}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)