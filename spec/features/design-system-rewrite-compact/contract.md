# Feature: design-system-rewrite-compact

## Goal
Complete design system rewrite fixing blank tenant pages, adding global CSS variables for typography/spacing/colors, compact density for data-dense pages, shared shift template/swap table components, and aligning all pages to one design system — with NO production deployment until user visual confirmation.

## Acceptance criteria
1. [AC-01] Tenant pages render content, not blank: `/t/:slug/*` routes mount child components via `<Outlet />` in `TenantLayout`. Verified by navigating to `/t/:slug/scheduling`, `/t/:slug/people`, `/t/:slug/dashboard` and confirming page content renders (not empty shell).
2. [AC-02] `Suspense fallback` is a loading skeleton/spinner, not `null` — no fully blank page on lazy-load failure.
3. [AC-03] All typography mapped to CSS variables: `--font-size-xs` through `--font-size-9xl` defined in `index.css` light/dark roots and in `tokens.ts` lightTokens/darkTokens maps. Components use `text-[var(--font-size-*)]` instead of hardcoded `text-xs`/`text-sm` etc.
4. [AC-04] Compact density variant: `PageHeader` and `SectionCard` accept a `compact` prop. When compact, headings use app scale (`h2-app` 20px, `h3-app` 16px) instead of marketing scale (`mk-h1` 44px, `mk-h2` 32px), padding reduced (`p-3` instead of `p-5`). Applied to Roster Builder, Scheduling, and table-heavy pages.
5. [AC-05] Shared `ShiftTemplateTable` component (`components/ui/shift-template-table.tsx`) used by both `Scheduling.tsx` and `RosterBuilder.tsx` — identical padding, font sizes, badge alignment, action-button layout.
6. [AC-06] Shared `ShiftSwapTable` component (`components/ui/shift-swap-table.tsx`) used by `Scheduling.tsx` — consistent with ShiftTemplateTable styling.
7. [AC-07] `SwapsReplacements.tsx` either renamed to reflect actual responsibility (location/project assignment) or repurposed to handle shift swaps, with styling matching `table-base`.
8. [AC-08] All hardcoded text sizes (`text-lg`, `text-xl`, `text-2xl`, `text-3xl`) in app pages replaced with token-based classes or compact variants. Marketing pages exempt.
9. [AC-09] `text-text-secondary` becomes a real CSS variable (`--text-text-secondary: var(--fg-muted)`) in `index.css`, not just a Tailwind key.
10. [AC-10] `npm run typecheck && npm run build && npm run verify` all pass in frontend/.
11. [AC-11] NO changes pushed to `main`/production until user visually reviews and confirms the design. Build happens on a feature branch only.
12. [AC-12] Regression test plan documented: all 14 E2E specs + backend test suites must pass after redesign.

## Non-goals
- Backend changes (none required)
- Marketing page redesigns (exempt from compact scale)
- Error boundaries beyond scope of this contract
- Deployment to production before user visual sign-off

## Files to touch
- `frontend/src/components/TenantLayout.tsx` — add `<Outlet />`
- `frontend/src/App.tsx` — replace `Suspense fallback={null}` with loading fallback
- `frontend/src/index.css` — add `--font-size-*` CSS variables, `--text-text-secondary`
- `frontend/src/lib/tokens.ts` — add typography to lightTokens/darkTokens maps
- `frontend/src/components/ui/layout.tsx` — `compact` prop on `PageHeader`
- `frontend/src/components/ui/card.tsx` — `compact` prop on `SectionCard`
- `frontend/src/components/ui/shift-template-table.tsx` — NEW shared component
- `frontend/src/components/ui/shift-swap-table.tsx` — NEW shared component
- `frontend/src/pages/RosterBuilder.tsx` — use compact variants, shared table components
- `frontend/src/pages/Scheduling.tsx` — use compact variants, shared table components
- `frontend/src/pages/admin/SwapsReplacements.tsx` — fix naming/styling
- `frontend/src/pages/*.tsx` — replace hardcoded text sizes with tokens (all app pages)
- `frontend/public/_redirects` — NEW: SPA fallback for Render direct refreshes

## Files not to touch
- `backend/` — no backend changes
- `frontend/src/pages/marketing/*` — marketing pages keep their existing design (exempt from compact)
- `frontend/e2e/*` — tests verify, not change (unless a test needs updating for new component structure)
- `spec/features/*` — existing contracts unchanged

## Step-by-step build plan
### Phase 1 — Fix blank tenant pages (critical, AC-01, AC-02)
1. Add `<Outlet />` to `TenantLayout.tsx`
2. Replace `Suspense fallback={null}` with `<PageSkeleton />` fallback in `App.tsx`
3. Add `frontend/public/_redirects` for Render SPA fallback
4. Verify: `/t/Usha/scheduling` renders scheduling content, not blank

### Phase 2 — Typography CSS variables (AC-03, AC-09)
1. Add `--font-size-xs` through `--font-size-9xl` to `index.css` light/dark roots
2. Add typography to `tokens.ts` lightTokens/darkTokens maps
3. Add `--text-text-secondary` CSS variable to `index.css`
4. Verify: `npm run typecheck` passes

### Phase 3 — Compact density variant (AC-04, AC-08)
1. Add `compact` prop to `PageHeader` in `layout.tsx`
2. Add `compact` prop to `SectionCard` in `card.tsx`
3. Apply compact to Roster Builder, Scheduling, and table-heavy pages
4. Replace hardcoded `text-lg`/`text-xl`/`text-2xl`/`text-3xl` on app pages with token classes
5. Verify: `npm run build` passes

### Phase 4 — Shared table components (AC-05, AC-06, AC-07)
1. Create `shift-template-table.tsx` shared component
2. Create `shift-swap-table.tsx` shared component
3. Refactor `Scheduling.tsx` to use both
4. Refactor `RosterBuilder.tsx` demand grid to use `ShiftTemplateTable`
5. Fix/rename `SwapsReplacements.tsx`
6. Verify: `npm run verify` passes all 6 checks

### Phase 5 — Regression testing & user review (AC-10, AC-11, AC-12)
1. Run full E2E suite (14 specs) — all must pass or failures documented as pre-existing
2. Run backend test suites (`ci/run_backend_tests.sh`)
3. Present design to user via browser preview/screenshot for visual confirmation
4. ONLY after user confirmation: merge to main and deploy

## Risks / edge cases
- Marketing pages use `mk-h1`/`mk-h2` at marketing scale — exempt from compact, must not break
- `SectionCard` and `PageHeader` are used on ~15 pages — compact prop must default to false (backward compatible)
- `TenantLayout` missing `<Outlet />` affects ALL `/t/:slug/*` routes — fix is high-impact
- `Suspense fallback={null}` change affects all lazy-loaded routes — must ensure skeleton doesn't flash excessively
- No error boundaries exist — adding one could change error UX

## Test command
Frontend: `npm run typecheck && npm run build && npm run verify`
Backend: `ci/run_backend_tests.sh`
E2E: `npx playwright test`

## Process requirement (user-mandated)
**NO code is pushed to `main` or production until the user visually reviews and confirms the design.** All work happens on a feature branch. The user must approve the design before any merge.
