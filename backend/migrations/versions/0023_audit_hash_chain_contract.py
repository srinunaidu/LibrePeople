"""audit_hash_chain_contract: the chain columns become NOT NULL

Revision ID: 0023_audit_hash_chain_contract
Revises: 0022_audit_hash_chain
Create Date: 2026-10-26

The contract half of the expand-then-contract pair. Revision 0022 added the
columns nullable so that a table with existing rows could be backfilled;
this revision states what is now true — every entry carries a link and a
hash — and lets the database enforce it. A row written without them is a
bug, and it must fail at the write rather than be discovered by the verifier.

The append-only triggers are dropped while the column definition changes and
reinstalled afterwards. On SQLite the change rebuilds the table (which drops
its triggers anyway); on Oracle it is an in-place ``MODIFY``.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.audit_chain import (
    backfill_chain,
    install_append_only,
    remove_append_only,
    set_head,
)
from app.core.migrations import catalog_names

revision = "0023_audit_hash_chain_contract"
down_revision = "0022_audit_hash_chain"
branch_labels = None
depends_on = None

TABLE = "audit_logs"
COLUMNS = ("prev_hash", "entry_hash")


def upgrade() -> None:
    bind = op.get_bind()
    remove_append_only(bind)
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        print(f"[0023_audit_hash_chain_contract] {TABLE} is not present; skipping")
        return

    # A write from the previous release can land between the expand
    # migration's backfill and the contract statement below. Chain anything
    # still unhashed first, or the NOT NULL change would fail on a row nobody
    # tampered with.
    pending = [
        column
        for column in COLUMNS
        if catalog.column(live_table, column) is not None
        and not catalog.is_not_null(live_table, column)
    ]
    if pending:
        chained, last_id, last_hash = backfill_chain(bind)
        if chained:
            # The backfill extended the tail, so the head has to name the new
            # last entry or the verifier would report a truncation.
            set_head(bind, last_hash, last_id)
            print(
                f"[0023_audit_hash_chain_contract] chained {chained} late "
                f"entries before the contract"
            )

    for column in COLUMNS:
        if catalog.column(live_table, column) is None:
            print(
                f"[0023_audit_hash_chain_contract] {live_table}.{column} is "
                f"absent; skipping"
            )
            continue
        if catalog.is_not_null(live_table, column):
            print(
                f"[0023_audit_hash_chain_contract] {live_table}.{column} is "
                f"already NOT NULL; skipping"
            )
            continue
        with op.batch_alter_table(live_table) as batch:
            batch.alter_column(
                column,
                existing_type=sa.String(64),
                existing_nullable=True,
                nullable=False,
            )
        print(f"[0023_audit_hash_chain_contract] {live_table}.{column} is NOT NULL")

    install_append_only(bind)


def downgrade() -> None:
    bind = op.get_bind()
    remove_append_only(bind)
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        return
    for column in COLUMNS:
        if catalog.column(live_table, column) is None:
            continue
        if not catalog.is_not_null(live_table, column):
            continue
        with op.batch_alter_table(live_table) as batch:
            batch.alter_column(
                column,
                existing_type=sa.String(64),
                existing_nullable=False,
                nullable=True,
            )
        print(
            f"[0023_audit_hash_chain_contract] {live_table}.{column} is nullable again"
        )
    install_append_only(bind)
