"""audit_source_address: the hashed client address of an audited action

Revision ID: 0021_audit_source_address
Revises: 0020_payslip_inputs
Create Date: 2026-10-26

What this adds
--------------
* ``audit_logs.source_ip_hash`` — the SHA-256 of the client address that
  performed the action, matching the convention ``refresh_tokens.ip_hash``
  already uses.

Why the trail needs it
----------------------
The audit trail could say *who* did something and *what* changed, but not
*from where*. An incident review could not tell an action taken by the
account holder from the same action taken with a stolen session. The
refresh-token table already stores a digest of the address; the audit row
did not, so the evidence was available for a token refresh and absent for
the change the token authorised.

Only the digest is stored. The raw address is personal data, and the trail
needs to answer "same place or not", not "which place".

Expand-then-contract
--------------------
The column is nullable: a row written before this revision carries no
address, and an action outside a request (a seed, a background job) carries
none either. A null means "not recorded", not "no address". The downgrade
drops the column, which is the true reverse of adding it.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names

revision = "0021_audit_source_address"
down_revision = "0020_payslip_inputs"
branch_labels = None
depends_on = None

TABLE = "audit_logs"
COLUMN = "source_ip_hash"


def upgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        print(f"[0021_audit_source_address] {TABLE} is not present; skipping")
        return

    present = catalog.columns.get(live_table.upper(), {})
    if COLUMN.upper() in present:
        print(f"[0021_audit_source_address] {live_table}.{COLUMN} is already present; skipping")
        return

    op.add_column(live_table, sa.Column(COLUMN, sa.String(64), nullable=True))
    print(f"[0021_audit_source_address] added {live_table}.{COLUMN}")


def downgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        print(f"[0021_audit_source_address] {TABLE} is not present; skipping")
        return

    live_column = catalog.column(live_table, COLUMN)
    if live_column is None:
        print(f"[0021_audit_source_address] {live_table} carries no {COLUMN}; nothing to do")
        return

    # SQLite cannot drop a column in place before 3.35, so the table is
    # rebuilt through Alembic's batch mode there.
    with op.batch_alter_table(live_table) as batch:
        batch.drop_column(live_column)
        print(f"[0021_audit_source_address] dropped {live_table}.{live_column}")
