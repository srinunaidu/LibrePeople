"""fk_indexes: index every foreign key

Revision ID: 0008_fk_indexes
Revises: 0007_import_dry_runs
Create Date: 2026-10-21

Why
---
Oracle does not create an index for a foreign key. The consequence is that
every join and every lookup through a relationship — an employee's
department, a leave request's employee, a pay slip's pay run — is a full
table scan, and it gets worse as the tables grow. The audit's Block 2
finding is "index every foreign key and filter column".

What this revision does
-----------------------
It creates an index on every foreign-key column that does not already have
one. It adds nothing else: no columns, no constraints, no data.

Expand-then-contract
---------------------
Pure expansion. It adds indexes and it changes no column and no row, so it
can be applied before the release whose queries need it, and it can be
reverted by dropping the indexes it created without touching any data.

Every index this revision creates is dropped again by its downgrade, and
only those: the names are prefixed with ``ix_fk_``, which is a name no
model-generated index can have, so the downgrade can never take an index
that belongs to somebody else. A column that already had an index — because
it is ``index=True`` in the model, because a unique constraint implies one,
or because it is the leading column of the primary key — is left alone in
both directions. Oracle refuses a second index over a column list that is
already indexed (ORA-01408), so this is not an optimisation: it is what
keeps the revision applicable to a fresh database.

The table and the column are named as the catalog holds them. SQLAlchemy's
Oracle reflection lower-cases every identifier, and the catalog is mixed —
a table can be ``CASE_COMMENTS`` while a column is ``comment``, in lower
case and quoted — so a statement built from a reflected name can name an
object that does not exist.

Missing tables and columns
--------------------------
A table that does not exist yet is skipped, not created. A column that
does not exist yet — ``pay_runs.processed_by`` was added by a later
revision of the alignment migration, and ``leave_ledger`` is new work in
another lane — is skipped too. The revision is therefore safe to apply
against a database that is behind the models, which is what a deployment
that is mid-release looks like.

Oracle
------
Index names are capped at 30 characters, which is the limit older Oracle
releases impose. A longer name is truncated and a short hash of the
original is appended, so two long names never collide.
"""
from __future__ import annotations

import hashlib

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names

revision = "0008_fk_indexes"
down_revision = "0007_import_dry_runs"
branch_labels = None
depends_on = None


#: The foreign-key columns, as (table, column).
#:
#: The list is written out rather than derived from the models at run
#: time. A migration that reads the models is a migration that changes
#: meaning when a model changes; this one says exactly what it does.
FOREIGN_KEYS: tuple[tuple[str, str], ...] = (
    ("announcements", "created_by"),
    ("applications", "requisition_id"),
    ("applications", "candidate_id"),
    ("background_checks", "candidate_id"),
    ("benefit_enrollments", "employee_id"),
    ("benefit_enrollments", "plan_id"),
    ("case_comments", "case_id"),
    ("certifications", "employee_id"),
    ("client_settings", "client_id"),
    ("compensation_bands", "job_id"),
    ("compliance_checks", "rule_id"),
    ("compliance_violations", "employee_id"),
    ("compliance_violations", "rule_id"),
    ("continuous_feedback", "from_employee_id"),
    ("continuous_feedback", "to_employee_id"),
    ("cost_centers", "department_id"),
    ("course_enrollments", "employee_id"),
    ("course_enrollments", "course_id"),
    ("employee_directory", "employee_id"),
    ("employee_documents", "employee_id"),
    ("employee_files", "employee_id"),
    ("employee_pay_profiles", "employee_id"),
    ("employee_self_service", "employee_id"),
    ("employees", "job_id"),
    ("employees", "department_id"),
    ("employees", "manager_id"),
    ("feature_flags", "client_id"),
    ("forecast_results", "forecast_run_id"),
    ("goal_alignments", "goal_id"),
    ("goal_alignments", "parent_goal_id"),
    ("goals", "employee_id"),
    ("headcount_plans", "department_id"),
    ("hr_cases", "employee_id"),
    ("integrations", "client_id"),
    ("job_requisitions", "department_id"),
    ("job_requisitions", "job_id"),
    ("jobs", "department_id"),
    ("leave_balances", "employee_id"),
    ("leave_balances", "leave_type_id"),
    ("leave_ledger", "balance_id"),
    ("leave_ledger", "employee_id"),
    ("leave_ledger", "leave_type_id"),
    ("leave_ledger", "created_by"),
    ("leave_requests", "employee_id"),
    ("leave_requests", "leave_type_id"),
    ("leave_requests", "decided_by"),
    ("leaves_of_absence", "employee_id"),
    ("leaves_of_absence", "approved_by"),
    ("life_events", "employee_id"),
    ("merit_allocations", "cycle_id"),
    ("merit_allocations", "employee_id"),
    ("migration_jobs", "client_id"),
    ("migration_jobs", "integration_id"),
    ("notifications", "recipient_id"),
    ("offboarding_items", "termination_id"),
    ("offboarding_items", "task_id"),
    ("offers", "application_id"),
    ("offers", "job_id"),
    ("onboarding_documents", "employee_id"),
    ("onboarding_steps", "client_id"),
    ("onboarding_tasks", "employee_id"),
    ("org_chart_nodes", "employee_id"),
    ("org_chart_nodes", "manager_id"),
    ("pay_runs", "period_id"),
    ("pay_runs", "processed_by"),
    ("pay_runs", "approved_by"),
    ("pay_runs", "finalized_by"),
    ("pay_slips", "pay_run_id"),
    ("pay_slips", "employee_id"),
    ("performance_reviews", "employee_id"),
    ("performance_reviews", "reviewer_id"),
    ("positions", "job_id"),
    ("positions", "department_id"),
    ("positions", "location_id"),
    ("positions", "reports_to_position_id"),
    ("refresh_tokens", "user_id"),
    ("report_definitions", "created_by"),
    ("review_feedback", "review_id"),
    ("review_feedback", "from_employee_id"),
    ("roster_entries", "employee_id"),
    ("roster_entries", "shift_template_id"),
    ("saved_reports", "definition_id"),
    ("scenarios", "base_plan_id"),
    ("shift_swaps", "roster_entry_id"),
    ("shift_swaps", "requester_id"),
    ("shift_swaps", "target_id"),
    ("shift_swaps", "decided_by"),
    ("succession_plans", "position_id"),
    ("succession_plans", "primary_successor_id"),
    ("succession_plans", "backup_successor_id"),
    ("talent_pool_members", "pool_id"),
    ("talent_pool_members", "employee_id"),
    ("terminations", "employee_id"),
    ("terminations", "initiated_by"),
    ("terminations", "decided_by"),
    ("time_entries", "employee_id"),
    ("timesheets", "employee_id"),
    ("timesheets", "approved_by"),
    ("users", "employee_id"),
    ("webhook_deliveries", "webhook_id"),
)

#: The longest index name Oracle accepts without complaint.
MAX_NAME_LENGTH = 30


def index_name(table: str, column: str) -> str:
    """The name of the index on ``table.column``.

    The name is prefixed with ``ix_fk_`` so that it can never collide
    with an index the models create themselves — SQLAlchemy names those
    ``ix_<table>_<column>``. The distinction matters for the downgrade:
    it drops only the indexes this revision created, and a name that
    cannot be produced any other way is what makes that possible.

    Names longer than the limit are truncated and a short hash of the
    original is appended, so two different long names cannot collide.
    """
    name = f"ix_fk_{table}_{column}"
    if len(name) <= MAX_NAME_LENGTH:
        return name
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    keep = MAX_NAME_LENGTH - len(digest) - 1
    return f"{name[:keep]}_{digest}"


def _primary_key_columns(inspector, table: str) -> list[str]:
    """The columns the table's primary key is over.

    The primary key has an index behind it, and Oracle refuses a second
    index over a column list that is already indexed (ORA-01408). The
    reflection reports the primary key on its own — it is not one of the
    table's indexes and not one of its unique constraints — so it has to be
    asked for separately.
    """
    primary_key = inspector.get_pk_constraint(table) or {}
    return [str(name) for name in (primary_key.get("constrained_columns") or [])]


def _leading_columns(inspector, table: str) -> set[str]:
    """The columns that are the *first* column of some index."""
    leading: set[str] = set()
    for index in inspector.get_indexes(table):
        columns = index.get("column_names") or []
        if columns:
            leading.add(str(columns[0]).casefold())
    return leading


def _unique_constraints(inspector, table: str) -> set[str]:
    """The columns a unique constraint already indexes."""
    covered: set[str] = set()
    for constraint in inspector.get_unique_constraints(table):
        columns = [str(name).casefold() for name in (constraint.get("column_names") or [])]
        if columns:
            covered.add(columns[0])
    return covered


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # The table and the column are named as the catalog holds them. The
    # reflection lower-cases every identifier on Oracle, and the catalog is
    # mixed, so a statement built from a reflected name can name an object
    # that does not exist.
    catalog = catalog_names(bind)
    tables = {name.upper(): name for name in catalog.tables.values()}
    created: list[tuple[str, str]] = []

    for table, column in FOREIGN_KEYS:
        live_table = tables.get(table.upper())
        if live_table is None:
            print(f"[0008_fk_indexes] {table} is not present; skipping")
            continue
        live_column = catalog.column(live_table, column)
        if live_column is None:
            print(f"[0008_fk_indexes] {live_table}.{column} is not present; skipping")
            continue
        if column.casefold() in _leading_columns(inspector, live_table):
            continue
        if column.casefold() in _unique_constraints(inspector, live_table):
            # A unique constraint already has an index behind it.
            continue
        primary_key = _primary_key_columns(inspector, live_table)
        if primary_key and column.casefold() == primary_key[0].casefold():
            # The primary key already has an index behind it.
            continue
        name = index_name(table, column)
        op.create_index(name, live_table, [live_column])
        created.append((live_table, name))
        print(f"[0008_fk_indexes] created {name}")

    print(f"[0008_fk_indexes] {len(created)} indexes created")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    catalog = catalog_names(bind)
    tables = {name.upper(): name for name in catalog.tables.values()}
    dropped = 0

    for table, column in reversed(FOREIGN_KEYS):
        live_table = tables.get(table.upper())
        if live_table is None:
            continue
        name = index_name(table, column)
        existing = {
            str(index["name"]).casefold()
            for index in inspector.get_indexes(live_table)
            if index.get("name")
        }
        if name.casefold() not in existing:
            continue
        op.drop_index(name, table_name=live_table)
        dropped += 1
        print(f"[0008_fk_indexes] dropped {name}")

    print(f"[0008_fk_indexes] {dropped} indexes dropped")
