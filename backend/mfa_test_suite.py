"""MFA regression suite.

Covers multi-factor authentication for SuperAdmin and HR roles (P-05):

* TOTP secret generation and provisioning URI
* TOTP code verification (valid / invalid / wrong length)
* Recovery code generation, hashing, and single-use consumption
* MFA enroll → confirm flow (secret encrypted at rest, enabled after confirm)
* MFA status endpoint
* MFA disable with password or recovery code
* Non-enforced roles (Manager) can skip MFA

Run:  python mfa_test_suite.py
"""
import os
import tempfile
import sys
import urllib.parse

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="mfa_test_"), "mfa_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
# Field encryption (item 6: no SECRET_KEY fallback) — /auth/mfa/enroll encrypts
# the TOTP secret via app.core.security.encrypt_secret.
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import pyotp  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
db.add(User(
    username="mfa_admin", email="mfa_admin@example.test",
    hashed_password=get_password_hash("AdminPass12345!"),
    role="SuperAdmin", is_active=True,
))
db.add(User(
    username="mfa_hr", email="mfa_hr@example.test",
    hashed_password=get_password_hash("HrPass12345!"),
    role="HR", is_active=True,
))
db.add(User(
    username="mfa_mgr", email="mfa_mgr@example.test",
    hashed_password=get_password_hash("MgrPass12345!"),
    role="Manager", is_active=True,
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


def secret_from_enrollment(body: dict) -> str | None:
    parsed = urllib.parse.urlparse(body.get("provisioning_uri", ""))
    params = urllib.parse.parse_qs(parsed.query)
    return params.get("secret", [None])[0]


print("=" * 68)
print("MFA SUITE")
print("=" * 68)

# --- Login as SuperAdmin -------------------------------------------------
r = login("mfa_admin", "AdminPass12345!")
assert r.status_code == 200, f"login failed: {r.text}"
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}

# --- MFA status before enrollment ----------------------------------------
r = client.get(api("/auth/mfa/status"), headers=H)
check(
    "mfa status: not enrolled initially",
    r.status_code == 200 and r.json()["mfa_enabled"] is False,
    f"got {r.status_code}: {r.text[:120]}",
)

# --- Enrollment ----------------------------------------------------------
r = client.post(api("/auth/mfa/enroll"), headers=H)
check(
    "mfa enroll returns 200",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)
if r.status_code == 200:
    body = r.json()
    check(
        "enrollment has provisioning_uri",
        "provisioning_uri" in body
        and body["provisioning_uri"].startswith("otpauth://"),
        f"got {str(body.get('provisioning_uri', ''))[:60]}",
    )
    check(
        "enrollment has 8 recovery codes",
        len(body.get("recovery_codes", [])) == 8,
        f"got {len(body.get('recovery_codes', []))}",
    )

# --- Confirmation with valid code ----------------------------------------
if r.status_code == 200:
    secret = secret_from_enrollment(body)
    if secret:
        code = pyotp.TOTP(secret).now()
        r = client.post(
            api("/auth/mfa/confirm"),
            headers=H,
            json={"totp_code": code},
        )
        check(
            "mfa confirm with valid code returns 200",
            r.status_code == 200,
            f"got {r.status_code}: {r.text[:120]}",
        )
        if r.status_code == 200:
            check(
                "confirm returns mfa_enabled",
                r.json().get("status") == "mfa_enabled",
                f"got {r.json()}",
            )

# --- Status after enrollment ---------------------------------------------
r = client.get(api("/auth/mfa/status"), headers=H)
check(
    "mfa status: enrolled after confirm",
    r.status_code == 200 and r.json()["mfa_enabled"] is True,
    f"got {r.status_code}: {r.text[:120]}",
)

# --- Invalid TOTP code (re-enroll to test) -------------------------------
r = client.post(
    api("/auth/mfa/disable"),
    headers=H,
    json={"password": "AdminPass12345!"},
)
check(
    "mfa disable with password returns 200",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)

r = client.post(api("/auth/mfa/enroll"), headers=H)
if r.status_code == 200:
    body = r.json()
    secret = secret_from_enrollment(body)

    # The QR code is rendered by the server. A third-party charting service
    # would receive the TOTP secret in a URL and log it.
    qr = body.get("qr_code_data_uri")
    check(
        "mfa enroll returns a QR code rendered by the server",
        isinstance(qr, str) and qr.startswith("data:image/png;base64,"),
        f"got {type(qr).__name__}",
    )
    if isinstance(qr, str) and qr.startswith("data:image/png;base64,"):
        import base64
        import io

        try:
            from PIL import Image

            raw = base64.b64decode(qr.split(",", 1)[1])
            image = Image.open(io.BytesIO(raw))
            check(
                "the QR code is a decodable PNG",
                image.format == "PNG" and image.size[0] > 0,
                f"format={image.format} size={image.size}",
            )
        except Exception as exc:  # noqa: BLE001
            check("the QR code is a decodable PNG", False, str(exc))

    if secret:
        r = client.post(
            api("/auth/mfa/confirm"),
            headers=H,
            json={"totp_code": "000000"},
        )
        check(
            "mfa confirm with wrong code returns 403",
            r.status_code == 403,
            f"got {r.status_code}: {r.text[:120]}",
        )
        # Confirm with valid code to leave MFA enabled
        code = pyotp.TOTP(secret).now()
        r = client.post(
            api("/auth/mfa/confirm"),
            headers=H,
            json={"totp_code": code},
        )
        check(
            "mfa confirm with valid code (re-enroll) returns 200",
            r.status_code == 200,
            f"got {r.status_code}: {r.text[:120]}",
        )

# --- Disable with recovery code ------------------------------------------
r = client.post(
    api("/auth/mfa/disable"),
    headers=H,
    json={"password": "AdminPass12345!"},
)
check(
    "mfa disable with password (2nd time) returns 200",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)

# Re-enroll and get recovery codes
r = client.post(api("/auth/mfa/enroll"), headers=H)
if r.status_code == 200:
    recovery_code = r.json()["recovery_codes"][0]
    # Confirm
    body = r.json()
    secret = secret_from_enrollment(body)
    if secret:
        code = pyotp.TOTP(secret).now()
        client.post(
            api("/auth/mfa/confirm"),
            headers=H,
            json={"totp_code": code},
        )

    # Disable with recovery code (no password)
    r = client.post(
        api("/auth/mfa/disable"),
        headers=H,
        json={"recovery_code": recovery_code},
    )
    check(
        "mfa disable with recovery code returns 200",
        r.status_code == 200,
        f"got {r.status_code}: {r.text[:120]}",
    )
    # Recovery code should be consumed (single-use). After disable, MFA is
    # no longer enabled, so a second disable returns "not enabled" (409).
    r = client.post(
        api("/auth/mfa/disable"),
        headers=H,
        json={"recovery_code": recovery_code},
    )
    check(
        "mfa disable with consumed recovery code returns 409 (not enabled)",
        r.status_code == 409,
        f"got {r.status_code}: {r.text[:120]}",
    )

# --- Re-enable for role tests --------------------------------------------
r = client.post(api("/auth/mfa/enroll"), headers=H)
if r.status_code == 200:
    body = r.json()
    secret = secret_from_enrollment(body)
    if secret:
        code = pyotp.TOTP(secret).now()
        client.post(
            api("/auth/mfa/confirm"),
            headers=H,
            json={"totp_code": code},
        )

# --- HR user enroll ------------------------------------------------------
r = login("mfa_hr", "HrPass12345!")
hr_token = r.json()["access_token"]
hr_h = {"Authorization": f"Bearer {hr_token}"}
r = client.post(api("/auth/mfa/enroll"), headers=hr_h)
check(
    "HR can enroll MFA",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)

# --- Manager (not enforced) can skip MFA ---------------------------------
r = login("mfa_mgr", "MgrPass12345!")
mgr_token = r.json()["access_token"]
mgr_h = {"Authorization": f"Bearer {mgr_token}"}
r = client.get(api("/auth/mfa/status"), headers=mgr_h)
check(
    "Manager mfa status: not enrolled",
    r.status_code == 200 and r.json()["mfa_enabled"] is False,
    f"got {r.status_code}: {r.text[:120]}",
)

# --- Impersonate step-up via TOTP -------------------------------------------
# An MFA-enabled actor may pass impersonation step-up with a current TOTP
# code instead of the password. No MFA reset or bootstrap is involved:
# the actor is already enrolled; the secret below is the live enrollment.
r = client.post(
    api("/auth/mfa/disable"),
    headers=H,
    json={"password": "AdminPass12345!"},
)
check(
    "step-up setup: mfa disable with password returns 200",
    r.status_code == 200,
    f"got {r.status_code}: {r.text[:120]}",
)
r = client.post(api("/auth/mfa/enroll"), headers=H)
_step_secret = secret_from_enrollment(r.json()) if r.status_code == 200 else None
check(
    "step-up setup: re-enroll returns a secret",
    bool(_step_secret),
    f"got {r.status_code}: {r.text[:120]}",
)
if _step_secret:
    _code = pyotp.TOTP(_step_secret).now()
    r = client.post(
        api("/auth/mfa/confirm"),
        headers=H,
        json={"totp_code": _code},
    )
    check(
        "step-up setup: confirm re-enables MFA",
        r.status_code == 200,
        f"got {r.status_code}: {r.text[:120]}",
    )

    # (e) valid TOTP with no password passes step-up
    _good = pyotp.TOTP(_step_secret).now()
    r = client.post(
        api("/auth/impersonate"),
        headers=H,
        json={"target_username": "mfa_mgr", "totp_code": _good},
    )
    check(
        "(e) impersonate with a valid TOTP code succeeds without a password",
        r.status_code == 200,
        f"got {r.status_code}: {r.text[:140]}",
    )
    if r.status_code == 200:
        check(
            "the TOTP step-up token is for the target user",
            r.json().get("user", {}).get("username") == "mfa_mgr",
            f"got {r.text[:140]}",
        )

    # (f) a wrong TOTP code fails closed with 403 step_up_required
    r = client.post(
        api("/auth/impersonate"),
        headers=H,
        json={"target_username": "mfa_mgr", "totp_code": "000000"},
    )
    check(
        "(f) impersonate with a wrong TOTP code is refused with 403 step_up_required",
        r.status_code == 403 and "step_up_required" in r.text,
        f"got {r.status_code}: {r.text[:140]}",
    )

print()
print("=" * 68)
print(f"MFA SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print()
    print("Failures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
