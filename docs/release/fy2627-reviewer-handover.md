# FY 2026-27 Statutory Reviewer Handover Package

**Status: ALL ITEMS PENDING — NO SIGN-OFF GIVEN. NOT VERIFIED. NOT ACTIVATED.**
**Pack:** `in-standard` v0.1.0-fy2627-skeleton (`backend/rule_packs/in-standard-fy2627-skeleton.json`), `status: pending_verification`, `effective_from: 2026-04-01`, `effective_to: open`.
**Engine gate:** resolver returns `pack=None` for IN on/after 2026-04-01; pay-run, direct-write, payslip paths refuse with `rule_pack_not_verified`. No fallback to FY25-26.
**Source block (skeleton):** title "India Standard FY 2026-27 — skeleton only (no instrument transcribed yet)", publisher "TBD by FY26-27 verification", reference "TBD — skeleton carries no statutory values", retrieved 2026-03-31. All rates/amounts 0, thresholds/overtime numerics null, golden cases 14 TEST-ONLY zero placeholders (`gc-fy2627-p5-01` … `p5-14`).
**Reference only:** `docs/release/fy2627-reviewer-package.md` (rule inventory), `backend/rule_packs/in-standard-FY2627-SIGNOFF.md` (transcribe→golden-cases→scope→verify→gates→commit scaffold), `backend/rule_packs/in-standard-VERIFICATION.md` (FY25-26 checklist carry-overs), `docs/release/pg-proof-report.md` (scratch-DB proof methodology ONLY — proves migration/seed/backup method, asserts no statutory values).

## 1. Per-rule trackable items (all PENDING — verified PENDING, no violations)

Reviewer status convention: PENDING = no transcription, no verification, no approval. Any non-PENDING claim without the closure artifact is a violation. Audit result: **all 12 items are honestly PENDING; zero PENDING violations found.**

| # | Rule / Table (rule ID) | Population | Jurisdiction | Effective date | Primary source status | Methodology status | Test evidence status | Closure criterion (exact sign-off artifact required) | Reviewer status |
|---|---|---|---|---|---|---|---|---|---|
| 1 | TDS new-regime bands → `tax_bands` | Salaried employees, IN payroll | India (Income Tax) | 2026-04-01 | MISSING — Finance Act 2026 not cited (skeleton: TBD) | MISSING — transcribe annual slabs; monthly = annual/12 as engine pins; confirm 2dp band-rounding | MISSING — placeholder `gc-fy2627-p5-01-tds-band` (zero); real cases TBD | Verifier transcribes slabs, writes engine-reproduced golden cases, fills 5 verification fields, flips to `verified`, greens 5 gate suites, commits with verifier name | PENDING |
| 2 | Marginal relief → `tax_rebates` / `tax_adjustments` | Taxpayers just above rebate limit | India (Income Tax) | 2026-04-01 | MISSING — Finance Act 2026 relief clause TBD | MISSING — encode relief formula iff statute provides it (FY25-26 v1 has none) | MISSING — TBD | Same closure artifact as #1, covering relief formula or explicit no-relief finding | PENDING |
| 3 | Cess (health & education) → `tax_adjustments` | Taxable employees | India (Income Tax) | 2026-04-01 | MISSING — Finance Act 2026 rate/base TBD | MISSING — transcribe cess rate + base | MISSING — TBD | Same closure artifact as #1, covering cess rate/base | PENDING |
| 4 | EPF / EPS → `social_insurance_employee` / `social_insurance_employer` / `social_insurance_ceilings` | Covered establishments/employees | India (EPFO) | 2026-04-01 | MISSING — EPF Act + Scheme 2026 updates TBD | MISSING — transcribe 12% heads, EPS 8.33% split + ₹15,000 ceiling treatment (FY25-26 v1 flat-12% simplification must be decided) | MISSING — placeholder `gc-fy2627-p5-04-pf-scope` (zero); TBD | Same closure artifact as #1, covering EPS split + ceiling decision | PENDING |
| 5 | ESI → `social_insurance_*` | Covered employees (wage ≤ threshold) | India (ESIC) | 2026-04-01 | MISSING — ESI Act 2026 updates TBD | MISSING — transcribe 0.75%/3.25% heads + wage-limit edge (FY25-26: applies at exactly 21000, skipped above) | MISSING — placeholder `gc-fy2627-p5-05-esi-limit` (zero); TBD | Same closure artifact as #1, covering ESI heads + 21000 edge | PENDING |
| 6 | PT by state → `pt_ka` / `pt_mh` / `pt_tn` / `pt_tg` / `pt_wb` | Employees in each state | KA, MH, TN, TG, WB respectively | 2026-04-01 | MISSING — state PT notifications 2026 TBD (all five states) | MISSING — transcribe monthly tables incl. FY25-26 exceptions to confirm: MH Feb ₹300 + ₹2,500 cap; TN half-yearly→monthly; WB 10 rows | MISSING — placeholders `gc-fy2627-p5-06/07/08` (KA/MH/WB zero); TN/TG cases TBD | Same closure artifact as #1, per state table | PENDING |
| 7 | Basic / DA (PF-able wages) — definition decision | All IN employees | India (EPF wages definition) | 2026-04-01 | MISSING — EPF wages definition TBD | MISSING — decide Basic+DA split vs single `base_salary` (FY25-26 v1 uses full gross) | MISSING — TBD | Recorded verifier decision (split vs gross) inside closure artifact | PENDING |
| 8 | Bonus → `bonus_act` | Eligible employees | India (Payment of Bonus Act) | 2026-04-01 | MISSING — Bonus Act + 2026 updates TBD | MISSING — transcribe eligibility / wage-limit / formula | MISSING — placeholder `gc-fy2627-p5-10-bonus-stub` (zero); TBD | Same closure artifact as #1, covering bonus table | PENDING |
| 9 | Form 16 / Form 24Q → `reporting_obligations` IN_TDS_RETURN | Employers / deductors | India (Income Tax Dept) | 2026-04-01; 24Q quarterly within 31 days | MISSING — filing instruments TBD (`template_refs` IN-24Q / Form 16 unconfirmed) | MISSING — confirm template mapping; no generator verified (structure only) | MISSING — TBD (no generator verified) | Same closure artifact as #1, confirming template_refs mapping | PENDING |
| 10 | LWF → `lwf_state` | Employees in applicable states | State-wise | 2026-04-01 | MISSING — state LWF notifications TBD | MISSING — transcribe state rows | MISSING — placeholder `gc-fy2627-p5-11-lwf-stub` (zero); TBD | Same closure artifact as #1, covering LWF rows | PENDING |
| 11 | Gratuity → `gratuity_accrual` | — (OUT OF SCOPE, see §4) | India (Payment of Gratuity Act 1972) | — | MISSING (deferred by design) | DEFERRED — verifier must both scope (`in_scope: true`) and verify before any use | MISSING — placeholder `gc-fy2627-p5-09-gratuity-boundary` (zero); none required while excluded | Stays excluded; activation requires separate scoping + full closure artifact | PENDING (deferred) |
| 12 | Standard deduction / §87A rebate → `tax_adjustments` / `tax_rebates` | Salaried / rebate-eligible employees | India (Income Tax) | 2026-04-01 | MISSING — Finance Act 2026 TBD | MISSING — transcribe deduction + rebate | MISSING — placeholders `gc-fy2627-p5-02/03` (zero); TBD | Same closure artifact as #1 | PENDING |

Five verification fields (per SIGNOFF scaffold): `verified_by_name`, `verified_by_role`, `verified_on` (≥ `source.retrieved_on`), `source_document_reference`, `golden_case_set_id`. Five gate suites: `india`, `payroll`, `migration`, `framework`, `app/rules` (see SIGNOFF §Gate suites).

## 2. Missing-evidence list (every gap preventing sign-off)

1. Finance Act 2026: slabs, §87A rebate, marginal relief, standard deduction, cess rate/base — no citation, no transcription, no real golden cases.
2. EPF/EPS 2026 instrument: 12% heads, EPS split, ₹15,000 ceiling — undecided, untranscribed, untested.
3. ESI 2026 instrument: heads + wage-limit edge — untranscribed, untested.
4. PT notifications 2026 (KA/MH/TN/TG/WB) + LWF notifications — all untranscribed; MH Feb/cap, TN half-yearly, WB rows unresolved.
5. Basic/DA definition decision — open (gross vs split).
6. Bonus Act 2026 values — untranscribed, untested.
7. Form 16 / 24Q template mapping — unconfirmed; no generator verified.
8. Jurisdictional decisions: PT state applicability, LWF applicable states, EPF/ESI coverage, Bonus eligibility — all TBD by verifier.
9. Methodology reference only: `pg-proof-report.md` proves scratch-DB migration/seed/backup method; contributes zero statutory evidence.
10. No reviewer appointed; no verification fields filled; no gate re-run post-flip; no verifier commit.

## 3. Engagement requirement

**Reviewer profile required:** qualified Indian payroll/statutory professional (e.g. Payroll Compliance Analyst, labour-law counsel, or Chartered Accountant with Indian payroll practice) competent in Finance Act/Income-tax TDS, EPF/EPS, ESI, state PT/LWF, Bonus and Gratuity Acts, able to cite instruments line-for-line and defend golden-case arithmetic.
**Engagement channel:** the owner must appoint the reviewer — no authorized engagement channel exists in this repo/session; this package authorizes no appointment, no contact, no instruction to any named person.
**Handover checklist for owner:** (1) appoint reviewer per profile; (2) give reviewer this file + package.md + SIGNOFF + VERIFICATION + skeleton JSON; (3) reviewer transcribes instruments (no invented values); (4) reviewer writes engine-reproduced golden cases; (5) reviewer sets `in_scope` only for tables the engine may emit; (6) reviewer fills five verification fields, flips to `verified`; (7) reviewer re-runs five gate suites green; (8) reviewer commits with name; (9) owner files sign-off form below per rule.

**Sign-off form template (copy per rule; text signature block):**

```text
FY26-27 STATUTORY SIGN-OFF — one form per rule
Rule / table: <e.g. TDS new-regime bands → tax_bands>
Instrument cited: <exact Act/notification/section + date>
Values transcribed: <slabs/rates/thresholds as cited; or explicit no-relief finding>
Golden cases: <case IDs reproducing engine output line for line>
Methodology: <how monthly/deduction/edge derived>
Jurisdictional decision: <coverage/applicability as decided>
Gate suites re-run: india ___ payroll ___ migration ___ framework ___ app/rules ___
Verdict: [ ] VERIFIED / [ ] REJECTED (no other verdict permitted)
Name: ___
Credentials: ___
Date: ___ (YYYY-MM-DD, >= source.retrieved_on)
Signature (text): /s/ ___ <full legal name>
Commit: <SHA + message with verifier name>
```

## 4. Explicit boundaries (frozen, no authority granted)

- **Gratuity OFF:** `gratuity_accrual` stays out of scope unless a verifier both scopes (`in_scope: true`) and verifies it. Placeholder `gc-fy2627-p5-09` is TEST-ONLY.
- **No filing / reconciliation / recalculation authorized:** no Form 16/24Q filing, no ECR/ESI/PT remittance, no payroll recalculation on FY26-27 values is authorized by this package.
- **FY25-26 frozen:** `in-standard.json` v1.0.0 (`verified`, 2025-04-01–2026-03-31) stays byte-identical; no values invented; engine refusal (`rule_pack_not_verified`) must not be bypassed.
- **No approvals, no activation:** this handover grants none; all 12 items remain PENDING until the artifacts in §1 are filed.
