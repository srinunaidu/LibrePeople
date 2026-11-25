"""legal entities master + employee legal-entity link (LP-CORE-003+010)

Revision ID: 0036_legal_entities
Revises: 0035_time_corrections_locks
Create Date: 2026-11-22

What this adds
--------------
* ``legal_entities`` — the employer-of-record master: code (unique natural
  key), name, country, registration number, address, ``is_active`` and the
  shared ``tenant_id`` discriminator, plus the composite
  ``ix_legal_entities_tenant_id_id`` index the other masters carry.
* ``employees.legal_entity_id`` — INTEGER, nullable, with the named foreign
  key ``fk_employees_legal_entity`` to ``legal_entities.id`` and the index
  ``ix_employees_legal_entity_id``.

Expand-only
-----------
Pure expansion. It creates one table and adds one nullable column; it
changes no existing column and backfills nothing, so it applies cleanly on
a database that already holds data. The downgrade removes exactly what the
upgrade created: the index, the foreign key and the column first, then the
table.

Idempotency
-----------
Both directions ask the catalog first (the 0029/0030 pattern): a database
the current models already built via ``create_all()`` carries the table
and the column, so the upgrade skips them there. The foreign key is dropped
only when it is present, so a database that never took the constraint path
downgrades cleanly too. Re-running is a no-op.

The foreign key is deliberately absent from the model: the frozen baseline
builds ``employees`` from the current models, and an inline reference to a
table a later revision creates would leave a fresh database with a dangling
reference that the 0018 batch migration cannot reflect past. The constraint
lives here, and the model spells the join out on the relationship instead.

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

revision = "0036_legal_entities"
down_revision = "0035_time_corrections_locks"
branch_labels = None
depends_on = None

LEGAL_ENTITIES = "legal_entities"
EMPLOYEES = "employees"
LEGAL_ENTITY_COLUMN = "legal_entity_id"

#: The foreign key from ``employees`` to ``legal_entities``. It is named so
#: that the downgrade can drop exactly what the upgrade created: an unnamed
#: constraint cannot be addressed reliably on every dialect.
EMPLOYEE_LEGAL_ENTITY_FK = "fk_employees_legal_entity"

#: Indexes this revision owns (the 0035 pattern): created on upgrade only
#: when the column list is not already indexed, dropped on downgrade only
#: when present.
LEGAL_ENTITY_INDEXES = (
    ("ix_legal_entities_tenant_id_id", (LEGAL_ENTITIES, ("tenant_id", "id"))),
    ("ix_employees_legal_entity_id", (EMPLOYEES, (LEGAL_ENTITY_COLUMN,))),
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _employee_fk_names() -> set:
    """The foreign-key constraint names the live employees table carries."""
    inspector = sa.inspect(op.get_bind())
    return {fk.get("name") for fk in inspector.get_foreign_keys(EMPLOYEES)}


def _add_employee_link(live_employees: str) -> None:
    """Add the nullable link column, then its named foreign key.

    The column goes in plain on every dialect. The foreign key follows as
    an explicit named constraint — but only where constraints are enforced
    (Oracle): on SQLite an explicit ``batch_alter_table`` rebuilds the
    table from reflection, and reflection re-emits the models' inline
    column CHECKs as table-level constraints, which then outlive the
    column they guard and break the india-payroll downgrade that drops
    it (0030). SQLite never enforces foreign keys in the suites, so the
    constraint would be dead weight there with a live cost. The proxied
    batch ``add_column`` itself preserves the inline form.
    """
    op.add_column(
        live_employees,
        sa.Column(LEGAL_ENTITY_COLUMN, sa.Integer(), nullable=True),
    )
    if op.get_bind().dialect.name == "sqlite":
        print(
            f"[0036_legal_entities] added {live_employees}.{LEGAL_ENTITY_COLUMN} "
            "(foreign key enforced on Oracle only; skipped on SQLite)"
        )
        return
    op.create_foreign_key(
        EMPLOYEE_LEGAL_ENTITY_FK,
        live_employees,
        LEGAL_ENTITIES,
        [LEGAL_ENTITY_COLUMN],
        ["id"],
    )
    print(f"[0036_legal_entities] added {live_employees}.{LEGAL_ENTITY_COLUMN}")


def _drop_employee_link(live_employees: str, live_column: str) -> None:
    """Drop the named foreign key first, then the column.

    A batch DROP COLUMN on SQLite rebuilds the table from its reflected
    definition: a foreign key that still names the dropped column fails the
    rebuild with ``unknown column ... in foreign key definition``. The
    guard keeps the downgrade a no-op on databases whose upgrade skipped
    the constraint path (the column was already there from ``create_all``).
    """
    if EMPLOYEE_LEGAL_ENTITY_FK in _employee_fk_names():
        if op.get_bind().dialect.name == "sqlite":
            with op.batch_alter_table(live_employees) as batch:
                batch.drop_constraint(
                    EMPLOYEE_LEGAL_ENTITY_FK, type_="foreignkey"
                )
        else:
            op.drop_constraint(
                EMPLOYEE_LEGAL_ENTITY_FK, live_employees, type_="foreignkey"
            )
        print(
            f"[0036_legal_entities] dropped constraint {EMPLOYEE_LEGAL_ENTITY_FK}"
        )
    else:
        print(
            f"[0036_legal_entities] constraint {EMPLOYEE_LEGAL_ENTITY_FK} "
            "already absent; skipping"
        )
    op.drop_column(live_employees, live_column)
    print(f"[0036_legal_entities] dropped {live_employees}.{LEGAL_ENTITY_COLUMN}")


def upgrade() -> None:
    catalog = catalog_names(op.get_bind(), tables=[LEGAL_ENTITIES, EMPLOYEES])

    if catalog.table(LEGAL_ENTITIES) is None:
        op.create_table(
            LEGAL_ENTITIES,
            sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
            sa.Column("tenant_id", sa.String(60), nullable=True),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("country", sa.String(80), nullable=True),
            sa.Column("registration_number", sa.String(60), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code", name="uq_legal_entities_code"),
        )
        print(f"[0036_legal_entities] created {LEGAL_ENTITIES}")
    else:
        print(f"[0036_legal_entities] {LEGAL_ENTITIES} already present; skipping")

    live_employees = catalog.table(EMPLOYEES)
    if live_employees is None:
        print(f"[0036_legal_entities] {EMPLOYEES} is not present; skipping column")
    elif catalog.column(live_employees, LEGAL_ENTITY_COLUMN) is not None:
        print(
            f"[0036_legal_entities] {live_employees}.{LEGAL_ENTITY_COLUMN} "
            "is already present; skipping"
        )
    else:
        _add_employee_link(live_employees)

    for name, (table, columns) in LEGAL_ENTITY_INDEXES:
        if create_index_if_missing(name, table, list(columns)):
            print(f"[0036_legal_entities] created index {name}")
        else:
            print(f"[0036_legal_entities] index {name} already present; skipping")


def downgrade() -> None:
    for name, (table, _columns) in reversed(LEGAL_ENTITY_INDEXES):
        if drop_index_if_present(name, table):
            print(f"[0036_legal_entities] dropped index {name}")

    catalog = catalog_names(op.get_bind(), tables=[EMPLOYEES])
    live_employees = catalog.table(EMPLOYEES)
    if live_employees is not None:
        live_column = catalog.column(live_employees, LEGAL_ENTITY_COLUMN)
        if live_column is None:
            print(
                f"[0036_legal_entities] {live_employees}.{LEGAL_ENTITY_COLUMN} "
                "already absent; skipping"
            )
        else:
            _drop_employee_link(live_employees, live_column)

    if LEGAL_ENTITIES in _tables():
        op.drop_table(LEGAL_ENTITIES)
        print(f"[0036_legal_entities] dropped {LEGAL_ENTITIES}")
    else:
        print(f"[0036_legal_entities] {LEGAL_ENTITIES} already absent; skipping")
