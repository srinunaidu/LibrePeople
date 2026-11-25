"""Step-up rate-limit suite: impersonate + admin MFA reset share the login budget.

Covers, on a real FastAPI app + real database:

* Step-up attempts spend the ``login`` IP budget (trusted ``client_ip`` key),
  so X-Forwarded-For rotation from an untrusted peer cannot evade it.
* Every 403 ``step_up_required`` counts toward the per-account 5-in-900s
  lockout via ``_register_failed_login``; the lock transition writes a
  ``login_locked`` audit row. A locked actor is then refused by the shared
  auth gate (fail-closed) on both endpoints and at /login.
* A successful step-up clears the actor's per-account counters but does NOT
  refund the IP budget (no peer reset).
* No new bucket, no new config, no role/audit-hygiene change.

Checks (mirrored on BOTH endpoints):

* (a) five wrong-password impersonations lock the actor; ``login_locked`` is
  audited; the actor is then refused at /login AND at impersonate (locked).
* (b) eleven impersonations from one peer end in 429 with Retry-After —
  proven with successes, since failures lock the account first.
* (c) rotating X-Forwarded-For from an untrusted peer does not evade the
  impersonation throttle (429 still lands on the 11th attempt).
* (d) five wrong-password MFA resets lock the actor; ``login_locked`` is
  audited; the actor is refused at /login AND at reset (locked).
* (e) eleven MFA resets from one peer end in 429 with Retry-After, and
  rotating X-Forwarded-For does not evade it — proven with a fail/success
  mix that never locks the account.
* (f) three failures then a success clear the per-account counters while the
  IP budget stays spent (429 arrives on the 11th cumulative attempt).

Run:  python stepup_rate_limit_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="stepup_rl_"), "stepup_rl.db")
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
from app.core.config import Settings  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.mfa import generate_totp_secret  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.core.security import encrypt_secret, get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

PEER = "testclient"  # TestClient's direct peer; untrusted, so XFF is ignored.

IMP_A_PW = "StepUpImpLock123!"
IMP_B_PW = "StepUpImpPeer123!"
IMP_C_PW = "StepUpImpClear123!"
RST_A_PW = "StepUpRstLock123!"
TGT_PW = "StepUpTarget12345!"

_rst_secret = generate_totp_secret()

db = SessionLocal()
# NB: SuperAdmins must be MFA-enrolled or the shared role gate refuses them
# before any endpoint logic runs (that gate is unchanged by this work).
db.add(User(
    username="su_imp_a", email="su_imp_a@example.test",
    hashed_password=get_password_hash(IMP_A_PW),
    role="SuperAdmin", is_active=True, mfa_enabled=True,
))
db.add(User(
    username="su_imp_b", email="su_imp_b@example.test",
    hashed_password=get_password_hash(IMP_B_PW),
    role="SuperAdmin", is_active=True, mfa_enabled=True,
))
db.add(User(
    username="su_imp_c", email="su_imp_c@example.test",
    hashed_password=get_password_hash(IMP_C_PW),
    role="SuperAdmin", is_active=True, mfa_enabled=True,
))
db.add(User(
    username="su_rst_a", email="su_rst_a@example.test",
    hashed_password=get_password_hash(RST_A_PW),
    role="SuperAdmin", is_active=True,
    mfa_enabled=True, mfa_secret_hash=encrypt_secret(_rst_secret),
))
db.add(User(
    username="step_tgt_imp", email="step_tgt_imp@example.test",
    hashed_password=get_password_hash(TGT_PW),
    role="Associate", is_active=True, mfa_enabled=False,
))
for _name in ("step_tgt_rst", "step_tgt_rst2", "step_tgt_rst3", "step_tgt_rst4"):
    db.add(User(
        username=_name, email=f"{_name}@example.test",
        hashed_password=get_password_hash(TGT_PW),
        role="Associate", is_active=True, mfa_enabled=True,
        mfa_secret_hash=encrypt_secret(generate_totp_secret()),
    ))
db.commit()
db.close()

client = TestClient(app, raise_server_exceptions=False)

API = "/api/v1"


def api(path: str) -> str:
    return f"{API}{path}"


def login(username: str, password: str):
    return client.post(api("/auth/login"), json={"username": username, "password": password})


def user(name: str) -> User:
    sess = SessionLocal()
    try:
        return sess.query(User).filter(User.username == name).first()
    finally:
        sess.close()


def clear_actor(name: str) -> None:
    sess = SessionLocal()
    try:
        u = sess.query(User).filter(User.username == name).first()
        u.failed_login_count = 0
        u.failed_login_window_started_at = None
        u.locked_until = None
        sess.commit()
    finally:
        sess.close()


def lock_rows(name: str) -> int:
    u = user(name)
    sess = SessionLocal()
    try:
        return sess.query(AuditLog).filter(
            AuditLog.action == "login_locked", AuditLog.entity_id == u.id,
        ).count()
    finally:
        sess.close()


def fresh_ip() -> None:
    limiter.reset("login", PEER)


def good_reset(target: str, headers: dict) -> object:
    return client.post(
        api("/auth/mfa/reset"), headers=headers,
        json={
            "target_username": target,
            "current_password": RST_A_PW,
            "totp_code": pyotp.TOTP(_rst_secret).now(),
        },
    )


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
print("STEP-UP RATE LIMIT SUITE")
print("=" * 68)

check("lockout threshold defaults to five", Settings.model_fields["LOGIN_MAX_FAILED_ATTEMPTS"].default == 5)
check("failure window defaults to 900s", Settings.model_fields["LOGIN_FAILURE_WINDOW_SECONDS"].default == 900)
check("lock duration defaults to 900s", Settings.model_fields["LOGIN_LOCKOUT_SECONDS"].default == 900)
check(
    "step-up shares the login IP budget (10 attempts / 300s, no new bucket)",
    limiter._policy.get("login") == (10, 300),
    f"got {limiter._policy.get('login')}",
)

r = login("su_imp_a", IMP_A_PW)
assert r.status_code == 200, f"su_imp_a login failed: {r.text[:120]}"
HA = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = login("su_imp_b", IMP_B_PW)
assert r.status_code == 200, f"su_imp_b login failed: {r.text[:120]}"
HB = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = login("su_imp_c", IMP_C_PW)
assert r.status_code == 200, f"su_imp_c login failed: {r.text[:120]}"
HC = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = login("su_rst_a", RST_A_PW)
assert r.status_code == 200, f"su_rst_a login failed: {r.text[:120]}"
HR = {"Authorization": f"Bearer {r.json()['access_token']}"}

IMP_URL = api("/auth/impersonate")
RST_URL = api("/auth/mfa/reset")


def imp(headers: dict, password: str | None, extra: dict | None = None) -> object:
    body: dict = {"target_username": "step_tgt_imp"}
    if password is not None:
        body["current_password"] = password
    return client.post(IMP_URL, headers={**(extra or {}), **headers}, json=body)


def rst(headers: dict, password: str | None, extra: dict | None = None) -> object:
    body: dict = {"target_username": "step_tgt_rst"}
    if password is not None:
        body["current_password"] = password
    return client.post(RST_URL, headers={**(extra or {}), **headers}, json=body)


# --- (a) impersonate: five wrong passwords lock the actor -------------------
fresh_ip()
codes = [imp(HA, "wrong-password").status_code for _ in range(5)]
check(
    "(a) five wrong-password impersonations are each refused 403 step_up_required",
    codes == [403] * 5,
    f"codes={codes}",
)
_a = user("su_imp_a")
check(
    "(a) the fifth failure locks the actor (5/900s)",
    _a.locked_until is not None and _a.failed_login_count == 5,
    f"count={_a.failed_login_count} locked={_a.locked_until}",
)
check(
    "(a) the lock transition writes a login_locked audit row",
    lock_rows("su_imp_a") == 1,
    f"rows={lock_rows('su_imp_a')}",
)
r = login("su_imp_a", IMP_A_PW)
check(
    "(a) the correct password is refused at /login while locked",
    r.status_code == 403,
    f"got {r.status_code}: {r.text[:120]}",
)
r = imp(HA, IMP_A_PW)
check(
    "(a) a locked actor is refused at impersonate even with the right password",
    r.status_code == 403 and "locked" in r.text.lower(),
    f"got {r.status_code}: {r.text[:140]}",
)

# --- (b) impersonate: eleven successes from one peer -> 429 + Retry-After ----
# Successes never lock (each clears the per-account counters), so all eleven
# reach the throttle: the first ten pass, the 11th is refused with 429.
fresh_ip()
codes = [imp(HB, IMP_B_PW).status_code for _ in range(10)]
r = imp(HB, IMP_B_PW)
check(
    "(b) ten impersonations from one peer succeed",
    codes == [200] * 10,
    f"codes={codes}",
)
check(
    "(b) the 11th impersonation from one peer is 429 with Retry-After",
    r.status_code == 429 and bool(r.headers.get("retry-after")),
    f"got {r.status_code} retry-after={r.headers.get('retry-after')}",
)

# --- (c) impersonate: rotating XFF from an untrusted peer does not evade -----
fresh_ip()
codes = [
    imp(HB, IMP_B_PW, extra={"X-Forwarded-For": f"198.51.100.{i}"}).status_code
    for i in range(10)
]
r = imp(HB, IMP_B_PW, extra={"X-Forwarded-For": "198.51.100.250"})
check(
    "(c) ten rotating-XFF impersonations succeed (one shared budget)",
    codes == [200] * 10,
    f"codes={codes}",
)
check(
    "(c) the 11th rotating-XFF impersonation is still 429",
    r.status_code == 429 and bool(r.headers.get("retry-after")),
    f"got {r.status_code} retry-after={r.headers.get('retry-after')}",
)

# --- (d) MFA reset: five wrong passwords lock the actor ----------------------
fresh_ip()
codes = [rst(HR, "wrong-password").status_code for _ in range(5)]
check(
    "(d) five wrong-password resets are each refused 403 step_up_required",
    codes == [403] * 5,
    f"codes={codes}",
)
_a = user("su_rst_a")
check(
    "(d) the fifth failure locks the actor (5/900s)",
    _a.locked_until is not None and _a.failed_login_count == 5,
    f"count={_a.failed_login_count} locked={_a.locked_until}",
)
check(
    "(d) the lock transition writes a login_locked audit row",
    lock_rows("su_rst_a") == 1,
    f"rows={lock_rows('su_rst_a')}",
)
r = login("su_rst_a", RST_A_PW)
check(
    "(d) the correct password is refused at /login while locked",
    r.status_code == 403,
    f"got {r.status_code}: {r.text[:120]}",
)
r = good_reset("step_tgt_rst", HR)
check(
    "(d) a locked actor is refused at reset even with password+TOTP",
    r.status_code == 403 and "locked" in r.text.lower(),
    f"got {r.status_code}: {r.text[:140]}",
)
clear_actor("su_rst_a")

# --- (e) MFA reset: 429 + Retry-After, XFF rotation does not evade -----------
# Four fails, one success, four fails, one success, one fail: eleven throttle
# hits that never lock the account (each success clears the counters), so the
# 11th attempt is refused with 429 rather than 403.
fresh_ip()
codes = [rst(HR, "wrong-password").status_code for _ in range(4)]
codes.append(good_reset("step_tgt_rst", HR).status_code)
codes += [rst(HR, "wrong-password").status_code for _ in range(4)]
codes.append(good_reset("step_tgt_rst2", HR).status_code)
r = rst(HR, None)
check(
    "(e) nine reset hits pass (4x403, 200, 4x403, 200)",
    codes == [403] * 4 + [200] + [403] * 4 + [200],
    f"codes={codes}",
)
check(
    "(e) the 11th reset from one peer is 429 with Retry-After",
    r.status_code == 429 and bool(r.headers.get("retry-after")),
    f"got {r.status_code} retry-after={r.headers.get('retry-after')}",
)
check(
    "(e) the mixed run never locked the actor",
    user("su_rst_a").locked_until is None,
    f"locked={user('su_rst_a').locked_until}",
)
fresh_ip()
codes = [
    client.post(
        RST_URL, headers={**HR, "X-Forwarded-For": f"203.0.113.{i}"},
        json={"target_username": "step_tgt_rst", "current_password": "wrong-password"},
    ).status_code
    for i in range(4)
]
codes.append(
    client.post(
        RST_URL, headers={**HR, "X-Forwarded-For": "203.0.113.10"},
        json={
            "target_username": "step_tgt_rst3",
            "current_password": RST_A_PW,
            "totp_code": pyotp.TOTP(_rst_secret).now(),
        },
    ).status_code
)
codes += [
    client.post(
        RST_URL, headers={**HR, "X-Forwarded-For": f"203.0.113.{20 + i}"},
        json={"target_username": "step_tgt_rst", "current_password": "wrong-password"},
    ).status_code
    for i in range(4)
]
codes.append(
    client.post(
        RST_URL, headers={**HR, "X-Forwarded-For": "203.0.113.30"},
        json={
            "target_username": "step_tgt_rst4",
            "current_password": RST_A_PW,
            "totp_code": pyotp.TOTP(_rst_secret).now(),
        },
    ).status_code
)
r = client.post(
    RST_URL, headers={**HR, "X-Forwarded-For": "203.0.113.99"},
    json={"target_username": "step_tgt_rst"},
)
check(
    "(e) rotating X-Forwarded-For fills the same reset budget",
    codes == [403] * 4 + [200] + [403] * 4 + [200],
    f"codes={codes}",
)
check(
    "(e) the 11th rotating-XFF reset is still 429",
    r.status_code == 429 and bool(r.headers.get("retry-after")),
    f"got {r.status_code} retry-after={r.headers.get('retry-after')}",
)

# --- (f) success clears per-account counters but not the peer budget ---------
fresh_ip()
for _ in range(3):
    imp(HC, "wrong-password")
check(
    "(f) three failures stage a count of three",
    user("su_imp_c").failed_login_count == 3,
    f"count={user('su_imp_c').failed_login_count}",
)
r = imp(HC, IMP_C_PW)
_a = user("su_imp_c")
check(
    "(f) a success clears the per-account counters (no lock, count zero)",
    r.status_code == 200 and _a.failed_login_count == 0
    and _a.failed_login_window_started_at is None and _a.locked_until is None,
    f"got {r.status_code}: {r.text[:120]}",
)
# Four hits spent (3 fails + success). Six more successes reach the budget of
# ten; the 11th cumulative attempt is 429 — a peer reset on success would have
# needed eleven more instead.
codes = [imp(HC, IMP_C_PW).status_code for _ in range(6)]
r = imp(HC, IMP_C_PW)
check(
    "(f) six more successes pass (budget now spent ten deep)",
    codes == [200] * 6,
    f"codes={codes}",
)
check(
    "(f) the 11th cumulative attempt is 429: success never refunded the peer",
    r.status_code == 429 and bool(r.headers.get("retry-after")),
    f"got {r.status_code} retry-after={r.headers.get('retry-after')}",
)

print()
print("=" * 68)
print(f"STEP-UP RATE LIMIT SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print()
    print("Failures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
