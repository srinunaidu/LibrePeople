"""forecasting: add location_id and role_id to forecast_runs

Revision ID: 0006_forecast_run_location_role
Revises: 0014_payslip_contributions
Create Date: 2026-10-24

Adds location_id and role_id foreign keys to forecast_runs table
to link forecasts to the scheduler.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_forecast_run_location_role"
down_revision = "0014_payslip_contributions"
branch_labels = None
depends_on = None


def _columns(inspector, table: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table)}


def _indexes(inspector, table: str) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "forecast_runs" not in existing:
        # Table doesn't exist - this migration shouldn't run independently
        # The 0005_forecasting migration creates the table
        return

    present = _columns(inspector, "forecast_runs")
    dialect = bind.dialect.name

    # Add location_id column
    if "location_id" not in present:
        if dialect == "sqlite":
            # SQLite: add column without FK, FK cannot be added via ALTER TABLE
            op.add_column(
                "forecast_runs",
                sa.Column("location_id", sa.Integer(), nullable=True),
            )
        else:
            # Oracle and others: add column with FK
            op.add_column(
                "forecast_runs",
                sa.Column(
                    "location_id",
                    sa.Integer(),
                    sa.ForeignKey("locations.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )
        print("[0006_forecast_run_location_role] added column forecast_runs.location_id")

    # Add role_id column
    if "role_id" not in present:
        if dialect == "sqlite":
            op.add_column(
                "forecast_runs",
                sa.Column("role_id", sa.Integer(), nullable=True),
            )
        else:
            op.add_column(
                "forecast_runs",
                sa.Column(
                    "role_id",
                    sa.Integer(),
                    sa.ForeignKey("jobs.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )
        print("[0006_forecast_run_location_role] added column forecast_runs.role_id")

    # Create indexes (the model defines index=True)
    present_indexes = _indexes(inspector, "forecast_runs")
    if "ix_forecast_runs_location_id" not in present_indexes:
        try:
            op.create_index("ix_forecast_runs_location_id", "forecast_runs", ["location_id"])
            print("[0006_forecast_run_location_role] created index ix_forecast_runs_location_id")
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise
    if "ix_forecast_runs_role_id" not in present_indexes:
        try:
            op.create_index("ix_forecast_runs_role_id", "forecast_runs", ["role_id"])
            print("[0006_forecast_run_location_role] created index ix_forecast_runs_role_id")
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "forecast_runs" not in existing:
        return

    present = _columns(inspector, "forecast_runs")

    # Drop indexes first (batch mode handles this for SQLite)
    present_indexes = _indexes(inspector, "forecast_runs")
    if "ix_forecast_runs_location_id" in present_indexes:
        op.drop_index("ix_forecast_runs_location_id", table_name="forecast_runs")
        print("[0006_forecast_run_location_role] dropped index ix_forecast_runs_location_id")
    if "ix_forecast_runs_role_id" in present_indexes:
        op.drop_index("ix_forecast_runs_role_id", table_name="forecast_runs")
        print("[0006_forecast_run_location_role] dropped index ix_forecast_runs_role_id")

    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("forecast_runs") as batch:
        if "location_id" in present:
            batch.drop_column("location_id")
            print("[0006_forecast_run_location_role] dropped column forecast_runs.location_id")
        if "role_id" in present:
            batch.drop_column("role_id")
            print("[0006_forecast_run_location_role] dropped column forecast_runs.role_id")
