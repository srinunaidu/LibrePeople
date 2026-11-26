"""Assets: register, custody lifecycle, clearance (team-a assets module).

What this suite proves
----------------------
* **Register** — create/read/patch, tag unique per tenant (case-insensitive
  within a tenant, the same tag allowed in another tenant), metadata-only
  edits (``status`` is not client-settable), explicit nulls refused;
* **FSM** — assign only from ``in_stock``; return by condition
  (good -> in_stock, damaged -> maintenance, lost -> lost); maintenance
  start/complete; retire final; every illegal move is ``409``;
* **Custody** — one open assignment per asset; assignment requires a
  same-tenant Active employee; transfer closes the old spell and opens a
  new unacknowledged one atomically (re-ack); acknowledgement is self-only
  (even admins are refused) and single-shot;
* **Roles** — HR/Admin manage; Associate sees own custody only; Manager
  sees the reporting line; PayrollViewer is refused;
* **Tenant scope** — foreign rows read 404, lists are tenant-filtered, a
  conflicting client-supplied tenant id is refused 409;
* **Clearance** — read-only toward offboarding: reports open spells and
  writes nothing (audit count unchanged);
* **Audit** — every write chained in the same transaction; refused moves
  leave no audit row; the whole chain verifies;
* **Migration 0046** — a fresh database reaches head with both tables,
  declared columns/indexes and the per-tenant tag uniqueness; the downgrade
  removes exactly what the upgrade created.

Run:  python tests/test_assets.py   (from backend/)
  or: pytest tests/test_assets.py
"""
import datetime
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="assets_test_suite_"), "assets_test_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
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

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.api.v1.endpoints import assets as assets_endpoints  # noqa: E402
from app.models.assets import Asset, AssetAssignment  # noqa: E402,F401
from app.models.audit import AuditLog  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402

# Integration is deliberately NOT wired into app/api/v1/api.py by this
# module (exclusive-files build); the suite mounts the router itself, the
# same way the integration snippet in docs/coordination will.
app.include_router(assets_endpoints.router, prefix="/api/v1/assets", tags=["assets"])

PASSWORD = "AssetPass123"
TENANT_A = "tenant-ast-a"
TENANT_B = "tenant-ast-b"

_RESULT = None


def _run() -> dict:
    global _RESULT
    if _RESULT is not None:
        return _RESULT

    results = {"pass": 0, "fail": 0}
    failures: list[tuple[str, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        if ok:
            results["pass"] += 1
            print(f"  PASS  {name}")
        else:
            results["fail"] += 1
            failures.append((name, detail))
            print(f"  FAIL  {name}  {detail}")

    Base.metadata.create_all(bind=engine)

    # --- fixtures -----------------------------------------------------------
    db = SessionLocal()
    dept = Department(name="Asset Ops", code="ASTOPS")
    db.add(dept)
    db.commit()
    db.refresh(dept)
    job = Job(title="Asset Custodian", code="ASTCUST", department_id=dept.id)
    db.add(job)
    db.commit()
    db.refresh(job)

    def _employee(code: str, manager_id=None, status="Active", tenant_id=None) -> Employee:
        person = Employee(
            employee_id=code,
            first_name="Ast",
            last_name=code,
            email=f"{code.lower()}@example.com",
            hire_date=datetime.date(2024, 1, 1),
            job_id=job.id,
            department_id=dept.id,
            manager_id=manager_id,
            status=status,
            tenant_id=tenant_id,
        )
        db.add(person)
        db.commit()
        db.refresh(person)
        return person

    emp_mgr = _employee("AST-MGR")
    emp_a = _employee("AST-A", manager_id=emp_mgr.id)
    emp_b = _employee("AST-B")
    emp_left = _employee("AST-LEFT", status="Terminated")
    emp_foreign = _employee("AST-FOR", tenant_id=TENANT_B)

    def _user(username: str, role: str, employee_id=None) -> None:
        db.add(
            User(
                username=username,
                email=f"{username}@example.com",
                hashed_password=get_password_hash(PASSWORD),
                role=role,
                is_active=True,
                employee_id=employee_id,
                mfa_enabled=role in ("SuperAdmin", "HR"),
            )
        )
        db.commit()

    _user("ast_admin", "SuperAdmin")
    _user("ast_hr", "HR")
    _user("ast_mgr", "Manager", emp_mgr.id)
    _user("ast_assoc_a", "Associate", emp_a.id)
    _user("ast_assoc_b", "Associate", emp_b.id)
    _user("ast_pay", "PayrollViewer")

    EMP_MGR_ID, EMP_A_ID, EMP_B_ID = emp_mgr.id, emp_a.id, emp_b.id
    EMP_LEFT_ID, EMP_FOR_ID = emp_left.id, emp_foreign.id
    db.close()

    client = TestClient(app, raise_server_exceptions=False)

    def _headers(username: str) -> dict:
        token = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": PASSWORD},
        ).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def _tenant_headers(username: str, tenant: str) -> dict:
        token = create_access_token(subject=username, extra_claims={"tenant": tenant})
        return {"Authorization": f"Bearer {token}"}

    H_ADMIN = _headers("ast_admin")
    H_HR = _headers("ast_hr")
    H_MGR = _headers("ast_mgr")
    H_A = _headers("ast_assoc_a")
    H_B = _headers("ast_assoc_b")
    H_PAY = _headers("ast_pay")
    HA = _tenant_headers("ast_admin", TENANT_A)
    HB = _tenant_headers("ast_admin", TENANT_B)

    def _create(headers, tag, name="Laptop", **kw):
        return client.post(
            "/api/v1/assets",
            headers=headers,
            json={"tag": tag, "name": name, "category": "IT", **kw},
        )

    def _audit_count() -> int:
        s = SessionLocal()
        try:
            return s.query(AuditLog).count()
        finally:
            s.close()

    # =======================================================================
    print("\n[REGISTER-1] The asset register and per-tenant tags")
    # =======================================================================
    r = _create(H_ADMIN, "AST-0001", "Laptop One", serial_number="SN-1")
    check("admin creates an asset", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    check("a new asset is in_stock", r.json().get("status") == "in_stock", r.text[:200])
    A1 = r.json().get("id")

    r = _create(H_ADMIN, "ast-0001", "Duplicate")
    check("a duplicate tag is refused case-insensitively", r.status_code == 409, f"got {r.status_code}")
    check("the refusal is duplicate_natural_key", r.json().get("error", {}).get("code") == "duplicate_natural_key", r.text[:200])

    r = _create(HB, "AST-0001", "Tenant B Laptop")
    check("the same tag in another tenant is allowed", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    B1 = r.json().get("id") if r.status_code == 201 else None
    check("the tenant is stamped on create", r.json().get("tenant_id") == TENANT_B, r.text[:200])

    r = _create(HA, "AST-0001", "Tenant A Laptop")
    check("tenant A may also hold AST-0001 (uniqueness is per tenant)", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

    A2 = _create(H_ADMIN, "AST-0002", "Laptop Two").json().get("id")
    A3 = _create(H_ADMIN, "AST-0003", "Phone Three").json().get("id")

    for who, hdr in (("Associate", H_A), ("Manager", H_MGR), ("PayrollViewer", H_PAY)):
        r = _create(hdr, f"AST-NO-{who}")
        check(f"{who} cannot create assets", r.status_code == 403, f"got {r.status_code}")

    r = client.get("/api/v1/assets/999999", headers=H_ADMIN)
    check("an unknown asset reads as 404", r.status_code == 404, f"got {r.status_code}")

    r = client.patch(f"/api/v1/assets/{A1}", headers=H_HR, json={"name": "Laptop One (renamed)"})
    check("HR patches metadata", r.status_code == 200 and r.json()["name"] == "Laptop One (renamed)", f"got {r.status_code}: {r.text[:200]}")

    r = client.patch(f"/api/v1/assets/{A1}", headers=H_ADMIN, json={"tag": "ast-0002"})
    check("patching onto another asset's tag is 409", r.status_code == 409, f"got {r.status_code}")

    r = client.patch(f"/api/v1/assets/{A1}", headers=H_ADMIN, json={"name": None})
    check("an explicit null name is refused", r.status_code == 422, f"got {r.status_code}")

    r = client.patch(f"/api/v1/assets/{A1}", headers=H_ADMIN, json={"status": "retired"})
    check(
        "status is not client-settable (extra field ignored)",
        r.status_code == 200 and r.json()["status"] == "in_stock",
        f"got {r.status_code}: {r.text[:200]}",
    )

    r = client.patch(f"/api/v1/assets/{A1}", headers=H_A, json={"name": "Nope"})
    check("Associate cannot patch assets", r.status_code == 403, f"got {r.status_code}")

    # =======================================================================
    print("\n[ASSIGN-1] Assignment: in_stock, same-tenant active, single open")
    # =======================================================================
    r = client.post(f"/api/v1/assets/{A1}/assign", headers=H_ADMIN, json={"employee_id": EMP_A_ID})
    check("admin assigns an in_stock asset", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    ASG1 = r.json().get("id")
    check("the assignment opens unacknowledged", r.json().get("status") == "open" and r.json().get("acknowledged_at") is None, r.text[:200])
    r = client.get(f"/api/v1/assets/{A1}", headers=H_ADMIN)
    check("the asset is now assigned", r.json().get("status") == "assigned", r.text[:200])

    r = client.post(f"/api/v1/assets/{A1}/assign", headers=H_ADMIN, json={"employee_id": EMP_B_ID})
    check("a second open assignment is refused 409", r.status_code == 409, f"got {r.status_code}: {r.text[:200]}")

    r = client.post(f"/api/v1/assets/{A2}/assign", headers=H_ADMIN, json={"employee_id": EMP_LEFT_ID})
    check("a terminated employee cannot hold assets (409)", r.status_code == 409, f"got {r.status_code}: {r.text[:200]}")
    check("the refusal names employee_not_active", r.json().get("error", {}).get("code") == "employee_not_active", r.text[:200])

    r = client.post(f"/api/v1/assets/{A2}/assign", headers=H_ADMIN, json={"employee_id": EMP_FOR_ID})
    check("a foreign-tenant employee does not resolve (422)", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")

    r = client.post(f"/api/v1/assets/{A2}/assign", headers=H_A, json={"employee_id": EMP_A_ID})
    check("Associate cannot assign (manage is HR/Admin)", r.status_code == 403, f"got {r.status_code}")

    r = client.post(f"/api/v1/assets/{A2}/assign", headers=H_ADMIN, json={"employee_id": EMP_A_ID})
    check("a second asset assigns to the same employee", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    ASG2 = r.json().get("id")

    # =======================================================================
    print("\n[ACK-1] Acknowledgement is self-only and single-shot")
    # =======================================================================
    r = client.post(f"/api/v1/assets/assignments/{ASG1}/ack", headers=H_ADMIN)
    check("an admin cannot acknowledge on the employee's behalf", r.status_code == 403, f"got {r.status_code}")

    r = client.post(f"/api/v1/assets/assignments/{ASG1}/ack", headers=H_B)
    check("another employee cannot acknowledge", r.status_code == 403, f"got {r.status_code}")

    r = client.post(f"/api/v1/assets/assignments/{ASG1}/ack", headers=H_A)
    check("the assigned employee acknowledges", r.status_code == 200 and r.json().get("acknowledged_at"), f"got {r.status_code}: {r.text[:200]}")

    r = client.post(f"/api/v1/assets/assignments/{ASG1}/ack", headers=H_A)
    check("acknowledging twice is 409", r.status_code == 409, f"got {r.status_code}")

    # =======================================================================
    print("\n[TRANSFER-1] Transfer closes and re-opens atomically, re-ack")
    # =======================================================================
    r = client.post(f"/api/v1/assets/{A1}/transfer", headers=H_HR, json={"employee_id": EMP_B_ID})
    check("HR transfers custody", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    ASG3 = r.json().get("id")
    check("the new spell is open and unacknowledged (re-ack)", r.json().get("status") == "open" and r.json().get("acknowledged_at") is None, r.text[:200])

    r = client.get(f"/api/v1/assets/assignments?asset_id={A1}", headers=H_ADMIN)
    rows = {row["id"]: row for row in r.json()}
    check(
        "the old spell closed as transferred in the same transaction",
        rows.get(ASG1, {}).get("status") == "closed" and rows.get(ASG1, {}).get("close_reason") == "transferred",
        r.text[:300],
    )
    check("exactly one open spell remains", sum(1 for row in rows.values() if row["status"] == "open") == 1, r.text[:300])

    r = client.get(f"/api/v1/assets/{A1}", headers=H_ADMIN)
    check("the asset stays assigned across a transfer", r.json().get("status") == "assigned", r.text[:200])

    r = client.post(f"/api/v1/assets/{A1}/transfer", headers=H_ADMIN, json={"employee_id": EMP_B_ID})
    check("transferring to the current holder is 409", r.status_code == 409, f"got {r.status_code}")

    r = client.post(f"/api/v1/assets/{A1}/transfer", headers=H_ADMIN, json={"employee_id": EMP_LEFT_ID})
    check("transferring to an inactive employee is 409", r.status_code == 409, f"got {r.status_code}")

    r = client.post(f"/api/v1/assets/assignments/{ASG3}/ack", headers=H_B)
    check("the new holder acknowledges afresh", r.status_code == 200 and r.json().get("acknowledged_at"), f"got {r.status_code}: {r.text[:200]}")

    r = client.post(f"/api/v1/assets/assignments/{ASG1}/ack", headers=H_A)
    check("a closed spell can no longer be acknowledged (409)", r.status_code == 409, f"got {r.status_code}")

    # =======================================================================
    print("\n[RETURN-1] Return records condition and moves status")
    # =======================================================================
    r = client.post(f"/api/v1/assets/{A1}/return", headers=H_ADMIN, json={"condition": "good"})
    check("return in good condition", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    check(
        "the spell closed as returned with its condition",
        r.json().get("status") == "closed" and r.json().get("close_reason") == "returned" and r.json().get("return_condition") == "good",
        r.text[:200],
    )
    r = client.get(f"/api/v1/assets/{A1}", headers=H_ADMIN)
    check("a good return lands in_stock", r.json().get("status") == "in_stock", r.text[:200])

    r = client.post(f"/api/v1/assets/{A1}/return", headers=H_ADMIN, json={"condition": "good"})
    check("returning an unassigned asset is 409", r.status_code == 409, f"got {r.status_code}")

    r = client.post(f"/api/v1/assets/{A2}/return", headers=H_ADMIN, json={"condition": "broken"})
    check("an unknown condition is 422", r.status_code == 422, f"got {r.status_code}")

    # =======================================================================
    print("\n[MAINT-1] Maintenance flips, blocked while assigned")
    # =======================================================================
    r = client.post(f"/api/v1/assets/{A1}/maintenance/start", headers=H_ADMIN, json={})
    check("an in_stock asset enters maintenance", r.status_code == 200 and r.json().get("status") == "maintenance", f"got {r.status_code}: {r.text[:200]}")

    r = client.post(f"/api/v1/assets/{A1}/maintenance/complete", headers=H_ADMIN, json={})
    check("maintenance completes back to in_stock", r.status_code == 200 and r.json().get("status") == "in_stock", f"got {r.status_code}: {r.text[:200]}")

    before = _audit_count()
    r = client.post(f"/api/v1/assets/{A2}/maintenance/start", headers=H_ADMIN, json={})
    check("maintenance is blocked while assigned (409)", r.status_code == 409, f"got {r.status_code}: {r.text[:200]}")
    check("the refused flip wrote no audit row", _audit_count() == before, f"{before} -> {_audit_count()}")

    r = client.post(f"/api/v1/assets/{A2}/return", headers=H_ADMIN, json={"condition": "damaged", "notes": "cracked screen"})
    check("a damaged return lands in maintenance", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    r = client.get(f"/api/v1/assets/{A2}", headers=H_ADMIN)
    check("the damaged asset is in maintenance", r.json().get("status") == "maintenance", r.text[:200])

    r = client.post(f"/api/v1/assets/{A2}/maintenance/start", headers=H_ADMIN, json={})
    check("starting maintenance twice is 409", r.status_code == 409, f"got {r.status_code}")

    r = client.post(f"/api/v1/assets/{A2}/assign", headers=H_ADMIN, json={"employee_id": EMP_B_ID})
    check("an asset in maintenance cannot be assigned (409)", r.status_code == 409, f"got {r.status_code}")

    r = client.post(f"/api/v1/assets/{A2}/maintenance/complete", headers=H_HR, json={})
    check("repaired asset returns to stock", r.status_code == 200 and r.json().get("status") == "in_stock", f"got {r.status_code}: {r.text[:200]}")

    # =======================================================================
    print("\n[RETIRE-1] Retirement and loss are final")
    # =======================================================================
    r = client.post(f"/api/v1/assets/{A1}/retire", headers=H_ADMIN, json={"reason": "end of life"})
    check("an in_stock asset retires", r.status_code == 200 and r.json().get("status") == "retired", f"got {r.status_code}: {r.text[:200]}")

    r = client.post(f"/api/v1/assets/{A1}/retire", headers=H_ADMIN, json={})
    check("retiring twice is 409", r.status_code == 409, f"got {r.status_code}")

    r = client.post(f"/api/v1/assets/{A1}/assign", headers=H_ADMIN, json={"employee_id": EMP_A_ID})
    check("a retired asset cannot be assigned (409)", r.status_code == 409, f"got {r.status_code}")

    r = client.post(f"/api/v1/assets/{A3}/assign", headers=H_ADMIN, json={"employee_id": EMP_B_ID})
    ASG4 = r.json().get("id")
    r = client.post(f"/api/v1/assets/{A3}/return", headers=H_ADMIN, json={"condition": "lost"})
    check("a lost return closes the spell", r.status_code == 200 and r.json().get("return_condition") == "lost", f"got {r.status_code}: {r.text[:200]}")
    r = client.get(f"/api/v1/assets/{A3}", headers=H_ADMIN)
    check("a lost asset is lost", r.json().get("status") == "lost", r.text[:200])
    r = client.post(f"/api/v1/assets/{A3}/retire", headers=H_ADMIN, json={})
    check("a lost asset cannot be retired (final state)", r.status_code == 409, f"got {r.status_code}")
    r = client.post(f"/api/v1/assets/{A3}/maintenance/start", headers=H_ADMIN, json={})
    check("a lost asset cannot enter maintenance (final state)", r.status_code == 409, f"got {r.status_code}")

    # =======================================================================
    print("\n[VIS-1] Associate own-only, Manager reporting line")
    # =======================================================================
    r = client.get("/api/v1/assets", headers=H_A)
    ids_a = {row["id"] for row in r.json()}
    check("Associate A sees only assets in their own custody history", r.status_code == 200 and ids_a == {A1, A2}, f"got {r.status_code}: {sorted(ids_a)} expected {sorted({A1, A2})}")

    r = client.get("/api/v1/assets", headers=H_B)
    ids_b = {row["id"] for row in r.json()}
    check("Associate B sees their own, not A's", r.status_code == 200 and ids_b == {A1, A3}, f"got {r.status_code}: {sorted(ids_b)}")

    r = client.get(f"/api/v1/assets/{A3}", headers=H_A)
    check("an asset outside the Associate's custody reads 404", r.status_code == 404, f"got {r.status_code}")

    r = client.get("/api/v1/assets/assignments", headers=H_A)
    check(
        "Associate A's assignment list is own-only",
        r.status_code == 200 and all(row["employee_id"] == EMP_A_ID for row in r.json()) and {row["id"] for row in r.json()} == {ASG1, ASG2},
        f"got {r.status_code}: {r.text[:300]}",
    )

    r = client.get("/api/v1/assets/assignments?mine=true", headers=H_B)
    check(
        "mine=true selects the caller's own spells",
        r.status_code == 200 and {row["id"] for row in r.json()} == {ASG3, ASG4},
        f"got {r.status_code}: {r.text[:300]}",
    )

    r = client.get("/api/v1/assets/assignments?mine=true", headers=H_ADMIN)
    check("mine=true without an employee record is refused", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")

    r = client.get("/api/v1/assets/assignments", headers=H_MGR)
    check(
        "the Manager sees the reporting line (A), not B",
        r.status_code == 200 and {row["id"] for row in r.json()} == {ASG1, ASG2},
        f"got {r.status_code}: {r.text[:300]}",
    )

    r = client.get("/api/v1/assets", headers=H_PAY)
    check("PayrollViewer has no asset surface", r.status_code == 403, f"got {r.status_code}")

    # =======================================================================
    print("\n[TENANT-1] Tenant filter: 404 across, 409 on mismatch")
    # =======================================================================
    r = client.get(f"/api/v1/assets/{A1}", headers=HB)
    check("another tenant's asset reads 404", r.status_code == 404, f"got {r.status_code}")

    r = client.get(f"/api/v1/assets/{B1}", headers=HA)
    check("tenant A cannot read tenant B's asset", r.status_code == 404, f"got {r.status_code}")

    r = client.get("/api/v1/assets", headers=HB)
    check("tenant B's list holds only its own asset", r.status_code == 200 and {row["id"] for row in r.json()} == {B1}, f"got {r.status_code}: {r.text[:300]}")

    r = client.get("/api/v1/assets", headers={**HA, "X-Tenant-Id": TENANT_B})
    check("a conflicting client tenant id is 409 tenant_mismatch", r.status_code == 409 and r.json().get("error", {}).get("code") == "tenant_mismatch", f"got {r.status_code}: {r.text[:200]}")

    r = client.post(f"/api/v1/assets/{B1}/assign", headers=HB, json={"employee_id": EMP_A_ID})
    check("a default-tenant employee does not resolve for tenant B", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")

    r = client.post(f"/api/v1/assets/{A1}/retire", headers=HB, json={})
    check("another tenant cannot move the asset", r.status_code == 404, f"got {r.status_code}")

    # =======================================================================
    print("\n[CLEAR-1] Clearance is read-only toward offboarding")
    # =======================================================================
    r = client.post(f"/api/v1/assets/{A2}/assign", headers=H_ADMIN, json={"employee_id": EMP_B_ID})
    check("B takes custody of the repaired asset", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

    before = _audit_count()
    r = client.get(f"/api/v1/assets/clearance/{EMP_B_ID}", headers=H_HR)
    check("clearance reports the open spell", r.status_code == 200 and r.json().get("clear") is False and r.json().get("outstanding_count") == 1, f"got {r.status_code}: {r.text[:300]}")
    check("the outstanding item names the asset", r.json().get("outstanding", [{}])[0].get("tag") == "AST-0002", r.text[:300])
    check("clearance writes nothing (audit count unchanged)", _audit_count() == before, f"{before} -> {_audit_count()}")

    r = client.get(f"/api/v1/assets/clearance/{EMP_B_ID}", headers=H_A)
    check("Associate cannot read clearance", r.status_code == 403, f"got {r.status_code}")

    r = client.get(f"/api/v1/assets/clearance/{EMP_B_ID}", headers=H_MGR)
    check("a Manager outside the line reads 404", r.status_code == 404, f"got {r.status_code}")

    r = client.post(f"/api/v1/assets/{A2}/return", headers=H_ADMIN, json={"condition": "good"})
    check("the asset comes back", r.status_code == 200, f"got {r.status_code}")
    r = client.get(f"/api/v1/assets/clearance/{EMP_B_ID}", headers=H_HR)
    check("clearance is clear once nothing is held", r.status_code == 200 and r.json().get("clear") is True and r.json().get("outstanding_count") == 0, f"got {r.status_code}: {r.text[:300]}")

    # =======================================================================
    print("\n[AUDIT-1] Chained audit, same transaction")
    # =======================================================================
    s = SessionLocal()
    try:
        actions = {row.action for row in s.query(AuditLog).all()}
        expected = {
            "create_asset", "update_asset", "assign_asset", "acknowledge_asset",
            "transfer_asset", "return_asset", "start_asset_maintenance",
            "complete_asset_maintenance", "retire_asset",
        }
        check("every lifecycle write is audited", expected <= actions, str(sorted(expected - actions)))

        transfer_rows = s.query(AuditLog).filter(AuditLog.action == "transfer_asset").all()
        check(
            "the transfer audits one entry naming both spells",
            len(transfer_rows) == 1 and "closed=" in (transfer_rows[0].details or "") and "opened=" in (transfer_rows[0].details or ""),
            str([r.details for r in transfer_rows]),
        )

        from app.core.audit_chain import verify_chain

        verdict = verify_chain(s, check_head=True)
        check("the audit chain verifies end to end", verdict.ok, str(verdict.as_dict())[:300])
    finally:
        s.close()

    before = _audit_count()
    r = client.post(f"/api/v1/assets/{A1}/assign", headers=H_ADMIN, json={"employee_id": EMP_A_ID})
    check("a refused assign is 409", r.status_code == 409, f"got {r.status_code}")
    check("a refused move leaves no audit row (same-txn staging)", _audit_count() == before, f"{before} -> {_audit_count()}")

    # =======================================================================
    print("\n[MIGRATION-1] Migration 0046, and its downgrade")
    # =======================================================================

    def _run_migrations(db_path: str, target: str = "head", direction: str = "upgrade") -> None:
        env = dict(os.environ)
        env["DATABASE_URL"] = f"sqlite:///{db_path}"
        env["ALEMBIC_DATABASE_URL"] = f"sqlite:///{db_path}"
        result = subprocess.run(
            [sys.executable, "-m", "scripts.migrate", direction, target],
            cwd=str(_BACKEND_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]

    def _tables(db_path: str) -> set[str]:
        conn = sqlite3.connect(db_path)
        try:
            return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()

    def _columns(db_path: str, table: str) -> set[str]:
        conn = sqlite3.connect(db_path)
        try:
            return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        finally:
            conn.close()

    def _indexes(db_path: str, table: str) -> set[str]:
        conn = sqlite3.connect(db_path)
        try:
            return {row[1] for row in conn.execute(f"PRAGMA index_list({table})")}
        finally:
            conn.close()

    workdir = tempfile.mkdtemp(prefix="assets_migration_")
    fresh = os.path.join(workdir, "fresh.db")
    try:
        _run_migrations(fresh)
        check("a fresh database reaches head with the assets table", "assets" in _tables(fresh), f"tables={sorted(_tables(fresh))}")
        check("the assignment table is created", "asset_assignments" in _tables(fresh), f"tables={sorted(_tables(fresh))}")
        check(
            "the assets table holds the columns the model declares",
            {"id", "tenant_id", "tag", "name", "category", "description", "serial_number", "status", "created_by", "created_at", "updated_at"}
            <= _columns(fresh, "assets"),
            f"columns={sorted(_columns(fresh, 'assets'))}",
        )
        check(
            "the assignment table holds the custody columns",
            {"id", "tenant_id", "asset_id", "employee_id", "status", "notes", "assigned_by", "assigned_at", "acknowledged_at", "closed_by", "closed_at", "close_reason", "return_condition"}
            <= _columns(fresh, "asset_assignments"),
            f"columns={sorted(_columns(fresh, 'asset_assignments'))}",
        )
        check(
            "the declared indexes exist",
            {"ix_assets_tenant_id_id", "ix_asset_asg_tenant_id_id", "ix_asset_assignments_asset_id", "ix_asset_assignments_employee_id"}
            <= _indexes(fresh, "assets") | _indexes(fresh, "asset_assignments"),
            f"indexes={sorted(_indexes(fresh, 'assets')) + sorted(_indexes(fresh, 'asset_assignments'))}",
        )
        conn = sqlite3.connect(fresh)
        try:
            # SQLite renders a named UNIQUE constraint as sqlite_autoindex_*;
            # Postgres keeps the name. Either way, prove a UNIQUE index on
            # exactly (tenant_id, tag) exists.
            unique_on_tenant_tag = False
            for row in conn.execute("PRAGMA index_list(assets)").fetchall():
                idx_name, is_unique = row[1], row[2]
                if not is_unique:
                    continue
                cols = [r[2] for r in conn.execute(f"PRAGMA index_info({idx_name})")]
                if cols == ["tenant_id", "tag"]:
                    unique_on_tenant_tag = True
            check(
                "the per-tenant tag uniqueness is enforced by the database",
                unique_on_tenant_tag,
                f"indexes={sorted(_indexes(fresh, 'assets'))}",
            )
            conn.execute("INSERT INTO assets (tenant_id, tag, name) VALUES ('t1', 'X-1', 'One')")
            dup_refused = False
            try:
                conn.execute("INSERT INTO assets (tenant_id, tag, name) VALUES ('t1', 'X-1', 'Again')")
            except sqlite3.IntegrityError:
                dup_refused = True
            conn.execute("INSERT INTO assets (tenant_id, tag, name) VALUES ('t2', 'X-1', 'Other tenant')")
            conn.commit()
            check("the DB refuses a duplicate (tenant, tag) and allows it across tenants", dup_refused, "duplicate insert was not refused")
        finally:
            conn.close()

        _run_migrations(fresh, "0045_payroll_pipeline_run_type", "downgrade")
        check("the downgrade removes the assignment table", "asset_assignments" not in _tables(fresh), f"tables={sorted(_tables(fresh))}")
        check("the downgrade removes the assets table", "assets" not in _tables(fresh), f"tables={sorted(_tables(fresh))}")
        check("the downgrade leaves the employees table alone", "employees" in _tables(fresh), f"tables={sorted(_tables(fresh))}")
        _run_migrations(fresh)
        check("everything comes back on re-upgrade", {"assets", "asset_assignments"} <= _tables(fresh), f"tables={sorted(_tables(fresh))}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    # =======================================================================
    print()
    print("----------------------------------------------------------------")
    print(f"assets tests: {results['pass']} passed, {results['fail']} failed")
    if failures:
        print("\nFailures:")
        for name, detail in failures:
            print(f"  - {name}: {detail}")
    print("----------------------------------------------------------------")
    shutil.rmtree(os.path.dirname(DB_PATH), ignore_errors=True)
    _RESULT = results
    return results


def test_assets_module():
    """pytest entry point: the whole module suite must pass."""
    results = _run()
    assert results["fail"] == 0, f"{results['fail']} asset checks failed"


if __name__ == "__main__":
    raise SystemExit(1 if _run()["fail"] else 0)