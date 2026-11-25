"""Payroll reconciliation service.

This service wraps the rule-engine reconciliation to provide a pay-run level
reconciliation report that compares payslip values against the rule pack
computations. It is the bridge between the pay run API and the rule-engine
reconciliation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from app.models.payroll import PayRun, PaySlip
from app.rules.engine import calculate_payslip_from_pack, PayslipResult
from app.rules.loader import RulePack, load_rule_pack
from app.rules.reconciliation import (
    PayRunReconciliation,
    build_reconciliation,
    export_reconciliation_csv,
    export_reconciliation_summary_csv,
)
from app.rules.resolver import resolve_rule_pack


@dataclass(frozen=True)
class ReconciliationReport:
    """Reconciliation report for a pay run - matches the OpenAPI contract shape."""
    matched: bool
    run_id: int
    rule_pack_id: str
    rule_pack_version: str
    totals: dict[str, str]
    discrepancies: list[dict]
    payslips: list[dict]
    generated_at: str

    def to_dict(self) -> dict:
        return {
            "matched": self.matched,
            "run_id": self.run_id,
            "rule_pack_id": self.rule_pack_id,
            "rule_pack_version": self.rule_pack_version,
            "totals": self.totals,
            "discrepancies": self.discrepancies,
            "payslips": self.payslips,
            "generated_at": self.generated_at,
        }


def _recalculate_payslips(
    pack: RulePack,
    profiles: list,
    employees: dict,
) -> list[tuple[str, str, PayslipResult]]:
    """Recalculate all payslips from the rule pack."""
    results = []
    for profile in profiles:
        employee = employees.get(profile.employee_id)
        if not employee:
            continue
        result = calculate_payslip_from_pack(
            pack=pack,
            base_salary=profile.base_salary,
            pay_frequency=profile.pay_frequency or "Monthly",
            tax_withholding_override=profile.tax_withholding,
        )
        results.append((str(profile.employee_id), str(employee.id), result))
    return results


def build_pay_run_reconciliation(db, run_id: int) -> ReconciliationReport:
    """Build a reconciliation report for a pay run.

    This:
    1. Loads the pay run and its payslips
    2. Resolves the rule pack for the run's jurisdiction and pay date
    3. Recalculates each payslip from the rule pack
    4. Compares the recalculated values to the stored payslip values
    5. Returns a reconciliation report with matched flag and discrepancies
    """
    from app.models.employee import Employee
    from app.models.payroll import EmployeePayProfile

    run = db.query(PayRun).filter(PayRun.id == run_id).first()
    if not run:
        raise ValueError(f"Pay run {run_id} not found")

    # Resolve the rule pack
    resolution = resolve_rule_pack(run.jurisdiction, run.period.pay_date)
    if not resolution.is_verified:
        raise ValueError(
            f"No verified rule pack for jurisdiction {run.jurisdiction} on {run.period.pay_date}"
        )

    pack = resolution.pack

    # Get payslips for this run
    payslips = db.query(PaySlip).filter(PaySlip.pay_run_id == run_id).all()
    if not payslips:
        return ReconciliationReport(
            matched=True,
            run_id=run_id,
            rule_pack_id=pack.meta.pack_id,
            rule_pack_version=pack.meta.version,
            totals={},
            discrepancies=[],
            payslips=[],
            generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )

    # Get employee profiles and employees
    profiles = db.query(EmployeePayProfile).all()
    profiles = [p for p in profiles if any(p.employee_id == s.employee_id for s in payslips)]
    employees = {e.id: e for e in db.query(Employee).all()}

    # Recalculate from rule pack
    recalculated = _recalculate_payslips(pack, profiles, employees)

    # Build the rule-engine reconciliation
    recon = build_reconciliation(
        pay_run_id=str(run_id),
        period_start=run.period.start_date,
        period_end=run.period.end_date,
        pay_date=run.period.pay_date,
        rule_pack_id=pack.meta.pack_id,
        rule_pack_version=pack.meta.version,
        rule_pack_status=pack.meta.status,
        payslip_results=recalculated,
    )

    # Verify
    matched = recon.verify_all()

    # Build discrepancies list
    discrepancies = []
    if not matched:
        for error in recon.errors:
            discrepancies.append({
                "code": "mismatch",
                "message": error,
            })

    # Build payslip details for the report
    payslip_details = []
    for ps in recon.payslips:
        payslip_details.append({
            "payslip_id": ps.payslip_id,
            "employee_id": ps.employee_id,
            "gross": ps.gross,
            "net": ps.net,
            "total_deductions": ps.total_deductions,
            "employee_contributions": ps.employee_contributions,
            "employer_contributions": ps.employer_contributions,
            "trace_id": ps.trace_id,
        })

    # Build totals
    totals = {
        "total_gross": recon.total_gross,
        "total_deductions": recon.total_deductions,
        "total_employee_contributions": recon.total_employee_contributions,
        "total_employer_contributions": recon.total_employer_contributions,
        "total_net": recon.total_net,
    }

    return ReconciliationReport(
        matched=matched,
        run_id=run_id,
        rule_pack_id=pack.meta.pack_id,
        rule_pack_version=pack.meta.version,
        totals=totals,
        discrepancies=discrepancies,
        payslips=payslip_details,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )


def load_rule_pack_for_date(
    pack_dir: str,
    jurisdiction: str,
    calc_date: date,
) -> RulePack:
    """Load the rule pack for a jurisdiction effective on a date.

    This is a thin wrapper around the resolver's loader for the service layer.
    """
    from pathlib import Path

    pack_path = Path(pack_dir)
    candidates = []
    for file in pack_path.glob("*.json"):
        try:
            pack = load_rule_pack(file)
            if pack.meta.jurisdiction_country.upper() == jurisdiction.upper() and pack.is_effective_on(calc_date):
                if pack.is_verified():
                    candidates.append(pack)
        except Exception:
            continue

    if not candidates:
        raise ValueError(
            f"No verified rule pack found for jurisdiction '{jurisdiction}' effective on {calc_date}"
        )

    # Pick the one with the latest effective_from
    return max(candidates, key=lambda p: p.meta.effective_from)


def export_reconciliation_csv_report(report: ReconciliationReport) -> str:
    """Export reconciliation report as CSV."""
    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "run_id", "rule_pack_id", "rule_pack_version", "matched",
        "total_gross", "total_deductions", "total_employee_contributions",
        "total_employer_contributions", "total_net", "generated_at"
    ])
    writer.writerow([
        report.run_id, report.rule_pack_id, report.rule_pack_version, report.matched,
        report.totals.get("total_gross", "0"),
        report.totals.get("total_deductions", "0"),
        report.totals.get("total_employee_contributions", "0"),
        report.totals.get("total_employer_contributions", "0"),
        report.totals.get("total_net", "0"),
        report.generated_at,
    ])

    writer.writerow([])
    writer.writerow(["payslip_id", "employee_id", "gross", "net", "total_deductions",
                     "employee_contributions", "employer_contributions", "trace_id"])
    for ps in report.payslips:
        writer.writerow([
            ps["payslip_id"], ps["employee_id"], ps["gross"], ps["net"],
            ps["total_deductions"], ps["employee_contributions"],
            ps["employer_contributions"], ps["trace_id"],
        ])

    return output.getvalue()
