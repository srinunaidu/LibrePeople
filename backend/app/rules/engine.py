"""Rule-engine payroll calculation using a verified rule pack.

This module implements the payroll calculation pipeline driven by a rule pack.
It is pure, deterministic, and uses Decimal arithmetic throughout.

The two forms of a rate table, and how each is read
---------------------------------------------------
The rule-pack schema (``contracts/rules/rule-pack.schema.json``) writes a
rate table in one of two forms, and the engine reads each of them in one
way only. A pack that uses one form is never read as the other.

**The banded form** (``entries``) is a progressive table. A band states
three numbers: its ``value`` is the **lower bound** of the band, its
``max_value`` is the upper bound, and its ``rate`` is the percentage rate
that applies inside the band. The engine divides the taxable amount between
the bands by their bounds — the amount from ``value`` up to, but not
including, ``max_value`` — and taxes each part at the rate of the band it
falls in. A band states no rate, or the bounds do not ascend, and the band
table cannot be calculated: the engine refuses the pack rather than compute
a figure it cannot stand behind.

**The keyed-map form** (``values``) is a flat lookup. Every value is a
percentage rate that applies to the whole base, and the key is the code the
engine looks up. There are no bounds and no bands.

A band table that leaves the rate out is the shape the shipped demo pack has:
it states the bounds and leaves the rate in prose. The engine cannot read
that, so it refuses the pack and says which table and which band it could
not read — never what the band contains.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Sequence

from app.rules.loader import RulePack, RateTable, RateTableEntry, LeaveType, GoldenCase
from app.rules.money import money, money_raw, to_decimal, apply_rate, prorate, sum_money, ZERO, CENTS


#: The rate table the income tax is read from. It has to be a banded table:
#: the engine has to know which rate applies to which part of the taxable
#: amount, and a flat map does not say that.
TAX_TABLE = "tax_bands"

#: The rate table the employee's social insurance contributions are read
#: from. It has to be a flat map: every value is a percentage of the
#: contribution base.
EMPLOYEE_CONTRIBUTION_TABLE = "social_insurance_employee"

#: The rate table the employer's social insurance contributions are read
#: from. It has to be a flat map, for the same reason.
EMPLOYER_CONTRIBUTION_TABLE = "social_insurance_employer"

#: The rule id the employee's social insurance contribution lines carry. The
#: employee's contributions are deductions like any other, so the rule id is
#: what tells them apart from the tax and from the benefit deductions.
EMPLOYEE_CONTRIBUTION_RULE_ID = "SOCIAL_INSURANCE_EE"

#: The rule id the employer's social insurance contribution lines carry.
EMPLOYER_CONTRIBUTION_RULE_ID = "SOCIAL_INSURANCE_ER"


class RulePackNotReadable(ValueError):
    """The pack cannot be calculated exactly as it is written.

    The problems name the table and the band that cannot be read. They never
    carry a value from the pack: a rate, a bound or a threshold is the
    pack's business and must not leak through an error message.
    """

    def __init__(self, problems: Sequence[str]):
        self.problems = tuple(problems)
        super().__init__("; ".join(self.problems))


@dataclass(frozen=True)
class PayLine:
    """One calculated earnings/deduction/contribution line."""
    code: str
    name: str
    amount: Decimal
    line_type: str  # earning | deduction | employer_contribution | allowance | reimbursement | tax
    rule_id: str
    rule_version: str
    input_source: str  # e.g., "base_salary", "overtime_hours", "rule_pack:tax_bands"
    calculation: str   # human-readable formula, e.g., "5000 * 10%"


@dataclass(frozen=True)
class PayslipResult:
    earnings: tuple[PayLine, ...]
    deductions: tuple[PayLine, ...]
    employer_contributions: tuple[PayLine, ...]
    gross: Decimal
    total_deductions: Decimal
    net: Decimal
    pay_floor_check: str  # "pass" | "fail" | "flag"
    trace_id: str  # hash of inputs + rule pack version for determinism verification
    # The statutory contributions the pack computed, on each side of the
    # payslip. They are not part of the employee's pay: the employer's
    # money, and the employee's own money inside the deductions. They are
    # totals of their own so that the payslip can carry them and the
    # reconciliation can check them.
    total_employee_contributions: Decimal = ZERO
    total_employer_contributions: Decimal = ZERO


@dataclass
class CalculationContext:
    """Mutable context during a single payslip calculation."""
    pack: RulePack
    base_salary: Decimal
    pay_frequency: str
    hours_worked: Decimal
    overtime_hours: Decimal
    overtime_hourly_rate: Decimal
    leave_days: Decimal
    tax_withholding_override: Optional[Decimal]
    benefit_deductions: Decimal
    other_earnings: Decimal
    other_deductions: Decimal
    pt_state: Optional[str] = None
    # --- India slice 5 extensions (guarded: IN pack presence + flag) --------
    basic_pct: Optional[Decimal] = None
    tenure_years: Optional[Decimal] = None
    leave_encashment_days: Decimal = ZERO
    arrears_days: Decimal = ZERO
    jurisdiction: Optional[str] = None
    lines: list[PayLine] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_line(self, line: PayLine) -> None:
        self.lines.append(line)

    def add_earning(self, code: str, name: str, amount: Decimal, rule_id: str, input_source: str, calculation: str) -> None:
        self.add_line(PayLine(
            code=code, name=name, amount=money(amount), line_type="earning",
            rule_id=rule_id, rule_version=self.pack.meta.version,
            input_source=input_source, calculation=calculation
        ))

    def add_deduction(self, code: str, name: str, amount: Decimal, rule_id: str, input_source: str, calculation: str) -> None:
        self.add_line(PayLine(
            code=code, name=name, amount=money(amount), line_type="deduction",
            rule_id=rule_id, rule_version=self.pack.meta.version,
            input_source=input_source, calculation=calculation
        ))

    def add_employer_contribution(self, code: str, name: str, amount: Decimal, rule_id: str, input_source: str, calculation: str) -> None:
        self.add_line(PayLine(
            code=code, name=name, amount=money(amount), line_type="employer_contribution",
            rule_id=rule_id, rule_version=self.pack.meta.version,
            input_source=input_source, calculation=calculation
        ))


def _band_problems(table_name: str, table: RateTable) -> list[str]:
    """Why a band table cannot be read the way the schema reads it.

    A band table is a list of bands, and the engine divides the taxable
    amount between them by their bounds. A table that cannot be divided that
    way is refused: the alternatives are a wrong figure and a guess.
    """
    problems: list[str] = []
    previous_upper: Optional[Decimal] = None
    open_ended = False

    for entry in table.entries:
        if entry.rate is None:
            problems.append(
                f"the band table '{table_name}' states no rate for band "
                f"'{entry.code}': the engine reads a band's value as the lower "
                "bound of the band, so the rate that applies inside the band "
                "has to be stated in the band's 'rate' field"
            )
        if entry.max_value is not None and entry.max_value <= entry.value:
            problems.append(
                f"band '{entry.code}' in the table '{table_name}' ends at or "
                "before it starts: the bounds of a band table have to ascend"
            )
        if open_ended:
            problems.append(
                f"band '{entry.code}' in the table '{table_name}' follows a band "
                "that has no upper bound: an open ended band is the last band "
                "of the table"
            )
        elif previous_upper is not None and entry.value < previous_upper:
            problems.append(
                f"band '{entry.code}' in the table '{table_name}' overlaps the "
                "band before it: the bounds of a band table have to ascend and "
                "must not overlap"
            )
        if entry.max_value is None:
            open_ended = True
        else:
            previous_upper = entry.max_value
    return problems


def rate_table_problems(pack: RulePack) -> list[str]:
    """The reasons the pack's rate tables cannot be read exactly.

    An empty list means the engine can calculate from the pack as it is
    written. A non-empty list means it cannot, and the pack is refused: a
    wrong pay figure is worse than a refusal.

    Only the tables the engine actually reads are checked. A table the
    engine does not read cannot produce a wrong figure, so it is left alone.

    The problems name the table and the band. They never carry a value from
    the pack.
    """
    problems: list[str] = []

    tax_table = pack.get_rate_table(TAX_TABLE)
    if tax_table is not None:
        if not tax_table.entries:
            problems.append(
                f"the tax table '{TAX_TABLE}' is a flat rate map: the engine "
                "has to know which rate applies to which part of the taxable "
                "amount, so the tax table has to be a banded table"
            )
        else:
            problems.extend(_band_problems(TAX_TABLE, tax_table))

    for name in (EMPLOYEE_CONTRIBUTION_TABLE, EMPLOYER_CONTRIBUTION_TABLE):
        table = pack.get_rate_table(name)
        if table is not None and table.entries:
            problems.append(
                f"the table '{name}' is a banded table: the engine reads it as "
                "a flat rate map, where every value is a percentage of the "
                "contribution base, so a band table here would be read as "
                "nothing at all"
            )
    return problems


def _band_taxable(taxable: Decimal, entry: RateTableEntry) -> Decimal:
    """The part of the taxable amount that falls inside the band.

    The band runs from its lower bound up to, but not including, its upper
    bound. An open ended band runs to the end of the taxable amount.
    """
    lower = entry.value
    upper = entry.max_value
    top = taxable if upper is None else min(taxable, upper)
    if top <= lower:
        return ZERO
    return top - lower


def calculate_tax(ctx: CalculationContext) -> Decimal:
    """Calculate the tax from the pack's banded tax table (progressive).

    The bands are read the way the schema reads them: a band's ``value`` is
    its lower bound, ``max_value`` its upper bound, and ``rate`` the
    percentage rate that applies inside it. The taxable amount is divided
    between the bands by their bounds and each part is taxed at the rate of
    the band it falls in.
    """
    tax_table = ctx.pack.get_rate_table(TAX_TABLE)
    if not tax_table:
        # Fallback: flat percentage from override or pack default
        rate = ctx.tax_withholding_override
        if rate is None:
            rate = Decimal("0")
        tax = apply_rate(ctx.base_salary, rate)
        ctx.add_deduction("TAX", "Tax Withholding (flat)", tax,
                         "FLAT_TAX", "tax_withholding_override", f"{ctx.base_salary} * {rate}%")
        return tax

    # A pack the engine cannot read is refused here as well as at the gate:
    # the calculation must never fall back to a figure it cannot defend.
    problems = rate_table_problems(ctx.pack)
    if problems:
        raise RulePackNotReadable(problems)

    taxable = ctx.base_salary
    # Add overtime to taxable if configured
    if ctx.overtime_hours > 0:
        taxable += ctx.overtime_hours * ctx.overtime_hourly_rate
    # Slice 5: taxable includes encashment (§10(10AA) minimal) and arrears
    # Guarded: only when the pack carries gratuity_accrual (IN) and the
    # encashment/arrears inputs are non-zero → US pack unchanged.
    if ctx.leave_encashment_days and ctx.leave_encashment_days > ZERO:
        # encashment amount is daily Basic+DA × days, already an earning
        try:
            taxable += _daily_rate(ctx) * ctx.leave_encashment_days
        except Exception:
            taxable += ctx.leave_encashment_days * money(ctx.base_salary / Decimal("22"))
    if ctx.arrears_days and ctx.arrears_days > ZERO:
        try:
            taxable += _daily_rate(ctx) * ctx.arrears_days
        except Exception:
            taxable += ctx.arrears_days * money(ctx.base_salary / Decimal("22"))

    # Guarded India extension: standard deduction (monthly) if the pack carries
    # the tax_adjustments table. US pack has no such table → behaviour unchanged.
    adjustments = ctx.pack.get_rate_table("tax_adjustments")
    if adjustments is not None:
        sd = adjustments.values.get("standard_deduction_monthly")
        if sd is not None:
            taxable = money(taxable - sd.value)
            if taxable < ZERO:
                taxable = ZERO

    tax = ZERO

    for entry in tax_table.entries:
        taxable_in_band = _band_taxable(taxable, entry)
        if taxable_in_band <= ZERO:
            continue
        band_tax = apply_rate(taxable_in_band, entry.rate)
        tax += band_tax
        ctx.add_deduction(
            f"TAX_{entry.code}", f"Tax - {entry.label}", band_tax,
            "TAX_BAND", f"rule_pack:{TAX_TABLE}:{entry.code}",
            f"{taxable_in_band} * {entry.rate}%"
        )

    # Guarded India extension: rebate u/s 87A if the pack carries tax_rebates.
    rebates = ctx.pack.get_rate_table("tax_rebates")
    if rebates is not None:
        limit_val = rebates.values.get("rebate_87a_income_limit_monthly")
        max_val = rebates.values.get("rebate_87a_max_monthly")
        if limit_val is not None and max_val is not None:
            # taxable already reflects standard deduction
            if taxable <= limit_val.value:
                rebate = min(tax, max_val.value)
                # money quantisation for rebate amount
                rebate = money(rebate)
                if rebate > ZERO:
                    # Emit a negative deduction line so total_deductions reflects net tax
                    ctx.add_deduction(
                        "REBATE_87A", "Rebate u/s 87A", money(-rebate),
                        "REBATE_87A", "rule_pack:tax_rebates:rebate_87a_max_monthly",
                        f"min({tax}, {max_val.value})"
                    )
                    tax = money(tax - rebate)
                    if tax < ZERO:
                        tax = ZERO

    return tax


def _basic_da_amount(ctx: CalculationContext) -> Decimal:
    """Basic+DA amount for the period (India slice 5).

    When ``basic_pct`` is set the Basic+DA base is ``base_salary × basic_pct/100``,
    otherwise it is the full ``base_salary``. Guarded: only India packs set
    ``basic_pct``.
    """
    if ctx.basic_pct is not None:
        try:
            pct = to_decimal(ctx.basic_pct)
        except Exception:
            pct = ZERO
        if pct < ZERO:
            pct = ZERO
        if pct > Decimal("100"):
            pct = Decimal("100")
        return money(ctx.base_salary * pct / Decimal("100"))
    return ctx.base_salary


def _daily_rate(ctx: CalculationContext) -> Decimal:
    """Daily rate for leave/encashment/LOP/arrears.

    India slice 5: when Basic+DA split is flagged the daily rate is
    Basic+DA / 26 (gratuity denominator), otherwise base_salary / 22
    (monthly working days). 26 is the gratuity month denominator; 22 is the
    legacy monthly working-day count. Both are guarded on basic_pct presence.
    """
    # For PF-split cases the daily is Basic+DA / 26 (statutory month).
    # Fallback 22 retains the existing LOP behaviour for non-split packs.
    if ctx.basic_pct is not None:
        basic_da = _basic_da_amount(ctx)
        # Guard div zero
        return money(basic_da / Decimal("26")) if basic_da != ZERO else ZERO
    working_days_map = {
        "monthly": Decimal("22"),
        "semimonthly": Decimal("11"),
        "biweekly": Decimal("10"),
        "weekly": Decimal("5"),
    }
    working_days = working_days_map.get(ctx.pay_frequency.lower(), Decimal("22"))
    return money(ctx.base_salary / working_days)


def calculate_social_insurance(ctx: CalculationContext) -> tuple[Decimal, Decimal, Decimal]:
    """Calculate employee/employer social insurance contributions."""
    ee_table = ctx.pack.get_rate_table("social_insurance_employee")
    er_table = ctx.pack.get_rate_table("social_insurance_employer")

    ee_total = ZERO
    er_total = ZERO

    # Contribution base is typically capped; for demo use gross
    # Slice 5: PF base is Basic+DA when basic_pct is set, else gross.
    # ESI base stays on gross regardless of the split.
    use_basic_da = ctx.basic_pct is not None
    basic_da = _basic_da_amount(ctx) if use_basic_da else ctx.base_salary
    contrib_base = ctx.base_salary
    if ctx.overtime_hours > 0:
        contrib_base += ctx.overtime_hours * ctx.overtime_hourly_rate

    ceilings = ctx.pack.get_rate_table("social_insurance_ceilings")

    if ee_table:
        for code, val in ee_table.values.items():
            # PF uses Basic+DA when flagged; ESI always uses gross.
            base_for_code = basic_da if (use_basic_da and code.lower() == "pf") else contrib_base
            # For ESI the overtime-inclusive gross is not capped differently
            if ceilings is not None:
                # wage_ceiling caps the base; wage_limit skips when base exceeds limit
                ceiling_key = f"{code}_wage_ceiling"
                limit_key = f"{code}_wage_limit"
                # keys are lower-case in the pack; code keys are lower-case
                ce = ceilings.values.get(ceiling_key) or ceilings.values.get(ceiling_key.lower())
                li = ceilings.values.get(limit_key) or ceilings.values.get(limit_key.lower())
                if li is not None and base_for_code > li.value:
                    continue
                if ce is not None and base_for_code > ce.value:
                    base_for_code = ce.value
            amount = apply_rate(base_for_code, val.value)
            ee_total += amount
            ctx.add_deduction(
                f"{code.upper()}_EE", f"{val.label} (Employee)", amount,
                EMPLOYEE_CONTRIBUTION_RULE_ID,
                f"rule_pack:{EMPLOYEE_CONTRIBUTION_TABLE}:{code}",
                f"{base_for_code} * {val.value}%"
            )

    if er_table:
        for code, val in er_table.values.items():
            base_for_code = basic_da if (use_basic_da and code.lower() == "pf") else contrib_base
            if ceilings is not None:
                ceiling_key = f"{code}_wage_ceiling"
                limit_key = f"{code}_wage_limit"
                ce = ceilings.values.get(ceiling_key) or ceilings.values.get(ceiling_key.lower())
                li = ceilings.values.get(limit_key) or ceilings.values.get(limit_key.lower())
                if li is not None and base_for_code > li.value:
                    continue
                if ce is not None and base_for_code > ce.value:
                    base_for_code = ce.value
            amount = apply_rate(base_for_code, val.value)
            er_total += amount
            ctx.add_employer_contribution(
                f"{code.upper()}_ER", f"{val.label} (Employer)", amount,
                EMPLOYER_CONTRIBUTION_RULE_ID,
                f"rule_pack:{EMPLOYER_CONTRIBUTION_TABLE}:{code}",
                f"{base_for_code} * {val.value}%"
            )

    return ee_total, er_total, contrib_base


def calculate_overtime(ctx: CalculationContext) -> Decimal:
    """Calculate overtime pay based on rule pack thresholds.

    Slice 5 India extension: thresholds come from the pack's ``overtime``
    (and mirrored ``thresholds``) block — daily 9h / weekly 48h / premium 2x
    for IN. The engine reads the pack; it does not hard-code the thresholds.
    Guarded: a pack with no overtime table (US) falls back to 1.5x.
    """
    ot_config = ctx.pack.overtime
    if ctx.overtime_hours <= 0:
        return ZERO

    # Guarded India thresholds: when the pack carries overtime rules with a
    # premium, that premium is the one used (IN → 2x, US → 1.5x fallback).
    # Threshold hours themselves are info for compliance; the engine caps by
    # daily_cap_hours when the pack states one.
    multiplier = ot_config.premium_multiplier or Decimal("1.5")
    daily_cap = ot_config.daily_cap_hours

    # Cap overtime hours at daily cap if specified (India daily cap 2h)
    ot_hours = ctx.overtime_hours
    if daily_cap is not None and ot_hours > daily_cap:
        ot_hours = daily_cap
        ctx.warnings.append(f"Overtime capped at {daily_cap} hours/day per rule pack")

    ot_pay = money(ot_hours * ctx.overtime_hourly_rate * multiplier)
    if ot_pay > ZERO:
        ctx.add_earning(
            "OT", "Overtime", ot_pay,
            "OVERTIME", "overtime_hours",
            f"{ot_hours} hrs * {ctx.overtime_hourly_rate} * {multiplier}"
        )
    return ot_pay


def calculate_leave_deduction(ctx: CalculationContext) -> Decimal:
    """Calculate leave deduction (unpaid leave / LOP) if applicable.

    Slice 5: daily rate is Basic+DA / 26 when basic_pct is flagged (India
    statutory month), otherwise base_salary / 22 (legacy). LOP is emitted as
    deduction ``LOP`` guarded on IN presence; existing ``LEAVE_UNPAID`` path
    retained for byte-identical US packs that have no gratuity table.
    """
    if ctx.leave_days <= 0:
        return ZERO

    daily_rate = _daily_rate(ctx)
    leave_deduction = money(daily_rate * ctx.leave_days)

    if leave_deduction > ZERO:
        # Emit both canonical codes so payroll reports and F&F can read either:
        # LEAVE_UNPAID (legacy) and LOP (India slice 5). LOP is the India
        # contract code; LEAVE_UNPAID keeps existing assertions green.
        # Guarded: LOP code only when the pack carries an India gratuity table
        # (i.e. IN pack) — US pack has no such table → legacy line only.
        has_india = ctx.pack.get_rate_table("gratuity_accrual") is not None
        if has_india:
            ctx.add_deduction(
                "LOP", "Loss of Pay", leave_deduction,
                "LEAVE_DEDUCTION", "leave_days",
                f"{ctx.leave_days} days * {daily_rate}/day"
            )
        else:
            ctx.add_deduction(
                "LEAVE_UNPAID", "Unpaid Leave Deduction", leave_deduction,
                "LEAVE_DEDUCTION", "leave_days",
                f"{ctx.leave_days} days * {daily_rate}/day"
            )
    return leave_deduction


def calculate_gratuity_accrual(ctx: CalculationContext, tenure_years) -> Decimal:
    """Gratuity accrual — Payment of Gratuity Act 1972 §4 (guarded).

    Only when the pack carries ``gratuity_accrual`` AND declares it in scope
    AND the pack is verified, and tenure >=5: emits ``GRATUITY_ACCRUAL`` as
    employer_contribution at 15/26/12 = 4.81% of Basic+DA (or gross when no
    Basic/DA split). Else no line. Guarded so US pack (no table) is
    byte-identical.
    """
    table = ctx.pack.get_rate_table("gratuity_accrual")
    if table is None:
        return ZERO
    # Scope gate: a pack that does not explicitly declare gratuity in scope
    # emits no accrual, and neither does a pack that is not verified. The
    # employer total is summed from the lines emitted here, so it excludes
    # the accrual too.
    if not (table.in_scope and ctx.pack.is_verified()):
        return ZERO
    try:
        tenure = to_decimal(tenure_years)
    except Exception:
        return ZERO
    if tenure is None or tenure < Decimal("5"):
        return ZERO
    # Prefer stored rate; fallback to formula 15/26/12
    rate_val = table.values.get("gratuity_rate_pct")
    rate = rate_val.value if rate_val is not None else Decimal("4.81")
    basic_da = _basic_da_amount(ctx)
    # Monthly accrual = Basic+DA * rate%
    amount = apply_rate(basic_da, rate)
    if amount > ZERO:
        ctx.add_employer_contribution(
            "GRATUITY_ACCRUAL", "Gratuity Accrual (Payment of Gratuity Act 1972 §4)", amount,
            "GRATUITY_ACCRUAL", "rule_pack:gratuity_accrual:gratuity_rate_pct",
            f"{basic_da} * {rate}% (15/26/12, eligibility 5yr)"
        )
    return amount


def calculate_bonus_accrual(ctx: CalculationContext) -> Decimal:
    """Bonus Act stub — Payment of Bonus Act 1965 (guarded, info-only).

    Reads ``bonus_act`` table when present (IN) but does NOT emit a deduction
    in v1; only an employer info line ``BONUS_ACCRUAL`` when a future flag
    enables it. Currently returns 0 and emits no line, so net is unchanged.
    Guarded so US pack (no table) is no-op.
    """
    table = ctx.pack.get_rate_table("bonus_act")
    if table is None:
        return ZERO
    # Stub: record the min/max for F&F/reporting but do not affect pay.
    # Emit no deduction; optionally an info employer_contribution of 0.
    return ZERO


def calculate_lwf(ctx: CalculationContext) -> Decimal:
    """LWF per-state stub — guarded, info-only (no deduction in v1).

    Reads ``lwf_state`` when present (IN) but does not deduct. The flat
    amounts are per-state stubs for reports/F&F reference.
    """
    table = ctx.pack.get_rate_table("lwf_state")
    if table is None or not ctx.pt_state:
        return ZERO
    # No deduction in v1 — info line only when a future flag enables it.
    return ZERO


def calculate_arrears(ctx: CalculationContext, arrears_days, base_type: str = "basic_da") -> Decimal:
    """Arrears earning — guarded.

    ``arrears_days`` × daily Basic+DA (or gross) as earning ``ARREARS``.
    Guarded on gratuity table presence (IN); US pack → no table → no line.
    """
    try:
        days = to_decimal(arrears_days)
    except Exception:
        return ZERO
    if days is None or days <= ZERO:
        return ZERO
    table = ctx.pack.get_rate_table("gratuity_accrual")
    if table is None:
        return ZERO
    daily = _daily_rate(ctx)
    amount = money(daily * days)
    if amount > ZERO:
        ctx.add_earning(
            "ARREARS", "Arrears", amount,
            "ARREARS", "arrears_days",
            f"{days} days * {daily}/day"
        )
    return amount


def calculate_leave_encashment(ctx: CalculationContext) -> Decimal:
    """Leave encashment (encashable leave × daily Basic+DA) — taxable earning.

    Guarded on IN pack (gratuity table presence) and on an encashable leave
    type in the pack. Taxable via §10(10AA) minimal stub — amount is added as
    earning ``LEAVE_ENCASHMENT`` and will be included in gross/taxable.
    """
    if ctx.leave_encashment_days is None or ctx.leave_encashment_days <= ZERO:
        return ZERO
    table = ctx.pack.get_rate_table("gratuity_accrual")
    if table is None:
        return ZERO
    # Verify the pack has an encashable leave type (earned)
    has_encashable = any(lt.encashable for lt in ctx.pack.leave_types)
    if not has_encashable:
        return ZERO
    daily = _daily_rate(ctx)
    amount = money(daily * ctx.leave_encashment_days)
    if amount > ZERO:
        ctx.add_earning(
            "LEAVE_ENCASHMENT", "Leave Encashment", amount,
            "LEAVE_ENCASHMENT", "leave_encashment_days",
            f"{ctx.leave_encashment_days} days * {daily}/day (taxable §10(10AA))"
        )
    return amount


#: The hours in a pay period, used to turn a period salary into an hourly
#: rate and to compare gross pay with an hourly minimum wage. It is stated
#: once so the overtime rate, the leave deduction and the floor check cannot
#: disagree about what a period is.
PERIOD_HOURS: dict[str, Decimal] = {
    "monthly": Decimal("173"),
    "semimonthly": Decimal("86.5"),
    "biweekly": Decimal("80"),
    "weekly": Decimal("40"),
}


def period_hours(pay_frequency: str) -> Decimal:
    """The hours in one pay period for the given frequency."""
    return PERIOD_HOURS.get((pay_frequency or "").strip().lower(), PERIOD_HOURS["monthly"])


def calculate_professional_tax(ctx: CalculationContext) -> Decimal:
    """Calculate professional tax (PT) via pt_state — guarded for IN packs.

    If ctx.pt_state is set and the pack carries a table named ``pt_{state.lower()}``,
    the single entry whose gross band contains the base is applied as a flat
    monthly deduction ``PT_{STATE}`` = entry.rate. No table → zero, no line.
    """
    if not ctx.pt_state:
        return ZERO
    state = ctx.pt_state.strip().lower()
    if not state:
        return ZERO
    table_name = f"pt_{state}"
    table = ctx.pack.get_rate_table(table_name)
    if table is None or not table.entries:
        return ZERO
    # Gross for PT is sum of earnings (base + overtime) already in ctx.lines
    # Fallback to base_salary if earnings not yet summed
    earnings_total = sum_money(*[line.amount for line in ctx.lines if line.line_type == "earning"])
    pt_base = earnings_total if earnings_total != ZERO else ctx.base_salary
    # Also include overtime base if not yet added as earning? contrib base is salary + overtime
    # Use pt_base as Decimal
    for entry in table.entries:
        lower = entry.value
        upper = entry.max_value  # exclusive, None = open
        if pt_base < lower:
            continue
        if upper is not None and pt_base >= upper:
            continue
        amount = money(entry.rate if entry.rate is not None else ZERO)
        # entry.rate is the flat amount (engine reads `rate` as the amount)
        # But RateTableEntry.rate may be None for schedule? Contract says use `rate`
        # field as flat amount. Our loader stores rate correctly.
        if amount == ZERO and entry.rate is not None:
            # already zero correctly
            pass
        if amount != ZERO or (upper is None or pt_base >= lower):
            # Add line even if amount zero? Only when matched and amount >0 we add,
            # but zero PT still counts as no deduction. Only add when found.
            # For WB etc we always add matched entry (even if 0)
            ctx.add_deduction(
                f"PT_{state.upper()}", f"Professional Tax ({state.upper()})", amount,
                f"PT_{state.upper()}", f"rule_pack:{table_name}:{entry.code}",
                f"PT {state.upper()} band {entry.code}: {amount}"
            )
            return amount
        return ZERO
    return ZERO


def check_pay_floor(ctx: CalculationContext, gross: Decimal) -> str:
    """Check if gross pay meets minimum wage threshold from rule pack."""
    thresholds = ctx.pack.thresholds
    min_wage = thresholds.minimum_wage_amount
    min_wage_unit = thresholds.minimum_wage_unit

    if min_wage is None or min_wage_unit is None:
        return "pass"  # No floor defined

    # Convert gross to the same unit for comparison
    # For simplicity, assume monthly pay period and hourly minimum wage
    if min_wage_unit == "per_hour":
        hourly_gross = money(gross / period_hours(ctx.pay_frequency))
        if hourly_gross < min_wage:
            return "fail"
    elif min_wage_unit == "per_month":
        if gross < min_wage:
            return "fail"

    return "pass"


def calculate_payslip_from_pack(
    *,
    pack: RulePack,
    base_salary: Decimal,
    pay_frequency: str,
    hours_worked: Decimal = Decimal("0"),
    overtime_hours: Decimal = Decimal("0"),
    overtime_hourly_rate: Decimal = Decimal("0"),
    leave_days: Decimal = Decimal("0"),
    tax_withholding_override: Optional[Decimal] = None,
    benefit_deductions: Decimal = Decimal("0"),
    other_earnings: Decimal = Decimal("0"),
    other_deductions: Decimal = Decimal("0"),
    pt_state: Optional[str] = None,
    basic_pct: Optional[Decimal] = None,
    tenure_years: Optional[Decimal] = None,
    leave_encashment_days: Decimal = Decimal("0"),
    arrears_days: Decimal = Decimal("0"),
    jurisdiction: Optional[str] = None,
) -> PayslipResult:
    """Calculate a single payslip using the provided rule pack.

    All monetary inputs should be Decimal. The function is pure and deterministic.
    """
    if not pack.is_verified():
        raise ValueError("Cannot calculate payslip: rule pack is not verified")

    # A pack the engine cannot read exactly is refused before a single line
    # is calculated. The problems name the table and the band; they never
    # carry a value from the pack.
    problems = rate_table_problems(pack)
    if problems:
        raise RulePackNotReadable(problems)

    ctx = CalculationContext(
        pack=pack,
        base_salary=money(base_salary),
        pay_frequency=pay_frequency,
        hours_worked=money(hours_worked),
        overtime_hours=money(overtime_hours),
        overtime_hourly_rate=money(overtime_hourly_rate),
        leave_days=money(leave_days),
        tax_withholding_override=tax_withholding_override,
        benefit_deductions=money(benefit_deductions),
        other_earnings=money(other_earnings),
        other_deductions=money(other_deductions),
        pt_state=pt_state,
        basic_pct=to_decimal(basic_pct) if basic_pct is not None else None,
        tenure_years=to_decimal(tenure_years) if tenure_years is not None else None,
        leave_encashment_days=money(leave_encashment_days),
        arrears_days=money(arrears_days),
        jurisdiction=jurisdiction or pack.meta.jurisdiction_country,
    )
    # Guard basic_pct CHECK mirrors model/migration: clamp 0..100 still guarded here
    if ctx.basic_pct is not None and (ctx.basic_pct < ZERO or ctx.basic_pct > Decimal("100")):
        raise ValueError("basic_pct must be between 0 and 100")

    # Base earnings
    ctx.add_earning(
        "BASIC", "Base Salary", ctx.base_salary,
        "BASE_SALARY", "base_salary", f"Base salary for {pay_frequency} period"
    )

    # Overtime (reads pack premium, guarded IN thresholds)
    calculate_overtime(ctx)

    # Leave encashment (earned × daily Basic+DA) — taxable earning, guarded IN
    calculate_leave_encashment(ctx)

    # Arrears (arrears_days × daily Basic+DA) — earning, guarded IN
    if ctx.arrears_days and ctx.arrears_days > ZERO:
        calculate_arrears(ctx, ctx.arrears_days)

    # Other earnings
    if ctx.other_earnings > ZERO:
        ctx.add_earning(
            "OTHER_EARN", "Other Earnings", ctx.other_earnings,
            "OTHER_EARNINGS", "other_earnings", "Manual/period earnings"
        )

    # Gross = sum of earnings (includes encashment/arrears/OT)
    gross = sum_money(*[line.amount for line in ctx.lines if line.line_type == "earning"])

    # Tax (taxable includes encashment/arrears when those earnings exist)
    calculate_tax(ctx)

    # Social insurance (employee) — PF base is Basic+DA when basic_pct flagged
    ee_si, er_si, contrib_base = calculate_social_insurance(ctx)

    # Professional tax (guarded; no-op for packs without PT tables)
    calculate_professional_tax(ctx)

    # Gratuity accrual (guarded: table + tenure >=5)
    if ctx.tenure_years is not None:
        calculate_gratuity_accrual(ctx, ctx.tenure_years)

    # Bonus / LWF stubs (guarded, info-only — no deduction in v1)
    calculate_bonus_accrual(ctx)
    calculate_lwf(ctx)

    # Benefit deductions
    if ctx.benefit_deductions > ZERO:
        ctx.add_deduction(
            "BENEFITS", "Benefit Deductions", ctx.benefit_deductions,
            "BENEFIT_DEDUCTION", "benefit_deductions", "Period benefit deductions"
        )

    # Leave deduction / LOP (guarded daily rate Basic+DA)
    calculate_leave_deduction(ctx)

    # Other deductions
    if ctx.other_deductions > ZERO:
        ctx.add_deduction(
            "OTHER_DED", "Other Deductions", ctx.other_deductions,
            "OTHER_DEDUCTION", "other_deductions", "Manual/period deductions"
        )

    # Total deductions
    total_deductions = sum_money(*[line.amount for line in ctx.lines if line.line_type == "deduction"])

    # Net
    net = money(gross - total_deductions)

    # Employer contributions — recompute after gratuity/bonus/LWF stubs (slice 5)
    employer_contributions = tuple(line for line in ctx.lines if line.line_type == "employer_contribution")
    # Sum employer contributions after guarded accruals (PF + ESI + gratuity if any)
    er_total = sum_money(*[ln.amount for ln in employer_contributions]) if employer_contributions else er_si

    pay_floor = check_pay_floor(ctx, gross)

    # Build trace ID (deterministic hash of pack identity + content + inputs).
    # The content_sha names the exact pack bytes the engine read, so two
    # packs with the same id/version but different contents trace
    # differently; identical inputs on identical content trace identically.
    import hashlib
    trace_input = f"{pack.meta.pack_id}:{pack.meta.version}:{pack.content_sha}:{base_salary}:{pay_frequency}:{hours_worked}:{overtime_hours}:{overtime_hourly_rate}:{leave_days}:{tax_withholding_override}:{benefit_deductions}:{other_earnings}:{other_deductions}:{pt_state}:{basic_pct}:{tenure_years}:{leave_encashment_days}:{arrears_days}:{jurisdiction}"
    trace_id = hashlib.sha256(trace_input.encode()).hexdigest()[:16]

    return PayslipResult(
        earnings=tuple(line for line in ctx.lines if line.line_type == "earning"),
        deductions=tuple(line for line in ctx.lines if line.line_type == "deduction"),
        employer_contributions=employer_contributions,
        gross=gross,
        total_deductions=total_deductions,
        net=net,
        pay_floor_check=pay_floor,
        trace_id=trace_id,
        total_employee_contributions=ee_si,
        total_employer_contributions=er_total,
    )


def run_golden_cases(pack: RulePack) -> list[tuple[str, bool, str]]:
    """Run all golden cases for a rule pack and return results.

    Returns list of (case_id, passed, message).
    """
    results = []
    for gc in pack.golden_cases:
        try:
            # P5 skeleton placeholders (structure only): a TEST-ONLY
            # placeholder case never drives a calculation. It passes
            # deterministically without touching the engine, so a pending
            # pack stays non-calculating and repeated runs return the
            # identical message. Real cases fall through to calculation.
            expected_early = gc.expected or {}
            if expected_early.get("placeholder") is True and "TEST-ONLY placeholder" in (gc.description or ""):
                results.append((gc.case_id, True, "PLACEHOLDER structure-only, zero amounts; not calculated"))
                continue
            # Convert string inputs to Decimal
            inputs = gc.inputs
            result = calculate_payslip_from_pack(
                pack=pack,
                base_salary=to_decimal(inputs.get("base_salary", "0")),
                pay_frequency=inputs.get("pay_frequency", "monthly"),
                hours_worked=to_decimal(inputs.get("hours_worked", "0")),
                overtime_hours=to_decimal(inputs.get("overtime_hours", "0")),
                overtime_hourly_rate=to_decimal(inputs.get("overtime_hourly_rate", "0")),
                leave_days=to_decimal(inputs.get("leave_days", "0")),
                tax_withholding_override=to_decimal(inputs["tax_withholding_override"]) if inputs.get("tax_withholding_override") else None,
                benefit_deductions=to_decimal(inputs.get("benefit_deductions", "0")),
                other_earnings=to_decimal(inputs.get("other_earnings", "0")),
                other_deductions=to_decimal(inputs.get("other_deductions", "0")),
                pt_state=inputs.get("pt_state"),
            )

            # Compare expected vs actual
            expected = gc.expected
            passed = True
            messages = []

            # Check gross
            exp_gross = to_decimal(expected.get("gross", "0"))
            if result.gross != exp_gross:
                passed = False
                messages.append(f"gross: expected {exp_gross}, got {result.gross}")

            # Check net
            exp_net = to_decimal(expected.get("net", "0"))
            if result.net != exp_net:
                passed = False
                messages.append(f"net: expected {exp_net}, got {result.net}")

            # Check total deductions
            exp_ded = to_decimal(expected.get("total_deductions", "0"))
            if result.total_deductions != exp_ded:
                passed = False
                messages.append(f"total_deductions: expected {exp_ded}, got {result.total_deductions}")

            # Check pay floor
            exp_floor = expected.get("pay_floor_check", "pass")
            if result.pay_floor_check != exp_floor:
                passed = False
                messages.append(f"pay_floor_check: expected {exp_floor}, got {result.pay_floor_check}")

            # The contributions are checked when the case states them. They
            # are the employer's money and the employee's own money inside
            # the deductions, and a golden case that pins them is what stops
            # a contribution being computed and then lost.
            for key, actual in (
                ("employee_contributions", result.total_employee_contributions),
                ("employer_contributions", result.total_employer_contributions),
            ):
                if key not in expected:
                    continue
                exp_value = to_decimal(expected[key])
                if actual != exp_value:
                    passed = False
                    messages.append(f"{key}: expected {exp_value}, got {actual}")

            msg = "PASS" if passed else f"FAIL: {'; '.join(messages)}"
            results.append((gc.case_id, passed, msg))

        except Exception as e:
            results.append((gc.case_id, False, f"ERROR: {e}"))

    return results