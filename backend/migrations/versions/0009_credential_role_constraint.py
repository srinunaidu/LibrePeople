"""credential role constraint: the role column holds one of the five roles

Revision ID: 0009_credential_role_constraint
Revises: 0008_fk_indexes
Create Date: 2026-10-21

What this adds
--------------
* ``users.role`` becomes a constrained value. The column was a free
  ``VARCHAR(50)``: any string could be stored, and a role that the code does
  not recognise is a role that every policy denies — silently, and only after
  the row has been written. The column now carries a ``CHECK`` constraint
  admitting exactly the five roles the platform defines, and it is not
  nullable.
* Any row that already holds a value outside those five is moved to
  ``Associate``, the least-privileged role.

Why the data is moved rather than the migration refused
-------------------------------------------------------
A deploy must not fail because one row has a role nobody recognises, and it
must not fail *silently* either. Every unknown value becomes ``Associate``,
which is the only direction that reduces privilege: an account that was
written with a misspelled role stops being able to do anything, rather than
keeping a capability the policy never granted it. The count and the distinct
values are printed; no account identifier is, because a migration log is not
the place for one.

Expand-then-contract
---------------------
This revision is *expansion* in the strict sense: it adds a constraint and
normalises data. It removes no column and no data — the rows stay, only the
value in one column changes, and only for values the code could not act on
anyway. The downgrade removes the constraint and relaxes the column, so the
reverse is a true reverse.

Dialect notes
-------------
Oracle can add and drop a ``CHECK`` constraint, and can change a column to
``NOT NULL``, with plain statements. SQLite cannot: it has no
``ALTER TABLE ... ADD CONSTRAINT`` and no way to change a column's
nullability. There the table is rebuilt through Alembic's batch mode, which
copies the rows, the indexes and the foreign key across. The rebuild is
skipped entirely when the constraint is already there and the column is
already ``NOT NULL``, which is the case for every database built from the
current models.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names

revision = "0009_credential_role_constraint"
down_revision = "0008_fk_indexes"
branch_labels = None
depends_on = None


#: The roles the platform recognises. The same five the policy module names.
ROLES: tuple[str, ...] = (
    "SuperAdmin",
    "HR",
    "Manager",
    "Associate",
    "PayrollViewer",
)

#: Where an unrecognised role goes. The least-privileged role.
FALLBACK_ROLE = "Associate"

#: The name of the constraint. The model emits the same name, so a database
#: built from the models and a database this revision touches agree.
CONSTRAINT_NAME = "user_role"

#: The column the constraint is about.
COLUMN = "role"


def _check_sql() -> str:
    """The condition the constraint enforces."""
    allowed = ", ".join("'%s'" % role for role in ROLES)
    return f"{COLUMN} IN ({allowed})"


def _has_check_constraint(inspector, table: str) -> bool:
    """Whether the role constraint is already on the table."""
    for constraint in inspector.get_check_constraints(table):
        if str(constraint.get("name") or "").casefold() == CONSTRAINT_NAME.casefold():
            return True
    return False


def _normalise_roles(bind, live_table: str, live_column: str) -> None:
    """Move every unrecognised role to the least-privileged role.

    The statement is built from SQLAlchemy's own table construct rather than
    from a string, so the identifier is quoted the way the dialect expects.
    The table and the column are named as the catalog holds them.
    """
    users = sa.table(live_table, sa.column(live_column))
    invalid = ~users.c[live_column].in_(ROLES) | users.c[live_column].is_(None)

    count = bind.execute(
        sa.select(sa.func.count()).select_from(users).where(invalid)
    ).scalar()
    if not count:
        print(
            f"[0009_credential_role_constraint] {live_table}.{live_column} "
            "holds only known roles"
        )
        return

    values = bind.execute(
        sa.select(users.c[live_column]).where(invalid).distinct()
    ).scalars().all()
    # Only the roles are printed. An account identifier is not.
    print(
        f"[0009_credential_role_constraint] {count} row(s) with an unrecognised "
        f"role {sorted(str(v) for v in values)} moved to {FALLBACK_ROLE}"
    )
    bind.execute(users.update().where(invalid).values(**{live_column: FALLBACK_ROLE}))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # The table and the column are named as the catalog holds them.
    # SQLAlchemy's Oracle reflection lower-cases every identifier it
    # reports, and the catalog is mixed, so a statement built from a
    # reflected name can name an object that does not exist.
    catalog = catalog_names(bind)
    live_table = catalog.table("users")
    if live_table is None:
        print("[0009_credential_role_constraint] users is not present; skipping")
        return

    live_column = catalog.column(live_table, COLUMN)
    if live_column is None:
        print(
            f"[0009_credential_role_constraint] {live_table}.{COLUMN} is not present; skipping"
        )
        return

    _normalise_roles(bind, live_table, live_column)

    inspector = sa.inspect(bind)
    has_check = _has_check_constraint(inspector, live_table)
    nullable = not catalog.is_not_null(live_table, live_column)

    if not has_check or nullable:
        if bind.dialect.name == "sqlite":
            # SQLite cannot add a constraint or change nullability in place:
            # the table is rebuilt and the rows are copied across.
            with op.batch_alter_table(live_table) as batch:
                if not has_check:
                    batch.create_check_constraint(CONSTRAINT_NAME, _check_sql())
                if nullable:
                    batch.alter_column(live_column, nullable=False)
            print(
                f"[0009_credential_role_constraint] {live_table}.{live_column} "
                "rebuilt with the role constraint"
            )
        else:
            if not has_check:
                op.create_check_constraint(CONSTRAINT_NAME, live_table, _check_sql())
                print(
                    f"[0009_credential_role_constraint] constraint {CONSTRAINT_NAME} "
                    f"added to {live_table}"
                )
            if nullable:
                op.execute(
                    sa.text(
                        f'ALTER TABLE "{live_table}" MODIFY "{live_column}" NOT NULL'
                    )
                )
                print(
                    f"[0009_credential_role_constraint] {live_table}.{live_column} "
                    "is now not null"
                )
    else:
        print(
            f"[0009_credential_role_constraint] {live_table}.{live_column} is "
            "already constrained; nothing to do"
        )


def downgrade() -> None:
    """Remove the constraint and let the column be nullable again.

    The rows are not touched. A role that was normalised to ``Associate`` on
    the way up stays ``Associate`` on the way down: the downgrade reverses the
    *constraint*, not the data, because there is no way to know what an
    unrecognised role was before it was replaced.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    catalog = catalog_names(bind)
    live_table = catalog.table("users")
    if live_table is None:
        print("[0009_credential_role_constraint] users is not present; skipping")
        return

    live_column = catalog.column(live_table, COLUMN)
    if live_column is None:
        print(
            f"[0009_credential_role_constraint] {live_table}.{COLUMN} is not present; skipping"
        )
        return

    has_check = _has_check_constraint(inspector, live_table)
    nullable = not catalog.is_not_null(live_table, live_column)

    if has_check or not nullable:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table(live_table) as batch:
                if has_check:
                    batch.drop_constraint(CONSTRAINT_NAME, type_="check")
                if not nullable:
                    batch.alter_column(live_column, nullable=True)
            print(
                f"[0009_credential_role_constraint] {live_table}.{live_column} "
                "rebuilt without the role constraint"
            )
        else:
            if has_check:
                op.drop_constraint(CONSTRAINT_NAME, live_table, type_="check")
                print(
                    f"[0009_credential_role_constraint] constraint {CONSTRAINT_NAME} "
                    f"dropped from {live_table}"
                )
            if not nullable:
                op.execute(
                    sa.text(f'ALTER TABLE "{live_table}" MODIFY "{live_column}" NULL')
                )
                print(
                    f"[0009_credential_role_constraint] {live_table}.{live_column} "
                    "is nullable again"
                )
    else:
        print(
            f"[0009_credential_role_constraint] {live_table}.{live_column} carries no "
            "constraint; nothing to do"
        )
