"""Exercise the schema alignment migration against a drifted database.

Builds the schema the way the legacy deployment built it — from the
models as they were before the columns were added — and then runs the
migration over it.

Run from the backend directory:

    SECRET_KEY=... DATABASE_URL=sqlite:///./align_test.db \\
        .venv/bin/python scripts/align_probe.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

DB = "sqlite:///" + os.path.join(tempfile.mkdtemp(prefix="align_test_"), "align_test.db")
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


def head_revision() -> str:
    """The newest revision in the migrations directory.

    The test asks the repository what the head is rather than repeating a
    literal, so adding a migration does not require editing this suite.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(BACKEND_ROOT / "backend" / "alembic.ini"))
    cfg.set_main_option(
        "script_location", str(BACKEND_ROOT / "backend" / "migrations")
    )
    heads = ScriptDirectory.from_config(cfg).get_heads()
    return heads[0] if heads else ""


def columns_of(db_path: str, table: str) -> set[str]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def main() -> int:
    path = Path(DB.replace("sqlite:///", "", 1))
    if path.exists():
        path.unlink()

    # The engine is built at import time, so the variable has to point at
    # the throwaway database before the application modules are imported.
    os.environ["DATABASE_URL"] = DB
    os.environ.setdefault("SECRET_KEY", "test_secret_key_for_development_32_chars")

    from app.core.database import Base, engine
    from app.core.migrations import run_pending_migrations
    from app.core.schema_drift import schema_drift_report

    import app.models
    import importlib
    import pkgutil

    for _finder, name, is_pkg in pkgutil.iter_modules(app.models.__path__):
        if is_pkg:
            continue
        importlib.import_module(f"app.models.{name}")

    # Build the schema, then remove the columns the newer models added,
    # so the database looks like the legacy deployment.
    Base.metadata.create_all(bind=engine)

    from sqlalchemy import text

    # SQLite refuses to drop a column a foreign key refers to, so the
    # legacy shape of the table is built by hand and swapped in.
    LEGACY_PAY_RUNS = """
    CREATE TABLE pay_runs_legacy (
        id INTEGER NOT NULL,
        period_id INTEGER NOT NULL,
        status VARCHAR(20) NOT NULL,
        total_gross NUMERIC(14, 2) NOT NULL,
        total_deductions NUMERIC(14, 2) NOT NULL,
        total_net NUMERIC(14, 2) NOT NULL,
        headcount INTEGER NOT NULL,
        run_date DATETIME,
        approved_by INTEGER,
        approved_at DATETIME,
        created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(period_id) REFERENCES payroll_periods (id)
    )
    """

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE case_comments DROP COLUMN comment"))
        conn.execute(text("ALTER TABLE compensation_bands DROP COLUMN level"))
        conn.execute(text(LEGACY_PAY_RUNS))
        conn.execute(
            text(
                "INSERT INTO pay_runs_legacy SELECT id, period_id, status, "
                "total_gross, total_deductions, total_net, headcount, run_date, "
                "approved_by, approved_at, created_at FROM pay_runs"
            )
        )
        conn.execute(text("DROP TABLE pay_runs"))
        conn.execute(text("ALTER TABLE pay_runs_legacy RENAME TO pay_runs"))

    before = schema_drift_report()
    check(
        "the drifted database is reported as out of sync",
        before["in_sync"] is False,
    )
    check(
        "the drift names the missing columns",
        set(before["missing_columns"].get("pay_runs", []))
        == {
            "processed_by",
            "processed_at",
            "finalized_by",
            "finalized_at",
            "warning",
            "jurisdiction",
            "rule_pack_id",
            "currency",
            "tenant_id",
            "run_type",
            "reversal_of_run_id",
        },
        f"got {before['missing_columns'].get('pay_runs')}",
    )

    print("[probe] running the migrations...")
    state = run_pending_migrations()
    check(
        "the migrations reach the head revision",
        state.get("current_revision") == head_revision(),
        f"revision={state.get('current_revision')}",
    )

    after = schema_drift_report()
    check(
        "the database is in sync after the migration",
        after["in_sync"] is True,
        f"missing_tables={after['missing_tables']} "
        f"missing_columns={after['missing_columns']}",
    )
    check(
        "the not-null column is present",
        "comment" in columns_of(path, "case_comments"),
    )
    check(
        "the other not-null column is present",
        "level" in columns_of(path, "compensation_bands"),
    )
    check(
        "the nullable pay run columns are present",
        {"processed_by", "processed_at", "finalized_by", "finalized_at", "warning"}
        <= columns_of(path, "pay_runs"),
    )

    # The existing rows were backfilled so the not-null constraint holds.
    import sqlite3

    conn = sqlite3.connect(path)
    try:
        nulls = conn.execute(
            "SELECT COUNT(*) FROM case_comments WHERE comment IS NULL"
        ).fetchone()[0]
        band_nulls = conn.execute(
            "SELECT COUNT(*) FROM compensation_bands WHERE level IS NULL"
        ).fetchone()[0]
    finally:
        conn.close()
    check("the existing comments were backfilled", nulls == 0, f"nulls={nulls}")
    check("the existing bands were backfilled", band_nulls == 0, f"nulls={band_nulls}")

    # Running it again must not fail.
    print("[probe] running the migrations a second time...")
    state = run_pending_migrations()
    check(
        "the migrations are idempotent",
        state.get("current_revision") == head_revision(),
        f"revision={state.get('current_revision')}",
    )
    check(
        "the database is still in sync",
        schema_drift_report()["in_sync"] is True,
    )

    # The identifier the statement uses has to be the one the catalog has.
    # The model calls the column ``comment``; ``COMMENT`` is an Oracle reserved
    # word, so the column was created quoted and the catalog holds it in lower
    # case. A statement that quotes ``COMMENT`` does not find it.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "mig_0006",
        Path(__file__).resolve().parent / "migrations" / "versions" / "0006_schema_alignment.py",
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    statement = migration.backfill_statement("CASE_COMMENTS", "comment")
    check(
        "the backfill statement uses the catalog's column name",
        '"CASE_COMMENTS"' in statement and '"comment"' in statement,
        statement,
    )
    check(
        "the backfill statement does not fold the name to upper case",
        '"COMMENT"' not in statement,
        statement,
    )
    not_null = migration.not_null_statement("COMPENSATION_BANDS", "LEVEL")
    check(
        "the not-null statement uses the catalog's column name",
        '"COMPENSATION_BANDS"' in not_null and '"LEVEL"' in not_null,
        not_null,
    )

    # ------------------------------------------------------------------
    # Boolean predicates compile on Oracle
    # ------------------------------------------------------------------
    # `Column.is_(True)` renders `col IS 1` on Oracle, and Oracle requires the
    # NULL keyword after IS — ORA-00908. Every list endpoint that used the
    # idiom answered 503 in production while passing on SQLite (D-035).
    from sqlalchemy.dialects import oracle
    from sqlalchemy.orm import Session

    from app.core.booleans import is_false, is_true
    from app.models.job import Job

    dialect = oracle.dialect()
    true_sql = str(
        Session().query(Job).filter(is_true(Job.is_active)).statement.compile(
            dialect=dialect, compile_kwargs={"literal_binds": True}
        )
    )
    false_sql = str(
        Session().query(Job).filter(is_false(Job.is_active)).statement.compile(
            dialect=dialect, compile_kwargs={"literal_binds": True}
        )
    )
    check(
        "is_true renders `= 1` on Oracle, not `IS 1`",
        "jobs.is_active = 1" in true_sql and "IS 1" not in true_sql,
        true_sql,
    )
    check(
        "is_false renders `= 0` on Oracle",
        "jobs.is_active = 0" in false_sql,
        false_sql,
    )

    offenders: list[str] = []
    for source_file in (BACKEND_ROOT / "backend" / "app").rglob("*.py"):
        if source_file.name == "booleans.py":
            continue
        for number, line in enumerate(source_file.read_text().splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if ".is_(True)" in line or ".is_(False)" in line:
                offenders.append(
                    f"{source_file.relative_to(BACKEND_ROOT)}:{number}"
                )
    check(
        "no module uses .is_(True) / .is_(False) on a boolean column",
        not offenders,
        f"offenders={offenders[:5]}",
    )

    path.unlink(missing_ok=True)
    print()
    print("=" * 68)
    print(
        f"SCHEMA ALIGNMENT SUITE: {RESULTS['pass']} passed, "
        f"{RESULTS['fail']} failed"
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
