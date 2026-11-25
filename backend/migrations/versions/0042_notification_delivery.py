"""notification delivery tracking (LP-NOT-003)

Revision ID: 0042_notification_delivery
Revises: 0041_case_comment_attachments
Create Date: 2026-11-22

What this adds
--------------
* Three columns on ``notifications``: ``delivery_status`` (the queue state
  of the row: queued/sending/sent/failed/dead), ``delivery_attempts`` (how
  many times the ``notification_deliver`` handler has run for the row) and
  ``delivery_error`` (the last failure, if any). There is no external
  vendor behind delivery: the in-app centre is the channel, and the
  handler records its outcome here.

Expand-only
-----------
Pure expansion. It adds columns with server defaults and changes no
existing column of any existing table, so it applies cleanly on a
database that already holds notifications: existing rows read back as
``queued``/``0``, which is what they are — emitted before delivery was
tracked. The downgrade removes exactly what the upgrade created.

Idempotency
-----------
Both directions ask the catalog first (the 0036/0037/0039/0040/0041
pattern): a database the current models already built via
``create_all()`` carries the columns, so the upgrade skips them there.
Re-running is a no-op.

The migration imports no model: Alembic executes every revision module
while it reads the chain, and a model import would build the application
engine at read time.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0042_notification_delivery"
down_revision = "0041_case_comment_attachments"
branch_labels = None
depends_on = None

TABLE = "notifications"

NEW_COLUMNS: tuple[sa.Column, ...] = (
    sa.Column("delivery_status", sa.String(20), nullable=False, server_default="queued"),
    sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("delivery_error", sa.Text(), nullable=True),
)


def _column_names(table: str) -> set[str]:
    try:
        return {
            column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)
        }
    except sa.exc.NoSuchTableError:
        return set()


def upgrade() -> None:
    present = _column_names(TABLE)
    for column in NEW_COLUMNS:
        if column.name in present:
            print(
                f"[0042_notification_delivery] {TABLE}.{column.name} "
                "already present; skipping"
            )
            continue
        op.add_column(TABLE, column)
        print(f"[0042_notification_delivery] added {TABLE}.{column.name}")


def downgrade() -> None:
    present = _column_names(TABLE)
    for column in reversed(NEW_COLUMNS):
        if column.name in present:
            op.drop_column(TABLE, column.name)
            print(f"[0042_notification_delivery] dropped {TABLE}.{column.name}")
        else:
            print(
                f"[0042_notification_delivery] {TABLE}.{column.name} "
                "already absent; skipping"
            )
