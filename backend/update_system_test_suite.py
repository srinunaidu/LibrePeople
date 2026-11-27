"""Update-system suite (update-system slice).

Covers the consent-gated update endpoints at ``/api/v1/admin/updates``:

* ``GET /current`` — SuperAdmin 200 with version + migration state; HR,
  Manager, Associate refused with the shared 403 envelope; 401 anonymous.
* ``GET /available`` — local manifest verified before display
  (``verified`` true, dev-ephemeral flagged, never silent); remote fetch
  disallowed by default (no egress without the double opt-in).
* ``POST /check`` — fail-closed: with no backup arranged the
  ``backup_fresh`` gate fails and the endpoint answers 409 with a named
  remediation per failed gate; the attempt stages exactly one audit row.
* ``POST /install`` — wrong ``manifest_sha256`` refused with 409; a
  gate-failing install is refused AND recorded in history.
* ``GET /history`` — install attempts are listed (audit chain durable).
* Unit: a tampered manifest fails ``verify_manifest`` (checksum chain).

Run:  python update_system_test_suite.py   (from backend/)
"""
import os

DB_PATH = "update_system_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"
os.environ["BACKUP_ENABLED"] = "false"
os.environ["BACKUP_SCHEDULE"] = "manual"
if "BACKUP_LAST_SUCCESS_AT" in os.environ:
    del os.environ["BACKUP_LAST_SUCCESS_AT"]
# Remote check off by default (no egress) — the spec default.
os.environ["UPDATE_CHECK_ALLOW_REMOTE"] = "false"
if "UPDATE_CHECK_REMOTE_URL" in os.environ:
    del os.environ["UPDATE_CHECK_REMOTE_URL"]

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import update_manifest as updates  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
client = TestClient(app, raise_server_exceptions=False)

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


LOGIN = "/api/v1/auth/login"
BASE = "/api/v1/admin/updates"
PASSWORD = "UpdatePass123"

ROLE_ACCOUNTS = {
    "SuperAdmin": "updadmin",
    "HR": "updhr",
    "Manager": "updmgr",
    "Associate": "updassoc",
}

print("=" * 68)
print("UPDATE SYSTEM SUITE")
print("=" * 68)

for role, username in ROLE_ACCOUNTS.items():
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.delete(existing)
db.commit()
for role, username in ROLE_ACCOUNTS.items():
    db.add(
        User(
            username=username,
            email=f"{username}@example.test",
            hashed_password=get_password_hash(PASSWORD),
            role=role,
            is_active=True,
            mfa_enabled=True,
        )
    )
db.commit()


def _reason(response) -> dict:
    """Unwrap the shared error envelope (error.details.reason) or plain detail."""
    try:
        payload = response.json()
    except Exception:  # noqa: BLE001
        return {}
    if isinstance(payload, dict):
        if isinstance(payload.get("detail"), dict):
            return payload["detail"]
        err = payload.get("error") or {}
        details = err.get("details") or {}
        if isinstance(details.get("reason"), dict):
            return details["reason"]
    return {}


def H(username: str) -> dict:
    tok = client.post(
        LOGIN, json={"username": username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


admin_headers = H("updadmin")

print("-- GET /current --")
r = client.get(f"{BASE}/current", headers=admin_headers)
check("SuperAdmin gets 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
body = r.json() if r.status_code == 200 else {}
for field in ("app_version", "project", "current_revision", "head_revision", "up_to_date"):
    check(f"current carries {field}", field in body, f"missing {field}")
check("project is LibrePeople", body.get("project") == "LibrePeople", f"got {body.get('project')}")

print("-- role gate --")
for role, username in (("HR", "updhr"), ("Manager", "updmgr"), ("Associate", "updassoc")):
    rr = client.get(f"{BASE}/current", headers=H(username))
    check(f"{role} refused with 403", rr.status_code == 403, f"got {rr.status_code}")
rr = client.get(f"{BASE}/current")
check("missing token is 401", rr.status_code == 401, f"got {rr.status_code}")

print("-- GET /available (local, verified) --")
r = client.get(f"{BASE}/available", headers=admin_headers)
check("available 200 for SuperAdmin", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
avail = r.json() if r.status_code == 200 else {}
check("manifest verified before display", avail.get("verified") is True, f"got {avail}")
check("dev-ephemeral flagged, never silent",
      avail.get("dev_signature") is True and bool(avail.get("dev_warning")),
      f"got {avail}")
remote = avail.get("remote") or {}
check("remote fetch disallowed by default (no egress)",
      remote.get("allowed") is False, f"got {remote}")
r = client.get(f"{BASE}/available", headers=H("updhr"))
check("available refuses HR with 403", r.status_code == 403, f"got {r.status_code}")

print("-- POST /check fail-closed (no backup arranged) --")
audit_before = db.query(AuditLog).count()
r = client.post(f"{BASE}/check", json={"dry_run": True}, headers=admin_headers)
check("check refuses with 409 when gates fail", r.status_code == 409,
      f"got {r.status_code}: {r.text[:300]}")
detail = _reason(r) if r.status_code == 409 else {}
gates = detail.get("gates") or []
check("gates list is returned", isinstance(gates, list) and len(gates) == 5,
      f"got {gates}")
names = {g.get("gate") for g in gates if isinstance(g, dict)}
for name in ("compat", "single_head", "disk_space", "backup_fresh", "migration_plan"):
    check(f"gate {name} present", name in names, f"got {names}")
backup_gate = next((g for g in gates if g.get("gate") == "backup_fresh"), {})
check("backup_fresh fails without arranged backup",
      backup_gate.get("passed") is False, f"got {backup_gate}")
check("backup_fresh names a remediation",
      bool(backup_gate.get("remediation")), f"got {backup_gate}")
db.expire_all()
check("check stages exactly one audit row",
      db.query(AuditLog).count() == audit_before + 1,
      f"{audit_before} -> {db.query(AuditLog).count()}")
single = next((g for g in gates if g.get("gate") == "single_head"), {})
check("single-head assert passes (linear history)",
      single.get("passed") is True, f"got {single}")

print("-- POST /install --")
r = client.post(f"{BASE}/install", json={"manifest_sha256": "0" * 64},
                headers=admin_headers)
check("wrong sha refused with 409", r.status_code == 409, f"got {r.status_code}")
manifest, load_error = updates.load_local_manifest()
check("local manifest loads", manifest is not None, f"{load_error}")
real_sha = (manifest or {}).get("manifest_sha256", "")
hist_before = len(updates.UPDATE_HISTORY)
r = client.post(f"{BASE}/install", json={"manifest_sha256": real_sha},
                headers=admin_headers)
check("gate-failing install refused with 409", r.status_code == 409,
      f"got {r.status_code}: {r.text[:300]}")
check("refused install is still recorded in history",
      len(updates.UPDATE_HISTORY) == hist_before + 1,
      f"{hist_before} -> {len(updates.UPDATE_HISTORY)}")
r = client.get(f"{BASE}/history", headers=admin_headers)
entries = (r.json() if r.status_code == 200 else {}).get("entries") or []
check("history lists the attempt", r.status_code == 200 and len(entries) >= 1,
      f"got {r.status_code}: {r.text[:200]}")
r = client.post(f"{BASE}/install", json={"manifest_sha256": real_sha},
                headers=H("updhr"))
check("install refuses HR with 403", r.status_code == 403, f"got {r.status_code}")

print("-- unit: checksum chain --")
tampered = dict(manifest or {})
tampered["changelog"] = "edited after signing"
verdict = updates.verify_manifest(tampered)
check("tampered manifest fails verification",
      verdict["ok"] is False
      and any("manifest_sha256" in reason for reason in verdict["reasons"]),
      f"got {verdict}")
check("untampered manifest verifies",
      updates.verify_manifest(manifest or {})["ok"] is True)
allowed, reason = updates.remote_fetch_allowed()
check("remote fetch off by default", allowed is False and bool(reason),
      f"got {allowed} {reason}")

print("=" * 68)
print(f"RESULT: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print("FAILURES:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
    raise SystemExit(1)
