"""job_result_payload: a job remembers what it produced

Revision ID: 0025_job_result_payload
Revises: 0024_job_input_payload
Create Date: 2026-10-26

``complete`` computed the result hash and threw the result away. The hash
identifies one outcome — it is what makes a re-run with identical input a
no-op — but it is one-way, so the only record of what a job produced was a
fingerprint of it.

The consequence is concrete: a large import is applied by a background job,
the job returns the report the operator previewed plus what it applied, and
that report existed only in the handler's return value and in the log. There
was no way for the operator to collect it. The queue could say that the work
finished and nothing about what the work did.

This revision adds the result beside its hash, exactly as
`0024_job_input_payload` added the input beside the input hash. The column is
nullable so that jobs which completed before this revision keep their
history: their result cannot be reconstructed, and a reader is told so rather
than shown an empty success.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0025_job_result_payload"
down_revision = "0024_job_input_payload"
branch_labels = None
depends_on = None

TABLE = "job_queue"
COLUMN = "result_json"


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
