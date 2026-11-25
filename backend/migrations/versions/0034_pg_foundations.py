"""PostgreSQL foundations (LibrePeople Stage 3)

Revision ID: 0034_pg_foundations
Revises: lp_files_url_rewrite
Create Date: 2026-11-21

What this does
--------------
* On PostgreSQL only: ``CREATE EXTENSION IF NOT EXISTS "pgcrypto"`` so
  future UUID / digest helpers have a stable, explicit dependency.
* On every other dialect (Oracle, SQLite): no-op. The Oracle chain is
  untouched and existing installs see no schema change.

Why a revision with almost no DDL
---------------------------------
The model metadata already uses portable constructs (``Identity``,
``func.now()``, ``Numeric``) that render on both Oracle and PostgreSQL,
so Stage 3 needs no table rewrites — only an explicit PG extension
marker that keeps the chain at a single head behind ``lp_files``.

Idempotent: the extension statement is ``IF NOT EXISTS`` and the
dialect guard makes re-runs and non-PG runs no-ops. The downgrade is
intentionally a no-op: dropping an extension that later objects may
depend on is never part of an automated downgrade.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0034_pg_foundations"
down_revision = "lp_files_url_rewrite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        print(
            "[0034_pg_foundations] "
            f"dialect is {bind.dialect.name!r}, not postgresql; skipping"
        )
        return
    op.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
    print('[0034_pg_foundations] ensured extension "pgcrypto"')


def downgrade() -> None:
    # Dropping pgcrypto could break objects created after this revision,
    # so the downgrade is a deliberate no-op.
    print("[0034_pg_foundations] downgrade is a no-op (extension retained)")
