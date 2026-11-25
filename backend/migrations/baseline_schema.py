"""The frozen schema this platform started from, and how to create it.

Why the schema is frozen
------------------------
This product was deployed for a long time before Alembic existed: the schema
was built by ``Base.metadata.create_all()`` at application start. When Alembic
was adopted, the existing production database had to be brought under
migration control without rebuilding it.

The baseline migration therefore does not replay a list of ``CREATE TABLE``
statements. It creates the tables that existed at the moment Alembic was
adopted, using SQLAlchemy's own metadata so that:

* the DDL is generated for the **live dialect** (Oracle in production), so it
  is exactly the DDL ``create_all`` already ran successfully there; and
* the tables are created in **dependency order**, which Oracle requires —
  a table with a foreign key to a table that does not exist yet fails with
  ORA-02270.

The table list below is frozen on purpose. If a new model is added later, it
must not appear in the baseline: it belongs in a new, numbered migration. The
list is the boundary between "the schema we inherited" and "the schema we
have added since".
"""
from __future__ import annotations

from sqlalchemy import MetaData

#: Every table that existed when Alembic was adopted.
#:
#: Frozen deliberately. Do not add to this list. A new table belongs in a new
#: migration revision, where its creation is explicit and reviewable.
FROZEN_TABLES: frozenset[str] = frozenset(
    {
        "announcements",
        "applications",
        "audit_logs",
        "background_checks",
        "benefit_enrollments",
        "benefit_plans",
        "candidates",
        "case_comments",
        "certifications",
        "client_settings",
        "clients",
        "compensation_bands",
        "compliance_checks",
        "compliance_rules",
        "compliance_violations",
        "continuous_feedback",
        "cost_centers",
        "course_enrollments",
        "courses",
        "departments",
        "e_signatures",
        "employee_directory",
        "employee_documents",
        "employee_files",
        "employee_pay_profiles",
        "employee_self_service",
        "employees",
        "feature_flags",
        "goal_alignments",
        "goals",
        "headcount_plans",
        "hr_cases",
        "idempotency_records",
        "integrations",
        "job_requisitions",
        "jobs",
        "leave_balances",
        "leave_requests",
        "leave_types",
        "leaves_of_absence",
        "life_events",
        "locations",
        "merit_allocations",
        "merit_cycles",
        "migration_jobs",
        "notifications",
        "offboarding_items",
        "offboarding_tasks",
        "offers",
        "onboarding_documents",
        "onboarding_steps",
        "onboarding_tasks",
        "org_chart_nodes",
        "pay_components",
        "pay_runs",
        "pay_slips",
        "payroll_periods",
        "performance_reviews",
        "positions",
        "report_definitions",
        "review_feedback",
        "roster_entries",
        "saved_reports",
        "scenarios",
        "scim_tokens",
        "shift_swaps",
        "shift_templates",
        "sso_configs",
        "succession_plans",
        "talent_pool_members",
        "talent_pools",
        "terminations",
        "time_entries",
        "timesheets",
        "users",
        "webhook_deliveries",
        "webhooks",
    }
)


def _load_metadata() -> MetaData:
    """Return the application metadata with every model registered."""
    import importlib
    import pkgutil

    import app.models
    from app.core.database import Base
    from app.core.idempotency import IdempotencyRecord  # noqa: F401

    for _finder, name, _is_pkg in pkgutil.iter_modules(app.models.__path__):
        if name.startswith("_"):
            continue
        importlib.import_module(f"app.models.{name}")

    return Base.metadata


def frozen_tables() -> list:
    """The frozen table objects, in the order SQLAlchemy will create them.

    ``MetaData.create_all`` sorts the tables it is given into dependency order
    itself, so passing the list unsorted is safe.
    """
    metadata = _load_metadata()
    missing = FROZEN_TABLES - set(metadata.tables)
    if missing:
        raise RuntimeError(
            "The frozen baseline references tables that no longer exist in the "
            f"models: {sorted(missing)}. Either restore the model or amend the "
            "baseline deliberately in a new migration."
        )
    return [metadata.tables[name] for name in sorted(FROZEN_TABLES)]


def create_frozen_schema(bind) -> None:
    """Create every frozen table that is not already present."""
    metadata = _load_metadata()
    metadata.create_all(
        bind=bind,
        tables=frozen_tables(),
        checkfirst=True,
    )


def drop_frozen_schema(bind) -> None:
    """Drop every frozen table, in reverse dependency order.

    Used by the baseline's ``downgrade``. ``drop_all`` sorts the tables into
    reverse dependency order for the same reason ``create_all`` sorts them
    forwards.
    """
    metadata = _load_metadata()
    metadata.drop_all(
        bind=bind,
        tables=frozen_tables(),
        checkfirst=True,
    )
