"""Security headers regression suite.

Covers the platform's HTTP security headers (Gate 0A #1 / section P-07):

* Content-Security-Policy
* Strict-Transport-Security (production + HTTPS only)
* X-Content-Type-Options: nosniff
* X-Frame-Options: DENY
* Referrer-Policy: strict-origin-when-cross-origin

Headers must be present on every response, including error responses.

Run:  python security_headers_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="security_headers_test_"), "security_headers_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["ENVIRONMENT"] = "production"  # HSTS only applies in production
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine  # noqa: E402

Base.metadata.create_all(bind=engine)

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


EXPECTED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "content-security-policy": None,  # any non-empty value is acceptable
}


def _has_all_headers(headers) -> bool:
    lower = {k.lower(): v for k, v in headers.items()}
    for key, expected in EXPECTED_HEADERS.items():
        if key not in lower:
            return False
        if expected is not None and lower[key] != expected:
            return False
    return True


def _header_values(headers):
    lower = {k.lower(): v for k, v in headers.items()}
    return {
        "x-content-type-options": lower.get("x-content-type-options"),
        "x-frame-options": lower.get("x-frame-options"),
        "referrer-policy": lower.get("referrer-policy"),
        "content-security-policy": lower.get("content-security-policy"),
        "strict-transport-security": lower.get("strict-transport-security"),
    }


print("=" * 68)
print("SECURITY HEADERS SUITE")
print("=" * 68)

# --- Every response carries the headers --------------------------------

for path, method in [("GET", "/health"), ("GET", "/api/v1/openapi.json")]:
    r = client.request(method, path)
    vals = _header_values(r.headers)
    check(
        f"{method} {path} carries security headers",
        _has_all_headers(r.headers),
        f"got {vals}",
    )
    check(
        f"{method} {path} CSP is not empty",
        bool(vals["content-security-policy"]),
        f"csp={vals['content-security-policy']!r}",
    )

# --- 404 response also carries headers ---------------------------------
r = client.get("/api/v1/does-not-exist")
check(
    "404 response carries security headers",
    _has_all_headers(r.headers),
    f"got {_header_values(r.headers)}",
)

# --- 401 response also carries headers ---------------------------------
r = client.get("/api/v1/auth/me")
check(
    "401 response carries security headers",
    _has_all_headers(r.headers),
    f"got {_header_values(r.headers)}",
)

# --- 422 response also carries headers ---------------------------------
r = client.post("/auth/login", json={"username": "x"})
check(
    "422 response carries security headers",
    _has_all_headers(r.headers),
    f"got {_header_values(r.headers)}",
)

# --- HSTS absent on non-HTTPS (default test client is HTTP) ------------
r = client.get("/health")
check(
    "HSTS absent on plain-HTTP response",
    "strict-transport-security" not in {k.lower() for k in r.headers},
    f"got hsts={r.headers.get('strict-transport-security')!r}",
)

print()
print("=" * 68)
print(f"SECURITY HEADERS SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print()
    print("Failures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
