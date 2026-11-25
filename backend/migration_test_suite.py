"""Migration test suite.

Alembic is the only schema change path, so the migrations need their own
tests. The scenarios that matter are the ones that would otherwise only be
discovered in production:

1. **A fresh database** gets the inherited schema and reaches head.
2. **A legacy database** — the one shape production actually has: the tables
   exist, built by ``create_all()``, with no migration history — is adopted
   by stamping the baseline rather than by replaying it.
3. **The downgrade works**, and the schema can be brought back up afterwards.
4. **The migrations are idempotent**: running them again changes nothing.
5. **The baseline is frozen**: a table added after the baseline was adopted is
   *not* created by the baseline. It belongs to a numbered revision, and the
   test proves the boundary holds.

Run:  python migration_test_suite.py
"""
import os
import shutil
import sqlite3
import sys
import tempfile
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
# The application builds its engine at import time, so a database URL has to
# exist before anything from `app` is imported. It points at a scratch file
# that the suite never actually uses; every migration run names its own
# database explicitly.
os.environ.setdefault("DATABASE_URL", "sqlite:///./migration_suite_scratch.db")

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


def _head_revision() -> str:
    """The newest revision in the migrations directory.

    The test asks the repository what the head is rather than repeating a
    literal, so adding a migration does not require editing this suite.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))


    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    return heads[0] if heads else ""


def _run_migrations(db_path: str, target: str = "head", direction: str = "upgrade") -> None:
    """Run the migration CLI against a specific database.

    The CLI is invoked as a subprocess rather than in-process, so each run
    starts from a clean module state and the operator-facing entry point is
    what is actually exercised.

    ``direction`` matters: Alembic's ``upgrade`` only moves forward, so
    asking it to reach an ancestor revision is a no-op rather than a
    downgrade. Reverting is a separate command.
    """
    import subprocess

    backend = Path(__file__).resolve().parent
    env = dict(os.environ)
    # Both variables are set: the application reads DATABASE_URL, and the
    # migration CLI reads ALEMBIC_DATABASE_URL. Setting only one would let
    # the other win and migrate the wrong database.
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["ALEMBIC_DATABASE_URL"] = f"sqlite:///{db_path}"
    env["SECRET_KEY"] = os.environ["SECRET_KEY"]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.migrate", direction, target],
        cwd=str(backend),
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


def _tables(db_path: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def _columns(db_path: str, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def _revision(db_path: str) -> str | None:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
        return rows[0][0] if rows else None
    finally:
        conn.close()


def _build_legacy_database(db_path: str) -> None:
    """Build a database the way production was built: with ``create_all()``.

    The models are imported from the *baseline* list so the schema matches
    what the inherited deployment had, without the columns added since.
    """
    from sqlalchemy import create_engine

    from migrations.baseline_schema import FROZEN_TABLES, _load_metadata

    metadata = _load_metadata()
    engine = create_engine(f"sqlite:///{db_path}")
    metadata.create_all(
        bind=engine,
        tables=[metadata.tables[name] for name in sorted(FROZEN_TABLES)],
        checkfirst=True,
    )
    engine.dispose()


def _build_prebuilt_database(db_path: str) -> None:
    """Build a database whose forecast tables already exist.

    This is the production shape: the tables were created before Alembic
    existed, so the migration that introduces them has to adopt them
    rather than create them again. The forecast table is built without the
    ``finished_at`` column so the migration has to add it.
    """
    from sqlalchemy import create_engine, text

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE forecast_runs ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "name VARCHAR(200) NOT NULL, "
                "description TEXT, "
                "horizon_days INTEGER NOT NULL DEFAULT 30, "
                "method VARCHAR(50) NOT NULL DEFAULT 'auto', "
                "data_start_date DATETIME, "
                "data_end_date DATETIME, "
                "backtest_mape NUMERIC(6, 4), "
                "backtest_mase NUMERIC(6, 4), "
                "backtest_holdout_days INTEGER, "
                "status VARCHAR(20) NOT NULL DEFAULT 'pending', "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE forecast_results ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "forecast_run_id INTEGER NOT NULL, "
                "series_key VARCHAR(200) NOT NULL, "
                "horizon_step INTEGER NOT NULL, "
                "forecast_date DATETIME NOT NULL, "
                "predicted_value NUMERIC(14, 4) NOT NULL, "
                "lower_bound NUMERIC(14, 4), "
                "upper_bound NUMERIC(14, 4), "
                "input_hash VARCHAR(64) NOT NULL, "
                "rule_version VARCHAR(60) NOT NULL, "
                "method_used VARCHAR(50) NOT NULL, "
                "data_start_date DATETIME, "
                "data_end_date DATETIME, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE forecast_model_versions ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "version VARCHAR(60) NOT NULL, "
                "method VARCHAR(50) NOT NULL, "
                "description TEXT, "
                "parameters TEXT, "
                "is_active BOOLEAN NOT NULL DEFAULT 1, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            text(
                "INSERT INTO forecast_runs "
                "(id, name, horizon_days, method, status) "
                "VALUES (1, 'prebuilt run', 30, 'auto', 'completed')"
            )
        )
    engine.dispose()


def _row_count(db_path: str, table: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.Error:
        return -1
    finally:
        conn.close()


def _load_migration_0007():
    """The 0007 revision, loaded by path.

    The revision module starts with a digit, so it cannot be imported by
    name.
    """
    import importlib.util

    path = BACKEND_DIR / "migrations" / "versions" / "0007_import_dry_runs.py"
    spec = importlib.util.spec_from_file_location("mig_0007", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_revision(filename: str):
    """A revision module, loaded by path.

    The revision modules start with a digit, so they cannot be imported by
    name.
    """
    import importlib.util

    path = BACKEND_DIR / "migrations" / "versions" / filename
    spec = importlib.util.spec_from_file_location("mig_" + filename[:4], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _apply_revision(db_path: str, filename: str, direction: str = "upgrade") -> None:
    """Run a revision against a database, in process.

    Alembic does not run a revision that is already stamped, so the
    revision is invoked directly.
    """
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration = _load_revision(filename)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    try:
        with engine.begin() as conn:
            context = MigrationContext.configure(conn)
            with Operations.context(context):
                getattr(migration, direction)()
    finally:
        engine.dispose()


def _apply_0007(db_path: str, direction: str = "upgrade") -> None:
    """Run the 0007 revision against a database, in-process.

    Alembic does not run a revision that is already stamped, so the
    revision is invoked directly. That is the situation the release step
    is in when an earlier run of the revision failed after the table was
    created and the revision was never stamped: Oracle commits DDL
    implicitly, so the table is there and the version is not.
    """
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration = _load_migration_0007()
    engine = sa.create_engine(f"sqlite:///{db_path}")
    try:
        with engine.begin() as conn:
            context = MigrationContext.configure(conn)
            with Operations.context(context):
                getattr(migration, direction)()
    finally:
        engine.dispose()


def _index_column_lists(db_path: str, table: str) -> list[tuple[str, ...]]:
    """Every index over the table, as the list of columns it covers.

    A unique constraint is an index too, and SQLite reports it as an
    auto-index. Counting only the named indexes would miss the one that a
    unique constraint creates — which is the one that matters here,
    because a second index over the same column list is exactly what
    Oracle refuses with ORA-01408.

    The Oracle equivalent is ``user_ind_columns`` joined with
    ``user_indexes``; a unique constraint has an index behind it there
    too, under a name the database generates.
    """
    conn = sqlite3.connect(db_path)
    try:
        lists = []
        for row in conn.execute(f"PRAGMA index_list({table})"):
            name = row[1]
            columns = tuple(
                info[2] for info in conn.execute(f'PRAGMA index_info("{name}")')
            )
            lists.append(columns)
        return lists
    finally:
        conn.close()


def _index_names(db_path: str, table: str) -> set[str]:
    """The names of the indexes over a table."""
    conn = sqlite3.connect(db_path)
    try:
        return {row[1] for row in conn.execute(f'PRAGMA index_list("{table}")')}
    finally:
        conn.close()


def _duplicate_index_lists(db_path: str) -> list[str]:
    """The column lists that more than one index in the schema covers.

    SQLite allows two indexes over one column list. Oracle does not: it
    refuses the second with ORA-01408 ("such column list already indexed"),
    whatever the two indexes are called. A schema that has one is a schema
    the next migration cannot extend on Oracle — and a SQLite database is
    the only place that duplicate can be seen without a database.
    """
    conn = sqlite3.connect(db_path)
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        ]
        problems: list[str] = []
        for table in tables:
            seen: dict[tuple[str, ...], str] = {}
            for row in conn.execute(f'PRAGMA index_list("{table}")'):
                name = row[1]
                columns = tuple(
                    info[2]
                    for info in conn.execute(f'PRAGMA index_info("{name}")')
                )
                if not columns:
                    continue
                key = tuple(str(column).casefold() for column in columns)
                if key in seen:
                    problems.append(
                        f"{table}: {name} and {seen[key]} both index "
                        f"({', '.join(columns)})"
                    )
                else:
                    seen[key] = name
        return problems
    finally:
        conn.close()


def _count_indexes_over(lists, columns) -> int:
    """How many of the indexes cover exactly this column list."""
    wanted = tuple(str(name).casefold() for name in columns)
    return sum(1 for entry in lists if entry == wanted)


def _build_model_import_table(db_path: str) -> None:
    """Build the import table the way the models build it.

    The table is created from the model's own metadata, so it carries the
    constraints the models declare — the unique constraint on the token,
    the indexes, the identity — rather than a hand-written approximation
    of them. This is the shape a database built by ``create_all()`` has.
    """
    from sqlalchemy import create_engine

    from app.models.imports import ImportDryRun

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        ImportDryRun.__table__.create(bind=engine, checkfirst=True)
    finally:
        engine.dispose()


def _oracle_index_structures() -> list[tuple[str, tuple[str, ...], bool]]:
    """The index structures the import revision's DDL creates.

    The structures are built from the revision's own column list and its
    own index list, so the check tracks the migration rather than a copy
    of it. An index, a unique constraint and the primary key each occupy
    a column list in the database, and Oracle refuses a second index over
    a column list that is already indexed (ORA-01408), whatever the two
    indexes are called. No test that runs on SQLite can see that, which
    is why the deployment failed after every local test had passed.
    """
    import sqlalchemy as sa

    migration = _load_migration_0007()
    metadata = sa.MetaData()
    table = sa.Table(
        migration.TABLE,
        metadata,
        *[
            sa.Column(
                column.name,
                column.type,
                nullable=column.nullable,
                server_default=column.server_default,
                # The uniqueness of a column is part of the structure the
                # database ends up with, so it has to be carried over.
                unique=column.unique,
            )
            for column in migration.COLUMNS
        ],
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns, unique in migration.INDEXES:
        sa.Index(name, *[table.c[column] for column in columns], unique=unique)

    structures = []
    for index in table.indexes:
        structures.append(
            (
                index.name or "",
                tuple(column.name for column in index.columns),
                bool(index.unique),
            )
        )
    for constraint in table.constraints:
        if isinstance(constraint, sa.UniqueConstraint):
            structures.append(
                (
                    constraint.name or "UNIQUE",
                    tuple(column.name for column in constraint.columns),
                    True,
                )
            )
    primary_key = table.primary_key
    if primary_key is not None:
        structures.append(
            (
                primary_key.name or "PRIMARY KEY",
                tuple(column.name for column in primary_key.columns),
                True,
            )
        )
    return structures


def _duplicate_column_lists(structures) -> list[str]:
    """The column lists that more than one index structure occupies."""
    seen: dict[tuple[str, ...], str] = {}
    problems = []
    for name, columns, _unique in structures:
        key = tuple(column.casefold() for column in columns)
        if key in seen:
            problems.append(
                f"{name} and {seen[key]} both index ({', '.join(columns)})"
            )
        else:
            seen[key] = name
    return problems


def _oracle_ddl_duplicate_constraints() -> list[str]:
    """Problems the Oracle DDL of the forecasting tables would have.

    Oracle requires constraint names to be unique within a schema, so a
    table that declares the same relationship twice — once on the column
    and once as a table-level constraint — is rejected with ORA-00955.
    SQLite does not enforce that, so a migration can pass every local test
    and still fail on production.

    The tables are built from the migration's own column lists, so the
    check tracks the migration rather than a copy of it.
    """
    import re

    import sqlalchemy as sa
    from sqlalchemy.dialects import oracle
    from sqlalchemy.schema import CreateTable

    # The revision module starts with a digit, so it is loaded by path.
    import importlib.util
    from pathlib import Path

    migration_path = (
        Path(__file__).resolve().parent
        / "migrations"
        / "versions"
        / "0005_forecasting.py"
    )
    spec = importlib.util.spec_from_file_location("mig_0005", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    metadata = sa.MetaData()
    sa.Table(
        "forecast_runs",
        metadata,
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    results = sa.Table(
        "forecast_results",
        metadata,
        *migration.FORECAST_RESULTS_COLUMNS,
        *migration._forecast_results_constraints(),
    )

    ddl = str(CreateTable(results).compile(dialect=oracle.dialect()))

    problems = []
    foreign_keys = re.findall(r"FOREIGN KEY\s*\(", ddl, flags=re.IGNORECASE)
    if len(foreign_keys) > 1:
        problems.append(
            f"forecast_results declares {len(foreign_keys)} foreign keys; "
            "Oracle requires a unique constraint name per relationship"
        )
    return problems


class _StubOracleBind:
    """A stand-in for an Oracle connection.

    The catalog reader is the one part of the fix that SQLite cannot
    exercise: SQLite has no mixed-case catalog, no ``ALL_TAB_COLUMNS`` and
    no reserved words. This stub answers the two catalog queries the way
    Oracle would, so the reader itself is tested rather than assumed.

    The catalog it reports is deliberately mixed — the table is upper case
    and the column is lower case and quoted — because that is the shape
    the production database actually has.
    """

    def __init__(self, tables, columns):
        from types import SimpleNamespace

        self.dialect = SimpleNamespace(name="oracle")
        self._tables = list(tables)
        self._columns = list(columns)

    def exec_driver_sql(self, statement):
        if "all_tables" in statement:
            return [(name,) for name in self._tables]
        if "all_tab_columns" in statement:
            return [
                (table, column, nullable)
                for table, column, nullable in self._columns
            ]
        raise AssertionError(f"unexpected catalog query: {statement}")


def _check_shared_helpers(workdir: str) -> None:
    """The shared migration helpers: what they promise and what they refuse.

    These are the checks that cover the part of the fix SQLite cannot see:
    the catalog reader and the nullability check. The Oracle round trip
    (``ci/oracle_migration_roundtrip.py``) is what proves them against a
    real Oracle database; these prove the logic is right in between.
    """
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from app.core.migrations import (
        catalog_names,
        create_index_if_missing,
        drop_index_if_present,
    )

    # --- the catalog reader, against a database with a mixed catalog ---
    mixed = os.path.join(workdir, "mixed_catalog.db")
    engine = sa.create_engine(f"sqlite:///{mixed}")
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    'CREATE TABLE "CASE_COMMENTS" ('
                    '"ID" INTEGER PRIMARY KEY, "comment" TEXT NOT NULL)'
                )
            )
        with engine.connect() as conn:
            catalog = catalog_names(conn)
        check(
            "the catalog reader reports the table name the catalog holds",
            catalog.table("case_comments") == "CASE_COMMENTS",
            f"got={catalog.table('case_comments')!r}",
        )
        check(
            "the catalog reader reports the column name the catalog holds",
            catalog.column("CASE_COMMENTS", "comment") == "comment",
            f"got={catalog.column('CASE_COMMENTS', 'comment')!r}",
        )
        check(
            "the catalog reader finds a column whatever its case",
            catalog.column("case_comments", "COMMENT") == "comment",
            f"got={catalog.column('case_comments', 'COMMENT')!r}",
        )
        check(
            "the catalog reader reports a not-null column as not null",
            catalog.is_not_null("CASE_COMMENTS", "comment"),
            "the not-null column was not reported",
        )
        check(
            "the catalog reader does not report a nullable column as not null",
            not catalog.is_not_null("CASE_COMMENTS", "ID"),
            "a nullable column was reported as not null",
        )
    finally:
        engine.dispose()

    # --- the catalog reader, against the Oracle catalog views -----------
    stub = _StubOracleBind(
        tables=["CASE_COMMENTS"],
        columns=[
            ("CASE_COMMENTS", "ID", "Y"),
            ("CASE_COMMENTS", "comment", "N"),
        ],
    )
    catalog = catalog_names(stub)
    check(
        "the Oracle catalog reader reports the table name verbatim",
        catalog.table("case_comments") == "CASE_COMMENTS",
        f"got={catalog.table('case_comments')!r}",
    )
    check(
        "the Oracle catalog reader reports a lower-case quoted column verbatim",
        catalog.column("CASE_COMMENTS", "comment") == "comment",
        f"got={catalog.column('CASE_COMMENTS', 'comment')!r}",
    )
    check(
        "the Oracle catalog reader reports the nullability",
        catalog.is_not_null("CASE_COMMENTS", "comment")
        and not catalog.is_not_null("CASE_COMMENTS", "ID"),
        "the nullability was not read from the catalog",
    )

    # --- an index over a column list that is already indexed -----------
    indexed = os.path.join(workdir, "indexed.db")
    engine = sa.create_engine(f"sqlite:///{indexed}")
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text("CREATE TABLE things (id INTEGER PRIMARY KEY, name TEXT)")
            )
            conn.execute(
                sa.text("CREATE INDEX ix_things_name ON things (name)")
            )

        with engine.begin() as conn:
            context = MigrationContext.configure(conn)
            with Operations.context(context):
                created = create_index_if_missing(
                    "ix_things_name_again", "things", ["name"]
                )
        check(
            "an index over an already-indexed column list is skipped",
            created is False,
            f"created={created}",
        )
        check(
            "the skipped index left the schema alone",
            _index_names(indexed, "things") == {"ix_things_name"},
            f"indexes={sorted(_index_names(indexed, 'things'))}",
        )

        with engine.begin() as conn:
            context = MigrationContext.configure(conn)
            with Operations.context(context):
                missing = drop_index_if_present("ix_things_name_again", "things")
                dropped = drop_index_if_present("ix_things_name", "things")
        check(
            "dropping an index that is not there is a no-op",
            missing is False,
            f"dropped={missing}",
        )
        check(
            "dropping an index that is there drops it",
            dropped is True,
            f"dropped={dropped}",
        )
        check(
            "the index was really dropped",
            _index_names(indexed, "things") == set(),
            f"indexes={sorted(_index_names(indexed, 'things'))}",
        )
    finally:
        engine.dispose()

    # --- the nullability check the alignment revision uses -------------
    migration = _load_revision("0006_schema_alignment.py")
    nullable = os.path.join(workdir, "nullability.db")
    engine = sa.create_engine(f"sqlite:///{nullable}")
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    'CREATE TABLE "bands" ('
                    '"ID" INTEGER PRIMARY KEY, "level" TEXT, '
                    '"NAME" TEXT NOT NULL)'
                )
            )
        with engine.connect() as conn:
            catalog = catalog_names(conn)
        needs_not_null = getattr(migration, "needs_not_null", None)
        check(
            "the alignment revision asks the catalog whether the column is not null",
            callable(needs_not_null),
            "the revision does not read the nullability from the catalog",
        )
        if callable(needs_not_null):
            check(
                "a column the catalog reports as nullable still needs the constraint",
                needs_not_null(catalog, "bands", "level"),
                "the nullable column was reported as already not null",
            )
            check(
                "a column the catalog reports as not null does not need the constraint",
                not needs_not_null(catalog, "bands", "NAME"),
                "the not-null column was reported as needing the constraint",
            )
    finally:
        engine.dispose()

    # --- the statement the alignment revision builds --------------------
    # The names in the statement are the ones the catalog holds, spelled
    # exactly. A statement that quotes the model's lower-case name does not
    # find a column the catalog holds as ``comment``.
    statement = migration.backfill_statement("CASE_COMMENTS", "comment")
    check(
        "the backfill statement quotes the catalog's names exactly",
        statement
        == 'UPDATE "CASE_COMMENTS" SET "comment" = :value WHERE "comment" IS NULL',
        statement,
    )


def _scan_models_for_duplicate_indexes() -> list[str]:
    """Scan all model classes for duplicate index declarations.

    Returns a list of problem descriptions. A duplicate is when a column has
    index=True and the same column list is ALSO covered by an EXPLICIT
    table-level Index declared in __table_args__. Auto-generated indexes
    from unique=True or index=True on columns are not considered duplicates
    of themselves.
    """
    from sqlalchemy import Index

    from app.models.base import Base

    # Import all model modules to register the models with Base.metadata
    import app.models.user
    import app.models.employee
    import app.models.department
    import app.models.job
    import app.models.core_hr
    import app.models.leave
    import app.models.time_attendance
    import app.models.benefits
    import app.models.payroll
    import app.models.performance
    import app.models.learning
    import app.models.recruiting
    import app.models.onboarding
    import app.models.client_onboarding
    import app.models.compliance
    import app.models.offboarding
    import app.models.ess_hr
    import app.models.scheduling
    import app.models.forecasting
    import app.models.job_queue
    import app.models.refresh_token
    import app.models.audit
    import app.models.imports
    import app.models.integrations_platform

    problems = []

    # Iterate over model classes to find explicit Index declarations in __table_args__
    for cls in Base.__subclasses__():
        if not hasattr(cls, '__table_args__'):
            continue
        table_args = cls.__table_args__
        if not isinstance(table_args, tuple):
            continue
        
        explicit_indexes = []
        for arg in table_args:
            if isinstance(arg, Index):
                columns = tuple(col.name for col in arg.columns)
                explicit_indexes.append((arg.name, columns))
        
        if not explicit_indexes:
            continue
        
        # Now check columns with index=True that match these explicit indexes
        table = cls.__table__
        for index_name, columns in explicit_indexes:
            # Only flag if it's a single-column explicit index and that column has index=True
            if len(columns) == 1:
                col_name = columns[0]
                column = table.columns.get(col_name)
                if column is not None:
                    # column.index can be a ClauseElement or True/False
                    # Check if it's truthy in a SQLAlchemy-safe way
                    idx_val = column.index
                    has_index = idx_val is True or (hasattr(idx_val, '__bool__') and idx_val)
                    if has_index:
                        problems.append(
                            f"{table.name}: explicit Index '{index_name}' on ({col_name}) duplicates column.index=True"
                        )

    return problems


def main() -> int:
    print("=" * 68)
    print("MIGRATION SUITE")
    print("=" * 68)

    workdir = tempfile.mkdtemp(prefix="karmathy-migrations-")
    try:
        # ---------------------------------------------------------- fresh ---
        fresh = os.path.join(workdir, "fresh.db")
        _run_migrations(fresh)
        tables = _tables(fresh)

        check(
            "a fresh database reaches the head revision",
            _revision(fresh) == _head_revision(),
            f"revision={_revision(fresh)}",
        )
        check(
            "the inherited tables were created",
            {"users", "employees", "pay_runs", "leave_requests"} <= tables,
            f"missing={[t for t in ('users', 'employees', 'pay_runs', 'leave_requests') if t not in tables]}",
        )
        check(
            "the credential lifecycle table was created",
            "refresh_tokens" in tables,
            "refresh_tokens missing",
        )
        check(
            "the forecasting tables were created",
            {
                "forecast_runs",
                "forecast_results",
                "forecast_model_versions",
            }
            <= tables,
            f"missing={[t for t in ('forecast_runs', 'forecast_results', 'forecast_model_versions') if t not in tables]}",
        )
        check(
            "the forecast result rows carry their traceability columns",
            {
                "input_hash",
                "rule_version",
                "method_used",
                "lower_bound",
                "upper_bound",
            }
            <= _columns(fresh, "forecast_results"),
            f"columns={sorted(_columns(fresh, 'forecast_results'))}",
        )
        check(
            "the users credential columns were created",
            {
                "must_change_password",
                "password_changed_at",
                "failed_login_count",
                "locked_until",
                "password_history",
            }
            <= _columns(fresh, "users"),
            f"columns={sorted(_columns(fresh, 'users'))}",
        )

        # ------------------------------------------------- idempotency ---
        before = _tables(fresh)
        _run_migrations(fresh)
        check(
            "re-running the migrations changes nothing",
            _tables(fresh) == before and _revision(fresh) == _head_revision(),
            "the second run altered the schema",
        )

        # ------------------------------------- the schema-drift revision ---
        # 0029 adds the columns and tables the B1 models gained. On a fresh
        # database the baseline already created the columns (it builds the
        # frozen tables from the current models), so the tables are the
        # observable delta; the downgrade and re-upgrade prove both halves.
        check(
            "the schema-drift revision created its tables",
            {"break_glass_grants", "roster_versions"} <= tables,
            f"missing={[t for t in ('break_glass_grants', 'roster_versions') if t not in tables]}",
        )
        _run_migrations(fresh, "0028_tenant_discriminator", "downgrade")
        check(
            "its downgrade removes the tables and columns",
            not ({"break_glass_grants", "roster_versions"} & _tables(fresh))
            and "tenant_id" not in _columns(fresh, "audit_logs")
            and "archived_at" not in _columns(fresh, "clients")
            and "balance_applied" not in _columns(fresh, "leave_requests"),
            "the downgrade left the drift-fix objects behind",
        )
        _run_migrations(fresh)
        check(
            "its upgrade restores the tables and columns",
            {"break_glass_grants", "roster_versions"} <= _tables(fresh)
            and {"tenant_id", "break_glass_grant_id"} <= _columns(fresh, "audit_logs")
            and {
                "currency",
                "date_format",
                "working_week",
                "deprovisioned_at",
                "archived_at",
            }
            <= _columns(fresh, "clients")
            and "balance_applied" in _columns(fresh, "leave_requests"),
            "the upgrade did not restore the drift-fix objects",
        )

        # -------------------------------------------- the column lists ---
        # SQLite allows two indexes over one column list; Oracle refuses
        # the second with ORA-01408. The job queue revision declares
        # ``lease_expires_at`` with ``index=True`` and then creates a second
        # index over the same column list, which is how the chain came to
        # stop at 0004 on a fresh Oracle database.
        duplicates = _duplicate_index_lists(fresh)
        check(
            "no two indexes cover the same column list",
            not duplicates,
            "; ".join(duplicates),
        )
        job_queue_indexes = _index_names(fresh, "job_queue")
        check(
            "the job queue revision skips the index the column already has",
            "ix_job_queue_lease_expires" not in job_queue_indexes,
            f"indexes={sorted(job_queue_indexes)}",
        )
        check(
            "the job queue revision keeps the index the column declares",
            "ix_job_queue_lease_expires_at" in job_queue_indexes,
            f"indexes={sorted(job_queue_indexes)}",
        )
        check(
            "the job queue revision keeps its composite index",
            "ix_job_queue_state_type" in job_queue_indexes,
            f"indexes={sorted(job_queue_indexes)}",
        )

        # The downgrade of the job queue revision drops only what the
        # upgrade created. An index the upgrade skipped is not there to be
        # dropped, and dropping it anyway fails with ORA-01418.
        try:
            _run_migrations(fresh, "0003_mfa", "downgrade")
            downgraded = True
            detail = ""
        except Exception as exc:  # noqa: BLE001
            downgraded = False
            detail = f"{type(exc).__name__}: {exc}"
        check(
            "the job queue revision downgrades when the upgrade skipped an index",
            downgraded,
            detail,
        )
        _run_migrations(fresh)
        check(
            "the schema comes back up after that downgrade",
            _revision(fresh) == _head_revision(),
            f"revision={_revision(fresh)}",
        )

        # ---------------------------------------------------- downgrade ---
        _run_migrations(fresh, "0001_baseline", "downgrade")
        check(
            "downgrading removes the credential columns",
            "must_change_password" not in _columns(fresh, "users"),
            f"columns={sorted(_columns(fresh, 'users'))}",
        )
        check(
            "downgrading removes the refresh token table",
            "refresh_tokens" not in _tables(fresh),
            "refresh_tokens still present",
        )
        check(
            "downgrading keeps the inherited schema",
            {"users", "employees"} <= _tables(fresh),
            "the inherited tables were dropped",
        )

        _run_migrations(fresh)
        check(
            "the schema can be brought back up to head",
            _revision(fresh) == _head_revision()
            and "must_change_password" in _columns(fresh, "users"),
            f"revision={_revision(fresh)}",
        )

        # -------------------------------------------- downgrade to base ---
        _run_migrations(fresh, "base", "downgrade")
        remaining = _tables(fresh) - {"alembic_version"}
        check(
            "downgrading to base drops the inherited schema",
            remaining == set(),
            f"remaining={sorted(remaining)}",
        )
        _run_migrations(fresh)
        check(
            "the schema can be rebuilt from base",
            _revision(fresh) == _head_revision(),
            f"revision={_revision(fresh)}",
        )

        # ------------------------------------------------------- legacy ---
        legacy = os.path.join(workdir, "legacy.db")
        _build_legacy_database(legacy)
        legacy_tables = _tables(legacy)
        check(
            "the legacy database starts with the inherited schema and no history",
            "users" in legacy_tables and "alembic_version" not in legacy_tables,
            f"tables={len(legacy_tables)}",
        )

        _run_migrations(legacy)
        check(
            "the legacy database reaches the head revision",
            _revision(legacy) == _head_revision(),
            f"revision={_revision(legacy)}",
        )
        check(
            "the legacy database gained the credential columns",
            "must_change_password" in _columns(legacy, "users"),
            f"columns={sorted(_columns(legacy, 'users'))}",
        )
        check(
            "the legacy database gained the refresh token table",
            "refresh_tokens" in _tables(legacy),
            "refresh_tokens missing",
        )
        check(
            "the legacy database kept its data",
            _tables(legacy) >= legacy_tables,
            "tables were lost",
        )

        # ------------------------------------------- a table already there ---
        # A database whose forecast tables were built by create_all() before
        # Alembic existed. Creating them again raises ORA-00955 on Oracle, so
        # the migration must adopt them instead of recreating them.
        prebuilt = os.path.join(workdir, "prebuilt.db")
        _build_prebuilt_database(prebuilt)
        prebuilt_tables = _tables(prebuilt)
        check(
            "the prebuilt database starts with the forecast tables already in place",
            {
                "forecast_runs",
                "forecast_results",
                "forecast_model_versions",
            }
            <= prebuilt_tables,
            f"tables={sorted(t for t in prebuilt_tables if 'forecast' in t)}",
        )

        try:
            _run_migrations(prebuilt)
            adopted = True
            detail = ""
        except Exception as exc:  # noqa: BLE001
            adopted = False
            detail = f"{type(exc).__name__}: {exc}"

        check(
            "the migration adopts forecast tables that already exist",
            adopted,
            detail,
        )
        check(
            "the adopted database reaches the head revision",
            _revision(prebuilt) == _head_revision(),
            f"revision={_revision(prebuilt)}",
        )
        check(
            "the adopted forecast tables keep their rows",
            _row_count(prebuilt, "forecast_runs") == 1,
            f"rows={_row_count(prebuilt, 'forecast_runs')}",
        )
        check(
            "the adopted forecast tables gain the columns the models need",
            "finished_at" in _columns(prebuilt, "forecast_runs"),
            f"columns={sorted(_columns(prebuilt, 'forecast_runs'))}",
        )

        # ------------------------------------------------ the import table ---
        # The revision that creates the import table failed on Oracle with
        # ORA-01408 ("such column list already indexed"): it created the
        # table with the token column already unique and then created a
        # second unique index over the same column list. Oracle commits DDL
        # implicitly, so the failed run left the table behind and the
        # revision was never stamped, so the next run has to cope with a
        # table that is already there.
        #
        # Two states are exercised: a table the revision creates, and a
        # table it adopts.
        created = os.path.join(workdir, "import_created.db")
        _apply_0007(created)
        check(
            "the import migration creates its table",
            "import_dry_runs" in _tables(created),
            f"tables={sorted(_tables(created))}",
        )
        created_indexes = _index_column_lists(created, "import_dry_runs")
        check(
            "the token column of a created table has exactly one index",
            _count_indexes_over(created_indexes, ("token",)) == 1,
            f"indexes over token="
            f"{_count_indexes_over(created_indexes, ('token',))}",
        )

        try:
            _apply_0007(created)
            applied_twice = True
            detail = ""
        except Exception as exc:  # noqa: BLE001
            applied_twice = False
            detail = f"{type(exc).__name__}: {exc}"
        check(
            "applying the import migration twice succeeds",
            applied_twice,
            detail,
        )
        check(
            "applying the import migration twice changes nothing",
            _index_column_lists(created, "import_dry_runs") == created_indexes,
            "the second run altered the indexes",
        )

        _apply_0007(created, "downgrade")
        check(
            "the downgrade removes the table the revision created",
            "import_dry_runs" not in _tables(created),
            f"tables={sorted(_tables(created))}",
        )
        check(
            "the downgrade removes the indexes the revision created",
            _index_column_lists(created, "import_dry_runs") == [],
            f"indexes={_index_column_lists(created, 'import_dry_runs')}",
        )

        # The adopted table: built by create_all() from the models, with
        # the models' constraints. It already has an index over every
        # column list the revision wants to index, so the revision must
        # not add a second one — that is the error that failed the
        # deployment.
        adopted = os.path.join(workdir, "import_adopted.db")
        _build_model_import_table(adopted)
        adopted_indexes = _index_column_lists(adopted, "import_dry_runs")
        check(
            "the adopted table starts with the model's own indexes",
            _count_indexes_over(adopted_indexes, ("token",)) == 1,
            f"indexes over token="
            f"{_count_indexes_over(adopted_indexes, ('token',))}",
        )
        try:
            _apply_0007(adopted)
            adopted_ok = True
            detail = ""
        except Exception as exc:  # noqa: BLE001
            adopted_ok = False
            detail = f"{type(exc).__name__}: {exc}"
        check(
            "the import migration adopts a table that already exists",
            adopted_ok,
            detail,
        )
        check(
            "the adopted table keeps every column the models declare",
            {
                "token",
                "entity",
                "file_hash",
                "result_hash",
                "storage_key",
                "expires_at",
                "upload_expires_at",
            }
            <= _columns(adopted, "import_dry_runs"),
            f"columns={sorted(_columns(adopted, 'import_dry_runs'))}",
        )
        check(
            "the adopted table is not given a second index over the token",
            _count_indexes_over(
                _index_column_lists(adopted, "import_dry_runs"), ("token",)
            )
            == 1,
            "the token column is indexed more than once",
        )
        check(
            "adopting the table leaves the model's indexes alone",
            _index_column_lists(adopted, "import_dry_runs") == adopted_indexes,
            "the model's indexes were changed",
        )

        _apply_0007(adopted, "downgrade")
        check(
            "the downgrade leaves an adopted table alone",
            "import_dry_runs" in _tables(adopted),
            f"tables={sorted(_tables(adopted))}",
        )
        check(
            "the downgrade leaves the model's indexes alone",
            _index_column_lists(adopted, "import_dry_runs") == adopted_indexes,
            "the model's indexes were changed",
        )

        # The same defect, seen the way Oracle sees it: two index
        # structures over one column list. This check is compiled for the
        # Oracle dialect because a SQLite database accepts it.
        duplicate_lists = _duplicate_column_lists(_oracle_index_structures())
        check(
            "the import migration declares no two indexes over one column list",
            not duplicate_lists,
            "; ".join(duplicate_lists),
        )

        # ------------------------------------------ the Oracle DDL itself ---
        # SQLite accepts two constraints with the same name; Oracle does
        # not. The DDL is compiled for Oracle and checked here, because a
        # migration that only fails on production is not caught by any
        # local test that runs on SQLite.
        ddl_problems = _oracle_ddl_duplicate_constraints()
        check(
            "the forecasting tables declare no duplicate constraint for Oracle",
            not ddl_problems,
            "; ".join(ddl_problems),
        )

        # ------------------------------------------- the shared helpers ---
        _check_shared_helpers(workdir)

        # -------------------------------------------- the baseline is frozen ---
        from migrations.baseline_schema import FROZEN_TABLES

        check(
            "the frozen baseline list does not include later tables",
            "refresh_tokens" not in FROZEN_TABLES,
            "refresh_tokens leaked into the frozen baseline list",
        )
        check(
            "the frozen baseline list covers the inherited schema",
            {"users", "employees", "pay_runs", "leave_requests"} <= FROZEN_TABLES,
            "the frozen list is missing core tables",
        )

        # ------------------------------------------ static model index scan ---
        # Scan all models for duplicate indexes: a column with index=True that
        # is also covered by a table-level Index with the same column list.
        # This is the pattern that caused ORA-01408 on job_queue.
        model_duplicates = _scan_models_for_duplicate_indexes()
        check(
            "no model declares the same column list as both index=True and a table-level Index",
            not model_duplicates,
            "; ".join(model_duplicates),
        )

    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print()
    print("=" * 68)
    print(f"MIGRATION SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
    if FAILURES:
        print()
        print("Failures:")
        for name, detail in FAILURES:
            print(f"  - {name}: {detail}")
    print("=" * 68)
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
