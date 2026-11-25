"""Applying database migrations from inside the application.

Why this exists
---------------
Alembic is the only schema change path. Historically the application called
``create_all()`` at startup, which cannot alter an existing table and silently
drifted from the models. That has been replaced by real migrations.

This module owns the part of that job that is specific to this platform: the
production database was created by ``create_all()`` and therefore has no
migration history. Running the baseline against it would fail, because the
tables already exist. So the runner *stamps* the baseline on a legacy
database and then applies the newer, additive migrations.

The state of the last run is kept in :data:`MIGRATION_STATE` so that
``/health/db`` can report a schema that is behind the code instead of
letting it fail later in a confusing way.

The shared migration helpers
----------------------------
A migration that runs against Oracle has three ways to fail that no SQLite
test can see, because SQLite allows two indexes over one column list, folds
every identifier the same way, and has no reserved words:

* **Oracle refuses a second index over a column list the schema already
  indexes** (``ORA-01408``). An index, a unique constraint and the primary
  key each occupy a column list, so a migration has to know about all three
  of them before it creates one.
* **SQLAlchemy's Oracle reflection lower-cases every identifier.** The
  catalog is mixed — a table can be ``CASE_COMMENTS`` while a column added
  by an earlier migration is ``comment``, in lower case and quoted — so a
  statement built from a reflected name names an object that does not exist
  (``ORA-00942``, ``ORA-00904``).
* **A column that is already ``NOT NULL`` cannot be constrained again**
  (``ORA-01442``).

The helpers below answer all three, and they live here so that a lane can
use them without reaching into a private module:

* :func:`catalog_names` — the names the catalog actually holds, read from
  ``ALL_TABLES`` and ``ALL_TAB_COLUMNS`` on Oracle;
* :func:`indexed_column_lists`, :func:`uniquely_indexed_column_lists` and
  :func:`create_index_if_missing` — an index creator that knows about
  column lists and reports whether it created anything;
* :func:`drop_index_if_present` — the way back, for a downgrade that must
  drop only what the upgrade created; and
* :func:`CatalogNames.is_not_null` — the nullability check, read from
  ``ALL_TAB_COLUMNS.NULLABLE``.

This module builds no engine at import time, so a revision can import it
without a database being configured.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy import inspect

from app.core.observability import get_logger

log = get_logger("karmathy.migrations")

#: The revision representing the inherited, pre-Alembic schema.
BASELINE_REVISION = "0001_baseline"

#: A table that exists in the inherited schema. Its presence means the
#: database predates Alembic.
LEGACY_MARKER_TABLE = "users"

#: Status of the most recent migration run, surfaced by ``/health/db``.
MIGRATION_STATE: dict[str, Any] = {
    "status": "not_run",
    "current_revision": None,
    "head_revision": None,
    "legacy_schema_adopted": False,
    "last_error": None,
    "last_run_at": None,
}

_lock = threading.Lock()


def _backend_dir() -> Path:
    # app/core/migrations.py -> app/core -> app -> backend
    return Path(__file__).resolve().parent.parent.parent


def _engine():
    """The application's engine.

    Imported lazily. ``app.core.database`` builds its engine at import time
    and refuses to start without a configured database, and this module is
    imported by the migration revisions — which are themselves imported when
    the revision chain is *read*, long before anything connects. Reading the
    chain must not need a database.
    """
    from app.core.database import engine

    return engine


def _alembic_config():
    from alembic.config import Config

    cfg = Config(str(_backend_dir() / "alembic.ini"))
    cfg.set_main_option("script_location", str(_backend_dir() / "migrations"))
    return cfg


def _is_legacy_schema(inspector) -> bool:
    """True when the database holds the inherited schema but no history."""
    tables = set(inspector.get_table_names())
    if "alembic_version" in tables:
        return False
    return LEGACY_MARKER_TABLE in tables


def current_revision() -> str | None:
    """The revision the database is currently stamped at."""
    from sqlalchemy import text

    try:
        with _engine().connect() as conn:
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
            return rows[0][0] if rows else None
    except Exception:  # noqa: BLE001
        return None


def database_revision() -> str | None:
    """The revision the database is actually stamped at.

    Read from the database rather than from :data:`MIGRATION_STATE`, because
    the in-process state is only populated when *this* process ran the
    migration. In the container the migration is a release step that runs
    before the server starts, so the state would otherwise report "not run"
    for a database that is perfectly up to date.
    """
    from sqlalchemy import text

    try:
        with _engine().connect() as conn:
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
            return rows[0][0] if rows else None
    except Exception:  # noqa: BLE001
        return None


def head_revision() -> str | None:
    """The newest revision the codebase knows about."""
    try:
        from alembic import script as alembic_script

        heads = alembic_script.ScriptDirectory.from_config(_alembic_config()).get_heads()
        return heads[0] if heads else None
    except Exception:  # noqa: BLE001
        return None


def run_pending_migrations(target: str = "head") -> dict[str, Any]:
    """Bring the database up to ``target``.

    Handles three starting points:

    * **fresh database** — no tables, no history. The baseline creates the
      inherited schema and the newer migrations run on top.
    * **legacy database** — the inherited tables exist but there is no
      migration history. The baseline is stamped rather than replayed, then
      the newer migrations run.
    * **current database** — already under Alembic. The newer migrations run.

    Returns the updated :data:`MIGRATION_STATE`.
    """
    from datetime import datetime, timezone

    from alembic import command

    engine = _engine()

    with _lock:
        state = MIGRATION_STATE
        state["last_run_at"] = datetime.now(timezone.utc).isoformat()
        try:
            cfg = _alembic_config()

            with engine.connect() as conn:
                inspector = inspect(conn)
                legacy = _is_legacy_schema(inspector)
                has_history = "alembic_version" in set(inspector.get_table_names())

            if legacy and not has_history:
                log.warning(
                    "legacy schema detected; stamping the baseline instead of "
                    "replaying it. The inherited tables are already present.",
                    baseline_revision=BASELINE_REVISION,
                )
                with engine.begin() as conn:
                    command.stamp(cfg, BASELINE_REVISION)
                state["legacy_schema_adopted"] = True

                # Stamping records the baseline as applied, so the baseline
                # migration never runs and never creates the frozen tables
                # it would have created. Most of them are already there,
                # but one is not a model table and was added after the
                # deployment was built, so it can be missing. Creating the
                # frozen tables that are absent completes the schema
                # without touching the ones that are there.
                with engine.begin() as conn:
                    from migrations.baseline_schema import create_frozen_schema

                    create_frozen_schema(conn)

            command.upgrade(cfg, target)

            state["status"] = "ok"
            state["current_revision"] = current_revision()
            state["head_revision"] = head_revision()
            state["last_error"] = None
            log.info(
                "migrations applied",
                current_revision=state["current_revision"],
                head_revision=state["head_revision"],
            )
        except Exception as exc:  # noqa: BLE001
            state["status"] = "failed"
            state["last_error"] = f"{type(exc).__name__}: {exc}"
            state["current_revision"] = current_revision()
            state["head_revision"] = head_revision()
            log.error("migration run failed", error=state["last_error"])
            raise

        return dict(state)


# ---------------------------------------------------------------------------
# The shared migration helpers
# ---------------------------------------------------------------------------
#
# Everything above this line is the migration *runner*. Everything below it
# is the vocabulary the migration *revisions* share, so that a revision in
# any lane can ask the database what is really there instead of guessing.


@dataclass(frozen=True)
class CatalogNames:
    """The names the catalog holds for a schema's tables and columns.

    The keys are folded to upper case, so a lookup is a question about
    *which* object and not about how it is spelled. The values are the names
    exactly as the catalog holds them, so a statement built from them names
    the object that is really there.

    On Oracle the catalog is mixed: an object created with an unquoted
    identifier is upper case, and an object created with a quoted one keeps
    the case it was given. SQLAlchemy's Oracle reflection lower-cases every
    identifier it reports, so the reflection cannot tell the two apart. The
    catalog views can.
    """

    #: The catalog's name for each table, keyed by its upper-case name.
    tables: dict[str, str]

    #: The catalog's name for each column: keyed by the upper-case table
    #: name, then by the upper-case column name.
    columns: dict[str, dict[str, str]]

    #: The (table, column) pairs the catalog reports as ``NOT NULL``.
    not_null: frozenset[tuple[str, str]]

    def table(self, name: str) -> str | None:
        """The catalog's name for a table, or None if it is absent."""
        return self.tables.get(str(name).upper())

    def column(self, table: str, name: str) -> str | None:
        """The catalog's name for a column, or None if it is absent."""
        columns = self.columns.get(str(table).upper())
        if columns is None:
            return None
        return columns.get(str(name).upper())

    def is_not_null(self, table: str, column: str) -> bool:
        """Whether the catalog reports the column as ``NOT NULL``."""
        return (str(table).upper(), str(column).upper()) in self.not_null


def _oracle_catalog_names(bind, tables: Sequence[str] | None = None) -> CatalogNames:
    """The catalog names, read from the Oracle catalog views.

    ``ALL_TABLES`` and ``ALL_TAB_COLUMNS`` are the only places the real
    names are. SQLAlchemy's Oracle reflection lower-cases every identifier
    it reports, so a column the catalog holds as ``comment`` comes back as
    ``comment`` and a table the catalog holds as ``CASE_COMMENTS`` comes
    back as ``case_comments``; a statement built from either names an
    object that does not exist.

    ``NULLABLE`` is the answer to "is this column already not null", which
    is the check that keeps a migration from constraining a column twice.
    """
    owner = "SYS_CONTEXT('USERENV','CURRENT_SCHEMA')"
    catalog_tables: dict[str, str] = {}
    catalog_columns: dict[str, dict[str, str]] = {}
    not_null: set[tuple[str, str]] = set()

    for (name,) in bind.exec_driver_sql(
        f"SELECT table_name FROM all_tables WHERE owner = {owner}"
    ):
        catalog_tables[str(name).upper()] = str(name)

    for table, column, nullable in bind.exec_driver_sql(
        f"SELECT table_name, column_name, nullable FROM all_tab_columns "
        f"WHERE owner = {owner}"
    ):
        table = str(table)
        column = str(column)
        catalog_columns.setdefault(table.upper(), {})[column.upper()] = column
        if str(nullable).upper() == "N":
            not_null.add((table.upper(), column.upper()))

    return CatalogNames(catalog_tables, catalog_columns, frozenset(not_null))


def _reflected_catalog_names(
    bind, tables: Sequence[str] | None = None
) -> CatalogNames:
    """The catalog names, read through the inspector.

    Every dialect other than Oracle reports the names exactly as they were
    created, so there the reflection *is* the catalog.
    """
    inspector = inspect(bind)
    catalog_tables: dict[str, str] = {}
    catalog_columns: dict[str, dict[str, str]] = {}
    not_null: set[tuple[str, str]] = set()

    for name in inspector.get_table_names():
        catalog_tables[str(name).upper()] = str(name)

    wanted = (
        list(catalog_tables.values())
        if tables is None
        else [
            catalog_tables[str(name).upper()]
            for name in tables
            if str(name).upper() in catalog_tables
        ]
    )
    for name in wanted:
        upper = name.upper()
        for column in inspector.get_columns(name):
            exact = str(column["name"])
            catalog_columns.setdefault(upper, {})[exact.upper()] = exact
            if not column.get("nullable", True):
                not_null.add((upper, exact.upper()))

    return CatalogNames(catalog_tables, catalog_columns, frozenset(not_null))


def catalog_names(bind, tables: Sequence[str] | None = None) -> CatalogNames:
    """The names the catalog holds for the schema ``bind`` is connected to.

    ``tables`` narrows the column read to the tables a caller cares about.
    On Oracle the whole catalog is read in two queries either way; on the
    other dialects the narrowing saves a reflection call per table.
    """
    if bind.dialect.name == "oracle":
        return _oracle_catalog_names(bind, tables)
    return _reflected_catalog_names(bind, tables)


def indexed_column_lists(inspector, table: str) -> set[tuple[str, ...]]:
    """Every column list the live table already has an index over.

    An index, a unique constraint and the primary key each occupy a column
    list in the database. Oracle refuses a second index over a column list
    that is already indexed (``ORA-01408``), whatever the two indexes are
    called, so a migration has to know about all three of them before it
    creates one.

    The column names are folded, because the same column can be spelled
    ``COMMENT`` by one migration and ``comment`` by another.
    """
    lists: set[tuple[str, ...]] = set()

    def remember(columns) -> None:
        key = tuple(str(name).casefold() for name in columns or [])
        if key:
            lists.add(key)

    for index in inspector.get_indexes(table):
        remember(index.get("column_names"))
    for constraint in inspector.get_unique_constraints(table):
        remember(constraint.get("column_names"))
    primary_key = inspector.get_pk_constraint(table) or {}
    remember(primary_key.get("constrained_columns"))
    return lists


def uniquely_indexed_column_lists(inspector, table: str) -> set[tuple[str, ...]]:
    """The column lists a unique structure already indexes.

    A unique constraint and a unique index both refuse a duplicate value,
    so a column list in here is already unique and needs no unique index.
    """
    lists: set[tuple[str, ...]] = set()

    def remember(columns) -> None:
        key = tuple(str(name).casefold() for name in columns or [])
        if key:
            lists.add(key)

    for index in inspector.get_indexes(table):
        if index.get("unique"):
            remember(index.get("column_names"))
    for constraint in inspector.get_unique_constraints(table):
        remember(constraint.get("column_names"))
    return lists


def create_index_if_missing(
    name: str,
    table: str,
    columns: Sequence[str],
    unique: bool = False,
) -> bool:
    """Create an index, unless the column list is already indexed.

    Returns ``True`` when the index was created and ``False`` when it was
    skipped. The caller uses the return value to know what its downgrade
    has to drop: an index that was never created cannot be dropped, and
    dropping it anyway fails with ``ORA-01418``.

    The table is named as the catalog holds it, so the index lands on the
    table that is really there.
    """
    from alembic import op

    bind = op.get_bind()
    inspector = inspect(bind)
    catalog = catalog_names(bind, tables=[table])
    live = catalog.table(table) or table
    key = tuple(str(column).casefold() for column in columns)

    if key in indexed_column_lists(inspector, live):
        log.info(
            "index skipped: the column list is already indexed",
            index=name,
            table=live,
            columns=list(columns),
        )
        return False

    op.create_index(name, live, list(columns), unique=unique)
    log.info("index created", index=name, table=live, columns=list(columns))
    return True


def drop_index_if_present(name: str, table: str) -> bool:
    """Drop an index, if it is there.

    Returns ``True`` when the index was dropped. This is the counterpart of
    :func:`create_index_if_missing` for the way back: a downgrade that drops
    an index the upgrade skipped fails with ``ORA-01418``, and a downgrade
    that drops an index the models own breaks the schema.
    """
    from alembic import op

    bind = op.get_bind()
    inspector = inspect(bind)
    catalog = catalog_names(bind, tables=[table])
    live = catalog.table(table) or table
    present = {
        str(index["name"]).casefold()
        for index in inspector.get_indexes(live)
        if index.get("name")
    }
    if name.casefold() not in present:
        return False

    op.drop_index(name, table_name=live)
    log.info("index dropped", index=name, table=live)
    return True
