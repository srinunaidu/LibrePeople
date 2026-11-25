"""Alembic environment.

The database URL is resolved from the application settings, so there is one
place that knows how to reach the database and no connection string is ever
committed to the repository.

Two behaviours worth knowing about:

**Autogenerate target.** ``alembic revision --autogenerate`` compares the
models against the database. Point it at an empty database to get a clean
baseline, or at a live database to get the delta.

**Legacy adoption.** This product was deployed before Alembic existed, using
``create_all()`` to build the schema. Those databases have no
``alembic_version`` table. Rather than trying to replay a baseline against a
schema that already exists, the migration runner stamps the baseline revision
and applies only the newer migrations. See ``scripts/migrate.py`` for the
logic and the loud logging that accompanies it.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the `app` package importable when alembic is invoked from the
# `backend/` directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# `ALEMBIC_DATABASE_URL` lets an operator point a migration run at a different
# database (a staging copy, or an empty database when generating a baseline)
# without changing the application's own configuration.
#
# It is applied to the environment *before* the application modules are
# imported, because `app.core.database` builds its engine at import time and
# refuses to start without a configured database.
_override = os.environ.get("ALEMBIC_DATABASE_URL")
if _override:
    os.environ["DATABASE_URL"] = _override

from app.core.config import settings  # noqa: E402
from app.core.database import Base, engine  # noqa: E402

import app.models  # noqa: E402,F401  (the models package)

# Register every model on Base.metadata.
#
# The list is discovered from the package rather than written out by hand, so
# adding a new model file cannot silently leave it out of the migration
# metadata. `app.core.idempotency` owns its table but lives outside the
# package, so it is imported explicitly.
import importlib  # noqa: E402
import pkgutil  # noqa: E402

for _finder, _name, _ispkg in pkgutil.iter_modules(app.models.__path__):
    if _name.startswith("_"):
        continue
    importlib.import_module(f"app.models.{_name}")

from app.core.idempotency import IdempotencyRecord  # noqa: E402,F401

# The model that owns the idempotency bookkeeping table lives beside the code
# that uses it; import it so its table is part of the metadata.
assert IdempotencyRecord.__table__ is not None

target_metadata = Base.metadata

config = context.config

if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:  # noqa: BLE001
        # A missing or unreadable logging config must not abort a migration.
        pass


def _database_url() -> str:
    """Resolve the database URL, honouring an explicit override."""
    url = getattr(settings, "DATABASE_URL", "") or ""
    if url:
        return url
    if settings.ORACLE_DSN:
        return "oracle+oracledb://:@"
    raise RuntimeError(
        "No database configured for migrations. Set DATABASE_URL, "
        "ORACLE_DSN + ORACLE_USER + ORACLE_PASSWORD, or ALEMBIC_DATABASE_URL."
    )


#: Width of the pre-created ``alembic_version.version_num`` column. Alembic
#: auto-creates ``alembic_version(version_num VARCHAR(32))`` (see
#: ``alembic/ddl/impl.py``: ``Column("version_num", String(32))``), but repo
#: revision ids reach 33 characters (``0044_forecasting_tenant_isolation``,
#: also ``0047_expense_category_tenant_code``). SQLite ignores VARCHAR
#: lengths so the stamp fits; PostgreSQL enforces it and the stamp UPDATE
#: fails with ``StringDataRightTruncation``. 255 is generic ``String`` (plain
#: VARCHAR/VARCHAR2 on every dialect — no PG-only syntax), so this is
#: behavior-neutral on SQLite and Oracle.
WIDE_VERSION_NUM_LENGTH = 255


def _ensure_wide_version_table(connection) -> None:
    """Create ``alembic_version`` with a wide ``version_num`` if missing.

    Alembic's ``MigrationContext._ensure_version_table`` issues
    ``create(checkfirst=True)``, so a pre-existing table is reused untouched:
    existing deployments (already stamped with the narrow table) are never
    altered. Only a database with no version table at all gets the wide one,
    which Alembic then reuses instead of auto-creating ``VARCHAR(32)``.
    Revision ids are never renamed (existing SQLite stamps must keep
    matching), so widening the column is the only safe fix.
    """
    from sqlalchemy import (
        Column,
        MetaData,
        PrimaryKeyConstraint,
        String,
        Table,
    )
    from sqlalchemy import inspect as sa_inspect

    if sa_inspect(connection).has_table("alembic_version"):
        return
    Table(
        "alembic_version",
        MetaData(),
        Column("version_num", String(WIDE_VERSION_NUM_LENGTH), nullable=False),
        # Same primary-key name Alembic itself uses
        # (``f"{version_table}_pkc"`` in ``alembic/ddl/impl.py``).
        PrimaryKeyConstraint("version_num", name="alembic_version_pkc"),
    ).create(connection)


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=engine.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""

    def process_revision_directives(context_, revision, directives):
        # Do not generate an empty migration file.
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                print("No schema changes detected.")

    connectable = config.attributes.get("connection", None)
    if connectable is None:
        connectable = engine

    with connectable.connect() as connection:
        # Pre-create the version table wide (create-if-missing only; existing
        # tables are left untouched) so Alembic reuses it instead of
        # auto-creating VARCHAR(32). See _ensure_wide_version_table. The
        # explicit commit returns the connection to a non-transactional
        # state: the inspection above auto-begins a transaction, and Alembic
        # treats an already-in-transaction connection as externally managed
        # (MigrationContext._in_external_transaction) and then never commits
        # the migration run itself — on SQLite the final version stamp is
        # silently rolled back while the DDL persists (psqlite implicitly
        # commits DDL), and on PostgreSQL the whole run would roll back.
        _ensure_wide_version_table(connection)
        if connection.in_transaction():
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            compare_type=True,
            compare_server_default=True,
            # SQLite cannot ALTER most things in place; batch mode rebuilds the
            # table instead, so the same migrations work in tests and on
            # Oracle.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
