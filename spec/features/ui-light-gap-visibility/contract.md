# Feature: ui-light-gap-visibility

## Goal
Fix remaining light-mode invisibility (gray tables vanish on white, collapsed menu appears empty, font washed) and excessive stacked gaps (48-56px double spacing) on top of compact design enhancement, with a light-theme contrast suite.

## Acceptance criteria
1. **[AC-14] Light table visibility — ≥1.5:1 vs white:** In light mode (`theme=light`, `:root` vars), every table `thead th` background + `border` + `tbody td` borders + `table-striped` even-row background + hover state must each achieve ≥1.5:1 contrast against the underlying `bg-surface` (`#ffffff`). `thead` must be visibly distinct from `tbody` (not same `#ffffff`); striped rows must be distinguishable; hover must be distinguishable. No `table-base` row renders as white-on-white in light. Verified by Playwright light-mode contrast measurement sampling `thead th`, `tbody tr:nth-child(even)`, and hover state, plus computed-style assertion that `thead th bg != #ffffff` in light.
2. **[AC-15] Menu font visibility in light — no empty rail:** In light mode, `SecondarySidebar` collapsed (`w-[68px]`, not hovered/pinned) must not appear empty: either (a) labels remain visible (not `sr-only` only) via icon+truncated label or auto-expand on light, or (b) collapsed slot shows at least 11px legible text without `sr-only`. `WorkspaceRail` inactive items (`text-fg-muted` on `bg-surface`) and `SecondarySidebar` `nav-item` / `nav-item-compact` text must pass WCAG AA ≥4.5:1 on `bg-surface` in **both** light and dark (`--fg-muted` ratio checked, not `#64748b` washed on white). No menu relies solely on `title`/`aria-label` tooltip for label. Verified by Playwright light contrast on `.nav-item` and rail items + visual screenshot of rail+sidenav at collapsed width in light.
3. **[AC-16] Gap tightening — single stack gap-6:** Replace stacked `mb-*` chain with a single vertical stack gap. On `SuperAdminHome` (representative tight page) and all role homes: remove double spacing `Layout lg:py-8` (32px) + `PageHeader mb-6` (24px) + `NeedsAction mb-6` (24px) + `KPI grid mb-6` + `grid gap-4 mb-5` stacking. Instead wrap page content in `space-y-6` (or equivalent `flex flex-col gap-6`) and set child blocks to `mb-0`/isolated, or normalize to: `Layout py-6` (not `py-8`), `PageHeader mb-4` when `compact` (`mb-3` exempt only if tight h2), `NeedsAction` no outer `mb-6` when inside stack (or `mb-0` + stack gap), `SuperAdminHome` KPI/grids use `gap-4` consistently (not mix `gap-4 mb-6` + `gap-4 mb-5` double). Total gap between `NeedsAction` bottom and first KPI top and between KPI and next grid must be 24px (`gap-6`), not 40-56px. `PageHeader` bottom margin consistent across homes (single value). Verified by Playwright `boundingBox` distance measurement + screenshot ruler (no 48px+ whitespace band).
4. **[AC-17] Light contrast suite — duplicate for light theme:** Add `frontend/e2e/contrast-light.spec.ts` (or extend `contrast.spec.ts`) that duplicates the dark suite but calls `setTheme(page,'light')` for both `PUBLIC_PAGES` and `AUTHENTICATED_PAGES` and asserts same AA thresholds (4.5:1 normal, 3:1 large). Must be included in `verify`/`playwright` run and fail if any light text violates ratio (catches regressions like `fg-muted #64748b` on `surface-sunken #f8fafc`). `npm run verify` still passes. Existing dark suite untouched.

## Non-goals
- Backend changes — API, DB, auth, or route logic (reuse existing routes).
- New charting library, data-fetching, or LLM integration.
- Marketing site redesign beyond token alignment.
- Changing table data, columns, or pagination logic — only visual tokens/spacing.

## Files to touch
- `frontend/src/index.css:128-154` — light `:root` tokens: adjust `--surface-sunken`, `--surface-inset`, `--surface-hover`, `--border-subtle`, `--border-default`, `--fg-muted` if needed to hit AC-14 (thead ≥1.5:1) and AC-15 (4.5:1 on bg-surface); ensure `:root` vs `.dark` vs `.light-surface` vars explicitly set
- `frontend/src/index.css:684-711` — `.table-base thead th` / `tbody td` / `.table-striped` backgrounds + borders + hover: make light-mode values distinct from `#ffffff` (no white-on-white); striped even-row must differ by ≥1.5:1
- `frontend/src/index.css:568-612` — `.nav-group` / `.nav-rule` / `.nav-item` / `.nav-item-compact` / `.nav-item-active`: light `color: var(--fg-muted)` must be ≥4.5:1 on `var(--surface)`; collapsed rule not only visible element
- `frontend/src/components/Layout.tsx:168` — `main` padding `px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8` → tighten to `lg:px-8 lg:py-6` (reduce `py-8` 32px); add wrapper `div.max-w-container mx-auto space-y-6` (or `flex flex-col gap-6`) and remove per-child outer `mb-6` stacking; breadcrumb `mb-4` within stack adjusted to not double
- `frontend/src/components/ui.tsx:219-236` — `PageHeader` compact `gap-2 mb-3` vs `gap-4 mb-6`: normalize so `compact` uses `mb-4` (16px) consistently, not `mb-6` double with Layout; ensure `mb-*` is stack-compatible (caller may override to `mb-0` when inside `space-y-6`)
- `frontend/src/components/home/NeedsAction.tsx:33` — `section.card mb-6` → make margin conditional or remove when inside home stack (`mb-0` by default, parent stack provides `gap-6`); keep `mb-6` fallback only when not inside `space-y-6`
- `frontend/src/components/home/SuperAdminHome.tsx:101-167,220` — `PageHeader compact`, `NeedsAction`, `KPI grid gap-4 mb-6` (124), `grid gap-4 mb-5` (167,220): convert to single stack: remove `mb-6`/`mb-5` from grids and rely on parent `space-y-6`; keep `gap-4` inside grids, not `gap-6+5` double; update loading skeleton similarly (103-104)
- `frontend/src/components/shell/SecondarySidebar.tsx:34-108,111-151` — collapsed state: replace `sr-only` label with visible truncated text or increase rail width / auto-expand in light; ensure `nav-rule` 1px `bg-border-default` meets ≥1.5:1 in light; `expanded ? w-60 : w-[68px]` logic adjusted so light collapsed still affords label
- `frontend/src/components/shell/WorkspaceRail.tsx:84-113` — inactive `text-fg-muted hover:text-fg` contrast: verify `fg-muted` token passes 4.5:1 on `bg-surface` light; adjust hover bg to `var(--surface-hover)` distinct in light
- `frontend/src/tokens.css` — mirror any new/changed `index.css` vars
- `frontend/src/lib/tokens.ts` — mirror `lightTokens`/`darkTokens` if token values changed; `deriveTheme` contrast helper must still pass light+dark
- `frontend/tailwind.config.js:165-176` — ensure `surface-sunken`, `border-subtle`, `surface-hover` map to `var(--*)` (no hardcoded hex)
- `frontend/e2e/contrast.spec.ts:236-304` — add light variants (or new `frontend/e2e/contrast-light.spec.ts` duplicating structure with `setTheme(page,'light')`); wire into Playwright projects

## Files not to touch
- `backend/**` — no backend changes per scope
- `spec/features/*/contract.md` (other features) — do not modify except this addendum
- `frontend/src/pages/marketing/**` — exempt (light-only marketing stays)
- `frontend/scripts/**` — only update if adding light `check:design` invocation, else leave

## Step-by-step build plan
1. **Audit light failure:** Start dev with `theme=light` forced; screenshot a dense table page (`SuperAdminHome` tenant-health, `People`) and collapsed `SecondarySidebar` vs `WorkspaceRail` at 1280px. Run in browser console: measured luminance of `#f8fafc` on `#ffffff` (1.03:1) and `#e2e8f0` (1.24:1) to confirm <1.5:1. Confirm `sr-only` labels are only labels in collapsed nav (inspect `.nav-rule` alone).
2. **Token fix (light):** In `frontend/src/index.css:128-154` (`:root, .light-surface`), darken `surface-sunken` from `#f8fafc` toward `#f1f5f9`/`#eef2f7` so contrast vs `#ffffff` ≥1.5:1, and bump `border-subtle`/`border-default` from `#e2e8f0` to at least `#cbd5e1`/`#94a3b8` (or opaque `rgba` with ≥1.5:1) — verify with `luminance` helper. Keep `.dark` vars unchanged. Mirror to `frontend/src/tokens.css` and `frontend/src/lib/tokens.ts` lightTokens. Run `npm run check:design`.
3. **Table visuals (light):** In `frontend/src/index.css:688-710`, change `thead th` bg to `var(--surface-inset)` (`#f1f5f9`) or `var(--surface-sunken)` post-darken so it differs from `#ffffff`; ensure `border-bottom` uses `var(--border-default)` (now ≥1.5:1). Set `.table-striped tbody tr:nth-child(even)` to `var(--surface-inset)` distinct from hover `var(--surface-hover)`. Verify hover `bg-surface-hover` also ≥1.5:1. Snapshot table at light.
4. **Menu legibility (light):** In `frontend/src/components/shell/SecondarySidebar.tsx`, remove `sr-only` for label when collapsed: change `SidebarLink` line 140 from `!expanded && "sr-only"` to `!expanded ? "hidden lg:hidden" handled by tooltip + text-xs below icon` OR implement auto-expand `expanded=true` when `document.documentElement.classList.contains('dark')===false` and `window.innerWidth>=1280`. Minimal: keep `w-[68px]` but show `text-[11px] truncate text-fg-muted` under icon (not `sr-only`), and ensure `nav-item` `color: var(--fg-muted)` passes 4.5:1 (if `#64748b` fails, darken to `#475569` for light). Update `frontend/src/components/shell/WorkspaceRail.tsx:112` similarly. Run axe/contrast on nav.
5. **Gap tighten — Layout/PageHeader:** In `frontend/src/components/Layout.tsx:168`, change `lg:py-8` → `lg:py-6`, wrap `{children}` container: `<div className="max-w-container mx-auto flex flex-col gap-6">` and change breadcrumb `mb-4` → `mb-0` (stack provides gap). In `frontend/src/components/ui.tsx:221`, set `PageHeader` base to `gap-3 mb-0` inside stack (keep prop but default `mb-0`, not `mb-6`), so Layout stack owns spacing. Update `frontend/src/components/home/NeedsAction.tsx:33` `mb-6` → `mb-0`.
6. **Gap tighten — SuperAdminHome:** In `frontend/src/components/home/SuperAdminHome.tsx`, remove `mb-6` from `grid ... mb-6` (124) and `grid ... mb-5` (167,220) → `mb-0` (parent `space-y-6` gap). Ensure loading skeleton (103) similarly `mb-0`. Propagate same pattern to `HRHome.tsx`, `ManagerHome.tsx`, `PayrollHome.tsx`, `AssociateHome.tsx` (each has `NeedsAction` + KPI grid).
7. **Light contrast suite:** Duplicate `frontend/e2e/contrast.spec.ts` to `frontend/e2e/contrast-light.spec.ts` (or add two `test` blocks) replacing `setTheme(page,'dark')` with `setTheme(page,'light')` for identical `AUTHENTICATED_PAGES` + `PUBLIC_PAGES`. Keep `allTextContrasts` helper excluding `.sr-only`. Add `setTheme` local helper. Ensure new file is picked by `playwright.config.ts` projects.
8. **Verification:** Run `npm run check:design`, `npm run typecheck`, `npm run build`. Then `npx playwright test contrast-light` in light, `npx playwright test contrast` still dark. Capture gap screenshots: `page.screenshot({fullPage:true})` in light at 1280px for SuperAdminHome, measure `needs.bottom → kpi.top` = 24±4px, `kpi.bottom → nextGrid.top` =24±4px.

## Risks / edge cases
- **Token desync `index.css` vs `tokens.css` vs `tokens.ts`:** triple file must stay identical; manual diff each edit — drift breaks dark mode + tenant themes. Guard: `npm run check:tokens`.
- **Border 1.5:1 vs #ffffff is border contrast, not text:** WCAG non-text contrast (1.4.11) requires UI components ≥3:1, but contract asks 1.5:1 vs white for visibility floor — use color-mix luminance calc, not eyeball.
- **Collapsed nav tooltip-only violates 4.5:1:** `title`/`aria-label` not measured by contrast suite (`sr-only` excluded) — must add visible text or fail AC-15.
- **gap-6 wrapper double-counts if children keep mb-*:** removing `mb-6` from NeedsAction/KPI breaks pages not yet migrated — scope to homes only, leave other pages' `mb-5` until batch 2.
- **Light table hover indistinguishable:** if `surface-hover` = `#f8fafc` same as striped, hover vanishes — must daylight each token.
- **No-trade rule:** do not change table data/columns/pagination — visual only.
- **Dark regression:** light darkening must not reduce dark contrast; keep `.dark` vars untouched and re-run dark contrast suite.

## Test command
```sh
# frontend (from frontend/)
npm run check:design
npm run typecheck
npm run verify   # typecheck + check:routes + check:api-paths + check:design + build + check:classes
npx playwright test e2e/contrast.spec.ts          # dark (existing)
npx playwright test e2e/contrast-light.spec.ts    # light (new AC-17)

# light gap visual (manual)
npx playwright test --grep "light gap" --project=desktop  # or screenshot SuperAdminHome in light and measure 24px gaps

# optional unit
npm run test:unit
```

## Test plan
- **`check:design` light:** `npm run check:design` must pass with 0 hardcoded `slate/emerald/border/bg-white` on touched pages and no missing token vars in light.
- **Playwright light contrast:** `contrast-light.spec.ts` visits each `AUTHENTICATED_PAGES` + `PUBLIC_PAGES` with `setTheme('light')`, measures `allTextContrasts` and also explicit `thead th` / striped row / `nav-item` ratios; fails if <4.5:1 text or <1.5:1 border/surface.
- **Visual gap screenshot:** Light SuperAdminHome at 1280px + 375px: screenshot shows `PageHeader` → `NeedsAction` → KPI → grids each separated by single 24px gap (no 48px+ band); `table thead` visibly distinct gray bar (not white).
- **Menu collapsed check:** Light at 1280px, `SecondarySidebar` collapsed (`w-[68px]`): labels visible or rail auto-expanded; no empty nav (screenshot + DOM check `nav-item` text not `.sr-only` only).
- **No dark regression:** Dark suite still green; `lightTokens`/`darkTokens` in sync.

