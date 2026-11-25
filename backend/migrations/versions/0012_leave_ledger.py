"""leave_ledger: the leave ledger, and the genesis of the balances

Revision ID: 0012_leave_ledger
Revises: 0011_tenant_preset_state
Create Date: 2026-10-22

Why
---
The models declared a ``leave_ledger`` table and no database had it. A model
without its migration is a model that does not exist in any database, so this
revision creates the table the models describe.

What the table is
-----------------
The leave balance stops being three numbers that somebody edited and becomes
the sum of a signed history: every accrual, entitlement, carry-over, usage,
adjustment, expiry and encashment is a row, and the balance is their sum.
The three columns on ``leave_balances`` stay, as a cache of that sum, and
they are refreshed from the ledger whenever a row is written.

The backfill
------------
The delicate part. A balance that existed before this revision has cached
numbers and no history, so the derived balance would be zero while the cache
says otherwise, and the reconciliation would be a fiction. Every such balance
is therefore given a **real** genesis: an ``ENTITLEMENT`` row for the days
that were granted, a ``CARRY_OVER`` row for the days that were brought
forward, and a ``USAGE`` row for the days that were taken. Three rows that
say what happened, not one row that says "there used to be something here",
so the sum of the ledger is the balance the tenant already had.

A balance that already has ledger rows is left alone: the ledger is the
history, and a history is never rewritten.

Expand-then-contract
--------------------
Pure expansion. It adds a table, adds indexes and adds rows. It changes no
column of an existing table and removes no row, so it can be applied before
the release whose code needs it, and the downgrade removes exactly what the
upgrade created.

Oracle
------
The table and its indexes are created through the shared helpers, so the
identifiers come from the catalog and an index over a column list the schema
already indexes is skipped rather than refused with ``ORA-01408``. The
primary key constraint is named, which is how the downgrade tells a table it
created from a table it adopted: only a table it created is dropped.
"""
from __future__ import annotations

from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.migrations import (
    catalog_names,
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0012_leave_ledger"
down_revision = "0011_tenant_preset_state"
branch_labels = None
depends_on = None

#: The name of the table, as the models spell it.
TABLE = "leave_ledger"

#: The name of the primary key constraint this revision creates.
#:
#: The models do not name their primary keys, so a table that carries this
#: name is one this revision built. The downgrade uses that to leave an
#: adopted table exactly as it found it.
PRIMARY_KEY_NAME = "pk_leave_ledger_0010"

#: The columns of the table, in the order they are created.
COLUMNS = (
    sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column(
        "balance_id",
        sa.Integer(),
        sa.ForeignKey("leave_balances.id"),
        nullable=False,
    ),
    sa.Column(
        "employee_id",
        sa.Integer(),
        sa.ForeignKey("employees.id"),
        nullable=False,
    ),
    sa.Column(
        "leave_type_id",
        sa.Integer(),
        sa.ForeignKey("leave_types.id"),
        nullable=False,
    ),
    sa.Column("entitlement_year", sa.Integer(), nullable=False),
    sa.Column(
        "entry_type",
        postgresql.ENUM(
            "ACCRUAL",
            "ENTITLEMENT",
            "CARRY_OVER",
            "USAGE",
            "ADJUSTMENT",
            "EXPIRY",
            "ENCASHMENT",
            name="leaveledgerentrytype",
            length=11,
            # Version-independent no-op: the generic sa.Enum create_type flag
            # is honored only on SQLAlchemy 2.1+. On 2.0.x the kwarg is
            # silently swallowed (the object carries no create_type
            # attribute), so op.create_table still emits an unconditional
            # CREATE TYPE and the chain dies on PostgreSQL with
            # 'type "leaveledgerentrytype" already exists' (gate A FAIL,
            # 2026-11-25). The PG-dialect ENUM honors create_type=False on
            # 2.0 and 2.1 alike (verified on pinned 2.0.29 + system 2.1.5),
            # so the type is created idempotently by _ensure_entry_type()
            # below instead. No-op on SQLite/Oracle, where the enum compiles
            # to VARCHAR and no CREATE TYPE exists.
            create_type=False,
        ),
        nullable=False,
    ),
    sa.Column("signed_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("reference_type", sa.String(40), nullable=True),
    sa.Column("reference_id", sa.Integer(), nullable=True),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column(
        "created_by",
        sa.Integer(),
        sa.ForeignKey("users.id"),
        nullable=True,
    ),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    ),
)

#: The indexes this revision creates, in the order it creates them.
#:
#: The first four are the indexes the models declare. The fifth is the
#: foreign key on ``created_by``, which Oracle does not index by itself and
#: which ``0008_fk_indexes`` would have created had the table existed by
#: then. Its name follows that revision's convention, so the two cannot
#: collide.
INDEXES = (
    ("ix_leave_ledger_balance_id", ("balance_id",)),
    ("ix_leave_ledger_employee_id", ("employee_id",)),
    ("ix_leave_ledger_leave_type_id", ("leave_type_id",)),
    ("ix_leave_ledger_entitlement_year", ("entitlement_year",)),
    ("ix_fk_leave_ledger_created_by", ("created_by",)),
)

#: The genesis rows of a balance, in the order they are written.
#:
#: Each one is a movement that really happened, with the sign it really had.
#: The usage row is negative because the days left the balance.
GENESIS = (
    (
        "ENTITLEMENT",
        "entitled_days",
        1,
        "entitlement",
        "Entitlement reconstructed from the cached balance when the ledger was "
        "created.",
    ),
    (
        "CARRY_OVER",
        "carried_over_days",
        1,
        "carry_over",
        "Carry-over reconstructed from the cached balance when the ledger was "
        "created.",
    ),
    (
        "USAGE",
        "used_days",
        -1,
        "leave_balance",
        "Leave taken before the ledger existed, reconstructed from the cached "
        "balance.",
    ),
)


def _number(value) -> Decimal:
    """A decimal from whatever the database gave us."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _plain_column(column: sa.Column) -> sa.Column:
    """A copy of a column without its foreign key.

    ``add_column`` does not accept a foreign key, so the key is dropped from
    the copy and the table keeps the one it already has.
    """
    definition = column.copy()
    definition.foreign_keys = set()
    definition.index = False
    definition.unique = False
    return definition


def _created_by_this_revision(inspector, table: str) -> bool:
    """Whether this revision created the table.

    The primary key constraint is the marker: this revision names it and the
    models do not name theirs.
    """
    primary_key = inspector.get_pk_constraint(table) or {}
    name = str(primary_key.get("name") or "").casefold()
    return name == PRIMARY_KEY_NAME.casefold()


#: The two tables the backfill reads and writes, described for the query.
#:
#: They are written out rather than imported from the models: a migration
#: that reads the models is a migration that changes meaning when a model
#: changes. The column types are declared so that the dialect is handed a
#: value it understands.
BALANCES = sa.table(
    "leave_balances",
    sa.column("id", sa.Integer),
    sa.column("employee_id", sa.Integer),
    sa.column("leave_type_id", sa.Integer),
    sa.column("entitlement_year", sa.Integer),
    sa.column("entitled_days", sa.Numeric(6, 1)),
    sa.column("carried_over_days", sa.Numeric(6, 1)),
    sa.column("used_days", sa.Numeric(6, 1)),
)

LEDGER = sa.table(
    "leave_ledger",
    sa.column("balance_id", sa.Integer),
    sa.column("employee_id", sa.Integer),
    sa.column("leave_type_id", sa.Integer),
    sa.column("entitlement_year", sa.Integer),
    sa.column("entry_type", sa.String(11)),
    sa.column("signed_days", sa.Numeric(6, 2)),
    sa.column("reference_type", sa.String(40)),
    sa.column("reference_id", sa.Integer),
    sa.column("description", sa.Text),
)


def _backfill(bind) -> int:
    """Give every balance that has no ledger a real genesis.

    Returns the number of balances that were given one.
    """
    balances = bind.execute(
        sa.select(
            BALANCES.c.id,
            BALANCES.c.employee_id,
            BALANCES.c.leave_type_id,
            BALANCES.c.entitlement_year,
            BALANCES.c.entitled_days,
            BALANCES.c.carried_over_days,
            BALANCES.c.used_days,
        )
    ).fetchall()

    written = 0
    for balance in balances:
        (
            balance_id,
            employee_id,
            leave_type_id,
            entitlement_year,
            entitled_days,
            carried_over_days,
            used_days,
        ) = balance
        already = bind.execute(
            sa.select(sa.func.count())
            .select_from(LEDGER)
            .where(LEDGER.c.balance_id == balance_id)
        ).scalar()
        if already:
            # The balance already has a history. A history is never rewritten.
            continue

        cached = {
            "entitled_days": _number(entitled_days),
            "carried_over_days": _number(carried_over_days),
            "used_days": _number(used_days),
        }
        for entry_type, column, sign, reference_type, description in GENESIS:
            days = cached[column] * sign
            if days == 0:
                continue
            bind.execute(
                LEDGER.insert().values(
                    balance_id=balance_id,
                    employee_id=employee_id,
                    leave_type_id=leave_type_id,
                    entitlement_year=entitlement_year,
                    entry_type=entry_type,
                    signed_days=days,
                    reference_type=reference_type,
                    reference_id=balance_id
                    if reference_type == "leave_balance"
                    else None,
                    description=description,
                )
            )
        written += 1
    return written


def _ensure_entry_type(bind) -> None:
    """Create the ``leaveledgerentrytype`` native enum exactly once.

    On PostgreSQL the 0001 baseline already creates this type (via
    ``metadata.create_all`` over the frozen tables, which creates enum types
    even for tables outside the frozen set), so creating it here with
    ``checkfirst=True`` is a no-op when it exists and creates it when a
    database reaches this revision without it (e.g. a legacy database whose
    baseline ran before the enum's model existed). On SQLite/Oracle this is
    a no-op: the enum is not native there. Values are read from COLUMNS so
    the list lives in exactly one place.
    """
    column_type = next(c.type for c in COLUMNS if c.name == "entry_type")
    sa.Enum(
        *column_type.enums,
        name=column_type.name,
        length=column_type.length,
    ).create(bind, checkfirst=True)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    catalog = catalog_names(bind)

    _ensure_entry_type(bind)

    live = catalog.table(TABLE)
    if live is None:
        op.create_table(
            TABLE,
            *COLUMNS,
            sa.PrimaryKeyConstraint("id", name=PRIMARY_KEY_NAME),
        )
        live = TABLE
        print(f"[0012_leave_ledger] created {TABLE}")
    else:
        # The table is already there — a database built by ``create_all()``
        # against the new models, or an earlier run of this revision that
        # failed after the table was created. Bring it up to the shape the
        # models expect, and never fail on what is already there.
        present = {
            str(column["name"]).casefold()
            for column in inspector.get_columns(live)
        }
        for column in COLUMNS:
            if column.name.casefold() in present:
                continue
            op.add_column(live, _plain_column(column))
            print(f"[0012_leave_ledger] added missing column {live}.{column.name}")

    for name, columns in INDEXES:
        if create_index_if_missing(name, TABLE, list(columns)):
            print(f"[0012_leave_ledger] created index {name}")
        else:
            print(
                f"[0012_leave_ledger] {TABLE} ({', '.join(columns)}) is already "
                f"indexed; {name} was not created"
            )

    written = _backfill(bind)
    print(f"[0012_leave_ledger] {written} balance(s) given a genesis")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    catalog = catalog_names(bind)

    live = catalog.table(TABLE)
    if live is None:
        print(f"[0012_leave_ledger] {TABLE} is not present; nothing to drop")
        return

    for name, _columns in reversed(INDEXES):
        if drop_index_if_present(name, TABLE):
            print(f"[0012_leave_ledger] dropped index {name}")
        else:
            print(f"[0012_leave_ledger] {name} is not present; skipping")

    if _created_by_this_revision(inspector, live):
        op.drop_table(live)
        print(f"[0012_leave_ledger] dropped {live}")
    else:
        print(
            f"[0012_leave_ledger] {live} was not created by this revision; "
            "leaving it in place"
        )
