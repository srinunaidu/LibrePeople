"""employee relations confidential cases (gap #9)

Revision ID: 0051_er_cases
Revises: 0050_workflow_steps
Create Date: 2026-11-26

What this adds
--------------
* ``er_cases`` — one row per confidential ER case: the tenant, the case
  type (grievance/discipline/investigation/whistleblowing — no PIP, D2),
  the optional subject employee, the authenticated reporter (``reported_by``,
  server-set — no anonymous intake, D1), severity, the forward-only status,
  the assignee, classification, outcome and timestamps.
* ``er_case_comments`` — append-only investigation history per case.
* ``er_case_attachments`` — file references (filename + opaque key under
  the authorised ``/api/v1/files/`` route) per case.

Expand-only
-----------
Pure expansion: three new tables and their indexes, no column of an
existing table changes, so it applies cleanly on a database that already
holds data. The downgrade removes exactly what the upgrade created.

Idempotency
-----------
The upgrade asks the catalog first (the 0037/0050 pattern): a database the
current models already built via ``create_all()`` carries the tables, so
the upgrade skips them there. Re-running is a no-op.

Postgres cleanliness
--------------------
No database enum anywhere: ``case_type``, ``severity`` and ``status`` are
plain ``String`` columns with CHECK constraints and the lifecycle is
enforced by the service, so there is no enum type to create, check-first,
or drop. Indexes are created only when missing.

The migration imports no model: Alembic executes every revision module
while it reads the chain, and a model import would build the application
engine at read time. The CHECK texts below are duplicated from
``app.models.er_case`` deliberately and must stay in sync.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import (
    catalog_names,
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0051_er_cases"
down_revision = "0050_workflow_steps"
branch_labels = None
depends_on = None

CASES_TABLE = "er_cases"
COMMENTS_TABLE = "er_case_comments"
ATTACHMENTS_TABLE = "er_case_attachments"

CASE_TYPE_CHECK = (
    "case_type IN ('grievance','discipline','investigation','whistleblowing')"
)
SEVERITY_CHECK = "severity IN ('Low','Medium','High','Critical')"
STATUS_CHECK = (
    "status IN ('Open','Triaged','Investigating','ActionTaken','Resolved','Closed')"
)

ER_INDEXES = (
    ("ix_er_cases_tenant_id_id", (CASES_TABLE, ("tenant_id", "id"))),
    ("ix_er_case_comments_case_id", (COMMENTS_TABLE, ("case_id",))),
    ("ix_er_case_attachments_case_id", (ATTACHMENTS_TABLE, ("case_id",))),
)


def upgrade() -> None:
    catalog = catalog_names(
        op.get_bind(),
        tables=[CASES_TABLE, COMMENTS_TABLE, ATTACHMENTS_TABLE],
    )

    if catalog.table(CASES_TABLE) is None:
        op.create_table(
            CASES_TABLE,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("case_type", sa.String(40), nullable=False),
            sa.Column(
                "subject_employee_id",
                sa.Integer(),
                sa.ForeignKey("employees.id"),
                nullable=True,
            ),
            sa.Column("reported_by", sa.String(100), nullable=False),
            sa.Column(
                "severity", sa.String(20), nullable=False, server_default="Medium"
            ),
            sa.Column(
                "status", sa.String(20), nullable=False, server_default="Open"
            ),
            sa.Column("assigned_to", sa.String(100), nullable=True),
            sa.Column("classification", sa.Text(), nullable=True),
            sa.Column("outcome", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint(CASE_TYPE_CHECK, name="ck_er_case_type"),
            sa.CheckConstraint(SEVERITY_CHECK, name="ck_er_severity"),
            sa.CheckConstraint(STATUS_CHECK, name="ck_er_status_fsm"),
        )
        print(f"[0051_er_cases] created {CASES_TABLE}")
    else:
        print(f"[0051_er_cases] {CASES_TABLE} already present; skipping")

    if catalog.table(COMMENTS_TABLE) is None:
        op.create_table(
            COMMENTS_TABLE,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column(
                "case_id",
                sa.Integer(),
                sa.ForeignKey("er_cases.id"),
                nullable=False,
            ),
            sa.Column("author", sa.String(100), nullable=False),
            sa.Column("comment", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        print(f"[0051_er_cases] created {COMMENTS_TABLE}")
    else:
        print(f"[0051_er_cases] {COMMENTS_TABLE} already present; skipping")

    if catalog.table(ATTACHMENTS_TABLE) is None:
        op.create_table(
            ATTACHMENTS_TABLE,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column(
                "case_id",
                sa.Integer(),
                sa.ForeignKey("er_cases.id"),
                nullable=False,
            ),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("file_key", sa.String(500), nullable=False),
            sa.Column("uploaded_by", sa.String(100), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        print(f"[0051_er_cases] created {ATTACHMENTS_TABLE}")
    else:
        print(f"[0051_er_cases] {ATTACHMENTS_TABLE} already present; skipping")

    for name, (table, columns) in ER_INDEXES:
        if create_index_if_missing(name, table, list(columns)):
            print(f"[0051_er_cases] created index {name}")
        else:
            print(f"[0051_er_cases] index {name} already present; skipping")


def downgrade() -> None:
    for name, (table, _columns) in reversed(ER_INDEXES):
        if drop_index_if_present(name, table):
            print(f"[0051_er_cases] dropped index {name}")
    for table in (ATTACHMENTS_TABLE, COMMENTS_TABLE, CASES_TABLE):
        if catalog_names(op.get_bind(), tables=[table]).table(table) is not None:
            op.drop_table(table)
            print(f"[0051_er_cases] dropped {table}")
        else:
            print(f"[0051_er_cases] {table} already absent; skipping")
