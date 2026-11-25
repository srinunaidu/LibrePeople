"""Full & Final settlement calculator (India slice 5).

Reads stored payslip lines (deductions_json/earnings_json + inputs_json) and
does NOT recompute tax. Produces a structured settlement that the F&F tab
renders read-only.

The engine's guarded helpers (gratuity, leave encashment, LOP, arrears,
bonus/LWF) already wrote their lines into the payslip at process time. This
module reads those lines and combines them with tenure and notice inputs to
produce the final settlement.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.payroll import PayRun, PaySlip
from app.rules.loader import RulePack
from app.rules.money import ZERO, money, to_decimal


@dataclass(frozen=True)
class FnfSettlement:
    employee_id: int
    pay_run_id: int
    period_name: str
    pay_date: str
    jurisdiction: str
    currency: str
    basic_salary: Decimal
    basic_pct: Optional[Decimal]
    tenure_years: Optional[Decimal]
    notice_pay: Decimal
    leave_encashment: Decimal
    leave_encashment_days: Decimal
    gratuity_payable: Decimal
    gratuity_eligible: bool
    lop_recovery: Decimal
    lop_days: Decimal
    bonus_pro_rata: Decimal
    lwf_amount: Decimal
    arrears_payable: Decimal
    gross_settlement: Decimal
    net_settlement: Decimal
    lines: tuple[dict[str, Any], ...]
    notes: tuple[str, ...]


def _parse_lines(slip: PaySlip) -> tuple[list[dict], list[dict], dict]:
    earnings = []
    deductions = []
    inputs = {}
    try:
        if slip.earnings_json:
            earnings = json.loads(slip.earnings_json)
    except Exception:
        earnings = []
    try:
        if slip.deductions_json:
            deductions = json.loads(slip.deductions_json)
    except Exception:
        deductions = []
    try:
        if slip.inputs_json:
            inputs = json.loads(slip.inputs_json)
    except Exception:
        inputs = {}
    return earnings, deductions, inputs


def _amount(lines: list[dict], code: str) -> Decimal:
    for ln in lines:
        if ln.get("code") == code:
            try:
                return to_decimal(ln.get("amount"))
            except Exception:
                return ZERO
    return ZERO


def _daily_basic_da(base_salary: Decimal, basic_pct: Optional[Decimal]) -> Decimal:
    if basic_pct is not None:
        try:
            pct = to_decimal(basic_pct)
        except Exception:
            pct = ZERO
        basic_da = money(base_salary * pct / Decimal("100")) if pct and pct != ZERO else base_salary
        return money(basic_da / Decimal("26")) if basic_da != ZERO else ZERO
    return money(base_salary / Decimal("22")) if base_salary != ZERO else ZERO


def calculate_fnf(
    db: Session,
    pay_run_id: int,
    employee_id: int,
    *,
    pack: Optional[RulePack] = None,
    notice_days: Decimal = ZERO,
    bonus_pro_rata_override: Optional[Decimal] = None,
) -> FnfSettlement:
    """Calculate the Full & Final settlement for one employee/run.

    Reads from ``pay_slips.deductions_json`` / ``earnings_json`` /
    ``inputs_json`` accounting but does not mutate the run. The run must
    exist and the payslip for the employee must exist.
    """
    from app.rules.resolver import resolve_rule_pack
    from app.models.payroll import PayrollPeriod, EmployeePayProfile

    run = db.query(PayRun).filter(PayRun.id == pay_run_id).first()
    if not run:
        raise ValueError(f"pay_run {pay_run_id} not found")
    slip = (
        db.query(PaySlip)
        .filter(PaySlip.pay_run_id == pay_run_id, PaySlip.employee_id == employee_id)
        .first()
    )
    if not slip:
        raise ValueError(f"payslip for employee {employee_id} in run {pay_run_id} not found")
    period = db.query(PayrollPeriod).filter(PayrollPeriod.id == run.period_id).first()
    employee = db.get(Employee, employee_id)
    profile = db.query(EmployeePayProfile).filter(EmployeePayProfile.employee_id == employee_id).first()

    earnings, deductions, inputs = _parse_lines(slip)
    jurisdiction = (run.jurisdiction or "").strip().upper()
    currency = run.currency or slip.currency or "INR"
    base_salary = to_decimal(slip.gross_pay)  # gross is at least base; use gross for reference
    # Prefer profile base_salary if available
    if profile and profile.base_salary:
        try:
            base_salary = to_decimal(profile.base_salary)
        except Exception:
            pass
    basic_pct = None
    if profile and getattr(profile, "basic_pct", None) is not None:
        try:
            basic_pct = to_decimal(profile.basic_pct)
        except Exception:
            basic_pct = None

    # Tenure from hire_date to pay_date
    tenure_years = None
    if employee and employee.hire_date and period and period.pay_date:
        try:
            days = (period.pay_date - employee.hire_date).days
            tenure_years = money(Decimal(days) / Decimal("365.25"))
        except Exception:
            tenure_years = None
    # Allow caller tenure override via inputs_json
    if tenure_years is None and inputs.get("tenure_years"):
        try:
            tenure_years = to_decimal(inputs["tenure_years"])
        except Exception:
            tenure_years = None

    # Resolve pack if not provided
    _pack = pack
    if _pack is None and period and period.pay_date:
        try:
            res = resolve_rule_pack(jurisdiction, period.pay_date)
            # Even pending packs are readable in-memory; use the pack if dir has it
            # Loading directly to get IN pack when resolution is pending (pack is None)
            if res.pack is not None:
                _pack = res.pack
            else:
                # Fallback: load in-standard.json directly for IN
                from pathlib import Path
                from app.rules.loader import load_rule_pack
                cand = Path(__file__).resolve().parents[2] / "rule_packs" / "in-standard.json"
                if cand.is_file() and jurisdiction == "IN":
                    try:
                        _pack = load_rule_pack(str(cand))
                    except Exception:
                        _pack = None
        except Exception:
            _pack = None

    daily = _daily_basic_da(base_salary, basic_pct)

    # Leave encashment: from earnings line if present, else compute from inputs
    leave_encashment = _amount(earnings, "LEAVE_ENCASHMENT")
    leave_encashment_days = to_decimal(inputs.get("encashment_days", 0)) if inputs.get("encashment_days") else ZERO
    # Fallback to leave_encashment_days on context if no line but days present
    if leave_encashment == ZERO and leave_encashment_days and leave_encashment_days != ZERO:
        leave_encashment = money(daily * leave_encashment_days)
    # Also check slip earnings for earned encashment already computed
    if leave_encashment == ZERO:
        # try generic encashable days from inputs
        enc_days = to_decimal(inputs.get("leave_encashment_days", 0))
        if enc_days and enc_days != ZERO:
            leave_encashment = money(daily * enc_days)
            leave_encashment_days = enc_days

    # LOP recovery: from deduction line LOP or LEAVE_UNPAID
    lop_recovery = _amount(deductions, "LOP")
    if lop_recovery == ZERO:
        lop_recovery = _amount(deductions, "LEAVE_UNPAID")
    lop_days = to_decimal(inputs.get("unpaid_leave_days", 0)) if inputs.get("unpaid_leave_days") else ZERO
    if lop_days is None:
        lop_days = ZERO

    # Arrears payable
    arrears_payable = _amount(earnings, "ARREARS")
    if arrears_payable == ZERO and inputs.get("arrears_days"):
        try:
            arrears_payable = money(daily * to_decimal(inputs["arrears_days"]))
        except Exception:
            arrears_payable = ZERO

    # Gratuity payable — Payment of Gratuity Act 1972 §4: 15/26 × last Basic+DA × years, eligible ≥5yr
    gratuity_payable = ZERO
    gratuity_eligible = False
    if tenure_years is not None and tenure_years >= Decimal("5"):
        gratuity_eligible = True
        # Last drawn Basic+DA (or gross fallback)
        last_basic_da = daily * Decimal("26")  # reverses daily
        # 15/26 × years
        gratuity_payable = money(last_basic_da * Decimal("15") / Decimal("26") * tenure_years)
        # Also check if an accrual line exists and use its monthly accrual × tenure months as cross-check?
        # Keep the statutory formula as the settlement figure.
    # If pack has gratuity but tenure <5, gratuity stays 0

    # Bonus pro-rata — stub: minimal 8.33% when eligible, but v1 returns 0 unless overridden
    bonus_pro_rata = ZERO
    if bonus_pro_rata_override is not None:
        bonus_pro_rata = money(bonus_pro_rata_override)
    elif _pack is not None and _pack.get_rate_table("bonus_act"):
        # Stub: do not compute yet; leave 0 for verifier checklist
        bonus_pro_rata = ZERO

    # LWF amount — per-state stub flat
    lwf_amount = ZERO
    if _pack is not None and _pack.get_rate_table("lwf_state") and profile and getattr(profile, "pt_state", None):
        tbl = _pack.get_rate_table("lwf_state")
        key = f"lwf_{profile.pt_state.strip().lower()}" if profile.pt_state else None
        if key and key in tbl.values:
            lwf_amount = money(tbl.values[key].value)
            # But v1 stub says do not deduct; for F&F reference keep the flat as info
            # For net settlement we do not include LWF in net (info only)
            # So net excludes LWF
            pass

    # Notice pay (if any)
    try:
        nd = to_decimal(notice_days)
    except Exception:
        nd = ZERO
    notice_pay = money(daily * nd) if nd and nd != ZERO else ZERO

    # Gross settlement = sum of payable earnings (notice + encashment + gratuity + arrears + bonus)
    # LOP is a recovery (deduction) so subtract it.
    gross_settlement = money(notice_pay + leave_encashment + gratuity_payable + arrears_payable + bonus_pro_rata)
    net_settlement = money(gross_settlement - lop_recovery)
    # LWF is info-only; not included in net per slice 5 contract (stubs)

    notes = []
    if gratuity_eligible:
        notes.append("Gratuity payable per Payment of Gratuity Act 1972 §4: 15/26 × last Basic+DA × tenure_years (eligible ≥5yr).")
    else:
        notes.append("Gratuity not payable: tenure <5 years (Payment of Gratuity Act 1972 §4).")
    if _pack is not None and _pack.get_rate_table("bonus_act"):
        notes.append("Bonus Act values are stubs (8.33% min/20% max, ₹21k eligibility) — verifier checklist, not deducted in v1.")
    if _pack is not None and _pack.get_rate_table("lwf_state"):
        notes.append("LWF per-state values are stubs (MH/KA/TN/TG/WB) — verifier checklist, info only in v1.")

    lines = tuple(earnings + deductions)

    return FnfSettlement(
        employee_id=employee_id,
        pay_run_id=pay_run_id,
        period_name=period.name if period else "",
        pay_date=period.pay_date.isoformat() if period and period.pay_date else "",
        jurisdiction=jurisdiction,
        currency=currency,
        basic_salary=money(base_salary),
        basic_pct=basic_pct,
        tenure_years=tenure_years,
        notice_pay=notice_pay,
        leave_encashment=leave_encashment,
        leave_encashment_days=leave_encashment_days,
        gratuity_payable=gratuity_payable,
        gratuity_eligible=gratuity_eligible,
        lop_recovery=lop_recovery,
        lop_days=lop_days,
        bonus_pro_rata=bonus_pro_rata,
        lwf_amount=lwf_amount,
        arrears_payable=arrears_payable,
        gross_settlement=gross_settlement,
        net_settlement=net_settlement,
        lines=lines,
        notes=tuple(notes),
    )


def settlement_to_dict(s: FnfSettlement) -> dict:
    return {
        "employee_id": s.employee_id,
        "pay_run_id": s.pay_run_id,
        "period_name": s.period_name,
        "pay_date": s.pay_date,
        "jurisdiction": s.jurisdiction,
        "currency": s.currency,
        "basic_salary": str(s.basic_salary),
        "basic_pct": str(s.basic_pct) if s.basic_pct is not None else None,
        "tenure_years": str(s.tenure_years) if s.tenure_years is not None else None,
        "notice_pay": str(s.notice_pay),
        "leave_encashment": str(s.leave_encashment),
        "leave_encashment_days": str(s.leave_encashment_days),
        "gratuity_payable": str(s.gratuity_payable),
        "gratuity_eligible": s.gratuity_eligible,
        "lop_recovery": str(s.lop_recovery),
        "lop_days": str(s.lop_days),
        "bonus_pro_rata": str(s.bonus_pro_rata),
        "lwf_amount": str(s.lwf_amount),
        "arrears_payable": str(s.arrears_payable),
        "gross_settlement": str(s.gross_settlement),
        "net_settlement": str(s.net_settlement),
        "notes": list(s.notes),
        "lines": list(s.lines),
    }
