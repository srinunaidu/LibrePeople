"""Legal entities: the employer-of-record master (LP-CORE-003+010).

What this suite proves
----------------------
One installation holds many legal entities, and an employee belongs to at
most one of them:

* **CRUD** — create (explicit and auto-generated `LE-` code), read, patch,
  duplicate code refused (`409 duplicate_natural_key`), unknown reference
  refused (`422 reference_not_found`), and every write audited;
* **Soft-deactivate** — `DELETE` flips `is_active` to false instead of
  removing the row; the entity disappears from the default list, stays
  reachable directly and via `include_inactive=true`, and `PATCH
  is_active: true` restores it;
* **Tenant scope** — a caller sees only their own tenant's entities; another
  tenant's row reads as 404, and creation stamps the request's tenant;
* **Employee link** — an employee can be hired into an entity, moved between
  entities (effective-dated history), cleared back to null, and an unknown
  entity id is refused;
* **Migration 0036** — a fresh database reaches head with the
  `legal_entities` table, the `employees.legal_entity_id` column and both
  indexes; the downgrade removes exactly what the upgrade created.

Run:  python legal_entity_test_suite.py
"""
import datetime
import os
import shutil
import subprocess
import sys
import tempfile

DB_PATH = os.path.join(
    tempfile.mkdtemp(prefix="legal_entity_test_suite_"), "legal_entity_test_suite.db"
)
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"  # keep the suite's output readable

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.core_hr import LegalEntity  # noqa: E402
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

PASSWORD = "LegalEntityPass123"

session = SessionLocal()


def _user(username: str, role: str) -> User:
    """Create the caller directly: this suite is about legal entities, not auth."""
    existing = session.query(User).filter(User.username == username).first()
    if existing:
        return existing
    person = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash(PASSWORD),
        role=role,
        is_active=True,
        # MFA-enforced world: privileged roles are enrolled, otherwise every
        # call below is refused before the handler runs.
        mfa_enabled=role in ("SuperAdmin", "HR"),
    )
    session.add(person)
    session.commit()
    session.refresh(person)
    return person


admin = _user("le-admin", "SuperAdmin")
associate = _user("le-associate", "Associate")


def login(username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def tenant_headers(username: str, tenant: str) -> dict[str, str]:
    token = create_access_token(subject=username, extra_claims={"tenant": tenant})
    return {"Authorization": f"Bearer {token}"}


ADMIN = login(admin.username)
ASSOCIATE = login(associate.username)
TENANT_A = "tenant-le-a"
TENANT_B = "tenant-le-b"
HA = tenant_headers(admin.username, TENANT_A)
HB = tenant_headers(admin.username, TENANT_B)

# The seed a department + job every employee needs.
dept_row = Department(name="Operations", code="OPSLE", is_active=True)
session.add(dept_row)
session.commit()
session.refresh(dept_row)

job_row = Job(
    title="Operations Analyst",
    code="OPS-LE",
    department_id=dept_row.id,
    min_salary=40000,
    max_salary=90000,
)
session.add(job_row)
session.commit()
session.refresh(job_row)

# ===========================================================================
print("=" * 68)
print("LEGAL ENTITY SUITE")
print("=" * 68)

# ===========================================================================
print()
print("CRUD")
print("-" * 68)

created = client.post(
    "/api/v1/core-hr/legal-entities",
    headers=ADMIN,
    json={"code": "LE-ACME", "name": "Acme Pvt Ltd", "country": "IN",
          "registration_number": "CIN-U12345MH2020PTC000001"},
).json()
check("create returns the entity with its code", isinstance(created, dict) and created.get("code") == "LE-ACME", str(created)[:300])

entity_id = created.get("id")

auto = client.post(
    "/api/v1/core-hr/legal-entities",
    headers=ADMIN,
    json={"name": "Auto Code Ltd"},
).json()
check(
    "an omitted code is auto-generated in the LE- household",
    isinstance(auto, dict) and str(auto.get("code", "")).startswith("LE-"),
    str(auto)[:300],
)
auto_id = auto.get("id")

dup = client.post(
    "/api/v1/core-hr/legal-entities",
    headers=ADMIN,
    json={"code": "le-acme", "name": "Acme Duplicate"},
)
check(
    "a duplicate code is refused (case-insensitive)",
    dup.status_code == 409,
    f"got {dup.status_code}: {dup.text[:200]}",
)

listed = client.get("/api/v1/core-hr/legal-entities", headers=ADMIN)
check(
    "the list carries both entities",
    listed.status_code == 200
    and {created.get("code"), auto.get("code")} <= {row["code"] for row in listed.json()},
    f"got {listed.status_code}: {listed.text[:200]}",
)

read = client.get(f"/api/v1/core-hr/legal-entities/{entity_id}", headers=ADMIN)
check(
    "read returns the entity",
    read.status_code == 200 and read.json()["name"] == "Acme Pvt Ltd",
    f"got {read.status_code}: {read.text[:200]}",
)

missing = client.get("/api/v1/core-hr/legal-entities/999999", headers=ADMIN)
check("an unknown entity reads as 404", missing.status_code == 404, f"got {missing.status_code}")

patched = client.patch(
    f"/api/v1/core-hr/legal-entities/{entity_id}",
    headers=ADMIN,
    json={"name": "Acme Private Limited", "country": "IN"},
)
check(
    "patch renames the entity",
    patched.status_code == 200 and patched.json()["name"] == "Acme Private Limited",
    f"got {patched.status_code}: {patched.text[:200]}",
)

clash = client.patch(
    f"/api/v1/core-hr/legal-entities/{auto_id}",
    headers=ADMIN,
    json={"code": "LE-ACME"},
)
check("patch onto a taken code is refused", clash.status_code == 409, f"got {clash.status_code}")

nulled = client.patch(
    f"/api/v1/core-hr/legal-entities/{entity_id}",
    headers=ADMIN,
    json={"name": None},
)
check("an explicit null for the name is refused", nulled.status_code == 422, f"got {nulled.status_code}")

forbidden_create = client.post(
    "/api/v1/core-hr/legal-entities",
    headers=ASSOCIATE,
    json={"code": "LE-X", "name": "Nope Ltd"},
)
check("an Associate cannot create a legal entity", forbidden_create.status_code == 403, forbidden_create.text[:200])

forbidden_patch = client.patch(
    f"/api/v1/core-hr/legal-entities/{entity_id}",
    headers=ASSOCIATE,
    json={"name": "Nope"},
)
check("an Associate cannot edit a legal entity", forbidden_patch.status_code == 403, forbidden_patch.text[:200])

forbidden_delete = client.delete(
    f"/api/v1/core-hr/legal-entities/{entity_id}", headers=ASSOCIATE
)
check("an Associate cannot deactivate a legal entity", forbidden_delete.status_code == 403, forbidden_delete.text[:200])

# ===========================================================================
print()
print("Soft-deactivate")
print("-" * 68)

gone = client.delete(f"/api/v1/core-hr/legal-entities/{auto_id}", headers=ADMIN)
check("deactivate answers 204", gone.status_code == 204, f"got {gone.status_code}: {gone.text[:200]}")

still_there = client.get(f"/api/v1/core-hr/legal-entities/{auto_id}", headers=ADMIN)
check(
    "the deactivated row is still readable, flagged inactive",
    still_there.status_code == 200 and still_there.json()["is_active"] is False,
    f"got {still_there.status_code}: {still_there.text[:200]}",
)

default_list = client.get("/api/v1/core-hr/legal-entities", headers=ADMIN)
check(
    "the deactivated entity leaves the default list",
    default_list.status_code == 200
    and all(row["code"] != auto.get("code") for row in default_list.json()),
    str([row["code"] for row in default_list.json()])[:200],
)

with_inactive = client.get(
    "/api/v1/core-hr/legal-entities", headers=ADMIN, params={"include_inactive": True}
)
check(
    "include_inactive brings it back for maintenance",
    with_inactive.status_code == 200
    and any(row["code"] == auto.get("code") for row in with_inactive.json()),
    f"got {with_inactive.status_code}",
)

restored = client.patch(
    f"/api/v1/core-hr/legal-entities/{auto_id}",
    headers=ADMIN,
    json={"is_active": True},
)
check(
    "patch restores a deactivated entity",
    restored.status_code == 200 and restored.json()["is_active"] is True,
    f"got {restored.status_code}: {restored.text[:200]}",
)

repeat = client.delete(f"/api/v1/core-hr/legal-entities/{entity_id}", headers=ADMIN)
repeat_again = client.delete(f"/api/v1/core-hr/legal-entities/{entity_id}", headers=ADMIN)
check(
    "deactivating twice is a no-op success",
    repeat.status_code == 204 and repeat_again.status_code == 204,
    f"got {repeat.status_code}/{repeat_again.status_code}",
)
# Restore for the employee-link section below.
client.patch(
    f"/api/v1/core-hr/legal-entities/{entity_id}",
    headers=ADMIN,
    json={"is_active": True},
)

# ===========================================================================
print()
print("Tenant scope")
print("-" * 68)

tenant_created = client.post(
    "/api/v1/core-hr/legal-entities",
    headers=HA,
    json={"code": "LE-TA", "name": "Tenant A Ltd"},
)
check("tenant A creates its entity", tenant_created.status_code == 201, tenant_created.text[:200])
ta_id = tenant_created.json().get("id") if tenant_created.status_code == 201 else None
ta_row = session.get(LegalEntity, ta_id) if ta_id else None
check(
    "creation stamps the request tenant",
    ta_row is not None and ta_row.tenant_id == TENANT_A,
    tenant_created.text[:200],
)

cross_read = client.get(f"/api/v1/core-hr/legal-entities/{ta_id}", headers=HB)
check("tenant B reads tenant A's entity as 404", cross_read.status_code == 404, f"got {cross_read.status_code}")

cross_list = client.get("/api/v1/core-hr/legal-entities", headers=HB)
check(
    "tenant B's list excludes tenant A's entity",
    cross_list.status_code == 200
    and all(row["id"] != ta_id for row in cross_list.json()),
    f"got {cross_list.status_code}",
)

own_list = client.get("/api/v1/core-hr/legal-entities", headers=HA)
check(
    "tenant A still sees its own entity",
    own_list.status_code == 200 and any(row["id"] == ta_id for row in own_list.json()),
    f"got {own_list.status_code}",
)

cross_patch = client.patch(
    f"/api/v1/core-hr/legal-entities/{ta_id}", headers=HB, json={"name": "Hijacked"}
)
check("tenant B cannot edit tenant A's entity", cross_patch.status_code == 404, f"got {cross_patch.status_code}")

cross_delete = client.delete(f"/api/v1/core-hr/legal-entities/{ta_id}", headers=HB)
check("tenant B cannot deactivate tenant A's entity", cross_delete.status_code == 404, f"got {cross_delete.status_code}")

# Tenant-scoped codes: the same code may exist once per tenant, and the
# app check is case-insensitive within a tenant. A global unique would
# refuse the second tenant's row (and leak its existence via 409).
shared_a = client.post(
    "/api/v1/core-hr/legal-entities",
    headers=HA,
    json={"code": "LE-SHARED", "name": "Shared A Ltd"},
)
check("tenant A creates the shared code", shared_a.status_code == 201, shared_a.text[:200])
shared_b = client.post(
    "/api/v1/core-hr/legal-entities",
    headers=HB,
    json={"code": "LE-SHARED", "name": "Shared B Ltd"},
)
check(
    "the same code in another tenant is allowed (tenant-scoped)",
    shared_b.status_code == 201,
    f"got {shared_b.status_code}: {shared_b.text[:200]}",
)
shared_a_dup = client.post(
    "/api/v1/core-hr/legal-entities",
    headers=HA,
    json={"code": "le-shared", "name": "Shared A Duplicate"},
)
check(
    "a duplicate code in the same tenant is refused (case-insensitive)",
    shared_a_dup.status_code == 409,
    f"got {shared_a_dup.status_code}: {shared_a_dup.text[:200]}",
)

# ===========================================================================
print()
print("Employee link")
print("-" * 68)

hired = client.post(
    "/api/v1/employees/",
    headers=ADMIN,
    json={
        "first_name": "Lena",
        "last_name": "Entity",
        "email": "lena.entity@example.com",
        "hire_date": "2024-02-01",
        "job_id": job_row.id,
        "department_id": dept_row.id,
        "legal_entity_id": entity_id,
    },
)
check(
    "an employee can be hired into a legal entity",
    hired.status_code == 201 and hired.json().get("legal_entity_id") == entity_id,
    f"got {hired.status_code}: {hired.text[:300]}",
)
emp_id = hired.json().get("id") if hired.status_code == 201 else None

bad_link = client.post(
    "/api/v1/employees/",
    headers=ADMIN,
    json={
        "first_name": "Ghost",
        "last_name": "Link",
        "email": "ghost.link@example.com",
        "hire_date": "2024-02-01",
        "job_id": job_row.id,
        "department_id": dept_row.id,
        "legal_entity_id": 999999,
    },
)
check(
    "an unknown legal entity is refused on hire",
    bad_link.status_code == 422,
    f"got {bad_link.status_code}: {bad_link.text[:200]}",
)

plain_hire = client.post(
    "/api/v1/employees/",
    headers=ADMIN,
    json={
        "first_name": "No",
        "last_name": "Entity",
        "email": "no.entity@example.com",
        "hire_date": "2024-02-01",
        "job_id": job_row.id,
        "department_id": dept_row.id,
    },
)
check(
    "hiring without an entity still works (nullable)",
    plain_hire.status_code == 201 and plain_hire.json().get("legal_entity_id") is None,
    f"got {plain_hire.status_code}: {plain_hire.text[:300]}",
)

moved = client.patch(
    f"/api/v1/employees/{emp_id}",
    headers=ADMIN,
    json={"legal_entity_id": auto_id, "reason": "transferred to Auto Code Ltd"},
)
check(
    "an employee can move between entities",
    moved.status_code == 200 and moved.json().get("legal_entity_id") == auto_id,
    f"got {moved.status_code}: {moved.text[:300]}",
)

history = client.get(f"/api/v1/employees/{emp_id}/history", headers=ADMIN)
check(
    "the move leaves an effective-dated history row",
    history.status_code == 200
    and any(
        row.get("field") == "legal_entity_id"
        and str(row.get("new_value")) == str(auto_id)
        for row in history.json()
    ),
    f"got {history.status_code}: {history.text[:300]}",
)

bad_move = client.patch(
    f"/api/v1/employees/{emp_id}",
    headers=ADMIN,
    json={"legal_entity_id": 999999},
)
check("moving to an unknown entity is refused", bad_move.status_code == 422, f"got {bad_move.status_code}")

# Cross-tenant links: another tenant's entity answers the same 422 as an
# unknown id, so the caller cannot distinguish them (no existence leak),
# and the refused write leaves no history row.
cross_hire = client.post(
    "/api/v1/employees/",
    headers=ADMIN,
    json={
        "first_name": "Cross",
        "last_name": "Tenant",
        "email": "cross.tenant@example.com",
        "hire_date": "2024-02-01",
        "job_id": job_row.id,
        "department_id": dept_row.id,
        "legal_entity_id": ta_id,
    },
)
check(
    "hiring into another tenant's entity is refused (422)",
    cross_hire.status_code == 422,
    f"got {cross_hire.status_code}: {cross_hire.text[:200]}",
)
cross_move = client.patch(
    f"/api/v1/employees/{emp_id}",
    headers=ADMIN,
    json={"legal_entity_id": ta_id, "reason": "cross-tenant attempt"},
)
check(
    "moving to another tenant's entity is refused (422)",
    cross_move.status_code == 422,
    f"got {cross_move.status_code}: {cross_move.text[:200]}",
)
history_after_cross = client.get(f"/api/v1/employees/{emp_id}/history", headers=ADMIN)
check(
    "the refused cross-tenant move leaves no history",
    history_after_cross.status_code == 200
    and all(str(row.get("new_value")) != str(ta_id) for row in history_after_cross.json()),
    f"got {history_after_cross.status_code}: {history_after_cross.text[:300]}",
)

cleared = client.patch(
    f"/api/v1/employees/{emp_id}",
    headers=ADMIN,
    json={"legal_entity_id": None, "reason": "entity dissolved"},
)
check(
    "the link clears back to null",
    cleared.status_code == 200 and cleared.json().get("legal_entity_id") is None,
    f"got {cleared.status_code}: {cleared.text[:300]}",
)

# ===========================================================================
print()
print("Auditability")
print("-" * 68)

audit_rows = (
    session.query(AuditLog)
    .filter(AuditLog.entity_type == "LegalEntity")
    .all()
)
actions = {row.action for row in audit_rows}
check(
    "every legal-entity write is audited",
    {"create_legal_entity", "update_legal_entity", "deactivate_legal_entity"} <= actions,
    str(sorted(actions)),
)
check(
    "and the audit rows are attributable to the caller",
    all(row.actor_name == admin.username for row in audit_rows),
    str({row.actor_name for row in audit_rows}),
)

# ===========================================================================
print()
print("Migration 0036")
print("-" * 68)


def _run_migrations(db_path: str, target: str = "head", direction: str = "upgrade") -> None:
    """Run the migration CLI against a scratch database (the operator path)."""
    from pathlib import Path

    backend = Path(__file__).resolve().parent
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["ALEMBIC_DATABASE_URL"] = f"sqlite:///{db_path}"
    result = subprocess.run(
        [sys.executable, "-m", "scripts.migrate", direction, target],
        cwd=str(backend),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]


def _tables(db_path: str) -> set[str]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def _columns(db_path: str, table: str) -> set[str]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def _indexes(db_path: str, table: str) -> set[str]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return {row[1] for row in conn.execute(f"PRAGMA index_list({table})")}
    finally:
        conn.close()


workdir = tempfile.mkdtemp(prefix="legal_entity_migration_")
fresh = os.path.join(workdir, "fresh.db")
try:
    _run_migrations(fresh)
    check(
        "a fresh database reaches head with the legal_entities table",
        "legal_entities" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the table holds the columns the model declares",
        {
            "id", "tenant_id", "code", "name", "country",
            "registration_number", "address", "is_active", "created_at",
        } <= _columns(fresh, "legal_entities"),
        f"columns={sorted(_columns(fresh, 'legal_entities'))}",
    )
    check(
        "employees carries the nullable link column",
        "legal_entity_id" in _columns(fresh, "employees"),
        f"columns={sorted(_columns(fresh, 'employees'))}",
    )
    check(
        "the tenant composite index exists",
        "ix_legal_entities_tenant_id_id" in _indexes(fresh, "legal_entities"),
        f"indexes={sorted(_indexes(fresh, 'legal_entities'))}",
    )
    check(
        "the employee link index exists",
        "ix_employees_legal_entity_id" in _indexes(fresh, "employees"),
        f"indexes={sorted(_indexes(fresh, 'employees'))}",
    )

    _run_migrations(fresh, "0035_time_corrections_locks", "downgrade")
    check(
        "the downgrade removes the legal_entities table",
        "legal_entities" not in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the downgrade removes the employee link column",
        "legal_entity_id" not in _columns(fresh, "employees"),
        f"columns={sorted(_columns(fresh, 'employees'))}",
    )
    check(
        "the downgrade leaves the employees table alone",
        "employees" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    _run_migrations(fresh)
    check(
        "everything comes back on re-upgrade",
        "legal_entities" in _tables(fresh)
        and "legal_entity_id" in _columns(fresh, "employees"),
        f"tables={sorted(_tables(fresh))}",
    )
finally:
    shutil.rmtree(workdir, ignore_errors=True)

# ===========================================================================
print()
print("=" * 68)
print(f"LEGAL ENTITY SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
shutil.rmtree(os.path.dirname(DB_PATH), ignore_errors=True)
raise SystemExit(1 if RESULTS["fail"] else 0)
