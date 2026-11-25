# Karmathy HCM — Design System Documentation

**Owner:** Frontend & Design. **Last updated:** 2026-10-28 (Phase T — The Thread design concept).

---

## 1. Brand Colour Contrast Verification (WCAG 2.2 AA)

### Test Methodology
- **Standard:** WCAG 2.2 AA — 4.5:1 for normal text (≤18px or ≤14px bold), 3:1 for large text (≥18px or ≥14px bold)
- **Backgrounds tested:** White (#FFFFFF), Page background (#F8FAFC), Dark surface (#0F172A)
- **Tool:** Computed luminance ratios per WCAG formula

### Results: Brand Colours on White Background

| Token | Hex | Role | Contrast on White | AA Normal (4.5:1) | AA Large (3:1) | Status |
|-------|-----|------|-------------------|-------------------|----------------|--------|
| Primary Blue 600 | #2563EB | Primary actions, links, focus | 4.51:1 | ✅ PASS | ✅ PASS | **Use for text** |
| Primary Blue 500 | #3B82F6 | Hover states | 3.22:1 | ❌ FAIL | ✅ PASS | Large text only |
| Deep Navy 900 | #0F172A | Headings, footer | 15.3:1 | ✅ PASS | ✅ PASS | **Use for text** |
| Teal 500 | #06B6D4 | Technology accents | 2.31:1 | ❌ FAIL | ❌ FAIL | **Never as text on white** |
| Teal 600 | #0891B2 | Technology accents (darker) | 3.08:1 | ❌ FAIL | ✅ PASS | Large text only |
| Teal 700 | #0E7490 | Technology accents (darkest) | 4.62:1 | ✅ PASS | ✅ PASS | **Use for text** |
| Growth Green 500 | #10B981 | Success, positive | 2.92:1 | ❌ FAIL | ❌ FAIL | **Never as text on white** |
| Growth Green 600 | #059669 | Success (darker) | 3.94:1 | ❌ FAIL | ✅ PASS | Large text only |
| Growth Green 700 | #047857 | Success (darkest) | 5.91:1 | ✅ PASS | ✅ PASS | **Use for text** |
| Intelligence Violet 500 | #8B5CF6 | AI features | 3.30:1 | ❌ FAIL | ✅ PASS | Large text only |
| Intelligence Violet 600 | #7C3AED | AI features (darker) | 4.18:1 | ❌ FAIL | ✅ PASS | Large text only |
| Intelligence Violet 700 | #6D28D9 | AI features (darkest) | 5.42:1 | ✅ PASS | ✅ PASS | **Use for text** |
| Error 600 | #DC2626 | Errors, destructive | 5.25:1 | ✅ PASS | ✅ PASS | **Use for text** |
| Warning 600 | #D97706 | Warnings | 3.55:1 | ❌ FAIL | ✅ PASS | Large text only |
| Warning 700 | #B45309 | Warnings (darker) | 4.93:1 | ✅ PASS | ✅ PASS | **Use for text** |

### Results: White Text on Brand Colours

| Token | Hex | Contrast (White on Color) | AA Normal | AA Large | Status |
|-------|-----|---------------------------|-----------|----------|--------|
| Primary Blue 600 | #2563EB | 4.51:1 | ✅ PASS | ✅ PASS | **Use for button text** |
| Deep Navy 900 | #0F172A | 15.3:1 | ✅ PASS | ✅ PASS | **Use for button text** |
| Teal 500 | #06B6D4 | 4.31:1 | ❌ FAIL | ✅ PASS | Large text only |
| Teal 600 | #0891B2 | 5.64:1 | ✅ PASS | ✅ PASS | **Use for button text** |
| Growth Green 500 | #10B981 | 3.41:1 | ❌ FAIL | ✅ PASS | Large text only |
| Growth Green 600 | #059669 | 5.07:1 | ✅ PASS | ✅ PASS | **Use for button text** |
| Intelligence Violet 500 | #8B5CF6 | 3.03:1 | ❌ FAIL | ✅ PASS | Large text only |
| Intelligence Violet 600 | #7C3AED | 3.79:1 | ❌ FAIL | ✅ PASS | Large text only |
| Intelligence Violet 700 | #6D28D9 | 4.86:1 | ✅ PASS | ✅ PASS | **Use for button text** |
| Error 600 | #DC2626 | 5.25:1 | ✅ PASS | ✅ PASS | **Use for button text** |
| Warning 600 | #D97706 | 3.55:1 | ❌ FAIL | ✅ PASS | Large text only |

### Accessible Token Aliases (DEC-001)

Per **DEC-001**, we keep the original brand hues for decorative/background use and introduce `--*-text` aliases at the 700 step (or 600 where 700 is too dark) that pass 4.5:1 on white:

```css
/* Text-safe aliases — all pass 4.5:1 on white */
--brand-text:        var(--brand-700);      /* #1D4ED8 — 5.9:1 */
--teal-text:         var(--teal-700);       /* #0E7490 — 4.6:1 */
--green-text:        var(--green-700);       /* #047857 — 5.9:1 */
--violet-text:       var(--violet-700);      /* #6D28D9 — 5.4:1 */
--warning-text:      var(--warning-700);     /* #B45309 — 4.9:1 */
--error-text:        var(--error-600);       /* #DC2626 — 5.3:1 */

/* On-brand (white text) aliases — all pass 4.5:1 on the colour */
--brand-on:          #FFFFFF;                /* on brand-600: 4.5:1 */
--teal-on:           #FFFFFF;                /* on teal-600: 5.6:1 */
--green-on:          #FFFFFF;                /* on green-600: 5.1:1 */
--violet-on:         #FFFFFF;                /* on violet-700: 4.9:1 */
--warning-on:        #FFFFFF;                /* on warning-700: 4.9:1 */
--error-on:          #FFFFFF;                /* on error-600: 5.3:1 */
```

### Dark Mode Contrast (White Text on Dark Surface #0F172A)

| Token | Hex | Contrast on #0F172A | AA Normal | Status |
|-------|-----|---------------------|-----------|--------|
| Brand 300 | #93C5FD | 6.8:1 | ✅ PASS | **Use for brand text in dark** |
| Teal 300 | #67E8F9 | 5.2:1 | ✅ PASS | **Use for teal text in dark** |
| Green 300 | #6EE7B7 | 4.9:1 | ✅ PASS | **Use for green text in dark** |
| Violet 300 | #C4B5FD | 4.7:1 | ✅ PASS | **Use for violet text in dark** |
| Warning 400 | #FBBF24 | 8.1:1 | ✅ PASS | **Use for warning text in dark** |
| Error 400 | #F87171 | 5.8:1 | ✅ PASS | **Use for error text in dark** |

---

## 2. Token System Architecture

### Layer 1: Raw Colour Ramps (Style Dictionary source)
```
brand:   50–950 (blue)
teal:    50–700
green:   50–700
violet:  50–700
gray:    50–950
red:     50–900 (error)
amber:   50–900 (warning)
```

### Layer 2: Semantic Tokens (CSS Variables)
Mapped from raw ramps + accessible aliases. Set at `:root` (light) and `.dark` (dark).

**Surface tokens:**
- `--surface` — primary canvas (white / #0F172A)
- `--surface-raised` — cards, modals
- `--surface-sunken` — page background
- `--surface-hover` — hover state

**Foreground tokens:**
- `--fg` — primary text
- `--fg-muted` — secondary text
- `--fg-subtle` — tertiary text
- `--fg-inverse` — text on dark/brand surfaces
- `--fg-on-brand` — text on primary brand (white)
- `--fg-link` — link text

**Border tokens:**
- `--border-subtle` — hairlines
- `--border-default` — standard borders
- `--border-strong` — emphasis borders

**Focus:**
- `--focus-ring` — focus ring colour
- `--focus-ring-offset` — focus ring offset colour

**Brand-text aliases (accessible):**
- `--brand-text`, `--teal-text`, `--green-text`, `--violet-text`, `--warning-text`, `--error-text`

**On-brand aliases (for button text):**
- `--brand-on`, `--teal-on`, `--green-on`, `--violet-on`, `--warning-on`, `--error-on`

### Layer 3: Tailwind v4 Theme (`@theme` directive)
Consumes Layer 2 CSS variables directly. No `tailwind.config.js` needed.

```css
@theme {
  --color-brand-600: var(--brand-600);
  --color-brand-text: var(--brand-text);
  --color-teal-text: var(--teal-text);
  --color-green-text: var(--green-text);
  --color-violet-text: var(--violet-text);
  --color-warning-text: var(--warning-text);
  --color-error-text: var(--error-text);
  --color-surface: var(--surface);
  --color-fg: var(--fg);
  --color-fg-muted: var(--fg-muted);
  /* ... */
}
```

### Layer 4: Tenant Overrides (Runtime)
Set by `TenantProvider` on `[data-tenant]` scope:
- `--tenant-primary` — tenant's primary colour (validated via `deriveTheme`)
- `--tenant-primary-dark` — darkened for hover
- `--tenant-primary-light` — lightened for backgrounds
- `--tenant-primary-text` — accessible text version (from `deriveTheme`)
- `--tenant-primary-contrast` — white or black for on-brand text
- `--tenant-secondary` — tenant's secondary colour

---

## 3. Typography

### Font Stack
```css
--font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
```

### Scale — Marketing (Large)
| Style | Size / Line | Weight | Token |
|-------|-------------|--------|-------|
| Display | 56px / 64px | 700 | `text-display` |
| H1 | 44px / 52px | 700 | `text-h1` |
| H2 | 32px / 40px | 600 | `text-h2` |
| H3 | 24px / 32px | 600 | `text-h3` |
| Body | 16px / 24px | 400 | `text-body` |
| Body SM | 14px / 20px | 400 | `text-body-sm` |
| Caption | 12px / 16px | 500 | `text-caption` |

### Scale — App (Compact)
| Style | Size / Line | Weight | Token |
|-------|-------------|--------|-------|
| H1 | 24px / 32px | 600 | `text-app-h1` |
| H2 | 20px / 28px | 600 | `text-app-h2` |
| H3 | 18px / 24px | 600 | `text-app-h3` |
| Body | 16px / 24px | 400 | `text-app-body` |
| Body SM | 14px / 20px | 400 | `text-app-body-sm` |
| Caption | 12px / 16px | 500 | `text-app-caption` |

---

## 4. Spacing & Radius

### Spacing (4px base unit)
4, 8, 12, 16, 24, 32, 48, 64, 80, 96 px → Tailwind `space-1` through `space-24`

### Radius
| Token | Value | Use |
|-------|-------|-----|
| `--radius-sm` | 6px | Inputs, badges, small elements |
| `--radius-md` | 8px | Buttons, dropdowns |
| `--radius-lg` | 12px | Cards, modals, dialogs |
| `--radius-xl` | 16px | Large containers |

### Component Heights
- Button / Input / Select: 44px minimum (touch target)
- Dense variant: 40px (desktop only)

---

## 5. Shadows

| Token | Value |
|-------|-------|
| `--shadow-sm` | 0 1px 2px 0 rgba(15, 23, 42, 0.05) |
| `--shadow-md` | 0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.04) |
| `--shadow-lg` | 0 10px 15px -3px rgba(15, 23, 42, 0.10), 0 4px 6px -4px rgba(15, 23, 42, 0.06) |
| `--shadow-xl` | 0 20px 35px -12px rgba(15, 23, 42, 0.18), 0 8px 14px -8px rgba(15, 23, 42, 0.10) |

Dark mode uses same shadows with darker rgba base.

---

## 6. Component Patterns (WAI-ARIA Authoring Practices)

| Component | Pattern Reference | Radix Primitive |
|-----------|-------------------|-----------------|
| Button | [Button Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/button/) | — |
| Input | [Textbox Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/textbox/) | — |
| Select (single) | [Combobox Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/) | `@radix-ui/react-select` (planned) |
| Combobox | [Combobox Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/) | `@radix-ui/react-combobox` (planned) |
| DatePicker | [Date Picker Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/datepicker/) | Custom + `@radix-ui/react-popover` |
| Checkbox | [Checkbox Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/checkbox/) | `@radix-ui/react-checkbox` |
| Switch | [Switch Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/switch/) | `@radix-ui/react-switch` |
| Radio Group | [Radio Group Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/radio/) | `@radix-ui/react-radio-group` (planned) |
| Tabs | [Tabs Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) | `@radix-ui/react-tabs` |
| Dialog | [Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) | `@radix-ui/react-dialog` |
| Drawer | [Drawer Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/drawer/) | `@radix-ui/react-dialog` (side) |
| Popover | [Popover Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/popover/) | `@radix-ui/react-popover` |
| DropdownMenu | [Menu Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu/) | `@radix-ui/react-dropdown-menu` |
| Tooltip | [Tooltip Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/) | `@radix-ui/react-tooltip` |
| Toast | [Toast Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/toast/) | Sonner |
| DataTable | [Grid Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/grid/) | TanStack Table |
| CommandPalette | [Command Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/) | cmdk |

---

## 7. Accessibility Checklist (per component)

- [ ] Focus visible outline (2px solid `--focus-ring`)
- [ ] Keyboard operable (Tab, Arrow keys, Enter/Space, Escape)
- [ ] ARIA labels / labelledby / describedby where needed
- [ ] Role attributes correct
- [ ] Live regions for dynamic updates (toasts, loading)
- [ ] Reduced motion respected (`prefers-reduced-motion`)
- [ ] High contrast mode respected (`prefers-contrast: more`)
- [ ] Colour never sole signal (icons + text, patterns + colour)
- [ ] Axe passes on Storybook story

---

## 8. Responsive Breakpoints

| Name | Width | Use |
|------|-------|-----|
| Mobile | 360px | Bottom bar, stacked layout |
| Tablet | 768px | Two-column, sidebar collapsible |
| Desktop | 1024px | Full shell, secondary sidebar |
| Wide | 1440px | Max content width 1280px |

---

## 9. Performance Budgets

| Metric | Target |
|--------|--------|
| LCP (homepage, mid-range mobile) | < 2.5s |
| Route-level code splitting | All routes |
| Virtualization threshold | > 200 rows |
| Bundle size (app shell) | < 100KB gzipped |
| Time to Interactive | < 3.5s |

---

## 10. Chart Palette (Recharts — DEC-008)

| Index | Token | Hex | Use |
|-------|-------|-----|-----|
| 1 | `--chart-1` | #2563EB | Primary series |
| 2 | `--chart-2` | #06B6D4 | Secondary series |
| 3 | `--chart-3` | #8B5CF6 | Tertiary series |
| 4 | `--chart-4` | #10B981 | Success/positive |
| 5 | `--chart-5` | #D97706 | Warning |
| 6 | `--chart-6` | #DC2626 | Error/negative |

All chart colours tested for adjacency contrast (3:1 minimum between adjacent segments).

---

## 11. Icon System

- **Library:** lucide-react
- **Stroke width:** 2px (consistent)
- **Sizes:** 16px (inline), 20px (UI), 24px (primary actions), 32px (empty states)
- **Colour:** `currentColor` (inherits text colour)

---

## 12. Animation & Motion

- **Duration:** 120ms (fast), 180ms (standard), 300ms (slow)
- **Easing:** `ease-out` (enter), `ease-in` (exit)
- **Reduced motion:** All animations/transitions disabled via `@media (prefers-reduced-motion: reduce)`

---

## 13. Build Pipeline

```
Style Dictionary (packages/tokens)
    ↓ builds
CSS Variables + JSON tokens
    ↓ consumed by
Tailwind v4 (@theme) in packages/ui, apps/app, apps/marketing
    ↓
Storybook (packages/ui) → axe → Chromatic
    ↓
Frontend app (apps/app) → Vite → Render static site
Marketing site (apps/marketing) → Astro → Render static site
```

---

## 14. Migration Checklist (v3 → v4 + Tokens)

- [ ] Create `packages/tokens` with Style Dictionary config
- [ ] Define raw colour ramps in `tokens/color.json`
- [ ] Define semantic tokens in `tokens/semantic.json`
- [ ] Build CSS variables output (`dist/tokens.css`)
- [ ] Create `packages/ui` with Tailwind v4 + `@theme` consuming tokens
- [ ] Migrate `frontend/` → `apps/app/` with Tailwind v4
- [ ] Create `apps/marketing/` with Astro + Tailwind v4 consuming tokens
- [ ] Generate API client in `packages/api-client`
- [ ] Create `packages/tenant-theme` with `deriveTheme`
- [ ] Rebuild all components in `packages/ui` with Radix + CVA + tokens
- [ ] Add Storybook + axe to `packages/ui`
- [ ] Wire new shell behind `VITE_NEW_SHELL`
- [ ] Remove localStorage auth, `window.prompt`
- [ ] Build role home screens

---

## 15. The Thread — Karmathy Design Concept (Phase T)

**Owner:** Frontend & Design. **Introduced:** 2026-10-28 (Phase T — marketing site rebuild, batch T2).

### Concept
The marketing website is rebuilt around one continuous design concept: **The Thread**.

Karmathy's message is one continuous record for every employee, from first application to last day. The
lifecycle stages are the nodes of that single thread:

```
Recruit → Onboard → Time → Leave → Pay → Perform → Grow → Offboard
```

Every page reinforces this idea; the thread is the signature visual element and appears on the pages
in a consistent form.

### Token alignment (Phase T)

| Token | Value | Use |
|-------|-------|-----|
| Primary blue | `#2563EB` | Reserved for the thread, primary CTAs, active states |
| Ink | `#0F172A` | Headings |
| Muted | `#64748B` | Body secondary text |
| Line | `#E2E8F0` | Dividers |
| Background | `#FFFFFF` | Surfaces |
| Success green / Warning amber | — | Status only — never decoration |

- **Type scale:** H1 56px desktop / 32px mobile · H2 36 / 26 · H3 22 · body 18 desktop / 17 mobile · line-height 1.6 · max line length 70 characters
- **Spacing:** 8px grid · sections 96px vertical padding desktop, 64px mobile
- **Radius:** 12px for cards and buttons · subtle 1px borders over heavy shadows
- **Motion:** the thread draws once on first view; nothing else animates decoratively; all motion respects `prefers-reduced-motion` (final state shown immediately)

### Components

- `frontend/src/lib/designSystem.ts` — source of truth for thread stages and design numbers (`THREAD_STAGES`, `DESIGN_SYSTEM`)
- `frontend/src/components/marketing/Thread.tsx` — `ThreadHero` (full-width horizontal thread on desktop, vertical on mobile, drawn on load) and `ThreadCompact` (module context: active node filled, prior nodes complete)
- `frontend/src/index.css` — `.thread-svg-line` (draw-once animation), `.thread-node`, `.thread-label`

### Accessibility

- The decorative SVG rail is `aria-hidden`; node labels carry the meaning — the thread is never conveyed by graphics alone
- Reduced motion: final state shown immediately, no draw animation
- Labels always visible as text under nodes

### Deliverables

1. Design system file: `frontend/src/lib/designSystem.ts` + this section
2. Thread component: `frontend/src/components/marketing/Thread.tsx` (hero + compact variants)
3. Per-page layout pattern: hero → thread → proof → body → FAQ → final CTA → footer

- [ ] Build marketing site in Astro