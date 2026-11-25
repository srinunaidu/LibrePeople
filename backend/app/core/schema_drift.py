"""Compare the live database schema with the SQLAlchemy models.

The platform was deployed before Alembic existed: the schema was built
by ``Base.metadata.create_all()`` from the models as they were at the time.
The models have moved on since, so a table the deployment created can be
missing a column the code now expects. The frozen baseline deliberately
does not evolve those tables, so the drift is invisible until a query
fails at runtime — which is what happened to the payroll run listing.

This module reports the difference. It only reads the schema; it never
changes anything.

Oracle folds unquoted identifiers to upper case, so the comparison is
case-insensitive: a model that says ``pay_runs`` is matched to the
catalog's ``PAY_RUNS``.
"""
from __future__ import annotations

import importlib
import pkgutil
import re
from typing import Any

#: Tables that belong to the platform rather than to the application.
IGNORED_TABLES = {
    "alembic_version",
    "sqlite_sequence",
}


def _model_metadata() -> Any:
    """Return the metadata with every model module imported.

    A relationship whose target has not been imported fails to resolve, so
    every model module has to be loaded before the metadata is complete.
    """
    from app.core.database import Base

    import app.models
    from app.core.idempotency import IdempotencyRecord  # noqa: F401

    for _finder, name, is_pkg in pkgutil.iter_modules(app.models.__path__):
        if is_pkg:
            continue
        importlib.import_module(f"app.models.{name}")

    return Base.metadata


def _type_family(value: str) -> str:
    """The class a type name belongs to.

    The dialects render the same type differently and some are
    interchangeable in practice, so the comparison is by class rather than
    by spelling:

    * a boolean is stored as a whole number on both Oracle and SQLite, so
      it is the same class as an integer;
    * a decimal is a numeric column whose scale the catalog may not
      record, so it is the same class as a plain number.
    """
    value = (value or "").upper()
    if "VARCHAR" in value or "CHAR" in value or "TEXT" in value or "CLOB" in value:
        return "text"
    if "TIMESTAMP" in value or "DATETIME" in value or value.startswith("DATE"):
        return "datetime"
    if "BOOLEAN" in value or "BOOL" in value:
        return "number"
    if "FLOAT" in value or "DOUBLE" in value or "REAL" in value:
        return "float"
    if (
        "NUMBER" in value
        or "NUMERIC" in value
        or "DECIMAL" in value
        or "INT" in value
    ):
        return "number"
    return value


def schema_drift_report() -> dict[str, Any]:
    """Report the difference between the models and the live schema.

    Returns a dictionary with:

    ``missing_tables``
        Tables the models expect that the database does not have.
    ``missing_columns``
        Columns the models expect that the database does not have, keyed
        by table.
    ``extra_columns``
        Columns the database has that the models do not declare, keyed by
        table.
    ``type_mismatches``
        Columns whose type differs between the model and the database,
        keyed by table.
    ``inspection_errors``
        Tables whose columns could not be read, keyed by table.
    ``in_sync``
        True when nothing is missing.
    """
    from app.core.database import engine

    metadata = _model_metadata()
    inspector = inspect_engine(engine)

    # Oracle folds unquoted identifiers to upper case, so the two sets are
    # compared without regard to case and each model table is looked up
    # under the name the catalog actually uses.
    live_by_fold = {name.upper(): name for name in inspector.get_table_names()}

    missing_tables: list[str] = []
    extra_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}
    extra_columns: dict[str, list[str]] = {}
    type_mismatches: dict[str, list[str]] = {}
    inspection_errors: dict[str, str] = {}
    live_table_columns: dict[str, list[str]] = {}

    for table_name in sorted(metadata.tables):
        if table_name.upper() in IGNORED_TABLES:
            continue
        live_name = live_by_fold.get(table_name.upper())
        if live_name is None:
            missing_tables.append(table_name)
            continue

        table = metadata.tables[table_name]
        try:
            raw_columns = {
                col["name"]: col for col in inspector.get_columns(live_name)
            }
        except Exception as exc:  # noqa: BLE001
            inspection_errors[table_name] = f"{type(exc).__name__}: {exc}"
            continue

        # The comparison is case-insensitive on both sides. Oracle folds
        # unquoted identifiers to upper case, and SQLAlchemy quotes the
        # ones that are reserved words, so the same column can be spelled
        # either way. The folding is done here, on both sides, so it
        # cannot depend on how the names were collected.
        live_names = {str(name).casefold() for name in raw_columns}
        model_names = {
            str(column.name).casefold(): column for column in table.columns
        }

        # The names the catalog actually uses, so the difference between
        # the model and the database is visible and not just a summary.
        live_table_columns[table_name] = sorted(raw_columns)

        absent = sorted(name for name in model_names if name not in live_names)
        if absent:
            missing_columns[table_name] = [model_names[n].name for n in absent]

        surplus = sorted(live_names - set(model_names))
        if surplus:
            extra_columns[table_name] = sorted(surplus)

        mismatched = []
        for folded, column in model_names.items():
            live = next(
                (
                    raw_columns[name]
                    for name in raw_columns
                    if str(name).casefold() == folded
                ),
                None,
            )
            if live is None:
                continue
            model_type = str(column.type)
            live_type = str(live.get("type"))
            if _type_family(model_type) != _type_family(live_type):
                mismatched.append(
                    f"{column.name}: model {model_type}, db {live_type}"
                )
        if mismatched:
            type_mismatches[table_name] = sorted(mismatched)

    for live_name in sorted(live_by_fold.values()):
        if live_name.upper() in IGNORED_TABLES:
            continue
        if live_name.upper() not in {name.upper() for name in metadata.tables}:
            extra_tables.append(live_name)

    return {
        "missing_tables": missing_tables,
        "extra_tables": extra_tables,
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
        "type_mismatches": type_mismatches,
        "inspection_errors": inspection_errors,
        "live_columns": live_table_columns,
        # A marker so the running version of this report is identifiable.
        "comparison": "case-insensitive",
        "in_sync": not missing_tables and not missing_columns,
    }


def inspect_engine(engine: Any) -> Any:
    """Wrap ``sqlalchemy.inspect`` so the import stays local."""
    from sqlalchemy import inspect

    return inspect(engine)
