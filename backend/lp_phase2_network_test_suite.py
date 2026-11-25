"""LibrePeople Phase 2 security remediation — login lockout, trusted proxy and outbound URL guard.

  [ITEM-5]  five failures in a 15-minute window lock the account; forwarded
            headers are believed only from a trusted proxy
  [ITEM-8]  the outbound URL guard: https only, blocked destinations, every
            redirect re-validated, DNS answer pinned, call sites routed through it

Every item has an authorised-path and an unauthorised-path check. No network
access: the resolver and the transport are injected. No skip or xfail.

Run:  python lp_phase2_network_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="lp_phase2_net_"), "lp_phase2_net.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["ENVIRONMENT"] = "development"
os.environ["LOG_LEVEL"] = "CRITICAL"
# The IP limiter must not interfere with the per-account lockout checks.
os.environ["LOGIN_RATE_LIMIT_ATTEMPTS"] = "1000"
os.environ["LOGIN_RATE_LIMIT_WINDOW_SECONDS"] = "300"

from datetime import datetime, timedelta, timezone  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from starlette.requests import Request  # noqa: E402

from app.main import app  # noqa: E402
from app.core.config import Settings, settings  # noqa: E402
from app.core import url_guard  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.core import trusted_proxy  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

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


client = TestClient(app)
PASSWORD = "Lockout#Test2026x"
LOCK_USERS = ("lp_lock_ok", "lp_lock_out", "lp_lock_win", "lp_lock_hdr", "lp_lock_hdr2")

_db = SessionLocal()
for _name in LOCK_USERS:
    _u = _db.query(User).filter(User.username == _name).first()
    if _u:
        _db.delete(_u)
_db.commit()
for _name in LOCK_USERS:
    _db.add(
        User(
            username=_name,
            email=f"{_name}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role="Associate",
            is_active=True,
            must_change_password=False,
        )
    )
_db.commit()
_db.close()


def _user(name: str) -> User:
    sess = SessionLocal()
    try:
        return sess.query(User).filter(User.username == name).first()
    finally:
        sess.close()


def _set_user(name: str, **fields) -> None:
    sess = SessionLocal()
    try:
        u = sess.query(User).filter(User.username == name).first()
        for k, v in fields.items():
            setattr(u, k, v)
        sess.commit()
    finally:
        sess.close()


def login(name: str, password: str, headers=None):
    return client.post(
        "/api/v1/auth/login",
        json={"username": name, "password": password},
        headers=headers or {},
    )


# ===========================================================================
print("\n[ITEM-5a] Login lockout: five failures within the window lock the account")
# ===========================================================================

check("the default lockout threshold is five", Settings.model_fields["LOGIN_MAX_FAILED_ATTEMPTS"].default == 5)
check("the default failure window is 15 minutes", Settings.model_fields["LOGIN_FAILURE_WINDOW_SECONDS"].default == 900)
check("the default lock duration is 15 minutes", Settings.model_fields["LOGIN_LOCKOUT_SECONDS"].default == 900)

# Authorised: four failures, then the right password still signs in.
codes = [login("lp_lock_ok", "wrong-password-1").status_code for _ in range(4)]
check("four failed sign-ins are each refused", codes == [401, 401, 401, 401], f"codes={codes}")
r = login("lp_lock_ok", PASSWORD)
check("the correct password still works after four failures", r.status_code == 200, f"got {r.status_code}")

# Unauthorised: the fifth failure locks, and the right password is then refused.
codes = [login("lp_lock_out", f"wrong-{i}").status_code for i in range(5)]
check("the fifth failure is refused with the generic 401", codes[-1] == 401, f"codes={codes}")
check("the account is locked after five failures", _user("lp_lock_out").locked_until is not None)
r = login("lp_lock_out", PASSWORD)
check("the correct password is refused while locked", r.status_code == 403, f"got {r.status_code}")

# Window: failures outside the window do not add up.
_set_user(
    "lp_lock_win",
    failed_login_count=4,
    failed_login_window_started_at=datetime.now(timezone.utc) - timedelta(minutes=16),
)
r = login("lp_lock_win", "wrong-after-window")
check("a failure after the window has closed starts a new count", r.status_code == 401, f"got {r.status_code}")
check(
    "stale failures do not lock the account",
    _user("lp_lock_win").locked_until is None and _user("lp_lock_win").failed_login_count == 1,
    f"count={_user('lp_lock_win').failed_login_count} locked={_user('lp_lock_win').locked_until}",
)
r = login("lp_lock_win", PASSWORD)
check("a user with a stale window still signs in", r.status_code == 200, f"got {r.status_code}")

# Window: four failures inside the window plus one more do lock.
_set_user(
    "lp_lock_win",
    failed_login_count=4,
    failed_login_window_started_at=datetime.now(timezone.utc) - timedelta(minutes=1),
)
login("lp_lock_win", "wrong-inside-window")
check("five failures inside one window lock the account", _user("lp_lock_win").locked_until is not None)

# A client header cannot reset or bypass the account count.
for i in range(5):
    login("lp_lock_hdr", f"wrong-{i}", headers={"X-Forwarded-For": f"198.51.100.{i + 10}", "X-Forwarded-Host": "evil.example.com"})
check("rotating forwarded headers does not stop the lockout", _user("lp_lock_hdr").locked_until is not None)
r = login("lp_lock_hdr", PASSWORD, headers={"X-Forwarded-For": "203.0.113.200"})
check("a fresh forwarded address does not unlock a locked account", r.status_code == 403, f"got {r.status_code}")

# A successful sign-in clears the count (authorised path after failures).
_set_user("lp_lock_hdr2", failed_login_count=3, failed_login_window_started_at=datetime.now(timezone.utc))
r = login("lp_lock_hdr2", PASSWORD)
check("a successful sign-in clears the failure count", r.status_code == 200 and _user("lp_lock_hdr2").failed_login_count == 0 and _user("lp_lock_hdr2").failed_login_window_started_at is None)


# ===========================================================================
print("\n[ITEM-5b] Forwarded headers are believed only from a trusted proxy")
# ===========================================================================


def _request(peer: str, headers=None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": raw,
            "client": (peer, 40000),
            "server": ("testserver", 443),
            "scheme": "https",
        }
    )


_original_cidrs = settings.TRUSTED_PROXY_CIDRS


def _set_cidrs(value: str) -> None:
    settings.TRUSTED_PROXY_CIDRS = value


check("TRUSTED_PROXY_CIDRS defaults to empty (nothing trusted)", Settings.model_fields["TRUSTED_PROXY_CIDRS"].default == "")
_set_cidrs("")
req = _request("203.0.113.9", {"X-Forwarded-For": "198.51.100.7"})
check(
    "with no trusted proxy, X-Forwarded-For is ignored",
    trusted_proxy.client_ip(req) == "203.0.113.9",
    f"got {trusted_proxy.client_ip(req)}",
)
check("with no trusted proxy, a forwarded host is ignored", trusted_proxy.forwarded_host(_request("203.0.113.9", {"X-Forwarded-Host": "tenant-b.example.com"})) is None)
check("with no trusted proxy, a forwarded proto is ignored", trusted_proxy.forwarded_proto(_request("203.0.113.9", {"X-Forwarded-Proto": "https"})) is None)

_set_cidrs("10.0.0.0/8")
check(
    "a trusted proxy's X-Forwarded-For is honoured",
    trusted_proxy.client_ip(_request("10.0.0.2", {"X-Forwarded-For": "198.51.100.7"})) == "198.51.100.7",
)
check(
    "X-Forwarded-For from an untrusted peer is ignored even with a trusted range set",
    trusted_proxy.client_ip(_request("203.0.113.9", {"X-Forwarded-For": "198.51.100.7"})) == "203.0.113.9",
)
check(
    "the right-most untrusted address is the client, not a client-supplied left-most entry",
    trusted_proxy.client_ip(_request("10.0.0.2", {"X-Forwarded-For": "6.6.6.6, 198.51.100.7, 10.0.0.9"})) == "198.51.100.7",
)
check(
    "a malformed forwarded entry falls back to the peer",
    trusted_proxy.client_ip(_request("10.0.0.2", {"X-Forwarded-For": "not-an-address"})) == "10.0.0.2",
)
check(
    "a trusted proxy's forwarded host is honoured",
    trusted_proxy.forwarded_host(_request("10.0.0.2", {"X-Forwarded-Host": "Tenant-A.example.com"})) == "tenant-a.example.com",
)
check(
    "a trusted proxy's forwarded proto is honoured",
    trusted_proxy.forwarded_proto(_request("10.0.0.2", {"X-Forwarded-Proto": "https"})) == "https",
)

# The rate limiter key is the trusted client address: with the proxy untrusted,
# rotating X-Forwarded-For does not change the key.
_set_cidrs("")
keys = {trusted_proxy.client_ip(_request("203.0.113.9", {"X-Forwarded-For": f"192.0.2.{i}"})) for i in range(20)}
check("rotating X-Forwarded-For cannot change the limiter key", keys == {"203.0.113.9"}, f"keys={sorted(keys)[:3]}")

# A malformed CIDR fails at startup rather than trusting nothing silently.
try:
    Settings(TRUSTED_PROXY_CIDRS="not-a-network").validate()
    bad_cidr_refused = False
except RuntimeError:
    bad_cidr_refused = True
check("a malformed TRUSTED_PROXY_CIDRS stops startup", bad_cidr_refused)
try:
    Settings(TRUSTED_PROXY_CIDRS="10.0.0.0/8, 192.0.2.0/24").validate()
    good_cidr_accepted = True
except RuntimeError:
    good_cidr_accepted = False
check("a well-formed TRUSTED_PROXY_CIDRS starts", good_cidr_accepted)
_set_cidrs(_original_cidrs)


# ===========================================================================
print("\n[ITEM-8a] Outbound guard: scheme, credentials and host shape")
# ===========================================================================

NO_DNS = lambda host, port: (_ for _ in ()).throw(AssertionError("DNS must not be consulted"))  # noqa: E731


def refused(url: str, resolver=NO_DNS) -> bool:
    try:
        url_guard.validate_outbound_url(url, resolver=resolver)
    except url_guard.UnsafeURLError:
        return True
    return False


check("an http URL is refused", refused("http://93.184.216.34/hook"))
check("an ftp URL is refused", refused("ftp://93.184.216.34/file"))
check("a file URL is refused", refused("file:///etc/passwd"))
check("a URL with embedded credentials is refused", refused("https://user:pass@93.184.216.34/"))
check("an empty URL is refused", refused(""))
check("a public https address literal is accepted", not refused("https://93.184.216.34/hook"))
check("a public https name is accepted when it resolves publicly", not refused("https://hooks.example.com/x", resolver=lambda h, p: ["93.184.216.34"]))


# ===========================================================================
print("\n[ITEM-8b] Outbound guard: every blocked range is refused (address literals)")
# ===========================================================================

BLOCKED = [
    "127.0.0.1", "127.255.255.254",  # loopback
    "169.254.169.254", "169.254.0.1",  # link-local, incl. metadata
    "10.0.0.5", "10.255.255.255",  # RFC 1918
    "172.16.0.1", "172.31.255.255",  # RFC 1918
    "192.168.1.1",  # RFC 1918
    "100.64.0.1", "100.127.255.254",  # carrier-grade NAT
    "0.0.0.0", "0.1.2.3",  # 0.0.0.0/8
    "::1",  # IPv6 loopback
    "::",  # IPv6 unspecified
    "fc00::1", "fd12:3456::1",  # IPv6 unique local
    "fe80::1",  # IPv6 link-local
    "::ffff:127.0.0.1", "::ffff:169.254.169.254",  # IPv4-mapped
    "64:ff9b::7f00:1",  # NAT64 of loopback
    "224.0.0.1", "240.0.0.1",  # multicast, reserved
]
for ip in BLOCKED:
    url = f"https://[{ip}]/" if ":" in ip else f"https://{ip}/"
    check(f"blocked destination {ip} is refused", refused(url))

check("the bracketed IPv6 loopback literal is refused", refused("https://[::1]:8443/x"))
check("localhost is refused by name, without DNS", refused("https://localhost/x"))
check("a name under .localhost is refused by name", refused("https://api.localhost/x"))
check("a public address literal is still accepted after the blocked list", not refused("https://8.8.8.8/x"))
check("a public IPv6 literal is accepted", not refused("https://[2606:4700:4700::1111]/x"))


# ===========================================================================
print("\n[ITEM-8c] Outbound guard: a name is refused if ANY answer is blocked")
# ===========================================================================

check("a name resolving to the metadata address is refused", refused("https://evil.example.com/", resolver=lambda h, p: ["169.254.169.254"]))
check("a name with one private answer among public ones is refused", refused("https://mixed.example.com/", resolver=lambda h, p: ["93.184.216.34", "10.0.0.7"]))
check("a name resolving to loopback is refused", refused("https://loop.example.com/", resolver=lambda h, p: ["127.0.0.1"]))
check("a name that resolves to nothing is refused", refused("https://nothing.example.com/", resolver=lambda h, p: []))
check("a name whose resolution fails is refused", refused("https://broken.example.com/", resolver=lambda h, p: (_ for _ in ()).throw(OSError("nxdomain"))))


# ===========================================================================
print("\n[ITEM-8d] Outbound guard: DNS answer pinned, resolved once, no rebinding")
# ===========================================================================

calls = {"n": 0}


def rebinding_resolver(host, port):
    # First answer is public; a second lookup would return loopback.
    calls["n"] += 1
    return ["93.184.216.34"] if calls["n"] == 1 else ["127.0.0.1"]


seen_targets = []


def recording_transport(target, method, headers, body, timeout):
    seen_targets.append(target)
    return url_guard.OutboundResponse(status=200, headers={}, body=b"[]")


resp = url_guard.fetch("https://rebind.example.com/data", resolver=rebinding_resolver, transport=recording_transport)
check("a public name is fetched", resp.status == 200, f"status={resp.status}")
check("the name is resolved exactly once per hop", calls["n"] == 1, f"lookups={calls['n']}")
check("the connection goes to the address validated at the first lookup", seen_targets and seen_targets[0].ip == "93.184.216.34", f"ip={seen_targets[0].ip if seen_targets else None}")
check("the TLS name and Host header stay the original name", seen_targets[0].host == "rebind.example.com" and seen_targets[0].host_header == "rebind.example.com")

# Unauthorised counterpart: the same name, looked up again, would be refused.
second_refused = refused("https://rebind.example.com/data", resolver=rebinding_resolver)
check("a second lookup of the same name returns a blocked address and is refused", second_refused)


# ===========================================================================
print("\n[ITEM-8e] Outbound guard: every redirect hop is re-validated, and capped")
# ===========================================================================


def scripted(responses):
    queue = list(responses)
    log = []

    def transport(target, method, headers, body, timeout):
        log.append({"url": target.url, "method": method, "headers": dict(headers)})
        status, location = queue.pop(0)
        hdrs = {"location": location} if location else {}
        return url_guard.OutboundResponse(status=status, headers=hdrs, body=b"")

    return transport, log


public_resolver = lambda host, port: ["93.184.216.34"]  # noqa: E731

# Authorised: a redirect to another public https host is followed.
transport, log = scripted([(302, "https://cdn.example.com/final"), (200, None)])
resp = url_guard.fetch("https://start.example.com/", resolver=public_resolver, transport=transport)
check("a redirect to a public https host is followed", resp.status == 200 and len(log) == 2, f"status={resp.status} hops={len(log)}")

# Unauthorised: a redirect to a loopback name is refused, and never requested.
hits = {"n": 0}
transport, log = scripted([(302, "https://internal.example.com/admin"), (200, None)])
try:
    url_guard.fetch(
        "https://start.example.com/",
        resolver=lambda h, p: ["93.184.216.34"] if h == "start.example.com" else ["127.0.0.1"],
        transport=transport,
    )
    redirect_refused = False
except url_guard.UnsafeURLError:
    redirect_refused = True
check("a redirect to an internal name is refused", redirect_refused)
check("the refused redirect target is never requested", len(log) == 1, f"requests={len(log)}")

# Unauthorised: a redirect to the metadata address is refused.
transport, log = scripted([(302, "http://169.254.169.254/latest/meta-data/"), (200, None)])
try:
    url_guard.fetch("https://start.example.com/", resolver=public_resolver, transport=transport)
    meta_refused = False
except url_guard.UnsafeURLError:
    meta_refused = True
check("a redirect to the metadata service is refused", meta_refused and len(log) == 1)

# Unauthorised: a redirect downgrading to http is refused.
transport, log = scripted([(301, "http://start.example.com/plain"), (200, None)])
try:
    url_guard.fetch("https://start.example.com/", resolver=public_resolver, transport=transport)
    downgrade_refused = False
except url_guard.UnsafeURLError:
    downgrade_refused = True
check("a redirect downgrading to http is refused", downgrade_refused and len(log) == 1)

# Cap: an endless redirect chain is stopped at the limit.
transport, log = scripted([(302, "https://loop.example.com/")] * 10)
try:
    url_guard.fetch("https://loop.example.com/", resolver=public_resolver, transport=transport, max_redirects=3)
    capped = False
except url_guard.UnsafeURLError as exc:
    capped = "too many redirects" in str(exc)
check("an endless redirect chain is stopped at the cap", capped and len(log) == 4, f"requests={len(log)}")

# Credentials for the origin host are not sent to a different host.
transport, log = scripted([(302, "https://other.example.com/x"), (200, None)])
url_guard.fetch("https://start.example.com/", headers={"Authorization": "Basic c2VjcmV0"}, resolver=public_resolver, transport=transport)
check("Authorization is dropped when a redirect leaves the origin host", "Authorization" not in log[1]["headers"], f"headers={log[1]['headers']}")

# ...and kept when the redirect stays on the origin host.
transport, log = scripted([(302, "https://start.example.com/next"), (200, None)])
url_guard.fetch("https://start.example.com/", headers={"Authorization": "Basic c2VjcmV0"}, resolver=public_resolver, transport=transport)
check("Authorization is kept on a same-host redirect", log[1]["headers"].get("Authorization") == "Basic c2VjcmV0")

# A 303 turns a POST into a GET and drops the body.
transport, log = scripted([(303, "https://start.example.com/done"), (200, None)])
url_guard.fetch("https://start.example.com/", method="POST", body=b"{}", resolver=public_resolver, transport=transport)
check("a 303 redirect becomes a GET", log[1]["method"] == "GET")


# ===========================================================================
print("\n[ITEM-8f] Call sites route through the guard (webhook delivery, integration check)")
# ===========================================================================

from app.models.integrations_platform import Webhook, WebhookDelivery  # noqa: E402
from app.models.client_onboarding import Integration  # noqa: E402
from app.crud import crud_client_onboarding  # noqa: E402

_db = SessionLocal()
_hook_internal = Webhook(url="https://127.0.0.1/hook", events="test", secret=None, is_active=True)
_hook_http = Webhook(url="http://93.184.216.34/hook", events="test", secret=None, is_active=True)
_hook_public = Webhook(url="https://93.184.216.34/hook", events="test", secret=None, is_active=True)
_db.add_all([_hook_internal, _hook_http, _hook_public])
_db.commit()
HOOK_INTERNAL, HOOK_HTTP, HOOK_PUBLIC = _hook_internal.id, _hook_http.id, _hook_public.id
_db.close()

_sa_headers = None
from app.core.security import create_access_token  # noqa: E402

_tok = client.post("/api/v1/auth/login", json={"username": "lp_lock_ok", "password": PASSWORD})
# Use a SuperAdmin for the webhook route, created here for the purpose.
_sess = SessionLocal()
_sa = _sess.query(User).filter(User.username == "lp_net_super").first()
if _sa is None:
    _sa = User(username="lp_net_super", email="lp_net_super@example.com", hashed_password=get_password_hash(PASSWORD), role="SuperAdmin", is_active=True, mfa_enabled=True, must_change_password=False)
    _sess.add(_sa)
    _sess.commit()
_sess.close()
_super_tok = login("lp_net_super", PASSWORD).json()["access_token"]
SUPER = {"Authorization": f"Bearer {_super_tok}"}

r = client.post(f"/api/v1/platform/webhooks/{HOOK_INTERNAL}/deliver", headers=SUPER)
check("a webhook to a loopback address is recorded as Failed", r.status_code == 201 and r.json().get("status") == "Failed", f"got {r.status_code}: {r.text[:160]}")
r = client.post(f"/api/v1/platform/webhooks/{HOOK_HTTP}/deliver", headers=SUPER)
check("a webhook over plain http is recorded as Failed", r.status_code == 201 and r.json().get("status") == "Failed", f"got {r.status_code}: {r.text[:160]}")

# Authorised: a public https destination is delivered, through the same guard.
_seen = []
_real_transport = url_guard._https_transport


def _fake_delivery(target, method, headers, body, timeout):
    _seen.append((target.ip, method, target.host))
    return url_guard.OutboundResponse(status=200, headers={}, body=b"ok")


url_guard._https_transport = _fake_delivery
try:
    r = client.post(f"/api/v1/platform/webhooks/{HOOK_PUBLIC}/deliver", headers=SUPER)
finally:
    url_guard._https_transport = _real_transport
check("a webhook to a public https address is delivered", r.status_code == 201 and r.json().get("status") == "Delivered", f"got {r.status_code}: {r.text[:160]}")
check("the delivery went to the pinned public address via POST", _seen == [("93.184.216.34", "POST", "93.184.216.34")], f"seen={_seen}")

# Integration connectivity check: refused for http and for a blocked address.
from app.models.client_onboarding import Client as _Client  # noqa: E402

_db = SessionLocal()
_cl = _Client(name="LP Net Client", slug="lp-net-client")
_db.add(_cl); _db.commit()
_CLIENT_ID = _cl.id
_int_http = Integration(client_id=_CLIENT_ID, name="lp int http", kind="rest", endpoint="http://93.184.216.34/api", status="unconfigured")
_int_internal = Integration(client_id=_CLIENT_ID, name="lp int internal", kind="rest", endpoint="https://169.254.169.254/latest", status="unconfigured")
_int_public = Integration(client_id=_CLIENT_ID, name="lp int public", kind="rest", endpoint="https://93.184.216.34/api", status="unconfigured")
_db.add_all([_int_http, _int_internal, _int_public])
_db.commit()
_db.refresh(_int_http); _db.refresh(_int_internal); _db.refresh(_int_public)
_db.close()

_sess = SessionLocal()
_i1 = _sess.get(Integration, _int_http.id)
crud_client_onboarding.test_integration(_sess, _i1)
check("the connectivity check refuses plain http", _i1.status == "error" and "https" in (_i1.last_error or ""), f"status={_i1.status} err={_i1.last_error}")
_i2 = _sess.get(Integration, _int_internal.id)
crud_client_onboarding.test_integration(_sess, _i2)
check("the connectivity check refuses the metadata address", _i2.status == "error" and "blocked" in (_i2.last_error or ""), f"status={_i2.status} err={_i2.last_error}")
url_guard._https_transport = _fake_delivery
try:
    _i3 = _sess.get(Integration, _int_public.id)
    crud_client_onboarding.test_integration(_sess, _i3)
finally:
    url_guard._https_transport = _real_transport
check("the connectivity check reports a public https endpoint as connected", _i3.status == "connected", f"status={_i3.status} err={_i3.last_error}")
_sess.close()


# ===========================================================================
print(f"\n{'=' * 60}")
total = RESULTS["pass"] + RESULTS["fail"]
print(f"==== LP PHASE 2 NETWORK SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed of {total} ====")
if FAILURES:
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 60)
raise SystemExit(0 if RESULTS["fail"] == 0 else 1)
