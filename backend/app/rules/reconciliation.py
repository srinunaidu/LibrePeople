"""Reconciliation report structure and generation.

The reconciliation report ties every payslip total to its inputs and fails
if any total cannot be traced. It is the audit backbone of the payroll engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4
import json
import hashlib


@dataclass
class ReconciliationLine:
    """One line in the reconciliation — maps a payslip line to its source."""
    payslip_id: str
    employee_id: str
    line_code: str
    line_name: str
    line_type: str  # earning | deduction | employer_contribution
    amount: str  # Decimal as string
    rule_id: str
    rule_version: str
    input_source: str  # e.g., "base_salary", "rule_pack:tax_bands:BAND_1", "overtime_hours"
    calculation: str   # Human-readable formula
    trace_id: str      # Hash linking to the calculation run


@dataclass
class PayslipReconciliation:
    """Reconciliation for a single payslip."""
    payslip_id: str
    employee_id: str
    pay_run_id: str
    gross: str
    total_deductions: str
    net: str
    trace_id: str
    employee_contributions: str = "0"
    employer_contributions: str = "0"
    lines: list[ReconciliationLine] = field(default_factory=list)

    def add_line(self, line: ReconciliationLine) -> None:
        self.lines.append(line)

    def verify_totals(self) -> tuple[bool, list[str]]:
        """Verify that gross = sum(earnings), net = gross - deductions, etc."""
        errors = []
        from decimal import Decimal
        from app.rules.engine import EMPLOYEE_CONTRIBUTION_RULE_ID
        gross_sum = sum(
            (Decimal(l.amount) for l in self.lines if l.line_type == "earning"),
            Decimal("0"),
        )
        ded_sum = sum(
            (Decimal(l.amount) for l in self.lines if l.line_type == "deduction"),
            Decimal("0"),
        )
        ee_sum = sum(
            (
                Decimal(l.amount)
                for l in self.lines
                if l.line_type == "deduction" and l.rule_id == EMPLOYEE_CONTRIBUTION_RULE_ID
            ),
            Decimal("0"),
        )
        er_sum = sum(
            (Decimal(l.amount) for l in self.lines if l.line_type == "employer_contribution"),
            Decimal("0"),
        )

        if str(gross_sum.quantize(Decimal("0.01"))) != self.gross:
            errors.append(f"Gross mismatch: sum(earnings)={gross_sum} vs recorded gross={self.gross}")
        if str(ded_sum.quantize(Decimal("0.01"))) != self.total_deductions:
            errors.append(f"Deductions mismatch: sum(deductions)={ded_sum} vs recorded={self.total_deductions}")

        net_calc = gross_sum - ded_sum
        if str(net_calc.quantize(Decimal("0.01"))) != self.net:
            errors.append(f"Net mismatch: gross-deductions={net_calc} vs recorded net={self.net}")

        if str(ee_sum.quantize(Decimal("0.01"))) != self.employee_contributions:
            errors.append(
                f"Employee contributions mismatch: sum={ee_sum} vs "
                f"recorded={self.employee_contributions}"
            )
        if str(er_sum.quantize(Decimal("0.01"))) != self.employer_contributions:
            errors.append(
                f"Employer contributions mismatch: sum={er_sum} vs "
                f"recorded={self.employer_contributions}"
            )

        return len(errors) == 0, errors


@dataclass
class PayRunReconciliation:
    """Full reconciliation for a pay run."""
    reconciliation_id: str
    pay_run_id: str
    period_start: str
    period_end: str
    pay_date: str
    rule_pack_id: str
    rule_pack_version: str
    rule_pack_status: str
    generated_at: str
    employee_count: int
    total_gross: str
    total_deductions: str
    total_employee_contributions: str
    total_employer_contributions: str
    total_net: str
    payslips: list[PayslipReconciliation] = field(default_factory=list)
    status: str = "pending"  # pending | passed | failed
    errors: list[str] = field(default_factory=list)

    def add_payslip(self, ps: PayslipReconciliation) -> None:
        self.payslips.append(ps)

    def verify_all(self) -> bool:
        """Verify all payslips and aggregate totals."""
        all_errors = []
        gross_sum = Decimal("0")
        ded_sum = Decimal("0")
        ee_sum = Decimal("0")
        er_sum = Decimal("0")
        net_sum = Decimal("0")

        for ps in self.payslips:
            ok, errors = ps.verify_totals()
            if not ok:
                all_errors.extend([f"Payslip {ps.payslip_id}: {e}" for e in errors])

            gross_sum += Decimal(ps.gross)
            ded_sum += Decimal(ps.total_deductions)
            net_sum += Decimal(ps.net)
            ee_sum += Decimal(ps.employee_contributions)
            # Employer contributions sum from lines
            for line in ps.lines:
                if line.line_type == "employer_contribution":
                    er_sum += Decimal(line.amount)

        # Check run totals
        if str(gross_sum.quantize(Decimal("0.01"))) != self.total_gross:
            all_errors.append(f"Run gross mismatch: sum={gross_sum} vs recorded={self.total_gross}")
        if str(ded_sum.quantize(Decimal("0.01"))) != self.total_deductions:
            all_errors.append(f"Run deductions mismatch: sum={ded_sum} vs recorded={self.total_deductions}")
        if str(ee_sum.quantize(Decimal("0.01"))) != self.total_employee_contributions:
            all_errors.append(
                f"Run employee contributions mismatch: sum={ee_sum} vs "
                f"recorded={self.total_employee_contributions}"
            )
        if str(er_sum.quantize(Decimal("0.01"))) != self.total_employer_contributions:
            all_errors.append(f"Run employer contributions mismatch: sum={er_sum} vs recorded={self.total_employer_contributions}")
        if str(net_sum.quantize(Decimal("0.01"))) != self.total_net:
            all_errors.append(f"Run net mismatch: sum={net_sum} vs recorded={self.total_net}")

        self.errors = all_errors
        self.status = "passed" if not all_errors else "failed"
        return not all_errors

    def to_json(self) -> str:
        """Serialize to JSON with Decimal values as strings."""
        return json.dumps(asdict(self), default=str, indent=2)

    @classmethod
    def from_json(cls, data: str) -> "PayRunReconciliation":
        """Deserialize from JSON."""
        d = json.loads(data)
        # Reconstruct nested objects
        payslips = []
        for ps_data in d.get("payslips", []):
            lines = [ReconciliationLine(**l) for l in ps_data.pop("lines", [])]
            ps = PayslipReconciliation(**ps_data)
            ps.lines = lines
            payslips.append(ps)
        d["payslips"] = payslips
        return cls(**d)


def build_reconciliation(
    *,
    pay_run_id: str,
    period_start: date,
    period_end: date,
    pay_date: date,
    rule_pack_id: str,
    rule_pack_version: str,
    rule_pack_status: str,
    payslip_results: list[tuple[str, str, "PayslipResult"]],  # (payslip_id, employee_id, PayslipResult)
) -> PayRunReconciliation:
    """Build a reconciliation record from a completed pay run calculation."""
    from app.rules.engine import PayslipResult

    recon = PayRunReconciliation(
        reconciliation_id=str(uuid4()),
        pay_run_id=pay_run_id,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        pay_date=pay_date.isoformat(),
        rule_pack_id=rule_pack_id,
        rule_pack_version=rule_pack_version,
        rule_pack_status=rule_pack_status,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        employee_count=len(payslip_results),
        total_gross="0",
        total_deductions="0",
        total_employee_contributions="0",
        total_employer_contributions="0",
        total_net="0",
    )

    total_gross = Decimal("0")
    total_ded = Decimal("0")
    total_ee = Decimal("0")
    total_er = Decimal("0")
    total_net = Decimal("0")

    for payslip_id, employee_id, result in payslip_results:
        ps_recon = PayslipReconciliation(
            payslip_id=payslip_id,
            employee_id=employee_id,
            pay_run_id=pay_run_id,
            gross=str(result.gross),
            total_deductions=str(result.total_deductions),
            net=str(result.net),
            trace_id=result.trace_id,
            employee_contributions=str(result.total_employee_contributions),
            employer_contributions=str(result.total_employer_contributions),
        )

        for line in result.earnings:
            ps_recon.add_line(ReconciliationLine(
                payslip_id=payslip_id,
                employee_id=employee_id,
                line_code=line.code,
                line_name=line.name,
                line_type=line.line_type,
                amount=str(line.amount),
                rule_id=line.rule_id,
                rule_version=line.rule_version,
                input_source=line.input_source,
                calculation=line.calculation,
                trace_id=result.trace_id,
            ))

        for line in result.deductions:
            ps_recon.add_line(ReconciliationLine(
                payslip_id=payslip_id,
                employee_id=employee_id,
                line_code=line.code,
                line_name=line.name,
                line_type=line.line_type,
                amount=str(line.amount),
                rule_id=line.rule_id,
                rule_version=line.rule_version,
                input_source=line.input_source,
                calculation=line.calculation,
                trace_id=result.trace_id,
            ))

        for line in result.employer_contributions:
            ps_recon.add_line(ReconciliationLine(
                payslip_id=payslip_id,
                employee_id=employee_id,
                line_code=line.code,
                line_name=line.name,
                line_type=line.line_type,
                amount=str(line.amount),
                rule_id=line.rule_id,
                rule_version=line.rule_version,
                input_source=line.input_source,
                calculation=line.calculation,
                trace_id=result.trace_id,
            ))

        recon.add_payslip(ps_recon)
        total_gross += result.gross
        total_ded += result.total_deductions
        total_net += result.net
        total_ee += result.total_employee_contributions
        for line in result.employer_contributions:
            total_er += line.amount

    recon.total_gross = str(total_gross)
    recon.total_deductions = str(total_ded)
    recon.total_employee_contributions = str(total_ee)
    recon.total_employer_contributions = str(total_er)
    recon.total_net = str(total_net)

    return recon


def verify_reconciliation_file(path: str) -> tuple[bool, list[str]]:
    """Load and verify a reconciliation file from disk."""
    with open(path, "r") as f:
        recon = PayRunReconciliation.from_json(f.read())
    ok = recon.verify_all()
    return ok, recon.errors


# --- Export formats -----------------------------------------------------------

def export_reconciliation_csv(recon: PayRunReconciliation) -> str:
    """Export reconciliation as CSV for auditors."""
    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "reconciliation_id", "pay_run_id", "payslip_id", "employee_id",
        "line_code", "line_name", "line_type", "amount",
        "rule_id", "rule_version", "input_source", "calculation", "trace_id"
    ])

    for ps in recon.payslips:
        for line in ps.lines:
            writer.writerow([
                recon.reconciliation_id,
                recon.pay_run_id,
                ps.payslip_id,
                ps.employee_id,
                line.line_code,
                line.line_name,
                line.line_type,
                line.amount,
                line.rule_id,
                line.rule_version,
                line.input_source,
                line.calculation,
                line.trace_id,
            ])

    return output.getvalue()


def export_reconciliation_summary_csv(recon: PayRunReconciliation) -> str:
    """Export pay-run level summary as CSV."""
    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "reconciliation_id", "pay_run_id", "period_start", "period_end", "pay_date",
        "rule_pack_id", "rule_pack_version", "rule_pack_status",
        "employee_count", "total_gross", "total_deductions",
        "total_employee_contributions", "total_employer_contributions",
        "total_net", "status", "generated_at"
    ])

    writer.writerow([
        recon.reconciliation_id, recon.pay_run_id, recon.period_start, recon.period_end,
        recon.pay_date, recon.rule_pack_id, recon.rule_pack_version, recon.rule_pack_status,
        recon.employee_count, recon.total_gross, recon.total_deductions,
        recon.total_employee_contributions, recon.total_employer_contributions,
        recon.total_net, recon.status, recon.generated_at
    ])

    return output.getvalue()