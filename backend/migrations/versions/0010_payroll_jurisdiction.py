"""payroll_jurisdiction: the jurisdiction and the rule pack of a pay run

Revision ID: 0010_payroll_jurisdiction
Revises: 0009_credential_role_constraint
Create Date: 2026-10-22

What this adds
--------------
* ``pay_runs.jurisdiction`` — the ISO 3166-1 alpha-2 country code of the
  jurisdiction whose rule pack applies to the run.
* ``pay_runs.rule_pack_id`` — the pack that produced the run, recorded when
  the run is calculated.

Why the run has to name its jurisdiction
----------------------------------------
A pay run is calculated only from a rule pack that is ``verified`` and in
force on the pay date. The resolver needs two things to find that pack: the
jurisdiction and the date. The date is the pay date of the period, which
the run already points at. The jurisdiction had nowhere to live, so a run
could be calculated without the product ever knowing which rules applied to
it — which is the defect this column closes.

Expand-then-contract
---------------------
This revision is the *expand* half. It adds two nullable columns and changes
nothing that exists. A run created before the jurisdiction was recorded has
no jurisdiction, and such a run is refused at calculation time rather than
calculated against a guess — the refusal is the safe direction, and the
audit row that records it is the evidence.

The *contract* half — ``NOT NULL`` on the jurisdiction — is a separate
revision, to be written once every deployment records a jurisdiction on
every run. It is not in this one: making the column not null now would fail
against the rows that already exist, and a migration that cannot be applied
is not a migration.

The downgrade drops both columns, which is the true reverse of adding them.
It loses the jurisdiction of every run and the pack each run was calculated
from; that is what a downgrade of this revision means, and it is never run
against a production database as part of normal operation.

Identifiers come from the catalog
----------------------------------
SQLAlchemy's Oracle reflection lower-cases every identifier it reports and
the catalog is mixed, so a statement built from a reflected name names an
object that does not exist. Every statement here is built from the names
the catalog holds, read through :func:`app.core.migrations.catalog_names`.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names

revision = "0010_payroll_jurisdiction"
down_revision = "0009_credential_role_constraint"
branch_labels = None
depends_on = None


#: The table the columns are added to.
TABLE = "pay_runs"

#: The columns to add: name -> definition. Both are nullable.
COLUMNS: list[tuple[str, sa.Column]] = [
    ("jurisdiction", sa.Column("jurisdiction", sa.String(8), nullable=True)),
    ("rule_pack_id", sa.Column("rule_pack_id", sa.String(120), nullable=True)),
]


def upgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        # The table itself is missing; that is a different problem and this
        # revision does not invent tables.
        print(f"[0010_payroll_jurisdiction] {TABLE} is not present; skipping")
        return

    present = catalog.columns.get(live_table.upper(), {})
    for name, definition in COLUMNS:
        if name.upper() in present:
            # The column is already there under the name the catalog uses.
            print(
                f"[0010_payroll_jurisdiction] {live_table}.{name} is already "
                "present; skipping"
            )
            continue
        op.add_column(live_table, definition)
        print(f"[0010_payroll_jurisdiction] added {live_table}.{name}")


def downgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        print(f"[0010_payroll_jurisdiction] {TABLE} is not present; skipping")
        return

    to_drop = []
    for name, _definition in COLUMNS:
        live_column = catalog.column(live_table, name)
        if live_column is not None:
            to_drop.append(live_column)
    if not to_drop:
        print(f"[0010_payroll_jurisdiction] {live_table} carries neither column; nothing to do")
        return

    # SQLite cannot drop a column in place before 3.35, so the table is
    # rebuilt through Alembic's batch mode there; the rows, the indexes and
    # the foreign keys are copied across.
    with op.batch_alter_table(live_table) as batch:
        for live_column in to_drop:
            batch.drop_column(live_column)
            print(f"[0010_payroll_jurisdiction] dropped {live_table}.{live_column}")
