"""scheduled reporting tables (reporting-personalization Part F)

Revision ID: 0053_report_schedules
Revises: 0052_report_views
Create Date: 2026-11-26

What this adds
--------------
* ``report_schedules`` — one row per recurring delivery: the tenant, the
  owning user, the allowlisted report key, the stored filters as JSON text,
  the frequency (``daily``/``weekly``/``monthly``), the IANA timezone, the
  recipient user ids as JSON text, the output format (``csv``/``xlsx``),
  the next due instant, and the active flag.
* ``report_runs`` — one row per executed (or attempted) delivery: the
  schedule, the queue job, the outcome status, the recipient count, the
  rendered payload (CSV text, base64 for xlsx), and the error, if any.

Expand-only
-----------
Pure expansion: two new tables and their indexes, no column of an existing
table changes. The downgrade removes exactly what the upgrade created.

Idempotency
-----------
The upgrade asks the catalog first (the 0037/0050/0051/0052 pattern).
Re-running is a no-op.

Postgres cleanliness
--------------------
No database enum anywhere: ``report_key``, ``frequency`` and ``status``
are plain ``String`` columns with CHECK constraints. Indexes are created
only when missing. The migration imports no model.

The CHECK texts below are duplicated from
``app.models.report_personalization`` deliberately and must stay in sync.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import (
    catalog_names,
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0053_report_schedules"
down_revision = "0052_report_views"
branch_labels = None
depends_on = None

SCHEDULES_TABLE = "report_schedules"
RUNS_TABLE = "report_runs"

SCHEDULE_KEY_CHECK = (
    "report_key IN ('joiners','leavers','attrition','payroll-summary')"
)
FREQUENCY_CHECK = "frequency IN ('daily','weekly','monthly')"
FORMAT_CHECK = "output_format IN ('csv','xlsx')"
RUN_STATUS_CHECK = "status IN ('delivered','partial','failed','dead')"

INDEXES = (
    ("ix_report_schedules_tenant_owner", (SCHEDULES_TABLE, ("tenant_id", "owner_id"))),
    ("ix_report_schedules_due", (SCHEDULES_TABLE, ("active", "next_due_at"))),
    ("ix_report_runs_schedule", (RUNS_TABLE, ("schedule_id",))),
)


def upgrade() -> None:
    catalog = catalog_names(op.get_bind(), tables=[SCHEDULES_TABLE, RUNS_TABLE])

    if catalog.table(SCHEDULES_TABLE) is None:
        op.create_table(
            SCHEDULES_TABLE,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("report_key", sa.String(40), nullable=False),
            sa.Column("filters_json", sa.Text(), nullable=True),
            sa.Column(
                "frequency",
                sa.String(20),
                nullable=False,
                server_default="daily",
            ),
            sa.Column(
                "timezone", sa.String(80), nullable=False, server_default="UTC"
            ),
            sa.Column("recipient_ids_json", sa.Text(), nullable=True),
            sa.Column(
                "output_format",
                sa.String(10),
                nullable=False,
                server_default="csv",
            ),
            sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint(SCHEDULE_KEY_CHECK, name="ck_report_schedule_key"),
            sa.CheckConstraint(FREQUENCY_CHECK, name="ck_report_schedule_frequency"),
            sa.CheckConstraint(FORMAT_CHECK, name="ck_report_schedule_format"),
        )
        print(f"[0053_report_schedules] created {SCHEDULES_TABLE}")
    else:
        print(f"[0053_report_schedules] {SCHEDULES_TABLE} already present; skipping")

    if catalog.table(RUNS_TABLE) is None:
        op.create_table(
            RUNS_TABLE,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("schedule_id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=True),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="failed",
            ),
            sa.Column("recipient_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("payload", sa.Text(), nullable=True),
            sa.Column("payload_format", sa.String(10), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint(RUN_STATUS_CHECK, name="ck_report_run_status"),
        )
        print(f"[0053_report_schedules] created {RUNS_TABLE}")
    else:
        print(f"[0053_report_schedules] {RUNS_TABLE} already present; skipping")

    for name, (table, columns) in INDEXES:
        if create_index_if_missing(name, table, list(columns)):
            print(f"[0053_report_schedules] created index {name}")
        else:
            print(f"[0053_report_schedules] index {name} already present; skipping")


def downgrade() -> None:
    for name, (table, _columns) in reversed(INDEXES):
        if drop_index_if_present(name, table):
            print(f"[0053_report_schedules] dropped index {name}")
    for table in (RUNS_TABLE, SCHEDULES_TABLE):
        if catalog_names(op.get_bind(), tables=[table]).table(table) is not None:
            op.drop_table(table)
            print(f"[0053_report_schedules] dropped {table}")
        else:
            print(f"[0053_report_schedules] {table} already absent; skipping")
