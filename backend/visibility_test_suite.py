"""Data-visibility and audit-coverage regression suite.

Companion to `security_test_suite.py`. The enterprise audit found that role
checks gated *administrative actions* but not *data reads*: a lowest-privilege
Associate could read the whole employee directory, colleagues' leave and
termination records, offers, and the audit trail. These checks assert the
scoped behaviour and guard against it regressing.

Run:  python visibility_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="visibility_test_"), "visibility_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"

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
dept = Department(name="Ops", code="VOPS")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Analyst", code="VANALYST", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def mk_emp(code: str, first: str, last: str, manager_id: int | None = None) -> Employee:
    e = (
        db.query(Employee)
        .filter(Employee.employee_id == code)
        .first()
    )
    if not e:
        e = Employee(
            employee_id=code,
            first_name=first,
            last_name=last,
            email=f"{code.lower()}@example.com",
            hire_date=datetime.date(2024, 1, 1),
            job_id=job.id,
            department_id=dept.id,
            manager_id=manager_id,
            status="Active",
        )
        db.add(e)
        db.commit()
        db.refresh(e)
    return e


# Reporting structure:
#   manager (VP)
#     |- report_a  (IC)
#     |- report_b  (IC)
#     |     |- report_c (grandchild, 2 levels down)
manager_emp = mk_emp("V-MGR", "Mia", "Manager")
a_emp = mk_emp("V-A", "Ann", "Alpha", manager_emp.id)
b_emp = mk_emp("V-B", "Ben", "Beta", manager_emp.id)
c_emp = mk_emp("V-C", "Cara", "Gamma", b_emp.id)  # 2 levels below manager
outsider = mk_emp("V-OUT", "Oli", "Outsider")  # unrelated

IDS = {
    "mgr": manager_emp.id,
    "a": a_emp.id,
    "b": b_emp.id,
    "c": c_emp.id,
    "out": outsider.id,
}


def mk_user(username: str, role: str, employee_id: int | None):
    db.add(
        User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash("VisPass12345"),
            role=role,
            is_active=True,
            mfa_enabled=role in ("SuperAdmin", "HR"),
            employee_id=employee_id,
        )
    )
    db.commit()


mk_user("v_admin", "SuperAdmin", None)
mk_user("v_hr", "HR", None)
mk_user("v_pay", "PayrollViewer", None)
mk_user("v_manager", "Manager", manager_emp.id)
mk_user("v_assoc", "Associate", a_emp.id)
mk_user("v_orphan", "Associate", None)  # no linked employee
DEPT_ID = dept.id
db.close()

client = TestClient(app)

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


def tok(username: str) -> str:
    r = client.post(
        "/api/v1/auth/login", json={"username": username, "password": "VisPass12345"}
    )
    return r.json().get("access_token", "")


def H(username: str) -> dict:
    return {"Authorization": f"Bearer {tok(username)}"}


def emp_ids_for(username: str):
    r = client.get("/api/v1/employees?page=1&page_size=200", headers=H(username))
    if r.status_code != 200:
        return None, r.status_code
    return {e["id"] for e in r.json()["items"]}, r.status_code


print("=" * 66)
print("DATA VISIBILITY SCOPING")
print("=" * 66)

# --- Employee directory ---------------------------------------------------
ids, _ = emp_ids_for("v_hr")
check("HR sees the full directory", ids == set(IDS.values()), f"got {ids}")

ids, _ = emp_ids_for("v_pay")
check(
    "PayrollViewer sees the full directory (needed to run payroll)",
    ids == set(IDS.values()),
    f"got {ids}",
)

ids, _ = emp_ids_for("v_manager")
check(
    "Manager sees self + transitive reports (3 levels)",
    ids == {IDS["mgr"], IDS["a"], IDS["b"], IDS["c"]},
    f"got {ids} expected {sorted({IDS['mgr'], IDS['a'], IDS['b'], IDS['c']})}",
)

ids, _ = emp_ids_for("v_assoc")
check(
    "Associate sees only themselves",
    ids == {IDS["a"]},
    f"got {ids}",
)

ids, status = emp_ids_for("v_orphan")
check(
    "unprivileged user with no employee link sees nothing (fails closed)",
    ids == set(),
    f"got {ids}",
)

# --- Single-record access -------------------------------------------------
r = client.get(f"/api/v1/employees/{IDS['out']}", headers=H("v_assoc"))
check(
    "Associate cannot read a colleague's record by id",
    r.status_code == 404,
    f"got {r.status_code}",
)

r = client.get(f"/api/v1/employees/{IDS['a']}", headers=H("v_assoc"))
check("Associate can read their own record", r.status_code == 200, f"got {r.status_code}")

r = client.get(f"/api/v1/employees/{IDS['out']}", headers=H("v_manager"))
check("Manager cannot read an unrelated employee", r.status_code == 404, f"got {r.status_code}")

r = client.get(f"/api/v1/employees/{IDS['c']}", headers=H("v_manager"))
check("Manager can read a grandchild report", r.status_code == 200, f"got {r.status_code}")

r = client.get(f"/api/v1/employees/{IDS['out']}", headers=H("v_hr"))
check("HR can read any employee", r.status_code == 200, f"got {r.status_code}")

# --- Leave ----------------------------------------------------------------
HRH = H("v_hr")
lt = client.post(
    "/api/v1/leave/types",
    headers=HRH,
    json={"name": "Annual", "code": "VANN", "default_days": 20, "is_paid": True},
)
lt_id = lt.json()["id"] if lt.status_code in (200, 201) else None

if lt_id:
    for eid in (IDS["a"], IDS["out"]):
        client.post(
            "/api/v1/leave/entitlements",
            headers=HRH,
            json={"leave_type_id": lt_id, "entitlement_year": 2026},
        )
    # create requests for two different employees
    for label, eid in (("a", IDS["a"]), ("out", IDS["out"])):
        client.post(
            "/api/v1/leave/requests",
            headers=HRH,
            json={
                "employee_id": eid,
                "leave_type_id": lt_id,
                "start_date": "2026-06-01",
                "end_date": "2026-06-02",
                "reason": f"private reason for {label}",
            },
        )

    r = client.get("/api/v1/leave/requests", headers=H("v_assoc"))
    check("Associate sees only their own leave requests", r.status_code == 200)
    if r.status_code == 200:
        reasons = [x.get("reason") for x in r.json()]
        check(
            "Associate cannot see a colleague's leave reason",
            "private reason for out" not in reasons and "private reason for a" in reasons,
            f"got {reasons}",
        )

    r = client.get("/api/v1/leave/requests", headers=HRH)
    check(
        "HR sees all leave requests",
        r.status_code == 200 and len(r.json()) >= 2,
        f"got {len(r.json()) if r.status_code == 200 else r.status_code}",
    )

    r = client.get("/api/v1/leave/balances?year=2026", headers=H("v_assoc"))
    check(
        "Associate sees only their own leave balances",
        r.status_code == 200 and all(b["employee_id"] == IDS["a"] for b in r.json()),
        f"got {[b['employee_id'] for b in r.json()] if r.status_code == 200 else r.status_code}",
    )
else:
    check("leave type created for visibility checks", False, f"status={lt.status_code}")

# --- Terminations ---------------------------------------------------------
for eid in (IDS["a"], IDS["out"]):
    client.post(
        "/api/v1/offboarding/terminations",
        headers=HRH,
        json={"employee_id": eid, "last_working_date": "2026-07-01", "reason": "confidential"},
    )
r = client.get("/api/v1/offboarding/terminations", headers=H("v_assoc"))
check(
    "Associate sees only their own terminations",
    r.status_code == 200 and all(t["employee_id"] == IDS["a"] for t in r.json()),
    f"got {[t['employee_id'] for t in r.json()] if r.status_code == 200 else r.status_code}",
)
r = client.get("/api/v1/offboarding/terminations", headers=HRH)
check(
    "HR sees all terminations",
    r.status_code == 200 and len(r.json()) >= 2,
    f"got {len(r.json()) if r.status_code == 200 else r.status_code}",
)

# --- Recruiting pipeline --------------------------------------------------
r = client.get("/api/v1/candidates", headers=H("v_assoc"))
check("Associate cannot list candidates", r.status_code == 403, f"got {r.status_code}")
r = client.get("/api/v1/offers", headers=H("v_assoc"))
check("Associate cannot list offers (contains salary)", r.status_code == 403, f"got {r.status_code}")
r = client.get("/api/v1/applications", headers=H("v_assoc"))
check("Associate cannot list applications", r.status_code == 403, f"got {r.status_code}")
r = client.get("/api/v1/candidates", headers=HRH)
check("HR can list candidates", r.status_code == 200, f"got {r.status_code}")

# --- Audit trail ----------------------------------------------------------
r = client.get("/api/v1/reports/audit", headers=H("v_assoc"))
check("Associate cannot read the audit trail", r.status_code == 403, f"got {r.status_code}")
r = client.get("/api/v1/reports/audit", headers=H("v_manager"))
check("Manager cannot read the audit trail", r.status_code == 403, f"got {r.status_code}")
r = client.get("/api/v1/reports/audit", headers=HRH)
check("HR can read the audit trail", r.status_code == 200, f"got {r.status_code}")


print("=" * 66)
print("\n[AUDIT-COVERAGE] High-risk mutations must be traceable (P1-1)")
print("=" * 66)

r = client.get("/api/v1/reports/audit?limit=500", headers=HRH)
entries = r.json() if r.status_code == 200 else []
actions = {e.get("action") for e in entries}

created = client.post(
    "/api/v1/employees",
    headers=HRH,
    json={
        "employee_id": "V-NEW",
        "first_name": "Nia",
        "last_name": "Newly",
        "email": "v-new@example.com",
        "hire_date": "2026-08-01",
        "job_id": 1,
        "department_id": DEPT_ID,
    },
)
check("employee can be created through the API", created.status_code == 201, f"got {created.status_code}: {created.text[:120]}")

entries = client.get("/api/v1/reports/audit?limit=500", headers=HRH).json()
actions = {e.get("action") for e in entries}
check(
    "employee creation is audited",
    "create_employee" in actions,
    f"sample={sorted(a for a in actions if 'employee' in str(a))}",
)

# update an employee and confirm the delta was captured
r = client.put(
    f"/api/v1/employees/{IDS['out']}",
    headers=HRH,
    json={"department_id": DEPT_ID, "status": "On Leave"},
)
check("employee update succeeds", r.status_code == 200, f"got {r.status_code}")
entries = client.get("/api/v1/reports/audit?limit=500", headers=HRH).json()
upd = [e for e in entries if e.get("action") == "update_employee"]
check("employee update is audited", len(upd) >= 1, f"{len(upd)} entries")
if upd:
    detail = upd[-1].get("details") or ""
    check(
        "audit captures before -> after values",
        "->" in detail and "status" in detail,
        f"details={detail!r}",
    )

check(
    "leave type creation is audited",
    "create_leave_type" in actions,
    f"actions={sorted(actions)[:10]}",
)

print()
print("=" * 66)
print(f"==== VISIBILITY SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 66)
raise SystemExit(1 if RESULTS["fail"] else 0)