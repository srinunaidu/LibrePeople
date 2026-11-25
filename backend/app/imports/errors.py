"""Row-level error reporting.

Every error a row can fail with has a stable code. The code is what a
client branches on and what a golden file asserts; the message is for the
operator reading the row-error CSV.

Two rules govern the message:

*It names the column and the rule.* "hire_date is not a valid ISO 8601 date"
is actionable. "invalid value" is not.

*It never contains a personal value.* A column marked sensitive in the
entity contract produces a message that describes the rule without quoting
the data. This applies to the message, to the row-error CSV, and to anything
written to a log.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ErrorCode:
    """The catalogue of row-level error codes."""

    #: The file's header row contains a header this entity does not accept.
    UNKNOWN_HEADERS = "unknown_headers"
    #: A required column (or one of its alternatives) is absent or blank.
    MISSING_REQUIRED = "missing_required"
    #: A value is not a whole number.
    INVALID_INTEGER = "invalid_integer"
    #: A value is not a number.
    INVALID_NUMBER = "invalid_number"
    #: A value is not a recognised boolean.
    INVALID_BOOLEAN = "invalid_boolean"
    #: A value is not an ISO 8601 date.
    INVALID_DATE = "invalid_date"
    #: A value is not an ISO 8601 date-time.
    INVALID_DATETIME = "invalid_datetime"
    #: A value is not a 24-hour HH:MM time.
    INVALID_TIME = "invalid_time"
    #: A value is not an email address.
    INVALID_EMAIL = "invalid_email"
    #: A value is not one of the allowed values for the column.
    INVALID_ENUM = "invalid_enum"
    #: A value is longer than the column allows.
    TOO_LONG = "too_long"
    #: A number is below the configured lower bound.
    BELOW_MINIMUM = "below_minimum"
    #: A number is above the configured upper bound.
    ABOVE_MAXIMUM = "above_maximum"
    #: The row names a record that does not exist.
    REFERENCE_NOT_FOUND = "reference_not_found"
    #: The row names a record that does not exist, in another file.
    CROSS_FILE_REFERENCE_NOT_FOUND = "cross_file_reference_not_found"
    #: An earlier row in the same file has the same natural key.
    DUPLICATE_IN_FILE = "duplicate_in_file"
    #: The row's natural key collides with another unique column.
    DUPLICATE_EXISTS = "duplicate_exists"
    #: Two columns in the row disagree (e.g. min_salary above max_salary).
    INCONSISTENT_VALUES = "inconsistent_values"
    #: The file has more rows than the configured limit.
    TOO_MANY_ROWS = "too_many_rows"
    #: The file is larger than the configured limit.
    FILE_TOO_LARGE = "file_too_large"
    #: The file is not valid UTF-8.
    NOT_UTF8 = "not_utf8"
    #: The file is not parseable as RFC 4180 CSV.
    MALFORMED_CSV = "malformed_csv"
    #: The file is empty.
    EMPTY_FILE = "empty_file"
    #: The file has no header row.
    NO_HEADER = "no_header"
    #: The row could not be written. The detail is in the server log.
    WRITE_FAILED = "write_failed"
    #: The row has more values than the header declares.
    TOO_MANY_FIELDS = "too_many_fields"
    #: The row has fewer values than the header declares.
    TOO_FEW_FIELDS = "too_few_fields"
    #: The row would move a leave balance in a way the leave ledger
    #: cannot record. The ledger adds days to a balance; it does not take
    #: them off, so a file that lowers a balance is refused.
    LEDGER_REDUCTION_REFUSED = "ledger_reduction_refused"
    #: The row would leave a leave balance with no ledger row behind it,
    #: which is a balance the reconciliation cannot see.
    LEDGER_NO_MOVEMENT = "ledger_no_movement"


#: Codes that describe the file as a whole rather than one row.
FILE_LEVEL_CODES = frozenset({
    ErrorCode.UNKNOWN_HEADERS,
    ErrorCode.TOO_MANY_ROWS,
    ErrorCode.FILE_TOO_LARGE,
    ErrorCode.NOT_UTF8,
    ErrorCode.MALFORMED_CSV,
    ErrorCode.EMPTY_FILE,
    ErrorCode.NO_HEADER,
})


@dataclass
class RowError:
    """One problem with one row of one file."""

    row: int
    column: str | None
    code: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "row": self.row,
            "column": self.column,
            "code": self.code,
            "message": self.message,
        }

    def as_row(self) -> list[Any]:
        """The row-error CSV representation."""
        return [self.row, self.column or "", self.code, self.message]


@dataclass
class RowOutcome:
    """What happened to one row."""

    row: int
    status: str  # create | update | unchanged | reject
    errors: list[RowError] = field(default_factory=list)
    natural_key: tuple | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"row": self.row, "status": self.status}
        if self.errors:
            out["errors"] = [e.as_dict() for e in self.errors]
        return out


class ImportFileError(Exception):
    """A file cannot be imported at all.

    The limits (size, row count) and the header rules are not row errors: a
    file that breaks them is refused as a whole, because the operator's next
    action is to produce a different file, not to read a list of bad rows.
    """

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class ImportLimitError(ImportFileError):
    """Raised when a file breaks a hard limit and cannot be analysed."""
