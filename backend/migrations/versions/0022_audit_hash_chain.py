"""audit_hash_chain: chain columns, the head row and the append-only guards

Revision ID: 0022_audit_hash_chain
Revises: 0021_audit_source_address
Create Date: 2026-10-26

What this adds
--------------
* ``audit_logs.prev_hash`` and ``audit_logs.entry_hash`` — the chain, as
  nullable columns. The not-null contract is the next revision (0023), so
  this one can be applied to a table that already has rows.
* ``audit_chain_head`` — one row that names the newest entry, so two writers
  cannot fork the chain and a truncation of the tail is detectable.
* A unique index on ``prev_hash``: a second entry extending the same entry
  cannot exist, which is the database-level backstop to the compare-and-set.
* Append-only triggers on ``audit_logs``, which refuse UPDATE and DELETE for
  the application and for anyone else using the same credentials. The
  application connects as the schema owner, and an owner cannot have
  UPDATE/DELETE revoked from itself, so a trigger — not a REVOKE — is what
  actually stops the statement on Oracle.

The backfill
------------
Every existing row is hashed in id order with the canonical form documented
in ``app/core/audit_chain.py``, starting from the genesis hash. A row that
already carries a hash is left alone and becomes the predecessor of the next
one, so a partly applied revision can be re-run. The head is moved to the
last entry only when rows were backfilled (or the head row is absent): if an
existing head disagrees with the rows, that is evidence, and the migration
must not overwrite it.

Downgrade
---------
Drops the triggers, the index, the columns and the head table, in that
order. The audit rows themselves are never deleted: losing the trail is
worse than losing the chain over it.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.audit_chain import (
    GENESIS_HASH,
    backfill_chain,
    install_append_only,
    remove_append_only,
    set_head,
)
from app.core.migrations import catalog_names, create_index_if_missing, drop_index_if_present

revision = "0022_audit_hash_chain"
down_revision = "0021_audit_source_address"
branch_labels = None
depends_on = None

TABLE = "audit_logs"
HEAD_TABLE = "audit_chain_head"
COLUMNS = ("prev_hash", "entry_hash")
INDEX = "uq_audit_logs_prev_hash"


def _ensure_columns(bind) -> None:
    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is None:
        print(f"[0022_audit_hash_chain] {TABLE} is not present; skipping the chain")
        return
    present = catalog.columns.get(live_table.upper(), {})
    for column in COLUMNS:
        if column.upper() in present:
            continue
        op.add_column(live_table, sa.Column(column, sa.String(64), nullable=True))
        print(f"[0022_audit_hash_chain] added {live_table}.{column}")


def _ensure_head_table(bind) -> None:
    if sa.inspect(bind).has_table(HEAD_TABLE):
        return
    op.create_table(
        HEAD_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("head_hash", sa.String(64), nullable=False),
        sa.Column("head_id", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    print(f"[0022_audit_hash_chain] created {HEAD_TABLE}")


def _backfill(bind) -> tuple[int, int | None, str]:
    backfilled, last_id, last_hash = backfill_chain(bind)
    print(f"[0022_audit_hash_chain] chained {backfilled} existing entries")
    return backfilled, last_id, last_hash


def _move_head(bind, backfilled: int, last_id: int | None, last_hash: str) -> None:
    head = bind.execute(
        sa.text(f"SELECT head_hash FROM {HEAD_TABLE} WHERE id = 1")
    ).first()
    if head is None:
        set_head(bind, last_hash, last_id)
        print(f"[0022_audit_hash_chain] seeded the head at {last_hash[:12]}...")
        return
    if backfilled:
        set_head(bind, last_hash, last_id)
        print(f"[0022_audit_hash_chain] moved the head to {last_hash[:12]}...")


def upgrade() -> None:
    bind = op.get_bind()
    _ensure_columns(bind)
    _ensure_head_table(bind)
    backfilled, last_id, last_hash = _backfill(bind)
    _move_head(bind, backfilled, last_id, last_hash)
    create_index_if_missing(INDEX, TABLE, ["prev_hash"], unique=True)
    install_append_only(bind)
    print(f"[0022_audit_hash_chain] append-only triggers installed on {TABLE}")


def downgrade() -> None:
    bind = op.get_bind()
    remove_append_only(bind)
    drop_index_if_present(INDEX, TABLE)

    catalog = catalog_names(bind, tables=[TABLE])
    live_table = catalog.table(TABLE)
    if live_table is not None:
        present = catalog.columns.get(live_table.upper(), {})
        for column in COLUMNS:
            if column.upper() not in present:
                continue
            with op.batch_alter_table(live_table) as batch:
                batch.drop_column(column)
            print(f"[0022_audit_hash_chain] dropped {live_table}.{column}")

    if sa.inspect(bind).has_table(HEAD_TABLE):
        op.drop_table(HEAD_TABLE)
        print(f"[0022_audit_hash_chain] dropped {HEAD_TABLE}")
