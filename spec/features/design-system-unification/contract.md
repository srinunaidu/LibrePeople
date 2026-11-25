---
# Feature: design-system-unification

**Feature ID:** design-system-unification
**Contract path:** spec/features/design-system-unification/contract.md
**Tier:** Tier 2 (new behavior across multiple files — CSS tokens, components, pages; tests required)

## Goal
Create a single source of truth design system: all pages align to global CSS variables from tokens.ts/index.css, mk-* primitives are globally available (not marketing-scoped), no individual component hardcoded colors, all components use semantic tokens.

## Acceptance criteria

**AC-01** All `mk-*` primitives (mk-card, mk-cta, mk-chip, mk-reveal, mk-ghost, mk-link, mk-marquee, mk-grid, mk-noise, mk-kicker, mk-h1, mk-h2, mk-gradient-text, mk-eyebrow, mkt-nav, mk-window, mk-float, mk-pulse, mk-wordmark) are globally available — NOT scoped under `.mkt-root`. Remove `.mkt-root` prefix from all primitive rules in marketing.css.

**AC-02** `Button` component (`src/components/ui/button.tsx`) uses globally-available classes. The `danger` variant must NOT hardcode `bg-red-600 hover:bg-red-700`; it must use semantic `--error`/`--error-text` tokens or a global token-based class.

**AC-03** All hardcoded color sites replaced with semantic token references:
- button.tsx:13 — danger variant
- TopBar.tsx:136 — hover:bg-red-50
- Homepage.tsx:143 — bg-blue-400
- Homepage.tsx:200-201 — inline #67e8f9, #c4b5fd
- PublicLayout.tsx:98-99, 166-167 — inline linear-gradient
- TimeAttendance.tsx:146 — dark:text-amber-300
- AccuracyTab.tsx:369 — bg-red-100; 384 — text-amber-600
- 14 admin pages — text-amber-600

**AC-04** Token inconsistencies fixed:
- marketingSemantic brand/teal/green/violet ramp complete (50-950) in tokens.ts
- --font-display defined in index.css
- Tailwind radius maps 2xl (24px)
- dark .text-gray-100/200/300 remapped in index.css
- .dark[data-tenant] .surface-raised uses var(--surface-raised) not hardcoded #1e293b

**AC-05** tokens.css stays in sync with index.css/tokens.ts

**AC-06** `npm run verify` passes (typecheck, check:routes, check:api-paths, check:design, build, check:classes)

**AC-07** All changes committed to main

## Files to touch
- frontend/src/marketing.css
- frontend/src/index.css
- frontend/src/lib/tokens.ts
- frontend/src/tailwind.config.js
- frontend/src/components/ui/button.tsx
- frontend/src/components/shell/TopBar.tsx
- frontend/src/pages/Homepage.tsx
- frontend/src/components/PublicLayout.tsx
- frontend/src/pages/TimeAttendance.tsx
- frontend/src/pages/forecasting/AccuracyTab.tsx
- frontend/src/pages/admin/*.tsx (14 files with text-amber-600)

## Test command
Frontend: `npm run verify`
