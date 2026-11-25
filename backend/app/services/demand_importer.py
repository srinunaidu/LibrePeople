"""Driver CSV importer for demand forecasting.

Accepts an external driver file (POS sales, foot traffic, patient census, ...)
and produces the same per-day demand series shape as :mod:`app.services.demand`.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any, Optional

from app.services.demand import DemandPoint

DATE_COLUMNS = ("date", "day", "work_date", "period", "ds")
VALUE_COLUMNS = ("value", "hours", "demand", "quantity", "amount", "y")
LOCATION_COLUMNS = ("location", "location_code", "location_id")
ROLE_COLUMNS = ("role", "role_code", "job", "job_code", "job_id")


class DriverCSVError(ValueError):
    """Raised when a driver CSV cannot be parsed/validated."""


def _read_text(content: Any) -> str:
    if isinstance(content, (bytes, bytearray)):
        return content.decode("utf-8-sig")
    if hasattr(content, "read"):
        raw = content.read()
        if isinstance(raw, (bytes, bytearray)):
            return raw.decode("utf-8-sig")
        return str(raw)
    return str(content)


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        raise DriverCSVError("date is required")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # ISO with time
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    raise DriverCSVError(f"invalid date: {text!r}")


def _parse_value(value: Any) -> float:
    text = str(value).strip()
    if text == "":
        raise DriverCSVError("value is required")
    try:
        return float(text)
    except (TypeError, ValueError):
        raise DriverCSVError(f"invalid value: {text!r}")


def _pick(columns: list[str], candidates: tuple[str, ...]) -> Optional[str]:
    lower = {c.strip().lower(): c for c in columns}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def parse_driver_csv(
    content: Any,
    *,
    date_column: Optional[str] = None,
    value_column: Optional[str] = None,
    location_column: Optional[str] = None,
    role_column: Optional[str] = None,
) -> list[DemandPoint]:
    text = _read_text(content)
    if not text.strip():
        raise DriverCSVError("empty CSV")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise DriverCSVError("CSV has no header row")
    columns = list(reader.fieldnames)

    date_col = date_column or _pick(columns, DATE_COLUMNS)
    value_col = value_column or _pick(columns, VALUE_COLUMNS)
    if date_col is None:
        raise DriverCSVError("missing date column")
    if value_col is None:
        raise DriverCSVError("missing value column")

    loc_col = location_column or _pick(columns, LOCATION_COLUMNS)
    role_col = role_column or _pick(columns, ROLE_COLUMNS)

    out: list[DemandPoint] = []
    for row in reader:
        if row is None:
            continue
        # Skip completely blank lines.
        if all((v is None or str(v).strip() == "") for v in row.values()):
            continue
        d = _parse_date(row.get(date_col))
        v = _parse_value(row.get(value_col))
        loc = row.get(loc_col).strip() if (loc_col and row.get(loc_col) is not None) else None
        role = row.get(role_col).strip() if (role_col and row.get(role_col) is not None) else None
        try:
            loc_id = int(loc) if loc is not None and loc != "" else None
        except (TypeError, ValueError):
            loc_id = None
        out.append(
            DemandPoint(
                date=d,
                value=v,
                location_code=None if loc_id is not None else loc,
                location_id=loc_id,
                role=role,
                source="driver",
            )
        )
    if not out:
        raise DriverCSVError("CSV contained no data rows")
    out.sort(key=lambda p: p["date"])
    return out


# Aliases / alternative names.
import_driver_csv = parse_driver_csv
load_driver_csv = parse_driver_csv
read_driver_csv = parse_driver_csv
parse_csv = parse_driver_csv


class DriverCSVImporter:
    def __init__(self, db=None):
        self.db = db

    def parse(self, content, **kwargs):
        return parse_driver_csv(content, **kwargs)

    import_csv = parse
    load = parse
