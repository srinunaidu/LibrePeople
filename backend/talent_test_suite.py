"""Talent surface: performance, learning, succession (LP-TAL-001..006).

What this suite proves
----------------------
The performance and learning endpoints the CSV rows LP-TAL-001..006 point at.
Before this suite those rows carried "no dedicated performance/learning-
endpoint suite":

* TAL-001/002: goals list under the caller's scope; a manager may create a
  goal for a direct report (and update it) but a stranger's record answers
  404 and an associate is refused with 403;
* TAL-003/004: reviews create/list/update, and finalising stamps Finalized;
  feedback may be filed and is read back per review (unknown review: 404);
* TAL-003 (calibration/compensation): compensation bands and merit cycles
  with allocations are admin-only reads and writes;
* TAL-004/005: the course catalogue lists for every role but only an admin
  may add a course; mandatory-course flags survive the round trip;
* TAL-005/006: certifications record issue/expiry; enrolments create, list
  scoped to self for associates, and complete with an optional score;
* TAL-006 (optional talent stays optional): talent pools and succession
  plans serve managers, write only for admins, and refuse associates;
* anonymous callers are refused with 401 everywhere probed.

Run:  python talent_test_suite.py
"""
from __future__ import annotations

import os
import tempfile
from datetime import date

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="talent_test_"), "talent_test.db")

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
from app.models.core_hr import Position  # noqa: E402
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
GOALS = "/api/v1/performance/goals"
REVIEWS = "/api/v1/performance/reviews"
FEEDBACK = "/api/v1/performance/feedback"
BANDS = "/api/v1/performance/compensation-bands"
CYCLES = "/api/v1/performance/merit-cycles"
ALLOCATIONS = "/api/v1/performance/merit-allocations"
COURSES = "/api/v1/learning/courses"
COURSE_ENROLL = "/api/v1/learning/course-enrollments"
CERTS = "/api/v1/learning/certifications"
POOLS = "/api/v1/learning/talent-pools"
POOL_MEMBERS = "/api/v1/learning/talent-pool-members"
SUCCESSION = "/api/v1/learning/succession-plans"
PASSWORD = "TalentPass123"

print("=" * 68)
print("TALENT SUITE (LP-TAL-001..006)")
print("=" * 68)

# --- fixtures ---------------------------------------------------------------
dept = Department(name="Talent", code="TAL")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Talent Analyst", code="TAL-JOB", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)

mgr = Employee(
    employee_id="TAL-MGR", first_name="Mara", last_name="Manager",
    email="mara.talent@example.com", hire_date=date(2024, 3, 1),
    job_id=job.id, department_id=dept.id,
    status="Active", employment_type="Full-time",
)
db.add(mgr)
db.commit()
db.refresh(mgr)
member = Employee(
    employee_id="TAL-001", first_name="Theo", last_name="Member",
    email="theo.talent@example.com", hire_date=date(2025, 2, 3),
    job_id=job.id, department_id=dept.id, manager_id=mgr.id,
    status="Active", employment_type="Full-time",
)
outsider = Employee(
    employee_id="TAL-002", first_name="Uma", last_name="Outsider",
    email="uma.talent@example.com", hire_date=date(2025, 2, 3),
    job_id=job.id, department_id=dept.id,
    status="Active", employment_type="Full-time",
)
db.add_all([member, outsider])
db.commit()
db.refresh(member)
db.refresh(outsider)

position = Position(code="TAL-POS-1", title="Talent Lead",
                    job_id=job.id, department_id=dept.id)
db.add(position)
db.commit()
db.refresh(position)

for username in ("tal_admin", "tal_mgr", "tal_assoc"):
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.delete(existing)
db.commit()
db.add(User(
    username="tal_admin", email="tal_admin@example.com",
    hashed_password=get_password_hash(PASSWORD),
    role="SuperAdmin", is_active=True, mfa_enabled=True,
))
db.add(User(
    username="tal_mgr", email="tal_mgr@example.com",
    hashed_password=get_password_hash(PASSWORD),
    role="Manager", employee_id=mgr.id, is_active=True,
))
db.add(User(
    username="tal_assoc", email="tal_assoc@example.com",
    hashed_password=get_password_hash(PASSWORD),
    role="Associate", employee_id=member.id, is_active=True,
))
db.commit()


def login(username: str) -> dict:
    response = client.post(LOGIN, json={"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.text[:200]
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


ADMIN = login("tal_admin")
MGR = login("tal_mgr")
ASSOC = login("tal_assoc")
check("the admin, manager and associate accounts can sign in", True)


def audit_count(action: str) -> int:
    with SessionLocal() as session:
        return session.query(AuditLog).filter(AuditLog.action == action).count()


# ====[ TAL-001/002 — goals ]==================================================
print("\n[TAL-001/002] goals: scoped reads, manager writes for direct reports")
response = client.get(GOALS, headers=MGR)
check("TAL-001 goals list (empty at first)",
      response.status_code == 200 and response.json() == [], response.text[:160])

response = client.post(GOALS, headers=MGR, json={
    "employee_id": member.id, "title": "Ship onboarding revamp",
    "description": "Lead the Q1 revamp", "weight": 40, "status": "Not Started",
})
check("TAL-002 a manager may create a goal for a direct report",
      response.status_code == 201
      and response.json().get("employee_id") == member.id,
      response.text[:160])
goal_id = response.json().get("id")

response = client.get(GOALS, headers=MGR, params={"employee_id": member.id})
check("TAL-001 the goal reads back scoped to the employee",
      response.status_code == 200
      and any(g.get("id") == goal_id for g in response.json()),
      response.text[:160])

response = client.post(GOALS, headers=MGR, json={
    "employee_id": outsider.id, "title": "Not my report",
})
check("TAL-002 a manager may not create a goal for a stranger",
      response.status_code == 404, response.text[:160])

response = client.post(GOALS, headers=ASSOC, json={
    "employee_id": member.id, "title": "Self goal",
})
check("TAL-002 an associate may not create a goal",
      response.status_code == 403, response.text[:160])

response = client.put(GOALS + f"/{goal_id}", headers=MGR, json={
    "progress": 50, "status": "In Progress",
})
check("TAL-002 a manager may update the goal",
      response.status_code == 200 and response.json().get("progress") == 50,
      response.text[:160])

response = client.put(GOALS + "/999999", headers=MGR, json={"progress": 10})
check("TAL-002 updating an unknown goal is 404",
      response.status_code == 404, response.text[:160])

response = client.get(GOALS)
check("TAL-001 an unauthenticated caller may not list goals",
      response.status_code == 401, response.text[:160])

check("TAL-002 creating a goal writes its audit row",
      audit_count("create_goal") >= 1, "no audit row")

# ====[ TAL-003/004 — reviews and feedback ]===================================
print("\n[TAL-003/004] reviews: create, update, finalize; peer feedback")
response = client.get(REVIEWS, headers=MGR)
check("TAL-003 reviews list (empty at first)",
      response.status_code == 200 and response.json() == [], response.text[:160])

response = client.post(REVIEWS, headers=MGR, json={
    "employee_id": member.id, "period": "2025-H2", "status": "Draft",
})
check("TAL-004 a manager may create a review",
      response.status_code == 201
      and response.json().get("period") == "2025-H2",
      response.text[:160])
review_id = response.json().get("id")

response = client.post(REVIEWS, headers=ASSOC, json={
    "employee_id": member.id, "period": "2025-H2",
})
check("TAL-004 an associate may not create a review",
      response.status_code == 403, response.text[:160])

response = client.put(REVIEWS + f"/{review_id}", headers=MGR, json={
    "overall_rating": 4.5, "manager_comments": "Strong quarter",
})
check("TAL-003 a manager may rate the review",
      response.status_code == 200 and response.json().get("overall_rating") == 4.5,
      response.text[:160])

response = client.post(FEEDBACK, headers=ASSOC, json={
    "review_id": review_id, "from_employee_id": member.id,
    "feedback_type": "Peer", "rating": 4.0, "comments": "Great partner",
})
check("TAL-003 peer feedback may be filed on the review",
      response.status_code == 201, response.text[:160])

response = client.get(FEEDBACK, headers=MGR, params={"review_id": review_id})
check("TAL-003 feedback reads back per review",
      response.status_code == 200 and len(response.json()) == 1,
      response.text[:160])

response = client.get(FEEDBACK, headers=MGR, params={"review_id": 999999})
check("TAL-003 feedback for an unknown review is 404",
      response.status_code == 404, response.text[:160])

response = client.post(REVIEWS + f"/{review_id}/finalize", headers=MGR)
body = response.json() if response.status_code == 200 else {}
check("TAL-003 finalising stamps the review Finalized",
      response.status_code == 200
      and body.get("status") == "Finalized" and body.get("finalized_at") is not None,
      response.text[:160])

response = client.post(REVIEWS + "/999999/finalize", headers=MGR)
check("TAL-003 finalising an unknown review is 404",
      response.status_code == 404, response.text[:160])

# ====[ TAL-003 — calibration and compensation ]===============================
print("\n[TAL-003] compensation bands and merit cycles stay admin-only")
response = client.get(BANDS, headers=ADMIN)
check("TAL-003 compensation bands list (empty at first)",
      response.status_code == 200 and response.json() == [], response.text[:160])

response = client.post(BANDS, headers=ADMIN, json={
    "job_id": job.id, "level": "L3",
    "min_salary": 400000, "mid_salary": 550000, "max_salary": 700000,
})
check("TAL-003 an admin may create a compensation band",
      response.status_code == 201, response.text[:160])

response = client.get(BANDS, headers=ASSOC)
check("TAL-003 an associate may not read compensation bands",
      response.status_code == 403, response.text[:160])

response = client.post(CYCLES, headers=ADMIN, json={
    "name": "FY26 merit", "year": 2026, "budget_percent": 8,
    "start_date": "2026-04-01", "end_date": "2026-05-31",
})
check("TAL-003 an admin may open a merit cycle",
      response.status_code == 201, response.text[:160])
cycle_id = response.json().get("id")

response = client.post(ALLOCATIONS, headers=ADMIN, json={
    "cycle_id": cycle_id, "employee_id": member.id,
    "current_salary": 500000, "proposed_salary": 540000, "increase_percent": 8,
})
check("TAL-003 an admin may record a merit allocation",
      response.status_code == 201, response.text[:160])

response = client.get(ALLOCATIONS, headers=ADMIN, params={"cycle_id": cycle_id})
check("TAL-003 allocations read back per cycle",
      response.status_code == 200 and len(response.json()) == 1,
      response.text[:160])

response = client.get(CYCLES, headers=MGR)
check("TAL-003 a manager may not read merit cycles",
      response.status_code == 403, response.text[:160])

# ====[ TAL-004/005 — the learning catalogue ]=================================
print("\n[TAL-004/005] courses: open catalogue, admin-only writes")
response = client.get(COURSES, headers=ASSOC)
check("TAL-005 the course catalogue lists for every role (empty at first)",
      response.status_code == 200 and response.json() == [], response.text[:160])

response = client.post(COURSES, headers=ADMIN, json={
    "title": "POSH Refresher", "code": "POSH-2025", "category": "Compliance",
    "duration_hours": 2, "is_mandatory": True,
})
check("TAL-004 an admin may add a course",
      response.status_code == 201
      and response.json().get("is_mandatory") is True,
      response.text[:160])
course_id = response.json().get("id")

response = client.get(COURSES, headers=ASSOC)
check("TAL-005 the catalogue holds the new course",
      response.status_code == 200
      and any(c.get("code") == "POSH-2025" for c in response.json()),
      response.text[:160])

response = client.post(COURSES, headers=MGR, json={
    "title": "Sneaky course", "code": "SNEAKY",
})
check("TAL-004 a manager may not add a course",
      response.status_code == 403, response.text[:160])

response = client.get(COURSES)
check("TAL-005 an unauthenticated caller may not read the catalogue",
      response.status_code == 401, response.text[:160])

# ====[ TAL-005/006 — certifications and enrollments ]=========================
print("\n[TAL-005/006] certifications, enrollments, completion")
response = client.post(CERTS, headers=ASSOC, json={
    "employee_id": member.id, "name": "First Aid",
    "issuer": "Red Cross", "issued_date": "2025-01-15",
    "expiry_date": "2027-01-15",
})
check("TAL-005 an associate may record their own certification",
      response.status_code == 201, response.text[:160])

response = client.get(CERTS, headers=ASSOC)
body = response.json() if response.status_code == 200 else []
check("TAL-005 certifications read back scoped to self",
      response.status_code == 200
      and body and all(c.get("employee_id") == member.id for c in body),
      response.text[:160])

response = client.get(COURSE_ENROLL, headers=ASSOC)
check("TAL-006 enrollments list (empty at first)",
      response.status_code == 200 and response.json() == [], response.text[:160])

response = client.post(COURSE_ENROLL, headers=ASSOC, json={
    "employee_id": member.id, "course_id": course_id,
})
check("TAL-006 an associate may enrol themselves",
      response.status_code == 201, response.text[:160])
enrollment_id = response.json().get("id")

response = client.put(COURSE_ENROLL + f"/{enrollment_id}/complete",
                      headers=ASSOC, params={"score": 92})
body = response.json() if response.status_code == 200 else {}
check("TAL-006 completing stamps the enrollment with the score",
      response.status_code == 200
      and body.get("status") == "Completed" and body.get("score") == 92,
      response.text[:160])

response = client.put(COURSE_ENROLL + "/999999/complete", headers=ASSOC)
check("TAL-006 completing an unknown enrollment is 404",
      response.status_code == 404, response.text[:160])

# ====[ TAL-006 — optional talent stays optional ]=============================
print("\n[TAL-006] talent pools and succession do not gate core flows")
response = client.post(POOLS, headers=ADMIN, json={
    "name": "Future leads", "description": "High-potential bench",
})
check("TAL-006 an admin may open a talent pool",
      response.status_code == 201, response.text[:160])
pool_id = response.json().get("id")

response = client.get(POOLS, headers=MGR)
check("TAL-006 a manager may read talent pools",
      response.status_code == 200
      and any(p.get("id") == pool_id for p in response.json()),
      response.text[:160])

response = client.get(POOLS, headers=ASSOC)
check("TAL-006 an associate may not read talent pools",
      response.status_code == 403, response.text[:160])

response = client.post(POOL_MEMBERS, headers=ADMIN, json={
    "pool_id": pool_id, "employee_id": member.id, "readiness": "Ready now",
})
check("TAL-006 an admin may bench a successor",
      response.status_code == 201, response.text[:160])

response = client.get(SUCCESSION, headers=MGR)
check("TAL-006 succession plans list for managers (empty at first)",
      response.status_code == 200 and response.json() == [], response.text[:160])

response = client.post(SUCCESSION, headers=ADMIN, json={
    "position_id": position.id, "primary_successor_id": member.id,
    "readiness": "Ready in 1 year",
})
check("TAL-006 an admin may name a successor for a position",
      response.status_code == 201, response.text[:160])

response = client.get(SUCCESSION, headers=ASSOC)
check("TAL-006 an associate may not read succession plans",
      response.status_code == 403, response.text[:160])

check("TAL-001..006 talent writes are audited",
      audit_count("create_goal") >= 1 and audit_count("create_course") >= 1
      and audit_count("create_course_enrollment") >= 1,
      "missing audit row")

# ===========================================================================
print()
print("=" * 68)
print(f"TALENT SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
print("=" * 68)
if FAILURES:
    print("\nfailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
    raise SystemExit(1)
