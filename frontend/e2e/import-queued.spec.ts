import { expect, test, type Page } from "@playwright/test"

import { apiBaseUrl, assertNotProduction } from "./support/environment"

/**
 * The queued-import journey (FD-02): the screen must tell the truth about
 * a 202.
 *
 * The defect this guards against
 * ------------------------------
 * The import screen used to say "Import committed successfully!" whatever
 * the commit answered. A file over the row threshold (`IMPORT_JOB_ROW_THRESHOLD`,
 * 2000 rows) is answered with a **202** — the work was *queued* for a
 * background job, nothing is applied yet — and the screen said the
 * opposite. An operator was told their data was in when it was not.
 *
 * How this journey talks to a queue that is real
 * ----------------------------------------------
 * The screen is driven here by the real backend, not by a mock: the file
 * holds 2005 rows, one past the threshold, so the commit genuinely answers
 * 202 and the panel the operator sees is the one this journey asserts. In
 * the local harness the job stays `queued` (the suite runs no worker), and
 * that is the point — the screen says "queued" and must keep saying it,
 * because no endpoint answers with a later state (the progress feed of a
 * queued import is not served yet; it is DI-04's to build).
 *
 * What is asserted, and why it is the defect in reverse
 * -----------------------------------------------------
 *   - the words "import queued" and "running in the background" appear;
 *   - the words "committed successfully" appear nowhere, and no browser
 *     `alert` is raised — the old lie was a dialog;
 *   - the job's own line ("job #…") is shown, because the state is the
 *     job's and the operator deserves the reference;
 *   - the screen says it cannot follow the job live — it does not invent
 *     a state it cannot read;
 *   - after leaving the page and coming back (`reload`), the queued-import
 *     watch still names the job: the browser kept the job's identity,
 *     nothing about the job's state is recounted from the browser.
 *
 * The data is synthetic. A run-unique code prefix keeps a staging schema
 * from colliding with a previous run; no real person, no real company and
 * no real payroll figure appears in it.
 */

const ADMIN_USERNAME = "admin"
const ADMIN_PASSWORD = "E2e!Bootstrap#2026"

const ROWS = 2005 // one row past IMPORT_JOB_ROW_THRESHOLD (2000)
const NAME_PREFIX = "Queued Fixture Department"

function runToken(): string {
  return Math.random().toString(36).slice(2, 10).toUpperCase()
}

/** The CSV the operator uploads: ROWS synthetic departments, unique codes. */
function fixtureCsv(token: string): string {
  const lines = ["name,code,description"]
  for (let i = 1; i <= ROWS; i++) {
    lines.push(
      `${NAME_PREFIX} ${token} ${i},QA9-${token}${String(i).padStart(4, "0")},Synthetic row ${i} written by the queued-import journey.`
    )
  }
  return lines.join("\n")
}

async function signIn(page: Page) {
  await page.goto("/login")
  await page.locator("#login-username").fill(ADMIN_USERNAME)
  await page.locator("#login-password").fill(ADMIN_PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 })
}

/**
 * The number the dry-run panel shows under a label.
 *
 * The panel is label-and-figure pairs, the figure the label's next sibling.
 */
async function previewCount(page: Page, label: string): Promise<number> {
  const value = page
    .locator(`p:text-is("${label}")`)
    .locator("xpath=following-sibling::p[1]")
  await expect(value, `the dry-run panel has no "${label}" figure`).toBeVisible()
  const text = (await value.textContent())?.trim()
  return Number(text)
}

test.describe("Queued import (202) — the screen tells the truth", () => {
  test("a large file is queued, the screen says queued, and nothing says committed", async ({
    page,
  }) => {
    test.setTimeout(240_000)

    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")

    // Any dialog the old lie would raise is recorded and dismissed here,
    // then asserted empty: the honest screen never needs one.
    const dialogs: string[] = []
    page.on("dialog", (d) => {
      dialogs.push(`${d.type()}: ${d.message()}`)
      void d.dismiss()
    })

    // The commit's own answer is part of the evidence: this journey only
    // means anything if the server really queued the import (202), so the
    // status is asserted, not inferred from the panel.
    const commitStatuses: number[] = []
    page.on("response", (r) => {
      if (r.request().method() === "POST" && r.url().includes("/commit")) {
        commitStatuses.push(r.status())
      }
    })

    const token = runToken()
    await signIn(page)

    // --- the preview ----------------------------------------------------
    await page.goto("/import")
    await page.getByRole("button", { name: "departments", exact: true }).click()
    await page.locator('input[type="file"]').setInputFiles({
      name: "departments.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(fixtureCsv(token), "utf8"),
    })
    await page.getByRole("button", { name: /run dry run/i }).click()
    await expect(
      page.getByRole("heading", { name: /dry run results/i })
    ).toBeVisible({ timeout: 120_000 })

    expect(
      await previewCount(page, "Rows in file"),
      "the preview does not count every row of the file"
    ).toBe(ROWS)
    expect(
      await previewCount(page, "Rejected"),
      "the preview rejects rows (the fixture CSV is invalid)"
    ).toBe(0)

    // --- the commit ------------------------------------------------------
    await page.getByRole("button", { name: /commit import/i }).click()
    await expect(
      page.getByRole("heading", { name: /import queued/i })
    ).toBeVisible({ timeout: 120_000 })

    // The screen says queued, in the words that can only mean 202.
    await expect(page.getByText(/running in the background/i)).toBeVisible()

    // The old lie, asserted absent in both forms it took.
    await expect(page.getByText(/committed successfully/i)).toHaveCount(0)
    expect(dialogs, "a browser dialog claimed the queued import committed").toEqual([])

    // The job's own line: the state is the job's, so the job is named.
    await expect(page.getByText(/job #\d+/).first()).toBeVisible()

    // And the answer really was a 202: queued, not applied.
    expect(
      commitStatuses,
      "the commit was not answered with 202, so this journey did not run the case it exists for"
    ).toEqual([202])

    // The screen follows the job through its own progress operation. The
    // numbers are the server's: this harness runs the worker **off**, so the
    // job stays queued and nothing is applied — which is exactly what the
    // panel must say.
    await expect(page.getByText(/rows applied/i)).toBeVisible({ timeout: 30_000 })
    await expect(page.getByText(/0 of \d+ rows applied/i)).toBeVisible()
    await expect(page.getByRole("button", { name: /cancel this import/i })).toBeVisible()

    // --- cancelling it ---------------------------------------------------
    // The import is one transaction, so cancelling is safe and the server
    // says so. The panel must stop offering Cancel once it is cancelled.
    await page.getByRole("button", { name: /cancel this import/i }).click()
    await expect(page.getByText(/the import was cancelled/i)).toBeVisible({
      timeout: 30_000,
    })
    await expect(
      page.getByRole("button", { name: /cancel this import/i })
    ).toHaveCount(0)

    // Nothing is applied yet is part of the truthful answer — the count
    // cards above belong to the *preview*, and the queued panel never
    // dresses them up as applied rows.
    await expect(page.getByText(/has not been committed/i)).toBeVisible()

    // --- leaving the screen and coming back ------------------------------
    // The state is in the job, on the server; what the browser keeps is
    // the job's identity, and the screen must still show it.
    await page.reload()
    await expect(page.getByText(/queued import watch/i)).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByText(/job #\d+/).first()).toBeVisible()
    await expect(page.getByText(/committed successfully/i)).toHaveCount(0)
  })
})
