"""rewrite stored /files URLs to the authorised route (LibrePeople, item 9)

Revision ID: lp_files_url_rewrite
Revises: 0033_login_failure_window
Create Date: 2026-11-21

What this rewrites
------------------
Every stored value that still starts with the old unauthenticated prefix
``/files/`` is rewritten to ``/api/v1/files/`` — the prefix of the
authenticated download route (``GET /api/v1/files/{path}`` in
``app.main``). The ``StaticFiles`` mount it protected has been removed, so
stored URLs must name the protected path now.

Idempotent: the ``LIKE`` filter only matches the old prefix, so re-running
is a no-op. The downgrade rewrites the new prefix back to the old one.

This migration was written and exercised against a temporary SQLite
database; it has NOT been run against any real database. A snapshot of the
database and explicit owner approval are required before running it
anywhere else.
"""

from __future__ import annotations

from alembic import op

revision = "lp_files_url_rewrite"
down_revision = "0033_login_failure_window"


def upgrade() -> None:
    from app.storage.url_rewrite import (
        NEW_PREFIX,
        OLD_PREFIX,
        count_legacy_files_urls,
        rewrite_prefix,
    )

    bind = op.get_bind()
    for report in count_legacy_files_urls(bind):
        print(
            f"[lp_files_url_rewrite] rewriting {report['rows']} row(s) in "
            f"{report['table']}.{report['column']}"
        )
    changed = rewrite_prefix(bind, OLD_PREFIX, NEW_PREFIX)
    if not changed:
        print("[lp_files_url_rewrite] no stored /files/ URLs found; nothing to rewrite")


def downgrade() -> None:
    from app.storage.url_rewrite import NEW_PREFIX, OLD_PREFIX, rewrite_prefix

    changed = rewrite_prefix(op.get_bind(), NEW_PREFIX, OLD_PREFIX)
    if not changed:
        print("[lp_files_url_rewrite] downgrade: no /api/v1/files/ URLs found")
