# Feature: Phase D — page-content redesign (visual direction)

**Feature ID:** phase-d-redesign
**Risk tier:** 2 (visual-only; no migrations; no new routes; reversible by revert)
**Branch:** `agent/ux/phase-d1` (D1) from `main` HEAD; D2/D3 follow on their own batch branches. No push to remote.
**Seed discipline:** synthetic seed data only (existing e2e synthetic dataset). No production data, no screenshots in-repo.

## Behavior

Phase C rebuilt the shell + role-aware navigation. Phase D redesigns **page content** inside that shell
per 8 shared visual-direction deltas. IA, routes, role enforcement, and backend contracts do not change:
every number on screen keeps (or gains an explicit mapping to) a real GET source; any widget without a
real GET source is **dropped, not faked**, and recorded in the batch build report.

## Visual-direction deltas (shared across D1/D2/D3)

1. **Compact density** — `<PageHeader compact>` + `<SectionCard compact>` on all app pages; 4px grid,
   `text-h*-app` scale (no `text-2xl`/`text-3xl` on app pages).
2. **Color-role discipline** — no hardcoded hex on app pages; brand → primary actions/active states/focus
   only; red/amber/green → status only; surfaces/ink via tokens.
3. **Loading + empty honesty** — `LoadingRegion`/`PageSkeleton` (`skeleton` class) while loading;
   `EmptyState` (title + description + next action) when empty. No fabricated sparklines/rings/trends
   (no backend aggregation exists for deltas).
4. **KPI honesty** — every live number maps to a real GET endpoint (mapping table required in each batch
   report). No GET source → drop the widget and record it. Never render plausible-looking fake figures.
5. **Form labelling** — every input/select/textarea has a visible `<label htmlFor>` + matching `id`
   (or via shared inputs); errors via `aria-describedby`.
6. **Icon idiom** — design-system icons; zero emoji in app chrome.
7. **Responsive + dark-mode safe** — viewports **360 / 768 / 1440**; dark mode sampled per batch;
   tokens only, no viewport- or theme-fragile hardcodes.
8. **Marketing separation** — marketing pages keep their own editorial mode; app compact classes/tokens
   do not leak into marketing and vice versa. (Marketing permanently out of scope, decision D-e.)

## Batches

**D1 — employee-facing (this branch).** Exact files:
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/components/home/*`: `AssociateHome.tsx`, `HRHome.tsx`, `ManagerHome.tsx`,
  `PayrollHome.tsx`, `SuperAdminHome.tsx`, + shared `DashboardFallback.tsx`
  (`NeedsAction.tsx`, `NextBestActionCards.tsx` as supporting, no scope creep)
- `frontend/src/pages/People.tsx`
- `frontend/src/pages/Leave.tsx`
- `frontend/src/pages/leave/LeaveLedger.tsx`
- `frontend/src/pages/expenses/*`: `Expenses.tsx`, `ExpenseDetail.tsx`, `ExpenseNew.tsx`
- `frontend/src/pages/documents/DocumentsLibrary.tsx`
- `frontend/src/pages/ess/ESSHub.tsx`
- `frontend/src/pages/MyAssets.tsx`
- `frontend/src/pages/Onboarding.tsx`
- Deltas applied: **1–7** (delta 8 excluded — no marketing in D1 file set).

**D2 — manager/HR/admin console pages** (separate batch branch; file list per the brief — not in this branch).
**D3 — platform + remaining polish** (separate batch branch; file list per the brief — not in this branch).

## Acceptance criteria

1. Every touched D1 page renders compact density (delta 1), token colors (delta 2), shared
   loading/empty states (delta 3), labelled controls (delta 5), icon idiom (delta 6), and holds at
   360/768/1440 + sampled dark mode (delta 7), with zero backend/route/role-model changes.
2. KPI→endpoint mapping table in the D1 build report covers every live number on touched pages; any
   dropped widget is listed with its reason. No fabricated figures.
3. Playwright before/after screenshots per touched page at the same viewport set + same seed data,
   stored **outside** the repo (`/tmp/phase-d/d1/`); no screenshots committed.
4. Gates green: frontend typecheck + production build + full unit suite.

## Non-goals

- No backend changes (STOP + report if any page needs one — do not work around).
- No new routes, modules, path renames, or role-model changes (Phase C owns IA).
- No new endpoints to feed KPIs; missing endpoint = STOP for that widget (drop + record).
- No marketing pages, ever (D-e: permanently out of scope).
- Stepper flows: redesign applies only to steppers with ≥ 4 steps (D-c).

## Interfaces / data

- Read-only GET reuse only (existing `api.get` calls; `fetchAllEmployees` where already used).
- Component contracts reused, not created: `PageHeader compact`, `SectionCard compact`, `KPICard`
  (live value + hint, no trend props), `EmptyState`, `LoadingRegion`, `Alert`, `StatusPill`.
- No schema/migration/config changes. Backwards compatible by construction (props already optional).

## Test plan

1. Existing suites: frontend typecheck, production build, full unit (vitest) — all green.
2. Per-batch role render tests for touched homes/pages stay green; extend only to assert compact
   density + honest empty states where missing.
3. Playwright before/after screenshots (360/768/1440, same seed) stored outside the repo; eyeball
   delta 1–7 conformance + dark-mode sample.
4. Grep guards: no hardcoded hex / `text-2xl`+ / emoji in touched D1 app files.

## Risk tier

2 (normal): multi-file visual touch, test-backed, no migrations, fully revertible.

## Rollback

Revert the batch commit(s). No migration to unwind; alias/canonical routes untouched; screenshots live
outside the repo so nothing leaks into history.

## Open decisions — RESOLVED by lead 2026-11-27

- **D-a** Seed = existing e2e synthetic dataset (no new seed authoring for D1).
- **D-b** Viewports exactly **360 / 768 / 1440** for before/after screenshots.
- **D-c** Stepper redesign only for flows with **≥ 4 steps** (confirmed; no D1 stepper qualifies).
- **D-d** KPI→endpoint mapping table required in the build report (one row per live number).
- **D-e** Marketing permanently out of scope (delta 8 is a constraint, never a task).
- **D-f** Dark mode sampled per batch (D1 sample recorded in the build report).
