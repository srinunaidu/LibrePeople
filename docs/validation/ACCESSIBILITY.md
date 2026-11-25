# Accessibility report — axe-core, WCAG 2.2 A/AA

**Request:** `QA-04` · **Lane:** qa-validation · **Date:** 2026-10-26
**Journey:** `frontend/e2e/accessibility.spec.ts` · **Rules:** `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`
**Result after the fixes below:** **21 of 21 pass** — 2 public pages, 18 signed-in pages, and 1 negative test that proves the harness detects a violation.

The contrast journey measures whether text is legible. This journey measures what a
screen reader depends on: names, roles, list structure, table semantics and keyboard
access. It is the first time the product has been checked for either.

---

## 1. The first run — 9 pages failed, 12 passed

| Rule | Impact | Pages | What it found |
|---|---|---|---|
| `listitem` | serious | `/people`, `/people/departments`, `/people/jobs`, `/people/locations`, `/platform`, `/recruiting` | The **starred** items in the secondary sidebar were `<li>` elements rendered directly inside a `<div>` — six pages exposed orphaned list items. |
| `color-contrast` | serious | `/dashboard` | Four trend figures used the success **fill** colour `#10b981` as text on white: **2.53:1**, against the 4.5:1 minimum. |
| `color-contrast` | serious | `/client-onboarding` | Four empty-state lines used `text-gray-400` (`#94a3b8`) on white: **2.56:1**. |
| `scrollable-region-focusable` | serious | `/reports` | Four horizontally scrollable table wrappers had no keyboard stop and no focusable content. |

Every other page — `/login`, `/`, `/time`, `/leave`, `/platform/payroll`,
`/platform/performance`, `/platform/learning`, `/platform/compliance`, `/import`,
`/jobs`, `/mfa` — passed on the first run.

## 2. The fixes

| Finding | Fix | File |
|---|---|---|
| Orphaned list items | The starred block is a `<ul>`; the items are its `<li>` children. | `frontend/src/components/shell/SecondarySidebar.tsx` |
| Success text at 2.53:1 | A **text** token, `--success-text` (`#047857` light, `#6ee7b7` dark), exactly as `--error-text` already existed for danger text. Trend figures use it; the fill colour keeps its meaning on surfaces. | `frontend/src/index.css`, `frontend/tailwind.config.js`, `frontend/src/components/ui/sparkline.tsx` |
| Grey text at 2.56:1 | The four lines use the semantic `text-fg-muted` instead of a raw grey. | `frontend/src/pages/ClientOnboarding.tsx` |
| Unreachable scroll regions | Each report table is a named `region` with `tabIndex={0}`; the shared `Table` component does the same for every table it renders. | `frontend/src/pages/Reports.tsx`, `frontend/src/components/ui/table.tsx` |

No rule was disabled, no page was excluded and no violation was accepted.

## 3. The negative test

`the harness itself › an image without a name is a violation` renders an `<img>` with
no `alt` and asserts that axe reports `image-alt`. If axe stops reporting — a broken
dependency, a silent configuration change — that test fails instead of the suite
passing because nothing was measured.

## 4. Where it runs

`.github/workflows/ci.yml` — the `journeys` job installs the backend dependencies,
Chromium and the frontend dependencies, then runs `npm run e2e`. The accessibility
journey is part of that run, so **a violation fails the build** and the job keeps
`frontend/test-results` as an artifact on failure. The same job also runs the two
frontend checks that were missing from the gate (`check:api-paths`, `check:classes`).

## 5. What is still open

- The `mobile` Playwright project still matches `responsive.spec.ts`, which does not
  exist; the 360/768/1024/1440 px journeys are `QA-02`, not this report.
- axe covers the rendered page in the light theme at desktop width. A manual keyboard
  pass is still a human task and is not claimed here.
