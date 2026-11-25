"""The audit trail: same transaction, source address, the two missing events.

What this suite proves
----------------------
The audit trail is the evidence base for every other claim the product makes,
so it cannot be the first place a false statement enters. This suite pins the
four gaps the DEC-000 trail review found:

* **Same transaction.** A row staged with a mutation is committed with it and
  disappears when the mutation is rolled back.
* **Source address.** Every row written during a request carries the SHA-256
  of the client address, matching the refresh-token convention; the raw
  address is never stored; two requests from one address carry one digest.
* **The lockout transition.** The attempt that locks an account writes a
  `login_locked` row at the moment of the transition, not only on the next
  attempt.
* **An unknown username.** A failed sign-in against a name that does not
  exist writes a row that names no username and confirms nothing to the
  caller.
* **No sensitive value in `details`.** A salary, a bank detail, a national
  identifier, a date of birth or a card number is redacted before it reaches
  the column.
* **A denied request writes no audit row** (DEC-031); the refusal is in the
  request log.

Run:  python audit_test_suite.py
"""
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(
    tempfile.mkdtemp(prefix="audit_test_suite_"), "audit_test_suite.db"
)
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["LOGIN_RATE_LIMIT_ATTEMPTS"] = "1000"
os.environ["LOGIN_RATE_LIMIT_WINDOW_SECONDS"] = "300"
os.environ["LOGIN_MAX_FAILED_ATTEMPTS"] = "10"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.audit import record_audit, redact_details  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list[tuple[str, str]] = []

ADMIN = "audit_admin"
ADMIN_PASSWORD = "AuditAdminPass123"
ASSOCIATE = "audit_associate"
ASSOCIATE_PASSWORD = "AuditAssocPass123"


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


with SessionLocal() as db:
    db.add_all([
        User(
            username=ADMIN,
            email="audit_admin@example.com",
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            role="SuperAdmin",
            is_active=True,
            mfa_enabled=True,
        ),
        User(
            username=ASSOCIATE,
            email="audit_associate@example.com",
            hashed_password=get_password_hash(ASSOCIATE_PASSWORD),
            role="Associate",
            is_active=True,
        ),
    ])
    db.commit()


def token(username: str, password: str, ip: str = "198.51.100.10") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"X-Forwarded-For": ip},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def rows(action: str | None = None) -> list[AuditLog]:
    with SessionLocal() as db:
        query = db.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action)
        return query.order_by(AuditLog.id).all()


# ---------------------------------------------------------------------------
# The same transaction
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("A mutation and its audit row commit together")
print("-" * 68)

with SessionLocal() as db:
    before = db.query(AuditLog).count()
    record_audit(db, None, "transaction_probe", "Probe", 1, details="staged")
    db.rollback()
with SessionLocal() as db:
    after_rollback = db.query(AuditLog).count()
check("a rolled-back mutation leaves no audit row",
      after_rollback == before,
      f"before={before} after={after_rollback}")

with SessionLocal() as db:
    record_audit(db, None, "transaction_probe", "Probe", 2, details="committed")
    db.commit()
with SessionLocal() as db:
    after_commit = db.query(AuditLog).count()
check("a committed mutation leaves exactly one audit row",
      after_commit == before + 1,
      f"before={before} after={after_commit}")

# An audited endpoint writes its row with the mutation.
admin_token = token(ADMIN, ADMIN_PASSWORD)
response = client.post(
    "/api/v1/departments/",
    headers={
        "Authorization": f"Bearer {admin_token}",
        "X-Forwarded-For": "198.51.100.10",
    },
    json={"name": "Audit Probe", "code": "AUDIT-PROBE"},
)
check("the audited mutation succeeds", response.status_code == 201,
      f"got {response.status_code}: {response.text[:160]}")
created = [row for row in rows("create_department")
           if (row.details or "").startswith("code=AUDIT-PROBE")]
check("the endpoint's audit row exists exactly once", len(created) == 1,
      f"rows={len(created)}")

# ---------------------------------------------------------------------------
# The source address
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("The row records a hashed source address")
print("-" * 68)

logins = [row for row in rows("login") if row.actor_name == ADMIN]
check("the sign-in wrote an audit row", bool(logins), f"rows={len(logins)}")
if logins:
    digest = logins[-1].source_ip_hash or ""
    check("the source address is a SHA-256 digest",
          bool(re.fullmatch(r"[0-9a-f]{64}", digest)),
          f"digest={digest!r}")
    check("the raw address is not stored",
          "198.51.100.10" not in (logins[-1].details or "")
          and digest != "198.51.100.10",
          f"digest={digest!r}")

# The same address produces the same digest on a second request.
second = token(ADMIN, ADMIN_PASSWORD, ip="198.51.100.10")
logins = [row for row in rows("login") if row.actor_name == ADMIN]
check("two requests from one address carry one digest",
      len({row.source_ip_hash for row in logins}) == 1,
      f"digests={ {row.source_ip_hash for row in logins} }")

# A different address produces a different digest.
# Forwarded addresses are honoured only from a trusted proxy (see
# app.core.trusted_proxy): TestClient's peer ("testclient") is never in a
# CIDR, so with the default empty TRUSTED_PROXY_CIDRS both logins above
# correctly carry the peer digest. Honour the forwarded header by trusting
# the test peer for these two logins, then restore the default.
from app.core.config import settings as _audit_settings
import app.core.trusted_proxy as _audit_proxy
_audit_orig_cidrs = _audit_settings.TRUSTED_PROXY_CIDRS
_audit_orig_peer = _audit_proxy._peer
try:
    _audit_settings.TRUSTED_PROXY_CIDRS = "10.0.0.0/8"
    _audit_proxy._peer = lambda request: "10.0.0.2"
    token(ADMIN, ADMIN_PASSWORD, ip="203.0.113.77")
finally:
    _audit_settings.TRUSTED_PROXY_CIDRS = _audit_orig_cidrs
    _audit_proxy._peer = _audit_orig_peer
logins = [row for row in rows("login") if row.actor_name == ADMIN]
check("a different address produces a different digest",
      len({row.source_ip_hash for row in logins}) == 2,
      f"digests={ {row.source_ip_hash for row in logins} }")

# An action outside a request carries none.
with SessionLocal() as db:
    entry = record_audit(db, None, "outside_request", "Probe", 3, details="no request")
    db.commit()
    outside_id = entry.id
with SessionLocal() as db:
    outside = db.get(AuditLog, outside_id)
check("an action outside a request records no address",
      outside.source_ip_hash is None,
      f"digest={outside.source_ip_hash!r}")

# ---------------------------------------------------------------------------
# The lockout transition and an unknown username
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("The lockout transition and an unknown username are audited")
print("-" * 68)

lock_ip = "192.0.2.44"
for attempt in range(1, 11):
    client.post(
        "/api/v1/auth/login",
        json={"username": ADMIN, "password": "wrong-password"},
        headers={"X-Forwarded-For": lock_ip},
    )

failed = [row for row in rows("login_failed")
          if row.actor_name == ADMIN and row.source_ip_hash]
locked = rows("login_locked")
check("the attempt that locks the account writes a lockout row",
      len(locked) == 1, f"rows={len(locked)}")
check("the lockout row is written once, at the transition",
      len(locked) == 1 and locked[0].details == "failed_attempts=10",
      f"details={[row.details for row in locked]}")

# A later attempt against the locked account is a different event.
blocked = client.post(
    "/api/v1/auth/login",
    json={"username": ADMIN, "password": ADMIN_PASSWORD},
    headers={"X-Forwarded-For": "192.0.2.45"},
)
check("a locked account is refused", blocked.status_code == 403,
      f"got {blocked.status_code}")
check("the blocked attempt writes its own row",
      len(rows("login_blocked_locked")) == 1,
      f"rows={len(rows('login_blocked_locked'))}")

# The lockout window is unchanged: an attempt after it expires locks the
# account again, and that second transition is a second event.
with SessionLocal() as db:
    account = db.query(User).filter(User.username == ADMIN).first()
    account.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
after_expiry = client.post(
    "/api/v1/auth/login",
    json={"username": ADMIN, "password": "wrong-password"},
    headers={"X-Forwarded-For": "192.0.2.48"},
)
check("an attempt after the lock expires is still refused",
      after_expiry.status_code == 401, f"got {after_expiry.status_code}")
check("the second lock episode writes a second lockout row",
      len(rows("login_locked")) == 2,
      f"rows={len(rows('login_locked'))}")

# Unlock the account for the remaining checks.
with SessionLocal() as db:
    account = db.query(User).filter(User.username == ADMIN).first()
    account.failed_login_count = 0
    account.locked_until = None
    db.commit()

unknown = client.post(
    "/api/v1/auth/login",
    json={"username": "no-such-person", "password": "whatever12345"},
    headers={"X-Forwarded-For": "192.0.2.46"},
)
wrong = client.post(
    "/api/v1/auth/login",
    json={"username": ADMIN, "password": "wrong-password"},
    headers={"X-Forwarded-For": "192.0.2.47"},
)
check("an unknown username gets the same generic response as a wrong password",
      unknown.status_code == wrong.status_code == 401
      and unknown.json().get("error", {}).get("message")
      == wrong.json().get("error", {}).get("message"),
      f"unknown={unknown.status_code} {unknown.text[:80]} "
      f"wrong={wrong.status_code} {wrong.text[:80]}")

unknown_rows = [row for row in rows("login_failed") if row.actor_id is None]
check("an unknown username writes an audit row",
      len(unknown_rows) == 1, f"rows={len(unknown_rows)}")
check("the row names no username and does not store the attempt",
      bool(unknown_rows)
      and unknown_rows[0].actor_name is None
      and unknown_rows[0].details == "unknown_username"
      and "no-such-person" not in (unknown_rows[0].details or ""),
      f"actor={unknown_rows[0].actor_name if unknown_rows else None!r} "
      f"details={unknown_rows[0].details if unknown_rows else None!r}")

# ---------------------------------------------------------------------------
# No sensitive value in the detail string
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("Sensitive values are redacted before they reach the column")
print("-" * 68)

sensitive = (
    "salary=50000 bank_account=GB82WEST12345698765432 "
    "national_id=AB-1234-5678 dob=1990-01-01 card=4111111111111111"
)
redacted = redact_details(sensitive)
check("a salary value is redacted", "50000" not in redacted, redacted)
check("a bank detail is redacted", "GB82WEST12345698765432" not in redacted, redacted)
check("a national identifier is redacted", "AB-1234-5678" not in redacted, redacted)
check("a date of birth is redacted", "1990-01-01" not in redacted, redacted)
check("a card number is redacted", "4111111111111111" not in redacted, redacted)
check("the key survives so the trail still says what changed",
      all(key in redacted for key in
          ("salary", "bank_account", "national_id", "dob", "card")),
      redacted)
check("a harmless detail is unchanged",
      redact_details("role=SuperAdmin failed_attempts=3") ==
      "role=SuperAdmin failed_attempts=3",
      redact_details("role=SuperAdmin failed_attempts=3"))

with SessionLocal() as db:
    entry = record_audit(
        db, None, "redaction_probe", "Probe", 4, details=sensitive
    )
    db.commit()
    stored_id = entry.id
with SessionLocal() as db:
    stored = db.get(AuditLog, stored_id)
check("record_audit redacts before the row is written",
      "50000" not in (stored.details or "")
      and "GB82WEST12345698765432" not in (stored.details or ""),
      f"details={stored.details!r}")

# ---------------------------------------------------------------------------
# A denied request writes no audit row (DEC-031)
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("A denied request writes no audit row")
print("-" * 68)

associate_token = token(ASSOCIATE, ASSOCIATE_PASSWORD)
with SessionLocal() as db:
    before_denial = db.query(AuditLog).count()
denied = client.post(
    "/api/v1/departments/",
    headers={"Authorization": f"Bearer {associate_token}"},
    json={"name": "Denied Probe", "code": "DENIED-PROBE"},
)
with SessionLocal() as db:
    after_denial = db.query(AuditLog).count()
check("the request is refused with 403", denied.status_code == 403,
      f"got {denied.status_code}")
check("the refusal writes no audit row",
      after_denial == before_denial,
      f"before={before_denial} after={after_denial}")

# ---------------------------------------------------------------------------
print()
print("=" * 68)
print(f"==== AUDIT SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
