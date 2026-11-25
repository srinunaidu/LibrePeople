"""forecast_scenarios: add scenario tables for what-if forecasting

Revision ID: 0015_forecast_scenarios
Revises: 0006_forecast_run_location_role
Create Date: 2026-10-24

Creates scenario tables for what-if forecasting:
- forecast_scenarios: scenario metadata with assumptions
- forecast_scenario_results: per-period scenario results

These tables may already exist. A database created before Alembic existed
was built by ``Base.metadata.create_all()``, and an earlier revision of
this migration may have been applied by hand while the platform was being
set up. Creating the tables again raises ORA-00955, so each table is
checked first: a table that is already there is brought up to the shape
this revision expects rather than recreated, and the migration is a no-op
for the ones that are already correct.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_forecast_scenarios"
down_revision = "0006_forecast_run_location_role"
branch_labels = None
depends_on = None


#: The columns each table is made of, in the order they are created.
FORECAST_SCENARIOS_COLUMNS = [
    sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column("name", sa.String(200), nullable=False, index=True),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column(
        "base_run_id",
        sa.Integer(),
        sa.ForeignKey("forecast_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    sa.Column("assumptions", sa.Text(), nullable=False, server_default="[]"),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    ),
    sa.Column(
        "created_by",
        sa.Integer(),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    ),
]

FORECAST_SCENARIO_RESULTS_COLUMNS = [
    sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column(
        "scenario_id",
        sa.Integer(),
        sa.ForeignKey("forecast_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    sa.Column("series_key", sa.String(200), nullable=False, index=True),
    sa.Column("horizon_step", sa.Integer(), nullable=False),
    sa.Column(
        "forecast_date",
        sa.DateTime(timezone=True),
        nullable=False,
        index=True,
    ),
    sa.Column("predicted_value", sa.Numeric(14, 4), nullable=False),
    sa.Column("lower_bound", sa.Numeric(14, 4), nullable=True),
    sa.Column("upper_bound", sa.Numeric(14, 4), nullable=True),
    sa.Column("input_hash", sa.String(64), nullable=False, index=True),
    sa.Column("rule_version", sa.String(60), nullable=False),
    sa.Column("method_used", sa.String(50), nullable=False),
    sa.Column("data_start_date", sa.DateTime(timezone=True), nullable=True),
    sa.Column("data_end_date", sa.DateTime(timezone=True), nullable=True),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    ),
]


def _forecast_scenarios_constraints():
    return [sa.PrimaryKeyConstraint("id")]


def _forecast_scenario_results_constraints():
    return [
        sa.UniqueConstraint(
            "scenario_id",
            "series_key",
            "horizon_step",
            name="uq_forecast_scenario_series_horizon",
        )
    ]


def _columns(inspector, table: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table)}


def _ensure_columns(inspector, table: str, columns) -> None:
    """Add any column this revision expects that the table is missing.

    A table created by an earlier revision of this migration (or by
    ``create_all()`` against an older model) may not have every column.
    Adding the missing ones brings the table up to the shape the models
    expect without dropping data.
    """
    present = _columns(inspector, table)
    for column in columns:
        if column.name in present:
            continue
        # A column carrying a foreign key needs the constraint added
        # separately; ``add_column`` does not accept one.
        definition = column.copy()
        definition.foreign_keys = set()
        definition.index = False
        definition.unique = False
        op.add_column(table, definition)
        print(f"[0015_forecast_scenarios] added missing column {table}.{column.name}")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "forecast_scenarios" not in existing:
        op.create_table(
            "forecast_scenarios",
            *FORECAST_SCENARIOS_COLUMNS,
            *_forecast_scenarios_constraints(),
        )
    else:
        _ensure_columns(inspector, "forecast_scenarios", FORECAST_SCENARIOS_COLUMNS)

    if "forecast_scenario_results" not in existing:
        op.create_table(
            "forecast_scenario_results",
            *FORECAST_SCENARIO_RESULTS_COLUMNS,
            *_forecast_scenario_results_constraints(),
        )
    else:
        _ensure_columns(inspector, "forecast_scenario_results", FORECAST_SCENARIO_RESULTS_COLUMNS)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    for table in ("forecast_scenario_results", "forecast_scenarios"):
        if table in existing:
            op.drop_table(table)
