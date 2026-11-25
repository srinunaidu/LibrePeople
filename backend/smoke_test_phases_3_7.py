"""Local smoke test for Phases 3-7 using SQLite (no Oracle needed).

Covers: Time & Attendance, Scheduling/Rostering, Leave, Offboarding, Reports.
"""
import os
import tempfile
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.mkdtemp(prefix="smoke_p37_"), "smoke_p37.db"
)
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = "*"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
admin = db.query(User).filter(User.username == "admin").first()
if not admin:
    admin = User(
        username="admin",
        email="admin@k.local",
        hashed_password=get_password_hash("secret123"),
        role="SuperAdmin",
        is_active=True,
        mfa_enabled=True,
    )
    db.add(admin)
    db.commit()
db.close()

client = TestClient(app)
PASS, FAIL = 0, 0


def check(name, ok, extra=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS  {name} {extra}")
    else:
        FAIL += 1
        print(f"FAIL  {name} {extra}")


def login(username="admin", password="secret123"):
    r = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    return r.json().get("access_token", "")


token = login()
H = {"Authorization": f"Bearer {token}"}

# --- fixtures: department, job, employee, employee-linked user --------------- #
r = client.post("/api/v1/departments/", json={"name": "Ops", "code": "OPS"}, headers=H)
check("create department", r.status_code == 201, str(r.status_code))
dept_id = r.json()["id"]

r = client.post(
    "/api/v1/jobs/",
    json={"title": "Associate", "code": "ASSOC", "department_id": dept_id,
          "min_salary": 20000, "max_salary": 40000},
    headers=H,
)
check("create job", r.status_code == 201, str(r.status_code))
job_id = r.json()["id"]

today = date.today().isoformat()
r = client.post(
    "/api/v1/employees/",
    json={"employee_id": "EMP100", "first_name": "Priya", "last_name": "Sharma",
          "email": "priya@example.com", "hire_date": today,
          "job_id": job_id, "department_id": dept_id, "status": "Active",
          "salary": 30000},
    headers=H,
)
check("create employee", r.status_code == 201, str(r.status_code))
emp = r.json()
emp_id = emp["id"]

db = SessionLocal()
link_user = User(
    username="priya", email="priya@k.local",
    hashed_password=get_password_hash("secret123"),
    role="Associate", is_active=True, employee_id=emp_id,
)
db.add(link_user)
db.commit()
db.close()
token2 = login("priya")
H2 = {"Authorization": f"Bearer {token2}"}
check("employee-linked login", bool(token2))

# --- Phase 3: Time & Attendance -------------------------------------------- #
r = client.post("/api/v1/time/clock-in",
                json={"employee_id": emp_id, "source": "Web"}, headers=H2)
check("3. clock-in", r.status_code == 201, str(r.status_code))
entry_id = r.json()["id"]

r = client.post("/api/v1/time/clock-in",
                json={"employee_id": emp_id}, headers=H2)
check("3. duplicate clock-in rejected", r.status_code == 400, str(r.status_code))

r = client.post("/api/v1/time/clock-out", json={"employee_id": emp_id}, headers=H2)
check("3. clock-out", r.status_code == 201, str(r.status_code))
check("3. hours computed", r.json().get("worked_hours", 0) >= 0)

r = client.get(f"/api/v1/time/entries?employee_id={emp_id}", headers=H)
check("3. list entries", r.status_code == 200 and len(r.json()) >= 1, f"n={len(r.json())}")

start = date.today().replace(day=1).isoformat()
end = (date.today() + timedelta(days=28)).isoformat()
r = client.post("/api/v1/time/timesheets/generate",
                json={"employee_id": emp_id, "period_start": start, "period_end": end},
                headers=H)
check("3. generate timesheet", r.status_code == 201, str(r.status_code))
ts_id = r.json()["id"]

r = client.post(f"/api/v1/time/timesheets/{ts_id}/submit", headers=H)
check("3. submit timesheet", r.status_code == 200 and r.json()["status"] == "Submitted")

r = client.post(f"/api/v1/time/timesheets/{ts_id}/approve", headers=H)
check("3. approve timesheet", r.status_code == 200 and r.json()["status"] == "Approved")

# --- Phase 4: Scheduling --------------------------------------------------- #
r = client.post("/api/v1/scheduling/shift-templates",
                json={"name": "Day Shift", "code": "DAY", "start_time": "09:00",
                      "end_time": "17:00", "break_minutes": 60},
                headers=H)
check("4. create shift template", r.status_code == 201, str(r.status_code))
tmpl_id = r.json()["id"]

r = client.post("/api/v1/scheduling/roster/generate",
                json={"employee_id": emp_id, "start_date": start, "end_date": end,
                      "shift_template_id": tmpl_id},
                headers=H)
check("4. generate roster", r.status_code == 201 and len(r.json()) > 0, f"n={len(r.json())}")
roster_id = r.json()[0]["id"] if r.status_code == 201 else None

r = client.post("/api/v1/scheduling/swaps",
                json={"roster_entry_id": roster_id}, headers=H2)
check("4. request shift swap", r.status_code == 201, str(r.status_code))
swap_id = r.json().get("id")

r = client.post(f"/api/v1/scheduling/swaps/{swap_id}/approve", headers=H)
check("4. approve swap", r.status_code == 200 and r.json()["status"] == "Approved")

# --- Phase 5: Leave -------------------------------------------------------- #
r = client.post("/api/v1/leave/types",
                json={"name": "Annual Leave", "code": "AL", "is_paid": True,
                      "max_days_per_year": 18},
                headers=H)
check("5. create leave type", r.status_code == 201, str(r.status_code))
lt_id = r.json()["id"]

r = client.post("/api/v1/leave/entitlements",
                json={"entitlement_year": date.today().year, "leave_type_id": lt_id},
                headers=H)
check("5. assign entitlements", r.status_code == 201, str(r.status_code))

r = client.get(f"/api/v1/leave/balances?employee_id={emp_id}", headers=H)
check("5. balances", r.status_code == 200 and len(r.json()) == 1, f"n={len(r.json())}")
check("5. balance entitled", r.json()[0]["entitled_days"] == 18)

s = (date.today() + timedelta(days=7)).isoformat()
e = (date.today() + timedelta(days=8)).isoformat()
expected_days = sum(
    1
    for i in range((date.fromisoformat(e) - date.fromisoformat(s)).days + 1)
    if (date.fromisoformat(s) + timedelta(days=i)).weekday() < 5
)
r = client.post("/api/v1/leave/requests",
                json={"employee_id": emp_id, "leave_type_id": lt_id,
                      "start_date": s, "end_date": e, "reason": "Trip"},
                headers=H2)
check("5. create leave request", r.status_code == 201, str(r.status_code))
req_id = r.json()["id"]
check("5. working days", r.json()["working_days"] == expected_days,
      f"wd={r.json()['working_days']} expected={expected_days}")

r = client.post(f"/api/v1/leave/requests/{req_id}/approve", headers=H)
check("5. approve leave", r.status_code == 200 and r.json()["status"] == "Approved")

r = client.get(f"/api/v1/leave/balances?employee_id={emp_id}", headers=H)
check("5. used days updated", r.json()[0]["used_days"] == expected_days)

# --- Phase 6: Offboarding -------------------------------------------------- #
r = client.post("/api/v1/offboarding/terminations",
                json={"employee_id": emp_id,
                      "last_working_date": (date.today() + timedelta(days=30)).isoformat(),
                      "termination_type": "Resignation", "reason": "New opportunity"},
                headers=H)
check("6. start termination", r.status_code == 201, str(r.status_code))
term = r.json()
term_id = term["id"]
check("6. default checklist", len(term.get("items", [])) >= 5, f"items={len(term.get('items', []))}")

item_id = term["items"][0]["id"]
r = client.put(f"/api/v1/offboarding/items/{item_id}",
               json={"status": "Completed"}, headers=H)
check("6. complete item", r.status_code == 200 and r.json()["status"] == "Completed")

r = client.get(f"/api/v1/offboarding/terminations/{term_id}/progress", headers=H)
check("6. progress", r.status_code == 200 and r.json()["completed"] >= 1)

r = client.post(f"/api/v1/offboarding/terminations/{term_id}/complete", headers=H)
check("6. complete termination", r.status_code == 200 and r.json()["status"] == "Completed")

r = client.get(f"/api/v1/employees/{emp_id}", headers=H)
check("6. employee marked Terminated", r.json()["status"] == "Terminated")

# --- Phase 7: Reports ------------------------------------------------------- #
for path in ["dashboard", "headcount", "leave", "labor-cost", "attendance"]:
    r = client.get(f"/api/v1/reports/{path}", headers=H)
    check(f"7. report {path}", r.status_code == 200, str(r.status_code))

r = client.get("/api/v1/reports/dashboard", headers=H)
check("7. dashboard employees", r.json()["employees"]["total"] == 1)
check("7. dashboard pending leave", r.json()["approvals"]["pending_leave"] == 0)

r = client.get("/api/v1/reports/audit?limit=200", headers=H)
check("7. audit trail", r.status_code == 200 and len(r.json()) > 5, f"n={len(r.json())}")

# --- RBAC ------------------------------------------------------------------ #
r = client.post("/api/v1/departments/", json={"name": "X", "code": "X"}, headers=H2)
check("RBAC: associate cannot create", r.status_code == 403, str(r.status_code))

print(f"\n==== {PASS} passed, {FAIL} failed ====")
raise SystemExit(1 if FAIL else 0)
