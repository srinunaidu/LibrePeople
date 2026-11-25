"""job_input_payload: a job remembers what it was asked to do

Revision ID: 0024_job_input_payload
Revises: 0023_audit_hash_chain_contract
Create Date: 2026-10-26

``enqueue`` hashed the input payload and threw the payload away. A hash is
one-way, so no worker could ever recover the parameters a job was created
with — which is why no worker existed. The queue could record that work was
waiting but not what the work was.

This revision adds the payload. ``input_hash`` stays: it is what makes a
re-run with identical input a no-op, and it is compared, never reversed.

The column is nullable so that rows enqueued before this revision keep
their history. A job with no stored payload cannot be executed, and the
worker says so rather than inventing parameters.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0024_job_input_payload"
down_revision = "0023_audit_hash_chain_contract"
branch_labels = None
depends_on = None

TABLE = "job_queue"
COLUMN = "input_json"


def _has_table() -> bool:
    return sa.inspect(op.get_bind()).has_table(TABLE)


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(TABLE)}


def upgrade() -> None:
    if not _has_table() or COLUMN in _columns():
        return
    op.add_column(TABLE, sa.Column(COLUMN, sa.Text(), nullable=True))


def downgrade() -> None:
    if not _has_table() or COLUMN not in _columns():
        return
    # Batch mode keeps the drop portable: SQLite cannot drop a column in
    # place on every version it is run against, and rebuilding the table is
    # what batch mode does there. Oracle drops it in place.
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_column(COLUMN)
