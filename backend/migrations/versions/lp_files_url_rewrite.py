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

PostgreSQL note (gate A, 2026-11-25): the ``LIKE`` predicates below wrap
the column in portable ``CAST(<col> AS TEXT)``. On PostgreSQL a reflected
native-enum column (e.g. ``leave_ledger.entry_type``) is a ``String``
subclass, so a bare ``<enum-col> LIKE ...`` renders ``<enumtype> ~~
unknown`` and PG raises ``UndefinedFunction`` (no ``~~`` operator for a
custom enum). ``CAST()`` — not the PG-only ``::`` operator — keeps SQLite
behavior identical. Only the ``OLD_PREFIX``/``NEW_PREFIX`` constants are
imported from ``app.storage.url_rewrite``; the SQL is emitted locally so
no bare-``LIKE`` helper runs on PG.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import (
    Connection,
    Engine,
    MetaData,
    String,
    Table,
    Text,
    cast,
    func,
    inspect,
    select,
)

revision = "lp_files_url_rewrite"
down_revision = "0033_login_failure_window"

_TEXT_COLUMN_TYPES = (String, Text)


def _text_columns(bind):
    """Yield ``(table, column)`` for every string column in the database."""
    metadata = MetaData()
    for table_name in inspect(bind).get_table_names():
        table = Table(table_name, metadata, autoload_with=bind)
        for column in table.columns:
            if isinstance(column.type, _TEXT_COLUMN_TYPES):
                yield table, column


def _count_matching(conn: Connection, table: Table, column, prefix: str) -> int:
    """Count rows whose value starts with ``prefix`` (PG-safe via CAST)."""
    return conn.execute(
        select(func.count())
        .select_from(table)
        .where(cast(column, Text).like(f"{prefix}%"))
    ).one()[0]


def _rewrite_prefix(conn: Connection, old_prefix: str, new_prefix: str) -> list[str]:
    """Rewrite ``old_prefix`` to ``new_prefix`` in every text column."""
    changed: list[str] = []
    for table, column in _text_columns(conn):
        # Per-column count first: a native-enum column can never hold a
        # ``/files/`` value, so its count is 0 and the UPDATE below — whose
        # ``func.replace(<enum-col>, ...)`` PG could not resolve — is
        # skipped. Text columns with matches are rewritten as before.
        if not _count_matching(conn, table, column, old_prefix):
            continue
        statement = (
            table.update()
            .values({column: func.replace(column, old_prefix, new_prefix)})
            .where(cast(column, Text).like(f"{old_prefix}%"))
        )
        if conn.execute(statement).rowcount:
            changed.append(f"{table.name}.{column.name}")
    return changed


def _run(bind, old_prefix: str, new_prefix: str) -> list[str]:
    if isinstance(bind, Engine):
        with bind.begin() as conn:
            return _rewrite_prefix(conn, old_prefix, new_prefix)
    return _rewrite_prefix(bind, old_prefix, new_prefix)


def _report(bind, prefix: str) -> list[dict]:
    conn = bind.connect() if isinstance(bind, Engine) else bind
    try:
        reports: list[dict] = []
        for table, column in _text_columns(conn):
            count = _count_matching(conn, table, column, prefix)
            if count:
                reports.append(
                    {"table": table.name, "column": column.name, "rows": count}
                )
        return reports
    finally:
        if bind is not conn:
            conn.close()


def upgrade() -> None:
    from app.storage.url_rewrite import NEW_PREFIX, OLD_PREFIX

    bind = op.get_bind()
    for report in _report(bind, OLD_PREFIX):
        print(
            f"[lp_files_url_rewrite] rewriting {report['rows']} row(s) in "
            f"{report['table']}.{report['column']}"
        )
    changed = _run(bind, OLD_PREFIX, NEW_PREFIX)
    if not changed:
        print("[lp_files_url_rewrite] no stored /files/ URLs found; nothing to rewrite")


def downgrade() -> None:
    from app.storage.url_rewrite import NEW_PREFIX, OLD_PREFIX

    changed = _run(op.get_bind(), NEW_PREFIX, OLD_PREFIX)
    if not changed:
        print("[lp_files_url_rewrite] downgrade: no /api/v1/files/ URLs found")
