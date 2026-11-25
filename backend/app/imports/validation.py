"""Turning a cell into a value, and saying why it could not be one.

Every value in an import passes through :func:`coerce_value`. It returns the
value to write, or an error explaining what was wrong with the cell.

The rules
---------
*Dates are ISO 8601.* ``YYYY-MM-DD`` for a date, ``YYYY-MM-DDTHH:MM:SS``
for a date-time, ``HH:MM`` for a time. Nothing else is accepted. The
previous implementation also accepted ``31/12/2026`` and ``12/31/2026``,
which is ambiguous between two conventions and silently means different
things on different sides of the Atlantic.

*Enums are closed.* A column with an allowed set accepts only those values.
The comparison ignores case and the value is stored in the canonical
spelling, so ``active`` is accepted and stored as ``Active``.

*Personal values are masked.* A column marked sensitive in the entity
contract produces a message that describes the rule without quoting the
data. A salary that is out of range is reported as "must be between 0 and
100000" — never as "500000 is out of range".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.imports.errors import ErrorCode, RowError
from app.imports.headers import neutralise_formula_injection
from app.imports.spec import ColumnSpec

#: Accepted boolean spellings.
TRUE_VALUES = frozenset({"1", "true", "yes", "y", "t", "on"})
FALSE_VALUES = frozenset({"0", "false", "no", "n", "f", "off", ""})

#: The kinds whose values are free text, and to which the formula-injection
#: neutraliser applies.
TEXT_KINDS = frozenset({"text", "code"})


@dataclass(frozen=True)
class ImportBounds:
    """The limits the tenant's configuration places on imported values.

    These come from the deployment's configuration, which under the
    one-customer-per-deployment model *is* the tenant configuration. They
    are read once per import so that every row in a file is judged against
    the same limits.
    """

    salary_min: float | None = None
    salary_max: float | None = None

    def salary_bounds(self) -> tuple[float | None, float | None]:
        return self.salary_min, self.salary_max


def _masked(column: ColumnSpec, template: str) -> str:
    """The message for a sensitive column: the rule, never the value."""
    return template.format(column=column.name)


def _described(column: ColumnSpec, value: str, template: str) -> str:
    """The message for a column that is not sensitive."""
    return template.format(column=column.name, value=value)


def coerce_value(
    column: ColumnSpec,
    raw: str,
    bounds: ImportBounds | None = None,
) -> tuple[object | None, RowError | None]:
    """Convert one cell to the type the column declares."""
    if column.kind in TEXT_KINDS:
        # A text value keeps its leading tab or carriage return, because
        # those are two of the characters that make a spreadsheet treat a
        # cell as a formula. Stripping them first would hide the trigger
        # from the neutraliser. Surrounding spaces are still removed.
        value = raw.strip(" ").rstrip()
    else:
        value = raw.strip()
    if value == "":
        return None, None

    # The length is checked before the neutraliser runs, so that the quote
    # the neutraliser adds does not count against the column's limit.
    if column.max_length and len(value) > column.max_length:
        if column.sensitive:
            message = (
                f"'{column.name}' must be at most {column.max_length} characters"
            )
        else:
            message = (
                f"'{value}' is longer than '{column.name}'s limit of "
                f"{column.max_length} characters"
            )
        return None, RowError(0, column.name, ErrorCode.TOO_LONG, message)

    if column.kind in TEXT_KINDS:
        value = neutralise_formula_injection(value)

    if column.kind == "integer":
        return _coerce_integer(column, value)
    if column.kind == "decimal":
        return _coerce_decimal(column, value)
    if column.kind == "boolean":
        return _coerce_boolean(column, value)
    if column.kind == "date":
        return _coerce_date(column, value)
    if column.kind == "datetime":
        return _coerce_datetime(column, value)
    if column.kind == "time":
        return _coerce_time(column, value)
    if column.kind == "email":
        return _coerce_email(column, value)
    return _coerce_text(column, value)


def _coerce_text(column: ColumnSpec, value: str) -> tuple[object, RowError | None]:
    return value, None


def _coerce_integer(column: ColumnSpec, value: str) -> tuple[object, RowError | None]:
    try:
        number = int(value)
    except ValueError:
        if column.sensitive:
            message = _masked(column, "'{column}' must be a whole number")
        else:
            message = _described(
                column, value, "'{value}' is not a whole number"
            )
        return None, RowError(0, column.name, ErrorCode.INVALID_INTEGER, message)
    return _check_range(column, number)


def _coerce_decimal(column: ColumnSpec, value: str) -> tuple[object, RowError | None]:
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        if column.sensitive:
            message = _masked(column, "'{column}' must be a number")
        else:
            message = _described(column, value, "'{value}' is not a valid number")
        return None, RowError(0, column.name, ErrorCode.INVALID_NUMBER, message)
    return _check_range(column, number)


def _check_range(column: ColumnSpec, number):
    low = column.minimum
    high = column.maximum
    if low is not None and number < low:
        if column.sensitive:
            message = f"'{column.name}' must be at least {low}"
        else:
            message = f"'{number}' is below the minimum for '{column.name}'"
        return None, RowError(
            0, column.name, ErrorCode.BELOW_MINIMUM, message,
        )
    if high is not None and number > high:
        if column.sensitive:
            message = f"'{column.name}' must be at most {high}"
        else:
            message = f"'{number}' is above the maximum for '{column.name}'"
        return None, RowError(
            0, column.name, ErrorCode.ABOVE_MAXIMUM, message,
        )
    return number, None


def _coerce_boolean(column: ColumnSpec, value: str) -> tuple[object, RowError | None]:
    lowered = value.lower()
    if lowered in TRUE_VALUES:
        return True, None
    if lowered in FALSE_VALUES:
        return False, None
    message = _described(
        column, value, "'{value}' is not a true/false value"
    )
    return None, RowError(0, column.name, ErrorCode.INVALID_BOOLEAN, message)


def _coerce_date(column: ColumnSpec, value: str) -> tuple[object, RowError | None]:
    try:
        return date.fromisoformat(value), None
    except ValueError:
        message = _described(
            column, value, "'{value}' is not an ISO 8601 date (YYYY-MM-DD)"
        )
        return None, RowError(0, column.name, ErrorCode.INVALID_DATE, message)


def _coerce_datetime(column: ColumnSpec, value: str) -> tuple[object, RowError | None]:
    try:
        return datetime.fromisoformat(value), None
    except ValueError:
        message = _described(
            column,
            value,
            "'{value}' is not an ISO 8601 date-time (YYYY-MM-DDTHH:MM:SS)",
        )
        return None, RowError(0, column.name, ErrorCode.INVALID_DATETIME, message)


def _coerce_time(column: ColumnSpec, value: str) -> tuple[object, RowError | None]:
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError:
        message = _described(
            column, value, "'{value}' is not a 24-hour time (HH:MM)"
        )
        return None, RowError(0, column.name, ErrorCode.INVALID_TIME, message)
    return parsed.strftime("%H:%M"), None


def _coerce_email(column: ColumnSpec, value: str) -> tuple[object, RowError | None]:
    local, _, domain = value.partition("@")
    if not local or not domain or "." not in domain or " " in value:
        # The value is personal, so the message describes the rule and the
        # column and never quotes what was typed.
        message = _masked(column, "'{column}' must be an email address")
        return None, RowError(0, column.name, ErrorCode.INVALID_EMAIL, message)
    return value, None


def check_enum(column: ColumnSpec, value: object) -> RowError | None:
    """Whether a value is one of the column's allowed values."""
    if not column.enum or value is None:
        return None
    text = str(value)
    for allowed in column.enum:
        if allowed.lower() == text.lower():
            return None
    message = (
        f"'{text}' is not allowed for '{column.name}' "
        f"(allowed: {', '.join(column.enum)})"
    )
    return RowError(0, column.name, ErrorCode.INVALID_ENUM, message)


def canonical_enum_value(column: ColumnSpec, value: object) -> object:
    """The canonical spelling of an enum value."""
    if not column.enum or value is None:
        return value
    text = str(value)
    for allowed in column.enum:
        if allowed.lower() == text.lower():
            return allowed
    return value
