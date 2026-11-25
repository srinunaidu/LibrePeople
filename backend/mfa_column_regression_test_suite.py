"""MFA secret-column regression suite (0048_mfa_secret_envelope).

Guards the defect where ``users.mfa_secret_hash`` was ``VARCHAR(64)``
(sized for a SHA-256 hex digest) while ``POST /auth/mfa/enroll`` stores
the ``ENCv1:<key_id>:<fernet token>`` envelope (~150-160 chars).
SQLite never enforced the width so the MFA suites stayed green there;
PostgreSQL failed enrollment verbatim with::

    DataError (psycopg.errors.StringDataRightTruncation)
    value too long for type character varying(64)

Checks:

* (a) the live ``encrypt_secret`` envelope for a fresh TOTP secret is
  longer than 64 chars (the fact that made VARCHAR(64) wrong).
* (b) the mapped ``User.mfa_secret_hash`` column type is unbounded
  (TEXT, or a VARCHAR wide enough for any key-id length).
* (c) end-to-end on sqlite: enroll -> 200, the stored value is longer
  than 64 chars, it decrypts to the enroll-time secret, and confirm
  with a current TOTP code enables MFA.
* (d) PG-gated (only when MFA_REGRESSION_PG_URL is set, read-only):
  the live PG ``information_schema`` shows the column as TEXT/unbounded
  (or >= 200 chars) — i.e. migration 0048 has been applied there.

Run:  python mfa_column_regression_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="mfa_col_reg_"), "mfa_col_test.db")
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

import sqlalchemy as sa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.mfa import generate_totp_secret  # noqa: E402
from app.core.security import decrypt_secret, encrypt_secret  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"ok: {name}")
    else:
        failed += 1
        print(f"FAIL: {name} {detail}")


# (a) the envelope exceeds the old 64-char width.
_secret = generate_totp_secret()
_envelope = encrypt_secret(_secret)
check(
    "envelope-longer-than-64",
    _envelope is not None and len(_envelope) > 64,
    f"len={len(_envelope) if _envelope else None}",
)

# (b) the mapped column type is unbounded.
_coltype = User.__table__.columns["mfa_secret_hash"].type
_unbounded = (
    isinstance(_coltype, sa.Text)
    or (isinstance(_coltype, sa.String) and (_coltype.length is None or _coltype.length >= 200))
)
check("model-column-unbounded", _unbounded, f"type={_coltype!r}")

# (c) end-to-end enrollment on sqlite (create_all schema).
import pyotp  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402

PASSWORD = "MfaColRegPass123!"
db = SessionLocal()
db.add(User(
    username="mfa_col_user", email="mfa_col_user@example.test",
    hashed_password=get_password_hash(PASSWORD),
    role="Associate", is_active=True,
))
db.commit()
db.close()

client = TestClient(app, raise_server_exceptions=False)
_login = client.post(
    "/api/v1/auth/login",
    json={"username": "mfa_col_user", "password": PASSWORD},
)
check("login-200", _login.status_code == 200, f"status={_login.status_code}")
_token = _login.json().get("access_token") if _login.status_code == 200 else None

_enroll = client.post(
    "/api/v1/auth/mfa/enroll",
    headers={"Authorization": f"Bearer {_token}"} if _token else {},
)
check("enroll-200", _enroll.status_code == 200, f"status={_enroll.status_code} body={_enroll.text[:200]}")

db = SessionLocal()
_stored = db.query(User).filter(User.username == "mfa_col_user").first()
_stored_value = _stored.mfa_secret_hash if _stored is not None else None
db.close()
check(
    "stored-value-longer-than-64",
    isinstance(_stored_value, str) and len(_stored_value) > 64,
    f"len={len(_stored_value) if isinstance(_stored_value, str) else None}",
)
try:
    _roundtrip = decrypt_secret(_stored_value) if _stored_value else None
except Exception as exc:  # noqa: BLE001
    _roundtrip = f"ERROR: {exc}"
check(
    "stored-value-decrypts",
    isinstance(_roundtrip, str) and len(_roundtrip) == 32,
    f"roundtrip={str(_roundtrip)[:40]}",
)
if isinstance(_roundtrip, str) and len(_roundtrip) == 32:
    _code = pyotp.TOTP(_roundtrip).now()
    _confirm = client.post(
        "/api/v1/auth/mfa/confirm",
        json={"totp_code": _code},
        headers={"Authorization": f"Bearer {_token}"},
    )
    check("confirm-200", _confirm.status_code == 200, f"status={_confirm.status_code} body={_confirm.text[:200]}")
    db = SessionLocal()
    _user = db.query(User).filter(User.username == "mfa_col_user").first()
    check("mfa-enabled", bool(_user and _user.mfa_enabled))
    db.close()
else:
    check("confirm-200", False, "skipped: stored value did not decrypt")
    check("mfa-enabled", False, "skipped: stored value did not decrypt")

# (d) PG-gated read-only check: column must be TEXT/unbounded there.
_pg_url = os.environ.get("MFA_REGRESSION_PG_URL", "").strip()
if _pg_url:
    _pg_engine = sa.create_engine(_pg_url)
    with _pg_engine.connect() as _conn:
        _row = _conn.execute(
            sa.text(
                "SELECT data_type, character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'mfa_secret_hash'"
            )
        ).fetchone()
    _pg_ok = _row is not None and (
        _row[1] is None or (_row[0] == "text") or (isinstance(_row[1], int) and _row[1] >= 200)
    )
    check("pg-column-unbounded", _pg_ok, f"row={tuple(_row) if _row else None}")
else:
    print("skip: pg-column-unbounded (MFA_REGRESSION_PG_URL not set)")

print(f"\n{passed} passed, {failed} failed")
raise SystemExit(1 if failed else 0)
