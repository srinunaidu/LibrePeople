"""login failure window (LibrePeople Phase 2, item 5)

Revision ID: 0033_login_failure_window
Revises: 0032_india_aadhaar_encryption
Create Date: 2026-11-21

What this adds
--------------
* ``users.failed_login_window_started_at`` timestamp, nullable.

The lockout rule is five failed sign-ins within fifteen minutes. The counter
needs to know when its window opened, otherwise five failures spread over a
year would lock an account. Nullable, so every existing row is valid and
starts with no open window.

Idempotent: skips the column when it already exists. The downgrade removes it.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.migrations import catalog_names

revision = "0033_login_failure_window"
down_revision = "0032_india_aadhaar_encryption"
branch_labels = None
depends_on = None

USERS = "users"
COLUMN = "failed_login_window_started_at"


def upgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[USERS])
    live_table = catalog.table(USERS)
    if live_table is None:
        print(f"[0033_login_failure_window] {USERS} is not present; skipping")
        return
    if catalog.column(live_table, COLUMN) is None:
        op.add_column(
            live_table,
            sa.Column(COLUMN, sa.DateTime(timezone=True), nullable=True),
        )
        print(f"[0033_login_failure_window] added {live_table}.{COLUMN}")
    else:
        print(f"[0033_login_failure_window] {live_table}.{COLUMN} already present; skipping")


def downgrade() -> None:
    bind = op.get_bind()
    catalog = catalog_names(bind, tables=[USERS])
    live_table = catalog.table(USERS)
    if live_table is None:
        print(f"[0033_login_failure_window] {USERS} is not present; skipping")
        return
    live_column = catalog.column(live_table, COLUMN)
    if live_column is None:
        print(f"[0033_login_failure_window] {live_table}.{COLUMN} already absent; skipping")
        return
    op.drop_column(live_table, live_column)
    print(f"[0033_login_failure_window] dropped {live_table}.{COLUMN}")
