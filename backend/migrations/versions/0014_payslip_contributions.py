"""payslip_contributions: the statutory contributions of a payslip

Revision ID: 0014_payslip_contributions
Revises: 0013_public_intake
Create Date: 2026-10-22

What this adds
--------------
* ``pay_slips.employee_contributions`` — the contributions the employee pays
  under the rule pack, for the period.
* ``pay_slips.employer_contributions`` — the contributions the employer pays
  under the rule pack, for the period.

Why the payslip needs them
--------------------------
The rule pack computes the employer's contributions: the social insurance
the employer owes on the employee's pay. The engine produced them and the
payslip had nowhere to put them, so they were lost the moment the payslip was
written — the money was computed, paid for by the employer, and then gone.
The employee's own contributions were no better: they were inside the
deductions, with no total of their own to reconcile against.

Both columns are nullable, and the engine writes them on every payslip it
calculates. A payslip that existed before this revision carries no
contribution, and the reconciliation reads a missing total as zero rather
than as a discrepancy.

Expand-then-contract
--------------------
This revision is the *expand* half: two nullable columns, nothing changed,
nothing removed. The *contract* half — ``NOT NULL`` on both — waits until
every payslip carries a contribution, and a migration that cannot be applied
is not a migration.

The downgrade drops both columns, which is the true reverse of adding them.
It loses the contribution of every payslip; that is what a downgrade of this
revision means, and it is never run against a production database as part of
normal operation.

Identifiers come from the catalog
----------------------------------
SQLAlchemy's Oracle reflection lower-cases every identifier it reports and
the catalog is mixed, so a statement built from a reflected name names an
object that does not exist. Every statement here is built from the names the
catalog holds, read through :func:`app.core.migrations.catalog_names`.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names

revision = "0014_payslip_contributions"
down_revision = "0013_public_intake"
branch_labels = None
depends_on = None


#: The table the columns are added to.
TABLE = "pay_slips"

#: The columns to add: name -> definition. Both are nullable.
COLUMNS: list[tuple[str, sa.Column]] = [
    ("employee_contributions", sa.Column("employee_contributions", sa.Numeric(12, 2), nullable=True)),
    ("employer_contributions", sa.Column("employer_contributions", sa.Numeric(12, 2), nullable=True)),
]


def upgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        # The table itself is missing; that is a different problem and this
        # revision does not invent tables.
        print(f"[0014_payslip_contributions] {TABLE} is not present; skipping")
        return

    present = catalog.columns.get(live_table.upper(), {})
    for name, definition in COLUMNS:
        if name.upper() in present:
            # The column is already there under the name the catalog uses.
            print(
                f"[0014_payslip_contributions] {live_table}.{name} is already "
                "present; skipping"
            )
            continue
        op.add_column(live_table, definition)
        print(f"[0014_payslip_contributions] added {live_table}.{name}")


def downgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        print(f"[0014_payslip_contributions] {TABLE} is not present; skipping")
        return

    to_drop = []
    for name, _definition in COLUMNS:
        live_column = catalog.column(live_table, name)
        if live_column is not None:
            to_drop.append(live_column)
    if not to_drop:
        print(f"[0014_payslip_contributions] {live_table} carries neither column; nothing to do")
        return

    # SQLite cannot drop a column in place before 3.35, so the table is
    # rebuilt through Alembic's batch mode there; the rows, the indexes and
    # the foreign keys are copied across.
    with op.batch_alter_table(live_table) as batch:
        for live_column in to_drop:
            batch.drop_column(live_column)
            print(f"[0014_payslip_contributions] dropped {live_table}.{live_column}")
