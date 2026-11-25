# Feature: ui-compact-design-enhancement

## Goal
Fix misaligned screens, invisible font colors, and inconsistent spacing by tightening to a compact high-contrast design system while adding requested UX/UI enhancements — with no backend changes.

## Acceptance criteria
1. **[AC-01] Alignment fix — no drift:** All 22 core pages + sampled admin pages render inside the shared `Layout` shell with consistent max-width (`max-w-container` / 1280px), 4px grid spacing, and header/content/card padding aligned. Verified visually and by `npm run check:design` — no page overflows container or breaks 4px baseline.
2. **[AC-02] Visibility fix — WCAG AA text contrast:** All body/muted/subtle text meets WCAG AA (≥4.5:1 for body, ≥3:1 for large). No hardcoded `text-slate-*`/`text-gray-*`/`text-emerald-*` on app pages; all use `var(--fg)` / `var(--fg-muted)` / `var(--fg-subtle)` via `text-fg` etc. `TenantContext deriveTheme` contrast helper passes for light+dark+tenant overrides. Verified by `check:design` + axe/contrast spot-check on 3 pages (light & dark).
3. **[AC-03] Compact base — tighter density:** `SectionCard compact`, `PageHeader compact`, and `table-compact` applied to data-dense pages (Roster, Scheduling, Time & Attendance, admin tables). Padding reduced (`p-3` vs `p-5`), heading scale uses app scale (`h2-app 20px`, `h3-app 16px`), table row height ≤44px. Verified by measuring 3 compact pages vs 1 marketing page (marketing exempt).
4. **[AC-04] Next Best Action cards:** Dynamic homepage (`NeedsAction.tsx` pattern) shows ranked action cards driven by tenant state (e.g., pending approvals, unfilled shifts, upcoming deadlines). At least 3 card types, sorted by priority, each with CTA. Verified by unit test mocking tenant state + e2e on `/dashboard` or `/` as seeded user.
5. **[AC-05] Progressive disclosure:** Long/complex pages use accordions or `Advanced Options` collapsed sections (default collapsed). At least 2 pages refactored. Content accessible via keyboard (Enter/Space toggles, `aria-expanded`). Verified by unit test + e2e keyboard navigation.
6. **[AC-06] AI conversational command bar:** `CommandPalette` extended to accept natural-language input (e.g., "show pending leaves") and route/execute or suggest actions. Existing `Cmd+K` / `Ctrl+K` shortcut preserved, focus-trapped, ESC dismisses. No backend AI required — rule/keyword matching acceptable. Verified by unit test for query parsing + e2e open/type/select.
7. **[AC-07] Inline bulk editing & quick approvals:** Tables/drawers support row selection (checkbox), bulk action bar (approve/reject/edit), and inline cell edit or quick-approve button without full page nav. At least 1 table page (e.g., leave approvals or shift swaps) implements this. Verified by unit test + e2e bulk-select → approve flow.
8. **[AC-08] Smart validation & autosave:** Multi-step workflows (at least 1: e.g., leave request, roster creation, or scheduling wizard) show inline field validation (on blur, not only on submit) and autosave draft to localStorage/session (debounced ≤1s) with restore on reload. Verified by unit test (validation + autosave) + e2e reload restores draft.
9. **[AC-09] Scannable KPIs / progress rings / semantic badges:** `KPICard`, progress ring, and `badge` use semantic tokens — `success` (green), `warning` (amber), `error` (red) — mapped via `var(--success)` etc., not hardcoded `bg-emerald-100`/`bg-red-100`. At least 3 KPI instances and 2 badge status variants visible on dashboard/listing pages. Verified visually + `check:design` catches no hardcoded status colors.
10. **[AC-10] Neutral high-contrast surfaces + single brand primary:** Page background `var(--surface-sunken)`, cards `var(--surface)`/`var(--surface-raised)`, borders `var(--border-default)`; only one brand primary (`--brand-600` / `text-brand-600`). No competing blues/teals as primary. Neutral palette calming, contrast high. Verified by token audit (`grep` for hardcoded `bg-slate-*`/`bg-white` on app pages = 0 in changed files) + dark-mode visual check.
11. **[AC-11] Clear hierarchy / whitespace / cards:** Card hierarchy (header → body → footer), consistent `gap-4`/`gap-6` whitespace, and `SectionCard` usage on all app pages. No wall-of-text or overlapping elements. Verified visually on desktop + mobile screenshots.
12. **[AC-12] Responsive mobile-first (thumb-friendly):** All touched pages usable at 375px: no horizontal scroll, tappable targets ≥44px, bottom or thumb-reachable actions where applicable, drawer/sheet not clipped by z-index. Shell (`TopBar`, `WorkspaceRail`) collapses correctly. Verified by Playwright mobile viewport e2e + manual z-index check.
13. **[AC-13] Empathetic micro-interactions & empty states:** Buttons/accordions/cards have 150ms fade/slide transitions (existing tokens), empty tables show illustrated or friendly empty state with CTA ("No pending requests — you're all caught up") not blank table. At least 2 empty states updated. Verified visually + unit test for empty-state rendering.

## Non-goals
- Backend changes — API, DB, auth, or route logic (reuse 120 existing routes).
- New charting library or data-fetching logic.
- Marketing site redesign beyond token alignment (marketing pages keep display scale).
- Full AI LLM integration (command bar is keyword/rule-based unless backend already provides it).

## Files to touch
- `frontend/src/index.css` — ~983 lines, Layer 1/2 token roots; tighten spacing vars, add/verify `--surface*`, `--fg*`, semantic status vars; ensure light/dark roots complete
- `frontend/src/tokens.css` — keep in sync with `index.css` (mirror any new/changed vars)
- `frontend/src/lib/tokens.ts` — `lightTokens`/`darkTokens` maps + `deriveTheme` WCAG helper; add missing ramps, ensure single source of truth
- `frontend/tailwind.config.js` — map `colors`/`fontSize`/`spacing`/`borderRadius`/`boxShadow`/`zIndex` to CSS vars; spacing stays 4px base
- `frontend/src/components/Layout.tsx` + `components/shell/TopBar.tsx` + `WorkspaceRail.tsx` + `CommandPalette.tsx` — shell alignment, z-index scale, command-bar conversational input
- `frontend/src/components/ui/card.tsx` — `SectionCard` compact variant (already exists, apply + tighten)
- `frontend/src/components/ui/layout.tsx` — `PageHeader` compact variant
- `frontend/src/components/ui/kpi-card.tsx` — ensure uses `KPICard` + semantic tokens for progress rings
- `frontend/src/components/ui/badge.tsx` + `button.tsx` — semantic `success`/`warning`/`error` variants, no hardcoded `bg-red-600` etc.
- `frontend/src/components/ui/*` (table, accordion, drawer/sheet) — `table-compact`, progressive disclosure, inline bulk edit primitives
- `frontend/src/pages/NeedsAction.tsx` — reference pattern for Next Best Action cards; new `NextBestActionCards.tsx` or extension
- `frontend/src/pages/**/*.tsx` — 22 core + sampled admin pages: replace hardcoded `slate`/`emerald`/`border`/`bg-white` with `var(--*)`, apply compact where dense
- `frontend/src/contexts/TenantContext.tsx` — verify `deriveTheme` enforces WCAG AA contrast for tenant overrides

## Files not to touch
- `backend/**` — no backend changes per scope
- `spec/features/*/contract.md` (other features) — do not modify
- `frontend/e2e/**` — tests verify only (update selectors only if component structure changes, justify in PR)
- `frontend/src/pages/marketing/**` — exempt from compact scale (`mk-h1`/`mk-h2` 44px/32px stays)

## Step-by-step build plan
1. **Audit baseline:** Run `npm run check:design` and `grep -r "text-slate-\|text-gray-\|bg-slate-\|bg-emerald-\|border-slate" frontend/src/pages` to list hardcoded sites. Screenshot 3 misaligned/low-contrast pages (light+dark) as before.
2. **Token core fix:** In `index.css` light/dark roots + `tokens.css` + `lib/tokens.ts`, add/verify `--surface`, `--surface-raised/sunken/inset`, `--fg/muted/subtle`, `--border-*`, `--success/warning/error` + light/text/border variants, `--focus-ring`; ensure `deriveTheme` computes contrast ≥4.5:1 and falls back. Run `npm run check:design`.
3. **Tailwind mapping:** In `tailwind.config.js`, ensure every color/spacing/radius/shadow maps to `var(--*)`; keep 4px spacing scale; verify `zIndex` scale (`dropdown 1000` < `sticky 1100` < `overlay 1300` < `modal 1400`). No hardcoded hex in config.
4. **Primitives tightening:** Verify `SectionCard`/`PageHeader` `compact` props (padding `p-3`, headings `h2-app`/`h3-app`), `table-compact` row height, `KPICard` + `badge` semantic variants, `button` danger→`var(--error)` mapping. Add `accordion`/`Advanced Options` primitive if missing, with `aria-expanded` and 150ms transition.
5. **Shell & command bar:** Fix `Layout` max-width/container alignment; audit `TopBar`/`WorkspaceRail`/`CommandPalette` z-index vs `tailwind.config.js` scale; extend `CommandPalette` with conversational input (keyword → route/action), preserve `Cmd+K`, focus trap, ESC.
6. **Page sweep — visibility & spacing:** Replace hardcoded colors with token vars in `pages/**/*.tsx` (batch by 5 files, verify each batch with `check:design`); apply `compact` to Roster Builder, Scheduling, Time & Attendance, and 2 admin tables; ensure hierarchy/gap consistency.
7. **Next Best Action cards:** Build or extend `NeedsAction` pattern into ranked cards on homepage/dashboard, driven by existing tenant state (no new API); wire CTAs to existing routes.
8. **Bulk edit & approvals:** On one table page, add checkbox column + sticky bulk bar + inline edit/drawer quick-approve; reuse existing `table`/`drawer` primitives; handle empty selection state.
9. **Validation & autosave:** On one multi-step workflow, add on-blur inline validation + debounced autosave (≤1s) to localStorage with restore on mount; show "Draft saved" micro-feedback.
10. **KPI/badges/micro-interactions/empty states:** Replace status colors with semantic tokens on dashboard + one listing page; add progress rings via `KPICard`; set 150ms fade/slide on interactive elements; implement 2 friendly empty states.
11. **Responsive pass:** Test at 375px/768px/1280px; fix thumb targets ≥44px, prevent horizontal scroll, verify mobile z-index (drawer over content, not under TopBar). No separate mobile codebase.
12. **Verification:** Run `npm run test:unit && npm run check:design && npm run verify && npx playwright test` (see Test command). Capture after screenshots for before/after; open PR on feature branch only.

## Risks / edge cases
- **Token desync `tokens.css` vs `index.css` vs `tokens.ts`:** Triple file must stay identical; add CI check or manual diff step each token edit — drifting breaks dark mode + tenant themes.
- **Mobile z-index stacking:** `TopBar`/`WorkspaceRail`/`overlay`/`modal`/`drawer` compete; use `tailwind.config.js` zIndex scale strictly, test at 375px with drawer + command palette open simultaneously.
- **Token migration breakage:** 120 routes / ~122 pages import hardcoded colors; batch replacement risks missing files or breaking `dark:` variants — use codemod/grep + `check:design` per batch, keep marketing exempt.
- **WCAG AA regression on tenant override:** Custom tenant brand may fail contrast; `deriveTheme` must clamp/adjust and be unit-tested with light+dark extremes.
- **Autosave vs stale data:** Local draft may conflict with server truth on reload — show "Restore draft?" prompt, never auto-overwrite newer server data.
- **Command bar false positives:** Keyword matching may mis-route; keep suggestions list + explicit confirm before navigation.

## Test command
```sh
# frontend (from frontend/)
npm run test:unit
npm run check:design
npm run verify        # typecheck + check:routes + check:api-paths + check:design + build + check:classes
npx playwright test   # e2e incl. mobile viewport

# optional backend sanity (no changes expected)
ci/run_backend_tests.sh
```

## Test plan
- **Unit:** `npm run test:unit` — Next Best Action ranking, command-bar query parsing, bulk-selection logic, autosave debounce + restore, accordion toggle `aria-expanded`, badge/KPI semantic color mapping, `deriveTheme` contrast ≥4.5:1.
- **Visual:** Before/after screenshots at 375px & 1280px (light+dark) for 3 dense pages + dashboard; verify alignment, contrast, compact density, empty states, micro-interactions.
- **`check:design`:** `npm run check:design` must pass with 0 hardcoded `slate/emerald/border/bg-white` on touched app pages and no missing token vars.
- **E2E (Playwright):** Dashboard Next Best Action CTA, accordion keyboard nav, `Cmd+K` → type → select, bulk-select → approve, multi-step validation + reload-restore draft, mobile viewport no-overflow + thumb targets.
