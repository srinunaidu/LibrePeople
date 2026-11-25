# Rule Packs — Authoring and Verification Guide

**Version:** 0.1 (Draft)
**Last Updated:** 2026-10-21
**Owner:** Payroll & Rules Agent

---

## 1. What Is a Rule Pack?

A **rule pack** is a versioned, signed, jurisdiction-specific JSON document that contains **all statutory rules** required for payroll calculation in a given jurisdiction. It is the **only** artifact in Karmathy that may contain statutory values.

> **No tax rate, contribution rate, threshold, or legal wording lives in code.** All statutory numbers are in rule packs.

---

## 2. Pack Lifecycle

```
┌─────────┐     ┌──────────────────┐     ┌───────────┐     ┌─────────────┐
│  draft  │────►│pending_verification│────►│ verified  │────►│ superseded  │
└─────────┘     └──────────────────┘     └───────────┘     └─────────────┘
   │                    │                    │                   │
Editable          Frozen;             Production            Historical;
unusable          awaiting            usable;               has
                  review                signed +              effective_to
                                         golden cases
```

### Status Rules (Schema-Enforced)

| Status | Can Calculate? | Requirements |
|--------|----------------|--------------|
| `draft` | ❌ | — |
| `pending_verification` | ❌ | Complete `source` block; frozen (no edits) |
| `verified` | ✅ | `source` + `verification` block + ≥1 `golden_case` + valid signature |
| `superseded` | ❌ (historical only) | `effective_to` date required |

---

## 3. Pack Structure (Schema: `contracts/rules/rule-pack.schema.json`)

### 3.1 Required Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `pack_id` | string | Stable slug (e.g., `in-central`, `de-basic`) |
| `name` | string | Display name |
| `jurisdiction` | object | `country` (ISO 3166-1), `region` (optional, ISO 3166-2), `display_name` |
| `version` | string | Semantic version (e.g., `1.0.0`, `2.1.0-rc.1`) |
| `status` | enum | `draft` \| `pending_verification` \| `verified` \| `superseded` |
| `effective_from` | date | First date pack applies (inclusive) |
| `effective_to` | date/null | Last date pack applies (inclusive); null = no end |
| `tz` | string | IANA time zone (e.g., `Asia/Kolkata`) |
| `source` | object | **Required** — legal document citation |
| `verification` | object/null | **Required for `verified`** — human sign-off |
| `rate_tables` | object | Statutory rate tables |
| `thresholds` | object | Statutory numeric thresholds |
| `overtime` | object | Overtime rules |
| `leave_types` | array | Statutory leave types |
| `working_time_limits` | object | Working time limits |
| `break_rules` | array | Break entitlements |
| `mandatory_payslip_fields` | array | Required payslip field names |
| `mandatory_payslip_notes` | array | Required literal notes on payslip |
| `pay_frequency_rules` | object | Allowed frequencies, pay date rule |
| `reporting_obligations` | array | Statutory filing requirements |
| `public_holiday_rules` | object | Holiday calendar source and counts |
| `signing` | object | Ed25519 signature over canonical JSON |
| `golden_cases` | array | Worked examples (inputs → expected outputs) |

---

## 4. Authoring a Pack

### 4.1 Start from the Demo Pack

```bash
cp rule_packs/demo-synthetic-draft.json rule_packs/in-central-draft.json
# Edit with real values and sources
```

### 4.2 Source Block (Required for All Packs)

```json
"source": {
  "document_title": "Income Tax Act, 1961",
  "publisher": "Ministry of Finance, Government of India",
  "document_reference": "Section 192, Finance Act 2024, Notification No. 15/2024",
  "url": "https://www.incometax.gov.in/...",
  "retrieved_on": "2026-10-15",
  "notes": "Applies to FY 2025-26. Surcharge rates per Section 2(1A)."
}
```

**Every statutory value must be traceable to a source document.**

### 4.3 Rate Tables

Two forms supported (exactly one per table):

**Banded (progressive) — e.g., tax bands.**

A table written as a list of rows says what shape those rows have, in
`kind`: `"banded"` for a progressive table whose rows are bands, or
`"schedule"` for a table whose rows are scheduled values that carry no rate
of their own.

A band states three numbers: its `value` is the **lower bound** of the band,
its `max_value` is the upper bound, and its `rate` is the percentage rate
that applies inside the band. The engine divides the taxable amount between
the bands by their bounds and taxes each part at the rate of the band it
falls in.

> The numbers below are **synthetic**. A real pack states the values of its
> own jurisdiction, with a citation, and a named human verifies them.

```json
"tax_bands": {
  "description": "Progressive tax on the taxable amount of the period",
  "effective_from": "2026-04-01",
  "kind": "banded",
  "entries": [
    { "code": "BAND_0", "label": "First band", "value": 0, "max_value": 100000, "rate": 0, "unit": "currency_amount", "notes": "cite the provision" },
    { "code": "BAND_1", "label": "Second band", "value": 100000, "max_value": 300000, "rate": 5, "unit": "currency_amount", "notes": "cite the provision" },
    { "code": "BAND_2", "label": "Top band", "value": 300000, "rate": 20, "unit": "currency_amount", "notes": "cite the provision" }
  ]
}
```

**Every band of a banded table states its rate.** The schema refuses a
banded table whose bands leave the rate out, and the loader refuses the pack
**when it is loaded**, naming the table and the band — not when a pay run
needs the figure. The refusal never carries a value from the pack: it says
what is missing, never what the pack holds. A wrong pay figure is worse
than a refusal.

**A schedule table's rows carry no rate.** `kind: "schedule"` says the rows
are scheduled values — a value and a unit each — so the schema asks for no
rate:

```json
"allowance_schedule": {
  "description": "Scheduled allowances, by period",
  "effective_from": "2026-04-01",
  "kind": "schedule",
  "entries": [
    { "code": "ALLOWANCE_1", "label": "First allowance", "value": 100, "unit": "currency_amount", "notes": "cite the provision" }
  ]
}
```

**Keyed map (flat lookups) — e.g., social insurance rates.**

Every value is a **percentage rate** that applies to the whole base. There
are no bounds and no bands.

```json
"social_insurance_employee": {
  "description": "Employee social insurance contributions",
  "effective_from": "2026-04-01",
  "values": {
    "employee_contribution": { "value": 1.0, "unit": "percent", "label": "Employee contribution", "notes": "cite the provision" },
    "employee_contribution_2": { "value": 0.5, "unit": "percent", "label": "Second employee contribution", "notes": "cite the provision" }
  }
}
```

The two forms are never read as one another. The tax table has to be a
**banded** table, because the engine has to know which rate applies to which
part of the taxable amount; a contribution table has to be a **flat map**,
because every value in it applies to the whole base. A table written in the
wrong form is refused, not reinterpreted.

### 4.4 Thresholds (All Required, Null = Jurisdiction Sets No Limit)

```json
"thresholds": {
  "weekly_max_hours": 48,
  "daily_min_rest_hours": 11,
  "max_consecutive_work_days": 6,
  "daily_overtime_threshold_hours": 9,
  "weekly_overtime_threshold_hours": 48,
  "overtime_premium_multiplier": 2.0,
  "overtime_daily_cap_hours": 4,
  "minimum_wage_amount": 178,
  "minimum_wage_unit": "per_day"
}
```

### 4.5 Leave Types

```json
"leave_types": [
  {
    "code": "annual",
    "name": "Annual Leave (Earned Leave)",
    "entitlement_days": 15,
    "accrual": { "frequency": "per_month", "tenure_tiers": [] },
    "carry_over_limit_days": 30,
    "expiry_month": 3,
    "encashable": true,
    "entitlement_source": "Factories Act 1948, Section 79; Shops & Establishments Act (State)",
    "rule_ids": ["LV_CARRYOVER"]
  },
  {
    "code": "sick",
    "name": "Sick Leave",
    "entitlement_days": 12,
    "accrual": { "frequency": "front_loaded", "tenure_tiers": [] },
    "carry_over_limit_days": 0,
    "expiry_month": 12,
    "encashable": false,
    "entitlement_source": "State Shops & Establishments Act",
    "rule_ids": []
  }
]
```

### 4.6 Golden Cases (Required for Verified)

```json
"golden_cases": [
  {
    "case_id": "GC_IN_MONTHLY_BASIC",
    "description": "Monthly basic payslip: ₹50,000 base, no OT, standard deductions",
    "rule_pack_version": "1.0.0",
    "inputs": {
      "base_salary": "50000.00",
      "pay_frequency": "monthly",
      "hours_worked": "173",
      "overtime_hours": "0",
      "overtime_hourly_rate": "0",
      "leave_days": "0",
      "tax_withholding_override": null,
      "benefit_deductions": "1800.00",
      "other_earnings": "0",
      "other_deductions": "0"
    },
    "expected": {
      "earnings": [
        { "code": "BASIC", "name": "Basic Salary", "amount": "50000.00", "type": "earning" }
      ],
      "deductions": [
        { "code": "TAX", "name": "TDS", "amount": "4166.00", "type": "deduction" },
        { "code": "EPF_EE", "name": "EPF (Employee)", "amount": "6000.00", "type": "deduction" },
        { "code": "ESI_EE", "name": "ESI (Employee)", "amount": "375.00", "type": "deduction" },
        { "code": "BENEFITS", "name": "Benefit Deductions", "amount": "1800.00", "type": "deduction" }
      ],
      "employer_contributions": [
        { "code": "EPF_ER", "name": "EPF (Employer)", "amount": "6000.00" },
        { "code": "ESI_ER", "name": "ESI (Employer)", "amount": "1625.00" },
        { "code": "EDLI_ER", "name": "EDLI (Employer)", "amount": "250.00" }
      ],
      "gross": "50000.00",
      "total_deductions": "12341.00",
      "net": "37659.00",
      "pay_floor_check": "pass"
    },
    "notes": "Verified against Income Tax Act 1961 Section 192, EPF Scheme 1952, ESI Act 1948."
  }
]
```

---

## 5. Verification Process

### 5.1 Who Can Verify

- **Not** the person who wrote the pack
- A named human with relevant qualification:
  - Payroll compliance analyst (internal)
  - Chartered accountant / CPA (external)
  - Employment law counsel (external)
  - Statutory compliance consultant

### 5.2 Verification Block

```json
"verification": {
  "verified_by_name": "Priya Sharma",
  "verified_by_role": "Chartered Accountant",
  "verified_on": "2026-10-20",
  "source_document_reference": "Income Tax Act 1961 Sec 192; EPF Scheme 1952 Para 26; ESI Act 1948 Sec 39; Finance Act 2024 Notif 15/2024",
  "golden_case_set_id": "in-central-gc-2026"
}
```

### 5.3 Signing

The pack must be signed with Ed25519. The signature covers the canonical JSON **excluding the `signing` block**.

```json
"signing": {
  "algorithm": "ed25519",
  "key_id": "karmathy-compliance-key-2026",
  "signature": "base64-encoded-signature-bytes",
  "signed_at": "2026-10-20T14:30:00Z",
  "signed_by": "Priya Sharma"
}
```

---

## 6. Loading and Using Packs

### 6.1 Load a Pack

```python
from app.rules.loader import load_rule_pack

pack = load_rule_pack("rule_packs/in-central-verified.json")
# Raises RulePackLoadError if schema validation fails
```

### 6.2 Resolve Effective-Dated Pack

```python
from app.rules.loader import load_rule_pack_for_date
from datetime import date

pack = load_rule_pack_for_date(
    pack_dir="rule_packs",
    jurisdiction="IN",
    calc_date=date(2026, 6, 15)
)
# Returns the verified pack effective on 2026-06-15
```

### 6.3 Resolve the Pack a Pay Run May Use

The loader answers "which pack is in force"; the resolver answers the
question the payroll API asks, which is the same question plus "and if there
is none, what was found and what has to be done":

```python
from app.rules.resolver import resolve_rule_pack
from datetime import date

resolution = resolve_rule_pack("IN", date(2026, 6, 15))
if resolution.is_verified:
    pack = resolution.pack          # the verified pack in force
else:
    resolution.pack_status           # absent | draft | pending_verification | superseded
    resolution.missing               # what the operator has to do, and who
    resolution.details()             # the details of the refusal envelope
```

The packs are read from the directory named by the `RULE_PACK_DIR`
environment variable, or from `rule_packs/` when it is not set. The
directory is read on every resolution, so a pack can be installed without a
restart. A pack that does not validate against the schema cannot enable a
jurisdiction: it is skipped, and the refusal says so.

### 6.4 Calculate a Payslip

```python
from app.rules.engine import calculate_payslip_from_pack
from decimal import Decimal

result = calculate_payslip_from_pack(
    pack=pack,
    base_salary=Decimal("50000"),
    pay_frequency="monthly",
    overtime_hours=Decimal("5"),
    overtime_hourly_rate=Decimal("288.00"),
    benefit_deductions=Decimal("1800"),
)
```

---

## 7. Testing Packs

### 7.1 Schema Validation

```bash
python -c "
from app.rules.loader import validate_against_schema
import json
with open('rule_packs/in-central-draft.json') as f:
    errors = validate_against_schema(json.load(f))
print('Errors:' if errors else 'Valid')
for e in errors: print(f'  - {e}')
"
```

### 7.2 Run Golden Cases

```python
from app.rules.engine import run_golden_cases

results = run_golden_cases(pack)
for case_id, passed, msg in results:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} {case_id}: {msg}")
```

### 7.3 Determinism Test

```python
from app.rules.engine import calculate_payslip_from_pack
from decimal import Decimal

# Run 10 times
trace_ids = set()
for _ in range(10):
    result = calculate_payslip_from_pack(pack=pack, base_salary=Decimal("50000"), pay_frequency="monthly")
    trace_ids.add(result.trace_id)

assert len(trace_ids) == 1, "Non-deterministic!"
```

---

## 8. Jurisdiction-Specific Notes

### 8.1 India (Launch Jurisdiction)

| Area | Key Sources |
|------|-------------|
| Income Tax | Income Tax Act 1961, Finance Act (annual), CBDT notifications |
| EPF | EPF & MP Act 1952, EPF Scheme 1952, EDLI Scheme 1976 |
| ESI | ESI Act 1948, ESI Regulations |
| Professional Tax | State-specific Acts (e.g., Karnataka, Maharashtra, Tamil Nadu) |
| Gratuity | Payment of Gratuity Act 1972 |
| Maternity | Maternity Benefit Act 1961 (amended 2017) |
| Leave | State Shops & Establishments Acts; Factories Act 1948 |
| Overtime | Factories Act 1948 (Sec 59); State Shops Acts |
| Minimum Wage | Minimum Wages Act 1948; Central/State notifications |
| Payslip | Payment of Wages Act 1936; State rules |

### 8.2 Region-Dependent Rules

For India, many rules vary by state:
- Professional tax rates and slabs
- Shops & Establishments Act thresholds (weekly hours, overtime, leave)
- Minimum wage rates
- Public holidays

**Model as separate packs** with `jurisdiction.region` (e.g., `IN-KA`, `IN-MH`, `IN-TN`) or include region-dependent tables in a central pack with `region_dependent: true`.

---

## 9. Common Pitfalls

| Pitfall | Prevention |
|---------|------------|
| Missing `source` block | Schema requires it; pack cannot leave `draft` |
| Placeholder values in `verified` pack | Schema requires non-null for jurisdiction-defined thresholds |
| No golden cases | Schema requires `minItems: 1` on `golden_cases` when `verified` |
| Self-verification | Process control: writer ≠ verifier |
| Unsigned pack | Loader rejects packs without valid `signing` block |
| Overlapping effective dates | Loader refuses to attach overlapping packs for same jurisdiction |
| Float values in pack | Use JSON numbers (not strings) for rates; engine converts to Decimal |
| A band that states no rate | A band states its lower bound, its upper bound **and** its `rate`; a banded table (`"kind": "banded"`) has to state it on every band, and the pack is refused **when it is loaded**, naming the table and the band |
| A table written as a list of rows with no `kind` | A table says what shape its rows have: `"banded"` or `"schedule"` |
| A table written in both forms | A table is either a list of rows or a keyed map, never both; the schema refuses one that is both |
| A band table written as a flat map (or the other way round) | The tax table is banded, the contribution tables are flat maps; a table in the wrong form is refused, not reinterpreted |

---

## 10. Demo Pack

`rule_packs/demo-synthetic-draft.json` — Synthetic values only, clearly marked. Use for:
- Schema validation testing
- UI development (blocked state demonstration)
- Starting a pack of your own

**Never verify or use in production.**

> **It loads, and it computes.** The demo pack's `tax_bands` is a banded
> table (`"kind": "banded"`), and each of its four bands states the rate its
> own `notes` already gave in prose — 0 %, 10 %, 20 % and 30 %. Its three
> golden cases are the engine's output, line for line, and the payroll
> suite replays them, so the pack and the engine cannot drift apart. The
> pack stays a **draft**: a named human verifier, and not the author of a
> pack, is the only thing that may verify one.
>
> The pack's own `source.notes` say what a band is, so an author learns the
> shape from the file.

---

## 11. References

- `contracts/rules/rule-pack.schema.json` — Authoritative JSON Schema
- `contracts/rules/preset.schema.json` — Business preset schema (references rule packs)
- `backend/app/rules/loader.py` — Loading and validation logic
- `backend/app/rules/engine.py` — Calculation engine
- `backend/app/rules/test_determinism.py` — Determinism and golden case tests
- `agents/payroll-rules/ESCALATIONS.md` — Owner decisions needed for India pack