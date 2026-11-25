"""Auto-generated natural keys.

Phase T/F1 batch: employees, departments, jobs, positions, locations and
cost centers no longer force the caller to invent a human identifier.
When the create payload omits it, the endpoint asks `next_code` for the
next free identifier in the household's prefix family (EMP-0007, DEP-0004,
...). Explicit values still win — the generator only fills silence.
"""
import re
from typing import Any, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")

_NUM_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _num_re(prefix: str) -> re.Pattern[str]:
    re_obj = _NUM_RE_CACHE.get(prefix)
    if re_obj is None:
        re_obj = re.compile(re.escape(prefix) + r"(\d+)$")
        _NUM_RE_CACHE[prefix] = re_obj
    return re_obj


def next_code(
    db: Session,
    model: type[ModelT],
    column: Any,
    prefix: str,
    *,
    width: int = 4,
) -> str:
    """Return the next free identifier for `column`, e.g. EMP-0007.

    Scans the identifiers that share `prefix`, takes the largest numeric
    suffix, and walks forward until the candidate is free (a rare
    mid-sequence collision — e.g. someone created EMP-0006 by hand —
    costs one extra step, never an error).
    """
    existing_rows = (
        db.query(column).filter(column.like(prefix + "%")).all()
    )
    used: set[int] = set()
    num_re = _num_re(prefix)
    for row in existing_rows:
        code = row[0] if isinstance(row, tuple) else row
        m = num_re.match(str(code or ""))
        if m:
            used.add(int(m.group(1)))
    n = (max(used) + 1) if used else 1
    while True:
        candidate = f"{prefix}{n:0{width}d}"
        clash = (
            db.query(column)
            .filter(column == candidate)
            .first()
        )
        if not clash:
            return candidate
        n += 1
