"""Rule pack loader and validation.

A rule pack is a versioned, signed, jurisdiction-specific set of statutory rules.
Only packs with status `verified` may drive production payroll calculations.

This module handles:
- Loading a rule pack from JSON
- Validating against the JSON Schema (contracts/rules/rule-pack.schema.json)
- Effective-date resolution (selecting the version in force on a given date)
- Providing typed access to rate tables, thresholds, and rules
"""
from __future__ import annotations

import json
import hashlib
import os
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import jsonschema
from jsonschema import Draft202012Validator

from app.rules.money import money, to_decimal

# Path to the JSON Schema (relative to repo root)
# Inside the Docker image parents[3]/contracts resolves to /contracts (missing)
# because the image is built from ./backend with WORKDIR /app. Try multiple
# candidates and pick the first that exists.
_SCHEMA_CANDIDATES: list[Path] = [
    Path(__file__).resolve().parents[3] / "contracts" / "rules" / "rule-pack.schema.json",
    Path("/app/contracts/rules/rule-pack.schema.json"),
    Path(__file__).resolve().parents[2] / "contracts" / "rules" / "rule-pack.schema.json",
]


def _resolve_schema_path() -> Path:
    for cand in _SCHEMA_CANDIDATES:
        if cand.is_file():
            return cand
    # Fallback to the primary candidate so the error message points at the
    # expected location even when nothing exists.
    return _SCHEMA_CANDIDATES[0]


SCHEMA_PATH = _resolve_schema_path()


@dataclass(frozen=True)
class RulePackMeta:
    pack_id: str
    name: str
    jurisdiction_country: str
    jurisdiction_region: Optional[str]
    jurisdiction_display_name: str
    version: str
    status: str  # draft | pending_verification | verified | superseded
    effective_from: date
    effective_to: Optional[date]
    tz: str
    source_document_title: str
    source_publisher: str
    source_document_reference: str
    source_url: Optional[str]
    source_retrieved_on: date
    verification_verified_by_name: Optional[str]
    verification_verified_by_role: Optional[str]
    verification_verified_on: Optional[date]
    verification_source_document_reference: Optional[str]
    verification_golden_case_set_id: Optional[str]


@dataclass(frozen=True)
class RateTableEntry:
    """One row of a banded rate table.

    ``value`` is the **lower bound** of the band and ``max_value`` its upper
    bound, the way the schema reads them. ``rate`` is the percentage rate
    that applies inside the band, and it is ``None`` when the row states
    none: a band without a rate cannot be calculated, and the engine refuses
    such a pack rather than guess one.
    """

    code: str
    label: str
    value: Decimal
    max_value: Optional[Decimal]
    unit: str
    notes: Optional[str]
    rate: Optional[Decimal] = None


@dataclass(frozen=True)
class RateTableValue:
    value: Decimal
    unit: str
    label: Optional[str]
    notes: Optional[str]


@dataclass(frozen=True)
class RateTable:
    name: str
    description: str
    effective_from: date
    entries: tuple[RateTableEntry, ...]  # for banded tables
    values: dict[str, RateTableValue]    # for keyed maps
    # Declared scope. Only an explicit True puts the table in scope; the
    # engine emits nothing from a table that is not in scope.
    in_scope: bool = False


@dataclass(frozen=True)
class Thresholds:
    weekly_max_hours: Optional[Decimal]
    daily_min_rest_hours: Optional[Decimal]
    max_consecutive_work_days: Optional[int]
    daily_overtime_threshold_hours: Optional[Decimal]
    weekly_overtime_threshold_hours: Optional[Decimal]
    overtime_premium_multiplier: Optional[Decimal]
    overtime_daily_cap_hours: Optional[Decimal]
    minimum_wage_amount: Optional[Decimal]
    minimum_wage_unit: Optional[str]


@dataclass(frozen=True)
class OvertimeRule:
    rule_id: str
    description: str
    severity: str  # block | flag
    applies_when: str


@dataclass(frozen=True)
class OvertimeConfig:
    daily_threshold_hours: Optional[Decimal]
    weekly_threshold_hours: Optional[Decimal]
    premium_multiplier: Optional[Decimal]
    daily_cap_hours: Optional[Decimal]
    rules: tuple[OvertimeRule, ...]


@dataclass(frozen=True)
class LeaveType:
    code: str
    name: str
    entitlement_days: Decimal
    accrual_frequency: str
    tenure_tiers: tuple[tuple[int, Decimal], ...]  # (after_years, days)
    carry_over_limit_days: Decimal
    expiry_month: int
    encashable: bool
    entitlement_source: str
    rule_ids: tuple[str, ...]


@dataclass(frozen=True)
class WorkingTimeLimits:
    max_weekly_hours: Optional[Decimal]
    min_daily_rest_hours: Optional[Decimal]
    max_consecutive_days: Optional[int]
    max_night_work_hours: Optional[Decimal]
    min_rest_between_shifts_hours: Optional[Decimal]
    rules: tuple[OvertimeRule, ...]  # reusing same structure


@dataclass(frozen=True)
class BreakRule:
    after_hours: Optional[Decimal]
    duration_minutes: Optional[int]
    paid: bool
    rule_id: str
    description: str


@dataclass(frozen=True)
class ReportingObligation:
    code: str
    name: str
    frequency: str
    deadline_rule: str
    authority: str
    description: str
    rule_ids: tuple[str, ...]


@dataclass(frozen=True)
class PublicHolidayRules:
    source: str
    region_dependent: bool
    holiday_count_by_year: dict[int, int]


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    description: str
    rule_pack_version: str
    inputs: dict[str, Any]
    expected: dict[str, Any]
    notes: Optional[str]


@dataclass(frozen=True)
class RulePack:
    meta: RulePackMeta
    rate_tables: dict[str, RateTable]
    thresholds: Thresholds
    overtime: OvertimeConfig
    leave_types: tuple[LeaveType, ...]
    working_time_limits: WorkingTimeLimits
    break_rules: tuple[BreakRule, ...]
    mandatory_payslip_fields: tuple[str, ...]
    mandatory_payslip_notes: tuple[str, ...]
    pay_frequency_rules: dict[str, Any]
    reporting_obligations: tuple[ReportingObligation, ...]
    public_holiday_rules: PublicHolidayRules
    golden_cases: tuple[GoldenCase, ...]
    # Canonical content hash (sha256 over sorted-keys JSON of the pack dict
    # the pack was loaded from). It names the exact bytes the engine read, so
    # a trace can be tied back to them without carrying any value. Synthetic
    # in-memory packs hash their dict the same way.
    content_sha: str = ""

    def is_verified(self) -> bool:
        return self.meta.status == "verified"

    def is_effective_on(self, d: date) -> bool:
        if d < self.meta.effective_from:
            return False
        if self.meta.effective_to is not None and d > self.meta.effective_to:
            return False
        return True

    def get_rate_table(self, name: str) -> Optional[RateTable]:
        return self.rate_tables.get(name)

    def get_rate_value(self, table_name: str, code: str) -> Optional[Decimal]:
        table = self.rate_tables.get(table_name)
        if not table:
            return None
        if code in table.values:
            return table.values[code].value
        for entry in table.entries:
            if entry.code == code:
                return entry.value
        return None

    def get_leave_type(self, code: str) -> Optional[LeaveType]:
        for lt in self.leave_types:
            if lt.code == code:
                return lt
        return None

    def get_golden_case(self, case_id: str) -> Optional[GoldenCase]:
        for gc in self.golden_cases:
            if gc.case_id == case_id:
                return gc
        return None


class RulePackLoadError(Exception):
    """Raised when a rule pack fails to load or validate."""
    pass


def load_schema() -> dict:
    """Load the JSON Schema for rule packs."""
    # Re-resolve at call time so a container that baked the schema to
    # /app/contracts still finds it even if SCHEMA_PATH was computed before
    # the file existed, and so tests that point at different mounts work.
    path = SCHEMA_PATH
    if not path.is_file():
        path = _resolve_schema_path()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_against_schema(data: dict) -> list[str]:
    """Validate a rule pack dict against the JSON Schema.

    Returns a list of error messages (empty if valid).
    """
    schema = load_schema()
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(data))
    return [f"{err.json_path}: {err.message}" for err in errors]


def band_rate_problems(data: dict) -> list[str]:
    """The banded rate tables whose bands leave the rate out.

    The schema refuses such a pack: a table that declares itself banded has
    to state, on every one of its bands, the rate that applies inside that
    band. This reads the same rule and says **which** table and **which**
    band, because a schema error can only point at a position in a file.

    A problem names the table and the band and never carries a value from
    the pack. A rate, a bound or a threshold is the pack's business and must
    not leak through an error message: the reader is told what is missing,
    never what the pack holds.
    """
    problems: list[str] = []
    if not isinstance(data, dict):
        return problems
    tables = data.get("rate_tables")
    if not isinstance(tables, dict):
        return problems

    for table_name, table in tables.items():
        if not isinstance(table, dict):
            continue
        if table.get("kind") != "banded":
            continue
        entries = table.get("entries")
        if not isinstance(entries, list):
            continue
        missing: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            # `is None`, never a truth test: a band taxed at nothing states
            # the rate 0, and 0 is a rate like any other.
            if entry.get("rate") is None:
                code = entry.get("code")
                missing.append(code if isinstance(code, str) and code else "unnamed")
        if missing:
            names = ", ".join(f"'{code}'" for code in missing)
            problems.append(
                f"the band table '{table_name}' states no rate for the "
                f"band{'s' if len(missing) > 1 else ''} {names}: a banded "
                "table states the rate that applies inside every one of its "
                "bands"
            )
    return problems


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def parse_optional_date(s: Optional[str]) -> Optional[date]:
    if s is None:
        return None
    return parse_date(s)


def load_rule_pack_from_dict(data: dict) -> RulePack:
    """Load and parse a rule pack from an already-parsed JSON dict.

    Does NOT validate against schema — call validate_against_schema first.
    The ``content_sha`` is the sha256 of the canonical (sorted-keys, compact)
    JSON serialisation of the dict, so the trace names the exact content the
    engine read. Decimal values are rendered with ``str`` because the default
    encoder cannot serialise them; the hash names the structure, not a float.
    """
    content_sha = hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    # Meta
    jur = data["jurisdiction"]
    src = data["source"]
    ver = data.get("verification")

    meta = RulePackMeta(
        pack_id=data["pack_id"],
        name=data["name"],
        jurisdiction_country=jur["country"],
        jurisdiction_region=jur.get("region"),
        jurisdiction_display_name=jur["display_name"],
        version=data["version"],
        status=data["status"],
        effective_from=parse_date(data["effective_from"]),
        effective_to=parse_optional_date(data.get("effective_to")),
        tz=data["tz"],
        source_document_title=src["document_title"],
        source_publisher=src["publisher"],
        source_document_reference=src["document_reference"],
        source_url=src.get("url"),
        source_retrieved_on=parse_date(src["retrieved_on"]),
        verification_verified_by_name=ver.get("verified_by_name") if ver else None,
        verification_verified_by_role=ver.get("verified_by_role") if ver else None,
        verification_verified_on=parse_optional_date(ver.get("verified_on")) if ver else None,
        verification_source_document_reference=ver.get("source_document_reference") if ver else None,
        verification_golden_case_set_id=ver.get("golden_case_set_id") if ver else None,
    )

    # Rate tables
    rate_tables = {}
    for name, rt in data.get("rate_tables", {}).items():
        entries = []
        for e in rt.get("entries", []):
            entries.append(RateTableEntry(
                code=e["code"],
                label=e["label"],
                value=to_decimal(e["value"]),
                max_value=to_decimal(e["max_value"]) if e.get("max_value") is not None else None,
                unit=e["unit"],
                notes=e.get("notes"),
                rate=to_decimal(e["rate"]) if e.get("rate") is not None else None,
            ))
        values = {}
        for k, v in rt.get("values", {}).items():
            values[k] = RateTableValue(
                value=to_decimal(v["value"]),
                unit=v["unit"],
                label=v.get("label"),
                notes=v.get("notes"),
            )
        rate_tables[name] = RateTable(
            name=name,
            description=rt["description"],
            effective_from=parse_date(rt["effective_from"]),
            entries=tuple(entries),
            values=values,
            in_scope=rt.get("in_scope") is True,
        )

    # Thresholds
    th = data["thresholds"]
    thresholds = Thresholds(
        weekly_max_hours=to_decimal(th["weekly_max_hours"]) if th.get("weekly_max_hours") is not None else None,
        daily_min_rest_hours=to_decimal(th["daily_min_rest_hours"]) if th.get("daily_min_rest_hours") is not None else None,
        max_consecutive_work_days=th.get("max_consecutive_work_days"),
        daily_overtime_threshold_hours=to_decimal(th["daily_overtime_threshold_hours"]) if th.get("daily_overtime_threshold_hours") is not None else None,
        weekly_overtime_threshold_hours=to_decimal(th["weekly_overtime_threshold_hours"]) if th.get("weekly_overtime_threshold_hours") is not None else None,
        overtime_premium_multiplier=to_decimal(th["overtime_premium_multiplier"]) if th.get("overtime_premium_multiplier") is not None else None,
        overtime_daily_cap_hours=to_decimal(th["overtime_daily_cap_hours"]) if th.get("overtime_daily_cap_hours") is not None else None,
        minimum_wage_amount=to_decimal(th["minimum_wage_amount"]) if th.get("minimum_wage_amount") is not None else None,
        minimum_wage_unit=th.get("minimum_wage_unit"),
    )

    # Overtime
    ot = data["overtime"]
    ot_rules = tuple(OvertimeRule(
        rule_id=r["rule_id"],
        description=r["description"],
        severity=r["severity"],
        applies_when=r["applies_when"],
    ) for r in ot["rules"])
    overtime = OvertimeConfig(
        daily_threshold_hours=to_decimal(ot["daily_threshold_hours"]) if ot.get("daily_threshold_hours") is not None else None,
        weekly_threshold_hours=to_decimal(ot["weekly_threshold_hours"]) if ot.get("weekly_threshold_hours") is not None else None,
        premium_multiplier=to_decimal(ot["premium_multiplier"]) if ot.get("premium_multiplier") is not None else None,
        daily_cap_hours=to_decimal(ot["daily_cap_hours"]) if ot.get("daily_cap_hours") is not None else None,
        rules=ot_rules,
    )

    # Leave types
    leave_types = []
    for lt in data["leave_types"]:
        accrual = lt["accrual"]
        tenure_tiers = tuple((t["after_years"], to_decimal(t["days"])) for t in accrual.get("tenure_tiers", []))
        leave_types.append(LeaveType(
            code=lt["code"],
            name=lt["name"],
            entitlement_days=to_decimal(lt["entitlement_days"]),
            accrual_frequency=accrual["frequency"],
            tenure_tiers=tenure_tiers,
            carry_over_limit_days=to_decimal(lt["carry_over_limit_days"]),
            expiry_month=lt["expiry_month"],
            encashable=lt["encashable"],
            entitlement_source=lt["entitlement_source"],
            rule_ids=tuple(lt.get("rule_ids", [])),
        ))

    # Working time limits
    wtl = data["working_time_limits"]
    wtl_rules = tuple(OvertimeRule(
        rule_id=r["rule_id"],
        description=r["description"],
        severity=r["severity"],
        applies_when=r["applies_when"],
    ) for r in wtl["rules"])
    working_time_limits = WorkingTimeLimits(
        max_weekly_hours=to_decimal(wtl["max_weekly_hours"]) if wtl.get("max_weekly_hours") is not None else None,
        min_daily_rest_hours=to_decimal(wtl["min_daily_rest_hours"]) if wtl.get("min_daily_rest_hours") is not None else None,
        max_consecutive_days=wtl.get("max_consecutive_days"),
        max_night_work_hours=to_decimal(wtl["max_night_work_hours"]) if wtl.get("max_night_work_hours") is not None else None,
        min_rest_between_shifts_hours=to_decimal(wtl["min_rest_between_shifts_hours"]) if wtl.get("min_rest_between_shifts_hours") is not None else None,
        rules=wtl_rules,
    )

    # Break rules
    break_rules = tuple(BreakRule(
        after_hours=to_decimal(br["after_hours"]) if br.get("after_hours") is not None else None,
        duration_minutes=br.get("duration_minutes"),
        paid=br["paid"],
        rule_id=br["rule_id"],
        description=br["description"],
    ) for br in data.get("break_rules", []))

    # Mandatory payslip fields/notes
    mandatory_payslip_fields = tuple(data.get("mandatory_payslip_fields", []))
    mandatory_payslip_notes = tuple(data.get("mandatory_payslip_notes", []))

    # Pay frequency rules
    pay_frequency_rules = data.get("pay_frequency_rules", {})

    # Reporting obligations
    reporting_obligations = tuple(ReportingObligation(
        code=ro["report_id"],
        name=ro["name"],
        frequency=ro["frequency"],
        deadline_rule=str(ro.get("due_within_days", 0)) + " days",
        authority=ro["authority"],
        description=ro["description"],
        rule_ids=tuple(),
    ) for ro in data.get("reporting_obligations", []))

    # Public holiday rules
    phr = data["public_holiday_rules"]
    public_holiday_rules = PublicHolidayRules(
        source=phr["source"],
        region_dependent=phr["region_dependent"],
        holiday_count_by_year={int(k): v for k, v in phr["holiday_count_by_year"].items()},
    )

    # Golden cases
    golden_cases = tuple(GoldenCase(
        case_id=gc["case_id"],
        description=gc["description"],
        rule_pack_version=data.get("version", "unknown"),
        inputs=gc["input"],
        expected=gc["expected"],
        notes=None,
    ) for gc in data.get("golden_cases", []))

    return RulePack(
        meta=meta,
        rate_tables=rate_tables,
        thresholds=thresholds,
        overtime=overtime,
        leave_types=tuple(leave_types),
        working_time_limits=working_time_limits,
        break_rules=break_rules,
        mandatory_payslip_fields=mandatory_payslip_fields,
        mandatory_payslip_notes=mandatory_payslip_notes,
        pay_frequency_rules=pay_frequency_rules,
        reporting_obligations=reporting_obligations,
        public_holiday_rules=public_holiday_rules,
        golden_cases=golden_cases,
        content_sha=content_sha,
    )


def load_rule_pack(path: str | Path) -> RulePack:
    """Load a rule pack from a JSON file, validating against the schema.

    A pack that breaks the band rule is refused **here**, when it is loaded,
    and the refusal names the table and the band. A pack that cannot be
    calculated is caught while it is being installed, not when a pay run
    needs the figure, and the first line of the error is the one an operator
    reads: it names the table and the band and carries no value from the
    pack.
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    problems = band_rate_problems(data)
    if problems:
        raise RulePackLoadError("\n".join(problems))

    errors = validate_against_schema(data)
    if errors:
        raise RulePackLoadError(f"Schema validation failed:\n" + "\n".join(errors))

    return load_rule_pack_from_dict(data)


def load_rule_pack_for_date(pack_dir: str | Path, jurisdiction: str, calc_date: date) -> RulePack:
    """Load the rule pack for a jurisdiction that is effective on calc_date.

    pack_dir is a directory containing rule pack JSON files.
    The function selects the pack with matching jurisdiction and effective date range.
    If multiple packs match, the one with the latest effective_from is used.
    Only packs with status 'verified' are considered for production use.
    """
    pack_dir = Path(pack_dir)
    candidates = []
    for file in pack_dir.glob("*.json"):
        try:
            pack = load_rule_pack(file)
            if pack.meta.jurisdiction_country == jurisdiction and pack.is_effective_on(calc_date):
                if pack.is_verified():
                    candidates.append(pack)
        except RulePackLoadError:
            # Skip invalid packs
            continue

    if not candidates:
        raise RulePackLoadError(
            f"No verified rule pack found for jurisdiction '{jurisdiction}' effective on {calc_date}"
        )

    # Pick the one with the latest effective_from (most recent version)
    return max(candidates, key=lambda p: p.meta.effective_from)