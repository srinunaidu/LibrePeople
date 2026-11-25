"""Audit-chain verification over HTTP (PS-12).

Covers the contract promise of `contracts/openapi/admin.yaml` at
`GET /admin/audit/verify` (`adminVerifyAudit`, `x-lifecycle: released`):

* an intact chain answers `verified: true`, the number of entries walked,
  the head hash and the head id, and `first_broken: null`;
* an edited row is reported as `hash_mismatch`, naming the row and the
  position the walk stopped at;
* a row whose `prev_hash` no longer matches the one before it is reported
  as `missing_predecessor` — the shape a row inserted, removed or
  reordered in the middle takes;
* a row removed from the end is reported as `head_mismatch`, with no id,
  because the last entry that *did* verify is not the broken one;
* the call is read only: the chain is never repaired, and the audit row the
  verification writes does not break it — a second call verifies one entry
  more;
* the role gate (SuperAdmin + HR only) with the shared 403 envelope, and a
  refused call writes no audit row because nothing happened;
* the response is in the contract's `AuditVerification` shape.

The destructive cases rebuild the chain between them: this suite owns a
throw-away SQLite file and the append-only triggers are a migration, not a
`create_all()` feature, so a raw UPDATE/DELETE is available to the test and
is exactly the tamper the chain exists to detect.

Run:  python admin_audit_test_suite.py
"""
import os

DB_PATH = "admin_audit_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from datetime import datetime  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.main import app  # noqa: E402
from app.core.audit import record_audit  # noqa: E402
from app.core.audit_chain import GENESIS_HASH  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.audit import AuditChainHead, AuditLog  # noqa: E402
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
VERIFY = "/api/v1/admin/audit/verify"
PASSWORD = "AuditPass123"

ROLE_ACCOUNTS = {
    "SuperAdmin": "ps12admin",
    "HR": "ps12hr",
    "Manager": "ps12mgr",
    "Associate": "ps12assoc",
    "PayrollViewer": "ps12payroll",
}

print("=" * 68)
print("AUDIT CHAIN VERIFICATION SUITE (PS-12)")
print("=" * 68)

# --- the accounts -----------------------------------------------------------
for username in ROLE_ACCOUNTS.values():
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.delete(existing)
db.commit()
for role, username in ROLE_ACCOUNTS.items():
    db.add(
        User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role=role,
            is_active=True,
            mfa_enabled=role in ("SuperAdmin", "HR"),
        )
    )
db.commit()

HEADERS: dict[str, dict] = {}
for role, username in ROLE_ACCOUNTS.items():
    resp = client.post(LOGIN, json={"username": username, "password": PASSWORD})
    if resp.status_code != 200:
        check(f"the {role} account can sign in", False, f"status={resp.status_code}")
        continue
    HEADERS[role] = {"Authorization": f"Bearer {resp.json()['access_token']}"}
check(
    "one account per role signed in",
    len(HEADERS) == len(ROLE_ACCOUNTS),
    f"got {sorted(HEADERS)}",
)

ADMIN = HEADERS["SuperAdmin"]
HR = HEADERS["HR"]


# --- helpers ----------------------------------------------------------------
def reset_chain(entries: int = 3) -> None:
    """Replace the audit log with a short, honest chain.

    The suite owns the database. Clearing the rows and the head is the only
    way to get a clean three-entry chain between destructive cases without
    re-inserting a deleted row by hand.
    """
    with Session(engine) as session:
        session.query(AuditLog).delete()
        session.query(AuditChainHead).delete()
        session.commit()
        for index in range(entries):
            record_audit(
                session,
                None,
                "chain_probe",
                "Probe",
                index + 1,
                details=f"row {index + 1}",
            )
        session.commit()
    db.expire_all()


def chain_rows() -> list[AuditLog]:
    with Session(engine) as session:
        return (
            session.query(AuditLog).order_by(AuditLog.id).all()
        )


def head_row() -> tuple[str, int | None]:
    with Session(engine) as session:
        head = session.get(AuditChainHead, 1)
        if head is None:
            return GENESIS_HASH, None
        return head.head_hash or GENESIS_HASH, head.head_id


def verify(headers: dict | None = None):
    return client.get(VERIFY, headers=ADMIN if headers is None else headers)


def audit_count(action: str) -> int:
    with Session(engine) as session:
        return (
            session.query(AuditLog)
            .filter(AuditLog.action == action, AuditLog.entity_type == "AuditLog")
            .count()
        )


# ====[ the honest chain ]====================================================
print("\n[PS12-1] an intact chain is reported intact")

reset_chain(3)
rows = chain_rows()
head_hash, head_id = head_row()
before = audit_count("verify_audit")

r = verify()
body = r.json() if r.status_code == 200 else {}
check("SuperAdmin can verify the chain", r.status_code == 200, f"got {r.status_code}: {r.text[:160]}")
check(
    "the answer is in the contract's AuditVerification shape",
    {"verified", "checked_entries", "head", "head_id", "first_broken", "verified_at"}
    <= set(body),
    f"got {sorted(body)}",
)
check(
    "an intact chain verifies",
    body.get("verified") is True and body.get("first_broken") is None,
    f"got verified={body.get('verified')!r} first_broken={body.get('first_broken')!r}",
)
check(
    "every entry was walked",
    body.get("checked_entries") == 3,
    f"got {body.get('checked_entries')!r} expected 3",
)
check(
    "the head is the head the chain records",
    body.get("head") == head_hash and body.get("head_id") == head_id,
    f"got head={body.get('head')!r} id={body.get('head_id')!r} "
    f"expected {head_hash!r} / {head_id!r}",
)
check(
    "the head is a SHA-256 digest",
    isinstance(body.get("head"), str)
    and len(body["head"]) == 64
    and all(c in "0123456789abcdef" for c in body["head"]),
    f"got {body.get('head')!r}",
)
try:
    verified_at = datetime.fromisoformat(str(body.get("verified_at")).replace("Z", "+00:00"))
    stamped = verified_at.tzinfo is not None
except ValueError:
    stamped = False
check(
    "the answer is stamped with a timezone-aware instant",
    stamped,
    f"got {body.get('verified_at')!r}",
)

hr_call = verify(HR)
check(
    "HR can verify the chain too",
    hr_call.status_code == 200,
    f"got {hr_call.status_code}",
)
check(
    "each successful call writes an audit row",
    audit_count("verify_audit") == before + 2,
    f"got {audit_count('verify_audit')} expected {before + 2}",
)

# The verification's own entry must not break the chain: the next walk sees
# one more entry and still holds.
after_first = verify()
check(
    "the verification's own audit row does not break the chain",
    after_first.status_code == 200
    and after_first.json()["verified"] is True
    and after_first.json()["checked_entries"] == 5,
    f"got {after_first.text[:200]}",
)


# ====[ the role gate ]=======================================================
print("\n[PS12-2] the role gate")

for role in ("Manager", "Associate", "PayrollViewer"):
    before_refusal = audit_count("verify_audit")
    r = verify(HEADERS[role])
    envelope = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    error = envelope.get("error", {}) if isinstance(envelope, dict) else {}
    check(
        f"{role} is refused with the shared 403 envelope",
        r.status_code == 403 and error.get("code") == "forbidden",
        f"got {r.status_code}: {r.text[:160]}",
    )
    check(
        f"the refused {role} call writes no audit row",
        audit_count("verify_audit") == before_refusal,
        f"count={audit_count('verify_audit')} expected={before_refusal}",
    )

r = client.get(VERIFY)
check("an unauthenticated call answers 401", r.status_code == 401, f"got {r.status_code}")


# ====[ an edited row ]=======================================================
print("\n[PS12-3] an edited row is a hash_mismatch")

reset_chain(3)
rows = chain_rows()
target = rows[1]
with engine.begin() as conn:
    conn.execute(
        text("UPDATE audit_logs SET details = 'edited after the fact' WHERE id = :id"),
        {"id": target.id},
    )
db.expire_all()

r = verify()
body = r.json()
broken = body.get("first_broken") or {}
check(
    "an edited row fails the verification",
    r.status_code == 200 and body.get("verified") is False,
    f"got {r.status_code}: {r.text[:200]}",
)
check(
    "the reason is hash_mismatch",
    broken.get("reason") == "hash_mismatch",
    f"got {broken.get('reason')!r}",
)
check(
    "the edited entry is named",
    broken.get("id") == str(target.id),
    f"got id={broken.get('id')!r} expected={target.id}",
)
check(
    "the walk stopped at the edited entry's position",
    body.get("checked_entries") == 1 and broken.get("index") == 1,
    f"checked={body.get('checked_entries')!r} index={broken.get('index')!r}",
)

# Restoring the row makes the chain hold again: the failure was the edit,
# not the procedure.
with engine.begin() as conn:
    conn.execute(
        text("UPDATE audit_logs SET details = 'row 2' WHERE id = :id"),
        {"id": target.id},
    )
db.expire_all()
restored = verify()
check(
    "restoring the row makes the chain verify again",
    restored.status_code == 200 and restored.json().get("verified") is True,
    restored.text[:160],
)


# ====[ a wrong previous hash ]===============================================
print("\n[PS12-4] a broken link is a missing_predecessor")

reset_chain(3)
rows = chain_rows()
target = rows[1]
with engine.begin() as conn:
    conn.execute(
        text("UPDATE audit_logs SET prev_hash = :hash WHERE id = :id"),
        {"hash": "a" * 64, "id": target.id},
    )
db.expire_all()

r = verify()
body = r.json()
broken = body.get("first_broken") or {}
check(
    "a wrong prev_hash fails the verification",
    body.get("verified") is False,
    f"got {r.text[:200]}",
)
check(
    "the reason is missing_predecessor",
    broken.get("reason") == "missing_predecessor",
    f"got {broken.get('reason')!r}",
)
check(
    "the entry whose link is broken is named",
    broken.get("id") == str(target.id),
    f"got id={broken.get('id')!r} expected={target.id}",
)


# ====[ a removed row in the middle ]=========================================
print("\n[PS12-5] a removed row in the middle is found at the gap")

reset_chain(3)
rows = chain_rows()
removed = rows[1]
successor = rows[2]
with engine.begin() as conn:
    conn.execute(text("DELETE FROM audit_logs WHERE id = :id"), {"id": removed.id})
db.expire_all()

r = verify()
body = r.json()
broken = body.get("first_broken") or {}
check(
    "a removed row in the middle fails the verification",
    body.get("verified") is False,
    f"got {r.text[:200]}",
)
check(
    "the gap is reported as missing_predecessor",
    broken.get("reason") == "missing_predecessor",
    f"got {broken.get('reason')!r}",
)
check(
    "the entry after the gap is named, not the removed one",
    broken.get("id") == str(successor.id),
    f"got id={broken.get('id')!r} expected={successor.id}",
)


# ====[ a removed tail ]======================================================
print("\n[PS12-6] a removed tail is a head_mismatch")

reset_chain(3)
rows = chain_rows()
with engine.begin() as conn:
    conn.execute(text("DELETE FROM audit_logs WHERE id = :id"), {"id": rows[-1].id})
db.expire_all()

r = verify()
body = r.json()
broken = body.get("first_broken") or {}
check(
    "a removed tail fails the verification",
    body.get("verified") is False,
    f"got {r.text[:200]}",
)
check(
    "the reason is head_mismatch",
    broken.get("reason") == "head_mismatch",
    f"got {broken.get('reason')!r}",
)
check(
    "no honest entry is accused",
    broken.get("id") is None,
    f"got id={broken.get('id')!r}",
)
check(
    "the gap is the position after the last entry that verified",
    body.get("checked_entries") == 2 and broken.get("index") == 2,
    f"checked={body.get('checked_entries')!r} index={broken.get('index')!r}",
)
check(
    "the recorded head is still reported, so it can be anchored",
    isinstance(body.get("head"), str) and len(body["head"]) == 64,
    f"got head={body.get('head')!r}",
)

# The verification writes its own entry. The next walk finds the same break,
# now at the entry that does not follow the last present row. The break is
# still found and named; it is not silently repaired.
second = verify().json()
check(
    "the break is still found after the verification's own entry",
    second.get("verified") is False
    and (second.get("first_broken") or {}).get("reason") == "missing_predecessor",
    f"got {second.get('first_broken')!r}",
)
check(
    "the break is still named at a real entry",
    (second.get("first_broken") or {}).get("id") is not None,
    f"got {second.get('first_broken')!r}",
)


# ====[ a fresh chain ]======================================================
print("\n[PS12-7] an empty log is not a failure")

with Session(engine) as session:
    session.query(AuditLog).delete()
    session.query(AuditChainHead).delete()
    session.commit()
db.expire_all()

r = verify()
body = r.json()
check(
    "an empty log verifies with zero entries",
    r.status_code == 200
    and body.get("verified") is True
    and body.get("checked_entries") == 0,
    f"got {r.text[:200]}",
)
check(
    "the head of an empty log is the genesis hash",
    body.get("head") == GENESIS_HASH,
    f"got {body.get('head')!r}",
)


# ====[ the operation is served ]============================================
print("\n[PS12-8] the operation is served, not merely declared")

# FastAPI >=0.118 keeps included routers lazy: `app.routes` holds an
# `_IncludedRouter` placeholder instead of the endpoint routes. Descend
# into the original router and accumulate the mount prefix, so the check
# holds to the operations the application actually serves (same walk as
# `security_test_suite._served_operations`). No product-code change: the
# mount stays `admin_audit.router` at `/admin/audit` + `@router.get("/verify")`.
def _served_paths(routes, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for route in routes:
        original = getattr(route, "original_router", None)
        if original is not None and hasattr(original, "routes"):
            context = getattr(route, "include_context", None)
            child_prefix = getattr(context, "prefix", "") or ""
            paths |= _served_paths(original.routes, prefix + child_prefix)
            continue
        path = getattr(route, "path", None)
        if path is None:
            continue
        paths.add(f"{prefix}{path}")
    return paths


served = _served_paths(app.routes)
check("the route is mounted at the contract's path", VERIFY in served, f"got {sorted(p for p in served if 'audit' in p)}")


# ===========================================================================
print()
print("=" * 68)
print(f"AUDIT CHAIN VERIFICATION SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
print("=" * 68)
if FAILURES:
    print("\nfailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
    raise SystemExit(1)
