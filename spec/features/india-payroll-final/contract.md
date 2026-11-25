# Feature: india-payroll-final

## Goal
Complete India payroll with statutory accruals + Full & Final (slice 5) and hardened filings/identity/payments (slice 6) while pack stays `pending_verification` and monthly/new-regime/top-5 PT scope unchanged.

## Base
Branch `feat/india-payroll-slices-1-2` @2de4bdc → slices 1-4 PASS (0030, `in-standard.json` pending, guarded engine, run wiring NEFT, PDF + 4 gated reports). Continue on it. Do not merge main. Keep `pending_verification` until human verifies.

## Acceptance criteria

### Slice 5 — india-statutory-accruals-fnf (lands first)
- AC-21 [gratuity]: `in-standard.json` adds table `gratuity_accrual` (values: 4.81% = 15/26/12, notes cite Payment of Gratuity Act 1972 §4, 5yr eligibility). Engine `calculate_gratuity_accrual(ctx, tenure_years)` guarded — emits `GRATUITY_ACCRUAL` employer_contribution only when table exists and tenure >=5; else no line. Golden case `tenure 5yr vs 4.9yr` proves boundary. US pack → no table → byte-identical.
- AC-22 [bonus/LWF stubs]: `in-standard.json` adds `bonus_act` (values: 8.33% min, 20% max, eligibility 21k) and `lwf_state` (values per MH/KA/TN/TG/WB minimal flat stubs). Engine stubs read but do NOT emit deductions yet — only stored for reports/F&F reference (`BONUS_ACCRUAL`/`LWF_*` info lines when enabled). No rate change to existing PT/TDS/PF/ESI tables.
- AC-23 [overtime India]: `overtime` block gains India daily/weekly thresholds from Shops & Establishments (e.g. 9h/48h, premium 2x) as `overtime.rules` guarded — only applied when `jurisdiction==IN`; engine `calculate_overtime` must read pack thresholds (not hard-coded) and cap correctly. US overtime unchanged.
- AC-24 [leave encashment & LOP/arrears]: Engine handles `leave_encashment` (encashable leave x daily Basic+DA / taxable) and `LOP` arrears via `calculate_leave_deduction` + new `calculate_arrears(ctx, arrears_days, base_type)` guarded; arrears added as earning `ARREARS`, LOP as deduction `LOP`. Taxable includes encashment (block §10(10AA) minimal).
- AC-25 [Basic+DA split]: `EmployeePayProfile` gains `basic_pct` (default 40-50%, validated 0-100) + migration 0031 mirrors it. Engine flag `use_basic_da = basic_pct is not null`; PF base = `Basic+DA` when flagged else `gross` (existing). ESI base always gross. Pydantic schema adds optional `basic_pct`.
- AC-26 [Full & Final]: `POST /payroll/runs/{id}/fnf?employee_id=` or `backend/app/services/fnf_calculator.py::calculate_fnf(employee, period, pack, inputs)` returns structured settlement: `notice_pay`, `leave_encashment`, `gratuity_payable (if eligible)`, `lop_recovery`, `bonus_pro_rata`, `net_settlement`; reads from `deductions_json` accounting but does not mutate run. UI tab `F&F Settlement` renders it (read-only). No new money in engine outside guarded helpers.

### Slice 6 — india-filings-hardening
- AC-27 [filings]: `GET /reports/filings/{type}?jurisdiction=IN&period=YYYY-MM&state=XX` generators (5 endpoints or one with `type` param): `24q_quarterly`, `form16_annual`, `pf_ecr` (txt + challan), `esi_return`, `pt_challan` (per MH/KA/TN/TG/WB). Each streams txt/csv from `pay_slips.deductions_json/inputs_json` + employee fields — no engine recompute. PT filing validates state ∈5.
- AC-28 [identity]: Migration `0032` adds `employees.aadhaar_encrypted` Text nullable + `aadhaar_masked` String(14) + checks. Model `Employee.aadhaar_number` property decrypts via `app.core.encryption` (AES-GCM per docs/PAYROLL.md §9.3 pattern). API masks as `** **-****-1234` in list/detail; raw only for filings/neft server-side. Stubs `verify_pan/verify_uan/verify_esi` (external call stub returns `pending_verification`) + `Form 11`/`nominee` stubs stored as JSON.
- AC-29 [payments hardening]: `payment_file` adds validation layer before emitting NEFT/RTGS: `IFSC existence check stub` (regex + lookup dict), `account number` length 9-18 digits + checksum stub, `beneficiary_name` sanitization (strip `|`/`\\n`, max 100, ASCII). On failure → 422 with field errors. Field encryption at rest for `bank_account/ifsc_code/pan_number/aadhaar_encrypted` via same `app.core.encryption` helper; decrypt only in `payment_file`/filings. Existing `nacha` bytes unchanged when validation passes.
- AC-30 [India e2e journey]: New suite `backend/india_payroll_final_test_suite.py` e2e: create `period(IN, 2025-10-01)` → `run(jurisdiction=IN,currency=INR,period)` → dry-run `POST /runs/{id}/process?dry_run=true` → expect 409 `rule_pack_not_verified`; flip pack status in-memory to `verified` → re-process → assert `deductions_json` contains `PT_KA`, `TAX_*`, `PF_EE`; `GET /runs/{id}/reconciliation` `matched=true`; `POST /runs/{id}/payment-file?format=neft` starts `NEFT` + IFSC column; `GET /payslips/{id}/pdf` 200 contains watermark when pending else `in-standard v1.0.0`; `GET /reports/payroll?jurisdiction=IN&period=2025-10` 200 after gate.
- AC-31 [frontend]: Vitest + Playwright coverage for F&F tab and filings tabs (5 states): pending gate banner, PT line in PayslipDetail, NEFT validation errors, filing download naming `IN_{TYPE}_{PERIOD}.txt`.
- AC-32 [no regression]: `ci/run_backend_tests.sh` full green; `app/rules/test_determinism.py` + `test_reconciliation.py` green; US `us-standard-verified.json` output byte-identical.

## Non-goals
No `pending → verified` flip (pack stays pending). No monthly/new-regime/top-5 scope change. No hash-chain audit, no background job queue, no workforce-core wiring.

## Files to touch
- Create `backend/migrations/versions/0031_india_fnf_basic_da.py` (pt: `basic_pct` Numeric 5,2 nullable CHECK 0-100; follow 0030 idempotency pattern).
- Create `backend/migrations/versions/0032_india_aadhaar_encryption.py` (employees `aadhaar_encrypted` Text, `aadhaar_masked` String 14).
- Edit `backend/app/models/employee.py:90-122` — add `aadhaar_encrypted/_masked`, decrypt property, AADHAAR_CHECK `length=12 & GLOB [0-9]*` portable form.
- Edit `backend/app/models/payroll.py:58-86` — add `basic_pct` to `EmployeePayProfile`.
- Edit `backend/rule_packs/in-standard.json` — add `gratuity_accrual`, `bonus_act`, `lwf_state` tables; populate `overtime.rules` India values; `leave_types` encashable flag — no edit to existing rate values.
- Edit `backend/app/rules/engine.py:340-510` — add `calculate_gratuity_accrual`, `calculate_arrears`, extend `calculate_overtime`/`calculate_leave_deduction` guarded; Basic+DA branch on `basic_pct`.
- Create `backend/app/services/fnf_calculator.py` + `backend/app/api/v1/endpoints/filings.py` (5 generators) + `backend/app/core/encryption.py` (AES-GCM field helper per docs/PAYROLL.md §9.3).
- Edit `backend/app/api/v1/endpoints/payroll.py:268-384,688-828` — validation layer in `payment_file`, wire `pt_state`/`basic_pct`/`aadhaar` passthrough.
- Edit `backend/app/api/v1/endpoints/reports.py:178-460` — filings route, keep existing payroll reports gated.
- Create `backend/india_payroll_final_test_suite.py` + `backend/app/rules/test_india_fnf_filings.py`.
- Edit `ci/run_backend_tests.sh:57-60` — add `india_payroll_final_test_suite` after `india_payroll_test_suite`.
- Edit frontend: `frontend/src/pages/payroll/PayRunDetail.tsx`, `PayrollSetup.tsx`, `shared.tsx` (F&F tab, PT/bonus chips), `frontend/src/pages/admin/ComplianceCenter.tsx` (filings tabs), `frontend/src/lib/api.ts`, `frontend/src/types.ts`.

## Files not to touch
- `backend/rule_packs/us-standard-verified.json`, `backend/contracts/rules/rule-pack.schema.json`, `backend/app/rules/loader.py`, `backend/app/rules/money.py`, `backend/migrations/versions/0030_india_employee_fields.py`, existing PT/TDS/PF/ESI rate values in `in-standard.json` (only additions allowed).

## Data flow (authoritative)
- **Gratuity/F&F:** `PayrollPeriod.pay_date` -> `resolve_rule_pack(IN, pay_date)` -> `engine.calculate_payslip_from_pack(basic_pct=profile.basic_pct, pt_state, tenure_years)` -> guarded `calculate_gratuity_accrual` -> `_lines_as_json` -> `pay_slips.deductions_json/employer_contributions` -> `fnf_calculator.calculate_fnf` reads stored lines + `leave_encashment` -> frontend F&F tab renders no recompute.
- **Filings:** `GET /reports/filings/24q?period=YYYY-MM` -> gate `resolve_rule_pack` pending→409 else `db.query(PaySlip).join(PayRun)` by period -> parse `deductions_json` (TAX_*/REBATE_87A/PF_EE/ESI_EE/PT_*) -> emit txt (PF ECR spec `UAN|GROSS|EE|ER|WAGE`) -> stream Response.
- **Identity/NEFT:** `employees.aadhaar_encrypted` (AES-GCM) -> `Employee.aadhaar_number` decrypt -> API masks `** **1234`; `payment_file` decrypts `bank_account/ifsc_code/aadhaar` server-side only, validates IFSC stub + account checksum + name sanitization -> `NEFT` pipe rows `beneficiary|account|ifsc|net|currency|ref|pf_uan`.

## Step-by-step build plan
1. Slice 5 migration 0031: add `basic_pct` to `employee_pay_profiles` with catalog check; update `docs/DB_SCHEMA.sql` via `scripts/generate_db_schema.py`.
2. Extend `in-standard.json` with `gratuity_accrual/bonus_act/lwf_state` + overtime India rules (schema-valid, no existing values changed).
3. Engine: add `calculate_gratuity_accrual`, `calculate_arrears`, Basic+DA branch, gratuity/arrears unit tests; verify `run_golden_cases` still PASS for 11 cases (in-memory verified) + `pt_state None → no PT`.
4. Create `fnf_calculator.py` + API stub `GET /payroll/runs/{id}/fnf`; frontend F&F tab wired to it.
5. Slice 6 migration 0032: `aadhaar_encrypted/_masked`; create `app/core/encryption.py` (Fernet/AES-GCM key from `settings.SECRET_KEY`, versioned); model property + masking util.
6. Harden `payment_file`: validation helpers `validate_ifsc/account/name` + encryption decrypt layer; keep `nacha` snapshot identical.
7. Create `endpoints/filings.py`: 5 generators from stored JSON; register router in `app/main.py` (or `reports.py`).
8. Tests: add `india_payroll_final_test_suite.py` (e2e journey AC-30) + `test_india_fnf_filings.py` (unit); add frontend vitest for F&F + filings tabs (pending gate, PT_*, watermark).
9. Run full gate below; fix failures before hand-off.

## Risks / edge cases
- Gratuity 4.81% = `last_basic × 15/26 × years`; tenure <5 → 0 (eligibility); v1 ignores Basic+DA vs last-drawn nuance — note in pack `source.notes`.
- IFSC fifth char `0` + 11 length already enforced; filing export must handle null → empty column, not crash.
- Aadhaar 12-digit masked `** **-****-1234`, encrypted at rest; never log raw; stub verification always returns `pending_verification`.
- Pack stays `pending_verification` — UI gate cosmetic, backend 409 is truth; no test may flip file on disk, only in-memory.
- LWF/Bonus stubs must not affect net until verifier enables; document as checklist in `in-standard-VERIFICATION.md` addendum.
- Currency `INR` only for IN runs; Decimal arithmetic half-up via `money()` — no float.
- Timestamps: all `effective_from/to` are `YYYY-MM-DD` Asia/Kolkata; no slippage — filings `period` parsed as first-of-month.

## Test command
```bash
bash ci/run_backend_tests.sh india && bash ci/run_backend_tests.sh payroll && bash ci/run_backend_tests.sh migration
cd backend && .venv/bin/python -m pytest app/rules -q
cd frontend && npm run verify && npm run test:unit
# new e2e (requires backend running): cd backend && .venv/bin/python india_payroll_final_test_suite.py
# manual e2e: create period IN 2025-10-01 → run IN/INR → POST /runs/{id}/process expect 409 → in-memory verified → PT_KA line + NEFT header NEFT + PDF watermark + GET /reports/payroll?jurisdiction=IN&period=2025-10 200
```
