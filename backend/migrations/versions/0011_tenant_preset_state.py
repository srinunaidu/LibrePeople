"""tenant_preset_state: the deployment's preset state

Revision ID: 0011_tenant_preset_state
Revises: 0010_payroll_jurisdiction
Create Date: 2026-10-22

What this adds
--------------
One table, ``tenant_preset_state``, holding the preset a deployment uses,
the modules it switched on and the settings it configured, with the
provenance of every setting: whether the value came from the preset, was
set by the customer, or is the customer's change to a value the preset
suggested.

The state is deployment level because one deployment serves one customer.
The table carries a ``scope`` column with a unique constraint so that the
deployment row is the only row that may exist, and so that a future
multi-tenant deployment has somewhere to put the other rows without
another migration.

Expand-then-contract
---------------------
This revision is pure expansion: it adds a table and its index and it
changes nothing that exists. Nothing writes to the table until the setup
flow lands, so it can be applied before the release that uses it. The
downgrade drops the table, which loses the deployment's preset choices —
the correct reverse of adding one, and never run against a production
database as part of normal operation.

Oracle
------
The primary key uses ``Identity()`` rather than ``autoincrement``: on
Oracle a plain autoincrement integer primary key raises ORA-01408 ("column
may not be implicitly specified") and the table is silently never created.

The revision is re-runnable
---------------------------
A database built by ``Base.metadata.create_all()`` before Alembic existed
already has this table, and an earlier run of this revision may have been
applied by hand. A table that is already there is therefore **adopted**,
not recreated, and the columns that are missing from it are added. An
index is created only when its **column list** is not already indexed — by
an index, by a unique constraint, or by the primary key — because Oracle
refuses a second index over a column list that is already taken
(ORA-01408).

The downgrade
-------------
The downgrade removes exactly what the upgrade created:

* the index this revision created, and only this one — an index it skipped
  is not dropped, because dropping an index that is not there fails with
  ORA-01418;
* the table, but only if this revision created it. The marker is the
  primary key constraint: this revision names it and the models do not
  name theirs, so a table that carries the name is one this revision
  built. An adopted table is left exactly as it was found.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names

revision = "0011_tenant_preset_state"
down_revision = "0010_payroll_jurisdiction"
branch_labels = None
depends_on = None


TABLE = "tenant_preset_state"
PRIMARY_KEY = "pk_tenant_preset_state"


def _live_name(bind) -> str:
    """The name the catalog holds the table under.

    Oracle folds an unquoted identifier to upper case, so the table this
    revision creates is ``TENANT_PRESET_STATE`` there and
    ``tenant_preset_state`` everywhere else. Every comparison with a
    catalog name is case-insensitive, because SQLAlchemy reports Oracle's
    table names in lower case while the catalog holds them in upper case.
    """
    catalog = catalog_names(bind, tables=[TABLE])
    return catalog.table(TABLE) or TABLE


def _table_is_there(inspector, live: str) -> bool:
    """Whether the table exists, whatever case either side spells it in."""
    names = {str(name).casefold() for name in inspector.get_table_names()}
    return live.casefold() in names


def _columns() -> list:
    return [
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("scope", sa.String(40), nullable=False),
        sa.Column("preset_id", sa.String(64), nullable=True),
        sa.Column("preset_version", sa.String(32), nullable=True),
        sa.Column("modules_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("settings_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("preset_document", sa.Text(), nullable=True),
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
    ]


def upgrade() -> None:
    bind = op.get_bind()
    live = _live_name(bind)
    inspector = sa.inspect(bind)

    if _table_is_there(inspector, live):
        # The table is already there: adopt it and add what is missing.
        present = {column["name"].casefold() for column in inspector.get_columns(live)}
        for column in _columns():
            if column.name.casefold() in present:
                continue
            op.add_column(live, column)
    else:
        op.create_table(
            live,
            *_columns(),
            sa.PrimaryKeyConstraint("id", name=PRIMARY_KEY),
            sa.UniqueConstraint("scope", name="uq_tenant_preset_state_scope"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    live = _live_name(bind)
    inspector = sa.inspect(bind)

    if not _table_is_there(inspector, live):
        return

    # Only drop the table when this revision built it. The marker is the
    # primary key constraint this revision names and the models do not.
    primary_key = inspector.get_pk_constraint(live) or {}
    if str(primary_key.get("name") or "").casefold() == PRIMARY_KEY.casefold():
        op.drop_table(live)
