"""SuperAdmin write-gate regression suite.

Pins the PATCH /api/v1/auth/users/{user_id} hardening:

* Every PATCH on a SuperAdmin target requires a SuperAdmin actor — not just
  role changes. An email-only or deactivate-only PATCH from HR is refused.
* The last active SuperAdmin cannot be demoted or deactivated (guard runs
  before commit, so the refused change is never persisted).
* Preserved paths: HR can still edit ordinary accounts, and a SuperAdmin can
  still edit (email / non-last demote / non-last deactivate) SuperAdmins.

Runs against a real FastAPI app and a real (temporary SQLite) database.
No mocks, no skips.

Run:  python superadmin_write_gate_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="superadmin_write_gate_"), "superadmin_write_gate.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["ENVIRONMENT"] = "development"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["LOGIN_RATE_LIMIT_ATTEMPTS"] = "1000"
os.environ["LOGIN_RATE_LIMIT_WINDOW_SECONDS"] = "300"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

PASSWORD = "WriteGate#2026x"
NEW_PW = "WriteGate#Fresh2026x"
USERS = {
    "wg_super": "SuperAdmin",
    "wg_hr": "HR",
    "wg_assoc": "Associate",
}

_db = SessionLocal()
for _name, _role in USERS.items():
    _existing = _db.query(User).filter(User.username == _name).first()
    if _existing:
        _db.delete(_existing)
_stale = _db.query(User).filter(User.username == "wg_super2").first()
if _stale:
    _db.delete(_stale)
_db.commit()
for _name, _role in USERS.items():
    _db.add(
        User(
            username=_name,
            email=f"{_name}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role=_role,
            is_active=True,
            mfa_enabled=True,
            must_change_password=False,
        )
    )
_db.commit()
_db.close()

client = TestClient(app)

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def login(username: str, password: str = PASSWORD) -> dict:
    r = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    if r.status_code != 200:
        raise SystemExit(f"setup: login failed for {username}: {r.status_code} {r.text[:200]}")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _user(username: str):
    sess = SessionLocal()
    try:
        return sess.query(User).filter(User.username == username).first()
    finally:
        sess.close()


def _user_id(username: str):
    u = _user(username)
    return u.id if u else None


HEADERS = {name: login(name) for name in USERS}

print("\n[WRITE-GATE] Every PATCH on a SuperAdmin target requires a SuperAdmin actor")

super_id = _user_id("wg_super")

# Unauthorised: HR email-only PATCH on a SuperAdmin (no role field at all).
r = client.patch(
    f"/api/v1/auth/users/{super_id}",
    headers=HEADERS["wg_hr"],
    json={"email": "hijacked@example.com"},
)
check("HR email-only PATCH on a SuperAdmin is refused", r.status_code == 403, f"got {r.status_code}")
check(
    "the refused email change was not persisted",
    _user("wg_super").email == "wg_super@example.com",
    f"email={_user('wg_super').email}",
)

# Unauthorised: HR deactivate-only PATCH on a SuperAdmin.
r = client.patch(
    f"/api/v1/auth/users/{super_id}",
    headers=HEADERS["wg_hr"],
    json={"is_active": False},
)
check("HR deactivate-only PATCH on a SuperAdmin is refused", r.status_code == 403, f"got {r.status_code}")
check(
    "the refused deactivation was not persisted",
    _user("wg_super").is_active is True,
    "wg_super is no longer active",
)

# Unauthorised: HR role PATCH on a SuperAdmin (previously covered, pinned here).
r = client.patch(
    f"/api/v1/auth/users/{super_id}",
    headers=HEADERS["wg_hr"],
    json={"role": "Associate"},
)
check("HR role PATCH on a SuperAdmin is refused", r.status_code == 403, f"got {r.status_code}")
check(
    "the refused demotion was not persisted",
    _user("wg_super").role == "SuperAdmin",
    f"role={_user('wg_super').role}",
)

# Preserved: HR can still edit an ordinary account.
assoc_id = _user_id("wg_assoc")
r = client.patch(
    f"/api/v1/auth/users/{assoc_id}",
    headers=HEADERS["wg_hr"],
    json={"email": "wg_assoc_new@example.com"},
)
check(
    "HR can still edit an ordinary account",
    r.status_code == 200 and _user("wg_assoc").email == "wg_assoc_new@example.com",
    f"got {r.status_code}: {r.text[:120]}",
)

print("\n[WRITE-GATE] SuperAdmin edits still work; last active SuperAdmin is protected")

# Setup: a second SuperAdmin owned by this suite.
r = client.post(
    "/api/v1/auth/users",
    headers=HEADERS["wg_super"],
    json={
        "user_in": {
            "username": "wg_super2",
            "email": "wg_super2@example.com",
            "password": NEW_PW,
            "role": "SuperAdmin",
            "is_active": True,
        }
    },
)
check("SuperAdmin can create a second SuperAdmin", r.status_code == 201, f"got {r.status_code}: {r.text[:120]}")
super2_id = _user_id("wg_super2")

# Preserved: SuperAdmin email-only edit on a SuperAdmin.
r = client.patch(
    f"/api/v1/auth/users/{super2_id}",
    headers=HEADERS["wg_super"],
    json={"email": "wg_super2_new@example.com"},
)
check(
    "SuperAdmin email edit on a SuperAdmin still works",
    r.status_code == 200 and _user("wg_super2").email == "wg_super2_new@example.com",
    f"got {r.status_code}: {r.text[:120]}",
)

# Preserved: SuperAdmin can deactivate a SuperAdmin while others remain.
r = client.patch(
    f"/api/v1/auth/users/{super2_id}",
    headers=HEADERS["wg_super"],
    json={"is_active": False},
)
check(
    "SuperAdmin can deactivate a non-last SuperAdmin",
    r.status_code == 200 and _user("wg_super2").is_active is False,
    f"got {r.status_code}: {r.text[:120]}",
)

# Guard skips accounts that are not active SuperAdmins: demoting the now
# inactive SuperAdmin is an ordinary edit, not a removal of the last one.
r = client.patch(
    f"/api/v1/auth/users/{super2_id}",
    headers=HEADERS["wg_super"],
    json={"role": "Associate"},
)
check(
    "SuperAdmin can demote an inactive SuperAdmin",
    r.status_code == 200 and _user("wg_super2").role == "Associate",
    f"got {r.status_code}: {r.text[:120]}",
)

# Guard: wg_super is now the sole active SuperAdmin — demoting it is refused
# before commit and nothing is persisted.
r = client.patch(
    f"/api/v1/auth/users/{super_id}",
    headers=HEADERS["wg_super"],
    json={"role": "HR"},
)
check("demoting the last active SuperAdmin is refused", r.status_code == 400, f"got {r.status_code}")
check(
    "the refused last-admin demotion was not persisted",
    _user("wg_super").role == "SuperAdmin",
    f"role={_user('wg_super').role}",
)

# Preserved: self-deactivation is still refused with the original message.
r = client.patch(
    f"/api/v1/auth/users/{super_id}",
    headers=HEADERS["wg_super"],
    json={"is_active": False},
)
check("a SuperAdmin still cannot deactivate their own account", r.status_code == 400, f"got {r.status_code}")
check(
    "the self-deactivation was not persisted",
    _user("wg_super").is_active is True,
    "wg_super is no longer active",
)

# Preserved: with two active SuperAdmins again, a non-last demote works.
r = client.patch(
    f"/api/v1/auth/users/{super2_id}",
    headers=HEADERS["wg_super"],
    json={"role": "SuperAdmin", "is_active": True},
)
check("SuperAdmin can restore a second active SuperAdmin", r.status_code == 200, f"got {r.status_code}: {r.text[:120]}")
r = client.patch(
    f"/api/v1/auth/users/{super2_id}",
    headers=HEADERS["wg_super"],
    json={"role": "Associate"},
)
check(
    "SuperAdmin can demote a non-last SuperAdmin",
    r.status_code == 200 and _user("wg_super2").role == "Associate",
    f"got {r.status_code}: {r.text[:120]}",
)
check(
    "the surviving SuperAdmin is untouched",
    _user("wg_super").role == "SuperAdmin" and _user("wg_super").is_active is True,
    f"role={_user('wg_super').role} active={_user('wg_super').is_active}",
)


# ===========================================================================
print(f"\n{'=' * 60}")
total = RESULTS["pass"] + RESULTS["fail"]
print(f"==== SUPERADMIN WRITE GATE SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed of {total} ====")
if FAILURES:
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 60)
raise SystemExit(0 if RESULTS["fail"] == 0 else 1)
