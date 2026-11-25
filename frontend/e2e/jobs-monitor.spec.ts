import { expect, test, type Page } from "@playwright/test"

/**
 * Background-jobs monitor journey (PS-10).
 *
 * The bug this guards against: the queue that runs imports, forecasts and
 * roster solves had no operator surface, and `/jobs` was the job-title
 * catalogue wearing the queue's name. A dead job could only be found in the
 * database.
 *
 * The journey reads the real `/admin/jobs` API against the seeded e2e
 * database: it finds the dead import, inspects it, retries it, then discards
 * the retried job with a reason. The backend suite proves the audit rows and
 * the transition rules; this proves the operator can actually do the work.
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

test.describe("background jobs monitor", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
    await page.goto("/jobs")
    await expect(page.getByRole("heading", { name: "Background jobs" })).toBeVisible()
  })

  test("the listing shows every state and never hides a dead job", async ({ page }) => {
    // The seeded queue has one dead import, one waiting import and one
    // finished forecast. All three are on the first page.
    const table = page.getByRole("table")
    await expect(page.getByText("import_row_rejected")).toBeVisible()
    // The count and the page are the server's `meta`, not a flat field that
    // does not exist. A screen reading `data.total` would print "undefined
    // jobs" here (D-044).
    await expect(page.getByText(/\d+ jobs? · page \d+ of \d+/)).toBeVisible()
    await expect(page.getByText(/undefined/i)).toHaveCount(0)
    // `.first()`: other journeys share this database and may have queued more
    // than one pending job by the time this runs, so the count is not the
    // assertion — the state being visible at all is.
    await expect(table.getByText("Dead", { exact: true }).first()).toBeVisible()
    await expect(table.getByText("Pending", { exact: true }).first()).toBeVisible()
    await expect(table.getByText("Succeeded", { exact: true }).first()).toBeVisible()

    // A filter with no match says so rather than showing a blank table.
    await page.locator("#job-state").selectOption("cancelled")
    await expect(page.getByText("No jobs match these filters")).toBeVisible()

    await page.locator("#job-state").selectOption("dead")
    await expect(page.getByText("import_row_rejected")).toBeVisible()
    await expect(table.getByText("Succeeded", { exact: true })).toHaveCount(0)

    await page.locator("#job-state").selectOption("succeeded")
    await expect(table.getByText("Succeeded", { exact: true }).first()).toBeVisible()
    await expect(page.getByText("import_row_rejected")).toHaveCount(0)
  })

  test("a finished job's stored result is shown, its stored input is not", async ({ page }) => {
    // The defect this guards against: the detail read returned `result: null`
    // for every job, so the screen could only ever say "no result stored" —
    // a false statement about a queue that has stored results since `0025`.
    await page.locator("#job-state").selectOption("succeeded")
    const finishedRow = page.getByRole("row").filter({ hasText: "Roster solve" }).first()
    await expect(finishedRow.getByText("Succeeded", { exact: true })).toBeVisible()

    await finishedRow.getByRole("button", { name: "View" }).click()
    const detail = page.getByRole("dialog")
    await expect(detail.getByRole("heading", { name: /Job #/ })).toBeVisible()

    // The stored result, as the queue wrote it.
    await expect(detail.getByText("FEASIBLE", { exact: false })).toBeVisible()
    await expect(detail.getByText("objective_value")).toBeVisible()
    await expect(detail.getByText("128.5")).toBeVisible()
    await expect(detail.getByText("The job has not stored a result.")).toHaveCount(0)

    // The stored input can carry an authorisation, so the screen does not
    // ask for it and it is not on the page.
    await expect(detail.getByText("time_limit_seconds")).toHaveCount(0)
    await expect(detail.getByText("confirm-", { exact: false })).toHaveCount(0)
  })

  test("a dead job can be inspected, retried and discarded", async ({ page }) => {
    const deadRow = page.getByRole("row").filter({ hasText: "import_row_rejected" })
    const jobLabel = (await deadRow.locator("td").first().innerText()).trim()
    const jobId = jobLabel.replace("#", "").trim()
    const rowWith = (label: string) =>
      page.getByRole("row").filter({ has: page.getByText(label, { exact: true }) })

    // --- inspect ---------------------------------------------------------
    //
    // The panel is read from the job itself, not from the list row: the row
    // is a snapshot, and `result` is only on the detail read. This waits for
    // the request the screen makes so the assertion is about the read, not
    // about a row that happened to already say the same thing.
    const detailRead = page.waitForRequest(
      (request) =>
        request.method() === "GET" &&
        new URL(request.url()).pathname.endsWith(`/admin/jobs/${jobId}`)
    )
    await deadRow.getByRole("button", { name: "View" }).click()
    expect((await detailRead).url()).toContain(`/admin/jobs/${jobId}`)

    const detail = page.getByRole("dialog")
    await expect(detail.getByRole("heading", { name: `Job #${jobId}` })).toBeVisible()
    await expect(detail.getByText("import_row_rejected")).toBeVisible()
    await expect(detail.getByText("Row 14: the department code does not exist.")).toBeVisible()
    // A job that stored no result says so; it does not show an empty object.
    await expect(detail.getByText("The job has not stored a result.")).toBeVisible()
    await detail.getByRole("button", { name: "Close" }).click()

    // --- retry -----------------------------------------------------------
    await deadRow.getByRole("button", { name: "Retry" }).click()
    await expect(page.getByText(`Job ${jobId} was put back in the queue.`)).toBeVisible()

    const retriedRow = rowWith(jobLabel)
    await expect(retriedRow.getByText("Pending", { exact: true })).toBeVisible()
    // The attempt budget is not reset by a retry.
    await expect(retriedRow.getByText("3/3")).toBeVisible()

    // --- discard ---------------------------------------------------------
    await retriedRow.getByRole("button", { name: "Discard" }).click()
    const confirm = page.getByRole("dialog")
    await expect(confirm.getByRole("heading", { name: `Discard job #${jobId}?` })).toBeVisible()
    await confirm.locator("#discard-reason").fill("The source file was withdrawn by the customer")
    await confirm.getByRole("button", { name: "Discard job" }).click()

    await expect(page.getByText(`Job ${jobId} was discarded; its record is kept.`)).toBeVisible()
    const discardedRow = rowWith(jobLabel)
    await expect(discardedRow.getByText("Discarded", { exact: true })).toBeVisible()
    // The row is evidence: discarding removes the work, not the record.
    await expect(discardedRow).toHaveCount(1)
  })
})
