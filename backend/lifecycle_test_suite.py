"""Employee lifecycle benefits surface (LP-LIFE-001..009).

What this suite proves
----------------------
The benefits endpoints (plans, enrollments, life events, leaves of absence)
are the lifecycle record the CSV rows LP-LIFE-001..009 point at. Before this
suite those rows carried "no dedicated benefits-endpoint suite":

* LIFE-001/002: the plan catalogue lists for every role and only an admin
  may create a plan (Associate is refused with 403, anonymous with 401);
* LIFE-003/004: enrollments list under the caller's visibility scope (an
  associate sees only their own rows) and only an admin may enrol;
* LIFE-005/006: life events list/create; an associate may file their own
  event but a stranger's record answers 404;
* LIFE-007/008: leaves of absence list/create with the same scope rule;
* LIFE-009: approving a leave of absence marks it Approved with the
  approver recorded, refuses an unknown id with 404 and refuses a
  non-admin with 403;
* every mutating call writes its audit row.

Run:  python lifecycle_test_suite.py
"""
from __future__ import annotations

import os
import tempfile
from datetime import date

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="lifecycle_test_"), "lifecycle_test.db")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
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


LOGIN = "/api/v1/auth/login"
PLANS = "/api/v1/benefits/benefit-plans"
ENROLLMENTS = "/api/v1/benefits/benefit-enrollments"
LIFE_EVENTS = "/api/v1/benefits/life-events"
LOA = "/api/v1/benefits/leaves-of-absence"
PASSWORD = "LifecyclePass123"

print("=" * 68)
print("LIFECYCLE SUITE (LP-LIFE-001..009)")
print("=" * 68)

# --- fixtures ---------------------------------------------------------------
dept = Department(name="Lifecycle", code="LIFE")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Lifecycle Analyst", code="LIFE-JOB", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)

member = Employee(
    employee_id="LIFE-001", first_name="Lena", last_name="Member",
    email="lena.lifecycle@example.com", hire_date=date(2025, 6, 2),
    job_id=job.id, department_id=dept.id,
    status="Active", employment_type="Full-time",
)
outsider = Employee(
    employee_id="LIFE-002", first_name="Omar", last_name="Outsider",
    email="omar.lifecycle@example.com", hire_date=date(2025, 6, 2),
    job_id=job.id, department_id=dept.id,
    status="Active", employment_type="Full-time",
)
db.add_all([member, outsider])
db.commit()
db.refresh(member)
db.refresh(outsider)

for username in ("life_admin", "life_assoc"):
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.delete(existing)
db.commit()
db.add(User(
    username="life_admin", email="life_admin@example.com",
    hashed_password=get_password_hash(PASSWORD),
    role="SuperAdmin", is_active=True, mfa_enabled=True,
))
db.add(User(
    username="life_assoc", email="life_assoc@example.com",
    hashed_password=get_password_hash(PASSWORD),
    role="Associate", employee_id=member.id, is_active=True,
))
db.commit()


def login(username: str) -> dict:
    response = client.post(LOGIN, json={"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.text[:200]
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


ADMIN = login("life_admin")
ASSOC = login("life_assoc")
check("the admin and associate accounts can sign in", True)


def audit_count(action: str) -> int:
    with SessionLocal() as session:
        return session.query(AuditLog).filter(AuditLog.action == action).count()


# ====[ LIFE-001/002 — the plan catalogue ]====================================
print("\n[LIFE-001/002] benefit plans: list for all, create for admins")
response = client.get(PLANS, headers=ADMIN)
check("LIFE-001 the plan catalogue lists (empty at first)",
      response.status_code == 200 and response.json() == [], response.text[:160])

response = client.post(PLANS, headers=ADMIN, json={
    "name": "Health Plus", "code": "HEALTH-PLUS", "plan_type": "Health",
    "provider": "Acme Care", "employer_contribution": 5000, "employee_contribution": 1500,
})
check("LIFE-002 an admin may create a benefit plan",
      response.status_code == 201 and response.json().get("code") == "HEALTH-PLUS",
      response.text[:160])
plan_id = response.json().get("id")

response = client.get(PLANS, headers=ADMIN)
check("LIFE-001 the catalogue holds the created plan",
      response.status_code == 200
      and any(p.get("code") == "HEALTH-PLUS" for p in response.json()),
      response.text[:160])

response = client.get(PLANS, headers=ASSOC)
check("LIFE-001 an associate may read the catalogue",
      response.status_code == 200, response.text[:160])

response = client.post(PLANS, headers=ASSOC, json={
    "name": "Sneaky", "code": "SNEAKY", "plan_type": "Health",
})
payload = response.json() if response.content else {}
check("LIFE-002 an associate may not create a plan",
      response.status_code == 403
      and (payload.get("error") or {}).get("code") == "forbidden",
      response.text[:160])

response = client.post(PLANS, json={"name": "Anon", "code": "ANON", "plan_type": "Health"})
check("LIFE-002 an unauthenticated caller may not create a plan",
      response.status_code == 401, response.text[:160])

response = client.get(PLANS)
check("LIFE-001 an unauthenticated caller may not read the catalogue",
      response.status_code == 401, response.text[:160])

response = client.post(PLANS, headers=ADMIN, json={
    "name": "Health Plus again", "code": "HEALTH-PLUS", "plan_type": "Health",
})
check("LIFE-002 a duplicate plan code is refused",
      response.status_code != 201, response.text[:160])

check("LIFE-002 creating a plan writes its audit row",
      audit_count("create_benefit_plan") >= 1, "no audit row")

# ====[ LIFE-003/004 — enrollments ]===========================================
print("\n[LIFE-003/004] enrollments: scoped reads, admin writes")
response = client.get(ENROLLMENTS, headers=ADMIN)
check("LIFE-003 enrollments list (empty at first)",
      response.status_code == 200 and response.json() == [], response.text[:160])

response = client.post(ENROLLMENTS, headers=ADMIN, json={
    "employee_id": member.id, "plan_id": plan_id, "effective_date": "2025-07-01",
})
check("LIFE-004 an admin may enrol an employee",
      response.status_code == 201
      and response.json().get("employee_id") == member.id,
      response.text[:160])

response = client.get(ENROLLMENTS, headers=ASSOC)
body = response.json() if response.status_code == 200 else []
check("LIFE-003 an associate sees only their own enrollment",
      response.status_code == 200
      and len(body) == 1 and body[0].get("employee_id") == member.id,
      response.text[:160])

response = client.get(ENROLLMENTS, headers=ASSOC, params={"employee_id": outsider.id})
check("LIFE-003 an associate may not scope the list to a stranger",
      response.status_code in (403, 404), response.text[:160])

response = client.post(ENROLLMENTS, headers=ASSOC, json={
    "employee_id": member.id, "plan_id": plan_id, "effective_date": "2025-08-01",
})
check("LIFE-004 an associate may not enrol",
      response.status_code == 403, response.text[:160])

check("LIFE-004 enrolling writes its audit row",
      audit_count("create_benefit_enrollment") >= 1, "no audit row")

# ====[ LIFE-005/006 — life events ]===========================================
print("\n[LIFE-005/006] life events: file your own, not a stranger's")
response = client.get(LIFE_EVENTS, headers=ADMIN)
check("LIFE-005 life events list (empty at first)",
      response.status_code == 200 and response.json() == [], response.text[:160])

response = client.post(LIFE_EVENTS, headers=ASSOC, json={
    "employee_id": member.id, "event_type": "Marriage", "event_date": "2025-09-14",
})
check("LIFE-006 an associate may file their own life event",
      response.status_code == 201
      and response.json().get("event_type") == "Marriage",
      response.text[:160])

response = client.post(LIFE_EVENTS, headers=ASSOC, json={
    "employee_id": outsider.id, "event_type": "Birth", "event_date": "2025-09-14",
})
check("LIFE-006 an associate may not file a stranger's life event",
      response.status_code == 404, response.text[:160])

response = client.get(LIFE_EVENTS, headers=ASSOC)
body = response.json() if response.status_code == 200 else []
check("LIFE-005 an associate sees only their own life events",
      response.status_code == 200
      and body and all(e.get("employee_id") == member.id for e in body),
      response.text[:160])

check("LIFE-006 filing a life event writes its audit row",
      audit_count("create_life_event") >= 1, "no audit row")

# ====[ LIFE-007/008/009 — leaves of absence ]=================================
print("\n[LIFE-007/008/009] leaves of absence: request, then approve")
response = client.get(LOA, headers=ADMIN)
check("LIFE-007 leaves of absence list (empty at first)",
      response.status_code == 200 and response.json() == [], response.text[:160])

response = client.post(LOA, headers=ASSOC, json={
    "employee_id": member.id, "leave_type": "Parental",
    "start_date": "2025-10-01", "end_date": "2025-12-31",
})
check("LIFE-008 an associate may request their own leave of absence",
      response.status_code == 201
      and response.json().get("status") == "Pending",
      response.text[:160])
loa_id = response.json().get("id")

response = client.put(f"{LOA}/{loa_id}/approve", headers=ASSOC)
check("LIFE-009 an associate may not approve a leave of absence",
      response.status_code == 403, response.text[:160])

response = client.put(f"{LOA}/{loa_id}/approve", headers=ADMIN)
body = response.json() if response.status_code == 200 else {}
check("LIFE-009 an admin may approve a leave of absence",
      response.status_code == 200
      and body.get("status") == "Approved" and body.get("approved_by") is not None,
      response.text[:160])

response = client.put(f"{LOA}/999999/approve", headers=ADMIN)
check("LIFE-009 approving an unknown leave of absence is 404",
      response.status_code == 404, response.text[:160])

response = client.get(LOA, headers=ASSOC)
body = response.json() if response.status_code == 200 else []
check("LIFE-007 an associate sees only their own leaves of absence",
      response.status_code == 200
      and body and all(e.get("employee_id") == member.id for e in body),
      response.text[:160])

check("LIFE-008/009 requesting and approving write audit rows",
      audit_count("create_leave_of_absence") >= 1
      and audit_count("approve_leave_of_absence") >= 1,
      "missing audit row")

# ===========================================================================
print()
print("=" * 68)
print(f"LIFECYCLE SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
print("=" * 68)
if FAILURES:
    print("\nfailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
    raise SystemExit(1)
