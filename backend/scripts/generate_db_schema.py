"""Generate ``docs/DB_SCHEMA.sql`` from the SQLAlchemy models.

Why a generator
---------------
The schema used to be a hand-written document. It drifted: it still said
that ``create_all()`` creates the schema, which stopped being true when
Alembic became the only schema-change path, and it covered the tables of
the first two phases rather than the tables that exist.

A document that is generated cannot drift. It is regenerated and committed,
and the test suite checks that the committed file is the one the models
produce.

What it emits
-------------
Oracle Autonomous Database DDL, because that is the production target:
the identity convention the models use, ``VARCHAR2`` for strings, ``CLOB``
for long text, ``NUMBER`` for numbers, ``TIMESTAMP`` for date-times, and
a foreign key on every relationship.

It is a *description* of the schema, not a way to build it. The way to
build it is the Alembic migrations, which is why the header says so.
"""
from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

OUTPUT = REPO_ROOT / "docs" / "DB_SCHEMA.sql"


def _load_metadata():
    from app.core.database import Base

    import app.models

    for _finder, name, _is_pkg in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f"app.models.{name}")

    from app.core.idempotency import IdempotencyRecord  # noqa: F401

    return Base.metadata


def _oracle_type(column) -> str:
    """The Oracle type of a column."""
    from sqlalchemy import (
        Boolean,
        Date,
        DateTime,
        Integer,
        Numeric,
        Text,
    )

    python_type = column.type
    if isinstance(python_type, Boolean):
        return "NUMBER(1)"
    if isinstance(python_type, Integer):
        return "NUMBER"
    if isinstance(python_type, Numeric):
        if python_type.precision and python_type.scale:
            return f"NUMBER({python_type.precision},{python_type.scale})"
        return "NUMBER"
    if isinstance(python_type, DateTime):
        return "TIMESTAMP"
    if isinstance(python_type, Date):
        return "DATE"
    if isinstance(python_type, Text):
        return "CLOB"
    length = getattr(python_type, "length", None)
    if length:
        return f"VARCHAR2({length})"
    return "VARCHAR2(255)"


def _is_identity(column) -> bool:
    """Whether the column uses the identity convention."""
    from sqlalchemy import Identity

    return isinstance(column.identity, Identity)


def _default_clause(column) -> str:
    """The DEFAULT clause of a column, if it has one."""
    default = column.default
    if default is not None and not default.is_sequence:
        value = getattr(default, "arg", None)
        if value is not None:
            if callable(value):
                # A Python-side default. Its repr carries a memory
                # address, so it must never reach the file: the document
                # has to be byte-for-byte reproducible.
                return _callable_default(value)
            if isinstance(value, bool):
                return f" DEFAULT {1 if value else 0}"
            if isinstance(value, (int, float)):
                return f" DEFAULT {value}"
            text = str(value)
            if "now(" in text.lower() or "CURRENT_TIMESTAMP" in text.upper():
                return " DEFAULT CURRENT_TIMESTAMP"
            return f" DEFAULT '{text}'"

    # A server default is a string of SQL in the dialect's own words.
    server_default = column.server_default
    if server_default is None:
        return ""
    text = str(getattr(server_default, "arg", server_default))
    if "now(" in text.lower() or "current_timestamp" in text.lower():
        return " DEFAULT CURRENT_TIMESTAMP"
    if text.strip():
        return f" DEFAULT {text.strip()}"
    return ""


def _callable_default(value) -> str:
    """The DEFAULT clause for a Python-side callable default."""
    try:
        import inspect

        source = inspect.getsource(value)
    except Exception:  # noqa: BLE001
        return ""
    if "now(" in source.lower():
        return " DEFAULT CURRENT_TIMESTAMP"
    if "utcnow" in source.lower():
        return " DEFAULT CURRENT_TIMESTAMP"
    # The default is applied by the application; the column keeps its
    # not-null constraint and the database is told nothing.
    return ""


def _references(column) -> str | None:
    """The foreign key target of a column."""
    for foreign_key in column.foreign_keys:
        target = foreign_key.target_fullname.split(".")[0]
        return target
    return None


def render(metadata) -> str:
    """The whole document."""
    lines: list[str] = []
    lines.append("-- Karmathy HCM — database schema")
    lines.append("--")
    lines.append("-- GENERATED FILE. Do not edit it by hand.")
    lines.append("--")
    lines.append("-- Regenerate it with:")
    lines.append("--     cd backend && .venv/bin/python scripts/generate_db_schema.py")
    lines.append("--")
    lines.append("-- This is a description of the schema, not a way to build it.")
    lines.append("-- The schema is built by the Alembic migrations in")
    lines.append("-- `backend/migrations/`, which is the only schema-change path.")
    lines.append("-- `create_all()` is never used outside local development.")
    lines.append("--")
    lines.append("-- Target: Oracle Autonomous Database.")
    lines.append("-- The identity convention is the one the models use:")
    lines.append("-- `GENERATED BY DEFAULT AS IDENTITY`.")
    lines.append("")

    tables = sorted(metadata.tables.values(), key=lambda table: table.name)
    for table in tables:
        if table.name in ("alembic_version", "sqlite_sequence"):
            continue
        lines.append(f"-- {table.name}")
        lines.append(f"CREATE TABLE {table.name} (")
        definitions: list[str] = []
        for column in table.columns:
            piece = f"    {column.name:<28} {_oracle_type(column)}"
            if _is_identity(column):
                piece += " GENERATED BY DEFAULT AS IDENTITY"
            if not column.nullable and not column.primary_key:
                piece += " NOT NULL"
            if column.unique and not column.primary_key:
                piece += " UNIQUE"
            default = _default_clause(column)
            if default and not _is_identity(column):
                piece += default
            target = _references(column)
            if target:
                piece += f" REFERENCES {target}(id)"
            definitions.append(piece)
        # The key is stated once, at table level. Stating it inline as well
        # produced a document with two PRIMARY KEY clauses for a table whose
        # key is not an identity column, which Oracle rejects.
        primary_key = ", ".join(
            column.name for column in table.primary_key.columns
        )
        definitions.append(f"    PRIMARY KEY ({primary_key})" if primary_key else "")
        lines.append(",\n".join(part for part in definitions if part))
        lines.append(");")
        lines.append("")

        indexes = sorted(table.indexes, key=lambda index: index.name or "")
        for index in indexes:
            columns = ", ".join(column.name for column in index.columns)
            unique = "UNIQUE " if index.unique else ""
            lines.append(
                f"CREATE {unique}INDEX {index.name} ON {table.name} ({columns});"
            )
        if indexes:
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the committed file differs from what the models produce.",
    )
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args(argv)

    metadata = _load_metadata()
    document = render(metadata)
    target = Path(args.output)

    if args.check:
        if not target.exists():
            print(f"generate_db_schema: {target} does not exist")
            return 1
        if target.read_text(encoding="utf-8") != document:
            print(
                f"generate_db_schema: {target} is out of date with the models.\n"
                f"  Regenerate it with: python scripts/generate_db_schema.py"
            )
            return 1
        print(f"generate_db_schema: {target.name} is up to date")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    print(f"generate_db_schema: wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
