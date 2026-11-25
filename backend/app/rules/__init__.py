"""Payroll Rules Engine Package.

This package contains:
- money.py: Decimal arithmetic helpers (single source of truth for money)
- loader.py: Rule pack loading, validation, and effective-date resolution
- resolver.py: Which pack is in force for a jurisdiction and a date, and why not
- engine.py: Pure, deterministic payroll calculation driven by rule packs
- reconciliation.py: Reconciliation report structure and verification
- test_determinism.py: Determinism and golden-case tests
- test_reconciliation.py: Reconciliation verification tests
"""
from app.rules.money import (
    money,
    money_raw,
    to_decimal,
    apply_rate,
    prorate,
    sum_money,
    rate_percentage,
    round_half_up,
    CENTS,
    ZERO,
)

from app.rules.loader import (
    RulePack,
    RulePackMeta,
    RateTable,
    RateTableEntry,
    RateTableValue,
    Thresholds,
    OvertimeConfig,
    OvertimeRule,
    LeaveType,
    WorkingTimeLimits,
    BreakRule,
    ReportingObligation,
    PublicHolidayRules,
    GoldenCase,
    load_rule_pack,
    load_rule_pack_from_dict,
    load_rule_pack_for_date,
    validate_against_schema,
    RulePackLoadError,
)

from app.rules.resolver import (
    PackLoadFailure,
    RulePackResolution,
    load_packs,
    pack_directory,
    resolve_rule_pack,
    PACK_DIR_ENV,
    DEFAULT_PACK_DIR,
    STATUS_ABSENT,
    STATUS_DRAFT,
    STATUS_PENDING_VERIFICATION,
    STATUS_SUPERSEDED,
    STATUS_VERIFIED,
)

from app.rules.engine import (
    PayLine,
    PayslipResult,
    CalculationContext,
    RulePackNotReadable,
    calculate_payslip_from_pack,
    rate_table_problems,
    run_golden_cases,
    TAX_TABLE,
    EMPLOYEE_CONTRIBUTION_TABLE,
    EMPLOYER_CONTRIBUTION_TABLE,
)

from app.rules.reconciliation import (
    ReconciliationLine,
    PayslipReconciliation,
    PayRunReconciliation,
    build_reconciliation,
    verify_reconciliation_file,
    export_reconciliation_csv,
    export_reconciliation_summary_csv,
)

__all__ = [
    # money
    "money",
    "money_raw",
    "to_decimal",
    "apply_rate",
    "prorate",
    "sum_money",
    "rate_percentage",
    "round_half_up",
    "CENTS",
    "ZERO",
    # loader
    "RulePack",
    "RulePackMeta",
    "RateTable",
    "RateTableEntry",
    "RateTableValue",
    "Thresholds",
    "OvertimeConfig",
    "OvertimeRule",
    "LeaveType",
    "WorkingTimeLimits",
    "BreakRule",
    "ReportingObligation",
    "PublicHolidayRules",
    "GoldenCase",
    "load_rule_pack",
    "load_rule_pack_from_dict",
    "load_rule_pack_for_date",
    "validate_against_schema",
    "RulePackLoadError",
    # resolver
    "PackLoadFailure",
    "RulePackResolution",
    "load_packs",
    "pack_directory",
    "resolve_rule_pack",
    "PACK_DIR_ENV",
    "DEFAULT_PACK_DIR",
    "STATUS_ABSENT",
    "STATUS_DRAFT",
    "STATUS_PENDING_VERIFICATION",
    "STATUS_SUPERSEDED",
    "STATUS_VERIFIED",
    # engine
    "PayLine",
    "PayslipResult",
    "CalculationContext",
    "RulePackNotReadable",
    "calculate_payslip_from_pack",
    "rate_table_problems",
    "run_golden_cases",
    "TAX_TABLE",
    "EMPLOYEE_CONTRIBUTION_TABLE",
    "EMPLOYER_CONTRIBUTION_TABLE",
    # reconciliation
    "ReconciliationLine",
    "PayslipReconciliation",
    "PayRunReconciliation",
    "build_reconciliation",
    "verify_reconciliation_file",
    "export_reconciliation_csv",
    "export_reconciliation_summary_csv",
]