"""Determinism tests for the payroll rule engine.

These tests verify that identical inputs always produce identical outputs,
which is a core requirement for payroll calculations.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.rules.engine import calculate_payslip_from_pack, run_golden_cases
from app.rules.loader import load_rule_pack_from_dict
from app.rules.money import money, to_decimal, sum_money, prorate, apply_rate


def make_test_pack() -> dict:
    """Create a minimal valid rule pack for testing (synthetic values)."""
    return {
        "pack_id": "test-determinism",
        "name": "Determinism Test Pack",
        "jurisdiction": {
            "country": "ZZ",
            "region": "TEST",
            "display_name": "Test Jurisdiction"
        },
        "version": "1.0.0",
        "status": "verified",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "tz": "UTC",
        "source": {
            "document_title": "Test Document",
            "publisher": "Test Publisher",
            "document_reference": "TEST-001",
            "url": "https://example.invalid/test",
            "retrieved_on": "2026-10-21",
            "notes": "Test pack for determinism verification"
        },
        "verification": {
            "verified_by_name": "Test Verifier",
            "verified_by_role": "Test Role",
            "verified_on": "2026-10-21",
            "source_document_reference": "TEST-001",
            "golden_case_set_id": "test-gc-1"
        },
        "rate_tables": {
            "tax_bands": {
                # A banded table: the value is the LOWER BOUND of the band,
                # the max_value is its upper bound and the rate is the
                # percentage rate that applies inside it. The engine reads
                # it that way, and the golden case below is what it
                # produces.
                "description": "A single band at 10% for testing",
                "effective_from": "2026-01-01",
                "kind": "banded",
                "entries": [
                    {
                        "code": "FLAT",
                        "label": "Flat rate",
                        "value": 0,
                        "max_value": 1000000,
                        "rate": 10,
                        "unit": "currency_amount",
                        "notes": "10% on all income"
                    }
                ]
            },
            "social_insurance_employee": {
                "description": "Employee contributions",
                "effective_from": "2026-01-01",
                "values": {
                    "pension": { "value": 5.0, "unit": "percent", "label": "Pension", "notes": "" },
                    "health": { "value": 3.0, "unit": "percent", "label": "Health", "notes": "" }
                }
            },
            "social_insurance_employer": {
                "description": "Employer contributions",
                "effective_from": "2026-01-01",
                "values": {
                    "pension": { "value": 7.0, "unit": "percent", "label": "Pension", "notes": "" },
                    "health": { "value": 4.0, "unit": "percent", "label": "Health", "notes": "" }
                }
            }
        },
        "thresholds": {
            "weekly_max_hours": 40,
            "daily_min_rest_hours": 11,
            "max_consecutive_work_days": 5,
            "daily_overtime_threshold_hours": 8,
            "weekly_overtime_threshold_hours": 40,
            "overtime_premium_multiplier": 1.5,
            "overtime_daily_cap_hours": 2,
            "minimum_wage_amount": 10.00,
            "minimum_wage_unit": "per_hour"
        },
        "overtime": {
            "daily_threshold_hours": 8,
            "weekly_threshold_hours": 40,
            "premium_multiplier": 1.5,
            "daily_cap_hours": 2,
            "rules": [
                {
                    "rule_id": "OT_TEST",
                    "description": "Test overtime rule",
                    "severity": "block",
                    "applies_when": "Hours exceed 8/day"
                }
            ]
        },
        "leave_types": [
            {
                "code": "annual",
                "name": "Annual Leave",
                "entitlement_days": 20,
                "accrual": {
                    "frequency": "per_month",
                    "tenure_tiers": []
                },
                "carry_over_limit_days": 5,
                "expiry_month": 3,
                "encashable": False,
                "entitlement_source": "Test Act",
                "rule_ids": []
            }
        ],
        "working_time_limits": {
            "max_weekly_hours": 40,
            "min_daily_rest_hours": 11,
            "max_consecutive_days": 5,
            "max_night_work_hours": 8,
            "min_rest_between_shifts_hours": 11,
            "rules": []
        },
        "break_rules": [],
        "mandatory_payslip_fields": ["gross_pay", "net_pay"],
        "mandatory_payslip_notes": [],
        "pay_frequency_rules": {
            "allowed_frequencies": ["monthly"],
            "pay_day_rule": "Last day of month",
            "cut_off_days_before_pay_day": 2,
            "pay_date_rule_id": "PAY_MONTH_END"
        },
        "reporting_obligations": [],
        "public_holiday_rules": {
            "source": "Test calendar",
            "region_dependent": False,
            "holiday_count_by_year": { "2026": 10 }
        },
        "signing": {
            "algorithm": "ed25519",
            "key_id": "test-key",
            "signature": "VGVTVF9TSUdOQVRVUkVfUEhBU0VfUExBQ0VIT0xERVJfTk9UX1JFQUw=",
            "signed_at": "2026-10-21T00:00:00Z",
            "signed_by": "Test Signer"
        },
        "golden_cases": [
            {
                "case_id": "gc-basic",
                "description": "Basic monthly payslip",
                "input": {
                    "base_salary": "5000.00",
                    "pay_frequency": "monthly",
                    "hours_worked": 173,
                    "overtime_hours": 0,
                    "overtime_hourly_rate": 0,
                    "leave_days": 0,
                    "tax_withholding_override": None,
                    "benefit_deductions": "0",
                    "other_earnings": "0",
                    "other_deductions": "0"
                },
                "expected": {
                    # 500.00 of tax (5000.00 at the rate of the band),
                    # 250.00 of pension and 150.00 of health.
                    "gross": "5000.00",
                    "total_deductions": "900.00",
                    "net": "4100.00",
                    "pay_floor_check": "pass"
                }
            }
        ]
    }


class TestDeterminism:
    """Tests verifying deterministic calculation."""

    @pytest.fixture
    def pack(self):
        return load_rule_pack_from_dict(make_test_pack())

    def test_identical_inputs_produce_identical_outputs(self, pack):
        """Same inputs + same rule pack version = identical output hash."""
        inputs = {
            "base_salary": Decimal("5000.00"),
            "pay_frequency": "monthly",
            "hours_worked": Decimal("173"),
            "overtime_hours": Decimal("5"),
            "overtime_hourly_rate": Decimal("28.90"),
            "leave_days": Decimal("1"),
            "tax_withholding_override": None,
            "benefit_deductions": Decimal("100.00"),
            "other_earnings": Decimal("50.00"),
            "other_deductions": Decimal("25.00"),
        }

        # Run calculation 10 times
        results = []
        for _ in range(10):
            result = calculate_payslip_from_pack(pack=pack, **inputs)
            # Create a hash of the full result
            result_data = {
                "gross": str(result.gross),
                "net": str(result.net),
                "total_deductions": str(result.total_deductions),
                "pay_floor_check": result.pay_floor_check,
                "earnings": [(l.code, l.name, str(l.amount), l.line_type, l.rule_id, l.calculation) for l in result.earnings],
                "deductions": [(l.code, l.name, str(l.amount), l.line_type, l.rule_id, l.calculation) for l in result.deductions],
                "employer_contributions": [(l.code, l.name, str(l.amount), l.line_type, l.rule_id, l.calculation) for l in result.employer_contributions],
            }
            h = hashlib.sha256(json.dumps(result_data, sort_keys=True).encode()).hexdigest()
            results.append(h)

        # All hashes must be identical
        assert len(set(results)) == 1, f"Non-deterministic: got {len(set(results))} different hashes"

    def test_identical_trace_ids_for_identical_inputs(self, pack):
        """The trace_id should be identical for identical inputs."""
        inputs = {
            "base_salary": Decimal("4000.00"),
            "pay_frequency": "monthly",
            "hours_worked": Decimal("160"),
            "overtime_hours": Decimal("0"),
            "overtime_hourly_rate": Decimal("0"),
            "leave_days": Decimal("0"),
            "tax_withholding_override": None,
            "benefit_deductions": Decimal("0"),
            "other_earnings": Decimal("0"),
            "other_deductions": Decimal("0"),
        }

        trace_ids = set()
        for _ in range(5):
            result = calculate_payslip_from_pack(pack=pack, **inputs)
            trace_ids.add(result.trace_id)

        assert len(trace_ids) == 1, f"Trace IDs differ: {trace_ids}"

    def test_different_inputs_produce_different_outputs(self, pack):
        """Different inputs should produce different results (not a hash collision test)."""
        base_inputs = {
            "base_salary": Decimal("5000.00"),
            "pay_frequency": "monthly",
            "hours_worked": Decimal("173"),
            "overtime_hours": Decimal("0"),
            "overtime_hourly_rate": Decimal("0"),
            "leave_days": Decimal("0"),
            "tax_withholding_override": None,
            "benefit_deductions": Decimal("0"),
            "other_earnings": Decimal("0"),
            "other_deductions": Decimal("0"),
        }

        # Vary base salary
        r1 = calculate_payslip_from_pack(pack=pack, **base_inputs)
        r2 = calculate_payslip_from_pack(pack=pack, **{**base_inputs, "base_salary": Decimal("6000.00")})
        assert r1.gross != r2.gross
        assert r1.net != r2.net
        assert r1.trace_id != r2.trace_id

        # Vary overtime
        r3 = calculate_payslip_from_pack(pack=pack, **{**base_inputs, "overtime_hours": Decimal("5"), "overtime_hourly_rate": Decimal("28.90")})
        assert r1.gross != r3.gross
        assert r1.trace_id != r3.trace_id

        # Vary leave
        r4 = calculate_payslip_from_pack(pack=pack, **{**base_inputs, "leave_days": Decimal("2")})
        assert r1.net != r4.net
        assert r1.trace_id != r4.trace_id

    def test_golden_cases_pass(self, pack):
        """All golden cases in the pack must pass."""
        results = run_golden_cases(pack)
        for case_id, passed, msg in results:
            assert passed, f"Golden case {case_id} failed: {msg}"

    def test_golden_case_determinism(self, pack):
        """Running the same golden case multiple times produces identical results."""
        results = run_golden_cases(pack)
        for case_id, passed, msg in results:
            if not passed:
                continue
            # Re-run the same case 5 times
            gc = pack.get_golden_case(case_id)
            inputs = gc.inputs
            trace_ids = set()
            for _ in range(5):
                result = calculate_payslip_from_pack(
                    pack=pack,
                    base_salary=Decimal(inputs.get("base_salary", "0")),
                    pay_frequency=inputs.get("pay_frequency", "monthly"),
                    hours_worked=Decimal(inputs.get("hours_worked", "0")),
                    overtime_hours=Decimal(inputs.get("overtime_hours", "0")),
                    overtime_hourly_rate=Decimal(inputs.get("overtime_hourly_rate", "0")),
                    leave_days=Decimal(inputs.get("leave_days", "0")),
                    tax_withholding_override=Decimal(inputs["tax_withholding_override"]) if inputs.get("tax_withholding_override") else None,
                    benefit_deductions=Decimal(inputs.get("benefit_deductions", "0")),
                    other_earnings=Decimal(inputs.get("other_earnings", "0")),
                    other_deductions=Decimal(inputs.get("other_deductions", "0")),
                )
                trace_ids.add(result.trace_id)
            assert len(trace_ids) == 1, f"Golden case {case_id} non-deterministic: {trace_ids}"


class TestMoneyArithmetic:
    """Tests for the decimal money helper."""

    def test_money_quantizes_to_cents(self):
        assert money("10.001") == Decimal("10.00")
        assert money("10.005") == Decimal("10.01")  # ROUND_HALF_UP
        assert money("10.004") == Decimal("10.00")
        assert money("10.006") == Decimal("10.01")

    def test_money_handles_none(self):
        assert money(None) == Decimal("0.00")

    def test_money_handles_float_without_drift(self):
        # Float 0.1 is not exact in binary; money() should handle it
        assert money(0.1) == Decimal("0.10")
        assert money(0.1 + 0.2) == Decimal("0.30")  # Would be 0.30000000000000004 as float

    def test_to_decimal_preserves_precision(self):
        assert to_decimal("123.456") == Decimal("123.456")
        assert to_decimal(Decimal("123.456")) == Decimal("123.456")
        assert to_decimal(100) == Decimal("100")
        assert to_decimal(None) == Decimal("0")

    def test_sum_money_rounds_final_result(self):
        # 0.005 + 0.005 = 0.01, not 0.01 then rounded
        assert sum_money("0.005", "0.005") == Decimal("0.01")

    def test_prorate_rounds_result(self):
        # Annual salary 50000, worked 15 of 30 days = 25000
        assert prorate("50000", "15", "30") == Decimal("25000.00")
        # Uneven division
        assert prorate("1000", "1", "3") == Decimal("333.33")

    def test_apply_rate_percentage(self):
        assert apply_rate("1000", "10") == Decimal("100.00")  # 10% of 1000
        assert apply_rate("333.33", "5.5") == Decimal("18.33")  # 5.5% of 333.33


class TestRulePackLoading:
    """Tests for rule pack loading and validation."""

    def test_load_valid_pack(self):
        pack = load_rule_pack_from_dict(make_test_pack())
        assert pack.meta.pack_id == "test-determinism"
        assert pack.meta.status == "verified"
        assert pack.is_verified()

    def test_pack_not_verified_cannot_calculate(self):
        """A non-verified pack must raise when used for calculation."""
        data = make_test_pack()
        data["status"] = "draft"
        data["verification"] = None
        pack = load_rule_pack_from_dict(data)

        with pytest.raises(ValueError, match="not verified"):
            calculate_payslip_from_pack(
                pack=pack,
                base_salary=Decimal("5000"),
                pay_frequency="monthly",
            )

    def test_pack_effective_date_resolution(self):
        """Pack should only be effective within its date range."""
        data = make_test_pack()
        data["effective_from"] = "2026-06-01"
        data["effective_to"] = "2026-12-31"
        pack = load_rule_pack_from_dict(data)

        from datetime import date
        assert not pack.is_effective_on(date(2026, 5, 31))
        assert pack.is_effective_on(date(2026, 6, 1))
        assert pack.is_effective_on(date(2026, 12, 31))
        assert not pack.is_effective_on(date(2027, 1, 1))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])