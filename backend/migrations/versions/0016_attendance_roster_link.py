"""attendance: link time entries to the published roster (SC-05)

Revision ID: 0016_attendance_roster_link
Revises: 0015_forecast_scenarios
Create Date: 2026-10-24

1. Adds ``time_entries.roster_entry_id`` so every clock-in/out can be traced
   to the published roster entry it filled.
2. Creates the ``working_time_violations`` table — the record of detected
   breaches (early/late arrival, early/late departure, a missing entry, an
   entry with no scheduled shift).

Both changes are additive and nullable: nothing is destroyed, and a
database that was built by ``create_all()`` without this history is
adopted without complaint.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016_attendance_roster_link"
down_revision = "0015_forecast_scenarios"
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

    # --- 1. time_entries.roster_entry_id -------------------------------- #
    if "roster_entries" not in existing or "time_entries" not in existing:
        # The tables this migration links do not exist yet; the numbered
        # revision that creates them will run first. Nothing to add here.
        print("[0016_attendance_roster_link] time_entries/roster_entries missing; nothing to do")
        return

    present = _columns(inspector, "time_entries")
    dialect = bind.dialect.name

    if "roster_entry_id" not in present:
        if dialect == "sqlite":
            # SQLite: add the column, then take the constraint in batch mode
            op.add_column(
                "time_entries",
                sa.Column("roster_entry_id", sa.Integer(), nullable=True),
            )
        else:
            # Oracle and others: add the column with its foreign key
            op.add_column(
                "time_entries",
                sa.Column(
                    "roster_entry_id",
                    sa.Integer(),
                    sa.ForeignKey("roster_entries.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )
        print("[0016_attendance_roster_link] added column time_entries.roster_entry_id")

    present_indexes = _indexes(inspector, "time_entries")
    if "ix_time_entries_roster_entry_id" not in present_indexes:
        op.create_index(
            "ix_time_entries_roster_entry_id",
            "time_entries",
            ["roster_entry_id"],
        )
        print("[0016_attendance_roster_link] created index ix_time_entries_roster_entry_id")

    # --- 2. working_time_violations table ------------------------------ #
    if "working_time_violations" not in existing:
        op.create_table(
            "working_time_violations",
            sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
            sa.Column(
                "employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False
            ),
            sa.Column("work_date", sa.Date(), nullable=False),
            sa.Column(
                "roster_entry_id",
                sa.Integer(),
                sa.ForeignKey("roster_entries.id"),
                nullable=True,
            ),
            sa.Column("time_entry_id", sa.Integer(), sa.ForeignKey("time_entries.id"), nullable=True),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("severity", sa.String(10), nullable=False),
            sa.Column("minutes", sa.Integer(), nullable=True, server_default="0"),
            sa.Column(
                "detected_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            # PG-strictness: Boolean defaults must be TRUE/FALSE, not 0/1.
            # sa.text("0") emits DEFAULT 0, which PostgreSQL rejects for a
            # boolean column ("column is of type boolean but default
            # expression is of type integer"). sa.false() renders DEFAULT
            # false on PG and 0 on SQLite — behavior-neutral on SQLite,
            # matching the model's default=False (unresolved).
            sa.Column("resolved", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.CheckConstraint(
                "kind IN ('early_arrival','late_arrival','early_departure',"
                "'late_departure','missing_entry','extra_entry')",
                name="ck_wtv_kind",
            ),
            sa.CheckConstraint(
                "severity IN ('info','warning','critical')",
                name="ck_wtv_severity",
            ),
        )
        op.create_index(
            "ix_working_time_violations_employee_id",
            "working_time_violations",
            ["employee_id"],
        )
        op.create_index(
            "ix_working_time_violations_work_date",
            "working_time_violations",
            ["work_date"],
        )
        op.create_index(
            "ix_working_time_violations_roster_entry_id",
            "working_time_violations",
            ["roster_entry_id"],
        )
        print("[0016_attendance_roster_link] created table working_time_violations")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    # --- 2. working_time_violations (drop the whole table) -------------- #
    if "working_time_violations" in existing:
        ix = _indexes(inspector, "working_time_violations")
        for name in (
            "ix_working_time_violations_roster_entry_id",
            "ix_working_time_violations_work_date",
            "ix_working_time_violations_employee_id",
        ):
            if name in ix:
                op.drop_index(name, table_name="working_time_violations")
        op.drop_table("working_time_violations")
        print("[0016_attendance_roster_link] dropped table working_time_violations")

    # --- 1. time_entries.roster_entry_id -------------------------------- #
    if "time_entries" not in existing:
        return

    present = _columns(inspector, "time_entries")
    present_indexes = _indexes(inspector, "time_entries")

    if "ix_time_entries_roster_entry_id" in present_indexes:
        op.drop_index("ix_time_entries_roster_entry_id", table_name="time_entries")
        print("[0016_attendance_roster_link] dropped index ix_time_entries_roster_entry_id")

    if "roster_entry_id" in present:
        # Batch mode handles SQLite's LIMITATIONS on ALTER TABLE DROP COLUMN
        with op.batch_alter_table("time_entries") as batch:
            batch.drop_column("roster_entry_id")
        print("[0016_attendance_roster_link] dropped column time_entries.roster_entry_id")
