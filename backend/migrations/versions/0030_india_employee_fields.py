"""india_employee_fields: the India payroll data model (india-payroll slice 1)

Revision ID: 0030_india_employee_fields
Revises: 0029_schema_drift_fix
Create Date: 2026-11-18

What this adds
--------------
* ``employees.pan_number`` VARCHAR(10) nullable — Permanent Account Number,
  CHECK `^[A-Z]{5}[0-9]{4}[A-Z]$`;
* ``employees.tax_regime`` VARCHAR(10) NOT NULL, server default ``'new'``,
  CHECK ``IN ('new','old')`` — the accepted decision is new regime (§115BAC)
  only, so every existing row reads back ``'new'``;
* ``employees.pf_uan`` VARCHAR(12) nullable — EPF Universal Account Number;
* ``employees.esi_number`` VARCHAR(17) nullable — ESI registration number;
* ``employees.ifsc_code`` VARCHAR(11) nullable — bank branch IFSC, CHECK
  `^[A-Z]{4}0[A-Z0-9]{6}$`;
* ``employee_pay_profiles.pt_state`` VARCHAR(2) nullable, CHECK
  ``IN ('KA','MH','TN','TG','WB')`` — the professional-tax state the rule
  pack's PT tables are picked by;
* ``clients.country_code`` VARCHAR(2) nullable — the ISO code the rule-pack
  loader selects by, backfilled from ``clients.country`` where that column
  already holds a two-letter upper-case code.

Backfill
--------
``tax_regime`` needs no explicit UPDATE: it is added NOT NULL with the
server default ``'new'``, so every existing row already reads back the
accepted decision. ``country_code`` is backfilled with one UPDATE guarded by
``country_code IS NULL``, which also makes the backfill re-runnable.

The CHECK texts mirror the models (``app/models/employee.py``,
``app/models/payroll.py``) literally — the 0029 pattern — because Alembic
executes every revision module while it reads the chain, so a model import
from a revision would build the application engine at read time.
The texts are plain ``length`` / ``substr`` / ``BETWEEN`` expressions: one
text has to compile on SQLite (the test suites) and on Oracle (production),
and ``regexp_like`` does not exist on SQLite while ``GLOB`` does not exist
on Oracle. They enforce exactly the patterns named in the contract for the
[A-Z]/[0-9] character classes those patterns use.

Idempotency
-----------
Every add asks the catalog first (the 0029 pattern): a database the baseline
already built from the current models carries the columns, so the upgrade
skips them there, and a database that predates them gets them. Re-running
the revision is a no-op.

Downgrade
---------
Drops the seven columns this revision adds (the five India employee fields,
``pt_state`` and ``country_code``), dropping any index that references a
column first, SQLite style, as 0029 does. None of the columns is indexed,
so no index drop is expected; the guard is there anyway.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names, drop_index_if_present

revision = "0030_india_employee_fields"
down_revision = "0029_schema_drift_fix"
branch_labels = None
depends_on = None

# The CHECK texts mirror the models exactly — the 0029 pattern. They are
# NOT imported from ``app.models``: Alembic executes every revision module
# while it reads the chain, long before any database is configured, and a
# model import would build the application engine at read time. The
# schema-drift and schema-alignment suites (and the checks in
# ``india_payroll_test_suite.py``) keep the two honest.
#
# The texts are plain ``length`` / ``substr`` / ``BETWEEN`` expressions so
# one text compiles on SQLite (the test suites) and on Oracle (production):
# ``regexp_like`` does not exist on SQLite and ``GLOB`` does not exist on
# Oracle. They enforce exactly the patterns the contract names, for the
# [A-Z]/[0-9] classes those patterns use.
PAN_NUMBER_CHECK = (
    "pan_number IS NULL OR (length(pan_number) = 10 "
    "AND substr(pan_number,1,1) BETWEEN 'A' AND 'Z' "
    "AND substr(pan_number,2,1) BETWEEN 'A' AND 'Z' "
    "AND substr(pan_number,3,1) BETWEEN 'A' AND 'Z' "
    "AND substr(pan_number,4,1) BETWEEN 'A' AND 'Z' "
    "AND substr(pan_number,5,1) BETWEEN 'A' AND 'Z' "
    "AND substr(pan_number,6,1) BETWEEN '0' AND '9' "
    "AND substr(pan_number,7,1) BETWEEN '0' AND '9' "
    "AND substr(pan_number,8,1) BETWEEN '0' AND '9' "
    "AND substr(pan_number,9,1) BETWEEN '0' AND '9' "
    "AND substr(pan_number,10,1) BETWEEN 'A' AND 'Z')"
)
TAX_REGIME_CHECK = "tax_regime IN ('new','old')"
IFSC_CODE_CHECK = (
    "ifsc_code IS NULL OR (length(ifsc_code) = 11 "
    "AND substr(ifsc_code,1,1) BETWEEN 'A' AND 'Z' "
    "AND substr(ifsc_code,2,1) BETWEEN 'A' AND 'Z' "
    "AND substr(ifsc_code,3,1) BETWEEN 'A' AND 'Z' "
    "AND substr(ifsc_code,4,1) BETWEEN 'A' AND 'Z' "
    "AND substr(ifsc_code,5,1) = '0' "
    "AND (substr(ifsc_code,6,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,6,1) BETWEEN 'A' AND 'Z') "
    "AND (substr(ifsc_code,7,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,7,1) BETWEEN 'A' AND 'Z') "
    "AND (substr(ifsc_code,8,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,8,1) BETWEEN 'A' AND 'Z') "
    "AND (substr(ifsc_code,9,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,9,1) BETWEEN 'A' AND 'Z') "
    "AND (substr(ifsc_code,10,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,10,1) BETWEEN 'A' AND 'Z') "
    "AND (substr(ifsc_code,11,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,11,1) BETWEEN 'A' AND 'Z'))"
)
PT_STATE_CHECK = "pt_state IN ('KA','MH','TN','TG','WB')"

EMPLOYEES = "employees"
PAY_PROFILES = "employee_pay_profiles"
CLIENTS = "clients"

#: The columns this revision adds, keyed by table. The downgrade drops all
#: of them, so the list is the single place that has to agree both ways.
INDIA_COLUMNS: dict[str, dict[str, sa.Column]] = {
    EMPLOYEES: {
        "pan_number": sa.Column(
            "pan_number",
            sa.String(10),
            sa.CheckConstraint(PAN_NUMBER_CHECK, name="ck_employees_pan_number"),
            nullable=True,
        ),
        "tax_regime": sa.Column(
            "tax_regime",
            sa.String(10),
            sa.CheckConstraint(TAX_REGIME_CHECK, name="ck_employees_tax_regime"),
            nullable=False,
            server_default=sa.text("'new'"),
        ),
        "pf_uan": sa.Column("pf_uan", sa.String(12), nullable=True),
        "esi_number": sa.Column("esi_number", sa.String(17), nullable=True),
        "ifsc_code": sa.Column(
            "ifsc_code",
            sa.String(11),
            sa.CheckConstraint(IFSC_CODE_CHECK, name="ck_employees_ifsc_code"),
            nullable=True,
        ),
    },
    PAY_PROFILES: {
        "pt_state": sa.Column(
            "pt_state",
            sa.String(2),
            sa.CheckConstraint(PT_STATE_CHECK, name="ck_employee_pay_profiles_pt_state"),
            nullable=True,
        ),
    },
    CLIENTS: {
        "country_code": sa.Column("country_code", sa.String(2), nullable=True),
    },
}

#: The ISO-like shape the backfill accepts in ``clients.country``. SQLite
#: has no regexp function and Oracle has no GLOB, so the predicate is
#: written per dialect; this is DML, not schema, so the two spellings live
#: here rather than in the models.
COUNTRY_CODE_PREDICATES = {
    "sqlite": "country GLOB '[A-Z][A-Z]'",
    "oracle": "REGEXP_LIKE(country, '^[A-Z]{2}$')",
}


def _add_missing_columns(table: str, columns: dict[str, sa.Column]) -> str | None:
    """Add each column the live table does not have.

    Returns the catalog's name for the table, or ``None`` when the table is
    not present.
    """
    catalog = catalog_names(op.get_bind(), tables=[table])
    live_table = catalog.table(table)
    if live_table is None:
        print(f"[0030_india_employee_fields] {table} is not present; skipping")
        return None

    for name, definition in columns.items():
        if catalog.column(live_table, name) is not None:
            print(
                f"[0030_india_employee_fields] {live_table}.{name} is already "
                "present; skipping"
            )
            continue
        op.add_column(live_table, definition)
        print(f"[0030_india_employee_fields] added {live_table}.{name}")
    return live_table


def _backfill_country_code() -> None:
    """Copy the ISO-like values of ``clients.country`` into ``country_code``.

    The UPDATE is guarded by ``country_code IS NULL`` so it only ever fills
    what is missing: re-running the revision (or a re-run after a partial
    failure) does not overwrite a code that is already there.
    """
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[CLIENTS])
    live_table = catalog.table(CLIENTS)
    if live_table is None:
        print(f"[0030_india_employee_fields] {CLIENTS} is not present; skipping backfill")
        return
    if catalog.column(live_table, "country_code") is None:
        # The column was not added here (a future revision owns it); leave
        # the backfill to whoever adds it.
        return

    predicate = COUNTRY_CODE_PREDICATES.get(bind.dialect.name)
    if predicate is None:
        # An unknown dialect gets the explicit SQL-standard spelling.
        predicate = (
            "length(country) = 2 AND upper(country) = country "
            "AND substr(country,1,1) BETWEEN 'A' AND 'Z' "
            "AND substr(country,2,1) BETWEEN 'A' AND 'Z'"
        )

    quoted_table = f'"{live_table}"'
    quoted_column = f'"{catalog.column(live_table, "country_code")}"'
    bind.exec_driver_sql(
        f"UPDATE {quoted_table} SET {quoted_column} = country "
        f"WHERE country IS NOT NULL AND {quoted_column} IS NULL AND {predicate}"
    )
    print(
        f"[0030_india_employee_fields] backfilled {live_table}.country_code "
        "from country where country is a two-letter code"
    )


def upgrade() -> None:
    for table, columns in INDIA_COLUMNS.items():
        _add_missing_columns(table, columns)
    _backfill_country_code()


def _drop_columns(table: str, columns: list[str]) -> None:
    """Drop columns this revision added, and any index that references them."""
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[table])
    live_table = catalog.table(table)
    if live_table is None:
        print(f"[0030_india_employee_fields] {table} is not present; skipping")
        return

    inspector = sa.inspect(bind)
    for name in columns:
        live_column = catalog.column(live_table, name)
        if live_column is None:
            print(
                f"[0030_india_employee_fields] {live_table}.{name} is already "
                "absent; skipping"
            )
            continue

        # SQLite refuses to drop a column an index still references. The
        # index this revision (or the baseline's ``index=True``) created has
        # to go first.
        for index in inspector.get_indexes(live_table):
            column_names = [
                str(column).casefold() for column in index.get("column_names") or []
            ]
            if live_column.casefold() in column_names:
                drop_index_if_present(index["name"], live_table)

        op.drop_column(live_table, live_column)
        print(f"[0030_india_employee_fields] dropped {live_table}.{name}")


def downgrade() -> None:
    for table, columns in INDIA_COLUMNS.items():
        _drop_columns(table, list(columns))
