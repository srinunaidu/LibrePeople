"""schema_drift_fix: the model columns and tables the earlier revisions missed

Revision ID: 0029_schema_drift_fix
Revises: 0028_tenant_discriminator
Create Date: 2026-11-12

Why this revision exists
------------------------
The B1 commit (``bda19a1``) added columns and two tables to the models, but
001-028 never created them. Production was built by ``create_all()`` and then
stamped at the baseline, so the models' newer shape never reached it. The
drift is invisible until a query names a missing object, which is what made
``/health/schema`` report:

* missing tables: ``break_glass_grants``, ``roster_versions``;
* missing columns: ``audit_logs.tenant_id``, ``audit_logs.break_glass_grant_id``,
  ``clients.archived_at``, ``clients.currency``, ``clients.date_format``,
  ``clients.deprovisioned_at``, ``clients.working_week``,
  ``leave_requests.balance_applied``.

The audit columns are the login-blocking ones: every login appends an audit
row, so the missing ``tenant_id`` made the INSERT fail with ``ORA-00904`` and
the login endpoint answer 503.

What this adds
--------------
* ``audit_logs.tenant_id`` VARCHAR(60) nullable, indexed;
* ``audit_logs.break_glass_grant_id`` INTEGER nullable;
* the five AD-03/lifecycle ``clients`` columns;
* ``leave_requests.balance_applied`` BOOLEAN NOT NULL default 0;
* ``break_glass_grants`` exactly as :mod:`app.models.break_glass` declares it;
* ``roster_versions`` exactly as :mod:`app.models.scheduling` declares it.

The definitions mirror the models: a nullable column stays nullable, a
``Mapped[...]`` (non-optional) column is NOT NULL, and the indexes the models
declare with ``index=True`` are created. ``balance_applied`` keeps a server
default of 0 so it can be added to a table that already holds rows on both
SQLite and Oracle; the model's Python-side ``default=False`` still fills it
for ORM inserts.

Idempotency
-----------
Every operation asks the catalog first. A fresh database built by the baseline
already carries the columns (the baseline creates the frozen tables from the
current models), so the upgrade skips them there; a production database that
predates the columns gets them. Re-running the revision is a no-op, and an
Oracle run that failed after a DDL statement auto-committed can be re-run:
tables are created only when absent and indexes only when the column list is
not already indexed.

Downgrade
---------
Drops the two tables and the eight columns this revision adds. That deletes
the break-glass history and the tenant attribution of every audit row; it is
never run against a production database as part of normal operation.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import (
    catalog_names,
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0029_schema_drift_fix"
down_revision = "0028_tenant_discriminator"
branch_labels = None
depends_on = None

AUDIT_LOGS = "audit_logs"
CLIENTS = "clients"
LEAVE_REQUESTS = "leave_requests"
BREAK_GLASS = "break_glass_grants"
ROSTER_VERSIONS = "roster_versions"

#: Indexes the models declare with ``index=True``. The names are the ones
#: SQLAlchemy generates for the model, so ``create_all()`` and this revision
#: agree on the schema. Oracle ADB (19c) accepts the 31/38-character names;
#: the older migrations in this chain already use names above 30 characters.
BREAK_GLASS_INDEXES = (
    ("ix_break_glass_grants_actor_id", ["actor_id"]),
    ("ix_break_glass_grants_target_tenant_id", ["target_tenant_id"]),
)
ROSTER_VERSION_INDEXES = (
    ("ix_roster_versions_tenant_id", ["tenant_id"]),
)


def _add_missing_columns(table: str, columns: dict[str, sa.Column]) -> str | None:
    """Add each column the live table does not have.

    Returns the catalog's name for the table, or ``None`` when the table is
    not present. ``op.add_column`` is not used for a foreign key (Alembic
    does not emit the constraint reliably on every dialect), so callers that
    add one use ``op.create_table`` instead.
    """
    catalog = catalog_names(op.get_bind(), tables=[table])
    live_table = catalog.table(table)
    if live_table is None:
        print(f"[0029_schema_drift_fix] {table} is not present; skipping")
        return None

    for name, definition in columns.items():
        if catalog.column(live_table, name) is not None:
            print(
                f"[0029_schema_drift_fix] {live_table}.{name} is already "
                "present; skipping"
            )
            continue
        op.add_column(live_table, definition)
        print(f"[0029_schema_drift_fix] added {live_table}.{name}")
    return live_table


def _ensure_index(table: str, name: str, columns: list[str]) -> None:
    """Create an index unless the table already indexes that column list."""
    catalog = catalog_names(op.get_bind(), tables=[table])
    live_table = catalog.table(table)
    if live_table is None:
        return
    if create_index_if_missing(name, live_table, columns):
        print(f"[0029_schema_drift_fix] created index {name} on {live_table}")


def _create_break_glass_grants() -> None:
    """Create the table :class:`app.models.break_glass.BreakGlassGrant` declares."""
    op.create_table(
        BREAK_GLASS,
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("target_tenant_id", sa.String(60), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("ttl_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "granted_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    print(f"[0029_schema_drift_fix] created table {BREAK_GLASS}")


def _create_roster_versions() -> None:
    """Create the table :class:`app.models.scheduling.RosterVersion` declares."""
    op.create_table(
        ROSTER_VERSIONS,
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.String(60), nullable=True),
        sa.Column("location_code", sa.String(50), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "published_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("solver_status", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    print(f"[0029_schema_drift_fix] created table {ROSTER_VERSIONS}")


def _ensure_table(table: str, create, indexes) -> None:
    """Create a table when it is absent, then ensure its indexes."""
    catalog = catalog_names(op.get_bind(), tables=[table])
    live_table = catalog.table(table)
    if live_table is None:
        create()
    else:
        print(
            f"[0029_schema_drift_fix] {live_table} is already present; "
            "leaving it in place"
        )
    for name, columns in indexes:
        _ensure_index(table, name, columns)


def upgrade() -> None:
    bind = op.get_bind()

    # --- audit_logs: the login-blocking columns ------------------------ #
    _add_missing_columns(
        AUDIT_LOGS,
        {
            "tenant_id": sa.Column("tenant_id", sa.String(60), nullable=True),
            "break_glass_grant_id": sa.Column(
                "break_glass_grant_id", sa.Integer(), nullable=True
            ),
        },
    )
    _ensure_index(AUDIT_LOGS, "ix_audit_logs_tenant_id", ["tenant_id"])

    # --- clients: AD-03 settings and lifecycle stamps ------------------ #
    _add_missing_columns(
        CLIENTS,
        {
            "currency": sa.Column("currency", sa.String(3), nullable=True),
            "date_format": sa.Column("date_format", sa.String(20), nullable=True),
            "working_week": sa.Column("working_week", sa.String(40), nullable=True),
            "deprovisioned_at": sa.Column(
                "deprovisioned_at", sa.DateTime(timezone=True), nullable=True
            ),
            "archived_at": sa.Column(
                "archived_at", sa.DateTime(timezone=True), nullable=True
            ),
        },
    )

    # --- leave_requests: whether the ledger was applied ---------------- #
    # NOT NULL with a server default so it can be added to a table that
    # already holds rows. Existing rows and raw-SQL inserts get 0, which is
    # the model's ``default=False``; ORM inserts still set it explicitly.
    _add_missing_columns(
        LEAVE_REQUESTS,
        {
            "balance_applied": sa.Column(
                "balance_applied",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        },
    )

    # --- the two tables the models declared but no revision created ---- #
    _ensure_table(BREAK_GLASS, _create_break_glass_grants, BREAK_GLASS_INDEXES)
    _ensure_table(
        ROSTER_VERSIONS, _create_roster_versions, ROSTER_VERSION_INDEXES
    )


def _drop_columns(table: str, columns: list[str]) -> None:
    """Drop columns this revision added, and any index that references them."""
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[table])
    live_table = catalog.table(table)
    if live_table is None:
        print(f"[0029_schema_drift_fix] {table} is not present; skipping")
        return

    inspector = sa.inspect(bind)
    for name in columns:
        live_column = catalog.column(live_table, name)
        if live_column is None:
            print(
                f"[0029_schema_drift_fix] {live_table}.{name} is already "
                "absent; skipping"
            )
            continue

        # SQLite refuses to drop a column an index still references. The
        # index this revision (or the baseline's ``index=True``) created has
        # to go first.
        for index in inspector.get_indexes(live_table):
            column_names = [
                str(column).casefold() for column in index.get("column_names") or []
            ]
            if live_column.casefold() in column_names:
                drop_index_if_present(index["name"], live_table)

        op.drop_column(live_table, live_column)
        print(f"[0029_schema_drift_fix] dropped {live_table}.{name}")


def downgrade() -> None:
    bind = op.get_bind()

    # The tables this revision created. Drop them first: their foreign keys
    # point at users, and roster_versions carries the tenant_id index.
    for table in (BREAK_GLASS, ROSTER_VERSIONS):
        catalog = catalog_names(bind, tables=[table])
        live_table = catalog.table(table)
        if live_table is None:
            print(f"[0029_schema_drift_fix] {table} is not present; skipping")
            continue
        op.drop_table(live_table)
        print(f"[0029_schema_drift_fix] dropped table {live_table}")

    _drop_columns(
        AUDIT_LOGS, ["tenant_id", "break_glass_grant_id"]
    )
    _drop_columns(
        CLIENTS,
        [
            "currency",
            "date_format",
            "working_week",
            "deprovisioned_at",
            "archived_at",
        ],
    )
    _drop_columns(LEAVE_REQUESTS, ["balance_applied"])
