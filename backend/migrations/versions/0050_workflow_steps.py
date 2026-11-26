"""workflow decision trail

Revision ID: 0050_workflow_steps
Revises: 0049_interviews
Create Date: 2026-11-26

What this adds
--------------
* ``workflow_steps`` — one append-only row per workflow decision: the
  entity (``entity_type`` in the v1 allowlist, ``entity_id``), the
  resulting ``stage`` (``PENDING``/``APPROVED``/``REJECTED``/``RETURNED``),
  the ``action`` that produced it, the deciding actor, an optional
  comment, the caller-supplied nullable ``due_at`` (NULL = never overdue,
  per D3) and the creation time. The core never owns domain state; the
  rows are only the decision trail.

Expand-only
-----------
Pure expansion: one new table and its indexes, no column of an existing
table changes, so it applies cleanly on a database that already holds
data. The downgrade removes exactly what the upgrade created.

Idempotency
-----------
The upgrade asks the catalog first (the 0037 pattern): a database the
current models already built via ``create_all()`` carries the table, so
the upgrade skips it there. Re-running is a no-op.

Postgres cleanliness
--------------------
No database enum anywhere: ``stage`` and ``action`` are plain ``String``
columns and the lifecycle is enforced by the service, so there is no
enum type to create, check-first, or drop. Indexes are created only when
missing.

The migration imports no model: Alembic executes every revision module
while it reads the chain, and a model import would build the application
engine at read time. The CHECK texts below are duplicated from
``app.models.workflow_step`` deliberately and must stay in sync.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import (
    catalog_names,
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0050_workflow_steps"
down_revision = "0049_interviews"
branch_labels = None
depends_on = None

TABLE = "workflow_steps"

STAGE_CHECK = "stage IN ('PENDING','APPROVED','REJECTED','RETURNED')"
ACTION_CHECK = "action IN ('OPEN','L1_APPROVE','APPROVE','REJECT','RETURN','REASSIGN')"

WORKFLOW_INDEXES = (
    ("ix_workflow_steps_tenant_id", (TABLE, ("tenant_id",))),
    ("ix_workflow_steps_entity_type", (TABLE, ("entity_type",))),
    ("ix_workflow_steps_entity_id", (TABLE, ("entity_id",))),
    ("ix_workflow_steps_tenant_id_id", (TABLE, ("tenant_id", "id"))),
)


def upgrade() -> None:
    catalog = catalog_names(op.get_bind(), tables=[TABLE])

    if catalog.table(TABLE) is None:
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("entity_type", sa.String(40), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=False),
            sa.Column("stage", sa.String(20), nullable=False, server_default="PENDING"),
            sa.Column("action", sa.String(20), nullable=False),
            sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint(STAGE_CHECK, name="ck_wf_stage_fsm"),
            sa.CheckConstraint(ACTION_CHECK, name="ck_wf_action_fsm"),
        )
        print(f"[0050_workflow_steps] created {TABLE}")
    else:
        print(f"[0050_workflow_steps] {TABLE} already present; skipping")

    for name, (table, columns) in WORKFLOW_INDEXES:
        if create_index_if_missing(name, table, list(columns)):
            print(f"[0050_workflow_steps] created index {name}")
        else:
            print(f"[0050_workflow_steps] index {name} already present; skipping")


def downgrade() -> None:
    for name, (table, _columns) in reversed(WORKFLOW_INDEXES):
        if drop_index_if_present(name, table):
            print(f"[0050_workflow_steps] dropped index {name}")
    if catalog_names(op.get_bind(), tables=[TABLE]).table(TABLE) is not None:
        op.drop_table(TABLE)
        print(f"[0050_workflow_steps] dropped {TABLE}")
    else:
        print(f"[0050_workflow_steps] {TABLE} already absent; skipping")
