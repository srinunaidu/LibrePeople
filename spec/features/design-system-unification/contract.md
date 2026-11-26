# Feature: design-system unification (R1)

## Behavior
Unify five dualities to one canonical Kit pattern each; pure className/swap migration, no visual or behavior change.

Decisions (canonical + why):
1. Button: `Button` from `@/components/ui` (cva `ui/button.tsx`: primary/secondary/ghost/danger + sm/md/lg/xs + loading). Raw `<button class="btn …">` / `action-link` diverge; kit already covers sizes/loading/a11y.
2. Modal: `Modal/*` from `@/components/ui` (`ui/modal.tsx`: size sm/md/lg/xl/full + Drawer). `ui/dialog.tsx` is a fixed-max-w-lg duplicate; `ConfirmDialog` is a third radix wrapper. One overlay/focus/close affordance.
3. Table: `Table` from `@/components/ui` (`ui/table.tsx`: sort/filter/paginate/select/loading/empty/a11y). Raw `<table class="table-base…">` majority; `Shift*Table` stay as domain wrappers ON `Table`; `DataTable` (tanstack, zero call sites) deprecated.
4. Header/Card: `PageHeader` + `SectionCard/Card` from `@/components/ui` (compact for admin). Covers icon/actions/description/a11y consistently.
5. Toast: barrel `showToast/showSuccess/showError + Toaster` from `@/components/ui` (`ui/toast.tsx` wraps sonner with tokens). Duplicate `ui/sonner.tsx` Toaster + raw `sonner` imports removed. Slice pages keep `RetryableAlert` (no toasts per slice tests).
6. Imports: barrel `@/components/ui` canonical. Deep `@/components/ui/*` only inside `ui/*` itself.

## Acceptance criteria
1. Zero raw `<button` in listed pages; all use kit `Button` with identical variant/size (btn-primary→primary, btn-secondary→secondary, btn-ghost→ghost, btn-xs→xs).
2. Zero `ui/dialog` + `ConfirmDialog` imports in pages; all modals use barrel `Modal/*`; `ui/dialog.tsx` deleted or re-export shim.
3. Zero raw `<table` in listed pages; all use kit `Table` (or Shift* wrappers); `DataTable` deleted or marked deprecated with zero imports.
4. All listed pages render kit `PageHeader` + `SectionCard/Card`; no hand `<h1`/raw `mk-card` divs.
5. Zero `sonner` / `@/components/ui/sonner` imports outside `ui/toast.tsx` + `App.tsx` Toaster; slices 1/2/3 keep RetryableAlert-only.
6. Zero deep `@/components/ui/*` imports in `pages/**`; `npm run typecheck`, `npm run build`, `npm run test:unit` (811/811) + slice1/2/3 tests green; no new deps; pixel-identical (className swaps only).
7. Migration lists (exact): Buttons — `pages/MyAssets.tsx:79,87,135` `pages/Assets.tsx:180,188,224,265,304,310,329,338,344,350,355` `pages/Leave.tsx:187,236,302,381,430,475,476,508,512,519` `pages/Recruiting.tsx:256,677,681,685,719,720` `pages/Offboarding.tsx:161,228,277,297,301,401` `pages/TimeAttendance.tsx:441` `pages/Scheduling.tsx:164,216,286` `pages/RosterBuilder.tsx:636,1099,1112` `pages/Reports.tsx:147,148,163,299` `pages/payroll/PayRuns.tsx:298-300` `ui/layout.tsx:193,197` (+ Contact/Login/ThemeStudio/Expense*/payroll Details — full `grep '<button' src` must be empty). Tables — raw `<table` in `pages/Leave.tsx,Recruiting.tsx,Assets.tsx,Reports.tsx,Onboarding.tsx,TimeAttendance.tsx,Scheduling.tsx:325,RosterBuilder.tsx,ess/ESSHub.tsx,performance/PerformanceHub.tsx,benefits/BenefitsHub.tsx,learning/LearningHub.tsx,leave/LeaveLedger.tsx,onboarding/OnboardingConfig.tsx,admin/IntegrationsHub.tsx,admin/ComplianceCenter.tsx,forecasting/*,ClientOnboarding.tsx:421+,ProjectStatus.tsx:221,Compare.tsx:130` → kit `Table`. Modals — `pages/Jobs.tsx:17 (deep modal→barrel),People.tsx:10-14 (already barrel, keep),ConfirmDialog.tsx (migrate to Modal)`.

## Non-goals
No backend, no App.tsx routing, no behavior/copy/token changes, no new deps, no responsive redesign.

## Interfaces / data
None. Config: none. Back-compat: barrel API unchanged; `dialog`/`sonner`/`data-table` removed only after zero refs.

## Test plan
`cd frontend && npm run typecheck && npm run build && npm run test:unit` (must stay 811/811 incl. `lib/feedback-slice*.test.ts`, `ui.test.tsx`, `features/ui-compact.test.tsx`). Plus `grep -rn '<button' src/pages src/components --include='*.tsx' | grep -v Button` empty (except intentional tests); same for `<table`, `ui/dialog`, `ui/sonner`, `"sonner"`.

## Risk tier
2 (normal; broad touch, mechanical swaps).

## Rollback
Revert per-batch commit; no migrations/flags.

## Open decisions
Lead to confirm: (a) git rev — asked main@6dfdb54, only verified `.git/HEAD=ref:refs/heads/main`, no shell to hash — STOP if file list assumed wrong? (b) delete vs shim `dialog.tsx/sonner.tsx/data-table.tsx`? (c) `SubmitBar` raw buttons in `ui/layout.tsx` — migrate to kit Button now or exempt?

## Owner/lead decisions
- D1: delete (not shim) zero-callsite duplicates (data-table.tsx et al); keep Toaster root; direct toast() calls forbidden outside barrel (Alert-pattern per slices).
- D2: migrate ui/layout.tsx SubmitBar raw buttons (no exemption).
- D3: modal-vs-dialog decided by call-site count — count `from.*ui/(modal|dialog)` imports across frontend/src, pick the majority as canonical, record counts + choice in the contract. Counts (2026-11-26, `grep -rn "from.*ui/(modal|dialog)" frontend/src`): `ui/modal` = 2 (`components/ui.tsx:9` barrel re-export, `pages/Jobs.tsx:17` deep import), `ui/dialog` = 0 in pages. Choice: canonical = Modal (`ui/modal.tsx` via barrel `Modal/*`); `ui/dialog.tsx` deleted, `ConfirmDialog` migrated to Modal.
