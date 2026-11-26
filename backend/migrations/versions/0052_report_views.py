"""saved report views (reporting-personalization Part E)

Revision ID: 0052_report_views
Revises: 0051_er_cases
Create Date: 2026-11-26

What this adds
--------------
* ``report_saved_views`` — one row per named filter set: the tenant, the
  owning user, the display name, the allowlisted report key
  (joiners/leavers/attrition/payroll-summary), the stored filters as JSON
  text, and the visibility (``personal`` or ``shared``).

Expand-only
-----------
Pure expansion: one new table and its index, no column of an existing
table changes, so it applies cleanly on a database that already holds
data. The downgrade removes exactly what the upgrade created.

Idempotency
-----------
The upgrade asks the catalog first (the 0037/0050/0051 pattern): a database
the current models already built via ``create_all()`` carries the table, so
the upgrade skips it there. Re-running is a no-op.

Postgres cleanliness
--------------------
No database enum anywhere: ``report_key`` and ``visibility`` are plain
``String`` columns with CHECK constraints. Indexes are created only when
missing. The migration imports no model.

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

revision = "0052_report_views"
down_revision = "0051_er_cases"
branch_labels = None
depends_on = None

VIEWS_TABLE = "report_saved_views"

REPORT_KEY_CHECK = (
    "report_key IN ('joiners','leavers','attrition','payroll-summary')"
)
VISIBILITY_CHECK = "visibility IN ('personal','shared')"

INDEXES = (
    ("ix_report_saved_views_tenant_owner", (VIEWS_TABLE, ("tenant_id", "owner_id"))),
)


def upgrade() -> None:
    catalog = catalog_names(op.get_bind(), tables=[VIEWS_TABLE])

    if catalog.table(VIEWS_TABLE) is None:
        op.create_table(
            VIEWS_TABLE,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("report_key", sa.String(40), nullable=False),
            sa.Column("filters_json", sa.Text(), nullable=True),
            sa.Column(
                "visibility",
                sa.String(20),
                nullable=False,
                server_default="personal",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint(REPORT_KEY_CHECK, name="ck_report_view_key"),
            sa.CheckConstraint(VISIBILITY_CHECK, name="ck_report_view_visibility"),
        )
        print(f"[0052_report_views] created {VIEWS_TABLE}")
    else:
        print(f"[0052_report_views] {VIEWS_TABLE} already present; skipping")

    for name, (table, columns) in INDEXES:
        if create_index_if_missing(name, table, list(columns)):
            print(f"[0052_report_views] created index {name}")
        else:
            print(f"[0052_report_views] index {name} already present; skipping")


def downgrade() -> None:
    for name, (table, _columns) in reversed(INDEXES):
        if drop_index_if_present(name, table):
            print(f"[0052_report_views] dropped index {name}")
    if catalog_names(op.get_bind(), tables=[VIEWS_TABLE]).table(VIEWS_TABLE) is not None:
        op.drop_table(VIEWS_TABLE)
        print(f"[0052_report_views] dropped {VIEWS_TABLE}")
    else:
        print(f"[0052_report_views] {VIEWS_TABLE} already absent; skipping")
