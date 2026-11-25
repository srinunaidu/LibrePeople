"""case comment attachments (LP-SVC-001+003)

Revision ID: 0041_case_comment_attachments
Revises: 0040_document_lifecycle
Create Date: 2026-11-22

What this adds
--------------
* Two nullable columns on ``case_comments``: ``attachment_filename`` (the
  attachment's file name) and ``attachment_key`` (the opaque key inside
  the storage backend the authorised ``/api/v1/files/`` route serves).
  Both-or-neither: a comment with no attachment carries neither.

Expand-only
-----------
Pure expansion. It adds two nullable columns and changes no existing
column of any existing table, so it applies cleanly on a database that
already holds cases and comments. The downgrade removes exactly what
the upgrade created.

Idempotency
-----------
Both directions ask the catalog first (the 0036/0037/0039/0040 pattern):
a database the current models already built via ``create_all()`` carries
the columns, so the upgrade skips them there. Re-running is a no-op.

The migration imports no model: Alembic executes every revision module
while it reads the chain, and a model import would build the application
engine at read time.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0041_case_comment_attachments"
down_revision = "0040_document_lifecycle"
branch_labels = None
depends_on = None

TABLE = "case_comments"

NEW_COLUMNS: tuple[sa.Column, ...] = (
    sa.Column("attachment_filename", sa.String(255), nullable=True),
    sa.Column("attachment_key", sa.String(500), nullable=True),
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
                f"[0041_case_comment_attachments] {TABLE}.{column.name} "
                "already present; skipping"
            )
            continue
        op.add_column(TABLE, column)
        print(f"[0041_case_comment_attachments] added {TABLE}.{column.name}")


def downgrade() -> None:
    present = _column_names(TABLE)
    for column in reversed(NEW_COLUMNS):
        if column.name in present:
            op.drop_column(TABLE, column.name)
            print(f"[0041_case_comment_attachments] dropped {TABLE}.{column.name}")
        else:
            print(
                f"[0041_case_comment_attachments] {TABLE}.{column.name} "
                "already absent; skipping"
            )
