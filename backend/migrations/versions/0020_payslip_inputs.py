"""payslip_inputs: the approved time and leave a payslip was paid from

Revision ID: 0020_payslip_inputs
Revises: 0019_forecast_accuracy
Create Date: 2026-10-26

What this adds
--------------
* ``pay_slips.inputs_json`` — the approved time entries and leave requests
  that fed the calculation, recorded on the slip itself.

Why the payslip needs it
------------------------
The engine has always accepted ``hours_worked``, ``overtime_hours``,
``overtime_hourly_rate`` and ``leave_days``. The pay-run calculation passed
none of them, so a payslip could be paid without the approved time and leave
of its period ever being read — and a slip nobody could trace back to the
rows that justified it. The figure now comes from approved rows only, and
this column records exactly which rows were consumed (counts, hours and
days), including any time entries that were **not** approved and therefore
excluded.

Expand-then-contract
--------------------
The column is nullable: a payslip written before this revision carries no
inputs record, and nothing reads it as zero — a missing record means "not
recorded", not "no inputs". The downgrade drops the column, which is the
true reverse of adding it.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names

revision = "0020_payslip_inputs"
down_revision = "0019_forecast_accuracy"
branch_labels = None
depends_on = None

TABLE = "pay_slips"
COLUMN = "inputs_json"


def upgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        print(f"[0020_payslip_inputs] {TABLE} is not present; skipping")
        return

    present = catalog.columns.get(live_table.upper(), {})
    if COLUMN.upper() in present:
        print(f"[0020_payslip_inputs] {live_table}.{COLUMN} is already present; skipping")
        return

    op.add_column(live_table, sa.Column(COLUMN, sa.Text(), nullable=True))
    print(f"[0020_payslip_inputs] added {live_table}.{COLUMN}")


def downgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        print(f"[0020_payslip_inputs] {TABLE} is not present; skipping")
        return

    live_column = catalog.column(live_table, COLUMN)
    if live_column is None:
        print(f"[0020_payslip_inputs] {live_table} carries no {COLUMN}; nothing to do")
        return

    # SQLite cannot drop a column in place before 3.35, so the table is
    # rebuilt through Alembic's batch mode there.
    with op.batch_alter_table(live_table) as batch:
        batch.drop_column(live_column)
        print(f"[0020_payslip_inputs] dropped {live_table}.{live_column}")
