# Feature: fd-08-payroll-talent-ops

**Feature ID:** fd-08-payroll-talent-ops
**Contract path:** spec/features/fd-08-payroll-talent-ops/contract.md
**Tier:** Tier 2 (new behavior across multiple files — backend endpoint, frontend API client, CI config; tests required. Not a data model change — payroll models already exist.)

## Goal
Close the FD-08 gaps: add the missing GET /payroll/runs/{run_id} backend detail endpoint, add typed payroll API client functions to the frontend, run the payroll execution suite in CI, and ship a standalone payroll overview page at /platform/payroll/overview.

## Acceptance criteria

**AC-01** Backend — GET /api/v1/payroll/runs/{run_id} returns a single PayRun object (200) for an existing run and 404 with `not_found` for a missing run. The endpoint does not filter client-side; PayRunDetail.tsx may keep using its existing list-filter fallback until it is switched to this endpoint.

**AC-02** Frontend — frontend/src/lib/api.ts exports typed functions: listPayrollPeriods, listPayrollComponents, listPayrollProfiles, listPayrollRuns, getPayrollRun, createPayrollRun, processPayrollRun, approvePayrollRun, finalizePayrollRun, listPayrollPayslips, getPayrollPayslip, getPayrollReconciliation, getPayrollPaymentFile. Each function is typed against the existing row/out types (PayrollPeriodRow, PayComponentRow, PayProfileRow, PayRunRow, PaySlipRow, PayRunReconciliation) and no existing call site is required to change.

**AC-03** Backend — `payroll_execution_test_suite.py` is added to the SUITES list in ci/run_backend_tests.sh so `ci/run_backend_tests.sh payroll` runs both payroll_test_suite and payroll_execution_test_suite and both report PASS.

**AC-04** Frontend — a new standalone payroll overview page is reachable at /platform/payroll/overview. It shows run summary cards (headcount, gross, deductions, net), a recent-runs table, and quick actions (create run, view reconciliation). The existing /platform/payroll tab shell (Platform.tsx) is unchanged. PayrollLinks continues to link to /platform/payroll.

**AC-05** All changes are committed to main.

## Non-goals
- No database/model change: payroll models (PayRun, PaySlip, PayrollPeriod, PayComponent, EmployeePayProfile) already exist and are untouched.
- No change to existing payroll endpoints except the new GET /runs/{run_id} addition.
- No change to existing screens' behavior; PayRunDetail.tsx keeps its client-side list filter unless a follow-up switches it.
- No new auth/roles; the new endpoint and page reuse REPORTS_ROLES / ADMIN_ROLES exactly as the neighboring payroll endpoints do.
- No payment file generation, reconciliation engine, or payroll calc changes.

## Files to touch
- backend/app/api/v1/endpoints/payroll.py:145-147 — add `GET /runs/{run_id}` detail route immediately after `list_runs`, returning PayRunOut or `not_found(f"Pay run {run_id}")`.
- frontend/src/lib/api.ts — append typed payroll API client functions (see AC-02), reusing `api.get`/`api.post` and the existing row types from "@/types".
- frontend/src/App.tsx:215 — add route `<Route path="/platform/payroll/overview" element={<ProtectedRoute><PayrollOverview /></ProtectedRoute>} />` next to the existing /platform/payroll route.
- frontend/src/pages/payroll/PayrollOverview.tsx — new page: run summary cards, recent-runs table, quick actions (create run → navigate to /platform/payroll/runs; view reconciliation → navigate to the run's reconciliation via PayRunDetail or the runs page).
- ci/run_backend_tests.sh:37-75 — add `payroll_execution_test_suite` to the SUITES list, adjacent to `payroll_test_suite`.

## Files not to touch
- backend/app/models/payroll.py — models already exist; no schema change.
- backend/app/schemas/payroll.py — no new schema; reuse PayRunOut.
- frontend/src/pages/payroll/Platform.tsx — the /platform/payroll tab shell is unchanged.
- frontend/src/pages/payroll/PayRunDetail.tsx — keeps existing list-filter behavior; not required to switch to the new endpoint in this feature.
- frontend/src/pages/payroll/PayRuns.tsx, PayrollSetup.tsx, shared.tsx — unchanged.
- backend/payroll_test_suite.py — already in CI and passing; not modified.
- backend/payroll_execution_test_suite.py — already passing standalone; not modified, only registered in CI.

## Step-by-step build plan
1. Backend endpoint (AC-01): In backend/app/api/v1/endpoints/payroll.py, add a `get_run` function after `list_runs` (line 147) with route `@router.get("/runs/{run_id}", response_model=PayRunOut, operation_id="payrollGetRun")`, query `PayRun` by id, raise `not_found(f"Pay run {run_id}")` when absent, otherwise return the run. Require `require_roles(*REPORTS_ROLES)` like list_runs.
2. Backend CI registration (AC-03): In ci/run_backend_tests.sh, add `payroll_execution_test_suite` to the SUITES list right after `payroll_test_suite` (line 56).
3. Frontend API client (AC-02): In frontend/src/lib/api.ts, append the typed functions listed in AC-02, each calling `api.get`/`api.post` under `/payroll/...` and typed with the existing "@/types" row types. getPayrollRun hits `GET /payroll/runs/{run_id}`; getPayrollPaymentFile returns the raw text/attachment bytes. Export every function.
4. Frontend overview page (AC-04): Create frontend/src/pages/payroll/PayrollOverview.tsx with summary cards (headcount, gross, deductions, net aggregated from GET /payroll/runs), a recent-runs table, and quick-action buttons (create run navigates to /platform/payroll/runs; view reconciliation navigates into a run's detail). Reuse fmtDate, money, PayrollLinks from ./shared.
5. Frontend route (AC-04): In frontend/src/App.tsx, add the /platform/payroll/overview route next to the existing /platform/payroll route (line 215).
6. Run `npm run typecheck && npm run build` in frontend/; both must pass with no new errors.
7. Run `ci/run_backend_tests.sh payroll`; payroll_test_suite and payroll_execution_test_suite must both report PASS.
8. Commit all changes to main (AC-05).

## Risks / edge cases
- Route ordering in FastAPI: register GET /runs/{run_id} so it does not shadow the existing verb routes (/runs/{run_id}/process, /approve, /finalize, /payment-file, /reconciliation). FastAPI matches static sub-paths before parametric ones, so placement after list_runs is safe, but the new route must not be placed after the verb routes.
- 404 vs empty: GET /runs/{run_id} returns 404 for a missing id, never an empty list.
- Currency: PayRunOut carries no currency symbol; the frontend must not invent a "$" (documented convention in shared.tsx).
- Authentication: the new endpoint and page reuse the existing Bearer-token interceptor and role guards; no new auth surface.
- The payroll execution suite creates its own temp SQLite DB; registering it in CI must not collide with payroll_test_suite's DB (each suite removes ./*.db before running).

## Test command
Frontend: `npm run typecheck && npm run build` (run in frontend/)
Backend: `ci/run_backend_tests.sh payroll` (run from repo root; expects payroll_test_suite and payroll_execution_test_suite both PASS)
TypeScript check on new API functions: covered by `npm run typecheck` (tsc --noEmit) which type-checks frontend/src/lib/api.ts including the new payroll functions.
