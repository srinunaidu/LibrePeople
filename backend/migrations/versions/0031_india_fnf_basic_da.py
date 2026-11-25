"""india F&F + Basic/DA split (india-payroll slice 5)

Revision ID: 0031_india_fnf_basic_da
Revises: 0030_india_employee_fields
Create Date: 2026-11-18

What this adds
--------------
* ``employee_pay_profiles.basic_pct`` Numeric(5,2) nullable — the Basic+DA
  proportion of gross, CHECK 0..100 (validated by Pydantic and the model).
  When present the engine computes PF on Basic+DA (``basic_pct`` × gross)
  instead of on full gross; ESI stays on gross. Nullable so every row that
  predates the column — and every non-Indian tenant — stays readable, and the
  fallback remains gross (the v1 behaviour).

Idempotency / downgrade follow the 0030 pattern: inspect the catalog first,
skip what already exists, drop what this revision added on downgrade.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names, drop_index_if_present

revision = "0031_india_fnf_basic_da"
down_revision = "0030_india_employee_fields"
branch_labels = None
depends_on = None

BASIC_PCT_CHECK = "basic_pct IS NULL OR (basic_pct >= 0 AND basic_pct <= 100)"
PAY_PROFILES = "employee_pay_profiles"


def upgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[PAY_PROFILES])
    live_table = catalog.table(PAY_PROFILES)
    if live_table is None:
        print(f"[0031_india_fnf_basic_da] {PAY_PROFILES} is not present; skipping")
        return
    if catalog.column(live_table, "basic_pct") is not None:
        print(f"[0031_india_fnf_basic_da] {live_table}.basic_pct is already present; skipping")
        return
    op.add_column(
        live_table,
        sa.Column(
            "basic_pct",
            sa.Numeric(5, 2),
            sa.CheckConstraint(BASIC_PCT_CHECK, name="ck_employee_pay_profiles_basic_pct"),
            nullable=True,
        ),
    )
    print(f"[0031_india_fnf_basic_da] added {live_table}.basic_pct")


def downgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[PAY_PROFILES])
    live_table = catalog.table(PAY_PROFILES)
    if live_table is None:
        print(f"[0031_india_fnf_basic_da] {PAY_PROFILES} is not present; skipping")
        return
    live_column = catalog.column(live_table, "basic_pct")
    if live_column is None:
        print(f"[0031_india_fnf_basic_da] {live_table}.basic_pct is already absent; skipping")
        return
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(live_table):
        column_names = [str(c).casefold() for c in index.get("column_names") or []]
        if live_column.casefold() in column_names:
            drop_index_if_present(index["name"], live_table)
    op.drop_column(live_table, live_column)
    print(f"[0031_india_fnf_basic_da] dropped {live_table}.basic_pct")
