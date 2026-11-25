"""asset register and custody assignments

Revision ID: 0046_assets
Revises: 0045_payroll_pipeline_run_type
Create Date: 2026-11-23

What this adds
--------------
* ``assets`` — the trackable asset register: ``tag`` (unique **per tenant**
  via ``uq_assets_tenant_tag``), name, category, description, serial number
  and the custody ``status`` FSM
  (``in_stock``/``assigned``/``maintenance``/``retired``/``lost``), with the
  shared ``tenant_id`` discriminator and composite tenant/id index.
* ``asset_assignments`` — one custody spell of an asset with an employee:
  open/closed status, the assigning actor and time, the employee's own
  acknowledgement time, and the close actor/time/reason
  (``returned``/``transferred``) plus the return condition
  (``good``/``damaged``/``lost``). At most one open spell per asset is
  enforced by the service inside the assigning transaction.

Expand-only
-----------
Pure expansion: two new tables and their indexes, no column of an existing
table changes, so it applies cleanly on a database that already holds data.
The downgrade removes exactly what the upgrade created.

Idempotency
-----------
Both directions ask the catalog first (the 0037 pattern): a database the
current models already built via ``create_all()`` carries the tables, so
the upgrade skips them there. Re-running is a no-op.

The migration imports no model: Alembic executes every revision module
while it reads the chain, and a model import would build the application
engine at read time. The CHECK texts below are duplicated from
``app.models.assets`` deliberately and must stay in sync.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import (
    catalog_names,
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0046_assets"
down_revision = "0045_payroll_pipeline_run_type"
branch_labels = None
depends_on = None

ASSETS = "assets"
ASSIGNMENTS = "asset_assignments"

ASSET_STATUS_CHECK = (
    "status IN ('in_stock','assigned','maintenance','retired','lost')"
)
ASSIGNMENT_STATUS_CHECK = "status IN ('open','closed')"
ASSIGNMENT_CLOSE_REASON_CHECK = (
    "close_reason IS NULL OR close_reason IN ('returned','transferred')"
)
RETURN_CONDITION_CHECK = (
    "return_condition IS NULL OR return_condition IN ('good','damaged','lost')"
)

ASSET_INDEXES = (
    ("ix_assets_tenant_id", (ASSETS, ("tenant_id",))),
    ("ix_assets_tag", (ASSETS, ("tag",))),
    ("ix_assets_tenant_id_id", (ASSETS, ("tenant_id", "id"))),
)

ASSIGNMENT_INDEXES = (
    ("ix_asset_assignments_tenant_id", (ASSIGNMENTS, ("tenant_id",))),
    ("ix_asset_assignments_asset_id", (ASSIGNMENTS, ("asset_id",))),
    ("ix_asset_assignments_employee_id", (ASSIGNMENTS, ("employee_id",))),
    ("ix_asset_asg_tenant_id_id", (ASSIGNMENTS, ("tenant_id", "id"))),
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    catalog = catalog_names(op.get_bind(), tables=[ASSETS, ASSIGNMENTS])

    if catalog.table(ASSETS) is None:
        op.create_table(
            ASSETS,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("tag", sa.String(40), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("category", sa.String(60), nullable=False, server_default="General"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("serial_number", sa.String(120), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="in_stock"),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
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
            sa.UniqueConstraint("tenant_id", "tag", name="uq_assets_tenant_tag"),
            sa.CheckConstraint(ASSET_STATUS_CHECK, name="ck_asset_status_fsm"),
        )
        print(f"[0046_assets] created {ASSETS}")
    else:
        print(f"[0046_assets] {ASSETS} already present; skipping")

    if catalog.table(ASSIGNMENTS) is None:
        op.create_table(
            ASSIGNMENTS,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
            sa.Column("status", sa.String(10), nullable=False, server_default="open"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column(
                "assigned_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("closed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("close_reason", sa.String(20), nullable=True),
            sa.Column("return_condition", sa.String(10), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint(ASSIGNMENT_STATUS_CHECK, name="ck_asset_asg_status"),
            sa.CheckConstraint(ASSIGNMENT_CLOSE_REASON_CHECK, name="ck_asset_asg_close_reason"),
            sa.CheckConstraint(RETURN_CONDITION_CHECK, name="ck_asset_asg_condition"),
        )
        print(f"[0046_assets] created {ASSIGNMENTS}")
    else:
        print(f"[0046_assets] {ASSIGNMENTS} already present; skipping")

    for name, (table, columns) in ASSET_INDEXES + ASSIGNMENT_INDEXES:
        if create_index_if_missing(name, table, list(columns)):
            print(f"[0046_assets] created index {name}")
        else:
            print(f"[0046_assets] index {name} already present; skipping")


def downgrade() -> None:
    for name, (table, _columns) in reversed(ASSET_INDEXES + ASSIGNMENT_INDEXES):
        if drop_index_if_present(name, table):
            print(f"[0046_assets] dropped index {name}")

    existing = _tables()
    for table in (ASSIGNMENTS, ASSETS):
        if table in existing:
            op.drop_table(table)
            print(f"[0046_assets] dropped {table}")
        else:
            print(f"[0046_assets] {table} already absent; skipping")