"""expense categories: tenant-scoped code uniqueness (Team D hardening)

Revision ID: 0047_expense_category_tenant_code
Revises: 0046_assets
Create Date: 2026-11-23

What this changes
-----------------
* Drops the global ``uq_expense_categories_code`` unique constraint on
  ``expense_categories.code``. A global code uniqueness leaks existence
  across tenants: a 409 for a code the caller may not see confirms a
  foreign row exists.
* Adds the composite ``uq_exp_cat_tenant_code`` over
  ``(tenant_id, code)`` — the DB backstop for the tenant-scoped app check
  in ``expenses._ensure_unique_expense_category_code``. The app check is
  case-insensitive and treats NULL tenant as the legacy default; the
  composite only backstops non-NULL tenants (NULL never equals NULL, so
  the app check remains authoritative). Name kept short for Oracle's
  30-char identifier limit.

Expand-only
-----------
Pure expansion of the constraint shape: it relaxes the global uniqueness
(which blocked the same code in two tenants) and adds the composite. No
column is added, removed, or backfilled; no row is touched. The downgrade
restores exactly what the upgrade removed.

Idempotency
-----------
Both directions ask the catalog first: the upgrade drops the global
constraint only when present and creates the composite only when absent;
the downgrade does the reverse. Re-running is a no-op. On SQLite the
constraint changes go through ``batch_alter_table`` (a table rebuild),
with the named-constraint guards so a database built from the current
models via ``create_all()`` (which already carries the composite) skips
creation there.

The migration imports no model: Alembic executes every revision module
while it reads the chain, and a model import would build the application
engine at read time.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0047_expense_category_tenant_code"
down_revision = "0046_assets"
branch_labels = None
depends_on = None

CATEGORIES = "expense_categories"

#: The global code uniqueness that leaked existence across tenants.
OLD_UQ = "uq_expense_categories_code"
#: Tenant-scoped backstop. Short for Oracle's 30-char identifier limit.
NEW_UQ = "uq_exp_cat_tenant_code"


def _unique_names(bind) -> set[str]:
    """The unique-constraint names the live table carries."""
    insp = sa.inspect(bind)
    try:
        return {c.get("name") for c in insp.get_unique_constraints(CATEGORIES)}
    except Exception:
        return set()


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    if CATEGORIES not in _tables(bind):
        print(f"[0047_expense_category_tenant_code] {CATEGORIES} absent; skipping")
        return
    uniques = _unique_names(bind)
    if OLD_UQ in uniques:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table(CATEGORIES) as batch:
                batch.drop_constraint(OLD_UQ, type_="unique")
        else:
            op.drop_constraint(OLD_UQ, CATEGORIES, type_="unique")
        print(f"[0047_expense_category_tenant_code] dropped {OLD_UQ}")
    else:
        print(f"[0047_expense_category_tenant_code] {OLD_UQ} already absent; skipping")
    uniques = _unique_names(bind)
    if NEW_UQ not in uniques:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table(CATEGORIES) as batch:
                batch.create_unique_constraint(NEW_UQ, ["tenant_id", "code"])
        else:
            op.create_unique_constraint(NEW_UQ, CATEGORIES, ["tenant_id", "code"])
        print(f"[0047_expense_category_tenant_code] created {NEW_UQ}")
    else:
        print(f"[0047_expense_category_tenant_code] {NEW_UQ} already present; skipping")


def downgrade() -> None:
    bind = op.get_bind()
    if CATEGORIES not in _tables(bind):
        print(f"[0047_expense_category_tenant_code] {CATEGORIES} absent; skipping")
        return
    uniques = _unique_names(bind)
    if NEW_UQ in uniques:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table(CATEGORIES) as batch:
                batch.drop_constraint(NEW_UQ, type_="unique")
        else:
            op.drop_constraint(NEW_UQ, CATEGORIES, type_="unique")
        print(f"[0047_expense_category_tenant_code] dropped {NEW_UQ}")
    else:
        print(f"[0047_expense_category_tenant_code] {NEW_UQ} already absent; skipping")
    uniques = _unique_names(bind)
    if OLD_UQ not in uniques:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table(CATEGORIES) as batch:
                batch.create_unique_constraint(OLD_UQ, ["code"])
        else:
            op.create_unique_constraint(OLD_UQ, CATEGORIES, ["code"])
        print(f"[0047_expense_category_tenant_code] created {OLD_UQ}")
    else:
        print(f"[0047_expense_category_tenant_code] {OLD_UQ} already present; skipping")
