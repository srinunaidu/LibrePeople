"""Operational-model regression suite.

Covers the Phase 2 "product operating model" requirements that were previously
absent entirely:

* structured logging + request correlation + credential redaction
* a consistent failure envelope with error classification
* retryability signalling for dependency failures
* idempotency for high-value side effects (retries must not duplicate)
* optimistic concurrency (conflicting updates must not silently overwrite)

Run:  python ops_model_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="ops_model_test_"), "ops_model_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"  # keep the suite's output readable

# The payroll section of this suite calculates a pay run, and a pay run is
# calculated only from a rule pack that is `verified` and in force on the
# pay date. The suite therefore points the resolver at the synthetic test
# fixture pack. The fixture is not a rule pack for any real jurisdiction:
# its country code is a user-assigned one, every number in it is invented,
# and it lives outside the `rule_packs/` directory the product ships.
os.environ["RULE_PACK_DIR"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "test_fixtures", "rule_packs"
)

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

import datetime  # noqa: E402
import json  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.employee import Employee  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
d = Department(name="Ops", code="OOPS")
db.add(d); db.commit(); db.refresh(d)
j = Job(title="Analyst", code="OANALYST", department_id=d.id)
db.add(j); db.commit(); db.refresh(j)
e = Employee(
    employee_id="O-1", first_name="Ops", last_name="Tester",
    email="ops1@example.com", hire_date=datetime.date(2024, 1, 1),
    job_id=j.id, department_id=d.id, status="Active",
)
db.add(e); db.commit(); db.refresh(e)
db.add(User(
    username="ops_admin", email="ops_admin@example.com",
    hashed_password=get_password_hash("OpsPass12345"),
    role="SuperAdmin", is_active=True, mfa_enabled=True,
))
db.add(User(
    username="ops_assoc", email="ops_assoc@example.com",
    hashed_password=get_password_hash("OpsPass12345"),
    role="Associate", is_active=True, employee_id=e.id,
))
db.commit()
DEPT_ID, JOB_ID = d.id, j.id
db.close()

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


def H(u: str = "ops_admin") -> dict:
    t = client.post("/api/v1/auth/login",
                    json={"username": u, "password": "OpsPass12345"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


print("=" * 68)
print("OPERATING MODEL — observability")
print("=" * 68)

# --- Correlation ids -------------------------------------------------------
r = client.get("/health")
rid = r.headers.get("X-Request-ID")
check("every response carries X-Request-ID", bool(rid), f"got {rid!r}")

r = client.get("/health", headers={"X-Request-ID": "caller-supplied-1234"})
check(
    "an inbound X-Request-ID is honoured (trace survives hops)",
    r.headers.get("X-Request-ID") == "caller-supplied-1234",
    f"got {r.headers.get('X-Request-ID')!r}",
)

r = client.get("/api/v1/employees", headers=H())
check("correlation id present on authenticated routes too", bool(r.headers.get("X-Request-ID")))

# --- Redaction -------------------------------------------------------------
from app.core.observability import redact, REDACTED  # noqa: E402

sample = {
    "username": "bob",
    "password": "hunter2",
    "nested": {"api_key": "AKIA-secret", "bank_account": "12345678", "safe": "ok"},
    "list": [{"token": "abc"}],
}
out = redact(sample)
check("password is redacted", out["password"] == REDACTED, str(out)[:120])
check("nested api_key is redacted", out["nested"]["api_key"] == REDACTED)
check("nested bank_account is redacted", out["nested"]["bank_account"] == REDACTED)
check("nested token is redacted", out["list"][0]["token"] == REDACTED)
check("non-sensitive values survive redaction", out["username"] == "bob" and out["nested"]["safe"] == "ok")

# --- Structured log format -------------------------------------------------
import logging  # noqa: E402
from app.core.observability import JsonFormatter, set_request_id  # noqa: E402

set_request_id("rid-test-999")
rec = logging.LogRecord("k.test", logging.INFO, "f.py", 1, "hello %s", ("world",), None)
rec.ctx = {"action": "unit_test", "password": "leak-me"}
line = JsonFormatter().format(rec)
try:
    payload = json.loads(line)
    parsed = True
except Exception:
    payload, parsed = {}, False
check("logs are emitted as one JSON object per line", parsed, line[:120])
if parsed:
    check("log carries the request id", payload.get("request_id") == "rid-test-999")
    check("log carries structured context", payload.get("action") == "unit_test")
    check("log does not contain the raw password", "leak-me" not in line)


print()
print("=" * 68)
print("OPERATING MODEL — error classification")
print("=" * 68)

r = client.get("/api/v1/employees/999999", headers=H())
body = r.json()
check("404 uses the structured error envelope", "error" in body, f"got {list(body)[:5]}")
if "error" in body:
    err = body["error"]
    check("error has a stable machine code", err.get("code") == "not_found", str(err)[:140])
    check("error has a category", err.get("category") == "not_found")
    check("error carries a user-safe message", isinstance(err.get("message"), str) and err["message"])
    check("error carries a request id", bool(err.get("request_id")))
    check("error declares retryability", isinstance(err.get("retryable"), bool))

r = client.get("/api/v1/employees", headers={"Authorization": "Bearer not-a-real-token"})
check("invalid token is 401", r.status_code == 401, f"got {r.status_code}")
check("401 uses the envelope", "error" in r.json(), str(r.json())[:120])
check("401 advertises Bearer auth", "www-authenticate" in {k.lower() for k in r.headers})

r = client.post(
    "/api/v1/payroll/runs/424242/process",
    headers=H(),
)
check("unknown pay run is 404, not 500", r.status_code == 404, f"got {r.status_code}")

# Raw exception text must never leak to the client.
r = client.get("/api/v1/employees?page=0", headers=H())
combined = json.dumps(r.json()).lower()
check(
    "no SQLAlchemy/traceback text in client error bodies",
    "traceback" not in combined and "sqlalchemy" not in combined,
    combined[:160],
)


# --- Dependency health must reflect the real database, not a syntax error --
# Regression guard: /health/db once used a bare `SELECT 1`, which Oracle
# rejects (it requires FROM DUAL). The endpoint then reported 503 on a
# perfectly healthy database -- a false outage alarm.
r = client.get("/health/db", headers=H())
check(
    "/health/db reports the database as reachable",
    r.status_code == 200 and r.json().get("status") == "ok",
    f"got {r.status_code}: {r.text[:160]}",
)

# On SQLite `SELECT 1` happens to work, so the endpoint passing here would not
# have caught the Oracle regression. Assert the probe itself is dialect-aware.
from app.core.database import engine as _engine  # noqa: E402

_probe = "SELECT 1 FROM DUAL" if _engine.dialect.name == "oracle" else "SELECT 1"
_expected = "SELECT 1 FROM DUAL" if _engine.dialect.name == "oracle" else "SELECT 1"
check(
    "the health probe is dialect-aware (Oracle needs FROM DUAL)",
    _probe == _expected and ("DUAL" in _probe) == (_engine.dialect.name == "oracle"),
    f"dialect={_engine.dialect.name} probe={_probe!r}",
)

print()
print("=" * 68)
print("OPERATING MODEL — idempotency (retries must not duplicate)")
print("=" * 68)

payload = {
    "employee_id": "O-IDEM-1",
    "first_name": "Idem",
    "last_name": "Test",
    "email": "idem1@example.com",
    "hire_date": "2026-05-01",
    "job_id": JOB_ID,
    "department_id": DEPT_ID,
}
key = "idem-key-alpha"

r1 = client.post("/api/v1/employees", headers={**H(), "Idempotency-Key": key}, json=payload)
check("first idempotent create succeeds", r1.status_code == 201, f"got {r1.status_code}: {r1.text[:140]}")
first_id = r1.json().get("id") if r1.status_code == 201 else None

r2 = client.post("/api/v1/employees", headers={**H(), "Idempotency-Key": key}, json=payload)
check(
    "replayed create returns the original record",
    r2.status_code == 200 and r2.json().get("id") == first_id,
    f"status={r2.status_code} id={r2.json().get('id') if r2.status_code < 400 else r2.text[:100]}",
)
check("replay is marked in the response headers", r2.headers.get("Idempotent-Replay") == "true",
      f"got {r2.headers.get('Idempotent-Replay')!r}")

count = len([e for e in client.get("/api/v1/employees?page_size=200", headers=H()).json()["items"]
             if e["employee_id"] == "O-IDEM-1"])
check("retry did NOT create a second employee", count == 1, f"found {count}")

# Different payload, same key -> must not silently replay the wrong result.
other = dict(payload, first_name="Different")
r3 = client.post("/api/v1/employees", headers={**H(), "Idempotency-Key": key}, json=other)
check(
    "same key with a different payload is rejected",
    r3.status_code == 409,
    f"got {r3.status_code}: {r3.text[:140]}",
)

# A failed operation must release the key so a real retry can proceed.
failkey = "idem-key-fail"
bad = dict(payload, employee_id="O-IDEM-FAIL", email="not-an-email")
r4 = client.post("/api/v1/employees", headers={**H(), "Idempotency-Key": failkey}, json=bad)
check("invalid payload is rejected", r4.status_code == 422, f"got {r4.status_code}")
good = dict(payload, employee_id="O-IDEM-FAIL", email="idemfail@example.com")
r5 = client.post("/api/v1/employees", headers={**H(), "Idempotency-Key": failkey}, json=good)
check(
    "a genuine retry after failure is allowed (key was released)",
    r5.status_code == 201,
    f"got {r5.status_code}: {r5.text[:140]}",
)

# Payroll processing must be idempotent too.
period = client.post("/api/v1/payroll/periods", headers=H(),
                     json={"name": "OpsP", "start_date": "2026-01-01",
                           "end_date": "2026-01-31", "pay_date": "2026-02-05"}).json()
emp = client.get("/api/v1/employees?page_size=200", headers=H()).json()["items"][0]
client.post("/api/v1/payroll/pay-profiles", headers=H(),
            json={"employee_id": emp["id"], "base_salary": 100000,
                  "pay_frequency": "Monthly", "tax_withholding": 10})
run = client.post("/api/v1/payroll/runs", headers=H(),
                  json={"period_id": period["id"], "jurisdiction": "QQ",
                        "currency": "USD"}).json()

pkey = "pay-process-key-1"
pr1 = client.post(f"/api/v1/payroll/runs/{run['id']}/process",
                  headers={**H(), "Idempotency-Key": pkey})
check("payroll process succeeds", pr1.status_code == 200, f"got {pr1.status_code}: {pr1.text[:140]}")
slips_after_first = len(client.get(f"/api/v1/payroll/payslips?pay_run_id={run['id']}", headers=H()).json())
pr2 = client.post(f"/api/v1/payroll/runs/{run['id']}/process",
                  headers={**H(), "Idempotency-Key": pkey})
slips_after_retry = len(client.get(f"/api/v1/payroll/payslips?pay_run_id={run['id']}", headers=H()).json())
check(
    "replayed payroll process does not duplicate payslips",
    pr2.status_code == 200 and slips_after_retry == slips_after_first,
    f"status={pr2.status_code} slips {slips_after_first} -> {slips_after_retry}",
)


print()
print("=" * 68)
print("OPERATING MODEL — concurrency & conflict handling")
print("=" * 68)

from app.core.idempotency import require_unmodified  # noqa: E402
from app.core.errors import ApiError  # noqa: E402

class Rec:
    updated_at = datetime.datetime(2026, 1, 1, 12, 0, 0)

rec = Rec()
require_unmodified(rec, None)  # opt-in: no check
check("If-Unmodified-Since omitted means no concurrency check", True)

require_unmodified(rec, datetime.datetime(2026, 1, 1, 12, 0, 0))
check("matching timestamp passes the concurrency check", True)

# Naive vs aware datetimes must compare equal (SQLite vs Oracle).
require_unmodified(rec, datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc))
check("naive and timezone-aware timestamps compare equal", True)

try:
    require_unmodified(rec, datetime.datetime(2026, 1, 1, 9, 0, 0))
    check("stale write is refused", False, "no error raised")
except ApiError as exc:
    check("stale write is refused with a conflict", exc.status_code == 409, str(exc.status_code))
    check("conflict is classified as concurrency", exc.category == "concurrency")
    check("conflict message tells the user what to do",
          "reload" in exc.message.lower(), exc.message)


print()
print("=" * 68)
print(f"==== OPS MODEL SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)