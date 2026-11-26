# Statutory Review Package — For the Qualified Reviewer (Technical Evidence, Not Advice)

**This package makes no legal conclusions. Every external-law determination below is phrased as "requires qualified reviewer" with the precise question. Nothing here authorises filing, payment, or FY-pack alteration.**

Base SHA `d80c0cd7f350be4be08b768d9a05573ef41a628f`; full inventory in `india-statutory-adjudication.md`.

## 1. Per-rule status

| Rule | Status | Evidence |
|------|--------|----------|
| TDS §115BAC bands / std deduction / §87A rebate | Implemented + tested | adjudication §1 rows 1–3, §2 (502 tests), §3 Case A |
| EPF EE/ER 12% + ₹15k ceiling; ESI 0.75/3.25% + ₹21k skip | Implemented + tested | rows 4–6, §3 Cases B/C, ESI edge golden cases |
| PT KA/MH/TN/TG/WB | Implemented + tested (5 states only) | row 7; filings gate `filings.py:37` |
| Filings 24Q/Form16/PF-ECR/ESI/PT (generators, verified-gate) | Implemented + tested | row 11; `india_payroll_final` 80/80 |
| Gratuity / Bonus / LWF | Skeleton, out-of-scope/info-only, emits nothing | rows 8–10; `in_scope: false` |
| FY26-27 pack | Skeleton, engine refuses | row 13 |
| Cess 4%, EPS split, marginal relief, MH-Feb/cap, TN half-yearly, old regime, surcharge, Basic+DA split | Absent from calculation | row 14 + §1 ABSENT list |

## 2. Applicability matrix — FROM THE CODE (everything else NOT IMPLEMENTED)

- Jurisdictions: **IN only** (`jurisdiction.country: IN`; resolver + loader verified-only).
- Employee categories: code distinguishes **none** — no age/senior, gender, establishment-size, wage-band (other than ESI limit), contractor, or exempt-category logic. Golden cases prove senior(62) ≡ young(25) byte-identical (new-regime behaviour as encoded).
- States: **KA, MH, TN, TG, WB** PT only. All other states/UTs: no table → PT zero, no line (silent, not an error).
- Regimes: **new regime only**; old-regime slabs absent. Frequencies: **monthly only**.

## 3. Open interpretation questions (requires qualified reviewer — no technical answer given)

- **Q1 (cess):** pack `source.notes` says 4% health-cess applied as surcharge; no cess table/code exists and golden cases expect pre-cess figures. Question: must v1.1 add a cess table + engine surcharge, or must the notes sentence be deleted?
- **Q2 (marginal relief):** rebate is cliff-edge at taxable ₹1,00,000/mo. Question: does the applicable Finance Act require marginal relief just above ₹12L/yr, and if so with what formula?
- **Q3 (MH PT):** flat ₹200/mo encoded. Question: are February ₹300 and the ₹2,500 annual cap legally required in-year?
- **Q4 (EPS split):** employer PF flat 12%. Question: must the payslip/ECR split 8.33% EPS (≤₹1,250) vs EPF remainder?
- **Q5 (TN PT):** collapsed to ₹0/₹208.50 at ₹25,000. Question: what is the correct monthly equivalent of the half-yearly schedule?
- **Q6 (WB PT):** 10 rows transcribed. Question: confirm each bound/amount against the governing notification.
- **Q7 (wage base):** PF/ESI base = full gross (single salary field). Question: is a Basic+DA split mandatory before production use?
- **Q8 (gratuity/bonus/LWF activation):** currently inert by design. Question: confirm they must STAY inert until a separately authorised, verified slice.
- **Q9 (FY26-27):** skeleton all-zero. Question: transcribe + verify Finance Act 2026 instruments before 2026-04-01 or confirm IN payroll must refuse post-2026-03-31.
- **Q10 (filings):** generators emit text/CSV from stored slips; no schema validation against department portals, no submission. Question: confirm these outputs are drafts pending reviewer sign-off, not filings.

## 4. Sign-off template (fields only — no appointment made)

- Reviewer full legal name: ___
- Suggested qualification holds (recommendation only): ___ (suggest reviewer holds: tax — Chartered Accountant / tax counsel for Q1–Q2; labour-law — employment counsel / PF-ESI consultant for Q4, Q7–Q8; state-PT practitioner for Q3, Q5–Q6; statutory auditor for Q10; FY26-27 Finance Act verifier for Q9)
- Scope reviewed (pack version + content SHA): ___
- Determination per Q1–Q10 (accept / change-required + ticket): ___
- Test evidence re-run (command + result): ___
- Verification fields to set (`verified_by_name/role/on`, `source_document_reference`, `golden_case_set_id`): ___
- Signature + date: ___

## 5. Test evidence refs

`india_payroll` 114/114 · `india_payroll_final` 80/80 · `payroll` 251/251 · `payroll_golden_p5` 27/27 · `app/rules` pytest 30/30 — total **502 passed, 0 failed**; 3 hand-computed synthetic cases (TDS/EPF-ESI/MH-PT) MATCH verbatim (adjudication §3). Synthetic data only; no real PAN/UAN/ESI numbers used.
