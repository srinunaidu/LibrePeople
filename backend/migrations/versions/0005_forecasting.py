"""forecasting: add forecasting tables

Revision ID: 0005_forecasting
Revises: 0004_job_queue
Create Date: 2026-10-20

Creates forecasting tables:
- forecast_runs: forecast run metadata
- forecast_results: individual forecast results per series/horizon
- forecast_model_versions: model version tracking

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

revision = "0005_forecasting"
down_revision = "0004_job_queue"
branch_labels = None
depends_on = None


#: The columns each table is made of, in the order they are created.
FORECAST_RUNS_COLUMNS = [
    sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column("name", sa.String(200), nullable=False, index=True),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("horizon_days", sa.Integer(), nullable=False, default=30),
    sa.Column("method", sa.String(50), nullable=False, default="auto"),
    sa.Column("data_start_date", sa.DateTime(timezone=True), nullable=True),
    sa.Column("data_end_date", sa.DateTime(timezone=True), nullable=True),
    sa.Column("backtest_mape", sa.Numeric(6, 4), nullable=True),
    sa.Column("backtest_mase", sa.Numeric(6, 4), nullable=True),
    sa.Column("backtest_holdout_days", sa.Integer(), nullable=True),
    sa.Column("status", sa.String(20), nullable=False, default="pending"),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    ),
    sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
]

FORECAST_RESULTS_COLUMNS = [
    sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column(
        "forecast_run_id",
        sa.Integer(),
        sa.ForeignKey("forecast_runs.id", ondelete="CASCADE"),
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

FORECAST_MODEL_VERSIONS_COLUMNS = [
    sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column("version", sa.String(60), nullable=False, unique=True),
    sa.Column("method", sa.String(50), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("parameters", sa.Text(), nullable=True),
    sa.Column("is_active", sa.Boolean(), nullable=False, default=True, index=True),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    ),
]


def _forecast_runs_constraints():
    return [sa.PrimaryKeyConstraint("id")]


def _forecast_results_constraints():
    # The foreign key is declared on the column above and must not be
    # repeated here: two constraints with the same auto-generated name are
    # rejected by Oracle with ORA-00955.
    return [
        sa.UniqueConstraint(
            "forecast_run_id",
            "series_key",
            "horizon_step",
            name="uq_forecast_run_series_horizon",
        )
    ]


def _forecast_model_versions_constraints():
    return [sa.PrimaryKeyConstraint("id")]


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
        print(f"[0005_forecasting] added missing column {table}.{column.name}")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "forecast_runs" not in existing:
        op.create_table(
            "forecast_runs",
            *FORECAST_RUNS_COLUMNS,
            *_forecast_runs_constraints(),
        )
    else:
        _ensure_columns(inspector, "forecast_runs", FORECAST_RUNS_COLUMNS)

    if "forecast_results" not in existing:
        op.create_table(
            "forecast_results",
            *FORECAST_RESULTS_COLUMNS,
            *_forecast_results_constraints(),
        )
    else:
        _ensure_columns(inspector, "forecast_results", FORECAST_RESULTS_COLUMNS)

    if "forecast_model_versions" not in existing:
        op.create_table(
            "forecast_model_versions",
            *FORECAST_MODEL_VERSIONS_COLUMNS,
            *_forecast_model_versions_constraints(),
        )
    else:
        _ensure_columns(
            inspector, "forecast_model_versions", FORECAST_MODEL_VERSIONS_COLUMNS
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    for table in ("forecast_model_versions", "forecast_results", "forecast_runs"):
        if table in existing:
            op.drop_table(table)
