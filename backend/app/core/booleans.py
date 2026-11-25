"""Boolean predicates that compile on every backend this product supports.

Why this file exists
--------------------
`Column.is_(True)` looks like the idiomatic way to say "the flag is set". It is
not portable. On a backend with a native boolean it renders ``col IS true``; on
Oracle, where the column is ``NUMBER(1)``, it renders ``col IS 1`` — and Oracle
requires the ``NULL`` keyword after ``IS``, so that is a parse error:

    ORA-00908: missing NULL keyword

Every list endpoint that used the idiom therefore answered **503** in
production while passing on the SQLite the test suites run against. Two
requests failed that way after each deploy before anyone read the log, because
the screens that call those endpoints swallow a failed list into an empty one
(D-035).

``is_true(column)`` renders ``col = 1`` on Oracle and ``col = 1`` on SQLite, and
``is_false(column)`` renders ``col = 0``. Both say what the caller means, and
both run.

Use these instead of ``.is_(True)`` / ``.is_(False)`` on a boolean column.
``schema_alignment_test_suite`` fails the build if the old idiom returns.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import false, true


def is_true(column: Any):
    """The predicate "this boolean column is true", portable across backends."""
    return column == true()


def is_false(column: Any):
    """The predicate "this boolean column is false", portable across backends."""
    return column == false()


__all__ = ["is_false", "is_true"]
