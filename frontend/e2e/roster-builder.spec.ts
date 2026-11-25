import { expect, test, type Page } from "@playwright/test"

import { apiBaseUrl, assertNotProduction } from "./support/environment"
import { adminSession } from "./support/p4-helpers"

/**
 * Screen-level journeys for the roster builder (SC-02/SC-04/SC-05) and the
 * pay-run reconciliation panel (PR-05).
 *
 * The bugs these guard against: a navigation entry that points at an
 * unregistered route (the catch-all silently drops the user on the marketing
 * homepage) and a screen whose shell never renders because its own state
 * handled loading but not the empty one. The journeys therefore walk the
 * real navigation and assert the shells, their tabs and their empty states
 * against a freshly seeded database, which deliberately holds no roster
 * versions and no payroll data.
 *
 * The seeded SuperAdmin is manager-and-above, so the roster screens open
 * rather than serving the not-permitted version.
 */

const ADMIN_USERNAME = "admin"
const ADMIN_PASSWORD = "E2e!Bootstrap#2026"

async function signIn(page: Page) {
  await page.goto("/login")
  await page.locator("#login-username").fill(ADMIN_USERNAME)
  await page.locator("#login-password").fill(ADMIN_PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 })
}

/** The rail is icon-only; the accessible name is the area label. */
function rail(page: Page, label: string) {
  return page.getByRole("link", { name: label, exact: true }).first()
}

test.describe("roster builder screen", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("every navigation path to it opens the real screen", async ({ page }) => {
    // Path 1: the secondary sidebar, from the scheduling area.
    await page.goto("/scheduling")
    await expect(page).toHaveURL(/\/scheduling$/)
    const sidebarLink = page.getByRole("link", { name: "Roster Builder", exact: true }).first()
    await expect(sidebarLink, "the sidebar entry is missing").toBeVisible()
    await sidebarLink.click()
    await expect(page).toHaveURL(/\/scheduling\/roster$/)
    await expect(page.getByRole("heading", { name: "Roster Builder", level: 1 })).toBeVisible()

    // Path 2: the header action on the scheduling screen.
    await page.goto("/scheduling")
    await page.getByRole("link", { name: "Open Roster Builder" }).first().click()
    await expect(page).toHaveURL(/\/scheduling\/roster$/)
  })

  test("the draft tab shows the generate form with its controls", async ({ page }) => {
    await page.goto("/scheduling/roster")
    await expect(page.getByRole("heading", { name: "Roster Builder", level: 1 })).toBeVisible()

    // The three tabs exist and the draft tab owns the panel first.
    const tablist = page.getByRole("tablist", { name: "Roster builder views" })
    await expect(tablist).toBeVisible()
    for (const name of ["Draft", "Versions", "Attendance"]) {
      await expect(tablist.getByRole("tab", { name })).toBeVisible()
    }

    await expect(page.getByRole("heading", { name: "Generate a draft" })).toBeVisible()

    // The form renders once the three lookups (locations, templates,
    // employees) have settled; the button is only in that settled branch.
    await expect(
      page.getByRole("button", { name: /generate draft roster/i })
    ).toBeVisible({ timeout: 30_000 })

    // No shift templates are seeded, so the empty state names the next step
    // rather than leaving a dead form.
    await expect(page.getByText(/no shift templates yet/i)).toBeVisible()
    await expect(page.getByRole("link", { name: /open scheduling/i })).toBeVisible()
  })

  test("the versions tab renders the list and its empty state", async ({ page }) => {
    await page.goto("/scheduling/roster")
    await page.getByRole("tab", { name: "Versions" }).click()
    await expect(
      page.getByRole("heading", { name: "Roster versions", level: 2 })
    ).toBeVisible()

    // The empty state itself carries the settled-fetch wait: Playwright only
    // resolves it once the versions request has been answered (success or the
    // error alert), so judging mid-flight cannot happen.
    await expect(
      page.getByText(/no roster versions yet/i),
      "versions fetch never settled to the empty state"
    ).toBeVisible({ timeout: 30_000 })


  })
})

test.describe("pay-run reconciliation", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("the reconciliation panel loads on the payroll screen", async ({
    page,
    request,
  }) => {
    // Self-sufficient setup: the payroll tab renders the reconciliation
    // panel once any payroll data exists. A seeded period (and no runs)
    // puts the panel in exactly the empty state asserted below, whatever
    // else ran before in this database.
    const tag = Math.random().toString(36).slice(2, 8).toUpperCase()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)
    const period = await request.post(`${api}/payroll/periods`, {
      headers: admin.headers,
      data: {
        name: `Recon panel period ${tag}`,
        start_date: "2026-04-01",
        end_date: "2026-04-30",
        pay_date: "2026-05-05",
      },
    })
    expect(period.status(), "pay period creation answers 201").toBe(201)

    await rail(page, "Payroll").click()
    await expect(page).toHaveURL(/\/platform\/payroll$/)

    await expect(
      page.getByRole("heading", { name: "Pay run reconciliation", level: 2 })
    ).toBeVisible()

    // The selector always offers the placeholder first and the panel says
    // what to do next. (Other journeys may have stored runs in this shared
    // database, so the count is not pinned — the placeholder-first shape and
    // the guidance text are.)
    const select = page.locator("#recon-run")
    await expect(select).toBeVisible()
    const options = select.locator("option")
    await expect(options.first()).toHaveText(/Select a pay run/)
    await expect(
      page.getByText(/choose a processed pay run to load its reconciliation/i)
    ).toBeVisible()
  })
})
