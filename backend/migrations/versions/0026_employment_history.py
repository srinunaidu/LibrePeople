"""employment_history: effective-dated employment changes and lifecycle fields

Revision ID: 0026_employment_history
Revises: 0025_job_result_payload
Create Date: 2026-10-27

The employee record held one current value per field and no record of how it
got there. "When did this person leave?" and "what was their salary before
the last change?" had no answer, and a lifecycle move (Active → Terminated)
was an overwrite with no rule about which moves were legal.

This revision adds the two date-bearing fields the employment record needs and
the append-only history table. A history row names the field, the previous and
the new value, the first day the new value was in force, the day it stopped
(``effective_to``, exclusive; null means still in force), the reason, the actor
and when it was written.

There is no backfill. The history begins with the feature; inventing rows for
changes that were never recorded would be fiction. The employee record's
current columns remain the state in force today.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0026_employment_history"
down_revision = "0025_job_result_payload"
branch_labels = None
depends_on = None

EMPLOYEES = "employees"
HISTORY = "employee_history"


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    columns = _columns(EMPLOYEES)
    if "employment_type" not in columns:
        op.add_column(
            EMPLOYEES, sa.Column("employment_type", sa.String(30), nullable=True)
        )
    if "termination_date" not in columns:
        op.add_column(
            EMPLOYEES, sa.Column("termination_date", sa.Date(), nullable=True)
        )

    if not _has_table(HISTORY):
        op.create_table(
            HISTORY,
            sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
            sa.Column(
                "employee_id",
                sa.Integer(),
                sa.ForeignKey("employees.id"),
                nullable=False,
            ),
            sa.Column("field", sa.String(40), nullable=False),
            sa.Column("previous_value", sa.String(255), nullable=True),
            sa.Column("new_value", sa.String(255), nullable=True),
            sa.Column("effective_from", sa.Date(), nullable=False),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("reason", sa.String(500), nullable=True),
            sa.Column("changed_by", sa.String(100), nullable=True),
            sa.Column(
                "changed_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_employee_history_employee_id", HISTORY, ["employee_id"]
        )
        op.create_index(
            "ix_employee_history_employee_field_from",
            HISTORY,
            ["employee_id", "field", "effective_from"],
        )


def downgrade() -> None:
    if _has_table(HISTORY):
        op.drop_table(HISTORY)
    columns = _columns(EMPLOYEES)
    with op.batch_alter_table(EMPLOYEES) as batch:
        if "termination_date" in columns:
            batch.drop_column("termination_date")
        if "employment_type" in columns:
            batch.drop_column("employment_type")
