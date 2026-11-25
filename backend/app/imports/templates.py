"""Building the CSV template an operator downloads.

The template is the header row plus one example row. The header row is the
entity's canonical columns; the example row shows what a valid value looks
like for each of them.

The example row is generated from the contract, so it cannot drift from it:
a column that is added to the contract appears in the template with an
example that satisfies its own rules.
"""
from __future__ import annotations

import csv
import io

from app.imports.spec import ColumnSpec, EntitySpec, get_spec


def example_value(column: ColumnSpec) -> str:
    """A value that satisfies the column's own rules."""
    if column.name == "employee_id":
        return "EMP-0001"
    if column.name == "employee_number":
        return "EMP-0001"
    if column.name == "entitlement_year":
        return "2026"
    if column.name in ("entitled_days", "carried_over_days", "used_days"):
        return "20.0"
    if column.name in ("break_minutes", "max_days_per_year"):
        return "30"
    if column.kind == "integer":
        return "1"
    if column.kind == "decimal":
        return "1000.00"
    if column.kind == "boolean":
        return "true"
    if column.kind == "date":
        return "2026-01-15"
    if column.kind == "datetime":
        return "2026-01-15T09:00:00"
    if column.kind == "time":
        return "09:00"
    if column.kind == "email":
        return "ada@example.com"
    if column.enum:
        return column.enum[0]
    if column.reference_by == "natural":
        return "REF-001"
    if column.reference:
        return "1"
    if column.name == "code":
        return "EXM-01"
    if column.name in ("start_time", "end_time"):
        return "09:00"
    if column.name == "timezone":
        return "Europe/London"
    if column.name == "name":
        return "Example"
    if column.name == "title":
        return "Example Title"
    if column.name == "first_name":
        return "Ada"
    if column.name == "last_name":
        return "Lovelace"
    return "Example"


def build_template(entity: str) -> str:
    """A CSV template for one entity."""
    spec = get_spec(entity)
    if spec is None:
        raise KeyError(entity)
    return build_template_for(spec)


def build_template_for(spec: EntitySpec) -> str:
    """A CSV template for an entity contract.

    One column per requirement group. A column that exists only as an
    alternative to another is left out: a template that offers both
    ``job_id`` and ``job_code`` tells the operator to fill in both.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    columns = [
        column for column in spec.primary_columns if column.name != "id"
    ]
    writer.writerow([column.name for column in columns])
    writer.writerow([example_value(column) for column in columns])
    return buffer.getvalue()
