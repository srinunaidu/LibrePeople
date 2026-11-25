"""Rewrite stored ``/files/`` URLs to the authorised download route (item 9).

``LocalStorage.url_for`` used to return the static path ``/files/<key>``,
which the removed ``StaticFiles`` mount served to any caller, unauthenticated.
Documents are now served through ``GET /api/v1/files/{path}`` (see
:mod:`app.main`), so stored values are rewritten from the old prefix to the
new one.

The Alembic migration ``migrations/versions/lp_files_url_rewrite.py`` runs
this logic; ``scripts/verify_files_urls.py`` reports values that still
carry the old prefix.
"""

from __future__ import annotations

from typing import Iterator

from sqlalchemy import Connection, Engine, MetaData, String, Table, Text, func, inspect, select

#: The unauthenticated prefix values were stored under.
OLD_PREFIX = "/files/"
#: The authenticated prefix they are stored under now.
NEW_PREFIX = "/api/v1/files/"

_TEXT_COLUMN_TYPES = (String, Text)


def _text_columns(bind) -> Iterator[tuple[Table, object]]:
    """Yield ``(table, column)`` for every string column in the database."""
    metadata = MetaData()
    for table_name in inspect(bind).get_table_names():
        table = Table(table_name, metadata, autoload_with=bind)
        for column in table.columns:
            if isinstance(column.type, _TEXT_COLUMN_TYPES):
                yield table, column


def _rewrite_prefix(conn: Connection, old_prefix: str, new_prefix: str) -> list[str]:
    """Rewrite ``old_prefix`` to ``new_prefix`` in every text column."""
    changed: list[str] = []
    for table, column in _text_columns(conn):
        statement = (
            table.update()
            .values({column: func.replace(column, old_prefix, new_prefix)})
            .where(column.like(f"{old_prefix}%"))
        )
        if conn.execute(statement).rowcount:
            changed.append(f"{table.name}.{column.name}")
    return changed


def rewrite_prefix(bind, old_prefix: str, new_prefix: str) -> list[str]:
    """Rewrite the old prefix to the new one; returns names of updated columns.

    Idempotent: after a successful run, :func:`count_legacy_files_urls`
    reports nothing. Accepts a :class:`Connection` (commits nothing itself)
    or an :class:`Engine` (commits at the end).
    """
    if isinstance(bind, Engine):
        with bind.begin() as conn:
            return _rewrite_prefix(conn, old_prefix, new_prefix)
    return _rewrite_prefix(bind, old_prefix, new_prefix)


def rewrite_stored_files_urls(bind) -> list[str]:
    """Rewrite the stored ``/files/`` prefix to :data:`NEW_PREFIX`."""
    return rewrite_prefix(bind, OLD_PREFIX, NEW_PREFIX)


def count_legacy_files_urls(bind) -> list[dict]:
    """Report every text column still holding values under :data:`OLD_PREFIX`."""
    reports: list[dict] = []
    conn = bind.connect() if isinstance(bind, Engine) else bind
    try:
        for table, column in _text_columns(conn):
            count = conn.execute(
                select(func.count())
                .select_from(table)
                .where(column.like(f"{OLD_PREFIX}%"))
            ).one()[0]
            if count:
                reports.append(
                    {"table": table.name, "column": column.name, "rows": count}
                )
    finally:
        if bind is not conn:
            conn.close()
    return reports
