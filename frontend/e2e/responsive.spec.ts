import { expect, test, type Page } from "@playwright/test"

/**
 * Responsive journey (QA-02, UX-08, UX-09).
 *
 * The `responsive` project matches only this file and runs it at the four
 * widths the mandate names: 360, 768, 1024 and 1440 px. Until now the project
 * matched a file that did not exist, so it ran nothing while the run summary
 * read "passed" (D-021) — a suite that measures nothing is worse than no
 * suite, because it is believed.
 *
 * What is asserted at every width:
 *
 * 1. The sign-in screen is usable — every control is inside the viewport.
 * 2. The shell adapts — below the `lg` breakpoint (1024 px) the workspace rail
 *    is gone and the drawer trigger is present; at and above it the rail is
 *    present and the trigger is gone.
 * 3. No page scrolls sideways. A page that overflows horizontally is a page
 *    whose right-hand content cannot be reached on a phone.
 * 4. The keyboard reaches the content: the skip link is the first stop and
 *    activating it moves focus into `<main>`, not merely the scroll position.
 *
 * A width is not a device. The layout is driven by CSS breakpoints, so the
 * width is what is measured here; touch behaviour is not claimed.
 */

const ADMIN_USERNAME = "admin"
const ADMIN_PASSWORD = "E2e!Bootstrap#2026"

/** The four widths the mandate names. */
const WIDTHS = [360, 768, 1024, 1440] as const

/** Tailwind's `lg` breakpoint: at and above it the desktop shell is shown. */
const LG = 1024

/** A representative page per area, so overflow is caught where tables and
 *  grids actually are, not only on a text page. */
const PAGES = ["/dashboard", "/people", "/leave", "/reports", "/jobs"]

async function signIn(page: Page) {
  await page.goto("/login")
  await page.locator("#login-username").fill(ADMIN_USERNAME)
  await page.locator("#login-password").fill(ADMIN_PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 })
}

/**
 * How far the page can be scrolled sideways, in pixels.
 *
 * Two measurements, because they disagree: `scrollWidth` sees layout overflow
 * that is visually clipped, and `scrollX` sees what the user can actually
 * reach. The larger of the two is the honest answer — a page that lays out
 * past the edge but cannot be scrolled is still broken, and a page that
 * scrolls is broken however its layout is clipped.
 */
async function horizontalOverflow(page: Page): Promise<number> {
  return page.evaluate(() => {
    const root = document.documentElement
    const byLayout = root.scrollWidth - root.clientWidth
    window.scrollTo(9999, 0)
    const byScroll = window.scrollX
    window.scrollTo(0, 0)
    return Math.max(byLayout, byScroll)
  })
}

for (const width of WIDTHS) {
  test.describe(`at ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } })

    test("the sign-in screen fits the viewport", async ({ page }) => {
      await page.goto("/login")
      const overflow = await horizontalOverflow(page)
      expect(overflow, `the sign-in page scrolls ${overflow}px sideways`).toBeLessThanOrEqual(1)

      // Every control must be inside the viewport, not merely present in the
      // DOM: a field clipped by the screen edge cannot be tapped.
      for (const selector of ["#login-username", "#login-password"]) {
        const box = await page.locator(selector).boundingBox()
        expect(box, `${selector} has no box at ${width}px`).not.toBeNull()
        expect(box!.x, `${selector} starts left of the viewport`).toBeGreaterThanOrEqual(0)
        expect(box!.x + box!.width, `${selector} runs past the right edge`).toBeLessThanOrEqual(
          width + 1,
        )
      }

      const submit = await page.getByRole("button", { name: "Sign in" }).boundingBox()
      expect(submit, "the sign-in button has no box").not.toBeNull()
      expect(submit!.x + submit!.width, "the sign-in button runs past the right edge").toBeLessThanOrEqual(
        width + 1,
      )
    })

    test("the shell shows the navigation that belongs to this width", async ({ page }) => {
      await signIn(page)

      const rail = page.getByRole("navigation", { name: "Workspace" })
      const drawerTrigger = page.getByRole("button", { name: "Open navigation" })

      if (width >= LG) {
        await expect(rail, `the workspace rail is missing at ${width}px`).toBeVisible()
        await expect(drawerTrigger, `the drawer trigger is shown at ${width}px`).toBeHidden()
      } else {
        await expect(rail, `the workspace rail is shown at ${width}px`).toBeHidden()
        await expect(drawerTrigger, `the drawer trigger is missing at ${width}px`).toBeVisible()

        // The drawer is the only navigation at this width, so it has to work.
        await drawerTrigger.click()
        const drawer = page.getByRole("navigation", { name: "Mobile navigation" })
        await expect(drawer).toBeVisible()
        await drawer.getByRole("button", { name: "Close navigation" }).click()
        await expect(drawer).toBeHidden()
      }
    })

    test("no page scrolls sideways", async ({ page }) => {
      await signIn(page)
      for (const path of PAGES) {
        await page.goto(path)
        // The screen is rendered before the measurement, otherwise a loading
        // skeleton would be measured instead of the real content.
        await expect(page.locator("#main-content")).toBeVisible()
        const overflow = await horizontalOverflow(page)
        expect(overflow, `${path} scrolls ${overflow}px sideways at ${width}px`).toBeLessThanOrEqual(
          1,
        )
      }
    })

    test("the skip link moves focus into the content", async ({ page }) => {
      await signIn(page)
      await page.goto("/dashboard")

      await page.keyboard.press("Tab")
      const skip = page.getByRole("link", { name: "Skip to main content" })
      await expect(skip, "the skip link is not the first keyboard stop").toBeFocused()

      await page.keyboard.press("Enter")
      // Focus, not scroll: a skip link that only scrolls leaves the keyboard
      // user at the top of the tab order, which is the thing it exists to
      // prevent.
      await expect
        .poll(() => page.evaluate(() => document.activeElement?.id ?? ""), {
          message: "activating the skip link did not move focus to #main-content",
        })
        .toBe("main-content")
    })
  })
}
