"""forecast_accuracy_records: forecast-vs-actual accuracy history (AN-06)

Revision ID: 0019_forecast_accuracy
Revises: 0018_scenario_versions
Create Date: 2026-10-24

Creates one table:

- forecast_accuracy_records: one row per (forecast run, month period,
  location, role) pair that compares the run's forecast hours with the
  actual hours measured for the same window, carrying MAPE, MAE, bias,
  the sample size the metrics were computed from, and a confidence
  status ("ok", "review", "degraded").

The revision is additive; the table is created only when missing, so a
database that was built by ``create_all()`` -- or by an earlier hand-run
of this revision -- is adopted without complaint.

NOTE: renumbered at merge coordination. The AN-05 lane shipped its
scenario-versioning revision as ``0018_scenario_versions``, so this
revision became ``0019`` and re-points at it; keeping
``down_revision`` a single module-level constant makes that a
one-line change.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_forecast_accuracy"

#: Renumbering a colliding revision means changing this constant (and
#: ``revision`` above) and letting alembic's own graph sort the rest.
PREVIOUS_REVISION = "0018_scenario_versions"
down_revision = PREVIOUS_REVISION

branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "forecast_accuracy_records" not in existing:
        op.create_table(
            "forecast_accuracy_records",
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column(
                "forecast_run_id",
                sa.Integer(),
                sa.ForeignKey("forecast_runs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("model_version", sa.String(60), nullable=False),
            sa.Column("method_used", sa.String(50), nullable=False),
            sa.Column("period", sa.String(7), nullable=False),
            sa.Column(
                "location_id",
                sa.Integer(),
                sa.ForeignKey("locations.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "role_id",
                sa.Integer(),
                sa.ForeignKey("jobs.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("forecast_hours", sa.Numeric(14, 4), nullable=False),
            sa.Column("actual_hours", sa.Numeric(14, 4), nullable=False),
            sa.Column("mape", sa.Numeric(10, 6), nullable=True),
            sa.Column("mae", sa.Numeric(14, 4), nullable=False),
            sa.Column("bias", sa.Numeric(14, 4), nullable=False),
            sa.Column("sample_size", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column(
                "measured_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "forecast_run_id", "period", "location_id", "role_id",
                name="uq_forecast_accuracy_row",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_forecast_accuracy_run_id", "forecast_accuracy_records", ["forecast_run_id"]
        )
        op.create_index(
            "ix_forecast_accuracy_period", "forecast_accuracy_records", ["period"]
        )
        op.create_index(
            "ix_forecast_accuracy_status", "forecast_accuracy_records", ["status"]
        )
        op.create_index(
            "ix_forecast_accuracy_location_id", "forecast_accuracy_records", ["location_id"]
        )
        op.create_index(
            "ix_forecast_accuracy_role_id", "forecast_accuracy_records", ["role_id"]
        )
        print("[0019_forecast_accuracy] created table forecast_accuracy_records")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "forecast_accuracy_records" in existing:
        op.drop_table("forecast_accuracy_records")
        print("[0019_forecast_accuracy] dropped table forecast_accuracy_records")
