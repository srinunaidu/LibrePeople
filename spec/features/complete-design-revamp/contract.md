# Feature: complete-design-revamp

**Feature ID:** complete-design-revamp
**Risk tier:** 2 (design behavior across multiple files, tests required; no migrations; reversible)
**Frontend root:** `Karmathy/frontend/` — all `src/`, `e2e/`, `scripts/` paths below are relative to this folder (where `package.json` lives). Repo-root paths are written out fully.

## Goal
Complete design system revamp that makes the Karmathy portal cohesive, accessible, and on-brand: a token-first design system with two clearly separated modes (data-dense, compact app shell; expressive, editorial marketing), color-role discipline, a zero-tolerance form-labelling standard, tenant-scoped API headers, compact admin density, and typography fully backed by CSS variables. No code is pushed to `main`/production until the user visually confirms the redesign ("best"). All work happens on a feature branch.

## Design direction
"Token-first HCM dashboard with two clearly separated modes." Do not redesign for redesign's sake — the token system (`tokens.ts`, `tailwind.config.js`, `index.css`, `DESIGN_SYSTEM.md`) is good; the problem is inconsistent application.

**App mode** (`Layout`, authenticated pages): data-dense, utilitarian, smaller app typography scale (`h1-app/h2-app/h3-app`), surface/role color discipline, tight 4px-grid spacing, compact table rows.

**Marketing mode** (`PublicLayout`, `.mkt-root`, `pages/marketing/*`): expressive, editorial, larger marketing typography scale (`display/h1/h2/h3`), sticky glass nav, giant wordmark, brand-color-forward — consumes the marketing semantic map only, no hardcoded hex.

**Color role discipline:** brand→primary buttons/active nav/links/focus rings (never backgrounds/body text); surface→cards/sidebars/modals; fg→body/labels; red/amber/green→status only.

**Form labelling standard:** every `<input>`/`<select>`/`<textarea>` has a visible `<label htmlFor={id}>` matched by an `id`, OR is wired through `components/ui/inputs.tsx` which auto-binds label↔control. Required/optional marked inline. Errors via `aria-describedby`→`error-box` id. Zero label-less controls.

## Acceptance criteria

### Batch A (P0 — critical)
**AC-01 Inter font loads.** Inter declared in `tokens.ts`/`tailwind.config.js` actually reaches the browser: a `@font-face` block or Google Fonts `<link>` for Inter exists in `index.html`/`index.css`, and the computed `font-family` of `body` on an app page resolves to Inter (not the `system-ui` fallback).
- *Test:* open devtools → Computed → `font-family` on `/dashboard` body; must contain `Inter`. Grep `index.html` + `index.css` for `fonts.googleapis.com` or `@font-face` + `Inter` → ≥1 match.

**AC-02 Tenant theming is visible.** The stylesheet consumes `--tenant-primary`/`--tenant-secondary` (e.g. primary button background `var(--tenant-primary)` or `bg-[var(--tenant-primary)]`). On a tenant page where `TenantContext` sets `data-tenant`, a primary button's computed background equals the tenant's `primary_color`.
- *Test:* sign in to a tenant workspace, inspect a primary button, compare computed `background-color` to the tenant's `primary_color` from `/onboarding-portal/clients/by-slug/:slug`.

**AC-03 Mobile drawer uses lucide-react icons.** `components/Layout.tsx` mobile drawer nav links use `lucide-react` icons (2px stroke idiom per `DESIGN_SYSTEM.md`). Zero emoji characters (`📊 👥 ⏱ 📅 📈 🌴 📒 🎯 ⚙️ 💰 🧾 ⚙️ 🎁 📚 ⭐ 🧑 📈 📊 🔌 🧹 👤 🔄 🏢 🎨`) in the drawer.
- *Test:* grep `src/components/Layout.tsx` for emoji → 0 matches; grep for `lucide-react` import + icon components in drawer → present.

**AC-04 Zero unlabelled form controls.** The 7 labelling-defect pages — Recruiting (7), Scheduling (8), Leave (9), Offboarding (6), ClientOnboarding (6), Onboarding (3), Time (3) — have 0 label-less controls. Every `<input>`/`<select>`/`<textarea>` has a visible `<label htmlFor={id}>` matched by an `id`, OR goes through `components/ui/inputs.tsx` auto-binding. Required fields show inline "(required)"; errors use `aria-describedby`→`error-box` id.
- *Test:* run axe `label` rule on each of the 7 pages → 0 `label`/`aria-labelledby` violations; query each page for bare `<input` without an associated label → 0.

### Batch B (P1)
**AC-05 `marketing.css` hardcoded hex migrated.** `src/marketing.css` contains zero literal brand hex values (`#2563eb`, `#3b82f6`, `#93c5fd`, `#60a5fa`, …) outside CSS variable declarations. All brand colors reference `--brand-*`/`--fg-*`/marketing semantic tokens defined in `src/lib/tokens.ts` (`marketingSemantic` map).
- *Test:* grep `src/marketing.css` for literal hex → only `var(--...)` references or non-brand neutrals remain; confirm each referenced token exists in `tokens.ts` `marketingSemantic`.

**AC-06 Shared loading skeletons + empty states.** Authenticated list pages render `PageSkeleton`/`skeleton` while loading and an empty-state component (illustration + primary CTA + "learn more" link) when empty. `/platform` read-only lists (payroll/performance/benefits/learning/compliance) show empty states until create endpoints exist.
- *Test:* navigate to each list page → skeleton during load; empty state shows illustration + primary CTA + "learn more" link when data is absent.

**AC-07 ESLint + Vitest added; `check:design` extended.** ESLint config and Vitest config added to frontend/; `npm run lint` and `npm run test:unit` pass. `scripts/check-design-alignment.mjs` extended to assert component consistency (PageHeader/SectionCard `compact` usage) and layout quality (4px grid, no orphaned hardcoded text sizes on app pages).
- *Test:* `npm run lint` → 0 errors; `npm run test:unit` → green; `npm run check:design` → 0 violations.

**AC-08 axe-core e2e extended.** `e2e/accessibility.spec.ts` (and/or `e2e/design-alignment.spec.ts`) runs axe on all 7 labelling-defect pages + `/login` + create-flow + `/dashboard`; 0 critical/serious violations.
- *Test:* `npx playwright test accessibility` → pass on the extended page set.

### Batch C (P2)
**AC-09 Per-role RBAC in route guard.** The route guard checks the user's role before rendering role-gated routes; an unauthorized role gets a 403/redirect, not a blank page.
- *Test:* sign in as non-admin, navigate to `/admin/*` → blocked with 403 or redirect, no blank page.

**AC-10 `tokens.css` reconciled with `tokens.ts`.** `src/tokens.css` is either regenerated from `tokens.ts` (single `--brand-*` source of truth) or retired; no duplicate/divergent `--color-*` vs `--brand-*` names.
- *Test:* `npm run check:tokens` passes; grep `src/tokens.css` → only token names present in `tokens.ts`; no `--color-*` names diverging from `--brand-*`.

**AC-11 Two modes visually separated.** App pages render data-dense/compact app scale (`h1-app/h2-app/h3-app`, tight 4px grid); marketing pages under `.mkt-root` render editorial marketing scale (`display/h1/h2`, Space Grotesk, glass nav). No marketing hex leaks into app; no app compact classes leak into marketing.
- *Test:* computed heading sizes/fonts differ between `/` (marketing) and `/dashboard` (app); `.mkt-root` present on marketing pages, absent on app pages.

**AC-12 `/platform` read-only lists get empty states.** `/platform/payroll`, `/platform/performance`, `/platform/benefits`, `/platform/learning`, `/platform/compliance` each render an empty state (illustration + primary CTA + "learn more") when no data exists, until create endpoints exist.
- *Test:* navigate to each `/platform/*` list page → empty state visible when empty.

### Batch D
**AC-13 ClientOnboarding new-tab anchor.** `ClientOnboarding.tsx` uses `<a href="/t/${slug}/dashboard" target="_blank" rel="noopener noreferrer">` instead of `<Link>`.
- *Test:* click "Open workplace" → new tab opens at `/t/:slug/dashboard`.

**AC-14 `X-Tenant-Slug` header interceptor.** `src/lib/api.ts` axios request interceptor appends `X-Tenant-Slug` from `TenantContext` slug for all outgoing requests; skipped for public/login requests when no slug is available.
- *Test:* DevTools Network → any authenticated API request includes `X-Tenant-Slug`; `/login` request does not.

**AC-15 Admin pages use detected tenant slug.** All ~60 admin pages under `src/pages/admin/` use `useTenant().tenant.slug` or `detectTenantSlug()` instead of hardcoded `/clients/1/` (minimum set: ScheduledReporting, AvailabilityLeave, Certifications, FeatureFlags, LocaleConfig, ModuleEntitlements, IntegrationCredentials, UserAdmin, DataQuality, RetentionExport, ExitInterviews, PlanReconciliation, PlannedVsActual, PaySchedule, ShiftBasedAttendance, TimesheetLock).
- *Test:* grep `src/pages/admin/` for `/clients/1/` → 0 matches; each admin page imports `useTenant`/`detectTenantSlug`.

**AC-16 Compact admin fonts.** `TenantBranding.tsx:142` `text-3xl`→`text-lg`; `LearningAnalytics.tsx:76/80/84` `text-2xl`→`text-base`; `PlanReconciliation.tsx:76/80/84` `text-2xl`→`text-base`; `PlannedVsActual.tsx:83/87/91/95/100` `text-2xl`→`text-base`.
- *Test:* grep those files/lines → new classes present, old classes absent.

**AC-17 Compact density on all app pages.** `compact` prop applied to PageHeader + SectionCard on: TimeAttendance, Leave, LeaveLedger, Reports, Platform, PerformanceHub, BenefitsHub, LearningHub, Forecasting, ProjectStatus, ThemeStudio, DesignGallery, DataQuality, Import, Jobs, Mfa, EssHub, ClientOnboarding, Onboarding, Recruiting, Scheduling, RosterBuilder, People.
- *Test:* each listed page renders `<PageHeader compact>` / `<SectionCard compact>`.

**AC-18 Typography backed by CSS variables.** `--font-size-*` classes replace hardcoded `text-lg`/`text-xl`/`text-2xl`/`text-3xl` on all app pages; marketing pages exempt.
- *Test:* grep app pages (`src/pages/*` minus `marketing/`) for hardcoded `text-(xl|2xl|3xl)` → 0 matches (marketing pages allowed).

## Non-goals
- Backend tenant data filtering (backend must honor `X-Tenant-Slug` itself; frontend only sends the header).
- Marketing page redesign (exempt from compact/typography changes; marketing keeps its own scale).
- Route structure changes in `src/App.tsx`.
- E2E user-flow changes — e2e specs verify only; the axe-coverage extension in AC-08 is test-side instrumentation only.

## Interfaces / data
- No database schema or migrations (frontend-only change; reversible by branch deletion).
- Request-header contract: `X-Tenant-Slug` (sent by `src/lib/api.ts`, consumed by backend — backend enforcement out of scope).
- CSS variable contract: `--tenant-primary`/`--tenant-secondary` (+ derived `--tenant-primary-dark/-light/-text/-contrast`), `--brand-*`, `--font-size-*`, `--surface-*`, `--fg-*`.
- Existing helpers reused, not created: `detectTenantSlug()`, `useTenant()`, `deriveTheme()`, `data-tenant` attribute (all in `src/context/TenantContext.tsx`); `PageSkeleton` (`src/components/ui/page-skeleton`).
- Backwards compatible: no route changes, no public API changes, no breaking component prop changes (`compact` already optional).

## Files to touch (by batch)

**Batch A:**
- `src/lib/tokens.ts` — Inter font token (already present; ensure webfont load path documented)
- `src/index.css` — add `@font-face`/webfont link for Inter (or `index.html`)
- `src/components/Layout.tsx` — mobile drawer: lucide-react icons, 2px stroke, remove emoji
- `src/components/ui/inputs.tsx` — label/`htmlFor` auto-binding primitive (per open decision below)
- `src/components/ui/layout.tsx` — `Field` (already has `htmlFor`; keep)
- `src/pages/Recruiting.tsx`, `src/pages/Scheduling.tsx`, `src/pages/Leave.tsx`, `src/pages/Offboarding.tsx`, `src/pages/ClientOnboarding.tsx`, `src/pages/Onboarding.tsx`, `src/pages/TimeAttendance.tsx` — label every control per labelling standard
- `docs/DESIGN_SYSTEM.md` — record labelling standard + two-mode direction

**Batch B:**
- `src/marketing.css` — migrate hardcoded hex to `--brand-*`/marketing semantic tokens
- `src/lib/tokens.ts` — ensure `marketingSemantic` map covers all marketing colors used
- `src/components/ui/page-skeleton` / new empty-state component — skeleton + empty state (illustration + primary CTA + learn more)
- `src/lib/designSystem.ts` — shared empty-state / loading primitives
- ESLint config + Vitest config (new files) + `npm run lint` / `npm run test:unit` scripts
- `scripts/check-design-alignment.mjs` — extend to component consistency + layout quality
- `e2e/accessibility.spec.ts` — add 7 labelling pages + login + create-flow + dashboard
- `e2e/design-alignment.spec.ts` — extend page list if needed

**Batch C:**
- Route guard component — per-role enforcement
- `src/lib/tokens.ts`, `src/index.css`, `src/marketing.css` — two-mode token scoping (app vs `.mkt-root`)
- `src/tokens.css` — reconcile with/retire against `tokens.ts`
- `src/pages/platform/*` — empty states on read-only lists

**Batch D:**
- `src/pages/ClientOnboarding.tsx` — new-tab anchor
- `src/lib/api.ts` — verify interceptor (already present)
- `src/context/TenantContext.tsx` — verify `detectTenantSlug()` export (already present)
- `src/pages/admin/*.tsx` (~60 files) — replace `/clients/1/` with tenant slug
- `src/pages/admin/TenantBranding.tsx` — `text-3xl`→`text-lg`
- `src/pages/admin/LearningAnalytics.tsx` — `text-2xl`→`text-base` ×3
- `src/pages/admin/PlanReconciliation.tsx` — `text-2xl`→`text-base` ×3
- `src/pages/admin/PlannedVsActual.tsx` — `text-2xl`→`text-base` ×5
- `src/components/ui/layout.tsx` — PageHeader `compact` applied everywhere
- `src/components/ui/card.tsx` — SectionCard `compact` applied everywhere
- App pages for `compact`: `src/pages/TimeAttendance.tsx`, `src/pages/Leave.tsx`, `src/pages/LeaveLedger.tsx`, `src/pages/Reports.tsx`, `src/pages/Platform.tsx`, `src/pages/performance/PerformanceHub.tsx`, `src/pages/benefits/BenefitsHub.tsx`, `src/pages/learning/LearningHub.tsx`, `src/pages/Forecasting.tsx`, `src/pages/ProjectStatus.tsx`, `src/pages/ThemeStudio.tsx`, `src/pages/DesignGallery.tsx`, `src/pages/DataQuality.tsx`, `src/pages/Import.tsx`, `src/pages/Jobs.tsx`, `src/pages/Mfa.tsx`, `src/pages/ess/ESSHub.tsx`, `src/pages/Onboarding.tsx`, `src/pages/Recruiting.tsx`
- `src/lib/tokens.ts`, `src/index.css`, `src/tokens.css` — `--font-size-*` mappings present

## Step-by-step build plan
1. Create feature branch (never `main`): `git checkout -b feature/complete-design-revamp` (work in `Karmathy/`).
2. **Batch D (parallel with A/B):** `ClientOnboarding.tsx` new-tab anchor (AC-13).
3. **Batch D:** verify `api.ts` X-Tenant-Slug interceptor + skip public/login (AC-14).
4. **Batch D:** replace `/clients/1/` with tenant slug across ~60 admin pages (AC-15).
5. **Batch D:** compact admin fonts (TenantBranding, LearningAnalytics, PlanReconciliation, PlannedVsActual) (AC-16).
6. **Batch D:** `compact` prop on PageHeader/SectionCard across all listed app pages (AC-17).
7. **Batch D:** `--font-size-*` CSS variables replace hardcoded text sizes on app pages (AC-18).
8. **Batch A:** add Inter webfont load (`@font-face`/Google Fonts link) (AC-01).
9. **Batch A:** make tenant theming visible — stylesheet consumes `--tenant-primary`/`--tenant-secondary` (AC-02).
10. **Batch A:** mobile drawer lucide-react icons, 2px stroke, zero emoji (AC-03).
11. **Batch A:** fix all 42 unlabelled controls across the 7 pages per labelling standard (AC-04).
12. **Batch B:** migrate `marketing.css` hardcoded hex to marketing semantic map (AC-05).
13. **Batch B:** add shared loading skeleton + empty state (illustration + primary CTA + learn more); apply to `/platform` read-only lists (AC-06, AC-12 partial).
14. **Batch B:** add ESLint + Vitest; extend `check:design` to component consistency + layout quality (AC-07).
15. **Batch B:** extend axe e2e to 7 labelling pages + login + create-flow + dashboard (AC-08).
16. **Batch C:** per-role RBAC in route guard (AC-09).
17. **Batch C:** reconcile/retire `tokens.css` vs `tokens.ts` (AC-10).
18. **Batch C:** enforce two-mode visual separation (app compact vs `.mkt-root` editorial) (AC-11).
19. **Batch C:** `/platform` read-only lists empty states (AC-12 complete).
20. Run `npm run typecheck && npm run build && npm run verify` in `Karmathy/frontend/` — all green.
21. Run `npm run lint` and `npm run test:unit` — green (after Batch B adds them).
22. Run `npx playwright test` (design-alignment + accessibility) — pass; no new failures beyond pre-existing baseline.
23. Run `ci/run_backend_tests.sh` — unchanged, no regression.
24. Validation gate: 0 axe critical/serious on labelling pages; 0 `check:design` violations; typecheck/build/verify green.
25. Do NOT push to `main`/production. Wait for user visual review and confirmation ("best") before any push.

## Test command
- Frontend (from `Karmathy/frontend/`): `npm run typecheck && npm run build && npm run verify`
- Unit/lint (added in Batch B): `npm run lint && npm run test:unit`
- E2E: `npx playwright test` (runs `design-alignment.spec.ts` + `accessibility.spec.ts`)
- Backend gate (unchanged): `ci/run_backend_tests.sh`

## Validation gate
- 0 axe critical/serious violations on the 7 labelling-defect pages + `/login` + create-flow + `/dashboard`.
- 0 `check:design` violations (`npm run check:design`).
- `npm run typecheck && npm run build && npm run verify` all green.
- Visual review confirmation required before any push to `main`/production ("best" from user).

## Risks / edge cases
- **Backend tenant data filtering:** frontend sends `X-Tenant-Slug`, but backend must honor it; without backend changes admin pages send the correct slug but may still return all-data or client-1 data. Flag to user; frontend cannot fix.
- **~60 admin pages each need tenant context:** every admin page must import `useTenant`/`detectTenantSlug()`; some pages may lack tenant context availability.
- **New tab loses in-flight state:** `/t/:slug/dashboard` opens a fresh SPA instance; TenantProvider re-detects slug from path, but unsaved form state is lost.
- **Compact over-density:** `compact` on all pages may make some pages too dense; iterate after visual review.
- **API interceptor must not break public/login requests:** skip header when slug unavailable (public routes, login).
- **Marketing hex migration:** `marketing.css` literal hex must be replaced without breaking the dark-first marketing aesthetic.

## Open decisions (lead must resolve before building)
1. Is `[data-tenant]` + `deriveTheme()` actually implemented or aspirational? `TenantContext.tsx` already sets `data-tenant` and calls `deriveTheme()` — confirm stylesheet consumption exists or must be added (AC-02).
2. Is `packages/tokens/` Style Dictionary output consumed by the app or orphaned? Determines whether `tokens.css` is regenerated (AC-10) or retired.
3. Does `components/ui/inputs.tsx` already support label/`htmlFor` binding? Currently `Input`/`Textarea`/`Select` are raw inputs without label binding — single primitive change (inputs.tsx) vs per-page wiring in all 7 labelling pages.
4. Is PageHeader/Breadcrumb used by ALL authenticated pages or only some? Determines coverage of AC-17 compact application.
5. Route taxonomy: which of the ~100+ routes are marketing vs app vs admin? Needed to scope AC-11 two-mode separation and AC-18 typography variable replacement.
6. Is there a Figma source of truth `docs/DESIGN_SYSTEM.md` maps to? Determines whether token tweaks need design sign-off.
