"""time corrections and attendance period locks (LP-TIME-004+005)

Revision ID: 0035_time_corrections_locks
Revises: 0034_pg_foundations
Create Date: 2026-11-21

What this adds
--------------
* ``time_correction_requests`` — an employee's request to fix a clock
  record. The request never edits the entry directly; a manager approves
  or rejects it, and the approval applies the requested times.
* ``attendance_period_locks`` — a locked attendance period. Every time
  write (clock in/out, manual entry create/update/delete, timesheet
  generation, correction create/approve) refuses a work day that falls
  inside a locked period.

Expand-then-contract
--------------------
Pure expansion. It creates two tables and their indexes and changes no
column of an existing table, so it can be applied before the release
whose code needs it. The downgrade removes exactly what the upgrade
created: each table is dropped only when it is present, and each index
only when it is there.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import (
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0035_time_corrections_locks"
down_revision = "0034_pg_foundations"
branch_labels = None
depends_on = None

CORRECTIONS = "time_correction_requests"
LOCKS = "attendance_period_locks"

CORRECTION_INDEXES = (
    ("ix_time_correction_requests_tenant_id", (CORRECTIONS, ("tenant_id",))),
    ("ix_time_correction_requests_employee_id", (CORRECTIONS, ("employee_id",))),
    ("ix_time_correction_requests_work_date", (CORRECTIONS, ("work_date",))),
)

LOCK_INDEXES = (
    ("ix_attendance_period_locks_tenant_id", (LOCKS, ("tenant_id",))),
    ("ix_attendance_period_locks_period_start", (LOCKS, ("period_start",))),
    ("ix_attendance_period_locks_period_end", (LOCKS, ("period_end",))),
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()

    if CORRECTIONS not in existing:
        op.create_table(
            CORRECTIONS,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("time_entry_id", sa.Integer(), nullable=True),
            sa.Column("work_date", sa.Date(), nullable=False),
            sa.Column("requested_clock_in", sa.DateTime(timezone=True), nullable=True),
            sa.Column("requested_clock_out", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="Pending"),
            sa.Column("requested_by", sa.Integer(), nullable=True),
            sa.Column("decided_by", sa.Integer(), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        print(f"[0035_time_corrections_locks] created {CORRECTIONS}")
    else:
        print(f"[0035_time_corrections_locks] {CORRECTIONS} already present; skipping")

    if LOCKS not in existing:
        op.create_table(
            LOCKS,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("locked_by", sa.Integer(), nullable=True),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reopened_by", sa.Integer(), nullable=True),
            sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        print(f"[0035_time_corrections_locks] created {LOCKS}")
    else:
        print(f"[0035_time_corrections_locks] {LOCKS} already present; skipping")

    for name, (table, columns) in CORRECTION_INDEXES + LOCK_INDEXES:
        if create_index_if_missing(name, table, list(columns)):
            print(f"[0035_time_corrections_locks] created index {name}")
        else:
            print(f"[0035_time_corrections_locks] index {name} already present; skipping")


def downgrade() -> None:
    for name, (table, _columns) in LOCK_INDEXES + CORRECTION_INDEXES:
        if drop_index_if_present(name, table):
            print(f"[0035_time_corrections_locks] dropped index {name}")

    existing = _tables()
    for table in (LOCKS, CORRECTIONS):
        if table in existing:
            op.drop_table(table)
            print(f"[0035_time_corrections_locks] dropped {table}")
        else:
            print(f"[0035_time_corrections_locks] {table} already absent; skipping")
