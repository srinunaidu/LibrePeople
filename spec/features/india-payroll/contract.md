# Feature: india-payroll

## Goal
Ship the India payroll data model (slice 1) and an FY 2025-26 India rule pack in pending-verification state (slice 2), so India payroll is representable end-to-end but the governance gate still refuses to calculate until a named human verifies the pack (GATE_0_DECISIONS.md §1.4).

## Approved scope (do not relitigate)
NEW regime (§115BAC) tax only; PT for KA/MH/TN/TG/WB; monthly pay only; FY 2025-26 rates. No UI, no payslip/report endpoints, no router changes.

**Recon correction:** the latest migration is `0029_schema_drift_fix` (not 0028). New migrations start at **0030**.

---

## SLICE 1 — india-payroll-data-model

### Migration `backend/migrations/versions/0030_india_employee_fields.py`
One migration, revision `0030_india_employee_fields`, down_revision `0029_schema_drift_fix`. Follow the 0029 idempotency pattern (`catalog_names`, ask the catalog before every add; print progress). Mirror the model changes exactly (schema_drift_test_suite / schema_alignment_test_suite compare models vs migrations).

**employees:** add `pan_number` String(10) nullable + CHECK `regexp_like(pan_number, '^[A-Z]{5}[0-9]{4}[A-Z]$')` (SQLite-compatible plain CHECK with GLOB/regex as the 0029 helpers allow); `tax_regime` String(10) NOT NULL server_default `'new'` + CHECK `IN ('new','old')`; `pf_uan` String(12) nullable; `esi_number` String(17) nullable; `ifsc_code` String(11) nullable + CHECK `^[A-Z]{4}0[A-Z0-9]{6}$`.

**Implementation note (PAN/IFSC CHECKs):** as implemented in 0030, the PAN and IFSC CHECKs are written as dialect-portable length/substr/BETWEEN text constraints rather than `regexp_like`/`GLOB` expressions. They enforce the exact same semantics as `^[A-Z]{5}[0-9]{4}[A-Z]$` (PAN) and `^[A-Z]{4}0[A-Z0-9]{6}$` (IFSC): upper-case letters, digit positions, and the literal `0` at IFSC position 5. The regex shapes above remain the normative intent; the portability tradeoff is recorded here so the verifier knows the CHECK text will not literally match this section.
**employee_pay_profiles:** add `pt_state` String(2) nullable + CHECK `IN ('KA','MH','TN','TG','WB')`.
**clients:** add `country_code` String(2) nullable; backfill from existing `country` where it already matches `^[A-Z]{2}$`.
**Backfill/defaults:** `tax_regime` defaults to `'new'` for all existing rows (accepted decision: new regime only). No other backfill.
**downgrade:** drop the seven added columns (5 employee fields: `pan_number`, `tax_regime`, `pf_uan`, `esi_number`, `ifsc_code`; plus `employee_pay_profiles.pt_state` and `clients.country_code`) — drop indexes referencing them first, SQLite style, as 0029 does.

**tax_withholding decision (record, don't change):** the flat percent column stays. The rule engine already ignores it whenever the pack carries a `tax_bands` table (engine.py `calculate_tax` uses it only as a fallback when the table is absent); banded packs supersede it implicitly. Add a comment on `EmployeePayProfile.tax_withholding`: "percent fallback; ignored by packs that carry a banded tax table (e.g. IN)".

### AC slice 1
- AC-1: `ci/run_backend_tests.sh migration` passes (up applies on the SQLite DB the suite builds; re-running is a no-op; downgrade drops cleanly).
- AC-2: `ci/run_backend_tests.sh payroll` and `ci/run_backend_tests.sh schema` pass unchanged (US data model untouched).
- AC-3: schema_drift + schema_alignment suites pass (models and 0030 agree).
- AC-4: an INSERT of a PAN like `ABCDE1234F` succeeds and `abcde1234f` / `ABCD1234F5` fail with a constraint error; same shape for IFSC.
- AC-5: an existing employee row reads back with `tax_regime == 'new'` after migration.

---

## SLICE 2 — india-rule-pack-fy2526

### Pack `backend/rule_packs/in-standard.json`
`pack_id "in-standard"`, `name "India Standard (FY 2025-26)"`, jurisdiction `{"country":"IN","display_name":"India"}` (no region — PT handled by tables inside the pack), version `1.0.0`, status **`pending_verification`**, `verification: null`, `effective_from "2025-04-01"`, `effective_to "2026-03-31"`, `tz "Asia/Kolkata"`. Conform to `backend/contracts/rules/rule-pack.schema.json` (all required blocks: thresholds, overtime, leave_types, working_time_limits, break_rules, mandatory_payslip_fields, pay_frequency_rules with `allowed_frequencies:["monthly"]` only, reporting_obligations, public_holiday_rules, signing, golden_cases). `signing`: mirror the block shape of us-standard-verified.json (`key_id "in-standard-key"`, signed_at at content freeze); note in the verification doc that the loader does not cryptographically verify signatures — same as the US pack today.
`source` block: Income Tax Act §115BAC + Finance Act 2025 (slabs & §87A), EPF Act 1952 §6 + EPF Scheme para 26A (ceiling ₹15,000), ESI Act 1948 (₹21,000 coverage; 0.75%/3.25%), the five state PT acts (cite each by name in `source.notes`). `mandatory_payslip_fields`: same list as the US pack plus `professional_tax`. Golden case set id reserved: `gc-in-standard-001` (name cases `gc-in-standard-001-*`).

**Rate tables (transcribe exactly; unit `currency_amount`, monthly):**
- `tax_bands` (banded, monthly = annual slab/12, bounds: 33333.33 / 66666.67 / 100000 / 133333.33 / 166666.67 / 200000 / open; rates 0 / 5 / 10 / 15 / 20 / 25 / 30; notes carry the annual §115BAC slab per band).
- `tax_adjustments` (values): `standard_deduction_monthly` = 6250 (§16(ia) ₹75,000/yr).
- `tax_rebates` (values): `rebate_87a_max_monthly` = 5000 (§87A ₹60,000/yr), `rebate_87a_income_limit_monthly` = 100000 (§87A ₹12,00,000 taxable/yr). `source.notes` must record: marginal relief above ₹12L is NOT encoded; verifier must decide whether v1.1 needs it.
- `social_insurance_employee` (values): `pf` 12% (EPF Act §6), `esi` 0.75% (ESI Act).
- `social_insurance_employer` (values): `pf` 12%, `esi` 3.25%. Notes: employer PF is EPS/EPF-split in law; v1 records 12% flat — checklist item for verifier.
- `social_insurance_ceilings` (values): `pf_wage_ceiling` 15000 (EPF Scheme cap — caps the contribution base), `esi_wage_limit` 21000 (ESI coverage limit — esi codes skipped above it, not capped).
- PT tables `pt_ka`, `pt_mh`, `pt_tn`, `pt_tg`, `pt_wb` — `kind "schedule"`, entries state gross bounds via `value` (lower, inclusive) and `max_value` (upper, exclusive; absent = open), and the flat monthly PT amount in `rate` (documented reading; put this exact convention in each table's `description`):
  - pt_ka: 0–25000 → 0; 25000+ → 200.
  - pt_mh: 0–10000 → 0; 10000+ → 200 (Feb ₹300/cap ₹2500 — checklist).
  - pt_tn: 0–25000 → 0; 25000+ → 208.50 (TN's statutory schedule is half-yearly with intermediate slabs — checklist: confirm/add before verification).
  - pt_tg: 0–15000 → 150; 15000+ → 200.
  - pt_wb: 0–5000 → 0; 5000–6000 → 18; 6000–7000 → 25; 7000–8000 → 30; 8000–9000 → 40; 9000–10000 → 45; 10000–15000 → 60; 15000–25000 → 80; 25000–40000 → 90; 40000+ → 200 (checklist: confirm rows).
- `thresholds` / `overtime`: nulls where India sets no value, with the §115BAC/FACTORIES ACT note; gratuity: **explicit exclusion note** in `source.notes` (Payment of Gratuity Act 1972 deferred to a later slice).

### Engine extensions — `backend/app/rules/engine.py` ONLY, all guarded so the US pack behaves byte-identically
1. `CalculationContext` and `calculate_payslip_from_pack` gain `pt_state: Optional[str] = None`; `run_golden_cases` forwards `pt_state` from case inputs when present (US golden cases unaffected).
2. `calculate_tax`: before banding, subtract `standard_deduction_monthly` if the `tax_adjustments` table exists; after banding, if `tax_rebates` exists and taxable ≤ `rebate_87a_income_limit_monthly`, emit deduction line `REBATE_87A` = min(band_tax, `rebate_87a_max_monthly`) and reduce tax by it. Tables absent → behavior unchanged (US pack has neither).
3. `calculate_social_insurance`: for each contribution code, if `social_insurance_ceilings` has `{code}_wage_ceiling`, cap that code's base at it (PF on 15000); if it has `{code}_wage_limit`, skip the code entirely when base > limit (ESI absent above 21000). Table absent → unchanged.
4. New `calculate_professional_tax(ctx)`: if `ctx.pt_state` is set and the pack has table `pt_{state.lower()}`, find the single entry whose gross band contains the base and add deduction line `PT_{state}` = the entry's `rate`. Call it from `calculate_payslip_from_pack` after social insurance. No table → zero, no line.

### Verification hand-off
`backend/rule_packs/in-standard-VERIFICATION.md`: the exact five fields the named human must fill (`verified_by_name`, `verified_by_role`, `verified_on`, `source_document_reference`, `golden_case_set_id: gc-in-standard-001`), the status flip `pending_verification → verified`, and the checklist of items above marked "checklist" (MH Feb ₹300, TN mid-slabs, WB rows, employer PF split, marginal relief).

### Golden cases (11, inputs in the US pack's shape + `pt_state`)
| # | case | base | key pins |
|---|------|------|----------|
| 1–5 | one per state KA/MH/TN/TG/WB | KA 25000→PT 200; MH 22000→200; TN 30000→208.50; TG 22000→200; WB 45000→200 | PT table per state; PF 1800/1800 (base ≥15000); ESI none (>21000) |
| 6 | `general-young-age-25` | 80000 | tax 0 after §87A rebate (rebate line 2729.16); bands 0–2 exercised |
| 7 | `senior-age-62` | 80000 | byte-identical output to case 6 — new regime has no age distinction |
| 8 | `pf-ceiling-cross` | 60000 | PF 1800 EE / 1800 ER on capped 15000 (NOT 7200); TDS 0 (rebate 1020.83); PT_KA 200 |
| 9 | `esi-edge-at-limit` | 21000 | ESI applies at exactly 21000: 157.50 EE / 682.50 ER; PF on capped 15000 |
| 10 | `esi-edge-above-limit` | 21000.01 | ESI skipped; PF unchanged |
| 11 | `high-earner-tds` | 200000 | TDS 23437.50 (no rebate); PT_KA 200; net 174562.50 |

Expected figures: compute each line half-up to 2dp (`money()`), state the arithmetic in each case's `notes`; the human verifier re-derives them from the cited acts.

### AC slice 2
- AC-6: `load_rule_pack("backend/rule_packs/in-standard.json")` succeeds (schema-valid, band rule clean).
- AC-7: `load_rule_pack_for_date(packs_dir, "IN", date(2025,10,1))` raises `RulePackLoadError("No verified rule pack ...")` — the gate refuses as shipped.
- AC-8: `calculate_payslip_from_pack(pack, ...)` raises (pack not verified) for the shipped file.
- AC-9: with status flipped to `verified` in memory (same pattern payroll_test_suite.py uses for the demo pack), `run_golden_cases(pack)` returns pass for all 11 cases; running twice is deterministic.
- AC-10: every AC of slice 1 still passes; `ci/run_backend_tests.sh payroll` unchanged-green.

---

## Test plan (real commands)
1. New suite `backend/india_payroll_test_suite.py` (own SQLite DB, `check()` style like payroll_test_suite.py): AC-6/7/8/9 + migration spot checks (AC-4/5). Register it in `ci/run_backend_tests.sh` `SUITES` after `payroll_execution_test_suite`.
2. `bash ci/run_backend_tests.sh india` → the new suite passes.
3. `bash ci/run_backend_tests.sh migration` and `bash ci/run_backend_tests.sh schema` → pass (slice 1 gate).
4. `bash ci/run_backend_tests.sh payroll` → unchanged pass (US regression).
5. `cd backend && .venv/bin/python -m pytest app/rules/test_determinism.py app/rules/test_reconciliation.py -q` → pass (engine guards don't disturb US-path tests).
6. `bash ci/run_backend_tests.sh` full run → all suites pass.
7. Only if employee Pydantic response schemas gained optional fields: `cd frontend && npm run verify` → pass.

## Files to touch
- create `backend/migrations/versions/0030_india_employee_fields.py`
- refresh `docs/DB_SCHEMA.sql` — generated artifact, regenerated via `cd backend && .venv/bin/python scripts/generate_db_schema.py` after the 0030 migration/model edits (do not hand-edit)
- edit `backend/app/models/employee.py`, `backend/app/models/payroll.py` (EmployeePayProfile), `backend/app/models/client_onboarding.py` (Clients.country_code)
- edit the employee Pydantic schema module (optional fields only; no endpoint changes) — locate under `backend/app/schemas/`; do NOT touch routers
- create `backend/rule_packs/in-standard.json`, `backend/rule_packs/in-standard-VERIFICATION.md`
- edit `backend/app/rules/engine.py` (guarded extensions only)
- create `backend/india_payroll_test_suite.py`; edit `ci/run_backend_tests.sh` (SUITES entry)

## Files NOT to touch
- `backend/rule_packs/us-standard-verified.json`; `backend/contracts/rules/rule-pack.schema.json`; `backend/app/rules/loader.py`; `backend/app/rules/reconciliation.py`; `backend/app/rules/money.py`
- `backend/app/services/payroll_engine.py` and `backend/app/api/**` (no router/payslip/report wiring)
- migrations ≤ 0029; frontend source (except running verify)

## Sequencing
Slice 1 lands and passes AC-1..AC-5 **before** slice 2 starts (golden cases and PT state depend on the migration's `tax_regime`/`pt_state`). One PR is fine if commits are per-slice and slice-1 tests are shown passing first.

## Risks / edge cases
- Band bounds 33333.33/66666.67 are thirds: rounding is pinned by golden cases, but the verifier must re-derive; document in pack notes.
- ESI `21000.01` relies on Decimal comparison — never float.
- Oracle: CHECK constraints in 0030 must be Oracle-compatible (plain CHECK / `regexp_like`, following 0029's helper style).
- Single `salary` field means PF/ESI base = full gross, not Basic+DA: recorded as v1 simplification in pack notes + checklist; verifier decides.
- The engine refuses non-verified packs by design — do NOT loosen `is_verified()` to make tests pass; flip status in test memory only.
- PT tables reuse the schedule entry's `rate` field as a flat monthly amount; this convention is documented in each table's `description` and in the verification doc.

## Test command
`bash ci/run_backend_tests.sh india && bash ci/run_backend_tests.sh payroll && cd backend && .venv/bin/python -m pytest app/rules -q`
