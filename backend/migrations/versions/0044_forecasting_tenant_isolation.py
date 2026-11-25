"""forecasting tenant isolation: shared-schema multi-tenancy tenant_id column

Revision ID: 0044_forecasting_tenant_isolation
Revises: 0043_integrity_expand
Create Date: 2026-11-23

What this adds
--------------
* ``tenant_id`` VARCHAR(60), nullable, on every forecasting table, plus a
  composite index ``ix_<table>_tenant_id_id`` over ``(tenant_id, id)`` so
  tenant-scoped lookups by id are served by a single index on every dialect.
* Every existing row is backfilled to ``DEFAULT_TENANT_SLUG`` (``"default"``)
  so legacy data keeps working immediately after the migration runs.

Why nullable here
-----------------
This is the *expand* half of an expand-then-contract change, mirroring
``0028_tenant_discriminator``. The column is nullable so the backfill cannot
fail against a row the API has not yet written, and so the migration can be
applied to a database that already holds data. The *contract* half — making
the column NOT NULL — is a separate revision, to be applied once every
deployment writes a tenant_id on every row it creates. It is not applied
here.

Downgrade
---------
Drops the composite index and the ``tenant_id`` column from every table. That
loses the tenant attribution of every row; that is what a downgrade means, and
it is never run against a production database as part of normal operation.

Idempotency
-----------
Both upgrade and downgrade are idempotent: an upgrade that is re-run skips
columns and indexes that are already present, and a downgrade skips columns
and indexes that are already gone.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names, create_index_if_missing

revision = "0044_forecasting_tenant_isolation"
down_revision = "0043_integrity_expand"
branch_labels = None
depends_on = None

#: The tenant slug used to backfill existing rows (see decision 3).
DEFAULT_TENANT_SLUG = "default"

#: The forecasting tenant-owned tables and the column definition to add to
#: each. Every row is forecast demand owned by one tenant: runs, their
#: per-series results, the model-version registry, the what-if scenarios
#: built on runs, the scenario results, the stored cost forecasts and
#: their rows, and the accuracy records. ``ForecastModelVersion`` is
#: registry metadata, but it is still written in a tenant's request
#: context, so it carries the discriminator like every other table here.
TABLES: dict[str, sa.Column] = {
    "forecast_runs": sa.Column("tenant_id", sa.String(60), nullable=True),
    "forecast_results": sa.Column("tenant_id", sa.String(60), nullable=True),
    "forecast_model_versions": sa.Column("tenant_id", sa.String(60), nullable=True),
    "forecast_scenarios": sa.Column("tenant_id", sa.String(60), nullable=True),
    "forecast_scenario_results": sa.Column("tenant_id", sa.String(60), nullable=True),
    "forecast_costs": sa.Column("tenant_id", sa.String(60), nullable=True),
    "forecast_cost_rows": sa.Column("tenant_id", sa.String(60), nullable=True),
    "forecast_accuracy_records": sa.Column("tenant_id", sa.String(60), nullable=True),
}


def _index_name(table: str) -> str:
    return f"ix_{table}_tenant_id_id"


def upgrade() -> None:
    bind = op.get_bind()
    for table, definition in TABLES.items():
        catalog = catalog_names(bind, tables=[table])
        live_table = catalog.table(table)
        if live_table is None:
            print(f"[0044_forecasting_tenant_isolation] {table} is not present; skipping")
            continue

        present = catalog.columns.get(live_table.upper(), {})
        if "TENANT_ID" not in present:
            op.add_column(live_table, definition)
            print(f"[0044_forecasting_tenant_isolation] added {live_table}.tenant_id")
        else:
            print(
                f"[0044_forecasting_tenant_isolation] {live_table}.tenant_id is already "
                "present; ensuring its index and backfill"
            )

        # Composite index over (tenant_id, id) for tenant-scoped lookups by id.
        # Idempotent: skipped when the column list is already indexed.
        create_index_if_missing(
            _index_name(table),
            live_table,
            ["tenant_id", "id"],
            unique=False,
        )

        # Backfill every existing row to the default tenant slug so that no row
        # is left without one. Safe to re-run: it only touches NULL rows.
        bind = op.get_bind()
        bind.execute(
            sa.text(
                f"UPDATE {live_table} SET tenant_id = :slug "
                f"WHERE tenant_id IS NULL"
            ),
            {"slug": DEFAULT_TENANT_SLUG},
        )
        print(
            f"[0044_forecasting_tenant_isolation] backfilled {live_table}.tenant_id to "
            f"{DEFAULT_TENANT_SLUG}"
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in TABLES:
        catalog = catalog_names(bind, tables=[table])
        live_table = catalog.table(table)
        if live_table is None:
            print(f"[0044_forecasting_tenant_isolation] {table} is not present; skipping")
            continue

        live_column = catalog.column(live_table, "tenant_id")
        if live_column is None:
            print(
                f"[0044_forecasting_tenant_isolation] {live_table} carries no tenant_id; "
                "nothing to do"
            )
            continue

        # Drop every index that references tenant_id before dropping the column.
        # SQLite refuses to drop a column that an index still references. The
        # composite index this revision created (``ix_<table>_tenant_id_id``)
        # plus any single-column index inherited from ``create_all()``
        # (``ix_<table>_tenant_id``) both have to go.
        for index in inspector.get_indexes(live_table):
            if "tenant_id" in (index.get("column_names") or []):
                op.drop_index(index["name"], table_name=live_table)
                print(
                    f"[0044_forecasting_tenant_isolation] dropped index "
                    f"{index['name']} on {live_table}"
                )

        # render_as_batch (migrations/env.py) rebuilds the table on SQLite so
        # the column can be dropped in place; on other dialects this is a plain
        # DROP COLUMN. Nesting an explicit batch_alter_table inside render_as_batch
        # makes the batch flush re-emit upgrade operations, so drop directly.
        op.drop_column(live_table, live_column)
        print(f"[0044_forecasting_tenant_isolation] dropped {live_table}.tenant_id")
