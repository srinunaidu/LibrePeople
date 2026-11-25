"""Admin MFA reset suite (strict defaults).

Covers POST /api/v1/auth/mfa/reset on a real FastAPI app + real database:

* Step-up is password AND TOTP together (both required, neither alone).
* SuperAdmin-only: HR (and every other role) is refused by the role gate.
* No self-reset: an actor cannot reset their own MFA; a second
  SuperAdmin is required.
* No break-glass bypass: a break-glass grant never authorizes a reset.
* No secrets in the audit trail (success or blocked rows).
* The target re-enrolls through the existing self-service flow
  (enroll -> confirm) after a reset.
* The all-SuperAdmins-lost emergency stays an OPEN owner decision: the
  endpoint documents it and defines no offline bypass.

Checks:

* (a) a SuperAdmin with password AND TOTP resets an enrolled target;
  the target's sessions end and the target re-enrolls via enroll+confirm.
* (b) HR cannot reset anyone (403, shared envelope).
* (c) self-reset is refused (second SuperAdmin required).
* (d) a call with no step-up proof is refused with 403 step_up_required.
* (e) password alone (no TOTP) is refused — AND, not OR.
* (f) TOTP alone (no password), and a wrong TOTP with the right
  password, are refused.
* (g) the mfa_reset / mfa_reset_blocked audit rows carry no secrets,
  break-glass is not wired into the endpoint, and the OPEN owner
  decision for all-SuperAdmins-lost is recorded on the endpoint.

Run:  python admin_mfa_reset_test_suite.py
"""
import inspect
import os
import tempfile
import urllib.parse

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="admin_mfa_reset_"), "reset_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

import pyotp  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.mfa import generate_totp_secret  # noqa: E402
from app.core.security import encrypt_secret, get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

ADMIN1_PASSWORD = "ResetAdminPass123!"
ADMIN2_PASSWORD = "ResetAdminTwo123!"
HR_PASSWORD = "ResetHrPass12345!"
TARGET_PASSWORD = "ResetTargetPass123!"

_admin1_secret = generate_totp_secret()

db = SessionLocal()
db.add(User(
    username="reset_admin", email="reset_admin@example.test",
    hashed_password=get_password_hash(ADMIN1_PASSWORD),
    role="SuperAdmin", is_active=True,
    mfa_enabled=True, mfa_secret_hash=encrypt_secret(_admin1_secret),
))
db.add(User(
    username="reset_admin2", email="reset_admin2@example.test",
    hashed_password=get_password_hash(ADMIN2_PASSWORD),
    role="SuperAdmin", is_active=True, mfa_enabled=True,
))
db.add(User(
    username="reset_hr", email="reset_hr@example.test",
    hashed_password=get_password_hash(HR_PASSWORD),
    role="HR", is_active=True, mfa_enabled=True,
))
db.add(User(
    username="reset_target", email="reset_target@example.test",
    hashed_password=get_password_hash(TARGET_PASSWORD),
    role="HR", is_active=True, mfa_enabled=True,
))
db.commit()
db.close()

client = TestClient(app, raise_server_exceptions=False)

API = "/api/v1"


def api(path: str) -> str:
    return f"{API}{path}"


def login(username: str, password: str):
    return client.post(api("/auth/login"), json={"username": username, "password": password})


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


print("=" * 68)
print("ADMIN MFA RESET SUITE")
print("=" * 68)

r = login("reset_admin", ADMIN1_PASSWORD)
assert r.status_code == 200, f"admin login failed: {r.text}"
H1 = {"Authorization": f"Bearer {r.json()['access_token']}"}

r = login("reset_admin2", ADMIN2_PASSWORD)
assert r.status_code == 200, f"second admin login failed: {r.text}"
H2 = {"Authorization": f"Bearer {r.json()['access_token']}"}

r = login("reset_hr", HR_PASSWORD)
assert r.status_code == 200, f"hr login failed: {r.text}"
HR_H = {"Authorization": f"Bearer {r.json()['access_token']}"}

# A live session for the target, so (a) can prove the reset ends it.
r = login("reset_target", TARGET_PASSWORD)
assert r.status_code == 200, f"target login failed: {r.text}"
_target_refresh = r.json()["refresh_token"]
T_H = {"Authorization": f"Bearer {r.json()['access_token']}"}

# --- (a) success: password AND TOTP resets the target ---------------------
_good_totp = pyotp.TOTP(_admin1_secret).now()
r = client.post(
    api("/auth/mfa/reset"),
    headers=H1,
    json={
        "target_username": "reset_target",
        "current_password": ADMIN1_PASSWORD,
        "totp_code": _good_totp,
    },
)
check(
    "(a) SuperAdmin with password AND TOTP resets the target (200)",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:140]}",
)

sess = SessionLocal()
_target = sess.query(User).filter(User.username == "reset_target").first()
sess.close()
check(
    "(a) the target's MFA state is cleared",
    _target is not None and not _target.mfa_enabled
    and _target.mfa_secret_hash is None
    and _target.recovery_codes_hash is None,
    f"mfa_enabled={getattr(_target, 'mfa_enabled', '?')}",
)

r = client.get(api("/auth/mfa/status"), headers=T_H)
check(
    "(a) the target reports mfa_enabled=false after the reset",
    r.status_code == 200 and r.json()["mfa_enabled"] is False,
    f"got {r.status_code}: {r.text[:120]}",
)

r = client.post(api("/auth/refresh"), json={"refresh_token": _target_refresh})
check(
    "(a) the target's pre-reset session no longer refreshes",
    r.status_code in (401, 403),
    f"got {r.status_code}: {r.text[:120]}",
)

# The target re-enrolls through the existing self-service flow.
r = login("reset_target", TARGET_PASSWORD)
T_H = {"Authorization": f"Bearer {r.json()['access_token']}"} if r.status_code == 200 else {}
check(
    "(a) the target can still sign in with the password after the reset",
    bool(T_H),
    f"got {r.status_code}: {r.text[:120]}",
)
r = client.post(api("/auth/mfa/enroll"), headers=T_H)
_new_secret = None
if r.status_code == 200:
    _parsed = urllib.parse.urlparse(r.json().get("provisioning_uri", ""))
    _new_secret = urllib.parse.parse_qs(_parsed.query).get("secret", [None])[0]
check(
    "(a) the reset target re-enrolls via POST /auth/mfa/enroll",
    r.status_code == 200 and bool(_new_secret),
    f"got {r.status_code}: {r.text[:120]}",
)
if _new_secret:
    r = client.post(
        api("/auth/mfa/confirm"),
        headers=T_H,
        json={"totp_code": pyotp.TOTP(_new_secret).now()},
    )
    check(
        "(a) the reset target confirms via POST /auth/mfa/confirm",
        r.status_code == 200,
        f"got {r.status_code}: {r.text[:120]}",
    )

# --- (b) HR cannot reset anyone -------------------------------------------
_good_totp = pyotp.TOTP(_admin1_secret).now()
r = client.post(
    api("/auth/mfa/reset"),
    headers=HR_H,
    json={
        "target_username": "reset_admin2",
        "current_password": HR_PASSWORD,
        "totp_code": _good_totp,
    },
)
check(
    "(b) HR is refused with the shared envelope (SuperAdmin-only)",
    r.status_code == 403 and "forbidden" in r.text,
    f"got {r.status_code}: {r.text[:140]}",
)

# --- (c) no self-reset ------------------------------------------------------
_good_totp = pyotp.TOTP(_admin1_secret).now()
r = client.post(
    api("/auth/mfa/reset"),
    headers=H1,
    json={
        "target_username": "reset_admin",
        "current_password": ADMIN1_PASSWORD,
        "totp_code": _good_totp,
    },
)
check(
    "(c) self-reset is refused (second SuperAdmin required)",
    r.status_code == 403 and "self_reset_not_allowed" in r.text,
    f"got {r.status_code}: {r.text[:140]}",
)
check(
    "the refusal body does not echo the supplied password",
    ADMIN1_PASSWORD not in r.text,
    f"body={r.text[:140]}",
)

# --- (d) no step-up proof ---------------------------------------------------
r = client.post(
    api("/auth/mfa/reset"),
    headers=H1,
    json={"target_username": "reset_admin2"},
)
check(
    "(d) reset with no step-up proof is refused with 403 step_up_required",
    r.status_code == 403 and "step_up_required" in r.text,
    f"got {r.status_code}: {r.text[:140]}",
)

# --- (e) password alone is not enough ---------------------------------------
r = client.post(
    api("/auth/mfa/reset"),
    headers=H1,
    json={
        "target_username": "reset_admin2",
        "current_password": ADMIN1_PASSWORD,
    },
)
check(
    "(e) reset with the password alone is refused (AND, not OR)",
    r.status_code == 403 and "step_up_required" in r.text,
    f"got {r.status_code}: {r.text[:140]}",
)

# --- (f) TOTP alone / wrong TOTP --------------------------------------------
_good_totp = pyotp.TOTP(_admin1_secret).now()
r = client.post(
    api("/auth/mfa/reset"),
    headers=H1,
    json={"target_username": "reset_admin2", "totp_code": _good_totp},
)
check(
    "(f) reset with a TOTP code alone is refused",
    r.status_code == 403 and "step_up_required" in r.text,
    f"got {r.status_code}: {r.text[:140]}",
)
r = client.post(
    api("/auth/mfa/reset"),
    headers=H1,
    json={
        "target_username": "reset_admin2",
        "current_password": ADMIN1_PASSWORD,
        "totp_code": "000000",
    },
)
check(
    "(f) reset with the right password but a wrong TOTP is refused",
    r.status_code == 403 and "step_up_required" in r.text,
    f"got {r.status_code}: {r.text[:140]}",
)
check(
    "the refusal body does not echo the supplied password",
    ADMIN1_PASSWORD not in r.text,
    f"body={r.text[:140]}",
)

# Blocked attempts must not have touched the second admin's enrollment.
r = client.get(api("/auth/mfa/status"), headers=H2)
check(
    "blocked resets leave the untouched account still enrolled",
    r.status_code == 200 and r.json()["mfa_enabled"] is True,
    f"got {r.status_code}: {r.text[:120]}",
)

# --- (g) audit without secrets, no break-glass, OPEN decision ---------------
sess = SessionLocal()
try:
    _reset_row = (
        sess.query(AuditLog)
        .filter(AuditLog.action == "mfa_reset")
        .order_by(AuditLog.id.desc())
        .first()
    )
    _blocked_rows = (
        sess.query(AuditLog)
        .filter(AuditLog.action == "mfa_reset_blocked")
        .order_by(AuditLog.id.desc())
        .limit(10)
        .all()
    )
finally:
    sess.close()

check(
    "(g) a successful reset writes an mfa_reset audit row",
    _reset_row is not None,
    "no mfa_reset row found",
)
if _reset_row is not None:
    _details = _reset_row.details or ""
    check(
        "the mfa_reset row carries no secrets",
        ADMIN1_PASSWORD not in _details
        and _admin1_secret not in _details
        and "totp" not in _details.lower(),
        f"details={_details[:160]}",
    )

check(
    "(g) blocked resets write mfa_reset_blocked audit rows",
    len(_blocked_rows) > 0,
    "no mfa_reset_blocked rows found",
)
_leak = False
for _row in _blocked_rows:
    _d = _row.details or ""
    if ADMIN1_PASSWORD in _d or _admin1_secret in _d or "totp" in _d.lower():
        _leak = True
check(
    "the blocked rows carry no secrets",
    not _leak,
    "a blocked row carried a secret",
)

from app.api.v1.endpoints.auth import admin_mfa_reset as _reset_fn  # noqa: E402

_source = inspect.getsource(_reset_fn)
check(
    "(g) break-glass is not wired into the reset (no bypass)",
    "require_break_glass" not in _source,
    "the endpoint references require_break_glass",
)
check(
    "(g) all-SuperAdmins-lost stays an OPEN owner decision, not an offline bypass",
    "OPEN" in (_reset_fn.__doc__ or ""),
    "the endpoint docstring does not record the OPEN decision",
)

print()
print("=" * 68)
print(f"ADMIN MFA RESET SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print()
    print("Failures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
