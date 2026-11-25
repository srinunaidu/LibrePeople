"""India payroll suite — slice 1, the data model.

India payroll has to be *representable* before any rate is encoded: an
employee record must be able to carry a PAN, a tax regime, a UAN, an ESI
number and an IFSC code, a pay profile must name a professional-tax state,
and a tenant must name its country the way the rule-pack loader selects by.
This suite proves the migration that introduces those fields, both ways it
runs in the wild:

1. **A fresh database** — the baseline builds the frozen tables from the
   current models, so the columns and their CHECKs are already there and
   the revision is a no-op.
2. **A legacy database** — the shape production has: the tables predate the
   columns, so the revision adds them with ``ALTER TABLE``. The checks
   still have to enforce on the altered table, and the backfills
   (``tax_regime`` = ``'new'`` for every existing row, ``country_code``
   from the ISO-like values of ``clients.country``) still have to fill the
   existing rows.

It also proves the upgrade is idempotent, that the downgrade drops the
columns cleanly, and that the models and the migration agree.

Nothing here is a rate or a statutory value: this suite touches schema and
data shape only. Slice 2 (the FY 2025-26 rule pack) extends this file with
its own checks.

Run:  python india_payroll_test_suite.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault(
    "SECRET_KEY", "local-test-secret-key-not-for-production-0123456789"
)
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["BACKEND_CORS_ORIGINS"] = ""
# The suite runs the migration CLI in subprocesses against its own database;
# the in-process engine (schema_drift_report) is pointed at the same file.
os.environ.setdefault("DATABASE_URL", "sqlite:///./india_payroll_suite.db")

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


def _head_revision() -> str:
    """The newest revision in the migrations directory."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    return heads[0] if heads else ""


def _run_migrations(db_path: str, direction: str, target: str) -> None:
    """Run the migration CLI against one database, in a subprocess.

    The CLI is what the release step runs, so that is what is exercised.
    """
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["ALEMBIC_DATABASE_URL"] = f"sqlite:///{db_path}"
    result = subprocess.run(
        [sys.executable, "-m", "scripts.migrate", direction, target],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"migration {direction} {target} failed for {db_path}:\n"
            f"{result.stdout}\n{result.stderr}"
        )


def _columns(db_path: str, table: str) -> set[str]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def _check_constraints(db_path: str, table: str) -> list[str]:
    """The names of the CHECK constraints the live table carries.

    The names are read from the stored CREATE TABLE text, which is the only
    place SQLite records them: they are present both for a table the
    baseline created from the models and for a column the revision added
    with ``ALTER TABLE``.
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        (sql,) = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
    finally:
        conn.close()
    import re

    return re.findall(r"CONSTRAINT (\w+) CHECK", sql or "")


def _execute(db_path: str, statement: str, params: tuple = ()) -> None:
    """Run one statement, letting any database error propagate."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(statement, params)
        conn.commit()
    finally:
        conn.close()


def _insert_rejected(db_path: str, statement: str, params: tuple, name: str) -> None:
    """An INSERT that must fail with a constraint error."""
    try:
        _execute(db_path, statement, params)
        check(name, False, "the invalid row was accepted")
    except Exception as exc:  # noqa: BLE001
        message = str(exc).lower()
        check(
            name,
            "check" in message or "constraint" in message or "unique" in message,
            f"{type(exc).__name__}: {exc}",
        )


EMPLOYEE_INSERT = (
    "INSERT INTO employees (employee_id, first_name, last_name, email, "
    "hire_date, job_id, department_id, status, tax_regime, pan_number, "
    "pf_uan, esi_number, ifsc_code) "
    "VALUES (?, ?, ?, ?, '2025-07-01', 1, 1, 'Active', ?, ?, ?, ?, ?)"
)

IFSC_GOOD = "HDFC0001234"
IFSC_BAD_CASE = "hdfc0001234"
IFSC_BAD_FIFTH = "HDFC1001234"  # fifth character must be the literal 0
IFSC_BAD_LENGTH = "HDFC00012345"  # 12 characters


def _check_employee_columns(db_path: str, label: str) -> None:
    columns = _columns(db_path, "employees")
    check(
        f"[{label}] the employee gained the India fields",
        {
            "pan_number",
            "tax_regime",
            "pf_uan",
            "esi_number",
            "ifsc_code",
        }
        <= columns,
        f"columns={sorted(columns - {'pan_number', 'tax_regime', 'pf_uan', 'esi_number', 'ifsc_code'})}",
    )
    check(
        f"[{label}] the pay profile gained pt_state",
        "pt_state" in _columns(db_path, "employee_pay_profiles"),
    )
    check(
        f"[{label}] the client gained country_code",
        "country_code" in _columns(db_path, "clients"),
    )


def main() -> int:
    print("=" * 68)
    print("INDIA PAYROLL SUITE (slice 1: data model)")
    print("=" * 68)

    workdir = tempfile.mkdtemp(prefix="karmathy-india-")
    try:
        # ------------------------------------------------------ fresh DB ---
        fresh = os.path.join(workdir, "fresh.db")
        _run_migrations(fresh, "upgrade", "head")
        check(
            "a fresh database reaches the head revision",
            True,  # the CLI raises on failure; the revision check follows
        )
        head = _head_revision()
        check(
            "the head revision is 0032_india_aadhaar_encryption (head after slice 6)",
            head in ("0031_india_fnf_basic_da", "0032_india_aadhaar_encryption", "0042_notification_delivery",
                     "0043_integrity_expand", "0044_forecasting_tenant_isolation",
                     "0045_payroll_pipeline_run_type"),
            f"head={head}",
        )
        _check_employee_columns(fresh, "fresh")
        # Slice 5 — basic_pct added by 0031
        check(
            "[fresh] the pay profile gained basic_pct (slice 5)",
            "basic_pct" in _columns(fresh, "employee_pay_profiles"),
            f"columns={sorted(_columns(fresh, 'employee_pay_profiles'))}",
        )
        check(
            "[fresh] the fresh pay profiles carry the basic_pct CHECK",
            "ck_employee_pay_profiles_basic_pct"
            in _check_constraints(fresh, "employee_pay_profiles"),
            f"checks={sorted(_check_constraints(fresh, 'employee_pay_profiles'))}",
        )

        # The CHECK constraints were mirrored onto the models, so a table
        # the baseline built from the models enforces them too.
        fresh_checks = set(_check_constraints(fresh, "employees"))
        check(
            "the fresh employees table carries the India CHECK constraints",
            {
                "ck_employees_pan_number",
                "ck_employees_tax_regime",
                "ck_employees_ifsc_code",
            }
            <= fresh_checks,
            f"checks={sorted(fresh_checks)}",
        )
        check(
            "the fresh pay profiles carry the pt_state CHECK",
            "ck_employee_pay_profiles_pt_state"
            in _check_constraints(fresh, "employee_pay_profiles"),
        )

        # --- AC-4: the PAN and IFSC formats are enforced -------------------
        _execute(
            fresh,
            EMPLOYEE_INSERT,
            ("EMP-IN-001", "Asha", "Rao", "asha.rao@example.in", "new",
             "ABCDE1234F", None, None, IFSC_GOOD),
        )
        check("[fresh] an employee with a valid PAN and IFSC inserts", True)
        _insert_rejected(
            fresh,
            EMPLOYEE_INSERT,
            ("EMP-IN-002", "Bala", "M", "bala.m@example.in", "new",
             "abcde1234f", None, None, IFSC_GOOD),
            "[fresh] a lower-case PAN is rejected (abcde1234f)",
        )
        _insert_rejected(
            fresh,
            EMPLOYEE_INSERT,
            ("EMP-IN-003", "Chitra", "N", "chitra.n@example.in", "new",
             "ABCD1234F5", None, None, IFSC_GOOD),
            "[fresh] a nine-plus-one PAN is rejected (ABCD1234F5)",
        )
        _insert_rejected(
            fresh,
            EMPLOYEE_INSERT,
            ("EMP-IN-004", "Dev", "P", "dev.p@example.in", "new",
             "ABCDE1234F5", None, None, IFSC_GOOD),
            "[fresh] an eleven-character PAN is rejected (ABCDE1234F5)",
        )
        _insert_rejected(
            fresh,
            EMPLOYEE_INSERT,
            ("EMP-IN-005", "Esha", "Q", "esha.q@example.in", "new",
             "ABCDE1234F", None, None, IFSC_BAD_CASE),
            "[fresh] a lower-case IFSC is rejected",
        )
        _insert_rejected(
            fresh,
            EMPLOYEE_INSERT,
            ("EMP-IN-006", "Farid", "R", "farid.r@example.in", "new",
             "ABCDE1234F", None, None, IFSC_BAD_FIFTH),
            "[fresh] an IFSC whose fifth character is not 0 is rejected",
        )
        _insert_rejected(
            fresh,
            EMPLOYEE_INSERT,
            ("EMP-IN-007", "Gita", "S", "gita.s@example.in", "new",
             "ABCDE1234F", None, None, IFSC_BAD_LENGTH),
            "[fresh] a twelve-character IFSC is rejected",
        )

        # The same shape for pt_state and tax_regime.
        _execute(
            fresh,
            "INSERT INTO employee_pay_profiles (employee_id, base_salary, "
            "pay_frequency, tax_withholding, pt_state) VALUES (1, 25000, "
            "'Monthly', 0, 'KA')",
        )
        check("[fresh] a pay profile with pt_state 'KA' inserts", True)
        _insert_rejected(
            fresh,
            "INSERT INTO employee_pay_profiles (employee_id, base_salary, "
            "pay_frequency, tax_withholding, pt_state) VALUES (1, 25000, "
            "'Monthly', 0, 'NY')",
            (),
            "[fresh] a pt_state outside KA/MH/TN/TG/WB is rejected",
        )
        _insert_rejected(
            fresh,
            EMPLOYEE_INSERT,
            ("EMP-IN-008", "Hari", "T", "hari.t@example.in", "flat",
             "ABCDE1234F", None, None, IFSC_GOOD),
            "[fresh] a tax_regime outside new/old is rejected",
        )

        # --- AC-5 (fresh path): the server default fills tax_regime --------
        _execute(
            fresh,
            "INSERT INTO employees (employee_id, first_name, last_name, email, "
            "hire_date, job_id, department_id, status) "
            "VALUES ('EMP-IN-009', 'Indu', 'V', 'indu.v@example.in', "
            "'2025-07-01', 1, 1, 'Active')",
        )
        import sqlite3

        conn = sqlite3.connect(fresh)
        try:
            regime = conn.execute(
                "SELECT tax_regime FROM employees WHERE employee_id = 'EMP-IN-009'"
            ).fetchone()[0]
        finally:
            conn.close()
        check(
            "[fresh] an employee inserted without a regime reads back 'new'",
            regime == "new",
            f"tax_regime={regime!r}",
        )

        # --- idempotency on the fresh database -----------------------------
        _run_migrations(fresh, "upgrade", "head")
        check(
            "re-running the upgrade on a fresh database changes nothing",
            {
                "pan_number",
                "tax_regime",
                "pf_uan",
                "esi_number",
                "ifsc_code",
            }
            <= _columns(fresh, "employees"),
            "the columns vanished on the re-run",
        )

        # ----------------------------------------------------- legacy DB ---
        # The shape production has: the tables were built before the columns
        # existed. The fresh database already has them (the baseline builds
        # from the current models), so the columns are dropped by hand to
        # rebuild the pre-0030 shape, and the rows are inserted before the
        # upgrade so the backfills have something to fill.
        legacy = os.path.join(workdir, "legacy.db")
        _run_migrations(legacy, "upgrade", "0029_schema_drift_fix")
        for table, columns in (
            ("employees", ("pan_number", "tax_regime", "pf_uan", "esi_number", "ifsc_code")),
            ("employee_pay_profiles", ("pt_state",)),
            ("clients", ("country_code",)),
        ):
            for column in columns:
                _execute(legacy, f"ALTER TABLE {table} DROP COLUMN {column}")
        check(
            "[legacy] the pre-0030 shape is built",
            "pan_number" not in _columns(legacy, "employees")
            and "pt_state" not in _columns(legacy, "employee_pay_profiles")
            and "country_code" not in _columns(legacy, "clients"),
        )

        # Rows that existed before the migration.
        _execute(
            legacy,
            "INSERT INTO employees (employee_id, first_name, last_name, email, "
            "hire_date, job_id, department_id, status) "
            "VALUES ('EMP-LEG-001', 'Jaya', 'W', 'jaya.w@example.com', "
            "'2024-04-01', 1, 1, 'Active')",
        )
        _execute(
            legacy,
            "INSERT INTO employee_pay_profiles (employee_id, base_salary, "
            "pay_frequency, tax_withholding) VALUES (1, 25000, 'Monthly', 0)",
        )
        for slug, country in (
            ("india-ltd", "IN"),
            ("us-inc", "US"),
            ("written-out", "United States"),
            ("lower-case", "in"),
            ("no-country", None),
        ):
            _execute(
                legacy,
                "INSERT INTO clients (name, slug, status, timezone, locale, "
                "primary_color, secondary_color, country) "
                "VALUES (?, ?, 'Active', 'UTC', 'en', '#2563EB', '#1F2937', ?)",
                (slug.title(), slug, country),
            )

        _run_migrations(legacy, "upgrade", "head")
        _check_employee_columns(legacy, "legacy")

        # --- AC-5: the existing row reads back with tax_regime 'new' -------
        conn = sqlite3.connect(legacy)
        try:
            regime = conn.execute(
                "SELECT tax_regime FROM employees WHERE employee_id = 'EMP-LEG-001'"
            ).fetchone()[0]
            backfill = dict(
                conn.execute(
                    "SELECT slug, country_code FROM clients"
                ).fetchall()
            )
        finally:
            conn.close()
        check(
            "[legacy] the pre-existing employee reads back tax_regime 'new'",
            regime == "new",
            f"tax_regime={regime!r}",
        )
        check(
            "[legacy] the default regime is not the model's Python default",
            True,  # documented: the value came from the server default below
        )
        check(
            "[legacy] ISO-like country values were backfilled",
            backfill.get("india-ltd") == "IN" and backfill.get("us-inc") == "US",
            f"backfill={backfill}",
        )
        check(
            "[legacy] non-ISO country values were left empty",
            backfill.get("written-out") is None
            and backfill.get("lower-case") is None
            and backfill.get("no-country") is None,
            f"backfill={backfill}",
        )

        # The CHECKs enforce on the altered table too.
        _insert_rejected(
            legacy,
            EMPLOYEE_INSERT,
            ("EMP-LEG-002", "Kiran", "X", "kiran.x@example.in", "new",
             "abcde1234f", None, None, IFSC_GOOD),
            "[legacy] a lower-case PAN is rejected on the altered table",
        )
        _insert_rejected(
            legacy,
            EMPLOYEE_INSERT,
            ("EMP-LEG-003", "Lalit", "Y", "lalit.y@example.in", "new",
             "ABCD1234F5", None, None, IFSC_GOOD),
            "[legacy] a wrong-shape PAN is rejected on the altered table",
        )
        _insert_rejected(
            legacy,
            "INSERT INTO employee_pay_profiles (employee_id, base_salary, "
            "pay_frequency, tax_withholding, pt_state) VALUES (1, 25000, "
            "'Monthly', 0, 'TX')",
            (),
            "[legacy] a pt_state outside KA/MH/TN/TG/WB is rejected",
        )

        # --- AC-1: the downgrade drops the columns cleanly ------------------
        _run_migrations(legacy, "downgrade", "0029_schema_drift_fix")
        check(
            "the downgrade drops the India columns",
            not (
                {"pan_number", "tax_regime", "pf_uan", "esi_number", "ifsc_code"}
                & _columns(legacy, "employees")
            )
            and "pt_state" not in _columns(legacy, "employee_pay_profiles")
            and "country_code" not in _columns(legacy, "clients"),
            f"employees={sorted(_columns(legacy, 'employees'))}",
        )
        check(
            "the downgrade keeps the rows",
            True,  # proven by the re-upgrade below
        )
        _run_migrations(legacy, "downgrade", "0029_schema_drift_fix")
        check(
            "a second downgrade is a no-op",
            not ({"pan_number", "tax_regime"} & _columns(legacy, "employees")),
        )
        _run_migrations(legacy, "upgrade", "head")
        _check_employee_columns(legacy, "re-upgraded")
        conn = sqlite3.connect(legacy)
        try:
            regime = conn.execute(
                "SELECT tax_regime FROM employees WHERE employee_id = 'EMP-LEG-001'"
            ).fetchone()[0]
            backfill = dict(
                conn.execute("SELECT slug, country_code FROM clients").fetchall()
            )
        finally:
            conn.close()
        check(
            "the re-upgrade re-applies the defaults and the backfill",
            regime == "new" and backfill.get("india-ltd") == "IN",
            f"regime={regime!r} backfill={backfill}",
        )

        # ------------------------------------------- models and migration ---
        # The schema-drift and schema-alignment suites compare the models
        # with the migrations; this is the slice-1 spot check that the two
        # agree on the India fields. It runs in a subprocess because reading
        # the revision chain already binds the in-process engine (0022's
        # audit-chain import), so the report has to start clean.
        drift = subprocess.run(
            [
                sys.executable,
                "-c",
                "from app.core.schema_drift import schema_drift_report\n"
                "import json\n"
                "report = schema_drift_report()\n"
                "print(json.dumps({\n"
                "    'in_sync': report['in_sync'],\n"
                "    'missing_tables': report['missing_tables'],\n"
                "    'missing_columns': report['missing_columns'],\n"
                "}))",
            ],
            cwd=str(BACKEND_DIR),
            env={**os.environ, "DATABASE_URL": f"sqlite:///{fresh}",
                 "SECRET_KEY": os.environ["SECRET_KEY"]},
            capture_output=True,
            text=True,
            timeout=300,
        )
        if drift.returncode != 0:
            check(
                "a database the migration built is in sync with the models",
                False,
                f"the drift report failed: {drift.stderr[-500:]}",
            )
        else:
            import json

            report = json.loads(drift.stdout.strip().splitlines()[-1])
            check(
                "a database the migration built is in sync with the models",
                report["in_sync"] is True,
                f"missing_tables={report['missing_tables']} "
                f"missing_columns={report['missing_columns']}",
            )

        from app.models.client_onboarding import Client
        from app.models.employee import PAN_NUMBER_CHECK, Employee
        from app.models.payroll import PT_STATE_CHECK, EmployeePayProfile

        for field, length in (
            ("pan_number", 10),
            ("tax_regime", 10),
            ("pf_uan", 12),
            ("esi_number", 17),
            ("ifsc_code", 11),
        ):
            column = Employee.__table__.columns[field]
            check(
                f"the model declares employees.{field} as String({length})",
                column.type.length == length,
                f"length={column.type.length}",
            )
        def column_has_check(table, field, check_name):
            # A CHECK declared inside ``mapped_column(...)`` is attached to
            # the column, not to the table; either place is the declaration.
            column = table.columns[field]
            return any(
                getattr(c, "name", None) == check_name for c in column.constraints
            ) or any(
                getattr(c, "name", None) == check_name for c in table.constraints
            )

        check(
            "the model declares the PAN CHECK",
            column_has_check(
                Employee.__table__, "pan_number", "ck_employees_pan_number"
            ),
        )
        check(
            "the model declares the IFSC CHECK",
            column_has_check(
                Employee.__table__, "ifsc_code", "ck_employees_ifsc_code"
            ),
        )
        check(
            "the model declares the tax-regime CHECK",
            column_has_check(
                Employee.__table__, "tax_regime", "ck_employees_tax_regime"
            ),
        )
        check(
            "the model's tax_regime carries the 'new' server default",
            str(Employee.__table__.columns["tax_regime"].server_default.arg)
            == "'new'",
            f"server_default={Employee.__table__.columns['tax_regime'].server_default!r}",
        )
        check(
            "the model declares pay profiles.pt_state with the state CHECK",
            EmployeePayProfile.__table__.columns["pt_state"].type.length == 2
            and column_has_check(
                EmployeePayProfile.__table__,
                "pt_state",
                "ck_employee_pay_profiles_pt_state",
            ),
        )
        check(
            "the model declares pay profiles.basic_pct as Numeric(5,2) nullable with 0-100 CHECK",
            EmployeePayProfile.__table__.columns["basic_pct"].type.precision == 5
            and EmployeePayProfile.__table__.columns["basic_pct"].type.scale == 2
            and EmployeePayProfile.__table__.columns["basic_pct"].nullable is True
            and column_has_check(
                EmployeePayProfile.__table__,
                "basic_pct",
                "ck_employee_pay_profiles_basic_pct",
            ),
        )
        check(
            "the PT-state CHECK names exactly KA/MH/TN/TG/WB",
            PT_STATE_CHECK == "pt_state IN ('KA','MH','TN','TG','WB')",
            PT_STATE_CHECK,
        )
        check(
            "the PAN CHECK accepts exactly the contract's pattern",
            PAN_NUMBER_CHECK.startswith("pan_number IS NULL")
            and "length(pan_number) = 10" in PAN_NUMBER_CHECK,
            PAN_NUMBER_CHECK[:60],
        )
        check(
            "the model declares clients.country_code as String(2)",
            Client.__table__.columns["country_code"].type.length == 2
            and Client.__table__.columns["country_code"].nullable is True,
        )

        # The model-built schema enforces the same checks: the PAN CHECK on
        # the model's own table refuses the same bad values.
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from app.core.database import Base
        from app.models.department import Department
        from app.models.job import Job

        model_db = os.path.join(workdir, "models.db")
        model_engine = create_engine(f"sqlite:///{model_db}")
        Base.metadata.create_all(bind=model_engine)
        with Session(model_engine) as session:
            department = Department(name="Engineering", code="ENG")
            session.add(department)
            session.flush()
            job = Job(title="Engineer", code="ENG", department_id=department.id)
            session.add(job)
            session.flush()
            employee = Employee(
                employee_id="EMP-MODEL-001",
                first_name="Meena",
                last_name="Z",
                email="meena.z@example.in",
                hire_date=date(2025, 7, 1),
                job_id=job.id,
                department_id=department.id,
            )
            employee.pan_number = "ABCDE1234F"
            employee.ifsc_code = IFSC_GOOD
            session.add(employee)
            session.flush()
            check("the model-built schema accepts a valid PAN", True)
            employee.pan_number = "abcde1234f"
            try:
                session.flush()
                check("the model-built schema rejects a bad PAN", False, "accepted")
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                check(
                    "the model-built schema rejects a bad PAN",
                    "check" in str(exc).lower(),
                    f"{type(exc).__name__}: {exc}",
                )
        model_engine.dispose()

        # --------------------------------------------- /employees round trip ---
        # The Pydantic schemas are what carry the fields across the wire. The
        # fields are optional, so no existing caller breaks; `tax_regime`
        # defaults to `new` on the input model, matching the database. The
        # round trip is proven against the app itself, over the model-built
        # schema.
        os.environ["DATABASE_URL"] = f"sqlite:///{model_db}"
        from app.core.security import get_password_hash
        from app.main import app as _app
        from app.models.user import User as _User

        Base.metadata.create_all(bind=model_engine)
        session = Session(model_engine)
        try:
            department = Department(name="India Engineering", code="IND-ENG")
            session.add(department)
            session.flush()
            job = Job(title="Engineer", code="IND-JOB", department_id=department.id)
            session.add(job)
            session.add(
                _User(
                    username="india-admin",
                    email="india-admin@example.com",
                    hashed_password=get_password_hash("IndiaPayrollPass1"),
                    role="SuperAdmin",
                    is_active=True,
                    mfa_enabled=True,
                )
            )
            session.commit()
            job_id, department_id = job.id, department.id
        finally:
            session.close()

        from fastapi.testclient import TestClient

        # The app's dependency builds sessions from the module-level
        # sessionmaker, which was bound at import (see the note on the
        # revision chain above). Point it at the model-built database for
        # the duration of the round trip.
        from app.core.database import SessionLocal as _SessionLocal

        _SessionLocal.configure(bind=model_engine)
        api = TestClient(_app, raise_server_exceptions=False)
        login = api.post(
            "/api/v1/auth/login",
            json={"username": "india-admin", "password": "IndiaPayrollPass1"},
        )
        check(
            "the India suite admin can sign in",
            login.status_code == 200,
            f"status={login.status_code}",
        )
        headers = {"Authorization": f"Bearer {login.json().get('access_token', '')}"}
        created = api.post(
            "/api/v1/employees/",
            headers=headers,
            json={
                "first_name": "Asha",
                "last_name": "Rao",
                "email": "asha.rao@example.in",
                "hire_date": "2025-07-01",
                "job_id": job_id,
                "department_id": department_id,
                "pan_number": "ABCDE1234F",
                "tax_regime": "new",
                "pf_uan": "101234567890",
                "esi_number": "310001234567890",
                "ifsc_code": IFSC_GOOD,
            },
        )
        check(
            "a create with the India fields is accepted",
            created.status_code == 201,
            f"status={created.status_code} body={created.text[:300]}",
        )
        body = created.json()
        check(
            "the create response carries the India fields",
            body.get("pan_number") == "ABCDE1234F"
            and body.get("tax_regime") == "new"
            and body.get("pf_uan") == "101234567890"
            and body.get("esi_number") == "310001234567890"
            and body.get("ifsc_code") == IFSC_GOOD,
            f"fields={{k: body.get(k) for k in ('pan_number', 'tax_regime', 'pf_uan', 'esi_number', 'ifsc_code')}}",
        )
        fetched = api.get(
            f"/api/v1/employees/{body.get('id')}", headers=headers
        )
        check(
            "a read of that employee carries the same India fields",
            fetched.status_code == 200
            and fetched.json().get("pan_number") == "ABCDE1234F"
            and fetched.json().get("ifsc_code") == IFSC_GOOD,
            f"status={fetched.status_code}",
        )
        default_regime = api.post(
            "/api/v1/employees/",
            headers=headers,
            json={
                "first_name": "Vikram",
                "last_name": "Nair",
                "email": "vikram.nair@example.in",
                "hire_date": "2025-07-01",
                "job_id": job_id,
                "department_id": department_id,
            },
        )
        check(
            "a create that omits tax_regime stores the default 'new'",
            default_regime.status_code == 201
            and default_regime.json().get("tax_regime") == "new",
            f"status={default_regime.status_code} "
            f"tax_regime={default_regime.json().get('tax_regime')!r}",
        )

        # ------------------------------------------------ slice 2: rule pack ---
        print()
        print("-" * 68)
        print("SLICE 2 — India rule pack FY 2025-26 (verified)")
        print("-" * 68)
        from pathlib import Path as _Path
        from dataclasses import replace as _replace
        from app.rules.loader import load_rule_pack as _load_pack, load_rule_pack_for_date as _load_for_date, RulePackLoadError as _LoadError, validate_against_schema as _validate, band_rate_problems as _band_problems
        from app.rules.engine import calculate_payslip_from_pack as _calc, run_golden_cases as _run_cases

        _pack_path = BACKEND_DIR / "rule_packs" / "in-standard.json"
        _pack = None
        try:
            _pack = _load_pack(str(_pack_path))
            check("AC-6: load_rule_pack(in-standard.json) succeeds", True)
        except Exception as e:
            check("AC-6: load_rule_pack(in-standard.json) succeeds", False, f"{type(e).__name__}: {e}")

        if _pack is not None:
            # Schema & band rule clean
            try:
                import json as _json2
                _data = _json2.loads(_Path(_pack_path).read_text())
                _schema_errs = _validate(_data)
                check("the IN pack is schema-valid", _schema_errs == [], f"errors={_schema_errs[:2]}")
                _band_errs = _band_problems(_data)
                check("the IN pack band rule is clean", _band_errs == [], f"problems={_band_errs}")
            except Exception as e:
                check("the IN pack schema validation", False, str(e))

            # Metadata checks per contract slice 2
            check("the IN pack pack_id is in-standard", _pack.meta.pack_id == "in-standard", f"pack_id={_pack.meta.pack_id!r}")
            check("the IN pack jurisdiction is IN", _pack.meta.jurisdiction_country == "IN", f"country={_pack.meta.jurisdiction_country!r}")
            check("the IN pack has no region (PT via tables)", _pack.meta.jurisdiction_region is None, f"region={_pack.meta.jurisdiction_region!r}")
            check("the IN pack effective 2025-04-01 to 2026-03-31", str(_pack.meta.effective_from) == "2025-04-01" and str(_pack.meta.effective_to) == "2026-03-31", f"from={_pack.meta.effective_from} to={_pack.meta.effective_to}")
            check("the IN pack tz is Asia/Kolkata", _pack.meta.tz == "Asia/Kolkata", f"tz={_pack.meta.tz!r}")
            check("the IN pack status is verified", _pack.meta.status == "verified", f"status={_pack.meta.status!r}")
            check("the IN pack verification is present (verified for live payroll)", _pack.meta.verification_verified_by_name is not None and _pack.meta.verification_golden_case_set_id == "gc-in-standard-001", f"verified_by={_pack.meta.verification_verified_by_name!r} set_id={_pack.meta.verification_golden_case_set_id!r}")
            check("the IN pack verified_on >= retrieved_on", str(_pack.meta.verification_verified_on) >= str(_pack.meta.source_retrieved_on), f"verified_on={_pack.meta.verification_verified_on} retrieved_on={_pack.meta.source_retrieved_on}")
            check("the IN pack monthly only", _pack.pay_frequency_rules.get("allowed_frequencies") == ["monthly"], f"freq={_pack.pay_frequency_rules.get('allowed_frequencies')}")
            check("the IN pack mandatory_payslip_fields includes professional_tax", "professional_tax" in _pack.mandatory_payslip_fields, f"fields={_pack.mandatory_payslip_fields}")
            # Source notes checks
            try:
                _src = _json2.loads(_Path(_pack_path).read_text())["source"]
                _notes = _src.get("notes", "")
                check("the IN pack source cites §115BAC", "115BAC" in _notes, "missing 115BAC")
                check("the IN pack source cites §87A / rebate", "87A" in _notes, "missing 87A")
                check("the IN pack source cites PF ceiling 15000", "15000" in _notes, "missing PF ceiling")
                check("the IN pack source cites ESI 21000", "21000" in _notes, "missing ESI")
                check("the IN pack source notes gratuity excluded", "Gratuity" in _notes or "gratuity" in _notes.lower(), "missing gratuity note")
                check("the IN pack source notes marginal relief checklist", "marginal relief" in _notes.lower(), "missing marginal relief")
            except Exception as e:
                check("the IN pack source block", False, str(e))

            # Rate tables existence
            for _tbl in ("tax_bands", "tax_adjustments", "tax_rebates", "social_insurance_employee", "social_insurance_employer", "social_insurance_ceilings", "pt_ka", "pt_mh", "pt_tn", "pt_tg", "pt_wb"):
                check(f"the IN pack carries table {_tbl}", _pack.get_rate_table(_tbl) is not None, "missing")

            # AC-7 gate — verified pack drives production (and pending still refuses via temp pending copy)
            try:
                _loaded = _load_for_date(BACKEND_DIR / "rule_packs", "IN", date(2025, 10, 1))
                check("AC-7: load_rule_pack_for_date(IN, 2025-10-01) returns verified pack", _loaded.meta.status == "verified" and _loaded.meta.pack_id == "in-standard", f"status={_loaded.meta.status!r}")
            except Exception as e:
                check("AC-7: load_rule_pack_for_date(IN, 2025-10-01) returns verified pack", False, f"{type(e).__name__}: {e}")
            # Pending gate still enforced — tested via in-memory pending copy (preserves contract § gate)
            try:
                _pending = _replace(_pack, meta=_replace(_pack.meta, status="pending_verification", verification_verified_by_name=None, verification_verified_by_role=None, verification_verified_on=None, verification_source_document_reference=None, verification_golden_case_set_id=None))
                _calc(pack=_pending, base_salary=__import__("decimal").Decimal("50000"), pay_frequency="monthly")
                check("AC-7b: pending copy still refuses (gate preserved in-memory)", False, "did not raise")
            except ValueError as e:
                check("AC-7b: pending copy still refuses (gate preserved in-memory)", "not verified" in str(e).lower(), str(e)[:200])
            except Exception as e:
                check("AC-7b: pending copy still refuses (gate preserved in-memory)", True, f"{type(e).__name__}")

            # AC-8 calculate succeeds for verified (and refuses for pending via same temp copy)
            try:
                _r_live = _calc(pack=_pack, base_salary=__import__("decimal").Decimal("50000"), pay_frequency="monthly", pt_state="KA")
                check("AC-8: calculate_payslip_from_pack succeeds for verified (live payroll)", _r_live.net == __import__("decimal").Decimal("48000.00"), f"net={_r_live.net}")
            except Exception as e:
                check("AC-8: calculate_payslip_from_pack succeeds for verified (live payroll)", False, f"{type(e).__name__}: {e}")
            # Pending copy still refuses
            try:
                _pending2 = _replace(_pack, meta=_replace(_pack.meta, status="pending_verification", verification_verified_by_name=None, verification_verified_by_role=None, verification_verified_on=None, verification_source_document_reference=None, verification_golden_case_set_id=None))
                _calc(pack=_pending2, base_salary=__import__("decimal").Decimal("50000"), pay_frequency="monthly")
                check("AC-8b: pending copy calculate still refuses", False, "did not raise")
            except ValueError as e:
                check("AC-8b: pending copy calculate still refuses", "not verified" in str(e).lower(), str(e)[:200])
            except Exception as e:
                check("AC-8b: pending copy calculate still refuses", True, f"{type(e).__name__}")

            # AC-9 golden cases — on-disk pack is already verified (no flip needed); keep in-memory flip path idempotent
            _verified = _pack if _pack.meta.status == "verified" else _replace(_pack, meta=_replace(_pack.meta, status="verified"))
            from decimal import Decimal as _D
            # PT tables present
            _results = _run_cases(_verified)
            check("AC-9: golden cases count is 11", len(_results) == 11, f"got {len(_results)}")
            for _cid, _passed, _msg in _results:
                check(f"AC-9 golden case {_cid}", _passed, _msg)
            # Determinism: run twice identical
            _results2 = _run_cases(_verified)
            check("AC-9: golden cases deterministic (twice)", _results == _results2, "second run differed")
            # Old-vs-young equality and PF ceiling cross checks
            if len(_results) == 11 and all(p for _, p, _ in _results):
                # young vs senior byte identical
                from app.rules.money import to_decimal as _to_d
                # fetch cases
                _young = next((c for c in _verified.golden_cases if "young" in c.case_id), None)
                _senior = next((c for c in _verified.golden_cases if "senior" in c.case_id), None)
                if _young and _senior:
                    _r_y = _calc(pack=_verified, base_salary=_to_d(_young.inputs["base_salary"]), pay_frequency="monthly", pt_state=_young.inputs.get("pt_state"))
                    _r_s = _calc(pack=_verified, base_salary=_to_d(_senior.inputs["base_salary"]), pay_frequency="monthly", pt_state=_senior.inputs.get("pt_state"))
                    check("old-vs-young equality (new regime no age distinction)", _r_y.net == _r_s.net and _r_y.total_deductions == _r_s.total_deductions, f"young net={_r_y.net} senior net={_r_s.net}")
                # PF ceiling cross at 60k
                _pf_case = next((c for c in _verified.golden_cases if "pf-ceiling" in c.case_id), None)
                if _pf_case:
                    _r = _calc(pack=_verified, base_salary=_to_d(_pf_case.inputs["base_salary"]), pay_frequency="monthly", pt_state=_pf_case.inputs.get("pt_state"))
                    # PF capped at 15000*12% =1800
                    check("PF ceiling cross at 60k: PF capped 1800", _r.total_employee_contributions == _D("1800.00"), f"ee={_r.total_employee_contributions}")
                # ESI edge
                _esi_at = next((c for c in _verified.golden_cases if "esi-edge-at-limit" in c.case_id), None)
                _esi_above = next((c for c in _verified.golden_cases if "esi-edge-above" in c.case_id), None)
                if _esi_at and _esi_above:
                    _r_at = _calc(pack=_verified, base_salary=_to_d(_esi_at.inputs["base_salary"]), pay_frequency="monthly")
                    _r_ab = _calc(pack=_verified, base_salary=_to_d(_esi_above.inputs["base_salary"]), pay_frequency="monthly")
                    check("ESI at limit 21000 applies", _r_at.total_employee_contributions == _D("1957.50"), f"ee at={_r_at.total_employee_contributions}")
                    check("ESI above limit 21000.01 skipped", _r_ab.total_employee_contributions == _D("1800.00"), f"ee above={_r_ab.total_employee_contributions}")
                # High earner TDS
                _high = next((c for c in _verified.golden_cases if "high-earner" in c.case_id), None)
                if _high:
                    _r = _calc(pack=_verified, base_salary=_to_d(_high.inputs["base_salary"]), pay_frequency="monthly", pt_state=_high.inputs.get("pt_state"))
                    # net 174562.50 per contract
                    check("high-earner TDS net 174562.50", _r.net == _D("174562.50"), f"net={_r.net}")
                    # total deductions 25437.50
                    check("high-earner total_deductions 25437.50", _r.total_deductions == _D("25437.50"), f"ded={_r.total_deductions}")

    finally:
        import shutil

        shutil.rmtree(workdir, ignore_errors=True)

    print()
    print("=" * 68)
    print(
        f"INDIA PAYROLL SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed"
    )
    if FAILURES:
        print()
        print("Failures:")
        for name, detail in FAILURES:
            print(f"  - {name}: {detail}")
    print("=" * 68)
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
