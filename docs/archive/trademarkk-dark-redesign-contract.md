# Feature: TradeMarkk Dark Redesign (obsidian compact shell)

## Behavior
Authenticated Karmathy HCM UI is restyled to an ultra-compact obsidian-dark "TradeMarkk" aesthetic: single 220px unified sidebar with categorized nav groups and a bottom-pinned TenantSwitcher, 48px compact TopBar, purple accent (#7C5CFF), high-density cards. All routing (/t/:slug/* and bare routes), role gating, keyboard shortcuts, and business logic are preserved. Zero functional regressions; all static checks and Playwright E2E pass.

## Acceptance criteria
1. Every existing CSS variable name in `src/tokens.css` survives; `bg-surface`/`text-fg-muted`/`border-border` classes still resolve — verified by `npm run check:tokens && npm run check:classes` (exit 0).
2. Token values match spec: `--bg #0B0B0F`, `--bg-shell #121217`, `--surface #15151C`, `--surface-elevated`/`--surface-hover #1C1C26`, `--bg-input #0F0F14`, `--border #1F1F27`, `--border-strong #2A2A35`, `--accent`/`--primary #7C5CFF` (hover #6A48F5, tint rgba(124,92,255,0.14)); status = emerald #34D399 / amber #FBBF24 / coral #F87171 on 14% tints — verified by grep of `src/tokens.css` for each literal.
3. `--sidebar-width: 220px`, `--topbar-height: 48px`, `--radius-md: 8px`, compact `--space-md`/`--space-lg` (12–16px card padding), and `font-variant-numeric: tabular-nums` on counters, tables, payroll figures, timestamps — verified by grep + `npm run check:design` (exit 0).
4. `src/context/TenantContext.tsx` is unmodified (git diff empty for that file) and contrast.spec.ts, contrast-light.spec.ts and tenant e2e tests remain green (WCAG AA preserved).
5. Exactly ONE sidebar renders on desktop >=1024px: width 220±2px, `background: var(--bg-shell)`, `border-right: var(--border)`, containing brand header, full-width purple "+ Quick Action" CTA (dispatches `karmathy:open-command-palette` CustomEvent), four groups with 10px uppercase tracked micro-labels (OVERVIEW, CORE HR & ESS, TIME & PAYROLL, PLATFORM & ADMIN), bottom-pinned TenantSwitcher — verified by `frontend/e2e/redesign-e2e.spec.ts` test (a).
6. Every nav item navigates to its existing App.tsx route unchanged (~145 `/admin/*` routes remain 1-click reachable via expandable Admin console sub-items) — verified by `npm run check:routes` (exit 0) + redesign-e2e (d) route sweep.
7. TenantSwitcher: fetches `listClients()` from `src/lib/api.ts`, shows active slug via `useTenant`, offers default (no-slug) workspace option; selecting a tenant lands on `/t/:slug/dashboard` (current sub-route via `useTenantNav` acceptable) — verified by redesign-e2e (c) tenant-switch test.
8. TopBar is a single compact 48px row: breadcrumb/page title left, Cmd+K trigger dispatching the same CustomEvent, ThemeToggle, compact user/role badge; mobile drawer from Layout still opens/closes — verified by redesign-e2e (a) + existing `responsive.spec.ts` unchanged and green.
9. Keyboard shortcuts and CommandPalette unaffected: `src/lib/keyboard.ts` `registerGoto` and Cmd+K both open the palette — verified by existing navigation.spec.ts remaining green.
10. Dashboard renders "Needs your action" banner, Open requisitions with "View", Compliance violations with "Review", Tenant health table; `/admin/feature-flags` toggle state persists across reload — verified by redesign-e2e (b).
11. `/admin/tenant-branding`, `/admin/locale-config`, `/admin/entitlements`, `/admin/user-admin` load with zero console errors and zero failed network requests — verified by redesign-e2e (c).
12. `/ess`, `/people`, `/recruiting`, `/time`, `/scheduling`, `/leave`, `/platform/payroll/overview`, `/reports` each return HTTP 200, show visible main content, zero uncaught page errors — verified by redesign-e2e (d).
13. Hardcoded hex values and inline `style={{}}` removed from ProjectStatus.tsx, Design.tsx, DesignGallery.tsx, forecasting/shared.tsx, admin/TenantBranding.tsx (token vars instead) — verified by grep for `#[0-9a-fA-F]{3,6}` and `style={{` in those files returning no production matches (exempt: ThemeStudio.tsx, TenantContext.tsx, lib/tokens.ts, tokens.css, marketing.css definitions).
14. Full gate: `npm run typecheck && npm run lint && npm run check:routes && npm run check:api-paths && npm run check:classes && npm run check:tokens && npm run check:design && npm run test:unit` exit 0; `npm run build` succeeds; `npm run e2e` all green (desktop + responsive, local SQLite harness port 8010 — never production).
15. No horizontal overflow at viewport widths 360/768/1024/1440 — verified by redesign-e2e (a) `document.documentElement.scrollWidth <= innerWidth`.

## Non-goals
- No route renames/additions/removals in App.tsx; no changes to ProtectedRoute role strings.
- No backend, API, schema, or migration changes; no changes to `src/lib/api.ts` request shapes.
- No changes to ThemeStudio.tsx swatches, TenantContext WCAG math or deriveTheme, lib/tokens.ts + tokens.css variable-name set.
- No light-theme removal: light mode keeps working via token swap; contrast-light.spec.ts must pass.
- No redesign of marketing/public pages (login, PublicLayout) beyond token inheritance.

## Interfaces / data
- New file: `src/components/shell/TenantSwitcher.tsx` (self-contained via `useTenant` + `listClients()`).
- CustomEvent contract unchanged: `karmathy:open-command-palette` is the single palette-open channel (sidebar CTA + Cmd+K trigger both dispatch it).
- Token additions allowed: `--sidebar-width`, `--topbar-height` (new names, additive — existing names untouched).
- Backwards compat: data-tenant accent overrides, tenantPath helpers, tenantSlugStore, queryClient untouched.
- E2E: new `frontend/e2e/redesign-e2e.spec.ts`; selector edits permitted ONLY in `navigation.spec.ts` and `design-alignment.spec.ts`.

## Test plan
Phase 1 — Tokens: edit `src/tokens.css`, `src/lib/tokens.ts`, `src/index.css` values only. Verify: `npm run check:tokens && npm run check:classes && npm run typecheck`.
Phase 2 — Shell: rewrite `Layout.tsx`, `shell/WorkspaceRail.tsx`, `shell/SecondarySidebar.tsx`, `shell/TopBar.tsx` into one sidebar; add `shell/TenantSwitcher.tsx`. Verify: `npm run check:routes && npm run check:api-paths && npm run typecheck && npm run lint`.
Phase 3 — Screens: restyle Dashboard, admin/FeatureFlags, admin/TenantBranding, admin/ESSProfile, ess/ESSHub; strip hardcoded hex/inline styles from ProjectStatus, Design, DesignGallery, forecasting/shared.tsx, admin/TenantBranding. Verify: `npm run check:classes && npm run check:design && npm run test:unit`.
Phase 4 — Gates: write `redesign-e2e.spec.ts`, update stale selectors in navigation.spec.ts / design-alignment.spec.ts only. Then full sequence: `npm run typecheck && npm run lint && npm run check:routes && npm run check:api-paths && npm run check:classes && npm run check:tokens && npm run check:design && npm run test:unit && npm run build && npm run e2e` (harness auto-starts; port 4173 frontend / 8010 backend).

## Risk tier
2 (normal): large visual refactor; no irreversible or data-layer changes.

## Rollback
Git revert of the feature branch commits restores the double-rail shell and prior tokens; tokens.css changes are value-only, so revert is atomically safe. No data migration to unwind.

## Risk notes
- Sidebar merge may break design-alignment.spec.ts "card padding is consistent" and font-size tests if paddings drift between pages — keep card padding on `--space-md`/`--space-lg` exclusively. (No pixel sidebar assertions exist today; adding any in redesign-e2e should use ±2px tolerance.)
- contrast.spec.ts / contrast-light.spec.ts AA thresholds: #7C5CFF on #0B0B0F and emerald/amber/coral-on-tint pairs must be checked; prefer tint backgrounds with lighter text for badges.
- ~145 admin routes in one group: sub-item collapse must not hide routes from check-routes or add render jank on Dashboard; Admin console expand must be a single click.
- Playwright flake: new spec reuses navigation.spec.ts login pattern (ADMIN_USERNAME "admin", #login-username/#login-password, E2E_ADMIN_PASSWORD bootstrap) to avoid divergent harness assumptions.
- TenantSwitcher + tenantSlugStore interplay: switching tenants must not leave stale query cache — invalidate via existing queryClient (do not bypass it).

## Do NOT touch
- `src/context/TenantContext.tsx` (deriveTheme, WCAG math), `src/pages/admin/ThemeStudio.tsx` swatches, `src/lib/tokens.ts` + `src/tokens.css` variable NAMES, `src/lib/keyboard.ts` registerGoto logic, `src/App.tsx` route paths (L173-430), `src/components/ProtectedRoute.tsx` role strings, `src/lib/api.ts` request/response shapes, all backend files, e2e specs other than navigation/design-alignment (+ the new redesign-e2e.spec.ts).

## Open decisions
None — scope approved. If the validator finds nav routes in App.tsx not covered by the four groups, escalate to lead rather than renaming routes.
