import { expect, test, type Page } from "@playwright/test"

/**
 * Screens that must tell the truth about what the server answered.
 *
 * Three defects, three journeys
 * -----------------------------
 * 1. **A failed read looked like an empty list.** Every table on `/platform`
 *    answered a failed request with `[]`, so a 503 rendered as "No locations
 *    recorded yet." On Oracle, twelve list endpoints answered 503 on *every*
 *    call (D-035) and the product said the customer had no data. The screen
 *    now records which path failed and says "This list could not be read."
 *
 * 2. **The payslip panel did not exist.** `GET /payroll/payslips` has served
 *    the inputs a payslip was calculated from (`inputs_json`) and the rule
 *    behind every line since PR-002, and no screen read either. The Payroll
 *    tab now shows them, and recalculates nothing.
 *
 * 3. **An employee's documents had no surface.** `GET` and `POST
 *    /core-hr/employee-documents` existed; the People detail panel showed a
 *    person's job and manager and nothing about their documents. It now lists
 *    them and records one.
 *
 * The first two journeys intercept the network on purpose: the local backend
 * has no seeded pay run, and a 503 is not something the local server produces.
 * The intercept is the *input* to the screen under test; what is asserted is
 * the screen's answer. The third journey is real end to end — it creates an
 * employee and a document through the API, because that is the path the
 * operator takes.
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

/** A unique suffix, so a staging schema does not collide with an earlier run. */
function runToken(): string {
  return Math.random().toString(36).slice(2, 8).toUpperCase()
}

test.describe("screens tell the truth about the server's answer", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("Core HR owns /platform and the integrations tab has its own address", async ({ page }) => {
    // The defect this guards against: the integrations tab's key was also
    // "platform", so `/platform` resolved to it. Clicking "Core HR" landed on
    // the integrations panel, and clicking "Platform" navigated to
    // `/platform/platform`, which is not a route — the catch-all sent the
    // operator to the marketing homepage, out of the product entirely.
    await page.goto("/platform")
    await expect(page.getByRole("tab", { name: "Core HR" })).toHaveAttribute(
      "aria-selected",
      "true"
    )
    await expect(page.getByRole("heading", { name: "Locations", exact: true })).toBeVisible()

    await page.getByRole("tab", { name: "Platform" }).click()
    await expect(page).toHaveURL(/\/platform\/integrations$/)
    await expect(page.getByRole("tab", { name: "Platform" })).toHaveAttribute(
      "aria-selected",
      "true"
    )
    await expect(page.getByRole("heading", { name: "Webhooks", exact: true })).toBeVisible()

    // And the address is shareable: a reload lands on the same tab.
    await page.reload()
    await expect(page.getByRole("heading", { name: "Webhooks", exact: true })).toBeVisible()
  })

  test("a list that could not be read does not read as an empty list", async ({ page }) => {
    // The one path that fails. Everything else the page reads is left alone,
    // so the assertion is about the failed list, not about a page that is
    // entirely broken.
    await page.route("**/api/v1/core-hr/locations*", (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "dependency_unavailable",
            category: "infrastructure",
            message: "The database is temporarily unavailable.",
            retryable: true,
          },
        }),
      })
    )

    await page.goto("/platform")

    const locations = page
      .locator("section.card")
      .filter({ has: page.getByRole("heading", { name: "Locations", exact: true }) })
    await expect(locations.getByRole("alert")).toContainText("This list could not be read")
    await expect(locations.getByText(/No locations recorded yet/)).toHaveCount(0)

    // The distinction is the point: a list that *was* read and is empty still
    // says it is empty. Cost centres were not intercepted and have no rows in
    // the e2e database.
    const costCenters = page
      .locator("section.card")
      .filter({ has: page.getByRole("heading", { name: "Cost centers", exact: true }) })
    await expect(costCenters.getByText("No cost centers recorded yet.")).toBeVisible()
    await expect(costCenters.getByRole("alert")).toHaveCount(0)
  })

  test("a payslip shows the time it paid and the rule behind every line", async ({ page }) => {
    // The stubbed run and slip are the shapes the API returns; the figures are
    // synthetic and deliberately not round, so a screen that recomputed them
    // would be caught by the numbers changing.
    await page.route("**/api/v1/payroll/runs", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { id: 7, status: "Approved", rule_pack_id: "US-CA-2026.1", jurisdiction: "US-CA" },
        ]),
      })
    )
    await page.route("**/api/v1/payroll/payslips*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 41,
            employee_id: 12,
            gross_pay: "4210.37",
            total_deductions: "913.22",
            net_pay: "3297.15",
            employee_contributions: "311.40",
            employer_contributions: "402.15",
            status: "Final",
            inputs_json: JSON.stringify({
              approved_time_entries: 20,
              approved_worked_hours: 152.5,
              approved_overtime_hours: 6.25,
              unapproved_time_entries: 3,
              approved_leave_requests: 1,
              paid_leave_days: 2,
              unpaid_leave_days: 0.5,
            }),
            earnings_json: JSON.stringify([
              {
                code: "BASIC",
                name: "Base salary",
                amount: "4000.00",
                type: "earning",
                rule_id: "BASIC",
                rule_version: "1.2.0",
                input_source: "base_salary",
                calculation: "monthly salary / 173 * 152.5 hours",
              },
            ]),
            deductions_json: JSON.stringify([
              {
                code: "FIT",
                name: "Federal income tax",
                amount: "913.22",
                type: "tax",
                rule_id: "US-FIT",
                rule_version: "2026.1",
                input_source: "rule_pack:tax_bands",
                calculation: "banded withholding on 4210.37",
              },
            ]),
          },
        ]),
      })
    )

    await page.goto("/platform/payroll")
    await expect(
      page.getByRole("heading", { name: "Payslips and what they were paid from" })
    ).toBeVisible()

    await page.locator("#payslip-run").selectOption("7")
    await expect(page.getByText("4210.37")).toBeVisible()
    await expect(page.getByText("3297.15")).toBeVisible()

    await page.getByRole("button", { name: "What it used", exact: true }).click()

    // What the payslip was calculated from, with the excluded entry named as
    // excluded rather than silently absent.
    const inputs = page.getByRole("region", {
      name: "Approved time and leave consumed by this payslip",
    })
    await expect(inputs.getByRole("row", { name: /Approved hours worked/ })).toContainText("152.5")
    await expect(inputs.getByRole("row", { name: /Approved overtime hours/ })).toContainText("6.25")
    const excluded = inputs.getByRole("row", { name: /Time entries not approved/ })
    await expect(excluded).toContainText("3")
    await expect(excluded).toContainText("No — excluded")

    // Every line carries the rule and the calculation that produced it.
    const earnings = page.getByRole("region", { name: "Earnings lines" })
    await expect(earnings.getByRole("row", { name: /Base salary/ })).toContainText("BASIC v1.2.0")
    await expect(earnings.getByRole("row", { name: /Base salary/ })).toContainText(
      "monthly salary / 173 * 152.5 hours"
    )
    const deductions = page.getByRole("region", { name: "Deductions lines" })
    await expect(deductions.getByRole("row", { name: /Federal income tax/ })).toContainText(
      "US-FIT v2026.1"
    )

    // Nothing was recalculated: the figures are exactly the ones the API sent.
    await expect(page.getByText("4210.38")).toHaveCount(0)
    await expect(page.getByText("3297.16")).toHaveCount(0)
  })

  test("the directory reads a page, knows the total, and loads the next one", async ({ page }) => {
    // Two defects are guarded here. The first: the screen read one page and
    // said "100 of 100 employees shown". The second: the endpoint answered a
    // bare list, so the screen could not know how many existed and paged with
    // `skip`, which the contract never declared (D-040). The operation now
    // answers `{items, meta}` and takes `page`; this asserts the screen reads
    // the envelope, says the server's total, and asks for the next page.
    const bulk = Array.from({ length: 200 }, (_, index) => ({
      id: index + 1,
      employee_id: `BULK-${String(index + 1).padStart(4, "0")}`,
      first_name: "Bulk",
      last_name: `Fixture ${index + 1}`,
      email: `bulk-${index + 1}@example.com`,
      job_id: 1,
      department_id: 1,
      manager_id: null,
      hire_date: "2025-01-01",
      status: "Active",
    }))

    let askedPage: string | null = null
    await page.route(/\/api\/v1\/employees\/?(\?|$)/, (route) => {
      const url = new URL(route.request().url())
      const pageNumber = Number(url.searchParams.get("page") ?? "1")
      askedPage = url.searchParams.get("page")
      const body =
        pageNumber === 1
          ? {
              items: bulk,
              meta: { page: 1, page_size: 200, total: 201, total_pages: 2 },
            }
          : {
              items: [
                {
                  id: 201,
                  employee_id: "BULK-0201",
                  first_name: "Last",
                  last_name: "Page Fixture",
                  email: "last-page@example.com",
                  job_id: 1,
                  department_id: 1,
                  manager_id: null,
                  hire_date: "2025-01-01",
                  status: "Active",
                },
              ],
              meta: { page: 2, page_size: 200, total: 201, total_pages: 2 },
            }
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      })
    })

    await page.goto("/people")
    await expect(page.getByText("200 of 201 employees shown")).toBeVisible()
    await expect.poll(() => askedPage).toBe("1")
    await expect(page.getByRole("button", { name: "Load more employees" })).toBeVisible()

    await page.getByRole("button", { name: "Load more employees" }).click()

    await expect(page.getByText("201 of 201 employees shown")).toBeVisible()
    await expect.poll(() => askedPage).toBe("2")
    await expect(page.getByRole("button", { name: "Last Page Fixture" })).toBeVisible()
    // `meta.total` is reached: the screen stops offering more.
    await expect(page.getByRole("button", { name: "Load more employees" })).toHaveCount(0)
  })

  test("the directory's search and filters are the server's, not a filter of the loaded page", async ({
    page,
  }) => {
    // The old screen filtered the rows it had already loaded. On a tenant
    // larger than a page that meant a search could say "no match" while the
    // person existed on the server — a false claim in the product's voice.
    // The request the screen makes is the evidence: if it stops sending
    // `search`/`status`/`department_id`, this journey fails even when the
    // stubbed page happens to contain the answer.
    const asked: URL[] = []
    const unfiltered = {
      id: 1,
      employee_id: "UNFILTERED-1",
      first_name: "Unfiltered",
      last_name: "Person",
      email: "unfiltered@example.com",
      job_id: 1,
      department_id: 1,
      manager_id: null,
      hire_date: "2025-01-01",
      status: "Active",
    }
    const filtered = {
      id: 2,
      employee_id: "FILTERED-1",
      first_name: "Filtered",
      last_name: "Result",
      email: "filtered@example.com",
      job_id: 1,
      department_id: 1,
      manager_id: null,
      hire_date: "2025-02-01",
      status: "On Leave",
    }

    await page.route(/\/api\/v1\/employees\/?(\?|$)/, (route) => {
      const url = new URL(route.request().url())
      asked.push(url)
      const narrowed =
        url.searchParams.has("search") ||
        url.searchParams.has("status") ||
        url.searchParams.has("department_id")
      const items = narrowed ? [filtered] : [unfiltered]
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items,
          meta: { page: 1, page_size: 200, total: items.length, total_pages: 1 },
        }),
      })
    })

    await page.goto("/people")
    await expect(page.getByRole("button", { name: "Unfiltered Person" })).toBeVisible()

    // Search: the server is asked, and its answer replaces the page. The
    // unfiltered row is gone because the server did not return it, not
    // because the browser hid it.
    await page.locator("#directory-search").fill("filtered")
    await expect(page.getByRole("button", { name: "Filtered Result" })).toBeVisible()
    await expect(page.getByRole("button", { name: "Unfiltered Person" })).toHaveCount(0)
    await expect
      .poll(() => asked.some((url) => url.searchParams.get("search") === "filtered"))
      .toBe(true)

    // Status: the stored vocabulary is sent, not a client-side comparison.
    await page.locator("#directory-search").fill("")
    await page.locator("#directory-status").selectOption("On Leave")
    await expect
      .poll(() => asked.some((url) => url.searchParams.get("status") === "On Leave"))
      .toBe(true)
    await expect(page.getByRole("button", { name: "Filtered Result" })).toBeVisible()

    // Department: the id goes to the server too.
    await page.locator("#directory-status").selectOption("")
    await page.locator("#directory-department").selectOption({ label: "Operations" })
    await expect
      .poll(() => asked.some((url) => Number(url.searchParams.get("department_id")) > 0))
      .toBe(true)
  })

  test("an employee's documents can be read and recorded", async ({ page }) => {
    const token = runToken()
    const employeeId = `QA-DOC-${token}`
    const firstName = "Document"
    const lastName = `Fixture ${token}`

    await page.goto("/people")
    await expect(page.getByRole("heading", { name: "People", level: 1 })).toBeVisible()

    // --- create the employee the documents belong to ---------------------
    await page.getByRole("button", { name: "Add employee" }).click()
    await page.locator("#new-employee-id").fill(employeeId)
    await page.locator("#new-first-name").fill(firstName)
    await page.locator("#new-last-name").fill(lastName)
    // `example.test` is a reserved name and the API refuses it on input (a
    // special-use domain cannot receive mail). `example.com` is the
    // documentation domain and is accepted.
    await page.locator("#new-email").fill(`doc-${token.toLowerCase()}@example.com`)
    await page.locator("#new-hire-date").fill("2026-01-05")
    await page.locator("#new-department").selectOption({ label: "Operations" })
    await page.locator("#new-job").selectOption({ label: "Operations Manager" })
    await page.getByRole("button", { name: "Add employee" }).last().click()
    await expect(page.getByText("Employee added to the directory.")).toBeVisible()

    // --- open the panel: documents are read, not assumed -----------------
    //
    // The directory is paged and newest hire first, so the person just added
    // is on the first page. The loop still pages if a fixture needs it: the
    // point is that the journey finds the person by reading pages the screen
    // actually offers, not by assuming one page holds everyone.
    const personRow = page.getByRole("button", { name: `${firstName} ${lastName}` })
    const loadMore = page.getByRole("button", { name: "Load more employees" })
    for (let attempt = 0; attempt < 20 && !(await personRow.isVisible()); attempt++) {
      if (!(await loadMore.isVisible())) break
      const rowsBefore = await page.getByRole("row").count()
      await loadMore.click()
      await expect
        .poll(() => page.getByRole("row").count(), { timeout: 20_000 })
        .toBeGreaterThan(rowsBefore)
    }
    await expect(personRow).toBeVisible()

    await personRow.click()
    const panel = page.getByRole("dialog")
    await expect(panel.getByRole("heading", { name: `${firstName} ${lastName}` })).toBeVisible()
    await expect(panel.getByText("No documents recorded for this employee.")).toBeVisible()

    // --- record one ------------------------------------------------------
    await page.locator("#doc-file").fill(`contract-${token}.pdf`)
    await page.locator("#doc-url").fill(`https://files.example.test/${token}/contract.pdf`)
    await panel.getByRole("button", { name: "Record document" }).click()

    await expect(page.getByText("Document recorded.")).toBeVisible()
    const documents = panel.getByRole("region", {
      name: "Documents recorded for this employee",
    })
    const recorded = documents.getByRole("row", { name: new RegExp(`contract-${token}`) })
    await expect(recorded).toContainText("Contract")
    await expect(recorded.getByRole("link", { name: `contract-${token}.pdf` })).toBeVisible()
    await expect(panel.getByText("No documents recorded for this employee.")).toHaveCount(0)
  })
})
