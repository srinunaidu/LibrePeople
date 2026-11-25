"""Master data: the reference entities can be edited, archived and guarded.

What this suite proves
----------------------
Departments, jobs, locations, positions and cost centres were creatable and
readable and nothing else. This suite pins the operations that were added and
the rules they have to hold:

* **Edit** changes only the fields that were sent, and refuses a code another
  row already owns (`409 duplicate_natural_key`), and a reference that does not
  exist (`422 reference_not_found`);
* **Archive** is `is_active: false`, and an archived record disappears from the
  list a form offers while staying reachable to the maintenance list that has
  to be able to restore it;
* **Delete** is refused with `409 reference_in_use`, and the refusal names what
  points at the row and how many — nothing is written when it is refused;
* **Delete** succeeds when nothing points at the row;
* a job whose minimum exceeds its maximum is refused as a payload error;
* a position may not report to itself, and its `fte` stays within 0…1;
* every write is audited, and `Associate` cannot perform any of these.

Run:  python master_data_test_suite.py
"""
import datetime
import os
import shutil
import tempfile

DB_PATH = os.path.join(
    tempfile.mkdtemp(prefix="master_data_test_suite_"), "master_data_test_suite.db"
)
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"  # keep the suite's output readable

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.core_hr import CostCenter, Location, Position  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)

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


# --- the fixtures ------------------------------------------------------------

PASSWORD = "MasterDataPass123"

session = SessionLocal()


def _user(username: str, role: str) -> User:
    """Create the caller directly: this suite is about master data, not auth."""
    existing = session.query(User).filter(User.username == username).first()
    if existing:
        return existing
    person = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash(PASSWORD),
        role=role,
        is_active=True,
        mfa_enabled=role in ("SuperAdmin", "HR"),
    )
    session.add(person)
    session.commit()
    session.refresh(person)
    return person


admin = _user("md-admin", "SuperAdmin")
associate = _user("md-associate", "Associate")


def login(username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


ADMIN = login(admin.username)
ASSOCIATE = login(associate.username)

# The seed a department + job every employee needs.
dept_row = Department(name="Operations", code="OPSMD", is_active=True)
session.add(dept_row)
session.commit()
session.refresh(dept_row)

job_row = Job(
    title="Operations Analyst",
    code="OPS-AN",
    department_id=dept_row.id,
    min_salary=40000,
    max_salary=60000,
    is_active=True,
)
session.add(job_row)
session.commit()
session.refresh(job_row)


def employee(code: str, **overrides) -> Employee:
    person = Employee(
        employee_id=code,
        first_name="Master",
        last_name=code,
        email=f"{code.lower()}@example.com",
        hire_date=datetime.date(2024, 1, 1),
        job_id=overrides.pop("job_id", job_row.id),
        department_id=overrides.pop("department_id", dept_row.id),
        status="Active",
        **overrides,
    )
    session.add(person)
    session.commit()
    session.refresh(person)
    return person


# One employee, so the guards that refuse a deletion have something that
# really points at the row — a department is held by its jobs *and* by the
# people in them.
emp = employee("MD-EMP-1")


# ===========================================================================
print()
print("Departments — edit, archive, restore and the deletion guard")
print("-" * 68)

created = client.post(
    "/api/v1/departments/",
    headers=ADMIN,
    json={"name": "Customer Operations", "code": "CSOPS", "description": "Calls"},
)
check("a department is created", created.status_code == 201, created.text)
dept = created.json()

patched = client.patch(
    f"/api/v1/departments/{dept['id']}", headers=ADMIN, json={"description": "Inbound"}
)
check(
    "a partial edit changes only the field that was sent",
    patched.status_code == 200
    and patched.json()["description"] == "Inbound"
    and patched.json()["name"] == "Customer Operations",
    patched.text,
)

duplicate = client.post(
    "/api/v1/departments/",
    headers=ADMIN,
    json={"name": "Another", "code": "csops"},
)
check(
    "a code another department owns, differing only in case, is refused",
    duplicate.status_code == 409
    and duplicate.json()["error"]["code"] == "duplicate_natural_key",
    duplicate.text,
)

archived = client.patch(
    f"/api/v1/departments/{dept['id']}", headers=ADMIN, json={"is_active": False}
)
check("a department is archived", archived.json()["is_active"] is False, archived.text)

offered = client.get("/api/v1/departments/", headers=ADMIN).json()
check(
    "an archived department is not offered to a form",
    all(d["id"] != dept["id"] for d in offered),
    str([d["code"] for d in offered]),
)
maintenance = client.get(
    "/api/v1/departments/", headers=ADMIN, params={"include_inactive": True}
).json()
check(
    "and the maintenance list can still see it, so it can be restored",
    any(d["id"] == dept["id"] for d in maintenance),
    str([d["code"] for d in maintenance]),
)

restored = client.patch(
    f"/api/v1/departments/{dept['id']}", headers=ADMIN, json={"is_active": True}
)
check("a department is restored", restored.json()["is_active"] is True, restored.text)

forbidden_delete = client.delete(f"/api/v1/departments/{dept_row.id}", headers=ADMIN)
check(
    "a department employees belong to cannot be deleted",
    forbidden_delete.status_code == 409
    and forbidden_delete.json()["error"]["code"] == "reference_in_use",
    forbidden_delete.text,
)
check(
    "and the refusal names every kind of row that points at it",
    {"employees", "jobs"}
    <= {
        d["entity"]
        for d in forbidden_delete.json()["error"]["details"]["dependents"]
    },
    forbidden_delete.text,
)

empty = client.post(
    "/api/v1/departments/", headers=ADMIN, json={"name": "Empty", "code": "EMPTY"}
).json()
deleted = client.delete(f"/api/v1/departments/{empty['id']}", headers=ADMIN)
check(
    "a department nothing points at is deleted",
    deleted.status_code == 204
    and session.query(Department).filter(Department.id == empty["id"]).first() is None,
    deleted.text,
)

cleared = client.patch(
    f"/api/v1/departments/{dept['id']}", headers=ADMIN, json={"name": None}
)
check(
    "an explicit null for a required column is refused before it is written",
    cleared.status_code == 422
    and cleared.json()["error"]["code"] == "validation_error"
    and cleared.json()["error"]["details"]["fields"] == ["name"],
    cleared.text,
)

forbidden = client.patch(
    f"/api/v1/departments/{dept['id']}", headers=ASSOCIATE, json={"name": "Nope"}
)
check("an Associate cannot edit a department", forbidden.status_code == 403, forbidden.text)

# ===========================================================================
print()
print("Jobs — edit, the salary band, and the deletion guard")
print("-" * 68)

created_job = client.post(
    "/api/v1/jobs/",
    headers=ADMIN,
    json={
        "title": "Support Engineer",
        "code": "SUP-EN",
        "department_id": dept_row.id,
        "min_salary": 30000,
        "max_salary": 45000,
    },
)
check("a job is created", created_job.status_code == 201, created_job.text)
job = created_job.json()

bad_band = client.patch(
    f"/api/v1/jobs/{job['id']}", headers=ADMIN, json={"min_salary": 90000}
)
check(
    "a band whose minimum exceeds its maximum is refused",
    bad_band.status_code == 422,
    bad_band.text,
)

missing_ref = client.post(
    "/api/v1/jobs/",
    headers=ADMIN,
    json={"title": "Ghost", "code": "GHOST", "department_id": 999999},
)
check(
    "a department that does not exist is refused as reference_not_found",
    missing_ref.status_code == 422
    and missing_ref.json()["error"]["code"] == "reference_not_found",
    missing_ref.text,
)

moved = client.patch(
    f"/api/v1/jobs/{job['id']}", headers=ADMIN, json={"department_id": dept_row.id}
)
check("a job is edited", moved.status_code == 200, moved.text)

# A second person holds the job that is about to be tested for deletion, so
# the refusal has a real employee to name.
holder = employee("MD-EMP-2", job_id=job["id"])
held = client.delete(f"/api/v1/jobs/{job['id']}", headers=ADMIN)
check(
    "a job an employee holds cannot be deleted",
    held.status_code == 409
    and any(
        d["entity"] == "employees"
        for d in held.json()["error"]["details"]["dependents"]
    ),
    held.text,
)
check(
    "and the employee is still there — nothing was written",
    session.query(Employee).filter(Employee.id == holder.id).first() is not None,
    "the employee vanished",
)

loose_job = client.post(
    "/api/v1/jobs/",
    headers=ADMIN,
    json={"title": "Unused", "code": "UNUSED", "department_id": dept_row.id},
).json()
check(
    "a job nothing holds is deleted",
    client.delete(f"/api/v1/jobs/{loose_job['id']}", headers=ADMIN).status_code == 204,
    "delete failed",
)

# ===========================================================================
print()
print("Locations, cost centres and positions")
print("-" * 68)

created_loc = client.post(
    "/api/v1/core-hr/locations",
    headers=ADMIN,
    json={"name": "Bengaluru", "code": "BLR", "city": "Bengaluru", "country": "India"},
)
check("a location is created", created_loc.status_code == 201, created_loc.text)
loc = created_loc.json()

check(
    "a location is read by id",
    client.get(
        f"/api/v1/core-hr/locations/{loc['id']}", headers=ADMIN
    ).json()["code"]
    == "BLR",
    "read failed",
)

edited_loc = client.patch(
    f"/api/v1/core-hr/locations/{loc['id']}", headers=ADMIN, json={"city": "Bengaluru North"}
)
check(
    "a location is edited",
    edited_loc.json()["city"] == "Bengaluru North",
    edited_loc.text,
)

duplicate_loc = client.post(
    "/api/v1/core-hr/locations", headers=ADMIN, json={"name": "Dup", "code": "BLR"}
)
check(
    "a duplicate location code is refused",
    duplicate_loc.status_code == 409,
    duplicate_loc.text,
)

created_cc = client.post(
    "/api/v1/core-hr/cost-centers",
    headers=ADMIN,
    json={"code": "CC-MD", "name": "Support", "department_id": dept_row.id},
)
check("a cost centre is created", created_cc.status_code == 201, created_cc.text)
cc = created_cc.json()

bad_cc = client.patch(
    f"/api/v1/core-hr/cost-centers/{cc['id']}",
    headers=ADMIN,
    json={"department_id": 999999},
)
check(
    "a cost centre cannot point at a department that does not exist",
    bad_cc.status_code == 422
    and bad_cc.json()["error"]["code"] == "reference_not_found",
    bad_cc.text,
)

created_pos = client.post(
    "/api/v1/core-hr/positions",
    headers=ADMIN,
    json={
        "code": "POS-MD",
        "title": "Support Engineer I",
        "job_id": job_row.id,
        "department_id": dept_row.id,
        "location_id": loc["id"],
        "fte": 1.0,
    },
)
check("a position is created", created_pos.status_code == 201, created_pos.text)
pos = created_pos.json()

bad_fte = client.patch(
    f"/api/v1/core-hr/positions/{pos['id']}", headers=ADMIN, json={"fte": 1.5}
)
check("an fte above one is refused", bad_fte.status_code == 422, bad_fte.text)

cleared_fte = client.patch(
    f"/api/v1/core-hr/positions/{pos['id']}", headers=ADMIN, json={"fte": None}
)
check(
    "an explicit null fte is refused, not stored",
    cleared_fte.status_code == 422
    and cleared_fte.json()["error"]["code"] == "validation_error",
    cleared_fte.text,
)

self_report = client.patch(
    f"/api/v1/core-hr/positions/{pos['id']}",
    headers=ADMIN,
    json={"reports_to_position_id": pos["id"]},
)
check(
    "a position may not report to itself",
    self_report.status_code == 422,
    self_report.text,
)

child_pos = client.post(
    "/api/v1/core-hr/positions",
    headers=ADMIN,
    json={
        "code": "POS-MD-2",
        "title": "Support Engineer II",
        "job_id": job_row.id,
        "department_id": dept_row.id,
        "reports_to_position_id": pos["id"],
    },
).json()

held_loc = client.delete(f"/api/v1/core-hr/locations/{loc['id']}", headers=ADMIN)
check(
    "a location a position sits at cannot be deleted",
    held_loc.status_code == 409
    and any(
        d["entity"] == "positions"
        for d in held_loc.json()["error"]["details"]["dependents"]
    ),
    held_loc.text,
)

held_pos = client.delete(f"/api/v1/core-hr/positions/{pos['id']}", headers=ADMIN)
check(
    "a position another position reports to cannot be deleted",
    held_pos.status_code == 409
    and any(
        d["entity"] == "positions"
        for d in held_pos.json()["error"]["details"]["dependents"]
    ),
    held_pos.text,
)

freed_child = client.delete(
    f"/api/v1/core-hr/positions/{child_pos['id']}", headers=ADMIN
)
check(
    "the child position is deleted once nothing reports to it",
    freed_child.status_code == 204,
    freed_child.text,
)

forbidden_pos = client.post(
    "/api/v1/core-hr/positions",
    headers=ASSOCIATE,
    json={"code": "POS-X", "title": "X", "job_id": job_row.id, "department_id": dept_row.id},
)
check("an Associate cannot create a position", forbidden_pos.status_code == 403, forbidden_pos.text)

# ===========================================================================
print()
print("Auditability")
print("-" * 68)

audit_rows = (
    session.query(AuditLog)
    .filter(AuditLog.entity_type == "Department")
    .filter(AuditLog.action.in_(["create_department", "update_department", "delete_department"]))
    .all()
)
check(
    "every department write is audited",
    {"create_department", "update_department", "delete_department"}
    <= {row.action for row in audit_rows},
    str([row.action for row in audit_rows]),
)
check(
    "and the audit row is attributable to the caller",
    all(row.actor_name == admin.username for row in audit_rows),
    str({row.actor_name for row in audit_rows}),
)

print()
print("=" * 68)
print(f"MASTER DATA SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
shutil.rmtree(os.path.dirname(DB_PATH), ignore_errors=True)
raise SystemExit(1 if RESULTS["fail"] else 0)
