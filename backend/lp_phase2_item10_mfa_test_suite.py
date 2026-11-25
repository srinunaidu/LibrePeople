"""LibrePeople Phase 2, item 10: MFA enforcement for SuperAdmin and HR.

Unenrolled privileged users may reach only the MFA escape-hatch endpoints.

Checks:

* Unauthenticated request: 401.
* Unenrolled SuperAdmin: privileged endpoints (GET /api/v1/auth/users)
  return 403 naming the MFA requirement.
* Unenrolled HR: privileged endpoints return 403.
* Unenrolled SuperAdmin reaches the escape hatch: GET /auth/mfa/status,
  GET /auth/me, POST /auth/mfa/enroll.
* Enrolled SuperAdmin: privileged endpoints are reachable (200).
* The flow works end to end: enroll -> confirm -> privileged endpoints 200.
* Manager is not enforced: an unenrolled Manager reaches privileged
  endpoints (GET /api/v1/employees/).

Run:  python lp_phase2_item10_mfa_test_suite.py
"""
import os
import tempfile
import urllib.parse
from datetime import datetime, timezone

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="lp_mfa10_"), "mfa10_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

from fastapi.testclient import TestClient  # noqa: E402
import pyotp  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()
PASSWORD = "AdminPass12345!"
db.add(User(username="sa_unenrolled", email="sa_unenrolled@example.test",
            hashed_password=get_password_hash(PASSWORD), role="SuperAdmin",
            is_active=True, password_changed_at=datetime.now(timezone.utc)))
db.add(User(username="hr_unenrolled", email="hr_unenrolled@example.test",
            hashed_password=get_password_hash(PASSWORD), role="HR",
            is_active=True, password_changed_at=datetime.now(timezone.utc)))
db.add(User(username="sa_enrolled", email="sa_enrolled@example.test",
            hashed_password=get_password_hash(PASSWORD), role="SuperAdmin",
            is_active=True, mfa_enabled=True,
            password_changed_at=datetime.now(timezone.utc)))
db.add(User(username="mgr_unenrolled", email="mgr_unenrolled@example.test",
            hashed_password=get_password_hash(PASSWORD), role="Manager",
            is_active=True, password_changed_at=datetime.now(timezone.utc)))
db.commit()
db.close()

client = TestClient(app)
_PASS, _FAIL = [], []


def check(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        _FAIL.append((name, exc))
        print(f"FAIL  {name}: {exc!r}")
    else:
        _PASS.append(name)
        print(f"PASS  {name}")


def api(path):
    return f"/api/v1{path}"


def _login(username):
    r = client.post(api("/auth/login"), json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, f"login failed for {username}: {r.text[:200]}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _privileged(headers):
    r = client.get(api("/auth/users"), headers=headers)
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"
    assert "Multi-factor authentication is required" in r.text, r.text[:200]


def _secret_from_enrollment(body):
    parsed = urllib.parse.urlparse(body.get("provisioning_uri", ""))
    return urllib.parse.parse_qs(parsed.query).get("secret", [None])[0]


def test_unauthenticated_is_401():
    r = client.get(api("/auth/users"))
    assert r.status_code == 401, r.status_code


def test_unenrolled_superadmin_blocked_on_privileged():
    _privileged(_login("sa_unenrolled"))


def test_unenrolled_hr_blocked_on_privileged():
    _privileged(_login("hr_unenrolled"))


def test_unenrolled_superadmin_reaches_escape_hatch():
    H = _login("sa_unenrolled")
    r = client.get(api("/auth/mfa/status"), headers=H)
    assert r.status_code == 200, r.text
    assert r.json()["mfa_enabled"] is False
    r = client.get(api("/auth/me"), headers=H)
    assert r.status_code == 200, r.text
    r = client.post(api("/auth/mfa/enroll"), headers=H)
    assert r.status_code == 200, r.text[:200]
    assert "provisioning_uri" in r.json()


def test_enroll_confirm_then_privileged_reachable():
    H = _login("sa_unenrolled")
    r = client.post(api("/auth/mfa/enroll"), headers=H)
    assert r.status_code == 200, r.text[:200]
    secret = _secret_from_enrollment(r.json())
    assert secret, r.json()
    code = pyotp.TOTP(secret).now()
    r = client.post(api("/auth/mfa/confirm"), headers=H, json={"totp_code": code})
    assert r.status_code == 200, r.text[:200]
    assert r.json().get("status") == "mfa_enabled"
    r = client.get(api("/auth/users"), headers=H)
    assert r.status_code == 200, f"privileged endpoint must be reachable after enroll+confirm: {r.text[:200]}"
    r = client.get(api("/auth/mfa/status"), headers=H)
    assert r.json()["mfa_enabled"] is True


def test_enrolled_superadmin_reachable():
    r = client.get(api("/auth/users"), headers=_login("sa_enrolled"))
    assert r.status_code == 200, r.text[:200]


def test_manager_not_enforced():
    r = client.get(api("/employees/"), headers=_login("mgr_unenrolled"))
    assert r.status_code == 200, r.text[:200]


def main():
    for name, fn in [
        ("unauthenticated request returns 401", test_unauthenticated_is_401),
        ("unenrolled SuperAdmin blocked on privileged endpoints (unauthorised path)",
         test_unenrolled_superadmin_blocked_on_privileged),
        ("unenrolled HR blocked on privileged endpoints (unauthorised path)",
         test_unenrolled_hr_blocked_on_privileged),
        ("unenrolled SuperAdmin reaches MFA escape-hatch endpoints",
         test_unenrolled_superadmin_reaches_escape_hatch),
        ("enroll + confirm unlocks privileged endpoints (authorized path)",
         test_enroll_confirm_then_privileged_reachable),
        ("enrolled SuperAdmin reaches privileged endpoints",
         test_enrolled_superadmin_reachable),
        ("Manager is not MFA-enforced", test_manager_not_enforced),
    ]:
        check(name, fn)
    print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
    for name, exc in _FAIL:
        print(f"FAIL  {name}: {exc!r}")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    import sys

    main()
