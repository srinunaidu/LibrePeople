import { expect, test, type Page } from "@playwright/test"

/**
 * Navigation journey for a signed-in SuperAdmin.
 *
 * The bug this guards against: a navigation entry pointing at a route that
 * either does not exist (the catch-all silently drops the user on the
 * marketing homepage) or points at the wrong screen ("People" opening the
 * admin form page). The user sees both as "clicking it does nothing".
 *
 * Every workspace-rail and secondary-sidebar entry is therefore clicked and
 * the resulting URL asserted.
 */

const ADMIN_USERNAME = "admin"
const ADMIN_PASSWORD = "E2e!Bootstrap#2026"

/**
 * Sign in as the shared navigation account.
 *
 * The account has already replaced its bootstrap password, so the sign-in
 * lands straight on the dashboard. The forced password-change journey has
 * its own account and its own test.
 */
async function signIn(page: Page) {
  await page.goto("/login")
  // The field ids are stable; the visible labels carry a required marker
  // that would make an exact-name match brittle.
  await page.locator("#login-username").fill(ADMIN_USERNAME)
  await page.locator("#login-password").fill(ADMIN_PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 })
}

/** The rail is icon-only; the accessible name is the area label. */
function rail(page: Page, label: string) {
  return page.getByRole("link", { name: label, exact: true }).first()
}

test.describe("workspace navigation", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("every workspace rail entry opens the screen it names", async ({ page }) => {
    const expected: Record<string, string> = {
      Dashboard: "/dashboard",
      People: "/people",
      Time: "/time",
      Leave: "/leave",
      Recruiting: "/recruiting",
      Payroll: "/platform/payroll",
      Performance: "/platform/performance",
      Learning: "/platform/learning",
      Reports: "/reports",
      Admin: "/client-onboarding",
    }

    for (const [label, path] of Object.entries(expected)) {
      const link = rail(page, label)
      await expect(link, `rail entry "${label}" is missing`).toBeVisible()
      await link.click()
      await expect(page).toHaveURL(new RegExp(`${path.replace(/\//g, "\\/")}$`), {
        timeout: 20_000,
      })
      // The catch-all route redirects to the marketing homepage. Landing
      // there means the entry pointed at an unregistered path.
      await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    }
  })

  test("People opens the employee directory and lists employees", async ({ page }) => {
    await rail(page, "People").click()
    await expect(page).toHaveURL(/\/people$/)
    await expect(page.getByRole("heading", { name: "People", level: 1 })).toBeVisible()
    // The directory table is present with its accessible caption.
    await expect(
      page.getByRole("table", { name: /employees visible to you/i })
    ).toBeVisible()
  })

  test("People sub-pages open their own tab", async ({ page }) => {
    await rail(page, "People").click()

    const links = [
      { name: "Departments", path: "/people/departments" },
      { name: "Jobs", path: "/people/jobs" },
      { name: "Locations", path: "/people/locations" },
    ]

    for (const { name, path } of links) {
      const link = page.getByRole("link", { name, exact: true }).first()
      await expect(link, `sidebar entry "${name}" is missing`).toBeVisible()
      await link.click()
      await expect(page).toHaveURL(new RegExp(`${path.replace(/\//g, "\\/")}$`))
    }
  })

  test("the admin section links to import, jobs and MFA", async ({ page }) => {
    await rail(page, "Admin").click()
    await expect(page).toHaveURL(/\/client-onboarding$/)

    const links = [
      { name: "Import / Export", path: "/import" },
      { name: "Background Jobs", path: "/jobs" },
      { name: "Security (MFA)", path: "/mfa" },
    ]

    for (const { name, path } of links) {
      const link = page.getByRole("link", { name, exact: true }).first()
      await expect(link, `admin entry "${name}" is missing`).toBeVisible()
      await link.click()
      await expect(page).toHaveURL(new RegExp(`${path.replace(/\//g, "\\/")}$`))
    }
  })

  test("the command palette navigates to People, not the platform page", async ({ page }) => {
    await page.keyboard.press("Control+k")
    // cmdk renders each entry as a listbox option, not a button, so the
    // accessible role is "option".
    const item = page.getByRole("option", { name: /go to people/i }).first()
    await expect(item).toBeVisible()
    await item.click()
    await expect(page).toHaveURL(/\/people$/)
  })

  test("no navigation entry lands on the marketing homepage", async ({ page }) => {
    // Walk the rail and the secondary sidebar, collecting every URL the
    // user can reach. The catch-all route rewrites to "/", so a landing on
    // the bare homepage means a link pointed at an unregistered path.
    const visited = new Set<string>()

    for (const label of [
      "Dashboard",
      "People",
      "Time",
      "Leave",
      "Recruiting",
      "Payroll",
      "Performance",
      "Learning",
      "Reports",
      "Admin",
    ]) {
      const link = rail(page, label)
      if (!(await link.isVisible().catch(() => false))) continue
      await link.click()
      await page.waitForLoadState("networkidle").catch(() => undefined)
      visited.add(new URL(page.url()).pathname)
    }

    for (const path of visited) {
      expect(path, `"${path}" is the catch-all redirect target`).not.toBe("/")
    }
    // The walk must have reached more than one screen, or the loop is broken.
    expect(visited.size).toBeGreaterThan(3)
  })
})
