# Feature: india-payroll-ui-polish

## Goal
Wire shipped backend `GET/POST /payroll/runs/{id}/fnf` and `GET /reports/filings/{type}` to frontend tabs, closing AC-31 UI gap; pack stays `pending_verification`.

## Acceptance criteria
1. AC-33 F&F Settlement tab in `PayRunDetail` — renders when `run.jurisdiction==IN` (or all runs with IN badge): calls `GET /payroll/runs/{id}/fnf?employee_id=&notice_days=` (+ `POST` preview), displays `notice_pay`, `leave_encashment`, `gratuity_payable` (=0 if tenure<5yr, >0 if ≥5yr), `lop_recovery`, `bonus_pro_rata`, `lwf_amount`, `net_settlement`, `tenure_years`, `basic_pct`/`Basic+DA` split; selects payslip employee via dropdown from `GET /payroll/payslips?pay_run_id=`; `notice_days` input triggers POST preview.
2. AC-34 Filings tabs in `ComplianceCenter` — `Payroll IN` gains sub-tabs/select for 5 types: `24q`/`form16_annual`/`pf_ecr`/`esi_return`/`pt_challan` (MH/KA/TN/TG/WB). Period input `YYYY-MM` (YYYY for Form16) → calls `GET /reports/filings/{type}?jurisdiction=IN&period=&state=`; renders returned txt as table; PT state outside 5 shows 422 validation message.
3. AC-35 pending_verification gate — both tabs show amber banner `pending_verification — not statutory/filing-ready` while `resolve_rule_pack` pending; on 409 `rule_pack_not_verified` display `errorMessage` + `rule_pack_not_verified` gate text (same as slice-4 `payroll-in` tab), no table/data; banner reuses `PayslipDetail packStatus` watermark pattern.
4. AC-36 Download — each filing tab has `Download IN_{TYPE}_{PERIOD}.txt` (TYPE upper e.g. `24Q_QUARTERLY`, `PT_CHALLAN_KA`) via blob `Content-Disposition`, same naming as `filings.py:329`; PT filename includes state suffix when state selected; period validation (422) blocks fetch before 409.
5. AC-37 Reuse & scope — reuse `shared.tsx:PayslipDetail` stat-line pattern and `ComplianceCenter.tsx:94-115` payroll-in state/Alert structure; add only frontend types in `types/index.ts` (FnfSettlement) and helpers in `lib/api.ts` if needed; no backend file touched; `npm run typecheck` passes.

## Non-goals
- No backend changes: `engine.py`, `money.py`, `loader.py`, `in-standard.json`, `payroll.py`/`filings.py`/`reports.py` endpoints, migrations `0030-0032`, `DB_SCHEMA.sql`, `TenantContext`/`ApiError` contracts.
- No verified flip on disk, no rate edits, no new backend tests, no currency/slippage change, no workforce-core wiring.

## Files to touch
- `frontend/src/pages/payroll/PayRunDetail.tsx:39,67,257-639` — add F&F tab state, fetch (`GET/POST /payroll/runs/{id}/fnf`), employee selector, notice_days input, settlement grid, pending banner; reuse `PayslipDetail` below.
- `frontend/src/pages/admin/ComplianceCenter.tsx:70,94-115,245-560` — add filings sub-tab state (`filingType`, `filingPeriod`, `filingState`, `filingData/error/loading`), 5-type Tabs/Select, period inputs, `GET /reports/filings/{type}` calls, 409/422 Alert handling, tables + download handler.
- `frontend/src/pages/payroll/shared.tsx:116-257` — optionally extract `FnfDetail` or extend `PayslipDetail` stat grid for F&F lines; no money logic.
- `frontend/src/types/index.ts:658-699` — add `FnfSettlement` interface matching `fnf_calculator.py:301-326` (`notice_pay`, `gratuity_payable`, etc., string Decimals + `gratuity_eligible` bool).
- `frontend/src/lib/api.ts:1-206` — add typed `getFnf`/`postFnf`/`getFiling` helpers wrapping `api.get` with `errorMessage` (or inline); export `errorMessage` reuse.
- `frontend/src/pages/payroll/PayRunDetail.test.tsx` (new) + `frontend/src/pages/admin/ComplianceCenter.test.tsx` (extend) — Vitest for AC-33..36.

## Files not to touch
- `backend/app/rules/engine.py`, `backend/app/rules/money.py`, `backend/app/rules/loader.py`, `backend/rule_packs/in-standard.json`, `backend/rule_packs/us-standard-verified.json`
- `backend/app/api/v1/endpoints/payroll.py`, `backend/app/api/v1/endpoints/filings.py`, `backend/app/api/v1/endpoints/reports.py`, `backend/app/services/fnf_calculator.py`, `backend/app/core/encryption.py`
- `backend/migrations/versions/0030*.py`, `0031*.py`, `0032*.py`, `backend/app/models/**`, `docs/DB_SCHEMA.sql`, `contracts/**`

## Step-by-step build plan
1. Add `FnfSettlement` type to `types/index.ts` mirroring `settlement_to_dict`; add optional `getFnf` helper in `lib/api.ts`.
2. In `PayRunDetail.tsx` add tab state (`activeSection` or `Tabs`): existing Payslips/Reconciliation + new `F&F Settlement`; fetch payslips for employee dropdown; on select call `GET /runs/{id}/fnf?employee_id=`; render banner if `isINPending` (reuse line 382 Alert) + settlement grid (money, tenure, basic_pct, gratuity 0 vs >0 copy); add `notice_days` number input + `Preview` button → `POST /runs/{id}/fnf?employee_id=&notice_days=`.
3. In `ComplianceCenter.tsx` inside `payroll-in` TabsContent add inner `Tabs`/`Select` for filingType; add `filingPeriod` (`YYYY-MM`) input, `filingState` select (KA/MH/TN/TG/WB); `Load` → `GET /reports/filings/{type}?jurisdiction=IN&period=&state=`; on 409 show `Alert` with `data-testid="filing-pending"` + `rule_pack_not_verified`; on 422 show `PT state must be one of…`; else render table (split txt lines by comma) + `Download` button creating blob `IN_{TYPE}_{PERIOD}.txt`.
4. Wire download: `new Blob([content],{type:"text/plain"})`, anchor `IN_${type.toUpperCase()}_${period}.txt` (PT append `_${state}`), `URL.createObjectURL`.
5. Add Vitest: `PayRunDetail.test.tsx` — mock `api.get` 409 pending banner, 200 settlement with gratuity 0/→5yr, POST preview; `ComplianceCenter.test.tsx` — mock filings 409 gate, 200 table, 422 state error, download filename assertion.
6. Run `cd frontend && npm run typecheck && npm run test:unit` — fix types; add `data-testid="fnf-settlement"` / `"filing-pending"` for e2e.
7. Manual check: `POST /payroll/runs/{id}/fnf` in pending pack still gates? (F&F currently not gated—confirm 200 with gratuity). Filings `period=2025-10` pending → 409 banner, after in-memory verified → 200 (use existing `india_payroll_final_test_suite.py` in-memory flip as reference, no disk edit).

## Risks / edge cases
- F&F gratuity boundary: `<5yr → 0.00, ≥5yr → >0` (tenure from hire_date vs pay_date, 365.25 divisor); do not recompute in browser.
- `notice_days` NaN/empty → send 0 (backend defaults `Decimal("0")`); UI caps min 0.
- Filings `period` = `YYYY-MM-DD` rejected 422 (regex `^\d{4}-\d{2}$`); Form16 accepts `YYYY` or `YYYY-MM` (backend normalizes to year); show 422 message verbatim.
- PT filing without state → `ALL` (backend shows header `state ALL`); unknown state → 422 `pt state must be one of …`.
- Pack stays `pending_verification` — banner visible always; backend 409 is truth; never flip `in-standard.json`.
- Employee without payslip → 404 `payslip for employee … not found` → show `errorMessage` in Alert.

## Test command
```bash
cd frontend && npm run typecheck && npm run test:unit
# subset verify (no full build needed): npm run check:api-paths && npm run check:routes
# manual 409→verify: create IN period 2025-10 → run IN/INR → PayRunDetail F&F tab 200, ComplianceCenter filings 2025-10 → 409 banner → in-memory verified (or verified pack fixture) → 200 + download IN_24Q_QUARTERLY_2025-10.txt
```
