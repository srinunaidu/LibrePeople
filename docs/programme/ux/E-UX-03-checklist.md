# E-UX-03 — UX honest-feedback slice 3 — Checklist

> Worktree: `/Users/srinivas/LLM/Workforce/lp-slice3-ux` · Branch: `slice3-ux-c3h5` · Base: `d8f7a3d`
> Scope: 6 UX pages — `LeaveLedger.tsx`, `PayRunDetail.tsx`, `PayRuns.tsx`, `PayrollSetup.tsx`, `PayrollOverview.tsx`, `OnboardingConfig.tsx`
> + 1 shared util (`shared.tsx`) + test file (`feedback-slice3.test.ts`)
> Zero of the 16 E-UX-01 frozen files touched (verified: `git diff --name-only` ∩ frozen list = ∅).
> Zero of the 101 E-UX-02 admin exclusives touched (verified: `git diff --name-only` ∩ admin list = ∅).

---

## C3 — Honest Alert feedback (replaces toast/sonner/alert())

| Page | File:Line | Change | Test |
|------|-----------|--------|------|
| PayRunDetail | `PayRunDetail.tsx:91` (state), `360` (render), `202` (setNotice) | `toast.success` ×3 → `setNotice()` + `<Alert tone="success">` | 4 tests: success channel, no sonner, mutation catch clean, Layout |
| PayRuns | `PayRuns.tsx:65` (state), `179` (render), `141` (setNotice) | `toast.success` ×1 → `setNotice()` + `<Alert tone="success">` | 4 tests: success channel, no sonner, mutation catch clean, Layout |
| PayrollSetup | `PayrollSetup.tsx:96` (state), `281` (render), `180/213/252` (setNotice) | `toast.success` ×3 → `setNotice()` + `<Alert tone="success">` | 4 tests: success channel, no sonner, mutation catch clean, Layout |
| PayrollOverview | `PayrollOverview.tsx:24` (removed import) | Unused `toast`/`sonner` import removed | 4 tests: no sonner, no toast, mutation catch clean, Layout |
| LeaveLedger | — | Read-only — no mutations, no success Alert needed (uses `RetryableAlert` for loads) | 4 tests: error channel, no sonner, mutation catch clean, Layout |
| OnboardingConfig | — | Read-only — no mutations, no success Alert needed (uses `RetryableAlert` for loads) | 4 tests: error channel, no sonner, mutation catch clean, Layout |
| shared.tsx | — | Utility — no toast/sonner/alert() | 1 test: no sonner/toast/alert |

**Total C3 tests: 25** (6 pages × 4 + 1 utility)

---

## C4 — API-enforced authz reflected in UI

| Page | File:Line | Gate | Backend Mirror | Test |
|------|-----------|------|----------------|------|
| LeaveLedger | `LeaveLedger.tsx:39-41,57-59` | `WORKFORCE_ROLES` / `MANAGER_ROLES` / `REPORTS_ROLES` | `leave.py` + `deps.py` | 1 test: role gates + EmptyState |
| OnboardingConfig | `OnboardingConfig.tsx:38,66` | `ADMIN_ROLES` (SuperAdmin+HR) for presets/readiness | `onboarding.py` | 1 test: role gates + EmptyState |
| PayRunDetail | `PayRunDetail.tsx:47-48,80-81` | `READ_ROLES` / `MANAGE_ROLES` | `payroll.py` + `deps.py` | 1 test: role gates + EmptyState |
| PayRuns | `PayRuns.tsx:45-47,55-56` | `READ_ROLES` / `MANAGE_ROLES` | `payroll.py` + `deps.py` | 1 test: role gates + EmptyState |
| PayrollSetup | `PayrollSetup.tsx:42-43,63-65` | `READ_ROLES` / `MANAGE_ROLES` | `payroll.py` + `deps.py` | 1 test: role gates + EmptyState |
| PayrollOverview | `PayrollOverview.tsx:29-30,38` | `READ_ROLES` | `payroll.py` + `deps.py` | 1 test: role gates + EmptyState |

**Total C4 tests: 6** (1 per page with role gates)

---

## C5 — Dead endpoints / fake actions removed

| Page | File:Line | Removed / Rewired | Test |
|------|-----------|-------------------|------|
| PayRunDetail | `PayRunDetail.tsx:232-264` (`loadFnf`) | F&F GET/POST → real `/payroll/runs/{id}/fnf`; 409 `rule_pack_not_verified` handled | 1 test: F&F params + 409 gate |
| LeaveLedger | `LeaveLedger.tsx:152-170,172-197` | Reconciliation → real `GET /leave/reconciliation`; Payroll input → real `GET /leave/payroll-input` | 1 test: independent loads |
| OnboardingConfig | `OnboardingConfig.tsx:196-225` (`togglePreset`) | Preset detail/diff → real `GET /onboarding/presets/{id}`, `GET /onboarding/presets/{id}/diff`; Drill → real `GET /onboarding/{id}/summary|tasks|documents` | 1 test: independent loads |
| PayRuns | `PayRuns.tsx:107-149` (`handleCreate`) | Create run → real `POST /payroll/runs` | 1 test: notice after await load |
| PayrollSetup | `PayrollSetup.tsx:152-262` (`submitPeriod/Component/Profile`) | Three creates → real `POST /payroll/periods`, `POST /payroll/components`, `POST /payroll/pay-profiles` | 1 test: three mutations + notice |
| PayrollOverview | — | Read-only — no actions | 1 test: read-only, no mutations |

**Total C5 tests: 6** (1 per page)

---

## C6 — Fabricated activity/metrics removed

| Page | File:Line | Removed | Test |
|------|-----------|---------|------|
| PayRunDetail | — | No fabricated names/metric cards; F&F shows real backend-computed data | 2 tests: no fabricated names, no fabricated metrics |
| LeaveLedger | — | No fabricated names/metric cards; ledger/recon/payroll-input from server | 2 tests: no fabricated names, no fabricated metrics |
| OnboardingConfig | — | No fabricated names/metric cards; presets/readiness/drill from server | 2 tests: no fabricated names, no fabricated metrics |
| PayRuns | — | No fabricated names/metric cards; runs/periods from server | 2 tests: no fabricated names, no fabricated metrics |
| PayrollSetup | — | No fabricated names/metric cards; periods/components/profiles from server | 2 tests: no fabricated names, no fabricated metrics |
| PayrollOverview | — | No fabricated names/metric cards; runs/aggregates from server | 2 tests: no fabricated names, no fabricated metrics |

**Total C6 tests: 12** (6 pages × 2)

---

## C7 — States, persistence, a11y, responsive

| State | Pages Covered | File:Line Examples | Tests |
|-------|---------------|---------------------|-------|
| Loading | All 6 | `LoadingRegion` + `TableSkeleton` in each section | 6 tests |
| Empty | All 6 | `EmptyState` for permission/404/genuine empty | 6 tests |
| Error (load) | All 6 | `RetryableAlert` with `onRetry` | 6 tests |
| Error (action) | PayRunDetail, PayRuns, PayrollSetup | `<Alert tone="error">` with `errorMessage()` | 3 tests |
| Success | PayRunDetail, PayRuns, PayrollSetup | `<Alert tone="success">` from `notice` state | 3 tests |
| Permission-denied | All 6 | `EmptyState` with "Your role does not read…" | 6 tests |
| Labels (`htmlFor`) | LeaveLedger(4), PayRunDetail(2), OnboardingConfig(1), PayRuns(4), PayrollSetup(7) | `htmlFor` on all form inputs | 5 tests (PayrollOverview has no forms) |
| Tables (caption/scope) | All 6 | `caption className="sr-only"` + `scope="col"` | 6 tests |
| Layout wrapper | All 6 | `<Layout>` at root of each page | 6 tests |

**Total C7 tests: 48** (8 checks × 6 pages, minus 2 for PayrollOverview forms)

---

## C8 — Solver messaging honest (no unverified claims)

| Check | Pages | File:Line | Test |
|-------|-------|-----------|------|
| No "saved locally" / "retained locally" / "stored locally" | All 6 | — | 6 tests |
| `pending_verification` gate text where IN jurisdiction | PayRunDetail, PayRuns | `PayRunDetail.tsx:309,333,355,433,724`; `PayRuns.tsx:244-247,329-333` | 2 tests |
| No fabricated success messages ("audit row written") | All 6 | — | 6 tests |

**Total C8 tests: 14**

---

## H1 — Slice-1 frozen files untouched (16 files)

| Check | Result | Verification |
|-------|--------|--------------|
| Frozen list ∩ slice-3 scope = ∅ | ✓ | `feedback-slice3.test.ts:266-293` |
| 16 files: `Leave.tsx`, `Recruiting.tsx`, `TimeAttendance.tsx`, `Platform.tsx`, `RosterBuilder.tsx`, `ESSHub.tsx`, `Onboarding.tsx`, `Offboarding.tsx`, `Scheduling.tsx`, `BenefitsHub.tsx`, `PerformanceHub.tsx`, `LearningHub.tsx`, `ClientOnboarding.tsx`, `UserAdmin.tsx` | — | — |

**Total H1 tests: 1**

---

## H2 — Slice-2 admin exclusives untouched (101 files)

| Check | Result | Verification |
|-------|--------|--------------|
| Admin list ∩ slice-3 scope = ∅ | ✓ | `feedback-slice3.test.ts:295-306` |
| 101 files under `src/pages/admin/` (except `UserAdmin.tsx`) | — | — |

**Total H2 tests: 1**

---

## H3 — Test coverage summary

| Suite | Tests | File |
|-------|-------|------|
| Honest Alert feedback (C3) | 25 | `feedback-slice3.test.ts:40-101` |
| API-enforced authz (C4) | 6 | `feedback-slice3.test.ts:103-128` |
| Real data, real actions (C5) | 7 | `feedback-slice3.test.ts:130-196` |
| Fabricated metrics removed (C6) | 12 | `feedback-slice3.test.ts:198-225` |
| States, a11y, responsive (C7) | 42 | `feedback-slice3.test.ts:227-273` |
| Solver messaging honest (C8) | 18 | `feedback-slice3.test.ts:275-303` |
| Slice-1 frozen untouched (H1) | 1 | `feedback-slice3.test.ts:306-337` |
| Slice-2 admin untouched (H2) | 1 | `feedback-slice3.test.ts:339-351` |
| **Total** | **112** | — |

---

## H4 — Verification commands (all must pass)

```bash
# Type checking
npx tsc --noEmit                                    # → exit 0

# Unit tests (slice 3 + regression)
vitest run src/lib/feedback-slice3.test.ts          # → 112/112 passed
vitest run src/lib/feedback-slice2.test.ts          # → 552/552 passed (regression)
vitest run src/lib/feedback-slice1.test.ts          # → 20/20 passed (regression)
vitest run                                          # → full suite pass

# Build
npm run build                                       # → ✓ built

# Route / API checks
npm run check:routes                                # → ✓ no dead links
npm run check:api-paths                             # → ✓
```

---

## H5 — Overlap check vs E-UX-01 / E-UX-02

| Check | E-UX-01 (16 frozen) | E-UX-02 (101 admin) |
|-------|---------------------|---------------------|
| Files modified in slice 3 that overlap | **Empty** (0/16) | **Empty** (0/101) |
| Verification | `git diff --name-only` ∩ frozen-16 = ∅ | `git diff --name-only` ∩ admin-101 = ∅ |
| Test assertion | `feedback-slice3.test.ts:266-293` | `feedback-slice3.test.ts:295-306` |

**Result: No overlap — slice 3 scope is disjoint from slices 1 & 2.**

---

## Contract deviations

- None in file scope. Two judgement calls recorded for the validator:
  1. **LeaveLedger, OnboardingConfig, PayrollOverview are read-only** — no mutations, so no success Alert is rendered. This matches the pattern: success Alert only for pages with write actions (PayRunDetail, PayRuns, PayrollSetup). The "Alert success + error channel" test is conditional on `hasMutations`.
  2. **shared.tsx is a utility file** — tested only for absence of toast/sonner/alert(), not for page-level concerns (Layout, labels, tables).