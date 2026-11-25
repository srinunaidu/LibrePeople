"""Where a statutory value may never appear in a preset.

Two rules, both enforced by the loader and both walked by the test suite:

1. **The declared slots.** Every slot in the preset schema that can hold a
   number a statute might set is listed here. In a preset those slots hold
   the sentinel, never a number.
2. **The named slots.** A key whose name says it holds a rate, a
   contribution, an entitlement or a floor may never hold a number either,
   whatever the schema says about it. This is the backstop: a new key that
   somebody adds to a preset cannot smuggle a statutory number in under a
   name the first list does not know.

The second rule is deliberately broad. A preset that cannot state a
statutory number is worth more than a preset that can state one it picked
itself.
"""
from __future__ import annotations

from typing import Any, Iterable

from app.core.presets.sentinel import SENTINEL, is_sentinel

#: The slots whose value a statute may set. A path segment of ``*``
#: matches one list index.
#:
#: Every one of them carries the sentinel in a preset.
STATUTORY_SLOTS: tuple[tuple[str, ...], ...] = (
    # Working time: the break length, and whether the rule is statutory.
    ("configuration", "time", "break_rules", "*", "duration_minutes"),
    ("configuration", "time", "break_rules", "*", "jurisdiction_specific"),
    # Leave: the entitlement, the accrual rhythm, the caps and the
    # carry-over, and whether leave may be paid out.
    ("configuration", "leave", "leave_types", "*", "entitlement_days"),
    ("configuration", "leave", "leave_types", "*", "accrual", "frequency"),
    ("configuration", "leave", "leave_types", "*", "accrual", "max_balance_days"),
    (
        "configuration",
        "leave",
        "leave_types",
        "*",
        "accrual",
        "tenure_tiers",
        "*",
        "days",
    ),
    ("configuration", "leave", "leave_types", "*", "carry_over_limit_days"),
    ("configuration", "leave", "leave_types", "*", "expiry_rule"),
    ("configuration", "leave", "leave_types", "*", "encashment_allowed"),
    # Payroll: the statutory components and the statutory leave pay.
    ("configuration", "payroll", "statutory_components", "*", "rate"),
    ("configuration", "payroll", "statutory_leave_pay", "leave_pay_rate"),
    # Recruiting: the consent scope, which data-protection law usually sets.
    ("configuration", "recruiting", "background_check_consent_scope"),
    # Scheduling: the rostered break, the minimum rest and the run of days.
    ("configuration", "scheduling", "shift_templates", "*", "break_length_minutes"),
    ("configuration", "scheduling", "shift_templates", "*", "minimum_rest_hours"),
    ("configuration", "scheduling", "shift_templates", "*", "max_consecutive_days"),
)

#: A key whose name carries one of these words may never hold a number.
#:
#: The list is the backstop, not the rule: it exists so that a key nobody
#: thought about cannot carry a rate.
STATUTORY_KEYWORDS: tuple[str, ...] = (
    "contribution",
    "entitlement",
    "minimum_wage",
    "notice_period",
    "pay_floor",
    "percentage",
    "percent",
    "rate",
    "social_security",
    "statutory",
    "tax",
    "wage_floor",
)


def _matches(pattern: tuple[str, ...], path: tuple[str, ...]) -> bool:
    if len(pattern) != len(path):
        return False
    return all(p == "*" or p == s for p, s in zip(pattern, path))


def _walk(value: Any, path: tuple[str, ...]) -> Iterable[tuple[tuple[str, ...], Any]]:
    """Yield every leaf of a JSON value with its path."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, path + (str(key),))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, path + (f"[{index}]",))
    else:
        yield path, value


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _slot_path(path: tuple[str, ...]) -> str:
    """Render a walked path as a dotted path a human can read."""
    out = ""
    for segment in path:
        if segment.startswith("["):
            out += segment
        elif out:
            out += "." + segment
        else:
            out = segment
    return out


def statutory_violations(document: dict) -> list[str]:
    """Every place where a preset carries a value the law may own.

    Returns one message per violation. An empty list means the preset
    carries no statutory number, which is the only state in which the
    loader will accept it.
    """
    problems: list[str] = []

    # 1. The declared slots.
    for leaf_path, value in _walk(document, ()):
        for pattern in STATUTORY_SLOTS:
            if not _matches(pattern, leaf_path):
                continue
            if pattern[-1] == "expiry_rule" and isinstance(value, dict):
                # The whole rule may be the sentinel, or it may be an object
                # whose carry-forward is the sentinel. Either is fine; a
                # number in the carry-forward is not.
                continue
            if not is_sentinel(value):
                problems.append(
                    f"the statutory slot {_slot_path(leaf_path)} carries {value!r}; "
                    f"it must carry {SENTINEL}"
                )

    # The expiry rule, when it is an object rather than the sentinel.
    leave_types = (
        document.get("configuration", {}).get("leave", {}).get("leave_types", []) or []
    )
    for leaf in leave_types:
        if not isinstance(leaf, dict):
            continue
        rule = leaf.get("expiry_rule")
        if isinstance(rule, dict):
            carried = rule.get("carry_forward_days")
            if not is_sentinel(carried):
                problems.append(
                    "the statutory slot "
                    f"configuration.leave.leave_types[{leaf.get('key')}]."
                    "expiry_rule.carry_forward_days carries a number; it must "
                    f"carry {SENTINEL}"
                )

    # 2. The named slots.
    for leaf_path, value in _walk(document, ()):
        if not leaf_path:
            continue
        key = leaf_path[-1]
        if not _is_number(value):
            continue
        lowered = key.lower()
        if any(word in lowered for word in STATUTORY_KEYWORDS):
            problems.append(
                f"the key {key} carries the number {value!r}; a value a statute "
                f"may set must be {SENTINEL} in a preset"
            )

    return problems
