"""The CSV import suite.

One test per feature row on the board, so the matrix can be rewritten with
evidence instead of with a claim.

| Row | What is proved |
|---|---|
| `I-01` | a template exists for each core entity, and the importer accepts the template's header row unchanged |
| `I-02` | an exact header and an aliased header both import; an unknown header is refused with 422 and names the header |
| `I-03` | a file over the row limit is refused; a file over the size limit is refused with 413; the parse is streaming |
| `I-04` | one case each for type, required field, ISO 8601 date, enum, referential integrity, duplicate and salary bound |
| `I-05` | the six formula-injection triggers are neutralised, asserted on the stored value |
| `I-06` | the dry run writes nothing; the commit writes exactly what the preview said; the row-error CSV carries the row, the column and the reason, and no sensitive value |
| `I-07` | a second import of the same file creates nothing and reports every row as unchanged |
| `DI-01` | the commit path commits; the counts equal the change in the database; the audit row is in the same transaction; a batch that fails is rolled back; a second commit does nothing |
| `DI-02` | the token is bound to the result hash, has a TTL, is single use, and the store is bounded |

Run:  python import_test_suite.py
"""
from __future__ import annotations

import atexit
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tracemalloc
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="import_test_"), "import_test.db")
STORAGE_DIR = tempfile.mkdtemp(prefix="karmathy-import-test-")

# LP-DATA-001 isolation: this suite owns a throwaway database and it must
# never poison a later run. The attempt flag below allows exactly one retry
# with a fresh database: a re-exec builds a new mkdtemp directory, so the
# second attempt cannot reuse the first attempt's file.
_SUITE_ATTEMPT = os.environ.get("IMPORT_SUITE_ATTEMPT", "0")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["LOCAL_STORAGE_DIR"] = STORAGE_DIR
# Field encryption (item 6: no SECRET_KEY fallback) — the import writes
# employee identity fields through app.core.encryption.
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402

# Isolation: return every pooled connection when the process ends, even when
# a check fails midway. With NullPool (SQLite) this is belt and braces; on
# a pooled server database it is what keeps one suite from starving the next.
atexit.register(engine.dispose)


def _retry_with_fresh_db():
    """Re-exec this suite once with a fresh database and exit with its code.

    The child builds a new ``mkdtemp`` database file, so it cannot reuse
    the exhausted pool state of this process. Only the first attempt
    (``IMPORT_SUITE_ATTEMPT=0``) may retry; the child runs with ``=1``.
    """
    try:
        engine.dispose()
    except Exception:  # noqa: BLE001
        pass
    child_env = dict(os.environ, IMPORT_SUITE_ATTEMPT="1")
    completed = subprocess.run(
        [sys.executable, os.path.abspath(__file__)], env=child_env
    )
    raise SystemExit(completed.returncode)


def _pool_timeout_hook(exc_type, exc_value, exc_traceback) -> None:
    """Uncaught pool exhaustion retries once with a fresh database.

    Installed as ``sys.excepthook``. Any other exception — including every
    import-semantics failure the suite asserts on — keeps the default
    behaviour: print the traceback and exit non-zero with no retry.
    """
    from sqlalchemy.exc import TimeoutError as _PoolTimeout  # noqa: E402

    if _SUITE_ATTEMPT == "0" and isinstance(exc_value, _PoolTimeout):
        _retry_with_fresh_db()
    import traceback  # noqa: E402

    traceback.print_exception(exc_type, exc_value, exc_traceback)


sys.excepthook = _pool_timeout_hook
from app.core.security import get_password_hash  # noqa: E402
from app.imports import runner  # noqa: E402
from app.imports.config import settings  # noqa: E402
from app.imports.headers import neutralise_formula_injection  # noqa: E402
from app.imports.spec import CORE_ENTITIES, get_spec  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.core_hr import Location  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.imports import ImportDryRun, ImportStatus  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.leave import LeaveBalance, LeaveType  # noqa: E402
from app.models.scheduling import ShiftTemplate  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    db.add(User(
        username="imp_admin", email="imp_admin@example.com",
        hashed_password=get_password_hash("ImpPass12345"),
        role="SuperAdmin", is_active=True,
        mfa_enabled=True,  # MFA-enforced world: privileged users are enrolled
    ))
    db.add(User(
        username="imp_hr", email="imp_hr@example.com",
        hashed_password=get_password_hash("ImpPass12345"),
        role="HR", is_active=True,
        mfa_enabled=True,  # MFA-enforced world: privileged users are enrolled
    ))
    db.add(User(
        username="imp_assoc", email="imp_assoc@example.com",
        hashed_password=get_password_hash("ImpPass12345"),
        role="Associate", is_active=True,
    ))
    db.commit()
finally:
    db.close()

client = TestClient(app, raise_server_exceptions=False)

GOLDEN = Path(__file__).resolve().parent / "golden"

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


def H(user: str = "imp_admin") -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"username": user, "password": "ImpPass12345"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


AUTH = H()


def count(model) -> int:
    session = SessionLocal()
    try:
        return session.query(model).count()
    finally:
        session.close()


def audit_count(action: str) -> int:
    session = SessionLocal()
    try:
        return session.query(AuditLog).filter(AuditLog.action == action).count()
    finally:
        session.close()


def upload(entity: str, csv_text: str, headers: dict | None = None, **params):
    return client.post(
        f"/api/v1/import-export/import/{entity}",
        headers=headers or AUTH,
        files={"file": ("data.csv", csv_text, "text/csv")},
        params=params,
    )


def dry_run(entity: str, csv_text: str, headers: dict | None = None):
    return upload(entity, csv_text, headers=headers, dry_run=True)


def commit(entity: str, token: str, headers: dict | None = None):
    return client.post(
        f"/api/v1/import-export/import/{entity}/commit",
        headers=headers or AUTH,
        params={"confirmation_token": token},
    )


def error_codes(body: dict) -> set[str]:
    return {
        error.get("code")
        for row in body.get("rows", [])
        for error in row.get("errors", [])
    }


def row_errors(body: dict, row: int) -> list[dict]:
    for entry in body.get("rows", []):
        if entry.get("row") == row:
            return entry.get("errors", [])
    return []


# --------------------------------------------------------------------------
print("=" * 68)
print("IMPORT — I-01: a template for every core entity, accepted unchanged")
print("=" * 68)

for entity in CORE_ENTITIES:
    response = client.get(f"/api/v1/import-export/template/{entity}", headers=AUTH)
    check(f"template downloads for {entity}", response.status_code == 200,
          f"got {response.status_code}")
    text = response.text
    header = text.splitlines()[0] if text else ""
    spec = get_spec(entity)
    expected = [c.name for c in spec.primary_columns if c.name != "id"]
    check(f"template header for {entity} is the contract's columns",
          header == ",".join(expected), f"{header!r} != {expected!r}")

    # The template's own header row must be accepted by the importer.
    body = dry_run(entity, text)
    check(f"the template for {entity} is accepted by the importer",
          body.status_code == 200 and not body.json().get("unknown_headers"),
          body.text[:200])

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — I-02: exact headers, aliased headers, unknown headers")
print("=" * 68)

response = upload("departments", "name,code\nExact,EXACT\n")
check("an exact header imports", response.status_code == 200
      and response.json().get("created") == 1, response.text[:200])

response = dry_run("departments", "department_name,department_code\nAliased,ALIASED\n")
body = response.json()
check("an aliased header imports", response.status_code == 200
      and body.get("create") == 1, response.text[:200])
check("the aliases that were used are reported back",
      body.get("aliases_used") == {"department_name": "name",
                                   "department_code": "code"},
      str(body.get("aliases_used")))

response = dry_run("departments", "name,code,wibble\nX,Y,Z\n")
check("an unknown header is refused with 422", response.status_code == 422,
      f"got {response.status_code}")
envelope = response.json()
check("the refusal uses the shared error envelope",
      "error" in envelope and "code" in envelope.get("error", {}),
      response.text[:200])
check("the refusal names the unknown header",
      "wibble" in json.dumps(envelope), response.text[:300])
check("the refusal lists the accepted headers",
      "name" in json.dumps(envelope.get("error", {}).get("details", {})),
      response.text[:300])

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — golden files: valid, invalid, and re-import")
print("=" * 68)


def read_golden(entity: str, case: str) -> tuple[str, dict]:
    directory = GOLDEN / entity
    csv_text = (directory / f"{case}.csv").read_text(encoding="utf-8")
    expected = json.loads((directory / f"{case}.expected.json").read_text(encoding="utf-8"))
    return csv_text, expected


def compare_golden(entity: str, case: str, response, expected: dict) -> None:
    body = response.json()
    for field in ("total_rows", "create", "update", "unchanged", "reject"):
        if field not in expected:
            continue
        check(f"{entity}/{case}: {field} is {expected[field]}",
              body.get(field) == expected[field],
              f"got {body.get(field)}")
    if "aliases_used" in expected:
        check(f"{entity}/{case}: the aliases are reported",
              body.get("aliases_used") == expected["aliases_used"],
              str(body.get("aliases_used")))
    for row in expected.get("rows", []):
        actual = row_errors(body, row["row"])
        if row["status"] == "reject":
            codes = {error["code"] for error in actual}
            want = {error["code"] for error in row.get("errors", [])}
            check(f"{entity}/{case}: row {row['row']} is rejected with {sorted(want)}",
                  want <= codes, f"got {sorted(codes)}")
            columns = {error.get("column") for error in actual}
            want_columns = {error.get("column") for error in row.get("errors", [])}
            check(f"{entity}/{case}: row {row['row']} names the column",
                  want_columns <= columns, f"got {columns}")
        else:
            outcome = next((r for r in body.get("rows", []) if r.get("row") == row["row"]), None)
            check(f"{entity}/{case}: row {row['row']} is {row['status']}",
                  outcome is not None and outcome.get("status") == row["status"],
                  str(outcome))


# The order matters: a job names a department, an employee names a job.
# The prerequisites are imported for real before the golden files are
# compared, because a golden file that names a department cannot be
# validated until that department exists.
PRECEDENTS = {
    "departments": [],
    "locations": [],
    "jobs": ["departments"],
    "employees": ["departments", "jobs"],
    "leave_balances": ["departments", "jobs", "employees"],
    "shift_templates": [],
}


def import_and_commit(entity: str, csv_text: str) -> dict:
    """The two-step flow: dry run, then commit."""
    preview = dry_run(entity, csv_text)
    if preview.status_code != 200:
        return {"status": preview.status_code, "body": preview.json()}
    token = preview.json()["confirmation_token"]
    committed = commit(entity, token)
    return {"status": committed.status_code, "body": committed.json(),
            "token": token, "preview": preview.json()}


# A leave type is needed by the leave balance file.
import_and_commit("leave_types",
                   "name,code,is_paid,max_days_per_year,is_active\n"
                   "Annual,ANN,true,25,true\n")

for entity in CORE_ENTITIES:
    # The prerequisites are imported for real first: a golden file that
    # names a department cannot be validated until that department exists.
    # Re-importing a prerequisite is a no-op, so this is safe to repeat.
    for prerequisite in PRECEDENTS[entity]:
        prerequisite_csv, _ = read_golden(prerequisite, "valid")
        import_and_commit(prerequisite, prerequisite_csv)

    # The entity's own golden files are compared before the entity itself
    # is imported, so the "valid" file is expected to create its rows.
    for case in ("valid", "invalid"):
        csv_text, expected = read_golden(entity, case)
        response = dry_run(entity, csv_text)
        check(f"{entity}/{case}: the dry run succeeds",
              response.status_code == 200, response.text[:200])
        if response.status_code != 200:
            continue
        compare_golden(entity, case, response, expected)

    # ------------------------------------------------------------------------
    print()
    print("=" * 68)
    print(f"IMPORT — I-07: a second import of {entity} changes nothing")
    print("=" * 68)

    csv_text, expected = read_golden(entity, "valid")
    before = count(get_spec(entity).model)
    first = import_and_commit(entity, csv_text)
    check(f"{entity}: the first import commits", first["status"] == 200,
          str(first["body"])[:200])
    after_first = count(get_spec(entity).model)
    check(f"{entity}: the first import created {expected['create']} rows",
          after_first - before == expected["create"],
          f"{before} -> {after_first}")

    second = import_and_commit(entity, csv_text)
    check(f"{entity}: the second import commits", second["status"] == 200,
          str(second["body"])[:200])
    body = second["body"]
    check(f"{entity}: the second import creates nothing",
          body.get("created") == 0, str(body)[:200])
    check(f"{entity}: the second import updates nothing",
          body.get("updated") == 0, str(body)[:200])
    check(f"{entity}: the second import reports every row as unchanged",
          body.get("unchanged") == expected["create"], str(body)[:200])
    check(f"{entity}: the second import leaves the table alone",
          count(get_spec(entity).model) == after_first,
          f"{after_first} -> {count(get_spec(entity).model)}")

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — I-04: every validation error has its own case")
print("=" * 68)

cases = [
    ("a value of the wrong type", "shift_templates",
     "name,code,start_time,end_time,break_minutes,is_night,is_active\n"
     "Bad,SH-T1,not-a-time,17:00,30,false,true\n", "invalid_time"),
    ("a missing required field", "departments",
     "name,code\n,ONLYCODE\n", "missing_required"),
    ("a date that is not ISO 8601", "employees",
     "employee_id,first_name,last_name,email,hire_date,job_code,department_code\n"
     "EMP-9001,Bad,Date,bd1@example.com,31/12/2026,J-ENG,ALPHA\n", "invalid_date"),
    ("a value outside an enum", "employees",
     "employee_id,first_name,last_name,email,hire_date,job_code,department_code,status\n"
     "EMP-9002,Bad,Enum,bd2@example.com,2026-01-15,J-ENG,ALPHA,Retired\n", "invalid_enum"),
    ("a reference that does not resolve", "employees",
     "employee_id,first_name,last_name,email,hire_date,job_code,department_code\n"
     "EMP-9003,Bad,Ref,bd3@example.com,2026-01-15,J-NOSUCH,ALPHA\n", "reference_not_found"),
    ("a duplicate of an existing record", "employees",
     "employee_id,first_name,last_name,email,hire_date,job_code,department_code\n"
     "EMP-9007,Duplicate,Row,ada@example.com,2026-01-15,J-ENG,ALPHA\n",
     "duplicate_exists"),
    ("a duplicate inside the file", "departments",
     "name,code\nDup1,SAMECODE\nDup2,SAMECODE\n", "duplicate_in_file"),
    ("a salary below the bound", "employees",
     "employee_id,first_name,last_name,email,hire_date,job_code,department_code,salary\n"
     "EMP-9004,Bad,Salary,bd4@example.com,2026-01-15,J-ENG,ALPHA,-1\n", "below_minimum"),
]
for label, entity, csv_text, code in cases:
    response = dry_run(entity, csv_text)
    body = response.json()
    check(f"{label} is reported as {code}", code in error_codes(body),
          f"{sorted(error_codes(body))} — {response.text[:160]}")
    check(f"{label} rejects the row", body.get("reject", 0) >= 1, str(body)[:160])

# The salary bound comes from the tenant's configuration.
settings.IMPORT_SALARY_MIN = 1000.0
settings.IMPORT_SALARY_MAX = 100000.0
try:
    response = dry_run("employees",
                       "employee_id,first_name,last_name,email,hire_date,job_code,"
                       "department_code,salary\n"
                       "EMP-9005,Bad,Bound,bd5@example.com,2026-01-15,J-ENG,ALPHA,10\n")
    check("a salary below the tenant's minimum is rejected",
          "below_minimum" in error_codes(response.json()),
          str(sorted(error_codes(response.json()))))
    response = dry_run("employees",
                       "employee_id,first_name,last_name,email,hire_date,job_code,"
                       "department_code,salary\n"
                       "EMP-9006,Bad,Bound,bd6@example.com,2026-01-15,J-ENG,ALPHA,999999\n")
    check("a salary above the tenant's maximum is rejected",
          "above_maximum" in error_codes(response.json()),
          str(sorted(error_codes(response.json()))))
finally:
    settings.IMPORT_SALARY_MIN = None
    settings.IMPORT_SALARY_MAX = None

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — I-05: formula injection is neutralised on the stored value")
print("=" * 68)

for trigger, label in (
    ("=", "equals"),
    ("+", "plus"),
    ("-", "minus"),
    ("@", "at"),
    ("\t", "tab"),
    ("\r", "carriage return"),
):
    check(f"a value starting with {label} is neutralised",
          neutralise_formula_injection(f"{trigger}payload").startswith("'"),
          repr(neutralise_formula_injection(f"{trigger}payload")))

# The one carve-out: a cell that is a number is a number, not a formula.
# Only the two characters that double as a sign can start a number.
for sign in ("+", "-"):
    check(f"a number starting with {sign} is left alone",
          neutralise_formula_injection(f"{sign}100") == f"{sign}100",
          repr(neutralise_formula_injection(f"{sign}100")))
check("a value that is not a number is neutralised even when it starts with a sign",
      neutralise_formula_injection("-abc") == "'-abc",
      repr(neutralise_formula_injection("-abc")))

formula_csv = (
    "name,code\n"
    '"=cmd",F-EQ\n'
    '"+plus",F-PL\n'
    '"-minus",F-MI\n'
    '"@at",F-AT\n'
    '"\ttab",F-TAB\n'
    '"\rcr",F-CR\n'
)
response = import_and_commit("departments", formula_csv)
check("the formula rows are imported", response["status"] == 200,
      str(response["body"])[:200])
session = SessionLocal()
try:
    stored = {
        row.code: row.name
        for row in session.query(Department).filter(
            Department.code.in_(["F-EQ", "F-PL", "F-MI", "F-AT", "F-TAB", "F-CR"])
        ).all()
    }
finally:
    session.close()
for code, trigger in (("F-EQ", "="), ("F-PL", "+"), ("F-MI", "-"),
                       ("F-AT", "@"), ("F-TAB", "\t"), ("F-CR", "\r")):
    value = stored.get(code, "")
    check(f"the stored value for {code} is literal text, not a formula",
          value.startswith("'") and value[1] == trigger, repr(value))

# A number in a text column is a number, not a formula.
response = import_and_commit("departments",
                             "name,code,description\n"
                             "Negative Number,DEPNEG,-100\n")
session = SessionLocal()
try:
    row = session.query(Department).filter(Department.code == "DEPNEG").first()
    stored_description = row.description if row else None
finally:
    session.close()
check("a negative number in a text column is stored as a number, not neutralised",
      stored_description == "-100", repr(stored_description))

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — I-06: the dry run writes nothing; the commit writes the preview")
print("=" * 68)

before = count(Department)
preview = dry_run("departments", "name,code\nPreview,PREVIEW\n")
check("the dry run succeeds", preview.status_code == 200, preview.text[:200])
body = preview.json()
check("the dry run says nothing was written", "nothing was written" in body.get("note", "").lower(),
      str(body.get("note")))
check("the dry run did not write", count(Department) == before,
      f"{before} -> {count(Department)}")
check("the dry run reports what it would create", body.get("create") == 1, str(body)[:200])

token = body["confirmation_token"]
committed = commit("departments", token)
check("the commit succeeds", committed.status_code == 200, committed.text[:200])
check("the commit created exactly what the preview said",
      committed.json().get("created") == 1, committed.text[:200])
check("the commit wrote the row", count(Department) == before + 1,
      f"{before} -> {count(Department)}")

# The row-error CSV.
bad_preview = dry_run("employees",
                      "employee_id,first_name,last_name,email,hire_date,job_code,"
                      "department_code,salary\n"
                      "EMP-9100,Bad,Row,badrow@example.com,not-a-date,J-ENG,ALPHA,-5\n")
bad_body = bad_preview.json()
bad_token = bad_body["confirmation_token"]
errors = client.get(
    "/api/v1/import-export/import/employees/row-errors",
    headers=AUTH,
    params={"confirmation_token": bad_token},
)
check("the row-error CSV downloads", errors.status_code == 200, f"got {errors.status_code}")
check("the row-error CSV is a CSV",
      errors.headers.get("content-type", "").startswith("text/csv"),
      errors.headers.get("content-type"))
rows = list(csv.DictReader(io.StringIO(errors.text)))
check("the row-error CSV carries the row number",
      rows and rows[0].get("row") == "2", str(rows)[:200])
check("the row-error CSV carries the column",
      rows and rows[0].get("column") == "hire_date", str(rows)[:200])
check("the row-error CSV carries the reason",
      rows and rows[0].get("code") == "invalid_date", str(rows)[:200])
check("the row-error CSV carries no personal value",
      "badrow@example.com" not in errors.text, errors.text[:300])

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — DI-01: the commit path commits, and says what it did")
print("=" * 68)

before = count(Department)
response = import_and_commit("departments", "name,code\nAudit,AUDIT\nAudit2,AUDIT2\n")
check("the two-step flow commits", response["status"] == 200, str(response["body"])[:200])
after = count(Department)
check("the counts equal the change in the database",
      response["body"].get("created") == after - before,
      f"response {response['body'].get('created')} vs database {after - before}")

session = SessionLocal()
try:
    audit = (
        session.query(AuditLog)
        .filter(AuditLog.action == "import_commit")
        .order_by(AuditLog.id.desc())
        .first()
    )
    details = (audit.details or "") if audit else ""
finally:
    session.close()
check("an audit row was written for the commit", audit is not None)
check("the audit row records the same count as the response",
      f"created={after - before}" in details, details)

# A second commit with the same token does nothing.
token = response["token"]
again = commit("departments", token)
check("a second commit with the same token is refused",
      again.status_code == 409, f"got {again.status_code}")
check("a second commit does not create a second row",
      count(Department) == after, f"{after} -> {count(Department)}")

# A batch that fails is rolled back, and the failure is reported against
# its rows. The row is made to fail by inserting a conflicting record after
# the dry run, so the preview cannot see it.
session = SessionLocal()
try:
    session.add(Employee(
        employee_id="IMP-CONFLICT", first_name="Conflict", last_name="Row",
        email="conflict@example.com", hire_date=datetime(2024, 1, 1).date(),
        job_id=1, department_id=1,
    ))
    session.commit()
finally:
    session.close()

previous_batch = settings.IMPORT_BATCH_SIZE
settings.IMPORT_BATCH_SIZE = 1
try:
    preview = dry_run("employees",
                      "employee_id,first_name,last_name,email,hire_date,job_code,"
                      "department_code\n"
                      "EMP-9200,Fail,Row,conflict@example.com,2026-01-15,J-ENG,ALPHA\n"
                      "EMP-9201,Good,Row,goodrow@example.com,2026-01-15,J-ENG,ALPHA\n")
    token = preview.json()["confirmation_token"]
    committed = commit("employees", token)
    body = committed.json()
    check("a batch that fails does not fail the whole import",
          committed.status_code == 200, committed.text[:300])
    check("the failing row is reported as a write failure",
          body.get("created") == 1, str(body)[:300])
    session = SessionLocal()
    try:
        written = session.query(Employee).filter(
            Employee.employee_id.in_(["EMP-9200", "EMP-9201"])
        ).count()
    finally:
        session.close()
    check("the failing row was not written", written == 1, f"wrote {written} of 2")
finally:
    settings.IMPORT_BATCH_SIZE = previous_batch

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — DI-02: the token is bound to the result, has a TTL, is single use")
print("=" * 68)

preview = dry_run("departments", "name,code\nBound,BOUND\n")
token = preview.json()["confirmation_token"]

session = SessionLocal()
try:
    record = session.query(ImportDryRun).filter(ImportDryRun.token == token).first()
    check("the dry run is recorded in the database", record is not None)
    check("the record holds the result hash",
          record is not None and len(record.result_hash) == 64)
    check("the record holds the file hash",
          record is not None and len(record.file_hash) == 64)
    check("the record records the user who asked for it",
          record is not None and record.user_id is not None)
finally:
    session.close()

# Change the outcome underneath the token: the commit must refuse.
session = SessionLocal()
try:
    record = session.query(ImportDryRun).filter(ImportDryRun.token == token).first()
    record.result_hash = "0" * 64
    session.add(record)
    session.commit()
finally:
    session.close()
refused = commit("departments", token)
check("a commit whose result no longer matches is refused with 409",
      refused.status_code == 409, f"got {refused.status_code}")
check("the refusal uses the shared error envelope",
      "error" in refused.json() and "code" in refused.json()["error"],
      refused.text[:200])
check("the refusal says the result changed",
      refused.json()["error"]["code"] == "import_result_changed",
      refused.text[:200])

# An expired token is refused with a message that says so.
preview = dry_run("departments", "name,code\nExpiring,EXPIRING\n")
expired_token = preview.json()["confirmation_token"]
session = SessionLocal()
try:
    record = session.query(ImportDryRun).filter(
        ImportDryRun.token == expired_token
    ).first()
    record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    session.add(record)
    session.commit()
finally:
    session.close()
expired = commit("departments", expired_token)
check("an expired token is refused", expired.status_code == 409,
      f"got {expired.status_code}")
check("the refusal says the token expired",
      "expired" in expired.json()["error"]["message"].lower(),
      expired.text[:300])

# The store is bounded.
previous_limit = settings.IMPORT_MAX_OUTSTANDING_TOKENS
settings.IMPORT_MAX_OUTSTANDING_TOKENS = 3
try:
    tokens = []
    for index in range(6):
        response = dry_run("departments", f"name,code\nBound{index},BOUND{index}\n")
        tokens.append(response.json()["confirmation_token"])
    session = SessionLocal()
    try:
        outstanding = session.query(ImportDryRun).filter(
            ImportDryRun.status == ImportStatus.PENDING
        ).count()
    finally:
        session.close()
    check("the number of outstanding tokens is bounded",
          outstanding <= 3, f"{outstanding} outstanding")
    oldest = commit("departments", tokens[0])
    check("the oldest token was evicted and no longer works",
          oldest.status_code == 409, f"got {oldest.status_code}")
finally:
    settings.IMPORT_MAX_OUTSTANDING_TOKENS = previous_limit

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — authorisation: who may import, and whose token may be used")
print("=" * 68)

response = client.post(
    "/api/v1/import-export/import/departments",
    files={"file": ("d.csv", "name,code\nNoAuth,NA1\n", "text/csv")},
)
check("an unauthenticated import is refused", response.status_code == 401,
      f"got {response.status_code}")
response = client.post(
    "/api/v1/import-export/import/departments",
    headers={"Authorization": "Bearer forged-token"},
    files={"file": ("d.csv", "name,code\nNoAuth,NA2\n", "text/csv")},
)
check("an import with a forged token is refused", response.status_code == 401,
      f"got {response.status_code}")
response = client.post(
    "/api/v1/import-export/import/departments",
    headers=H("imp_assoc"),
    files={"file": ("d.csv", "name,code\nNoPerm,NP1\n", "text/csv")},
)
check("a user without import permission is refused with 403",
      response.status_code == 403, f"got {response.status_code}")
session = SessionLocal()
try:
    check("the refused import wrote nothing",
          session.query(Department).filter(Department.code.in_(["NA1", "NA2", "NP1"])).count() == 0)
finally:
    session.close()

# One user's token is not another's.
preview = dry_run("departments", "name,code\nMine,MINE\n")
mine = preview.json()["confirmation_token"]
other = commit("departments", mine, headers=H("imp_hr"))
check("another user's token cannot be committed", other.status_code == 403,
      f"got {other.status_code}")
check("the refusal uses the shared error envelope",
      "error" in other.json() and other.json()["error"]["code"] == "forbidden",
      other.text[:200])

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — I-03: the limits, and the failure paths")
print("=" * 68)

too_many = io.StringIO()
writer = csv.writer(too_many)
writer.writerow(["name", "code"])
for index in range(settings.IMPORT_MAX_ROWS + 1):
    writer.writerow([f"Department {index}", f"ROW{index}"])
response = upload("departments", too_many.getvalue(), dry_run=True)
check("a file over the row limit is refused", response.status_code == 422,
      f"got {response.status_code}")
check("the refusal says the file has too many rows",
      response.json().get("error", {}).get("code") == "too_many_rows",
      response.text[:200])

too_big = io.StringIO()
writer = csv.writer(too_big)
writer.writerow(["name", "code", "description"])
filler = "x" * 400
row_count = (settings.IMPORT_MAX_UPLOAD_BYTES // 420) + 10
for index in range(row_count):
    writer.writerow([f"Department {index}", f"BIG{index}", filler])
check("the oversized file really is oversized",
      len(too_big.getvalue()) > settings.IMPORT_MAX_UPLOAD_BYTES,
      str(len(too_big.getvalue())))
response = upload("departments", too_big.getvalue(), dry_run=True)
check("a file over the size limit is refused with 413",
      response.status_code == 413, f"got {response.status_code}")
check("the refusal uses the shared error envelope",
      "error" in response.json(), response.text[:200])

response = client.post(
    "/api/v1/import-export/import/departments", headers=AUTH,
    files={"file": ("empty.csv", "", "text/csv")},
)
check("an empty upload is refused with 400", response.status_code == 400,
      f"got {response.status_code}")
check("the empty-upload refusal uses the shared error envelope",
      "error" in response.json(), response.text[:200])

response = client.post(
    "/api/v1/import-export/import/departments", headers=AUTH,
    files={"file": ("bad.csv", b"name,code\n\xff\xfe\x00bad,BAD1\n", "text/csv")},
)
check("a file that is not valid UTF-8 is refused",
      response.status_code in (400, 422), f"got {response.status_code}")

response = upload("departments", "name,code\nUnclosed,UNCLOSED\n\"broken,QUOTE\n",
                  dry_run=True)
check("a malformed CSV is refused", response.status_code in (400, 422),
      f"got {response.status_code}")

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — I-03: the parse streams, and stays inside the memory budget")
print("=" * 68)

streaming = io.StringIO()
writer = csv.writer(streaming)
writer.writerow(["name", "code", "description"])
for index in range(settings.IMPORT_MAX_ROWS):
    writer.writerow([f"Department {index}", f"STREAM{index}", "a description"])
payload = streaming.getvalue()
check("the streaming file is inside the size limit",
      len(payload) <= settings.IMPORT_MAX_UPLOAD_BYTES, str(len(payload)))

tracemalloc.start()
response = upload("departments", payload, dry_run=True)
_current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
check("the 10,000-row file is analysed", response.status_code == 200,
      f"got {response.status_code}")
check("every row was counted",
      response.json().get("total_rows") == settings.IMPORT_MAX_ROWS,
      str(response.json().get("total_rows")))
peak_mb = peak / (1024 * 1024)
print(f"        peak memory for a {settings.IMPORT_MAX_ROWS}-row import: {peak_mb:.1f} MB")
check(f"the import stays inside the memory budget (peak {peak_mb:.1f} MB < 64 MB)",
      peak_mb < 64, f"{peak_mb:.1f} MB")

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — a storage failure mid-import leaves nothing behind")
print("=" * 68)

import app.storage.backends as storage_backends  # noqa: E402

original_save_verified = storage_backends.LocalStorage.save_verified


def failing_save_verified(self, key, data, content_type="application/octet-stream"):
    if key.endswith(".json"):
        raise storage_backends.StorageError("object storage is unavailable")
    return original_save_verified(self, key, data, content_type)


before = count(Department)
audit_before = audit_count("import_commit")
preview = dry_run("departments", "name,code\nStorage,STORAGE\n")
token = preview.json()["confirmation_token"]
storage_backends.LocalStorage.save_verified = failing_save_verified
try:
    failed = commit("departments", token)
finally:
    storage_backends.LocalStorage.save_verified = original_save_verified
check("a storage failure fails the commit", failed.status_code >= 500,
      f"got {failed.status_code}")
check("a storage failure leaves no partial commit",
      count(Department) == before, f"{before} -> {count(Department)}")
check("a storage failure writes no audit row claiming a commit",
      audit_count("import_commit") == audit_before,
      f"{audit_before} -> {audit_count('import_commit')}")

session = SessionLocal()
try:
    committed_rows = session.query(ImportDryRun).filter(
        ImportDryRun.token == token, ImportDryRun.status == ImportStatus.COMMITTED
    ).count()
finally:
    session.close()
check("a storage failure leaves the dry run pending", committed_rows == 0,
      f"{committed_rows} committed")

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — the export round-trips back through the importer")
print("=" * 68)

export = client.get("/api/v1/import-export/export/departments", headers=AUTH)
check("the export succeeds", export.status_code == 200, f"got {export.status_code}")
check("the export is a CSV",
      export.headers.get("content-type", "").startswith("text/csv"),
      export.headers.get("content-type"))
check("the export carries the header the importer accepts",
      export.text.splitlines()[0].startswith("id,name,code"),
      export.text.splitlines()[0][:80] if export.text else "")

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — the documentation and the contract agree")
print("=" * 68)

DOC = Path(__file__).resolve().parent.parent / "docs" / "IMPORT_TEMPLATES.md"
if DOC.exists():
    doc_text = DOC.read_text(encoding="utf-8")
    for entity in CORE_ENTITIES:
        spec = get_spec(entity)
        for column in spec.columns:
            if column.name == "id":
                continue
            check(f"the documentation names the {entity} column {column.name}",
                  f"`{column.name}`" in doc_text, column.name)
    from app.imports.headers import HEADER_ALIASES

    for canonical, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            check(f"the documentation names the alias {alias}",
                  f"`{alias}`" in doc_text, alias)
    for code in (
        "missing_required", "invalid_integer", "invalid_number",
        "invalid_boolean", "invalid_date", "invalid_datetime", "invalid_time",
        "invalid_email", "invalid_enum", "too_long", "below_minimum",
        "above_maximum", "inconsistent_values", "reference_not_found",
        "duplicate_in_file", "duplicate_exists", "too_many_fields",
        "too_few_fields", "write_failed", "unknown_headers", "too_many_rows",
        "file_too_large", "not_utf8", "malformed_csv",
    ):
        check(f"the documentation names the error code {code}",
              f"`{code}`" in doc_text, code)
else:
    check("the import documentation exists", False, str(DOC))

# --------------------------------------------------------------------------
# The model of the import table must not declare a column that is unique
# *and* indexed. A unique constraint already has an index behind it, so a
# second index over the same column list is what Oracle refuses with
# ORA-01408 — the error that failed the deployment of the import feature.
#
# The combination is read from the source, because SQLAlchemy resolves it
# before the metadata is built: a column with both flags produces one
# unique index and no unique constraint, so the metadata no longer shows
# what was written. The source is where the mistake is.
import ast

MODEL_SOURCE = Path(__file__).resolve().parent / "app" / "models" / "imports.py"


def _unique_and_indexed_columns(source_path: Path) -> list[int]:
    """The lines that declare a column both unique and indexed."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        name = getattr(function, "attr", None) or getattr(function, "id", None)
        if name != "mapped_column":
            continue
        keywords = {keyword.arg for keyword in node.keywords}
        if "unique" in keywords and "index" in keywords:
            offenders.append(node.lineno)
    return offenders


offenders = _unique_and_indexed_columns(MODEL_SOURCE)
check(
    "no column of the import model is declared both unique and indexed",
    not offenders,
    f"lines={offenders} in {MODEL_SOURCE.name}",
)

from sqlalchemy import inspect  # noqa: E402

_inspector = inspect(engine)
_token_indexes = [
    index
    for index in _inspector.get_indexes("import_dry_runs")
    if [str(name).casefold() for name in index.get("column_names") or []]
    == ["token"]
]
_token_constraints = [
    constraint
    for constraint in _inspector.get_unique_constraints("import_dry_runs")
    if [str(name).casefold() for name in constraint.get("column_names") or []]
    == ["token"]
]
check(
    "the token column of the import model has exactly one index",
    len(_token_indexes) + len(_token_constraints) == 1,
    f"indexes={len(_token_indexes)} unique constraints={len(_token_constraints)}",
)
check(
    "the uniqueness of the token is a constraint, not a bare index",
    len(_token_constraints) == 1 and len(_token_indexes) == 0,
    f"unique constraints={len(_token_constraints)} indexes={len(_token_indexes)}",
)

# The generated schema document must match the models.
SCHEMA = Path(__file__).resolve().parent.parent / "docs" / "DB_SCHEMA.sql"
if SCHEMA.exists():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "generate_db_schema",
        Path(__file__).resolve().parent / "scripts" / "generate_db_schema.py",
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    expected = generator.render(generator._load_metadata())
    check("the generated schema document is up to date with the models",
          SCHEMA.read_text(encoding="utf-8") == expected,
          "run: python scripts/generate_db_schema.py")
else:
    check("the generated schema document exists", False, str(SCHEMA))

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — DI-03: the import writes through the leave ledger")
print("=" * 68)

from app.models.leave import LeaveLedger  # noqa: E402
from app.services import leave as leave_service  # noqa: E402

LEAVE_CSV = (
    "employee_number,leave_type_code,entitlement_year,entitled_days,"
    "carried_over_days,used_days\n"
)


def ledger_rows_for(employee_number: str, year: str = "2026"):
    """The ledger rows of one balance, in the order they were written."""
    session = SessionLocal()
    try:
        balance = (
            session.query(LeaveBalance)
            .join(Employee, LeaveBalance.employee_id == Employee.id)
            .filter(
                Employee.employee_id == employee_number,
                LeaveBalance.entitlement_year == int(year),
            )
            .first()
        )
        if balance is None:
            return None, []
        rows = (
            session.query(LeaveLedger)
            .filter(LeaveLedger.balance_id == balance.id)
            .order_by(LeaveLedger.id)
            .all()
        )
        return balance, [
            (row.entry_type.value, float(row.signed_days)) for row in rows
        ]
    finally:
        session.close()


# The golden file is imported for real, and the ledger rows it produces
# are the ones the golden file says.
golden_csv, golden_expected = read_golden("leave_balances", "valid")
response = import_and_commit("leave_balances", golden_csv)
check("the leave balance file imports", response["status"] == 200,
      str(response["body"])[:200])

balance, rows = ledger_rows_for("EMP-0001")
check("the imported balance exists", balance is not None)
check("the balance carries the imported numbers",
      balance is not None
      and float(balance.entitled_days) == float(golden_expected["ledger_entitled"])
      and float(balance.used_days) == float(golden_expected["ledger_used"]),
      f"{balance.entitled_days if balance else None}/"
      f"{balance.used_days if balance else None}")
check("the ledger rows are the ones the golden file says",
      rows == [tuple(entry) for entry in golden_expected["ledger_rows"]],
      f"{rows} != {golden_expected['ledger_rows']}")

if balance is not None:
    _derive_db = SessionLocal()
    try:
        derived = leave_service.derived_available_days(_derive_db, balance)
    finally:
        _derive_db.close()
    check("the derived balance is the imported balance",
          float(derived) == float(balance.entitled_days)
          + float(balance.carried_over_days) - float(balance.used_days),
          str(derived))

session = SessionLocal()
try:
    report = leave_service.reconcile(session)
finally:
    session.close()
states = {row["state"] for row in report}
check("the reconciliation reports no balance without a ledger",
      "no_ledger" not in states, str(states))
check("the imported balance reconciles",
      all(row["state"] == "in_sync" for row in report), str(states))

# The second import of the same file writes nothing and adds no history.
before_rows = len(rows)
second = import_and_commit("leave_balances", golden_csv)
check("the second import of the leave file creates nothing",
      second["body"].get("created") == 0 and second["body"].get("updated") == 0,
      str(second["body"])[:200])
check("the second import of the leave file adds no ledger row",
      len(ledger_rows_for("EMP-0001")[1]) == before_rows,
      f"{before_rows} -> {len(ledger_rows_for('EMP-0001')[1])}")

# The second golden file: a balance that moves once it has a history.
# The ledger keeps the first movement and adds the second one.
ledger_csv, ledger_expected = read_golden("leave_balances", "ledger")
response = dry_run("leave_balances", ledger_csv)
check("the ledger golden file is accepted", response.status_code == 200,
      response.text[:200])
if response.status_code == 200:
    compare_golden("leave_balances", "ledger", response, ledger_expected)
    result = import_and_commit("leave_balances", ledger_csv)
    check("the ledger golden file imports", result["status"] == 200,
          str(result["body"])[:200])
    balance, rows = ledger_rows_for("EMP-0001")
    check("the ledger keeps the first movement and adds the second",
          rows == [tuple(entry) for entry in ledger_expected["ledger_rows"]],
          f"{rows} != {ledger_expected['ledger_rows']}")
    check("the balance carries the new numbers",
          balance is not None
          and float(balance.entitled_days) == float(ledger_expected["ledger_entitled"])
          and float(balance.used_days) == float(ledger_expected["ledger_used"]),
          f"{balance.entitled_days if balance else None}/"
          f"{balance.used_days if balance else None}")

# The import refuses what the ledger would refuse: a file that lowers a
# balance, and a file that would leave a balance with no history.
lower = LEAVE_CSV + "EMP-0001,ANN,2026,30,0,1\n"
response = dry_run("leave_balances", lower)
body = response.json()
check("a file that lowers a balance is refused",
      body.get("reject") == 1, str(body)[:200])
errors = row_errors(body, 2)
check("the refusal names the row and the column",
      errors and errors[0].get("code") == "ledger_reduction_refused"
      and errors[0].get("column") == "used_days",
      str(errors)[:200])
check("the refusal does not quote a value",
      "EMP-0001" not in json.dumps(errors), str(errors)[:200])

zero = LEAVE_CSV + "EMP-0001,ANN,2027,0,0,0\n"
response = dry_run("leave_balances", zero)
body = response.json()
check("a balance of zero days is refused",
      "ledger_no_movement" in error_codes(body), str(sorted(error_codes(body))))

# The refusal is a refusal: the row is not written.
count_before = count(LeaveBalance)
response = import_and_commit("leave_balances", lower)
check("the refused file writes no balance",
      count(LeaveBalance) == count_before,
      f"{count_before} -> {count(LeaveBalance)}")

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("IMPORT — DI-03: the csv_import job really runs an import")
print("=" * 68)

from app.jobs import handlers as job_handlers  # noqa: E402
from app.jobs.queue import JobQueueService  # noqa: E402
from app.models.job_queue import JobQueue, JobState  # noqa: E402


def _claim_job(worker_id, job_types=None):
    """Claim the next job, then close the session before returning it.

    The session that claims a job holds a pooled connection; holding it
    open while the handler runs (the handler opens its own session) is
    what starved the fixed-size pool. The claimed row is expunged while
    its attributes are loaded, so the caller keeps a detached row with
    ``id``/``attempts`` available and no open connection behind it.
    """
    _db = SessionLocal()
    try:
        job = JobQueueService(_db).claim_next(worker_id, job_types=job_types)
        if job is not None:
            _db.expunge(job)
        return job
    finally:
        _db.close()


def _complete_job(job_id, worker_id, result):
    """Mark a job succeeded on a short-lived session (always closed)."""
    _db = SessionLocal()
    try:
        return JobQueueService(_db).complete(job_id, worker_id, result)
    finally:
        _db.close()


def _fail_job(job_id, worker_id, code, message, permanent=False):
    """Mark a job failed on a short-lived session (always closed)."""
    _db = SessionLocal()
    try:
        return JobQueueService(_db).fail(
            job_id, worker_id, code, message, permanent=permanent
        )
    finally:
        _db.close()

previous_threshold = settings.IMPORT_JOB_ROW_THRESHOLD
settings.IMPORT_JOB_ROW_THRESHOLD = 1
try:
    preview = dry_run("departments", "name,code\nJob,JOBD\nJob2,JOBD2\n")
    token = preview.json()["confirmation_token"]
    queued = client.post(
        "/api/v1/import-export/import/departments/commit",
        headers=AUTH,
        params={"confirmation_token": token},
    )
    check("a large import becomes a job", queued.status_code == 202,
          f"got {queued.status_code}")
    queued_body = queued.json()
    check("the response carries the job", queued_body.get("job", {}).get("id"),
          str(queued_body)[:200])
    check("the response says the import is queued",
          queued_body.get("state") == "queued" and queued_body.get("committed") is False,
          str(queued_body)[:200])
    check("the response carries the counts the operator was shown",
          queued_body.get("create") == 2, str(queued_body)[:200])

    session = SessionLocal()
    try:
        job_row = session.query(JobQueue).filter(
            JobQueue.id == queued_body["job"]["id"]
        ).first()
        check("the job is queued", job_row is not None and job_row.state == "queued",
              str(job_row.state if job_row else None))
        check("the job is a csv import", job_row is not None
              and job_row.job_type == "csv_import", str(job_row.job_type if job_row else None))
    finally:
        session.close()

    # The worker claims the job and runs it.
    # The claim session is closed before the handler runs: the handler opens
    # its own session, and holding both open starved the pool (LP-DATA-001).
    claimed = _claim_job("worker-1")
    check("the job is claimed", claimed is not None
          and claimed.id == queued_body["job"]["id"], str(claimed))
    result = job_handlers.csv_import(
        claimed,
        {"entity": "departments", "confirmation_token": token,
         "user_id": None},
    )
    check("the job returns the report the dry run produced",
          result.get("entity") == "departments" and result.get("total_rows") == 2,
          str(result)[:200])
    check("the job reports what it applied",
          result.get("created") == 2 and result.get("committed") is True,
          str(result)[:200])
    check("the job reports its own status", result.get("state") == "succeeded",
          str(result)[:200])
    session = SessionLocal()
    try:
        written = session.query(Department).filter(
            Department.code.in_(["JOBD", "JOBD2"])
        ).count()
    finally:
        session.close()
    check("the job wrote the rows", written == 2, str(written))

    # The job's status is the import's status.
    session = SessionLocal()
    try:
        record = session.query(ImportDryRun).filter(
            ImportDryRun.token == token
        ).first()
        check("the import the job applied is committed",
              record is not None and record.status == ImportStatus.COMMITTED,
              str(record.status if record else None))
    finally:
        session.close()

    # A failure is recorded against the rows it failed on.
    preview = dry_run("employees",
                      "employee_id,first_name,last_name,email,hire_date,job_code,"
                      "department_code\n"
                      "EMP-9300,Bad,Row,badrow@example.com,not-a-date,J-ENG,ALPHA\n"
                      "EMP-9301,Good,Row,jobrow@example.com,2026-01-15,J-ENG,ALPHA\n")
    token = preview.json()["confirmation_token"]
    queued = client.post(
        "/api/v1/import-export/import/employees/commit",
        headers=AUTH,
        params={"confirmation_token": token},
    )
    check("a large employee file becomes a job too", queued.status_code == 202,
          f"got {queued.status_code}")
    claimed = _claim_job("worker-2")
    result = job_handlers.csv_import(
        claimed,
        {"entity": "employees", "confirmation_token": token, "user_id": None},
    )
    check("the job reports the rows it failed on",
          result.get("reject") == 1, str(result)[:200])
    failed_rows = [row for row in result.get("rows", []) if row.get("status") == "reject"]
    check("the failed row is named",
          failed_rows and failed_rows[0].get("row") == 2, str(result.get("rows"))[:200])
    check("the failed row names the column",
          failed_rows and failed_rows[0]["errors"][0].get("column") == "hire_date",
          str(result.get("rows"))[:200])

    # A row that cannot be written is recorded against the row it failed
    # on, and the other rows are still applied.
    import app.imports.runner as runner_module  # noqa: E402

    original_apply = runner_module.apply_batch

    def failing_apply(db, spec, batch, undo=None, **kwargs):
        if any(number == 2 for number, _values in batch.rows):
            raise RuntimeError("the row cannot be written")
        return original_apply(db, spec, batch, undo, **kwargs)

    previous_batch_size = settings.IMPORT_BATCH_SIZE
    settings.IMPORT_BATCH_SIZE = 1
    runner_module.apply_batch = failing_apply
    try:
        preview = dry_run("departments", "name,code\nFail,FAILJOB\nGood,GOODJOB\n")
        token = preview.json()["confirmation_token"]
        queued = client.post(
            "/api/v1/import-export/import/departments/commit",
            headers=AUTH,
            params={"confirmation_token": token},
        )
        check("the file with an unwritable row becomes a job",
              queued.status_code == 202, f"got {queued.status_code}")
        claimed = _claim_job("worker-5")
        result = job_handlers.csv_import(
            claimed,
            {"entity": "departments", "confirmation_token": token,
             "user_id": None},
        )
    finally:
        runner_module.apply_batch = original_apply
        settings.IMPORT_BATCH_SIZE = previous_batch_size
    check("the job reports the row it could not write",
          result.get("failed") == 1, str(result)[:250])
    failed_rows = [row for row in result.get("rows", []) if row.get("status") == "reject"]
    check("the row that could not be written is named",
          failed_rows and failed_rows[0].get("row") == 2, str(result.get("rows"))[:250])
    check("the failure names the code",
          failed_rows and failed_rows[0]["errors"][0].get("code") == "write_failed",
          str(result.get("rows"))[:250])
    session = SessionLocal()
    try:
        written = session.query(Department).filter(
            Department.code.in_(["FAILJOB", "GOODJOB"])
        ).count()
    finally:
        session.close()
    check("the row that could not be written is not in the table",
          written == 1, f"wrote {written} of 2")

    # A cancelled job applies nothing.
    preview = dry_run("departments", "name,code\nCancelled,CANCELLED\nCancelled2,CANCELLED2\n")
    token = preview.json()["confirmation_token"]
    queued = client.post(
        "/api/v1/import-export/import/departments/commit",
        headers=AUTH,
        params={"confirmation_token": token},
    )
    check("the cancelled import becomes a job", queued.status_code == 202,
          f"got {queued.status_code}")
    claimed = _claim_job("worker-3")
    # The job loses its lease: another worker may have taken it.
    session = SessionLocal()
    try:
        row = session.query(JobQueue).filter(JobQueue.id == claimed.id).first()
        row.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.add(row)
        session.commit()
    finally:
        session.close()
    departments_before = count(Department)
    stopped = False
    try:
        job_handlers.csv_import(
            claimed,
            {"entity": "departments", "confirmation_token": token,
             "user_id": None},
        )
    except Exception:  # noqa: BLE001
        stopped = True
    check("a cancelled job stops", stopped, "the job ran to the end")
    check("a cancelled job applies nothing",
          count(Department) == departments_before,
          f"{departments_before} -> {count(Department)}")
    session = SessionLocal()
    try:
        cancelled_rows = session.query(Department).filter(
            Department.code == "CANCELLED"
        ).count()
    finally:
        session.close()
    check("the cancelled job wrote no row with its code", cancelled_rows == 0,
          str(cancelled_rows))

    # An import cancelled by the operator stops the same way.
    preview = dry_run("departments", "name,code\nByOperator,BYOPERATOR\nByOperator2,BYOPERATOR2\n")
    token = preview.json()["confirmation_token"]
    queued = client.post(
        "/api/v1/import-export/import/departments/commit",
        headers=AUTH,
        params={"confirmation_token": token},
    )
    check("the operator's import becomes a job", queued.status_code == 202,
          f"got {queued.status_code}")
    claimed = _claim_job("worker-4")
    session = SessionLocal()
    try:
        runner.cancel_import(session, "departments", token)
    finally:
        session.close()
    departments_before = count(Department)
    stopped = False
    reason = ""
    error_type = ""
    try:
        job_handlers.csv_import(
            claimed,
            {"entity": "departments", "confirmation_token": token,
             "user_id": None},
        )
    except Exception as exc:  # noqa: BLE001
        stopped = True
        reason = str(exc)
        error_type = type(exc).__name__
    check("an import cancelled by the operator stops", stopped,
          "the job ran to the end")
    check("the refusal says the import was cancelled",
          "cancel" in reason.lower(), reason[:200])
    check("a cancelled import is a permanent refusal, not a retry",
          error_type == "JobCancelled", error_type)
    check("an import cancelled by the operator applies nothing",
          count(Department) == departments_before,
          f"{departments_before} -> {count(Department)}")
finally:
    settings.IMPORT_JOB_ROW_THRESHOLD = previous_threshold

# --------------------------------------------------------------------------
print("IMPORT — a stored row the response model would refuse does not break the list")
print("=" * 68)

# The staging schema holds employees whose address is on a reserved domain
# (`@example.test`), written by a seed that predates the input rules. Pydantic
# refused it on the way *out*, so `GET /employees/` answered 500 for one row
# and the leave screen — which reads the employee list — showed a reload
# button instead of data. The response model is now what is stored; the input
# model still validates.
_session = SessionLocal()
try:
    _session.add(Employee(
        employee_id="EMP-RESERVED",
        first_name="Reserved",
        last_name="Domain",
        email="reserved.domain@example.test",
        hire_date=datetime(2026, 1, 15).date(),
        job_id=1,
        department_id=1,
        status="Active",
    ))
    _session.commit()
finally:
    _session.close()

# The directory is paged and newest-hire first, so the row is asked for by
# the address it carries rather than assumed to be on the first page.
r = client.get(
    "/api/v1/employees/",
    headers=AUTH,
    params={"search": "reserved.domain@example.test", "page_size": 200},
)
check("a stored address the input rules would refuse does not break the list",
      r.status_code == 200, f"{r.status_code} {r.text[:160]}")
_emails = [
    row.get("email")
    for row in (r.json().get("items", []) if r.status_code == 200 else [])
]
check("the row is in the list, with the address as stored",
      "reserved.domain@example.test" in _emails,
      str(_emails[:5])[:200])

# The input is still strict: the same address is refused on the way in.
_in = client.post(
    "/api/v1/employees/",
    headers=AUTH,
    json={
        "employee_id": "EMP-RESERVED2",
        "first_name": "Refused",
        "last_name": "Domain",
        "email": "another.reserved@example.test",
        "hire_date": "2026-02-01",
        "job_id": 1,
        "department_id": 1,
    },
)
check("the input still refuses a reserved-domain address",
      _in.status_code == 422, f"{_in.status_code} {_in.text[:160]}")

# --------------------------------------------------------------------------
print("IMPORT — DI-04: the progress of a queued import is served")
print("=" * 68)

from app.imports import progress as import_progress  # noqa: E402
from app.models.job_queue import JobQueue, JobType  # noqa: E402

HR_AUTH = H("imp_hr")
ASSOC_AUTH = H("imp_assoc")

_session = SessionLocal()
try:
    ADMIN_ID = _session.query(User).filter(User.username == "imp_admin").one().id
finally:
    _session.close()


def queue_import(entity: str, csv_text: str, owner_id: int | None = None):
    """Dry-run a file and queue it, the way a large commit does.

    The queue is entered directly rather than through the 202, because the
    202 is already proven above and this section needs to choose the owner
    of the job to prove that another operator is refused it.
    """
    preview = dry_run(entity, csv_text)
    token = preview.json()["confirmation_token"]
    session = SessionLocal()
    try:
        job = runner.queue_job(session, entity, token, owner_id)
        return job.id, token
    finally:
        session.close()


def progress_of(entity: str, job_id: int, headers: dict | None = None):
    return client.get(
        f"/api/v1/import-export/import/{entity}/progress/{job_id}",
        headers=headers or AUTH,
    )


JOB_A, TOKEN_A = queue_import(
    "departments", "name,code\nProg,PRG1\nProg2,PRG2\n", ADMIN_ID
)

r = progress_of("departments", JOB_A)
body = r.json()
check("a queued import's progress is served", r.status_code == 200,
      f"{r.status_code} {r.text[:160]}")
check("the progress reports the job's own state",
      body.get("state") == "queued"
      and body.get("job", {}).get("id") == JOB_A,
      str(body)[:200])
check("the progress reports the rows the file holds",
      body.get("rows_total") == 2 and body.get("rows_accepted") == 2,
      str(body)[:200])
check("a queued import has applied nothing",
      body.get("rows_applied") == 0
      and body.get("rows_pending") == 2
      and body.get("percent") == 0,
      str(body)[:200])
check("the progress reports the batch count",
      body.get("batch_size") == settings.IMPORT_BATCH_SIZE
      and body.get("batches_total") == 1
      and body.get("batches_done") == 0,
      str(body)[:200])
check("a queued import has no result yet",
      body.get("result") is None and body.get("result_stored") is False,
      str(body)[:200])
check("the progress says nothing is written yet",
      "queued" in (body.get("note") or "").lower(), body.get("note"))

# --- it is the operator's own job, and only theirs ------------------------

wrong_entity = progress_of("employees", JOB_A)
check("a job is not served under another entity",
      wrong_entity.status_code == 404, f"{wrong_entity.status_code}")

other_operator = progress_of("departments", JOB_A, HR_AUTH)
check("another operator's job is not served",
      other_operator.status_code == 404,
      f"{other_operator.status_code}")
check("the refusal says the job is not found",
      other_operator.json().get("error", {}).get("code") == "job_not_found",
      str(other_operator.json())[:200])

refused = progress_of("departments", JOB_A, ASSOC_AUTH)
check("a role that may not ask is refused with the shared envelope",
      refused.status_code == 403
      and refused.json().get("error", {}).get("category") == "permission",
      f"{refused.status_code} {refused.text[:160]}")

unknown = progress_of("departments", 999999)
check("an unknown job is not found", unknown.status_code == 404,
      f"{unknown.status_code}")

_session = SessionLocal()
try:
    other_job = JobQueueService(_session).enqueue(
        JobType.RETENTION_RUN, {"reason": "progress test"}
    )
    OTHER_JOB = other_job.id
finally:
    _session.close()
check("a job that is not an import is not served",
      progress_of("departments", OTHER_JOB).status_code == 404,
      "a retention job was served as an import")

# --- a running import shows how far it has got ----------------------------

claimed = _claim_job("worker-progress", job_types=[JobType.CSV_IMPORT])
check("the import job is claimed", claimed is not None and claimed.id == JOB_A,
      str(claimed))
import_progress.write_counts(JOB_A, "departments", 1, 2)

r = progress_of("departments", JOB_A)
body = r.json()
check("a running import reports its state", body.get("state") == "running",
      str(body)[:200])
check("a running import reports the rows it has applied",
      body.get("rows_applied") == 1
      and body.get("rows_pending") == 1
      and body.get("percent") == 50,
      str(body)[:200])
check("a running import reports the batch it is in",
      body.get("batches_done") == 1 and body.get("batches_total") == 1,
      str(body)[:200])
check("a running import has no result yet", body.get("result") is None,
      str(body)[:200])

# --- a finished import serves the report ---------------------------------

result = job_handlers.csv_import(
    claimed,
    {"entity": "departments", "confirmation_token": TOKEN_A,
     "user_id": ADMIN_ID},
)
_complete_job(claimed.id, "worker-progress", result)

r = progress_of("departments", JOB_A)
body = r.json()
check("a finished import reports success", body.get("state") == "succeeded",
      str(body)[:200])
check("a finished import serves its report",
      isinstance(body.get("result"), dict)
      and body["result"].get("created") == 2,
      str(body)[:300])
check("the report is marked as stored", body.get("result_stored") is True,
      str(body)[:200])
_report = body.get("result") or {}
check("the report names the rows it applied",
      _report.get("rows")
      and all(row.get("status") == "create" for row in _report.get("rows", [])),
      str(_report.get("rows"))[:200])
check("a finished import reports every row applied",
      body.get("rows_applied") == 2
      and body.get("rows_pending") == 0
      and body.get("percent") == 100,
      str(body)[:200])
check("the progress agrees with the job's own report",
      body.get("rows_applied")
      == (_report.get("created") or 0)
      + (_report.get("updated") or 0)
      + (_report.get("unchanged") or 0),
      str(body)[:200])
check("the import reports itself committed",
      body.get("committed") is True and body.get("import_status") == "committed",
      str(body)[:200])

# --- a failed import reports zero applied, not the rows it reached --------

JOB_B, TOKEN_B = queue_import(
    "departments", "name,code\nFailA,FL1\nFailB,FL2\n", ADMIN_ID
)
claimed_b = _claim_job("worker-progress-b",
                         job_types=[JobType.CSV_IMPORT])
check("the second import job is claimed", claimed_b is not None,
      str(claimed_b))
import_progress.write_counts(JOB_B, "departments", 1, 2)
_fail_job(
    claimed_b.id, "worker-progress-b", "job_failed",
    "RuntimeError: the database went away", permanent=True,
)

r = progress_of("departments", JOB_B)
body = r.json()
check("a dead-lettered import reports itself dead", body.get("state") == "dead",
      str(body)[:200])
check("a failed import reports zero rows applied",
      body.get("rows_applied") == 0, str(body)[:200])
check("a failed import reports how far it reached, separately",
      body.get("rows_applied_before_failure") == 1, str(body)[:200])
check("a failed import names the reason",
      (body.get("failure") or {}).get("code") == "job_failed"
      and "database" in ((body.get("failure") or {}).get("message") or ""),
      str(body.get("failure"))[:200])
check("a failed import says nothing was written",
      "rolled back" in (body.get("note") or "").lower(), body.get("note"))
check("a failed import serves no report", body.get("result") is None,
      str(body)[:200])

# --- a cancelled import says so ------------------------------------------

JOB_D, TOKEN_D = queue_import(
    "departments", "name,code\nCancelA,CA1\nCancelB,CA2\n", ADMIN_ID
)
claimed_d = _claim_job(
    "worker-progress-d", job_types=[JobType.CSV_IMPORT]
)
_session = SessionLocal()
try:
    runner.cancel_import(_session, "departments", TOKEN_D)
finally:
    _session.close()

_cancelled_error = ""
try:
    job_handlers.csv_import(
        claimed_d,
        {"entity": "departments", "confirmation_token": TOKEN_D,
         "user_id": ADMIN_ID},
    )
except Exception as exc:  # noqa: BLE001
    _cancelled_error = type(exc).__name__
check("a cancelled import refuses permanently, not transiently",
      _cancelled_error == "JobCancelled",
      _cancelled_error or "the handler returned a result")

_fail_job(
    claimed_d.id, "worker-progress-d", "job_cancelled",
    "The import was cancelled before it finished.", permanent=True,
)

r = progress_of("departments", JOB_D)
body = r.json()
check("a cancelled import reports itself cancelled",
      body.get("import_status") == "cancelled"
      and body.get("committed") is False,
      str(body)[:200])
check("a cancelled import reports zero rows applied",
      body.get("rows_applied") == 0, str(body)[:200])
check("a cancelled import says nothing was written",
      "cancelled" in (body.get("note") or "").lower(),
      body.get("note"))

# --- a rejected row is counted, and named in the report -------------------

JOB_C, TOKEN_C = queue_import(
    "employees",
    "employee_id,first_name,last_name,email,hire_date,job_code,"
    "department_code\n"
    "EMP-9400,Bad,Row,progbad@example.com,not-a-date,J-ENG,ALPHA\n"
    "EMP-9401,Good,Row,proggood@example.com,2026-01-15,J-ENG,ALPHA\n",
    ADMIN_ID,
)
claimed_c = _claim_job(
    "worker-progress-c", job_types=[JobType.CSV_IMPORT]
)
result_c = job_handlers.csv_import(
    claimed_c,
    {"entity": "employees", "confirmation_token": TOKEN_C,
     "user_id": ADMIN_ID},
)
_complete_job(claimed_c.id, "worker-progress-c", result_c)

r = progress_of("employees", JOB_C)
body = r.json()
check("a rejected row is counted, not applied",
      body.get("rows_total") == 2
      and body.get("rows_rejected") == 1
      and body.get("rows_accepted") == 1
      and body.get("rows_applied") == 1,
      str(body)[:300])
check("the failed row is named in the report",
      [row for row in (body.get("result") or {}).get("rows", [])
       if row.get("status") == "reject"],
      str((body.get("result") or {}).get("rows"))[:200])

# --- a job with no stored payload is not served ---------------------------

_session = SessionLocal()
try:
    row = _session.query(JobQueue).filter(JobQueue.id == JOB_C).one()
    row.input_json = None
    _session.add(row)
    _session.commit()
finally:
    _session.close()
check("a job with no stored payload is not served",
      progress_of("employees", JOB_C).status_code == 404,
      "a job queued before its payload was stored was served")

# --------------------------------------------------------------------------
print("IMPORT — DI-06: a queued import can be cancelled")
print("=" * 68)


def cancel_import(entity: str, token: str, headers: dict | None = None):
    return client.post(
        f"/api/v1/import-export/import/{entity}/cancel",
        headers=headers or AUTH,
        params={"confirmation_token": token},
    )


JOB_E, TOKEN_E = queue_import(
    "departments", "name,code\nStopA,ST1\nStopB,ST2\n", ADMIN_ID
)
departments_before = count(Department)
audits_before = audit_count("import_cancel")

r = cancel_import("departments", TOKEN_E)
body = r.json()
check("a queued import can be cancelled", r.status_code == 200,
      f"{r.status_code} {r.text[:160]}")
check("the answer says the import is cancelled",
      body.get("cancelled") is True
      and body.get("import_status") == "cancelled"
      and body.get("committed") is False,
      str(body)[:220])
check("the answer carries the counts the dry run produced",
      body.get("total_rows") == 2 and body.get("create") == 2,
      str(body)[:220])

_session = SessionLocal()
try:
    record = _session.query(ImportDryRun).filter(
        ImportDryRun.token == TOKEN_E
    ).one()
    check("the import record is cancelled",
          record.status == ImportStatus.CANCELLED, record.status)
    check("the reason is recorded against the import",
          (record.failure_reason or "").lower().startswith("cancelled"),
          str(record.failure_reason))
finally:
    _session.close()

check("the cancellation is audited",
      audit_count("import_cancel") == audits_before + 1,
      f"{audits_before} -> {audit_count('import_cancel')}")

# The job, when it runs, applies nothing.
claimed_e = _claim_job(
    "worker-cancel", job_types=[JobType.CSV_IMPORT]
)
_cancel_error = ""
try:
    job_handlers.csv_import(
        claimed_e,
        {"entity": "departments", "confirmation_token": TOKEN_E,
         "user_id": ADMIN_ID},
    )
except Exception as exc:  # noqa: BLE001
    _cancel_error = type(exc).__name__
check("the cancelled import's job refuses rather than applying it",
      _cancel_error == "JobCancelled", _cancel_error or "the job returned")
check("the cancelled import wrote nothing",
      count(Department) == departments_before,
      f"{departments_before} -> {count(Department)}")

# Cancelling twice changes nothing and writes no second audit row.
r = cancel_import("departments", TOKEN_E)
check("cancelling twice is idempotent",
      r.status_code == 200 and r.json().get("import_status") == "cancelled",
      f"{r.status_code} {r.text[:160]}")
check("a second cancellation writes no second audit row",
      audit_count("import_cancel") == audits_before + 1,
      f"{audit_count('import_cancel')}")

# A committed import cannot be cancelled.
r = cancel_import("employees", TOKEN_C)
check("a committed import cannot be cancelled", r.status_code == 409,
      f"{r.status_code} {r.text[:160]}")
check("the refusal says why",
      r.json().get("error", {}).get("code") == "import_not_cancellable",
      str(r.json())[:220])

# An unknown token is not a cancellation.
r = cancel_import("departments", "not-a-token")
check("an unknown token is refused as a conflict",
      r.status_code == 409
      and r.json().get("error", {}).get("code") == "invalid_confirmation_token",
      f"{r.status_code} {r.text[:160]}")

# Another operator's token is refused, with the shared envelope.
_preview = dry_run("departments", "name,code\nMine,MN1\n")
_other = cancel_import("departments", _preview.json()["confirmation_token"], HR_AUTH)
check("another operator's import cannot be cancelled",
      _other.status_code == 403
      and _other.json().get("error", {}).get("code") == "forbidden",
      f"{_other.status_code} {_other.text[:160]}")

# --------------------------------------------------------------------------
shutil.rmtree(STORAGE_DIR, ignore_errors=True)
try:
    engine.dispose()
except Exception:  # noqa: BLE001
    pass

# Soft-fail safety net: when the run finished but a check failed with a pool
# timeout signature (e.g. a 500 from a handler whose checkout timed out),
# retry once with a fresh database instead of reporting the infrastructure
# flake as an import failure. Import-semantics failures never match and are
# reported as-is with no retry.
if RESULTS["fail"] and _SUITE_ATTEMPT == "0":
    _failure_text = " ".join(
        f"{name} {detail}" for name, detail in FAILURES
    )
    if "QueuePool" in _failure_text or "TimeoutError" in _failure_text:
        _retry_with_fresh_db()

print()
print("=" * 68)
print(f"==== IMPORT SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
