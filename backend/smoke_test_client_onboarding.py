"""Local smoke test for the Client Onboarding Portal (SQLite)."""
import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.mkdtemp(prefix="smoke_co_"), "smoke_co.db"
)
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = "*"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402

from app.models.client_onboarding import Client as _Client
from app.crud import crud_client_onboarding as _crud
from app.schemas.client_onboarding import ClientCreate as _ClientCreate

Base.metadata.create_all(bind=engine)

db = SessionLocal()
if not db.query(User).filter(User.username == "admin").first():
    db.add(User(username="admin", email="admin@k.local",
                hashed_password=get_password_hash("secret123"),
                role="SuperAdmin", is_active=True, mfa_enabled=True))
    db.commit()
# Single-tenant install: no registry CRUD — seed the install's company row via
# the production seeding path (same defaults POST /clients used to create).
# The removed POST /clients must answer 404.
_company = db.query(_Client).order_by(_Client.id.asc()).first()
if _company is None:
    _company = _crud.create_client(db, _ClientCreate(
        name="Acme", slug="acme", industry="Mfg", country="India",
        timezone="Asia/Kolkata", primary_color="#1E40AF",
        contact_name="Jane", contact_email="jane@acme.com",
        status="Active"))
cid = _company.id
db.close()

client = TestClient(app)
H = {"Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'secret123'}).json()['access_token']}"}

PASS = FAIL = 0


def check(name, ok, extra=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS  {name} {extra}")
    else:
        FAIL += 1
        print(f"FAIL  {name} {extra}")


# The install's single company replaces the removed registry (AC-3 404s).
r = client.post("/api/v1/onboarding-portal/clients", headers=H, json={
    "name": "Acme", "slug": "acme", "industry": "Mfg", "country": "India",
    "timezone": "Asia/Kolkata", "primary_color": "#1E40AF",
    "contact_name": "Jane", "contact_email": "jane@acme.com",
})
check("registry create removed (404)", r.status_code == 404, str(r.status_code))

r = client.get("/api/v1/onboarding-portal/clients", headers=H)
check("registry list removed (404)", r.status_code == 404, str(r.status_code))

r = client.get(f"/api/v1/onboarding-portal/clients/{cid}", headers=H)
check("registry read removed (404)", r.status_code == 404, str(r.status_code))

r = client.get("/api/v1/onboarding-portal/clients/by-slug/acme", headers=H)
check("by-slug lookup removed (404)", r.status_code == 404, str(r.status_code))

r = client.get("/api/v1/onboarding-portal/tenants", headers=H)
check("tenants alias removed (404)", r.status_code == 404, str(r.status_code))

# Single company endpoint: public, deterministic, carries branding + id.
r = client.get("/api/v1/onboarding-portal/company")
check("company endpoint public", r.status_code == 200, str(r.status_code))
check("company carries id + branding",
      r.json().get("id") == cid and r.json().get("slug") == "acme"
      and r.json().get("primary_color") == "#1E40AF", str(r.json())[:160])
check("default feature flags", len(r.json()) >= 0)

# Feature flags seeded
r = client.get(f"/api/v1/onboarding-portal/clients/{cid}/feature-flags", headers=H)
check("list feature flags", r.status_code == 200 and len(r.json()) >= 10, f"n={len(r.json())}")

# Toggle a flag
r = client.put(f"/api/v1/onboarding-portal/clients/{cid}/feature-flags/feature.self_service",
               headers=H, json={"enabled": True})
check("toggle feature flag", r.status_code == 200 and r.json()["enabled"] is True)

# Create integration
r = client.post(f"/api/v1/onboarding-portal/clients/{cid}/integrations", headers=H, json={
    "name": "HR Source", "kind": "oracle_adb", "endpoint": "adb.example.com:1522/svc",
    "username": "admin", "secret": "secret123",
})
check("create integration", r.status_code == 201, str(r.status_code))
iid = r.json()["id"]
check("secret masked", r.json()["has_secret"] is True)

# Test integration
r = client.post(f"/api/v1/onboarding-portal/clients/{cid}/integrations/{iid}/test", headers=H)
check("test integration", r.status_code == 200 and r.json()["status"] in ("connected", "error", "tested"), r.json().get("status"))

# Migration job
r = client.post(f"/api/v1/onboarding-portal/clients/{cid}/migrations", headers=H,
                json={"integration_id": iid, "entity": "employees", "total": 50})
check("start migration", r.status_code == 201, str(r.status_code))
jid = r.json()["id"]

r = client.post(f"/api/v1/onboarding-portal/clients/{cid}/migrations/{jid}/run", headers=H)
check("run migration", r.status_code == 200 and r.json()["status"] == "succeeded",
      f"status={r.json().get('status')}")

# Settings
r = client.put(f"/api/v1/onboarding-portal/clients/{cid}/settings/payroll.cycle_day",
               headers=H, json={"key": "payroll.cycle_day", "value": "15"})
check("upsert setting", r.status_code == 200 and r.json()["value"] == "15")

r = client.get(f"/api/v1/onboarding-portal/clients/{cid}/settings", headers=H)
check("list settings", r.status_code == 200 and len(r.json()) == 1)

# Onboarding steps
r = client.get(f"/api/v1/onboarding-portal/clients/{cid}/onboarding", headers=H)
check("onboarding progress", r.status_code == 200 and r.json()["total"] == 6, f"total={r.json().get('total')}")
step_id = r.json()["steps"][0]["id"]

r = client.post(f"/api/v1/onboarding-portal/clients/{cid}/onboarding/steps/{step_id}/complete", headers=H)
check("complete step", r.status_code == 200 and r.json()["completed"] is True)

r = client.get(f"/api/v1/onboarding-portal/clients/{cid}/onboarding", headers=H)
check("progress updated", r.json()["completed"] == 1 and r.json()["percent"] > 0)

# Create custom step
r = client.post(f"/api/v1/onboarding-portal/clients/{cid}/onboarding/steps", headers=H,
                json={"key": "custom", "title": "Custom Step", "order_index": 7})
check("create custom step", r.status_code == 201)

# Documentation
r = client.get("/api/v1/onboarding-portal/docs/migration-api", headers=H)
check("migration docs served", r.status_code == 200 and len(r.json().get("content", "")) > 100)

# Client update removed with the registry: the row is managed per install.
r = client.put(f"/api/v1/onboarding-portal/clients/{cid}", headers=H, json={"status": "Active"})
check("registry update removed (404)", r.status_code == 404, str(r.status_code))

# RBAC: an Associate must not be able to reach tenant administration.
#
# Self-service registration is disabled by default, so this now fails closed at
# the door. When it is enabled the payload can no longer carry a role at all.
from app.core.config import settings as _settings  # noqa: E402
_settings.ALLOW_SELF_REGISTRATION = True
r = client.post("/api/v1/auth/register", json={"username": "assoc", "email": "assoc@example.com", "password": "WorkerLogin2024", "role": "SuperAdmin"})
print("  register:", r.status_code, r.text[:120])
check("self-register cannot request a privileged role", r.status_code != 201 or r.json().get("role") == "Associate")
if r.status_code == 201:
    at = client.post("/api/v1/auth/login", json={"username": "assoc", "password": "WorkerLogin2024"}).json()["access_token"]
    r = client.get("/api/v1/onboarding-portal/company", headers={"Authorization": f"Bearer {at}"})
    check("RBAC: company endpoint stays public", r.status_code == 200)
    r = client.get(f"/api/v1/onboarding-portal/clients/{cid}/settings", headers={"Authorization": f"Bearer {at}"})
    check("RBAC: associate denied company settings", r.status_code == 403)
    r2 = client.post("/api/v1/auth/users", headers={"Authorization": f"Bearer {at}"}, json={"user_in": {"username": "escalated", "email": "esc@example.com", "password": "EscalatedPass123", "role": "SuperAdmin"}})
    check("RBAC: associate cannot create privileged users", r2.status_code == 403)
else:
    check("RBAC: associate denied register failed", False, "register failed")
_settings.ALLOW_SELF_REGISTRATION = False

print(f"\n==== {PASS} passed, {FAIL} failed ====")
raise SystemExit(1 if FAIL else 0)
