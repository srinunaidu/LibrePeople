"""The ``REQUIRES_RULE_PACK`` sentinel.

A preset carries no jurisdiction. It therefore cannot know a tax rate, a
contribution percentage, a statutory leave entitlement, a minimum wage or a
pay floor, and it must not guess one. Every slot that can only be filled
from a jurisdiction rule pack carries this literal marker instead of a
number, and the server refuses to treat the slot as configured until a
verified rule pack resolves it.

The marker is a string. It is never a number and never ``null``, so a
missing value and a deferred value can never be confused.
"""
from __future__ import annotations

from typing import Any

#: The literal marker for a slot that only a rule pack can fill.
SENTINEL = "REQUIRES_RULE_PACK"


def is_sentinel(value: Any) -> bool:
    """True when the value is the sentinel itself."""
    return isinstance(value, str) and value == SENTINEL


def contains_sentinel(value: Any) -> bool:
    """True when the sentinel appears anywhere inside a JSON value.

    Walks dictionaries and lists. A configuration block that still holds the
    sentinel is a block that is not finished, and the readiness check says
    so rather than letting the tenant believe it is configured.
    """
    if is_sentinel(value):
        return True
    if isinstance(value, dict):
        return any(contains_sentinel(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_sentinel(item) for item in value)
    return False


def sentinel_paths(value: Any, prefix: str = "") -> list[str]:
    """Every path inside a JSON value that holds the sentinel.

    A path is a dotted string; a list element is written as ``[index]``.
    """
    found: list[str] = []
    if is_sentinel(value):
        return [prefix or "<root>"]
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            found.extend(sentinel_paths(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(sentinel_paths(item, f"{prefix}[{index}]"))
    return found
