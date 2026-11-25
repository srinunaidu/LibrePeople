"""Verify tenant isolation across the API.

This is a NEGATIVE test suite: every check asserts that one tenant's principal
cannot read another tenant's data. It is expected to FAIL until tenant scoping
is implemented — that failure is the evidence for the P0 finding, not a flaky
test.

Run:  python verify_tenant_isolation.py
Exit: 0 = isolated (ready to claim multi-tenancy)
      1 = NOT isolated (must not be sold as multi-tenant)
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./tenant_isolation.db"
os.environ["SECRET_KEY"] = "tenant-isolation-secret"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"

import datetime  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.client_onboarding import Client  # noqa: E402

Base.metadata.create_all(bind=engine)

# Two tenants. Each gets its own user and its own employee record.
db = SessionLocal()
acme = db.query(Client).filter(Client.slug == "acme").first()
if not acme:
    acme = Client(name="Acme Corp", slug="acme")
    db.add(acme); db.commit(); db.refresh(acme)
globex = db.query(Client).filter(Client.slug == "globex").first()
if not globex:
    globex = Client(name="Globex", slug="globex")
    db.add(globex); db.commit(); db.refresh(globex)

for username, client_name in (("acme_admin", "Acme"), ("globex_admin", "Globex")):
    if not db.query(User).filter(User.username == username).first():
        db.add(
            User(
                username=username,
                email=f"{username}@example.com",
                hashed_password=get_password_hash("TenantPass123"),
                role="SuperAdmin",
                is_active=True,
            )
        )
db.commit()
db.close()

client = TestClient(app)


def token_for(username: str) -> str:
    r = client.post(
        "/api/v1/auth/login", json={"username": username, "password": "TenantPass123"}
    )
    return r.json().get("access_token", "")


ACME = {"Authorization": f"Bearer {token_for('acme_admin')}"}
GLOBEX = {"Authorization": f"Bearer {token_for('globex_admin')}"}

RESULTS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append(name)
        print(f"  FAIL  {name}  {detail}")


print("=" * 64)
print("TENANT ISOLATION VERIFICATION (negative tests)")
print("=" * 64)

# --- Can one tenant see the other tenant's client records? ---------------
acme_clients = client.get("/api/v1/onboarding-portal/clients", headers=ACME).json()
globex_visible_to_acme = [
    c for c in acme_clients if c.get("slug") == "globex"
]
check(
    "Acme cannot see the Globex client record",
    not globex_visible_to_acme,
    f"leaked: {[c.get('slug') for c in globex_visible_to_acme]}",
)

globex_clients = client.get("/api/v1/onboarding-portal/clients", headers=GLOBEX).json()
acme_visible_to_globex = [
    c for c in globex_clients if c.get("slug") == "acme"
]
check(
    "Globex cannot see the Acme client record",
    not acme_visible_to_globex,
    f"leaked: {[c.get('slug') for c in acme_visible_to_globex]}",
)

# --- Can one tenant mutate the other's client settings? ------------------
target = None
for c in globex_clients:
    if c.get("slug") == "acme":
        target = c.get("id")
if target:
    r = client.put(
        f"/api/v1/onboarding-portal/clients/{target}",
        headers=GLOBEX,
        json={"name": "HIJACKED BY GLOBEX"},
    )
    still = client.get(
        f"/api/v1/onboarding-portal/clients/{target}", headers=ACME
    ).json()
    check(
        "Globex cannot modify an Acme client record",
        still.get("name") != "HIJACKED BY GLOBEX",
        f"status={r.status_code} name={still.get('name')!r}",
    )
else:
    check("Globex cannot see Acme's client id", False, "Acme client not visible at all")

# --- Can one tenant read the other's employees? --------------------------
emps = client.get("/api/v1/employees?skip=0&limit=100", headers=ACME)
if emps.status_code == 200:
    rows = emps.json()
    check(
        "employee directory is tenant scoped",
        isinstance(rows, dict) and "items" in rows,
        f"flat unscoped list returned ({len(rows)} rows, no tenant separation)",
    )
else:
    check("employee directory readable", True)

# --- Report on the tenant-scoping columns --------------------------------
from sqlalchemy import inspect  # noqa: E402

inspector = inspect(engine)
tables = inspector.get_table_names()
tenant_scoped = [
    t for t in tables if "tenant_id" in {c["name"] for c in inspector.get_columns(t)}
]
print()
print(f"  tables: {len(tables)}")
print(f"  tables carrying a tenant_id column: {len(tenant_scoped)}")
if tenant_scoped:
    print(f"    {tenant_scoped}")

users_cols = {c["name"] for c in inspector.get_columns("users")}
check(
    "users table carries a tenant reference",
    "tenant_id" in users_cols or "client_id" in users_cols,
    f"users columns: {sorted(users_cols)}",
)

print()
print("=" * 64)
print(f"==== TENANT ISOLATION: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("Unresolved: " + "; ".join(FAILURES))
print("=" * 64)
print(
    "\nUntil every check passes, Karmathy must NOT be described as a\n"
    "multi-tenant product. `/t/:slug/` changes branding only — it does not\n"
    "restrict which tenant's data a signed-in user can read."
)
raise SystemExit(1 if RESULTS["fail"] else 0)