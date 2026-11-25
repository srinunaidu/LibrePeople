# Payroll Module — Karmathy HCM

**Version:** 0.1 (Draft)
**Last Updated:** 2026-10-21
**Owner:** Payroll & Rules Agent

---

## 1. Overview

The Karmathy payroll module is a **configurable calculation engine**, not a statutory payroll engine. It produces payslips and payment data driven entirely by **verified rule packs** — versioned, signed, jurisdiction-specific JSON documents containing statutory rates, thresholds, and rules.

> **Critical:** Payroll output is labelled "configurable calculation" on every screen and export. It is never presented as statutory, compliant, or filing-ready.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PAYROLL PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Inputs ──► Validate ──► Calculate (per employee) ──► Totals   │
│    │                                                        │    │
│    │                    Rule Pack                             │    │
│    │              (verified, effective-dated)                  │    │
│    │                                                        ▼    │
│    │                    Review ──► Approve ──► Lock            │
│    │                                                        │    │
│    ▼                                                        ▼    │
│  Payslips ◄────────────── Reconciliation ◄──── Payment Export   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Core Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| Rule Pack Schema | `contracts/rules/rule-pack.schema.json` | Defines pack structure; enforces verification requirements |
| Rule Pack Loader | `backend/app/rules/loader.py` | Loads, validates, resolves effective-dated packs |
| Rule Pack Resolver | `backend/app/rules/resolver.py` | The pack in force for a jurisdiction and a pay date, and why there is none |
| Calculation Engine | `backend/app/rules/engine.py` | Pure, deterministic payslip calculation |
| Money Helpers | `backend/app/rules/money.py` | Decimal arithmetic, rounding, proration |
| Reconciliation | `backend/app/rules/reconciliation.py` | Traceability report; verifies every total |
| Payroll API | `backend/app/api/v1/endpoints/payroll.py` | HTTP endpoints for periods, runs, payslips |
| Payroll Models | `backend/app/models/payroll.py` | SQLAlchemy models for periods, runs, payslips, profiles |

---

## 3. Rule Packs

### 3.1 Lifecycle

```
draft → pending_verification → verified → superseded
  │            │                  │            │
  │            │                  │            └─ Historical only; has effective_to
  │            │                  └─ Production usable; signed + golden cases
  │            └─ Frozen; awaiting human review
  └─ Editable; unusable in production
```

### 3.2 Verification Requirements (Schema-Enforced)

A pack can only reach `verified` if it has:
- Complete `source` block (document, publisher, reference, URL, retrieved date)
- Complete `verification` block (verifier name, role, date, source reference, golden case set ID)
- At least one `golden_case`
- Valid Ed25519 signature in `signing` block

### 3.3 Blocked Jurisdictions

A jurisdiction without a `verified` pack in force on the pay date **cannot be
calculated**. A pay run for one is refused with `rule_pack_not_verified`
(409, the shared error envelope) and the details say what was found and what
has to be done:

```json
{
  "jurisdiction": "IN",
  "pay_date": "2026-03-31",
  "pack_status": "draft",
  "missing": [
    "the rule pack 'india-2026' for jurisdiction 'IN' is in state 'draft' and covers the pay date 2026-03-31: a named human verifier - not the author of the pack - has to verify it against its cited source and its golden cases before this pay run can be calculated"
  ]
}
```

`pack_status` is one of `absent` (no pack covers the jurisdiction, or none
covers the pay date), `draft`, `pending_verification` or `superseded`. The
refusal writes nothing: no payslip, no change to the pay run, and no audit
row that claims the run was calculated. The one row that is written records
the refusal, because that row is the evidence.

The `missing` list names what the operator has to do and who has to do it.
It never carries a rate, a threshold or an entitlement: the contents of a
rule pack are not the operator's problem, and they do not belong in an error
message.

### 3.4 The two forms of a rate table, and how each is read

The rule-pack schema writes a rate table in one of two forms, and the engine
reads each of them in one way only. A pack that uses one form is never read
as the other.

| Form | In the pack | How the engine reads it |
|------|-------------|--------------------------|
| **Banded** | `entries` | A band states three numbers: `value` is the **lower bound** of the band, `max_value` is its upper bound (omitted for an open-ended top band) and `rate` is the percentage rate that applies inside the band. The taxable amount is divided between the bands by their bounds, and each part is taxed at the rate of the band it falls in. |
| **Keyed map** | `values` | Every value is a **percentage rate** that applies to the whole base; the key is the code the engine looks up. There are no bounds and no bands. |

A band that states no rate, a band table whose bounds do not ascend, a tax
table written as a flat map and a contribution table written as bands are all
things the engine cannot read. **A pack it cannot read is refused**, with the
same `rule_pack_not_verified` envelope, before a single payslip is written:

```json
{
  "jurisdiction": "QQ",
  "pay_date": "2026-03-31",
  "pack_status": "verified",
  "required": [
    "the band table 'tax_bands' states no rate for band 'BAND_1': the engine reads a band's value as the lower bound of the band, so the rate that applies inside the band has to be stated in the band's 'rate' field"
  ]
}
```

The `required` list says **what is wrong with the pack**, not what the pack
contains: it names the table and the band and never a rate, a bound or a
threshold. A wrong pay figure is worse than a refusal, so the engine refuses
rather than guess.

> **Before this was fixed**, the engine read a band's `value` as a
> *percentage* while the schema read it as the band's *lower bound*. The two
> readings differ by a factor of a hundred, and a pack that follows the
> schema — including the demo pack the product ships — was computed wrongly
> or not at all. `agents/DECISIONS.md` DEC-020 settled it: the schema is the
> authority.

### 3.5 The jurisdiction of a pay run

A pay run names the jurisdiction whose rules apply to it: the ISO 3166-1
alpha-2 country code, on `pay_runs.jurisdiction`. It is required when the
run is created, because a run whose jurisdiction is unknown cannot be
calculated against a verified rule, and a run that guesses one would be
calculated against rules that may not be the ones that apply to its
employees.

The pack is resolved by jurisdiction **and** pay date: the pack whose
effective period covers the pay date of the period and whose state is
`verified`. Where more than one pack covers the date, the most recent
`effective_from` wins, and a verified pack is preferred over an unverified
one — an unverified pack may not be used at all, and the rules verified
before it are still the ones in force.

The rule packs are read from the directory named by the `RULE_PACK_DIR`
environment variable, or from `rule_packs/` when it is not set. The
directory is read on every resolution, so a deployment can install a pack
without a restart. A pack that does not validate is not a pack: it cannot
enable a jurisdiction.

---

## 4. Pay Run Lifecycle

| State | Description | Transitions | Who |
|-------|-------------|-------------|-----|
| `Draft` | Created, not calculated | → `Processing` | Admin |
| `Processing` | Calculation in progress | → `Draft` (cancel), → `Approved` | System |
| `Approved` | Calculated, awaiting sign-off | → `Processing` (reopen), → `Finalized` | Admin (different from processor — SoD) |
| `Finalized` | **Immutable**; payslips locked | → `Paid` | Admin |
| `Paid` | Payment file exported | (terminal) | System |

**Segregation of Duties:** The user who processes a run (`processed_by`) cannot approve it (`approved_by`).

**Idempotency:** `POST /runs/{id}/process` accepts `Idempotency-Key` header for safe retries.

**Dry Run:** `dry_run=true` query parameter produces full results without state change. Labelled "dry run — configurable calculation".

---

## 5. Calculation Engine

### 5.1 Inputs (per employee)

| Input | Source | Required |
|-------|--------|----------|
| `base_salary` | Employee pay profile (per pay period) | Yes |
| `pay_frequency` | Employee pay profile | Yes |
| `tax_withholding_override` | Employee pay profile (percentage) | No |
| `hours_worked` | Workforce Core (time attendance) | No |
| `overtime_hours` | Workforce Core (overtime calculation) | No |
| `overtime_hourly_rate` | Derived from base_salary / period hours | No |
| `leave_days` | Workforce Core (approved unpaid leave) | No |
| `benefit_deductions` | Benefits enrollment | No |
| `other_earnings` / `other_deductions` | Manual/ad-hoc | No |

### 5.2 Calculation Steps

1. **Base earnings** — `base_salary` for the period
2. **Overtime** — `overtime_hours × overtime_hourly_rate × premium_multiplier` (from pack)
3. **Other earnings** — Bonuses, allowances, reimbursements
4. **Gross** — Sum of all earnings
5. **Tax** — Progressive bands from the pack's `tax_bands` rate table (a
   banded table, read as in §3.4), or the flat configured withholding when
   the pack has no tax table
6. **Employee social insurance** — Rates from pack's `social_insurance_employee` table
7. **Benefit deductions** — Pre-tax/post-tax per benefit model
8. **Leave deductions** — Unpaid leave at daily rate
9. **Other deductions** — Loan repayments, garnishments, etc.
10. **Total deductions** — Sum of all deductions
11. **Net** — Gross − Total deductions
12. **Employer contributions** — Rates from pack's `social_insurance_employer` table
13. **Pay-floor check** — Compare gross vs pack's `minimum_wage_amount`/`unit`

### 5.3 The contributions on the payslip

The pack computes the statutory contributions on both sides of the payslip:
the employee's own, which are deductions like any other, and the employer's,
which are the employer's money and are not part of the employee's pay at
all. Both are stored on the payslip, in `pay_slips.employee_contributions`
and `pay_slips.employer_contributions`, and both are carried by the
reconciliation.

They are columns of their own because the employer's contribution was
computed, owed and then lost: the payslip had nowhere to put it, so it
disappeared the moment the payslip was written and the reconciliation had
nothing to check. A contribution that is not on the payslip is a
contribution nobody can reconcile.

### 5.4 Traceability

Every payslip line stores:
- `rule_id` — From the rule pack (e.g., `TAX_BAND_1`, `SOCIAL_INSURANCE_EE_PENSION`)
- `rule_version` — Pack version used
- `input_source` — Where the input came from (e.g., `base_salary`, `rule_pack:tax_bands:BAND_1`)
- `calculation` — Human-readable formula (e.g., `5000 * 10%`)

---

## 6. Reconciliation

Runs automatically on every pay run completion.

### 6.1 Verification Rules

- Gross = Sum of all earning lines
- Total Deductions = Sum of all deduction lines
- Net = Gross − Total Deductions
- Employee contributions = Sum of the deduction lines the employee's
  contribution rule produced
- Employer contributions = Sum of all employer contribution lines
- Run totals = Sum of all payslip totals
- Every line must have a `rule_id` and `input_source`

### 6.2 Failure Modes

| Failure | Cause |
|---------|-------|
| Gross mismatch | Earning line missing or amount changed |
| Deductions mismatch | Deduction line missing or amount changed |
| Net mismatch | Gross or deductions tampered |
| Run total mismatch | Payslip added/removed after calculation |
| Missing trace | Line without `rule_id` or `input_source` |

**Result:** `status = "failed"` with specific error messages. Run cannot be finalized until resolved.

---

## 7. Payment File Export

### 7.1 Formats

| Format | Jurisdiction | Template Source |
|--------|--------------|-----------------|
| SEPA Credit Transfer (ISO 20022) | EUR zone | Rule pack `payment_file_template` or customer template |
| NACHA ACH | US | Customer template |
| IMPS/NEFT/RTGS | India | Bank-specific format |
| BACS | UK | Customer template |
| Generic CSV | Any | Configurable columns |

### 7.2 Export Contents

- Employee reference (no name in event)
- Bank details (IBAN, account, sort code — **encrypted at rest**, decrypted only for export)
- Net pay amount
- Currency
- Payment reference
- Rule pack ID + version (for audit)

### 7.3 Background Job

Export runs as a background job (platform-security queue). Large payrolls do not block the web request.

---

## 8. Reports

### 8.1 Operational Reports

| Report | Description |
|--------|-------------|
| Payroll Register | All payslips for a run with earnings/deductions breakdown |
| Cost Centre Summary | Gross/net/employer cost by department/cost centre |
| Tax Liability | Employee/employer tax by jurisdiction |
| Social Insurance Summary | EE/ER contributions by component |
| Leave Liability | Accrued but untaken leave by type |
| Overtime Analysis | Overtime hours and cost by employee/department |

### 8.2 Compliance Reports

| Report | Description |
|--------|-------------|
| Working-Time Violations | Employees exceeding weekly/daily limits |
| Pay-Floor Breaches | Employees below minimum wage |
| Expiring Eligibility | Work visas, certifications expiring soon |
| Overdue Certifications | Mandatory training/certs past due |
| Retention Status | Documents past retention period |
| Erasure Log | Data erasure requests and completion |
| Audit Chain Status | Hash chain verification of audit log |

### 8.3 Export Formats

- CSV (streaming for large datasets)
- PDF (formatted, with rule pack version watermark)
- Background job with audit log entry

### 8.4 Statutory Filing Exports

**Only from a verified pack's template.** Shows pack version and status. Never generated for unverified jurisdictions.

---

## 9. Integration Points

### 9.1 Workforce Core (Inputs)

| Input | Endpoint | Status |
|-------|----------|--------|
| Approved leave days | `GET /leave/approved-days?employee_id=&period=` | Not connected |
| Overtime hours | `GET /time/overtime?employee_id=&period=` | Not connected |
| Hours worked | `GET /time/hours?employee_id=&period=` | Not connected |

### 9.2 Data Import (Base Data)

| Data | Endpoint | Status |
|------|----------|--------|
| Employee pay profiles | `POST /import-export/import/employee_pay_profiles` | Schema ready; unit decision needed |
| Pay components | `POST /import-export/import/pay_components` | Ready |

### 9.3 Platform Security (Infrastructure)

| Feature | Status |
|---------|--------|
| Audit log (same-transaction) | Partial (payroll commits audit separately) |
| Field encryption (bank details) | Not implemented |
| Background job queue | Not implemented |
| Hash chain audit | Not implemented |

---

## 10. Security & Compliance

### 10.1 Data Handling

- **No statutory values in code** — only in verified rule packs
- **No personal data in events** — payslip events carry only references
- **Bank details encrypted** — AES-256-GCM with key versioning (planned)
- **Payslips immutable after Finalized** — corrections via off-cycle runs

### 10.2 Access Control

| Role | Permissions |
|------|-------------|
| `SuperAdmin` | Full payroll access |
| `PayrollAdmin` | Create/run/approve/finalize pay runs |
| `PayrollViewer` | Read-only access to runs, payslips, reports |
| `Manager` | Team payslips only (visibility filter) |
| `Employee` | Own payslips only (ESS) |

---

## 11. Testing Requirements

| Test | Status |
|------|--------|
| Schema validation (missing source/verifier/golden case) | Implemented |
| Golden case replay for every verified rule | Implemented (no verified packs yet) |
| Reconciliation detects tampered totals | Implemented |
| Determinism: identical inputs → identical trace_id | Implemented |
| Blocked state: calculate a run without a verified pack | Implemented - `backend/payroll_test_suite.py` |
| E2E: Dry run → payslips → reconciliation | Not implemented |
| Immutability: Finalized run rejects edits | Partial (API enforces) |

---

## 12. Known Limitations (Audit Findings)

| ID | Finding | Status |
|----|---------|--------|
| A2-15 | Payroll ignores approved leave, overtime, benefit deductions | Engine accepts; API not connected |
| A2-16 | `base_salary` unit ambiguity (engine: per-period; offer: annual) | Owner confirmed per-period; offer letter must change |
| PY-08 | Payroll disabled without verified pack | **Verified** — by design; the refusal is in the API (`rule_pack_not_verified`) |

---

## 13. Future Work

- [x] Store the employer contributions the pack computes — the payslip carries `employee_contributions` and `employer_contributions`, and the reconciliation checks both
- [ ] Connect workforce-core inputs (leave, overtime, hours)
- [ ] Implement benefit deduction model (pre-tax/post-tax)
- [ ] Build India rule pack with named verifier
- [ ] Payment file templates per jurisdiction
- [ ] Background job integration for large payrolls
- [ ] Field encryption for bank details
- [ ] Hash chain audit for payroll mutations
- [ ] Manager/Employee visibility filters on payslip endpoints
- [ ] Off-cycle adjustment run workflow

---

## 14. References

- `docs/RULE_PACKS.md` — Rule pack authoring and verification guide
- `docs/REPORTS.md` — Report definitions and export formats
- `contracts/rules/rule-pack.schema.json` — Authoritative schema
- `backend/app/rules/` — Engine, loader, money, reconciliation
- `agents/payroll-rules/STATE.md` — Current agent state
- `agents/payroll-rules/ESCALATIONS.md` — Owner decisions needed