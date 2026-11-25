"""Decimal money helpers — single source of truth for all monetary arithmetic.

Rules
-----
* All monetary values are handled as Decimal, never float.
* Rounding is explicit and applied at a single point: amounts are quantised
  to CENTS using ROUND_HALF_UP (standard payroll convention).
* Line totals are computed from already-rounded components.
* No floats anywhere in calculation paths.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Union

# Set a high precision for intermediate calculations
getcontext().prec = 28

CENTS = Decimal("0.01")
ZERO = Decimal("0.00")

NumericInput = Union[int, float, str, Decimal, None]


def to_decimal(value: NumericInput) -> Decimal:
    """Coerce a DB/JSON/Python value to Decimal without going through float.

    - None -> ZERO
    - Decimal -> unchanged
    - int -> exact Decimal
    - float -> Decimal(repr(value)) to avoid binary-float representation artefacts
    - str -> Decimal(str) directly
    """
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # repr() gives the shortest round-trip string representation
        return Decimal(repr(value))
    return Decimal(str(value))


def money(value: NumericInput) -> Decimal:
    """Quantise to cents (2 decimal places), rounding half away from zero (ROUND_HALF_UP)."""
    return to_decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def money_raw(value: NumericInput) -> Decimal:
    """Convert to Decimal without quantising — for intermediate calculations only.

    Use `money()` for any value that will be stored, compared, or displayed.
    """
    return to_decimal(value)


def rate_percentage(value: NumericInput) -> Decimal:
    """Convert a percentage value (e.g., 5.5 for 5.5%) to a Decimal multiplier (0.055)."""
    return money_raw(value) / Decimal("100")


def apply_rate(base: NumericInput, rate_pct: NumericInput) -> Decimal:
    """Apply a percentage rate to a base amount, returning a quantised money value."""
    base_d = money_raw(base)
    rate_d = rate_percentage(rate_pct)
    return money(base_d * rate_d)


def sum_money(*values: NumericInput) -> Decimal:
    """Sum multiple money values, returning a quantised result."""
    return money(sum((money_raw(v) for v in values), ZERO))


def prorate(amount: NumericInput, numerator: NumericInput, denominator: NumericInput) -> Decimal:
    """Pro-rate an amount by numerator/denominator with explicit rounding.

    Example: prorate(annual_salary, days_worked, days_in_period)
    """
    amt = money_raw(amount)
    num = money_raw(numerator)
    den = money_raw(denominator)
    if den == ZERO:
        return ZERO
    return money(amt * num / den)


def round_half_up(value: NumericInput, places: int = 2) -> Decimal:
    """Round to arbitrary decimal places using ROUND_HALF_UP."""
    d = to_decimal(value)
    quant = Decimal("1") / (Decimal("10") ** places)
    return d.quantize(quant, rounding=ROUND_HALF_UP)