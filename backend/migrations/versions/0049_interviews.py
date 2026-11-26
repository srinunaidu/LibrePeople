"""interviews: the schedule behind a candidate's pipeline

Revision ID: 0049_interviews
Revises: 0048_mfa_secret_envelope
Create Date: 2026-11-26

What this adds
--------------
* ``interviews`` — one scheduled interview: the candidate, the optional
  requisition, the pipeline stage, the scheduled time, the interviewers
  (a JSON array stored as plain ``Text``), the ``status`` lifecycle
  (Scheduled -> Completed | Cancelled | NoShow) and the feedback.

Expand-only
-----------
Pure expansion: one new table and its indexes, no column of an existing
table changes, so it applies cleanly on a database that already holds data.
The downgrade removes exactly what the upgrade created.

Idempotency
-----------
The upgrade asks the catalog first (the 0037 pattern): a database the
current models already built via ``create_all()`` carries the table, so
the upgrade skips it there. Re-running is a no-op.

Postgres cleanliness
--------------------
No database enum anywhere: ``status`` and ``stage`` are plain ``String``
columns and the lifecycle is enforced by the service, so there is no
enum type to create, check-first, or drop. Indexes are created only when
missing.

The migration imports no model: Alembic executes every revision module
while it reads the chain, and a model import would build the application
engine at read time.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import (
    catalog_names,
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0049_interviews"
down_revision = "0048_mfa_secret_envelope"
branch_labels = None
depends_on = None

TABLE = "interviews"

INTERVIEWS_INDEXES = (
    ("ix_interviews_tenant_id", (TABLE, ("tenant_id",))),
    ("ix_interviews_candidate_id", (TABLE, ("candidate_id",))),
    ("ix_interviews_requisition_id", (TABLE, ("requisition_id",))),
)


def upgrade() -> None:
    catalog = catalog_names(op.get_bind(), tables=[TABLE])

    if catalog.table(TABLE) is None:
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False),
            sa.Column(
                "requisition_id",
                sa.Integer(),
                sa.ForeignKey("job_requisitions.id"),
                nullable=True,
            ),
            sa.Column("stage", sa.String(50), nullable=False, server_default="Screening"),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("interviewers", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="Scheduled"),
            sa.Column("feedback", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        print(f"[0049_interviews] created {TABLE}")
    else:
        print(f"[0049_interviews] {TABLE} already present; skipping")

    for name, (table, columns) in INTERVIEWS_INDEXES:
        if create_index_if_missing(name, table, list(columns)):
            print(f"[0049_interviews] created index {name}")
        else:
            print(f"[0049_interviews] index {name} already present; skipping")


def downgrade() -> None:
    for name, (table, _columns) in reversed(INTERVIEWS_INDEXES):
        if drop_index_if_present(name, table):
            print(f"[0049_interviews] dropped index {name}")
    if catalog_names(op.get_bind(), tables=[TABLE]).table(TABLE) is not None:
        op.drop_table(TABLE)
        print(f"[0049_interviews] dropped {TABLE}")
    else:
        print(f"[0049_interviews] {TABLE} already absent; skipping")
