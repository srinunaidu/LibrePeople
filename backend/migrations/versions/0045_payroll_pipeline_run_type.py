"""payroll pipeline run_type + reversal link (expand-only)

Revision ID: 0045_payroll_pipeline_run_type
Revises: 0044_forecasting_tenant_isolation
Create Date: 2026-11-23

What this adds
--------------
* ``pay_runs.run_type`` String(20) nullable — regular | off_cycle |
  adjustment | reversal. Nullable so every row that predates the column
  stays readable; the API defaults missing to ``regular``.
* ``pay_runs.reversal_of_run_id`` Integer nullable — self-reference to the
  Finalized run an adjustment/reversal corrects. Nullable; no NOT NULL.

Expand-then-contract
--------------------
This is the *expand* half only. Both columns are nullable, no backfill
changes semantics (existing runs read as ``regular`` with no reversal
link). The *contract* half (NOT NULL / CHECK enforcement) is a separate
revision, not applied here.

Idempotency / downgrade follow the 0010/0031 pattern: inspect the catalog
first, skip what already exists, drop what this revision added on
downgrade.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names, drop_index_if_present

revision = "0045_payroll_pipeline_run_type"
down_revision = "0044_forecasting_tenant_isolation"
branch_labels = None
depends_on = None

TABLE = "pay_runs"
RUN_TYPE_CHECK = (
    "run_type IS NULL OR run_type IN "
    "('regular','off_cycle','adjustment','reversal')"
)


def upgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        print(f"[0045_payroll_pipeline_run_type] {TABLE} is not present; skipping")
        return
    present = catalog.columns.get(live_table.upper(), {})

    if "RUN_TYPE" in present:
        print(f"[0045_payroll_pipeline_run_type] {live_table}.run_type already present; skipping")
    else:
        op.add_column(
            live_table,
            sa.Column(
                "run_type",
                sa.String(20),
                sa.CheckConstraint(RUN_TYPE_CHECK, name="ck_pay_runs_run_type"),
                nullable=True,
            ),
        )
        print(f"[0045_payroll_pipeline_run_type] added {live_table}.run_type")

    # Re-read catalog so the second add sees the fresh shape on dialects
    # that cache reflection per transaction.
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    present = catalog.columns.get(live_table.upper(), {})
    if "REVERSAL_OF_RUN_ID" in present:
        print(
            f"[0045_payroll_pipeline_run_type] {live_table}.reversal_of_run_id "
            "already present; skipping"
        )
        return
    # Plain Integer (no DB-level FK) keeps SQLite batch rebuild simple;
    # the ORM declares the self-FK and the API validates the link.
    op.add_column(
        live_table,
        sa.Column("reversal_of_run_id", sa.Integer(), nullable=True),
    )
    print(f"[0045_payroll_pipeline_run_type] added {live_table}.reversal_of_run_id")


def downgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        print(f"[0045_payroll_pipeline_run_type] {TABLE} is not present; skipping")
        return
    for col in ("reversal_of_run_id", "run_type"):
        live_column = catalog.column(live_table, col)
        if live_column is None:
            print(f"[0045_payroll_pipeline_run_type] {live_table}.{col} already absent; skipping")
            continue
        inspector = sa.inspect(bind)
        try:
            for index in inspector.get_indexes(live_table):
                column_names = [str(c).casefold() for c in index.get("column_names") or []]
                if live_column.casefold() in column_names:
                    drop_index_if_present(index["name"], live_table)
        except Exception:
            pass
        op.drop_column(live_table, live_column)
        print(f"[0045_payroll_pipeline_run_type] dropped {live_table}.{col}")
