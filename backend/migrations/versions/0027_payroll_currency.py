"""payroll_currency: ISO 4217 currency on pay runs and payslips

Revision ID: 0027_payroll_currency
Revises: 0026_employment_history
Create Date: 2026-11-07

What this adds
--------------
* ``pay_runs.currency`` — the ISO 4217 currency code of the run, CHAR(3),
  uppercase, e.g. ``USD``, ``GBP``.
* ``pay_slips.currency`` — the ISO 4217 currency code of the slip, CHAR(3).

Why every pay figure needs a currency
--------------------------------------
A pay amount without a currency is not a pay amount: $5,000 and £5,000 are
different obligations, and a bank file that mixes currencies is a rejected
file. The contract requires a non-null currency on every pay run and payslip,
but this revision is the *expand* half of an expand-then-contract change.

Expand-then-contract
--------------------
Both columns are added nullable here. Existing rows are backfilled to the
tenant default currency (``settings.DEFAULT_CURRENCY``, ``"USD"`` out of the
box) so that every row carries a value as soon as the migration runs. The
*contract* half — making the columns NOT NULL — is a separate revision, to be
applied once every deployment writes a currency on every run and slip. It is
not applied here: constraining the columns now would fail against rows the
backfill has not reached, and a migration that cannot be applied is not a
migration.

The downgrade drops both columns, which is the true reverse of adding them.
It loses the currency of every run and slip; that is what a downgrade means,
and it is never run against a production database as part of normal operation.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.config import settings
from app.core.migrations import catalog_names

revision = "0027_payroll_currency"
down_revision = "0026_employment_history"
branch_labels = None
depends_on = None

#: The tenant default currency used to backfill existing rows.
DEFAULT_CURRENCY = settings.DEFAULT_CURRENCY

#: The tables and the column definition to add to each.
TABLES: dict[str, sa.Column] = {
    "pay_runs": sa.Column("currency", sa.String(3), nullable=True),
    "pay_slips": sa.Column("currency", sa.String(3), nullable=True),
}


def upgrade() -> None:
    bind = op.get_bind()
    for table, definition in TABLES.items():
        catalog = catalog_names(bind, tables=[table])
        live_table = catalog.table(table)
        if live_table is None:
            print(f"[0027_payroll_currency] {table} is not present; skipping")
            continue

        present = catalog.columns.get(live_table.upper(), {})
        if "CURRENCY" in present:
            print(
                f"[0027_payroll_currency] {live_table}.currency is already "
                "present; skipping"
            )
            continue

        op.add_column(live_table, definition)
        print(f"[0027_payroll_currency] added {live_table}.currency")

        # Backfill every existing row to the tenant default currency so that
        # no row is left without one. The column stays nullable so the
        # backfill cannot fail against a row the API has not yet written.
        bind = op.get_bind()
        bind.execute(
            sa.text(
                f"UPDATE {live_table} SET currency = :currency "
                f"WHERE currency IS NULL"
            ),
            {"currency": DEFAULT_CURRENCY},
        )
        print(
            f"[0027_payroll_currency] backfilled {live_table}.currency to "
            f"{DEFAULT_CURRENCY}"
        )


def downgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        catalog = catalog_names(bind, tables=[table])
        live_table = catalog.table(table)
        if live_table is None:
            print(f"[0027_payroll_currency] {table} is not present; skipping")
            continue

        live_column = catalog.column(live_table, "currency")
        if live_column is None:
            print(
                f"[0027_payroll_currency] {live_table} carries no currency; "
                "nothing to do"
            )
            continue

        # SQLite cannot drop a column in place before 3.35, so the table is
        # rebuilt through Alembic's batch mode there; the rows, the indexes
        # and the foreign keys are copied across.
        with op.batch_alter_table(live_table) as batch:
            batch.drop_column(live_column)
            print(f"[0027_payroll_currency] dropped {live_table}.currency")
