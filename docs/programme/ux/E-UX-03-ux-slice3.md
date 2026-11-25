# E-UX-03 — UX honest-feedback slice 3

> Worktree: `/Users/srinivas/LLM/Workforce/lp-slice3-ux` · Branch: `slice3-ux-c3h5` · Base: `d8f7a3d`
> Scope: `frontend/src/pages/leave/LeaveLedger.tsx`, `frontend/src/pages/payroll/PayRunDetail.tsx`, `frontend/src/pages/payroll/shared.tsx`, `frontend/src/pages/onboarding/OnboardingConfig.tsx`, `frontend/src/lib/feedback-slice3.test.ts` (new), this doc.
> Zero of the 16 E-UX-01 frozen files touched (verified: `git diff --name-only` ∩ frozen list = ∅).
> Zero of the 101 E-UX-02 admin exclusives touched (verified: `git diff --name-only` ∩ admin list = ∅).

## What changed (4 UX pages + 1 shared util + new test)

### 1. Honest Alert feedback (slice-1/2 pattern, all pages with mutations)
- **PayRunDetail.tsx**: Three `toast.success()` calls (verb done, payment file download, payslip PDF) replaced with `setNotice()` + `<Alert tone="success">` rendered from `notice` state. Sonner import removed.
- Added `notice` state (string) and kept `actionError` for mutation failures — load-failure `error`/`RetryableAlert` channel reserved for reads (slice-1 Platform contract).
- Success notices set **after** `await load()` so the load reset cannot wipe them.
- **LeaveLedger.tsx**, **OnboardingConfig.tsx**: Read-only pages — no mutations, no success Alert needed. They already used `RetryableAlert` for load errors and `Alert tone="error"` for action errors (where applicable).
- **shared.tsx**: Utility file — no toasts, no sonner, no alerts.

### 2. API-enforced authz reflected in UI (already correct, verified)
- **LeaveLedger**: `WORKFORCE_ROLES` / `MANAGER_ROLES` / `REPORTS_ROLES` gates mirror `backend/app/api/v1/endpoints/leave.py`. Each section shows permission-denied `EmptyState` ("Your role does not read…") instead of a form that would 403.
- **OnboardingConfig**: `ADMIN_ROLES` gate for presets/readiness (SuperAdmin+HR). Employee drill open to all workforce roles. Matches `onboarding.py`.
- **PayRunDetail**: `READ_ROLES` / `MANAGE_ROLES` gates mirror `payroll.py`. Segregation of duties enforced (processor cannot approve).

### 3. Dead endpoints / fake actions removed or rewired
- **PayRunDetail F&F (AC-33)**: `loadFnf("get")` / `loadFnf("post")` use real `GET/POST /payroll/runs/{id}/fnf` endpoints. No fake actions remain.
- **LeaveLedger**: "Run reconciliation" button calls real `GET /leave/reconciliation`. "Query payroll input" calls real `GET /leave/payroll-input`. No dead endpoints.
- **OnboardingConfig**: Preset detail/diff use real `GET /onboarding/presets/{id}` and `GET /onboarding/presets/{id}/diff`. Employee drill uses real `GET /onboarding/{id}/summary|tasks|documents`.
- No `alert()` fake-success buttons, no fabricated audit-row claims, no placeholder endpoints.

### 4. Fabricated activity/metrics removed
- No static tables presenting invented records (names, dates, counts, statuses) in the exclusive scope.
- Reference lists (predefined options like leave types, status pills) are labelled as predefined, not records.
- **PayRunDetail F&F**: Shows real settlement data from server; "gratuity 0 when tenure <5yr" is computed by backend, not invented in UI.

### 5. States, persistence, a11y, responsive
- **Loading**: `LoadingRegion` + `TableSkeleton` on every async section.
- **Empty**: `EmptyState` for permission-denied, 404/not-yet-served, and genuine empty data (no ledger entries, no payslips, no presets).
- **Error**: `RetryableAlert` for load failures (with `onRetry`), `Alert tone="error"` for action failures.
- **Success**: `Alert tone="success"` for mutations (PayRunDetail only).
- **Persistence**: All config persists server-side (no local-only "saved" claims).
- **Layout**: All 4 pages render inside `<Layout>` (nav shell, responsive container).
- **Labels**: Form inputs tied to labels via `htmlFor` (LeaveLedger: 4, PayRunDetail: 2, OnboardingConfig: 1).
- **Tables**: `caption className="sr-only"` + `scope="col"` on all data tables.
- **Dead links**: `npm run check:routes` → all internal links resolve.

### 6. Solver messaging honest
- **pending_verification gate**: PayRunDetail shows amber banner "configurable calculation — pending_verification — not statutory/filing-ready" for IN jurisdiction (rule pack not verified). F&F section shows same. No retry loop — 409 surfaces verbatim with gate text.
- **Failure-as-zero fixed**: No metric shows "0" when data is unavailable — shows honest empty state or "not yet served".
- **No fabricated success messages**: No "audit row written", no "saved locally", no "retained locally".

## Tests (regression)
`frontend/src/lib/feedback-slice3.test.ts` — **112 tests**:
- **Honest Alert feedback** (4 pages × 4): Alert success + error channel (mutations only), no toast/sonner/alert(), mutation catch never feeds load-error channel, no dead endpoints/fabricated claims, Layout wrapper.
- **Authz** (3 pages): Role gates mirror backend + permission-denied state.
- **Real data, real actions, persistence** (4): Independent loads with per-section error/notFound, `Promise.allSettled`, success notice set after `await load()`, F&F params + 409 gate.
- **Fabricated metrics removed** (3 pages × 2): No fabricated person names, no fabricated metric cards.
- **States, a11y, responsive** (4 pages × 8): Loading, empty, error, success (mutations only), permission, labels, tables (caption/scope).
- **Solver messaging honest** (3 pages × 3): No local-only persistence claims, pending_verification gate where IN, no fabricated success messages.
- **Slice-1 frozen 16 untouched**, **Slice-2 admin 101 untouched**.

## Verification (exact results)
- `vitest run src/lib/feedback-slice3.test.ts src/lib/feedback-slice2.test.ts src/lib/feedback-slice1.test.ts` → **112 + 552 + 20 = 684/684 passed**.
- `vitest run` (full frontend suite) → **811/811 passed, 15 files**.
- `tsc --noEmit` → exit 0.
- `npm run build` (vite) → ✓ built in 3.10s.
- `npm run check:routes` → ✓ 247 routes, no dead links.
- `npm run check:api-paths` → ✓.
- Scope: 4 modified files + 1 new test file + 1 new doc; frozen-16 intersection **empty**; admin-101 intersection **empty**; no backend/payroll calc/auth files touched. No push.

## Contract deviations
- None in file scope. Two judgement calls recorded for the validator:
  1. **LeaveLedger and OnboardingConfig are read-only** — no mutations, so no success Alert is rendered. This matches the pattern: success Alert only for pages with write actions (PayRunDetail). The "Alert success + error channel" test is conditional on `hasMutations`.
  2. **shared.tsx is a utility file** — tested only for absence of toast/sonner/alert(), not for page-level concerns (Layout, labels, tables).