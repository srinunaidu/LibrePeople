"""public_intake: the fields a message from the public form needs

Revision ID: 0013_public_intake
Revises: 0012_leave_ledger
Create Date: 2026-10-22

Why
---
The public contact form posts to an endpoint that requires a bearer token,
so it has answered 401 for every visitor since the role policy was applied.
The form is given an endpoint of its own, and that endpoint creates a case
in the case table — so the case table needs to be able to hold a message
from somebody who is not an employee.

Three columns:

* ``source`` — where the case came from. ``hr`` for the cases HR opens
  itself, ``public_contact`` for the ones the form sends. The column is not
  null and defaults to ``hr``, so the cases that are already there are
  unchanged by this revision.
* ``sender_email`` — the address the message was sent from. Null for a case
  HR opened itself.
* ``message`` — the message itself. Null for a case HR opened itself.

The sender's *name* goes in the subject, which is the case's label and
already exists.

Expand-then-contract
--------------------
Pure expansion: it adds columns and an index, and it changes no existing
column and removes no row. The downgrade removes exactly what the upgrade
added, and the columns it drops are the ones it added.

Oracle
------
The index is created through the shared helper, so an index over a column
list the schema already indexes is skipped rather than refused with
``ORA-01408``. The columns are added with the catalog's own names, read
through ``catalog_names``, because a statement built from a reflected name
names an object that does not exist.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import (
    catalog_names,
    create_index_if_missing,
    drop_index_if_present,
)

revision = "0013_public_intake"
down_revision = "0012_leave_ledger"
branch_labels = None
depends_on = None

#: The table the public intake writes to.
TABLE = "hr_cases"

#: The index the models declare on ``source``.
INDEX = "ix_hr_cases_source"

#: The columns this revision adds, in the order it adds them.
COLUMNS = (
    sa.Column(
        "source",
        sa.String(40),
        server_default="hr",
        nullable=False,
    ),
    sa.Column("sender_email", sa.String(255), nullable=True),
    sa.Column("message", sa.Text(), nullable=True),
)


def _plain_column(column: sa.Column) -> sa.Column:
    """A copy of a column without its index flag.

    ``add_column`` does not create the index; the index is created
    separately, through the helper that knows what the schema already
    indexes.
    """
    definition = column.copy()
    definition.index = False
    definition.unique = False
    return definition


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    catalog = catalog_names(bind)

    live = catalog.table(TABLE)
    if live is None:
        print(f"[0011_public_intake] {TABLE} is not present; nothing to do")
        return

    present = {
        str(column["name"]).casefold() for column in inspector.get_columns(live)
    }
    for column in COLUMNS:
        if column.name.casefold() in present:
            continue
        op.add_column(live, _plain_column(column))
        print(f"[0011_public_intake] added {live}.{column.name}")

    if create_index_if_missing(INDEX, TABLE, ["source"]):
        print(f"[0011_public_intake] created index {INDEX}")
    else:
        print(
            f"[0011_public_intake] {TABLE}(source) is already indexed; "
            f"{INDEX} was not created"
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    catalog = catalog_names(bind)

    live = catalog.table(TABLE)
    if live is None:
        print(f"[0011_public_intake] {TABLE} is not present; nothing to drop")
        return

    if drop_index_if_present(INDEX, TABLE):
        print(f"[0011_public_intake] dropped index {INDEX}")
    else:
        print(f"[0011_public_intake] {INDEX} is not present; skipping")

    present = {
        str(column["name"]).casefold() for column in inspector.get_columns(live)
    }
    for column in reversed(COLUMNS):
        if column.name.casefold() not in present:
            continue
        op.drop_column(live, column.name)
        print(f"[0011_public_intake] dropped {live}.{column.name}")
