"""forecast_costs: stored, versioned labour cost forecasts (AN-04)

Revision ID: 0017_forecast_costs
Revises: 0016_attendance_roster_link
Create Date: 2026-10-24

Creates two tables:
- forecast_costs: one row per version of a cost forecast of a run
- forecast_cost_rows: per-period (month) x location x role cost lines

Both are additive; each is created only when missing, so a database that
was built by ``create_all()`` — or by an earlier hand-run of this
revision — is adopted without complaint.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_forecast_costs"
down_revision = "0016_attendance_roster_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    # --- 1. forecast_costs ---------------------------------------------- #
    if "forecast_costs" not in existing:
        op.create_table(
            "forecast_costs",
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column(
                "forecast_run_id",
                sa.Integer(),
                sa.ForeignKey("forecast_runs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("hourly_costs", sa.Text(), nullable=False),
            sa.Column("input_hash", sa.String(64), nullable=False),
            sa.Column("excludes_statutory", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column(
                "created_by",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint("forecast_run_id", "version", name="uq_forecast_cost_run_version"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_forecast_costs_forecast_run_id", "forecast_costs", ["forecast_run_id"])
        op.create_index("ix_forecast_costs_input_hash", "forecast_costs", ["input_hash"])
        op.create_index("ix_costs_created_by", "forecast_costs", ["created_by"])
        print("[0017_forecast_costs] created table forecast_costs")

    # --- 2. forecast_cost_rows ------------------------------------------ #
    if "forecast_cost_rows" not in existing:
        op.create_table(
            "forecast_cost_rows",
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column(
                "cost_forecast_id",
                sa.Integer(),
                sa.ForeignKey("forecast_costs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("period", sa.String(7), nullable=False),
            sa.Column(
                "location_id",
                sa.Integer(),
                sa.ForeignKey("locations.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("location_code", sa.String(50), nullable=True),
            sa.Column(
                "role_id",
                sa.Integer(),
                sa.ForeignKey("jobs.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("role", sa.String(200), nullable=True),
            sa.Column("role_code", sa.String(50), nullable=True),
            sa.Column("hours", sa.Numeric(14, 4), nullable=False),
            sa.Column("hourly_cost", sa.Numeric(14, 4), nullable=False),
            sa.Column("cost", sa.Numeric(14, 4), nullable=False),
            sa.UniqueConstraint(
                "cost_forecast_id", "period", "location_id", "role_id",
                name="uq_forecast_cost_row",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_forecast_cost_rows_cost_forecast_id", "forecast_cost_rows", ["cost_forecast_id"])
        op.create_index("ix_forecast_cost_rows_period", "forecast_cost_rows", ["period"])
        op.create_index("ix_forecast_rows_location_id", "forecast_cost_rows", ["location_id"])
        op.create_index("ix_forecast_rows_role_id", "forecast_cost_rows", ["role_id"])
        print("[0017_forecast_costs] created table forecast_cost_rows")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "forecast_cost_rows" in existing:
        op.drop_table("forecast_cost_rows")
        print("[0017_forecast_costs] dropped table forecast_cost_rows")

    if "forecast_costs" in existing:
        op.drop_table("forecast_costs")
        print("[0017_forecast_costs] dropped table forecast_costs")
