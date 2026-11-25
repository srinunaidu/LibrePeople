"""Payroll calculation engine - **not on the pay-run path any more**.

.. warning::

   A pay run is calculated from a verified rule pack, through
   ``app.rules.engine`` (see ``backend/app/rules/``). This module computes a
   payslip from a pay profile and a configured withholding percentage, and
   nothing in the product calls it any more: a figure computed without a
   verified rule is a figure the product cannot stand behind.

   It is still here because the security suite checks the money semantics
   against it, and because it documents the "configurable calculation"
   behaviour the pack replaced. When those checks move to
   ``app.rules.money``, this module goes with them. Do not wire it back into
   a pay run.

Money handling rules
--------------------
* All monetary values are handled as :class:`decimal.Decimal`, never float.
  Binary floats cannot represent values like ``0.10`` exactly, so repeated
  float arithmetic on salaries produces cent-level drift that accumulates
  across a pay run and makes the run totals disagree with the payslips.
* Rounding is explicit and applied at a single point: amounts are quantised to
  ``CENTS`` using ``ROUND_HALF_UP`` (the convention used by payroll systems
  generally), and line totals are computed from already-rounded components.
* Employee compensation figures are interpreted per pay period (see "Salary
  basis" below). No frequency normalisation is applied here.

Salary basis
------------
``EmployeePayProfile.base_salary`` is treated as the amount payable **for one
pay period**, which is the semantics the existing product has always used.

This is stated explicitly because the alternative reading (an annual salary
divided by 12) would silently change every employee's net pay by 12x. The unit
was never recorded on the column, so changing it here would be a business
decision, not a bug fix. If Karmathy later decides to store annual salary,
that needs a schema change plus a migration of existing profiles — see
OPEN QUESTIONS in docs/ENTERPRISE_AUDIT.md.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")
ZERO = Decimal("0.00")

# How many payroll periods make up one month, for the supported frequencies.
PERIODS_PER_YEAR = {
    "Weekly": Decimal("52"),
    "Biweekly": Decimal("26"),
    "Semimonthly": Decimal("24"),
    "Monthly": Decimal("12"),
}


def to_decimal(value) -> Decimal:
    """Coerce a DB/JSON value to Decimal without going through float."""
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # `repr` gives the shortest round-trip string, so this converts the
        # float the DB handed us without adding a second rounding step.
        return Decimal(repr(value))
    return Decimal(str(value))


def money(value) -> Decimal:
    """Quantise to cents, rounding half away from zero."""
    return to_decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


class PayLine:
    """One calculated earnings/deduction line."""

    __slots__ = ("code", "name", "amount", "is_earning")

    def __init__(self, code: str, name: str, amount: Decimal, is_earning: bool):
        self.code = code
        self.name = name
        self.amount = money(amount)
        self.is_earning = is_earning

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "amount": float(self.amount),
            "type": "earning" if self.is_earning else "deduction",
        }


class PayslipResult:
    __slots__ = ("earnings", "deductions", "gross", "total_deductions", "net")

    def __init__(
        self,
        earnings: list[PayLine],
        deductions: list[PayLine],
    ) -> None:
        self.earnings = earnings
        self.deductions = deductions
        self.gross = sum((l.amount for l in earnings), ZERO)
        self.total_deductions = sum((l.amount for l in deductions), ZERO)
        self.net = money(self.gross - self.total_deductions)

    def as_json(self) -> tuple[str, str]:
        import json

        return (
            json.dumps([l.as_dict() for l in self.earnings]),
            json.dumps([l.as_dict() for l in self.deductions]),
        )


def period_divisor(pay_frequency: str) -> Decimal:
    """How many times a year this pay frequency runs."""
    return PERIODS_PER_YEAR.get((pay_frequency or "Monthly").strip(), Decimal("12"))


def calculate_payslip(
    *,
    base_salary: object,
    pay_frequency: str,
    tax_withholding: object,
    benefit_deductions: object = 0,
    other_earnings: object = 0,
    other_deductions: object = 0,
) -> PayslipResult:
    """Compute one payslip from a pay profile plus period inputs.

    ``base_salary`` is the gross amount for **this pay period** (see "Salary
    basis" in the module docstring). ``tax_withholding`` is a percentage of
    gross. ``benefit_deductions`` / ``other_*`` are period amounts supplied by
    the caller.
    """
    base_period = money(base_salary)

    earnings = [PayLine("BASIC", "Base Salary", base_period, True)]
    extra_earn = money(other_earnings)
    if extra_earn:
        earnings.append(PayLine("EARNINGS", "Other Earnings", extra_earn, True))

    gross = sum((l.amount for l in earnings), ZERO)

    rate = to_decimal(tax_withholding)
    if rate < ZERO:
        rate = ZERO
    # Guard against a misconfigured rate that would exceed 100%.
    if rate > Decimal("100"):
        rate = Decimal("100")
    tax = money(gross * rate / Decimal("100"))

    deductions: list[PayLine] = []
    if tax:
        deductions.append(PayLine("TAX", "Tax Withholding", tax, False))
    benefit = money(benefit_deductions)
    if benefit:
        deductions.append(PayLine("BENEFITS", "Benefit Deductions", benefit, False))
    other_ded = money(other_deductions)
    if other_ded:
        deductions.append(PayLine("OTHER", "Other Deductions", other_ded, False))

    return PayslipResult(earnings, deductions)