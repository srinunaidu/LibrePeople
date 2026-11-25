# Feature: india-payroll-slices-3-4

## Goal
Wire India fields through the payroll run lifecycle and ship India payslip/reports UI, gated on `pending_verification` and limited to monthly / new-regime / KA,MH,TN,TG,WB, without changing pack rates or engine bands.

## Base
Branch `feat/india-payroll-slices-1-2` (d103d50→6b18340→bc24c47). Continue on it; do not merge from main. Constraints: monthly only, new-regime only, top-5 PT states; pack `in-standard.json` stays `pending_verification`.

## Acceptance criteria

### Slice 3 — india-payroll-run-wiring (lands first)
- AC-11 [gate UI]: `GET /payroll/runs/{id}` detail and create-run surface show jurisdiction `IN` + pack status `pending_verification` badge; **Process** is disabled with message "configurable calculation — pending verification, cannot calculate" and explains the 409 `rule_pack_not_verified` path (docs/PAYROLL.md §3.3). Dry-run also blocked. US `US` runs behave unchanged.
- AC-12 [pt_state wiring]: Selecting `pt_state` KA/MH/TN/TG/WB on `employee_pay_profiles` (PayrollSetup + employee edit) persists; `_calculate_payslips(db,run,u)` loads `profile.pt_state`, passes `pt_state=` to `calculate_payslip_from_pack`; engine emits `PT_{STATE}` deduction from `pt_{state}` table; line serialised to `pay_slips.deductions_json` with `rule_id=PT_{STATE}` and `input_source=rule_pack:pt_{state}:CODE`. payslip detail renders it. No pt_state → no line, no regression for US.
- AC-13 [PAN/IFSC/bank surfacing]: Employees API exposes `pan_number/ifsc_code/pf_uan/esi_number` (read; masked PAN in list view `***1234F`), stored on `employees`; pay-profile bank account unchanged. Payslip header shows IFSC/account "on file" (never raw value in DOM, same as bank_account today). Export uses raw value server-side only.
- AC-14 [statutory lines visible]: After verification-flip in memory, a calculated IN run payslips show earnings `BASIC` + deductions `TAX_*`, `REBATE_87A` (negative), `PF_EE/ESI_EE`, `PT_*`, employer `PF_ER/ESI_ER` via existing `PayslipDetail` (earnings_json/deductions_json/employer_contributions). Amounts match golden cases; reconciliation `matched=true`.
- AC-15 [NEFT/RTGS export]: `POST /payroll/runs/{id}/payment-file` gains `?format=nacha|neft` (default `nacha` for backwards compat). `nacha` keeps current pipe format (line 301-322 payroll.py). `neft` emits NEFT/RTGS per docs/PAYROLL.md: header `NEFT` + `RUN_ID/CURRENCY/TOTAL_NET`, rows `beneficiary_name|account_number|ifsc_code|net|currency|reference|pf_uan` sourced from `employees`+`employee_pay_profiles`; if `jurisdiction==IN` and `?format` absent, auto-select `neft`. Only `Approved` runs; 409 otherwise. Filename `payroll_run_{id}_neft.txt`.

### Slice 4 — india-payslip-reports
- AC-16 [payslip PDF/template]: `GET /payroll/payslips/{id}/pdf` (or `?format=pdf`) renders India statutory breakdown (gross, TDS bands+rebate, PF/ESI EE/ER, PT) with watermark "configurable calculation — pending_verification — not statutory/filing-ready" when pack status pending; `verified` shows pack `in-standard v1.0.0`. Same data as deductions_json; not recomputed in browser. US pack PDF unchanged (no PT/TDS lines).
- AC-17 [payroll history]: Runs list / detail show `rule_pack_id/version/jurisdiction/currency` lineage per run; India monthly runs filterable; history entry links to recon + export artifact.
- AC-18 [compliance reports]: `GET /reports/payroll?jurisdiction=IN&period=YYYY-MM` (reuse `backend/app/api/v1/endpoints/reports.py`) adds India slices: Payroll Register (all payslips with statutory columns), TDS liability (tax+rebate), PF/ESI summary (EE/ER and ceilings), PT by state. Requires verified pack to generate; pending shows `rule_pack_not_verified` gate. Unverified export refused like §3.3.
- AC-19 [pending gate never bypassed]: No UI path calls `process` when resolver says `is_verified==false`; backend loader/engine still refuse (`_record_refusal` + 409). No new migration, no pack rate change, no engine band tweak to make pending pass.
- AC-20 [no US regression]: `bash ci/run_backend_tests.sh payroll` + `india_payroll_test_suite.py` green; US `us-standard-verified.json` output byte-identical (PT/India branches not taken).

## Non-goals
No new statutory rates, no engine band logic change, no migration 0030 edit, no deduction of gratuity, no 12L marginal relief, no multi-frequency or old-regime support, no bank-detail encryption change, no hash-chain audit beyond existing `record_audit`.

## Data flow (authoritative)
- **pt_state:** `PayrollSetup.tsx` Select `pt_state` (KA/MH/TN/TG/WB, nullable) → `POST /payroll/pay-profiles` (`EmployeePayProfileCreate` add optional `pt_state`) → `employee_pay_profiles.pt_state` (CK `pt_state IN (...)`) → `backend/app/api/v1/endpoints/payroll.py:_calculate_payslips:734` loads profile → `engine.calculate_payslip_from_pack(pt_state=profile.pt_state)` → `calculate_professional_tax(ctx)` reads `pack.get_rate_table(f"pt_{state.lower()}")`, picks entry where `gross∈[value,max_value)` (open-ended last) → `ctx.add_deduction(f"PT_{STATE}", ..., amount=entry.rate)` → `_lines_as_json` → `pay_slips.deductions_json / inputs_json` → `frontend/src/pages/payroll/shared.tsx:PayslipDetail` parses and renders PT line like other deductions.
- **PAN/IFSC/bank:** `frontend/src/pages/*` employee form (reuse `employees.py` schema, add optional `pan_number/ifsc_code/pf_uan/esi_number`) → `employees` table (CHECKs from slice1) → payroll run resolves employee via `db.get(Employee, slip.employee_id)` and `EmployeePayProfile`; pseudonymised in UI, raw only in server export.
- **NEFT vs NACHA:** Today `payment_file()` at `payroll.py:268` builds `PAYMENT_FILE` pipe lines with `bank_account` only. Slice 3 branches: `format=query param` (or jurisdiction sniff) → if `neft`: header `NEFT` + IFSC column, row `slip.employee_id | employee.employee_id | bank_account | ifsc_code | net | currency | run.id | pf_uan`; `nacha` path unchanged. Plugs into same `POST /runs/{id}/payment-file` route; frontend `BankExport.tsx` / `PayRunDetail.tsx` "Download NEFT file" calls it with `?format=neft` + blob download.

## Files to touch
- `frontend/src/pages/payroll/PayrollSetup.tsx:70-80,210-245,540-650` — add pt_state Select to profile form, POST with pt_state, show "On file" for new fields; handle 409 pending message.
- `frontend/src/pages/payroll/PayRuns.tsx` + `PayRunDetail.tsx:174-210,340-412,490-556` — jurisdiction IN badge, pending-verification Alert, disable Process when `rule_pack_status==pending`, wire `?format=neft` download button, guard dry-run.
- `frontend/src/pages/payroll/shared.tsx:115-242` — PayslipDetail already renders earnings/deductions/employer_contributions; add India statutory grouping header when `PT_`/`TAX_`/`REBATE_87A` present, watermark prop `packStatus`.
- `frontend/src/pages/admin/JurisdictionRules.tsx:58-132` — add `IN` to `JURISDICTION_OPTIONS`, show `in-standard` status `pending_verification` with verification checklist link.
- `frontend/src/lib/api.ts:20-60` + `frontend/src/types.ts` — add `EmployeePayProfile` `pt_state` + employee India fields to types; api helpers for `payment-file?format=`.
- `backend/app/api/v1/endpoints/payroll.py:88-142,268-330,635-828` — extend `EmployeePayProfileCreate/Out` to carry `pt_state` (thin schema passthrough), plumb `pt_state` in `_calculate_payslips`, branch `payment_file()` on `?format` + jurisdiction.
- `backend/app/schemas/payroll.py:52-67` — add optional `pt_state: str|None` with validator `in KA,MH,TN,TG,WB`.
- `frontend/src/pages/admin/BankExport.tsx:13-80` — add format toggle `NACHA/NEFT`, call `POST /payroll/runs/{id}/payment-file?format=neft` when IN.
- Slice 4 adds: `backend/app/api/v1/endpoints/reports.py` + `frontend/src/pages/admin/ComplianceCenter.tsx` or `reports/payroll` — payroll register/TDS/PF-ESI/PT reports (reuse `build_pay_run_reconciliation`).

## Files NOT to touch
- `backend/rule_packs/in-standard.json` rates/thresholds/PT tables, `backend/rule_packs/us-standard-verified.json`, `backend/app/rules/engine.py` bands/ceilings logic, `backend/app/rules/loader.py` verification gate, `backend/migrations/versions/0030_india_employee_fields.py`, `backend/app/rules/money.py`, `backend/app/rules/reconciliation.py` logic (read-only use), `backend/contracts/rules/rule-pack.schema.json`.

## Step-by-step build plan
1. Slice3 backend schema passthrough: add `pt_state?: string` to `EmployeePayProfileCreate/Out` in `schemas/payroll.py` + return it in `endpoints/payroll.py` list/get/create (no model change, column exists).
2. Wire `_calculate_payslips`: fetch `profile.pt_state`, pass to `calculate_payslip_from_pack(pt_state=...)`; keep `tax_regime` untouched (new only). Verify US path: `pt_state=None` → no PT line.
3. Branch `payment_file(run_id, format?: str)`: query param `format`; default `nacha` unless `run.jurisdiction==IN` then `neft`; implement NEFT rows with `ifsc_code` + `bank_account` + `pf_uan`; keep NACHA bytes identical (snapshot test).
4. Frontend Slice3: PayrollSetup pt_state select + error mapping; PayRunDetail gate Alert + disable Process + show `rule_pack_not_verified` details; shared PayslipDetail grouping (no new math).
5. Manual golden-path: create `period(IN, pay_date 2025-10-01)` → `run(jurisdiction=IN,currency=INR)` → Process → expect 409 pending; flip pack status in memory for local verify → Process → check `deductions_json` contains `PT_KA` etc.
6. Slice4 (depends Slice3): add `GET /payroll/payslips/{id}/pdf` stub rendering `PayslipDetail` to PDF with watermark + pack version; add reports endpoint filters by jurisdiction; frontend ComplianceCenter/Reports page tables for the four India reports.
7. Tests: extend `india_payroll_test_suite.py` or new `india_payroll_slices_3_4_suite.py` for pt_state→PT line, NEFT header, gate 409; add frontend vitest for gate/PayslipDetail.

## Risks / edge cases
- PT at boundary (e.g. gross==25000 KA): engine uses `pt_base < lower` / `>= upper`; match schedule semantics exactly; add boundary unit test.
- IFSC fifth-char `0` already CHECKed (slice1) but export must blank-out when null → row has empty column, not crash.
- Pack pending: never loosen `is_verified()` to make UI pass; UI gate is cosmetic, backend 409 is the real gate.
- Currency: IN runs are `INR` only; mismatch with profile base handled as before (no conversion).
- Employer PF 12% flat is v1 simplification — report it as-is, note checklist in PDF footer.
- PAN regex CHECK must remain dialect-portable substr form.

## Test command
```bash
bash ci/run_backend_tests.sh india && bash ci/run_backend_tests.sh payroll && bash ci/run_backend_tests.sh migration
cd frontend && npm run verify && npm run test:unit
# manual: create IN run → expect 409 pending; US run processes; NEFT download header starts "NEFT"
```
