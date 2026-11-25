"""The public contact intake: an unauthenticated door that is not an open one.

What this suite proves
----------------------
* a visitor's message is accepted with no token, and it becomes a case in
  the intake state;
* the schema is closed: a request carrying an employee id, a tenant id, a
  case category or a comment is refused, and a message that is not text is
  refused;
* a body over the size limit is refused with 413;
* the per-IP rate limit and the per-IP daily cap both apply, and a request
  over either is refused with the shared error envelope;
* the audit row records the case and the source, and neither the address nor
  the message reaches the audit trail or the log;
* the case queue does not show the intake among its own cases, and the
  intake is asked for by name;
* the migration adds the columns the intake needs, and its downgrade
  removes exactly what it added.

Run:  python public_contact_test_suite.py
"""
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="public_contact_test_suite_"), "public_contact_test_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
# The log level is INFO on purpose. The privacy check reads the log, and a
# log level that silences it would make the check true by accident.
os.environ["LOG_LEVEL"] = "INFO"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.core_hr import HRCase  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


class _LogCapture(logging.Handler):
    """Collects the log lines the application writes."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.lines.append(self.format(record))
        except Exception:  # noqa: BLE001
            self.lines.append(str(record.msg))


logging.getLogger("httpx").setLevel(logging.WARNING)

capture = _LogCapture()
capture.setFormatter(logging.getLogger().handlers[0].formatter if logging.getLogger().handlers else None)
logging.getLogger().addHandler(capture)

PASSWORD = "PublicContactPass123"

db = SessionLocal()
db.add(
    User(
        username="contact_hr",
        email="contact_hr@example.com",
        hashed_password=get_password_hash(PASSWORD),
        role="HR",
        is_active=True,
    )
)
db.commit()
db.close()



client = TestClient(app, raise_server_exceptions=False)

token = client.post(
    "/api/v1/auth/login",
    json={"username": "contact_hr", "password": PASSWORD},
).json()["access_token"]
H_HR = {"Authorization": f"Bearer {token}"}


def _from(address: str) -> dict:
    """Headers that make the request look like it came from ``address``."""
    return {"X-Forwarded-For": address}


# ===========================================================================
print("\n[PUBLIC-1] A visitor's message is accepted")
# ===========================================================================

VISITOR_EMAIL = "visitor@example.com"
VISITOR_MESSAGE = "I would like to know whether you support on-site childcare."

r = client.post(
    "/api/v1/public/contact",
    headers=_from("203.0.113.10"),
    json={
        "name": "A Visitor",
        "email": VISITOR_EMAIL,
        "message": VISITOR_MESSAGE,
    },
)
check("a message with no token is accepted", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
check(
    "the sender is told the message was received, and nothing else",
    r.status_code == 201 and r.json() == {"received": True},
    f"got {r.text[:200]}",
)
check(
    "the receipt does not carry the case id",
    r.status_code == 201 and "id" not in r.json(),
    f"got {r.text[:200]}",
)

db = SessionLocal()
intake = db.query(HRCase).order_by(HRCase.id.desc()).first()
check("the message became a case", intake is not None, "no case was created")
check(
    "the case is in the intake state, which is a state of its own",
    intake is not None and intake.status == "Intake",
    f"status={intake.status if intake else None}",
)
check(
    "the case says where it came from",
    intake is not None and intake.source == "public_contact",
    f"source={intake.source if intake else None}",
)
check(
    "the case carries no employee and no case of its own",
    intake is not None
    and intake.employee_id is None
    and intake.assigned_to is None
    and intake.sla_due is None,
    f"employee={intake.employee_id if intake else None}",
)
check(
    "the case holds the sender's name, address and message",
    intake is not None
    and intake.subject == "A Visitor"
    and intake.sender_email == VISITOR_EMAIL
    and intake.message == VISITOR_MESSAGE,
    f"case={intake.subject if intake else None}",
)

r = client.get("/api/v1/core-hr/cases", headers=H_HR)
check(
    "the case queue does not show the intake among its own cases",
    r.status_code == 200 and all(case["id"] != intake.id for case in r.json()),
    f"got {r.status_code}: {r.text[:200]}",
)
r = client.get("/api/v1/core-hr/cases?status=Intake", headers=H_HR)
check(
    "the queue shows the intake when it is asked for by name",
    r.status_code == 200 and any(case["id"] == intake.id for case in r.json()),
    f"got {r.status_code}: {r.text[:200]}",
)

# ===========================================================================
print("\n[PUBLIC-2] The schema is closed")
# ===========================================================================

for field, value in (
    ("employee_id", 1),
    ("tenant_id", "acme"),
    ("category", "Payroll"),
    ("comment", "a comment"),
    ("priority", "Urgent"),
):
    r = client.post(
        "/api/v1/public/contact",
        headers=_from("203.0.113.11"),
        json={
            "name": "A Visitor",
            "email": VISITOR_EMAIL,
            "message": "hello",
            field: value,
        },
    )
    check(
        f"a request carrying {field} is refused",
        r.status_code == 422,
        f"got {r.status_code}: {r.text[:160]}",
    )

before = db.query(HRCase).count()
client.post(
    "/api/v1/public/contact",
    headers=_from("203.0.113.12"),
    json={
        "name": "A Visitor",
        "email": VISITOR_EMAIL,
        "message": "hello",
        "employee_id": 1,
    },
)
check(
    "a refused request creates nothing",
    db.query(HRCase).count() == before,
    "a case was created by a refused request",
)

r = client.post(
    "/api/v1/public/contact",
    headers=_from("203.0.113.13"),
    json={"name": "A Visitor", "email": VISITOR_EMAIL, "message": 42},
)
check(
    "a message that is not text is refused",
    r.status_code == 422,
    f"got {r.status_code}: {r.text[:160]}",
)

r = client.post(
    "/api/v1/public/contact",
    headers=_from("203.0.113.14"),
    json={"name": "A Visitor", "email": VISITOR_EMAIL},
)
check(
    "a request without a message is refused",
    r.status_code == 422,
    f"got {r.status_code}: {r.text[:160]}",
)

# ===========================================================================
print("\n[PUBLIC-3] The body is size limited")
# ===========================================================================

r = client.post(
    "/api/v1/public/contact",
    headers=_from("203.0.113.15"),
    json={
        "name": "A Visitor",
        "email": VISITOR_EMAIL,
        "message": "x" * 20000,
    },
)
check(
    "a body over the size limit is refused with 413",
    r.status_code == 413,
    f"got {r.status_code}: {r.text[:160]}",
)
check(
    "the refusal carries the shared error envelope",
    r.status_code == 413 and "error" in r.json(),
    f"got {r.text[:160]}",
)

# ===========================================================================
print("\n[PUBLIC-4] The rate limit is the control")
# ===========================================================================

from app.core.rate_limit import limiter  # noqa: E402

flood = "203.0.113.20"
statuses = []
for _ in range(8):
    posted = client.post(
        "/api/v1/public/contact",
        headers=_from(flood),
        json={"name": "A Visitor", "email": VISITOR_EMAIL, "message": "hello"},
    )
    statuses.append(posted.status_code)
check(
    "the first messages of a burst are accepted",
    statuses[:5] == [201] * 5,
    f"statuses={statuses}",
)
check(
    "a burst over the limit is refused",
    all(status == 429 for status in statuses[5:]),
    f"statuses={statuses}",
)
r = client.post(
    "/api/v1/public/contact",
    headers=_from(flood),
    json={"name": "A Visitor", "email": VISITOR_EMAIL, "message": "hello"},
)
check(
    "the refusal carries the shared error envelope",
    r.status_code == 429 and r.json().get("error", {}).get("code") == "rate_limited",
    f"got {r.status_code}: {r.text[:160]}",
)

# The daily cap is the second line: it stops a flood that is slow enough to
# stay under the short window, so the test spreads the messages out.
slow = "203.0.113.21"
statuses = []
for _ in range(25):
    limiter.reset("contact", slow)
    posted = client.post(
        "/api/v1/public/contact",
        headers=_from(slow),
        json={"name": "A Visitor", "email": VISITOR_EMAIL, "message": "hello"},
    )
    statuses.append(posted.status_code)
check(
    "the daily cap stops a slow flood",
    statuses[:20] == [201] * 20 and all(status == 429 for status in statuses[20:]),
    f"statuses={statuses}",
)

# ===========================================================================
print("\n[PUBLIC-5] Nothing personal reaches the audit trail or the log")
# ===========================================================================

audit_rows = db.query(AuditLog).filter(AuditLog.action == "public_contact_received").all()
check(
    "the audit row records the case and the source",
    audit_rows
    and audit_rows[0].entity_type == "HRCase"
    and audit_rows[0].entity_id == intake.id
    and "public_contact" in (audit_rows[0].details or ""),
    f"rows={[(row.action, row.entity_id, row.details) for row in audit_rows]}",
)
check(
    "the audit row names no actor, because nobody was signed in",
    all(row.actor_id is None and row.actor_name is None for row in audit_rows),
    f"rows={[(row.actor_id, row.actor_name) for row in audit_rows]}",
)
check(
    "the sender's address is in neither the audit trail nor the log",
    all(VISITOR_EMAIL not in (row.details or "") for row in audit_rows)
    and all(VISITOR_EMAIL not in line for line in capture.lines),
    "the address reached the audit trail or the log",
)
check(
    "the message is in neither the audit trail nor the log",
    all(VISITOR_MESSAGE not in (row.details or "") for row in audit_rows)
    and all(VISITOR_MESSAGE not in line for line in capture.lines),
    "the message reached the audit trail or the log",
)
db.close()



# ===========================================================================
print("\n[MIGRATION-1] The migration, and its downgrade")
# ===========================================================================


def _run_migrations(db_path: str, target: str = "head", direction: str = "upgrade") -> None:
    """Run the migration CLI against a specific database."""
    backend = Path(__file__).resolve().parent
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["ALEMBIC_DATABASE_URL"] = f"sqlite:///{db_path}"
    env["SECRET_KEY"] = os.environ["SECRET_KEY"]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.migrate", direction, target],
        cwd=str(backend),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"migration {direction} {target} failed for {db_path}:\n"
            f"{result.stdout}\n{result.stderr}"
        )


def _columns(db_path: str, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def _indexes(db_path: str, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{table}'"
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def _rows(db_path: str, sql: str) -> list[tuple]:
    conn = sqlite3.connect(db_path)
    try:
        return list(conn.execute(sql).fetchall())
    finally:
        conn.close()


workdir = tempfile.mkdtemp(prefix="karmathy-public-intake-")
try:
    scratch = os.path.join(workdir, "intake.db")
    _run_migrations(scratch, "0010_leave_ledger")

    # The baseline builds the frozen tables from the models, so a fresh
    # database already has the columns. The migration is for the databases
    # that were built before the columns existed, so the old shape is built
    # here: the columns are dropped and a case that predates them is left
    # behind.
    conn = sqlite3.connect(scratch)
    try:
        conn.execute("DROP INDEX IF EXISTS ix_hr_cases_source")
        for column in ("source", "sender_email", "message"):
            conn.execute(f"ALTER TABLE hr_cases DROP COLUMN {column}")
        conn.execute(
            "INSERT INTO hr_cases (id, subject, category, priority, status, created_at) "
            "VALUES (1, 'An existing case', 'Payroll', 'Medium', 'Open', CURRENT_TIMESTAMP)"
        )
        conn.commit()
    finally:
        conn.close()
    check(
        "the intake columns are missing from the old shape",
        not {"source", "sender_email", "message"} & _columns(scratch, "hr_cases"),
        f"columns={sorted(_columns(scratch, 'hr_cases'))}",
    )

    # The migration is run in a subprocess, so a failure in it is a failure
    # of the check and not the end of the suite.
    try:
        _run_migrations(scratch)
        applied = True
        detail = ""
    except Exception as exc:  # noqa: BLE001
        applied = False
        detail = f"{type(exc).__name__}: {exc}"

    check("the migration applies", applied, detail)
    if applied:
        check(
            "the migration adds the columns the intake needs",
            {"source", "sender_email", "message"} <= _columns(scratch, "hr_cases"),
            f"columns={sorted(_columns(scratch, 'hr_cases'))}",
        )
        check(
            "the migration indexes the source, as the models declare",
            "ix_hr_cases_source" in _indexes(scratch, "hr_cases"),
            f"indexes={sorted(_indexes(scratch, 'hr_cases'))}",
        )
        check(
            "the cases that were already there are not changed by the migration",
            _rows(scratch, "SELECT source FROM hr_cases WHERE id = 1") == [("hr",)],
            f"rows={_rows(scratch, 'SELECT source FROM hr_cases WHERE id = 1')}",
        )

    try:
        _run_migrations(scratch, "0010_leave_ledger", "downgrade")
        downgraded = True
        detail = ""
    except Exception as exc:  # noqa: BLE001
        downgraded = False
        detail = f"{type(exc).__name__}: {exc}"

    check("the downgrade applies", downgraded, detail)
    if downgraded:
        check(
            "the downgrade removes the columns it added",
            not {"source", "sender_email", "message"} & _columns(scratch, "hr_cases"),
            f"columns={sorted(_columns(scratch, 'hr_cases'))}",
        )
        check(
            "the downgrade leaves the cases alone",
            _rows(scratch, "SELECT subject FROM hr_cases WHERE id = 1")
            == [("An existing case",)],
            "the case was changed by the downgrade",
        )
finally:
    shutil.rmtree(workdir, ignore_errors=True)

print()
print("=" * 68)
print(f"==== PUBLIC CONTACT SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)

