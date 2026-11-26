# India Statutory Adjudication — What the Code ACTUALLY Implements (Technical Record)

**Not professional advice. Technical inventory only — every external-law question is routed to a qualified reviewer in the companion review package.**

- Base SHA: `d80c0cd7f350be4be08b768d9a05573ef41a628f` (branch `agent/legal/statutory-evidence`)
- Scope: `backend/rule_packs/in-standard.json` (FY25-26, v1.0.0, `status: verified`) + `backend/rule_packs/in-standard-fy2627-skeleton.json` (v0.1.0, `status: pending_verification`, all rates 0) + consuming engine `backend/app/rules/engine.py` + filings `backend/app/api/v1/endpoints/filings.py`.
- Deprecated module `backend/app/services/payroll_engine.py:1-16` is NOT on any pay-run path (flat-% withholding only, no rule-pack logic). The pack-driven engine is `app/rules/engine.py::calculate_payslip_from_pack` (`engine.py:740`).

## 1. Rule inventory (pack → engine, with file:line)

| # | Rule | Pack location | Engine location | Verdict |
|---|------|---------------|-----------------|---------|
| 1 | TDS slabs §115BAC new regime, 7 monthly bands 0–30% | `in-standard.json:29-97` | `engine.py:253-321` (`calculate_tax`, `IN_BAND_0..6`) | IMPLEMENTED+TESTED |
| 2 | Standard deduction ₹6,250/mo | `in-standard.json:102-107` | `engine.py:302-320` | IMPLEMENTED+TESTED |
| 3 | Rebate §87A ≤₹1,00,000 taxable, max ₹5,000 | `in-standard.json:110-126` | `engine.py:322-345` (negative `REBATE_87A` line) | IMPLEMENTED+TESTED |
| 4 | EPF EE 12%, ceiling ₹15,000 (cap base) | `in-standard.json:131-137,168-173` | `engine.py:391-458` | IMPLEMENTED+TESTED |
| 5 | EPF ER 12% flat on same ceiling | `in-standard.json:146-155` | `engine.py:437-457` (`PF_ER`) | IMPLEMENTED+TESTED (flat; EPS 8.33% split ABSENT — open question Q4) |
| 6 | ESI EE 0.75% / ER 3.25%, skip if base > ₹21,000 | `in-standard.json:138-144,156-163,174-180` | `engine.py:391-458` (limit-skip, not cap) | IMPLEMENTED+TESTED incl. 21000.00/21000.01 edge |
| 7 | PT KA/MH/TN/TG/WB schedules (flat `rate`) | `in-standard.json:182-373` | `engine.py:668-716` (`PT_{STATE}`) | IMPLEMENTED+TESTED (5 states; all other states ABSENT — no table → zero, no line) |
| 8 | Gratuity 4.81%/5yr | `in-standard.json:374-404`, **`in_scope: false` (:377)** | `engine.py:530-567` (triple gate: table + `in_scope` + verified + tenure≥5) | SKELETON — pack out of scope ⇒ engine emits nothing. Never activated this slice. |
| 9 | Bonus 8.33–20%/₹21k limit | `in-standard.json:405-428` | `engine.py:569-583` (returns ZERO, no line) | SKELETON (info-only stub) |
| 10 | LWF 5-state stubs | `in-standard.json:429-464` | `engine.py:585-596` (returns ZERO, no deduction) | SKELETON (info-only stub) |
| 11 | Filings: 24Q / Form 16 / PF-ECR / ESI / PT-challan from stored slips, verified-pack gate | — | `filings.py:49-63` (409 gate), `:116-260` (5 generators), `:37` (5 PT states) | IMPLEMENTED+TESTED (generators only; no filing/submission logic — ABSENT by design) |
| 12 | Overtime IN 9h-day/48h-week/2x; leave casual 12/earned 18; reporting obligations; pay-day rule | `in-standard.json:466-557` | `engine.py:459-528` | IMPLEMENTED+TESTED (via payroll suites) |
| 13 | FY26-27 skeleton (all `rate`/`value` 0, thresholds null, leave 0, 14 placeholder golden cases) | `in-standard-fy2627-skeleton.json` (status `pending_verification`, `verification: null`) | resolver refuses non-verified (`resolver.py:303-351`); `load_rule_pack_for_date` verified-only (`loader.py:574-596`) | SKELETON — must not drive calculation until transcribed + verified |
| 14 | Health-cess/surcharge 4% | pack `source.notes` sentence ONLY (`in-standard.json:26`); **no rate table, no engine code** (`grep cess → engine: none`) | — | ABSENT from calculation. Golden cases expect pre-cess figures → engine matches pack tables. Notes-vs-code inconsistency → open question Q1. NOT a pack-vs-engine defect. |

Old-regime slabs, surcharge slabs, marginal relief above ₹12L, MH Feb-₹300/₹2,500 cap, TN half-yearly schedule, EPS split, Basic+DA salary split, Form 24Q e-file schema validation, challan payment: all ABSENT (no code).

## 2. Test evidence (exact counts, this branch)

| Suite | Result |
|-------|--------|
| `backend/india_payroll_test_suite.py` | **114 passed, 0 failed** |
| `backend/india_payroll_final_test_suite.py` | **80 passed, 0 failed** |
| `backend/payroll_test_suite.py` | **251 passed, 0 failed** |
| `backend/payroll_golden_p5_test_suite.py` | **27 passed, 0 failed** |
| `backend/app/rules` (pytest: determinism, display-parity, reconciliation) | **30 passed** |
| **Total** | **502 passed, 0 failed** |

## 3. Hand-computed verification (from pack JSON, synthetic data, no external law)

Method: taxable = gross − 6,250; band widths from `in-standard.json:33-95`; PF = 12% × min(gross,15000); ESI skipped iff gross > 21000; PT from schedule rows.

- **Case A — TDS multi-band, gross ₹1,50,000, no PT.** Hand: taxable 1,43,750 → B1 33,333.34×5% = 1,666.67; B2 33,333.33×10% = 3,333.33; B3 33,333.33×15% = 5,000.00; B4 (1,43,750−1,33,333.33)×20% = 2,083.33 → tax 12,083.33 (no rebate, >1,00,000) + PF 1,800 = deductions **13,883.33**, net **1,36,116.67**. Engine: `gross 150000.00 deduct 13883.33 net 136116.67` → **MATCH verbatim**.
- **Case B — EPF/ESI below ceilings, gross ₹12,000.** Hand: taxable 5,750 → tax 0; PF EE/ER 12%×12,000 = **1,440/1,440**; ESI EE 0.75% = **90**, ER 3.25% = **390**; deductions **1,530**, net **10,470**. Engine: `deduct 1530.00 net 10470.00 ee 1530.00 er 1830.00` → **MATCH verbatim**.
- **Case C — MH PT, gross ₹22,000.** Hand: taxable 15,750 → tax 0; PF capped 1,800/1,800; ESI skipped (22,000>21,000); PT_MH (≥10,000) = **200**; deductions **2,000**, net **20,000**. Engine: `deduct 2000.00 net 20000.00` with `PT_MH 200.00` → **MATCH verbatim**.

## 4. Defect verdict

**NONE FOUND** — no case where hand-computed pack-table value ≠ engine output. Per instructions no code was changed and no fix attempted. The single inconsistency (cess sentence in `source.notes` vs no cess table/code) is a documentation-vs-implementation gap, recorded as review question Q1, not a calculation defect: the engine faithfully reproduces the pack's rate tables and golden cases.
