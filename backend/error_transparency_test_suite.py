"""Error-transparency regression suite.

Covers two failures that made production incidents harder to diagnose:

* An uncaught exception (including database outages classified as
  ``dependency_unavailable``) is handled by Starlette's ServerErrorMiddleware,
  which sits outside CORSMiddleware. Its response therefore used to carry no
  Access-Control-Allow-Origin and no X-Request-ID, and the browser reported a
  5xx as a CORS error. The handler now adds those headers itself.
* The shared error envelope and Retry-After behaviour must stay unchanged.

Run:  python error_transparency_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="error_transparency_test_"), "error_transparency_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = "https://app.example.com"
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine  # noqa: E402

Base.metadata.create_all(bind=engine)

ALLOWED_ORIGIN = "https://app.example.com"
DISALLOWED_ORIGIN = "https://evil.example.com"


@app.get("/api/v1/__test/unhandled-dependency")
def _raise_dependency_failure():
    raise RuntimeError("database connection lost")


@app.get("/api/v1/__test/unhandled-internal")
def _raise_internal_failure():
    raise RuntimeError("boom")


# raise_server_exceptions=False lets the registered Exception handler build the
# response, exactly as it does in production.
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


def envelope(response) -> dict:
    try:
        return response.json().get("error", {})
    except Exception:
        return {}


print("=" * 68)
print("ERROR TRANSPARENCY SUITE")
print("=" * 68)

# --- AC-01: an allowed origin gets CORS on an unhandled 503 ----------------
print("\nAC-01: unhandled dependency failure carries CORS for an allowed origin")
r = client.get(
    "/api/v1/__test/unhandled-dependency",
    headers={"Origin": ALLOWED_ORIGIN, "X-Request-ID": "trace-allowed-123"},
)
body = envelope(r)
check("status is 503", r.status_code == 503, f"got {r.status_code}")
check(
    "Access-Control-Allow-Origin echoes the allowed origin",
    r.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN,
    f"got {r.headers.get('access-control-allow-origin')!r}",
)
check(
    "Vary includes Origin",
    "origin" in r.headers.get("vary", "").lower(),
    f"got {r.headers.get('vary')!r}",
)
check(
    "Access-Control-Allow-Credentials is not added",
    "access-control-allow-credentials" not in r.headers,
    f"got {r.headers.get('access-control-allow-credentials')!r}",
)

# --- AC-02: traceability on the same response ------------------------------
print("\nAC-02: unhandled failure response includes X-Request-ID")
rid = r.headers.get("x-request-id")
check("X-Request-ID is present and non-empty", bool(rid), f"got {rid!r}")
check(
    "inbound X-Request-ID is echoed",
    rid == "trace-allowed-123",
    f"got {rid!r}",
)
check(
    "envelope keeps the request_id field",
    "request_id" in body,
    f"body={body!r}",
)

# --- AC-01: a disallowed origin gets no CORS allowance ---------------------
print("\nAC-01: a disallowed origin is not reflected")
r = client.get(
    "/api/v1/__test/unhandled-dependency",
    headers={"Origin": DISALLOWED_ORIGIN},
)
check("status is still 503", r.status_code == 503, f"got {r.status_code}")
check(
    "no Access-Control-Allow-Origin for a disallowed origin",
    r.headers.get("access-control-allow-origin") is None,
    f"got {r.headers.get('access-control-allow-origin')!r}",
)
check(
    "X-Request-ID is still present",
    bool(r.headers.get("x-request-id")),
    f"got {r.headers.get('x-request-id')!r}",
)

# --- AC-01: no Origin means no CORS header ---------------------------------
print("\nAC-01: a request without Origin gets no CORS header")
r = client.get("/api/v1/__test/unhandled-dependency")
check(
    "no Access-Control-Allow-Origin without an Origin header",
    r.headers.get("access-control-allow-origin") is None,
    f"got {r.headers.get('access-control-allow-origin')!r}",
)
check(
    "X-Request-ID is generated when the client sends none",
    bool(r.headers.get("x-request-id")),
    f"got {r.headers.get('x-request-id')!r}",
)

# --- AC-03: envelope and Retry-After are unchanged ------------------------
print("\nAC-03: dependency envelope and Retry-After are unchanged")
r = client.get(
    "/api/v1/__test/unhandled-dependency",
    headers={"Origin": ALLOWED_ORIGIN},
)
body = envelope(r)
check("envelope has the error object", bool(body), f"body={r.text[:200]!r}")
check("code is dependency_unavailable", body.get("code") == "dependency_unavailable", f"got {body.get('code')!r}")
check("category is dependency", body.get("category") == "dependency", f"got {body.get('category')!r}")
check("retryable is true", body.get("retryable") is True, f"got {body.get('retryable')!r}")
check(
    "message is the safe dependency message",
    isinstance(body.get("message"), str) and "temporarily unavailable" in body["message"],
    f"got {body.get('message')!r}",
)
check("Retry-After is 5", r.headers.get("retry-after") == "5", f"got {r.headers.get('retry-after')!r}")

# --- internal errors keep their own 500 envelope --------------------------
print("\nAC-03: an unclassified exception keeps the internal 500 envelope")
r = client.get(
    "/api/v1/__test/unhandled-internal",
    headers={"Origin": ALLOWED_ORIGIN},
)
body = envelope(r)
check("status is 500", r.status_code == 500, f"got {r.status_code}")
check("code is internal_error", body.get("code") == "internal_error", f"got {body.get('code')!r}")
check("Retry-After is absent", r.headers.get("retry-after") is None, f"got {r.headers.get('retry-after')!r}")
check(
    "CORS is still applied to the 500",
    r.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN,
    f"got {r.headers.get('access-control-allow-origin')!r}",
)
check("X-Request-ID is present on the 500", bool(r.headers.get("x-request-id")), f"got {r.headers.get('x-request-id')!r}")

# ===========================================================================
print("\n" + "=" * 62)
print(f"==== ERROR TRANSPARENCY SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 62)
raise SystemExit(1 if RESULTS["fail"] else 0)
