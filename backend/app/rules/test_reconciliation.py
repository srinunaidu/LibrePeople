"""Tests for the reconciliation report."""
from __future__ import annotations

from decimal import Decimal
from datetime import date

import pytest

from app.rules.engine import calculate_payslip_from_pack
from app.rules.loader import load_rule_pack_from_dict
from app.rules.reconciliation import (
    build_reconciliation,
    PayRunReconciliation,
    ReconciliationLine,
    PayslipReconciliation,
    export_reconciliation_csv,
    export_reconciliation_summary_csv,
)


def make_test_pack():
    """Minimal verified pack for reconciliation testing."""
    return {
        "pack_id": "test-recon",
        "name": "Reconciliation Test Pack",
        "jurisdiction": {"country": "ZZ", "region": "TEST", "display_name": "Test"},
        "version": "1.0.0",
        "status": "verified",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "tz": "UTC",
        "source": {
            "document_title": "Test", "publisher": "Test", "document_reference": "TEST-001",
            "url": "https://example.invalid", "retrieved_on": "2026-10-21", "notes": ""
        },
        "verification": {
            "verified_by_name": "Test", "verified_by_role": "Test",
            "verified_on": "2026-10-21", "source_document_reference": "TEST-001",
            "golden_case_set_id": "gc-1"
        },
        "rate_tables": {
            "tax_bands": {
                # A banded table: the value is the lower bound of the band,
                # the max_value is its upper bound and the rate is the
                # percentage rate that applies inside it.
                "description": "A single band at 10%", "effective_from": "2026-01-01",
                "entries": [{"code": "FLAT", "label": "Flat", "value": 0, "max_value": 1000000, "rate": 10, "unit": "currency_amount", "notes": ""}]
            },
            "social_insurance_employee": {
                "description": "EE", "effective_from": "2026-01-01",
                "values": {"pension": {"value": 5.0, "unit": "percent", "label": "Pension", "notes": ""}}
            },
            "social_insurance_employer": {
                "description": "ER", "effective_from": "2026-01-01",
                "values": {"pension": {"value": 7.0, "unit": "percent", "label": "Pension", "notes": ""}}
            }
        },
        "thresholds": {
            "weekly_max_hours": 40, "daily_min_rest_hours": 11, "max_consecutive_work_days": 5,
            "daily_overtime_threshold_hours": 8, "weekly_overtime_threshold_hours": 40,
            "overtime_premium_multiplier": 1.5, "overtime_daily_cap_hours": 2,
            "minimum_wage_amount": 10.00, "minimum_wage_unit": "per_hour"
        },
        "overtime": {
            "daily_threshold_hours": 8, "weekly_threshold_hours": 40,
            "premium_multiplier": 1.5, "daily_cap_hours": 2,
            "rules": [{"rule_id": "OT", "description": "OT", "severity": "block", "applies_when": ">"}]
        },
        "leave_types": [],
        "working_time_limits": {
            "max_weekly_hours": 40, "min_daily_rest_hours": 11, "max_consecutive_days": 5,
            "max_night_work_hours": 8, "min_rest_between_shifts_hours": 11, "rules": []
        },
        "break_rules": [],
        "mandatory_payslip_fields": ["gross_pay", "net_pay"],
        "mandatory_payslip_notes": [],
        "pay_frequency_rules": {
            "allowed_frequencies": ["monthly"], "pay_day_rule": "End", "cut_off_days_before_pay_day": 2,
            "pay_date_rule_id": "PAY_END"
        },
        "reporting_obligations": [],
        "public_holiday_rules": {"source": "Test", "region_dependent": False, "holiday_count_by_year": {"2026": 10}},
        "signing": {"algorithm": "ed25519", "key_id": "k", "signature": "s", "signed_at": "2026-10-21T00:00:00Z", "signed_by": "Test"},
        "golden_cases": []
    }


class TestReconciliation:
    @pytest.fixture
    def pack(self):
        return load_rule_pack_from_dict(make_test_pack())

    def test_build_reconciliation(self, pack):
        """Build reconciliation from payslip results."""
        # Calculate two payslips
        result1 = calculate_payslip_from_pack(
            pack=pack, base_salary=Decimal("5000"), pay_frequency="monthly",
            overtime_hours=Decimal("0"), benefit_deductions=Decimal("100")
        )
        result2 = calculate_payslip_from_pack(
            pack=pack, base_salary=Decimal("4000"), pay_frequency="monthly",
            overtime_hours=Decimal("2"), overtime_hourly_rate=Decimal("25"),
            benefit_deductions=Decimal("50")
        )

        recon = build_reconciliation(
            pay_run_id="PR-001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            pay_date=date(2026, 2, 1),
            rule_pack_id=pack.meta.pack_id,
            rule_pack_version=pack.meta.version,
            rule_pack_status=pack.meta.status,
            payslip_results=[
                ("PS-001", "EMP-001", result1),
                ("PS-002", "EMP-002", result2),
            ],
        )

        assert recon.employee_count == 2
        assert recon.rule_pack_id == "test-recon"
        assert recon.rule_pack_version == "1.0.0"
        assert len(recon.payslips) == 2

    def test_reconciliation_verification_passes(self, pack):
        """A correctly built reconciliation should verify."""
        result1 = calculate_payslip_from_pack(pack=pack, base_salary=Decimal("5000"), pay_frequency="monthly")
        result2 = calculate_payslip_from_pack(pack=pack, base_salary=Decimal("4000"), pay_frequency="monthly")

        recon = build_reconciliation(
            pay_run_id="PR-001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            pay_date=date(2026, 2, 1),
            rule_pack_id=pack.meta.pack_id,
            rule_pack_version=pack.meta.version,
            rule_pack_status=pack.meta.status,
            payslip_results=[("PS-001", "EMP-001", result1), ("PS-002", "EMP-002", result2)],
        )

        ok = recon.verify_all()
        assert ok, f"Reconciliation failed: {recon.errors}"
        assert recon.status == "passed"
        assert len(recon.errors) == 0

    def test_reconciliation_detects_tampered_totals(self, pack):
        """If a payslip total is manually changed, reconciliation should fail."""
        result1 = calculate_payslip_from_pack(pack=pack, base_salary=Decimal("5000"), pay_frequency="monthly")

        recon = build_reconciliation(
            pay_run_id="PR-001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            pay_date=date(2026, 2, 1),
            rule_pack_id=pack.meta.pack_id,
            rule_pack_version=pack.meta.version,
            rule_pack_status=pack.meta.status,
            payslip_results=[("PS-001", "EMP-001", result1)],
        )

        # Tamper with the recorded gross
        recon.payslips[0].gross = "9999.99"

        ok = recon.verify_all()
        assert not ok
        assert recon.status == "failed"
        assert any("Gross mismatch" in e for e in recon.errors)

    def test_reconciliation_detects_missing_line(self, pack):
        """If a line is removed from a payslip, reconciliation should fail."""
        result1 = calculate_payslip_from_pack(pack=pack, base_salary=Decimal("5000"), pay_frequency="monthly")

        recon = build_reconciliation(
            pay_run_id="PR-001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            pay_date=date(2026, 2, 1),
            rule_pack_id=pack.meta.pack_id,
            rule_pack_version=pack.meta.version,
            rule_pack_status=pack.meta.status,
            payslip_results=[("PS-001", "EMP-001", result1)],
        )

        # Remove a line
        recon.payslips[0].lines = recon.payslips[0].lines[:-1]

        ok = recon.verify_all()
        assert not ok
        assert recon.status == "failed"

    def test_reconciliation_json_roundtrip(self, pack):
        """Reconciliation can be serialized to JSON and back."""
        result1 = calculate_payslip_from_pack(pack=pack, base_salary=Decimal("5000"), pay_frequency="monthly")

        recon = build_reconciliation(
            pay_run_id="PR-001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            pay_date=date(2026, 2, 1),
            rule_pack_id=pack.meta.pack_id,
            rule_pack_version=pack.meta.version,
            rule_pack_status=pack.meta.status,
            payslip_results=[("PS-001", "EMP-001", result1)],
        )

        json_str = recon.to_json()
        recon2 = PayRunReconciliation.from_json(json_str)

        assert recon2.reconciliation_id == recon.reconciliation_id
        assert recon2.pay_run_id == recon.pay_run_id
        assert len(recon2.payslips) == 1
        assert len(recon2.payslips[0].lines) == len(recon.payslips[0].lines)

    def test_csv_export(self, pack):
        """CSV export produces valid rows."""
        result1 = calculate_payslip_from_pack(pack=pack, base_salary=Decimal("5000"), pay_frequency="monthly")

        recon = build_reconciliation(
            pay_run_id="PR-001",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            pay_date=date(2026, 2, 1),
            rule_pack_id=pack.meta.pack_id,
            rule_pack_version=pack.meta.version,
            rule_pack_status=pack.meta.status,
            payslip_results=[("PS-001", "EMP-001", result1)],
        )

        csv_output = export_reconciliation_csv(recon)
        lines = csv_output.strip().split("\n")
        assert len(lines) >= 2  # header + at least one data row
        assert "line_code" in lines[0]  # header check

        summary_csv = export_reconciliation_summary_csv(recon)
        summary_lines = summary_csv.strip().split("\n")
        assert len(summary_lines) == 2  # header + one data row

    def test_payslip_reconciliation_verify_totals(self, pack):
        """PayslipReconciliation.verify_totals checks line sums."""
        result1 = calculate_payslip_from_pack(pack=pack, base_salary=Decimal("5000"), pay_frequency="monthly")

        ps_recon = PayslipReconciliation(
            payslip_id="PS-001",
            employee_id="EMP-001",
            pay_run_id="PR-001",
            gross=str(result1.gross),
            total_deductions=str(result1.total_deductions),
            net=str(result1.net),
            trace_id=result1.trace_id,
            employee_contributions=str(result1.total_employee_contributions),
            employer_contributions=str(result1.total_employer_contributions),
        )

        for line in result1.earnings:
            ps_recon.add_line(ReconciliationLine(
                payslip_id="PS-001", employee_id="EMP-001",
                line_code=line.code, line_name=line.name, line_type=line.line_type,
                amount=str(line.amount), rule_id=line.rule_id, rule_version=line.rule_version,
                input_source=line.input_source, calculation=line.calculation, trace_id=result1.trace_id
            ))
        for line in result1.deductions:
            ps_recon.add_line(ReconciliationLine(
                payslip_id="PS-001", employee_id="EMP-001",
                line_code=line.code, line_name=line.name, line_type=line.line_type,
                amount=str(line.amount), rule_id=line.rule_id, rule_version=line.rule_version,
                input_source=line.input_source, calculation=line.calculation, trace_id=result1.trace_id
            ))
        for line in result1.employer_contributions:
            ps_recon.add_line(ReconciliationLine(
                payslip_id="PS-001", employee_id="EMP-001",
                line_code=line.code, line_name=line.name, line_type=line.line_type,
                amount=str(line.amount), rule_id=line.rule_id, rule_version=line.rule_version,
                input_source=line.input_source, calculation=line.calculation, trace_id=result1.trace_id
            ))

        ok, errors = ps_recon.verify_totals()
        assert ok, f"Payslip verification failed: {errors}"

    def test_payslip_reconciliation_detects_a_tampered_contribution(self, pack):
        """A contribution that does not match its lines is a failure.

        The employer's contribution is the employer's money and the
        employee's is the employee's own; neither is part of the pay
        totals, so nothing else on the payslip accounts for them.
        """
        result1 = calculate_payslip_from_pack(pack=pack, base_salary=Decimal("5000"), pay_frequency="monthly")

        ps_recon = PayslipReconciliation(
            payslip_id="PS-001",
            employee_id="EMP-001",
            pay_run_id="PR-001",
            gross=str(result1.gross),
            total_deductions=str(result1.total_deductions),
            net=str(result1.net),
            trace_id=result1.trace_id,
            employee_contributions=str(result1.total_employee_contributions),
            employer_contributions="1.00",
        )
        for line in list(result1.earnings) + list(result1.deductions) + list(result1.employer_contributions):
            ps_recon.add_line(ReconciliationLine(
                payslip_id="PS-001", employee_id="EMP-001",
                line_code=line.code, line_name=line.name, line_type=line.line_type,
                amount=str(line.amount), rule_id=line.rule_id, rule_version=line.rule_version,
                input_source=line.input_source, calculation=line.calculation, trace_id=result1.trace_id
            ))

        ok, errors = ps_recon.verify_totals()
        assert not ok
        assert any("Employer contributions mismatch" in e for e in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])