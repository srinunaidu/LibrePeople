# Responsive report — 360, 768, 1024 and 1440 px

**Request:** `QA-02` · **Lane:** qa-validation · **Date:** 2026-10-26
**Journey:** `frontend/e2e/responsive.spec.ts` · **Project:** `responsive` · **Widths:** 360, 768, 1024, 1440 px
**Result after the fixes below:** **16 of 16 pass** — four widths, four assertions each.

The `mobile` Playwright project matched `responsive.spec.ts`, which did not exist. It ran zero
tests while the run summary read "passed", so the product was believed to be responsive on the
strength of a project that measured nothing (`D-021`). The project is now `responsive`, it matches
a file that exists, and it sets each of the four mandated widths explicitly.

A width is not a device. The layout is driven by CSS breakpoints, so the width is what is measured;
touch behaviour is not claimed here.

---

## 1. What is asserted at every width

| # | Assertion | Why it matters |
|---|---|---|
| 1 | The sign-in screen fits the viewport — every field and the button are inside it, and the page does not scroll sideways | A field clipped by the screen edge cannot be tapped, so the product cannot be entered at all |
| 2 | The shell shows the navigation that belongs to the width — below 1024 px the workspace rail is gone and the drawer trigger is present; at and above it the reverse, and the drawer opens and closes | The only navigation on a phone is the drawer; if the trigger is missing there is no way to move |
| 3 | No page scrolls sideways (`/dashboard`, `/people`, `/leave`, `/reports`, `/jobs`) | Content past the right edge is unreachable on a phone |
| 4 | The skip link is the first keyboard stop and activating it moves **focus** into `<main>`, not merely the scroll position | A skip link that only scrolls leaves the keyboard user at the top of the tab order — the thing it exists to prevent |

The overflow measurement takes the larger of two readings: the layout overflow (`scrollWidth`) and
the distance the page can actually be scrolled (`scrollX`). They disagree — one page laid out
378 px past the edge and scrolled there — so both are measured.

## 2. What the first run found — four defects

The first run failed 7 of 16. Every failure was a real defect in the product, not in the test.

| Finding | Evidence | Fix |
|---|---|---|
| **Two fixed bottom bars rendered at once.** `MobileBar` (65 px) and `MobileBottomNav` (137 px) were both `position: fixed; bottom: 0`. | At 360 × 900 the two bars occupied 202 px of the screen while `main` reserved 80 px (`pb-20`), so the end of every page sat behind them. | The duplicate bar is removed (its `MORE` list was dead code and it carried a stray `raised` class). One bar remains. |
| **The remaining bar wrapped to two rows.** `grid-cols-3` with five items. | Measured height 137 px for a one-row bar of about 65 px. | The column count is the item count. |
| **`/people` scrolled 218 px sideways at 360 px.** The six-tab strip is 562 px wide and `inline-flex` does not wrap. | `documentElement.scrollWidth` 578 vs 360. | The tab list wraps (`flex-wrap max-w-full`), so every tab stays reachable. |
| **`/jobs` scrolled 378 px sideways at 360 px.** The "Actions" header was a visually-hidden `<span>`; `.sr-only` is `position: absolute` with no positioned ancestor, so it was placed at the far right of the 797 px table — outside the `.table-scroll` clip — and the document grew to 738 px. | `window.scrollX` reached 378 after `scrollTo(9999, 0)`. | The header is visible, like every other column; `.table-scroll` is a containing block, so a hidden label can never escape a table again. |
| **The skip link did not move focus.** `<main id="main-content">` was not focusable. | After Enter on the skip link, `document.activeElement` stayed on `<body>`. | `<main>` is `tabIndex={-1}` in all four layouts (workspace, public, sign-in, change-password). |

## 3. A defect the typo fix exposed

The tab label carried `text-fm-muted` — a typo for `text-fg-muted`, so no class applied and the
tabs silently inherited the page colour. Correcting the typo made the label `#64748b` on the
`#f1f5f9` inset strip: **4.34:1**, under the 4.5:1 minimum, and the accessibility journey caught it.
The label now uses the readable foreground token; the raised pill carries the active state, not the
text colour.

## 4. The onboarding journey in this request — corrected and not written

The request said `J5` is the tenant setup. It is not: **`J5` is the payroll refusal** (gap `G1`).
Tenant setup is **`J13`**.

The request also assumed the preset and readiness work could be exercised from the browser. It
cannot: **no frontend route consumes `/onboarding/presets`, `/onboarding/presets/{id}/diff` or
`/onboarding/readiness`** (`grep -rn "onboarding/presets\|/readiness" frontend/src` → no match), and
`write_state()` — the only writer of the deployment's preset state — is called **only from the test
suite**, never from an endpoint. There is no screen to drive, and this request's own exclusion says
not to change the product to make a journey pass.

What exists, and is proven:

| Behaviour | Evidence |
|---|---|
| Six presets load, validate against the contract, define every required slot, and carry **no statutory value** | `backend/onboarding_test_suite.py` — 163 checks |
| The difference report and provenance distinguish a preset default from a customer override, and the customer's value wins | same suite |
| The readiness check reports and changes nothing | same suite |
| The onboarding portal itself (tasks, documents, summary) | `backend/smoke_test_client_onboarding.py` — 20 checks |

So the browser journey is **blocked on a screen that no request owns**, not on missing tests. It is
recorded as gap `G5` in `docs/validation/JOURNEYS.md` with that owner and date rather than claimed.

## 5. Where it runs

`.github/workflows/ci.yml` → the `journeys` job runs `npm run e2e`: 20 journeys, 21 accessibility
tests and these 16 responsive tests — **57 browser tests**, all passing. The `desktop` project
ignores `responsive.spec.ts`, because that file sets its own viewport for each width and would
otherwise be measured twice at the wrong size.

## 6. What is still open

- A manual keyboard and screen-reader pass is a human task and is not claimed here.
- `G1` — the payroll-refusal journey (`J5`), a named pilot-gate criterion — is still unwritten.
- `G5` — the tenant-setup journey needs a screen first.
