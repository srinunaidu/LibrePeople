"""job_queue: add background job queue table

Revision ID: 0004_job_queue
Revises: 0003_mfa
Create Date: 2026-10-20

Creates the job_queue table for tracking background jobs through their
lifecycle (queued, running, succeeded, failed, dead). Each job carries
an input hash and (on completion) a result hash, making re-runs with
identical input a no-op.

Oracle
------
The table declares ``lease_expires_at`` with ``index=True``, so the column
is already indexed by the time the table exists. Creating a *second* index
over the same column list is refused by Oracle with ``ORA-01408`` ("such
column list already indexed"), whatever the two indexes are called, and the
first version of this revision did exactly that. The migration chain could
therefore not be applied to a fresh database at all: it stopped here.

The indexes are created through
:func:`app.core.migrations.create_index_if_missing`, which reads the column
lists the schema already indexes — the indexes, the unique constraints and
the primary key — and skips the one that is taken. The composite index over
``(state, job_type)`` is a column list of its own, so it is still created;
the one over ``(lease_expires_at)`` is not, because the column carries an
index already.

The downgrade uses the matching
:func:`app.core.migrations.drop_index_if_present`. An index the upgrade
skipped is not there to be dropped, and dropping it anyway fails with
``ORA-01418`` ("specified index does not exist"). The downgrade also leaves
a table that is not there alone, which is the state of a legacy database
that predates this revision.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import (
    catalog_names,
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0004_job_queue"
down_revision = "0003_mfa"
branch_labels = None
depends_on = None

#: The indexes this revision creates, in the order it creates them.
#:
#: The names are the revision's own. SQLAlchemy names the index the column
#: declaration creates ``ix_job_queue_lease_expires_at``, which is why the
#: two collide: they are the same column list.
INDEXES = (
    ("ix_job_queue_state_type", ("state", "job_type")),
    ("ix_job_queue_lease_expires", ("lease_expires_at",)),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    catalog = catalog_names(bind)

    if catalog.table("job_queue") is None:
        op.create_table(
            "job_queue",
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("job_type", sa.String(50), nullable=False, index=True),
            sa.Column("input_hash", sa.String(64), nullable=False, index=True),
            sa.Column("result_hash", sa.String(64), nullable=True),
            sa.Column(
                "state",
                sa.String(20),
                nullable=False,
                default="queued",
                index=True,
            ),
            sa.Column("attempts", sa.Integer(), nullable=False, default=0),
            sa.Column("max_attempts", sa.Integer(), nullable=False, default=5),
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True, index=True),
            sa.Column("worker_id", sa.String(100), nullable=True),
            sa.Column("error_code", sa.String(100), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                default=lambda: __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ),
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False, default=10),
            sa.PrimaryKeyConstraint("id"),
        )
        print("[0004_job_queue] created job_queue")

    for name, columns in INDEXES:
        if create_index_if_missing(name, "job_queue", list(columns)):
            print(f"[0004_job_queue] created index {name}")
        else:
            print(
                f"[0004_job_queue] job_queue ({', '.join(columns)}) is already "
                f"indexed; {name} was not created"
            )


def downgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind)

    live = catalog.table("job_queue")
    if live is None:
        print("[0004_job_queue] job_queue is not present; nothing to drop")
        return

    for name, _columns in reversed(INDEXES):
        if drop_index_if_present(name, "job_queue"):
            print(f"[0004_job_queue] dropped index {name}")
        else:
            print(f"[0004_job_queue] {name} is not present; skipping")

    op.drop_table(live)
    print("[0004_job_queue] dropped job_queue")
