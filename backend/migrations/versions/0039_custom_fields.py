"""configurable employee fields (LP-CORE-005)

Revision ID: 0039_custom_fields
Revises: 0038_legal_entity_tenant_code
Create Date: 2026-11-22

What this adds
--------------
* ``custom_field_defs`` — one row per tenant-configured employee
  attribute: machine ``key`` (imported/exported as ``custom.<key>``),
  display ``label``, ``field_type`` (text/number/integer/date/boolean/
  email), ``required``, ``is_sensitive``, ``visibility`` (all/hr_only),
  optional ``options_json``, ``is_active`` and the shared ``tenant_id``
  discriminator, plus the tenant-scoped unique backstop
  ``uq_cfdef_tenant_key`` over (tenant_id, key).
* ``custom_field_values`` — one value per (employee, definition), stored
  as text, with the unique backstop ``uq_cfval_emp_def`` over
  (employee_id, def_id).

Expand-only
-----------
Pure expansion. It creates two tables and their indexes and changes no
column of an existing table, so it applies cleanly on a database that
already holds data. The downgrade removes exactly what the upgrade
created.

Idempotency
-----------
Both directions ask the catalog first (the 0036/0037 pattern): a database
the current models already built via ``create_all()`` carries the tables,
so the upgrade skips them there. Re-running is a no-op.

The migration imports no model: Alembic executes every revision module
while it reads the chain, and a model import would build the application
engine at read time.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import (
    catalog_names,
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0039_custom_fields"
down_revision = "0038_legal_entity_tenant_code"
branch_labels = None
depends_on = None

DEFS = "custom_field_defs"
VALUES = "custom_field_values"

DEF_INDEXES = (
    ("ix_cfdef_tenant_id_id", (DEFS, ("tenant_id", "id"))),
    ("ix_custom_field_defs_key", (DEFS, ("key",))),
)

VALUE_INDEXES = (
    ("ix_cfval_tenant_id_id", (VALUES, ("tenant_id", "id"))),
    ("ix_cfval_employee_id", (VALUES, ("employee_id",))),
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    catalog = catalog_names(op.get_bind(), tables=[DEFS, VALUES])

    if catalog.table(DEFS) is None:
        op.create_table(
            DEFS,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("key", sa.String(60), nullable=False),
            sa.Column("label", sa.String(160), nullable=False),
            sa.Column("field_type", sa.String(20), nullable=False, server_default="text"),
            sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("visibility", sa.String(20), nullable=False, server_default="all"),
            sa.Column("options_json", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "key", name="uq_cfdef_tenant_key"),
        )
        print(f"[0039_custom_fields] created {DEFS}")
    else:
        print(f"[0039_custom_fields] {DEFS} already present; skipping")

    if catalog.table(VALUES) is None:
        op.create_table(
            VALUES,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column(
                "employee_id",
                sa.Integer(),
                sa.ForeignKey("employees.id"),
                nullable=False,
            ),
            sa.Column(
                "def_id",
                sa.Integer(),
                sa.ForeignKey("custom_field_defs.id"),
                nullable=False,
            ),
            sa.Column("value_text", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("employee_id", "def_id", name="uq_cfval_emp_def"),
        )
        print(f"[0039_custom_fields] created {VALUES}")
    else:
        print(f"[0039_custom_fields] {VALUES} already present; skipping")

    for name, (table, columns) in DEF_INDEXES + VALUE_INDEXES:
        if create_index_if_missing(name, table, list(columns)):
            print(f"[0039_custom_fields] created index {name}")
        else:
            print(f"[0039_custom_fields] index {name} already present; skipping")


def downgrade() -> None:
    for name, (table, _columns) in reversed(VALUE_INDEXES + DEF_INDEXES):
        if drop_index_if_present(name, table):
            print(f"[0039_custom_fields] dropped index {name}")

    existing = _tables()
    for table in (VALUES, DEFS):
        if table in existing:
            op.drop_table(table)
            print(f"[0039_custom_fields] dropped {table}")
        else:
            print(f"[0039_custom_fields] {table} already absent; skipping")
