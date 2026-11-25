"""Administrator operational status suite (LP-ADM-005).

Covers the contract promise of `contracts/openapi/admin.yaml` at
`GET /admin/status` (`adminGetStatus`, `x-lifecycle: released`):

* SuperAdmin gets 200 with the contract's `AdminStatus` shape —
  `app_version`, `environment`, `upgrade`, `backup`, `warnings`,
  `checked_at`;
* the backup block reports the env defaults honestly: not configured
  with the `backup_not_configured` warning when no backup was arranged;
* a dead job in the queue surfaces a `dead_jobs_present` warning;
* HR, Manager and Associate are refused with the shared 403 envelope —
  this endpoint is SuperAdmin only;
* an unauthenticated call is 401;
* the call is read only: the audit row count and the job row count are
  identical before and after, and no upgrade/migration/backup runs.

Run:  python admin_status_test_suite.py
"""
import os

DB_PATH = "admin_status_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"
# LP-ADM-005 defaults under test: no backup arranged.
os.environ["BACKUP_ENABLED"] = "false"
os.environ["BACKUP_SCHEDULE"] = "manual"
if "BACKUP_LAST_SUCCESS_AT" in os.environ:
    del os.environ["BACKUP_LAST_SUCCESS_AT"]

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.job_queue import JobQueue  # noqa: E402
from app.models.user import User  # noqa: E402

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
STATUS = "/api/v1/admin/status"
PASSWORD = "StatusPass123"

ROLE_ACCOUNTS = {
    "SuperAdmin": "adm05admin",
    "HR": "adm05hr",
    "Manager": "adm05mgr",
    "Associate": "adm05assoc",
}

print("=" * 68)
print("ADMIN STATUS SUITE (LP-ADM-005)")
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


def H(username: str) -> dict:
    tok = client.post(
        LOGIN, json={"username": username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def codes(body) -> set:
    if isinstance(body, dict):
        warnings = body.get("warnings") or []
    else:
        warnings = []
    return {w.get("code") for w in warnings if isinstance(w, dict)}


print("-- contract shape (SuperAdmin) --")
r = client.get(STATUS, headers=H("adm05admin"))
check("SuperAdmin gets 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
body = r.json() if r.status_code == 200 else {}
for field in ("app_version", "environment", "upgrade", "backup", "warnings", "checked_at"):
    check(f"response carries {field}", field in body, f"missing {field}")
check("warnings is a list", isinstance(body.get("warnings"), list))
upgrade = body.get("upgrade") or {}
for field in ("current_revision", "head_revision", "up_to_date", "status"):
    check(f"upgrade carries {field}", field in upgrade, f"missing {field}")
backup = body.get("backup") or {}
for field in ("configured", "schedule", "last_success_at", "stale"):
    check(f"backup carries {field}", field in backup, f"missing {field}")
check(
    "warning entries have code/severity/message",
    all(
        isinstance(w, dict) and w.get("code") and w.get("severity") and w.get("message")
        for w in (body.get("warnings") or [])
    ),
    f"got {body.get('warnings')}",
)

print("-- env defaults: no backup arranged --")
check("backup reports not configured", backup.get("configured") is False, f"got {backup}")
check("backup schedule defaults to manual", backup.get("schedule") == "manual", f"got {backup}")
check(
    "backup_not_configured warning is present",
    "backup_not_configured" in codes(body),
    f"got {codes(body)}",
)

print("-- dead jobs surface a warning --")
db.add(
    JobQueue(
        job_type="csv_import",
        input_hash="adm05-dead-job-input-hash",
        state="dead",
        attempts=3,
        max_attempts=3,
    )
)
db.commit()
r = client.get(STATUS, headers=H("adm05admin"))
check("status still 200 with a dead job", r.status_code == 200, f"got {r.status_code}")
check(
    "dead_jobs_present warning is present",
    "dead_jobs_present" in codes(r.json()),
    f"got {codes(r.json())}",
)

print("-- role gate: SuperAdmin only --")
for role, username in (("HR", "adm05hr"), ("Manager", "adm05mgr"), ("Associate", "adm05assoc")):
    rr = client.get(STATUS, headers=H(username))
    ok = rr.status_code == 403
    try:
        envelope = rr.json().get("error", {}).get("code") is not None
    except Exception:
        envelope = False
    check(f"{role} is refused with 403", ok, f"got {rr.status_code}")
    check(f"{role} refusal uses the shared envelope", ok and envelope, f"got {rr.text[:160]}")

print("-- unauthenticated --")
rr = client.get(STATUS)
check("missing token is 401", rr.status_code == 401, f"got {rr.status_code}")

print("-- read only: no state change --")
admin_headers = H("adm05admin")
audit_before = db.query(AuditLog).count()
jobs_before = db.query(JobQueue).count()
r1 = client.get(STATUS, headers=admin_headers)
r2 = client.get(STATUS, headers=admin_headers)
db.expire_all()
audit_after = db.query(AuditLog).count()
jobs_after = db.query(JobQueue).count()
check("repeated reads stay 200", r1.status_code == 200 and r2.status_code == 200)
check("no audit row is written", audit_after == audit_before, f"{audit_before} -> {audit_after}")
check("no job row changes", jobs_after == jobs_before, f"{jobs_before} -> {jobs_after}")

print("=" * 68)
print(f"RESULT: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print("FAILURES:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
    raise SystemExit(1)
