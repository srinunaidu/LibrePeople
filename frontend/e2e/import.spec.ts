import { expect, test, type APIRequestContext, type Page } from "@playwright/test"

import { apiBaseUrl, assertNotProduction } from "./support/environment"

/**
 * The import journey: a CSV is previewed, committed, and the database is
 * asked what actually happened.
 *
 * The defect this guards against
 * ------------------------------
 * `DI-01`. The commit path used to pop the dry run, rewrite each accepted
 * row's status to `created`, increment a counter, write an audit row saying
 * `created=N` and answer `"committed": true` — having written nothing. The
 * audit trail recorded the fiction, so a response-only test would have
 * passed the whole time.
 *
 * So this journey does not believe the response. It reads the departments
 * table before the dry run, after the dry run and after the commit, through
 * an endpoint that is not the import endpoint, and it reads the audit trail
 * and holds it against the change in the table. The import's own numbers
 * are only ever used as the *preview* — the thing the operator was shown and
 * the thing the commit has to match.
 *
 * The re-import is the second half of the same story (`I-07`): running the
 * same file again is an upsert that finds the row already there, so it
 * changes nothing.
 *
 * The data is synthetic. A department with a code unique to this run is
 * written to the scratch schema the run is pointed at; no real person, no
 * real company and no real payroll figure appears in it.
 */

const ADMIN_USERNAME = "admin"
const ADMIN_PASSWORD = "E2e!Bootstrap#2026"

const FIXTURE_NAME = "Quality Assurance Fixture"
const FIXTURE_DESCRIPTION = "Synthetic department written by the import journey."

/** One department row, as the table holds it. */
interface Department {
  id: number
  name: string
  code: string
  description?: string | null
  is_active?: boolean
}

/** One audit row, as the audit trail holds it. */
interface AuditRow {
  id: number
  action: string
  entity_type: string
  details?: string | null
}

/**
 * A code that is unique to this run.
 *
 * The local suite rebuilds its database on every run, but the staging schema
 * keeps what it is given, so a fixed code would be a *create* the first time
 * and an *unchanged* the second. A code per run makes the journey mean the
 * same thing in both places.
 */
function uniqueCode(): string {
  const suffix = Math.random().toString(36).slice(2, 10).toUpperCase()
  return `QA1-${suffix}`
}

/** The CSV the operator uploads. */
function fixtureCsv(code: string): string {
  return [
    "name,code,description",
    `${FIXTURE_NAME},${code},${FIXTURE_DESCRIPTION}`,
  ].join("\n")
}

async function signIn(page: Page) {
  await page.goto("/login")
  await page.locator("#login-username").fill(ADMIN_USERNAME)
  await page.locator("#login-password").fill(ADMIN_PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 })
}

/** The bearer token the browser is holding. */
async function bearerToken(page: Page): Promise<string> {
  const token = await page.evaluate(() =>
    localStorage.getItem("karmathy_token")
  )
  expect(token, "the browser holds no access token").toBeTruthy()
  return token as string
}

/**
 * Read the departments table.
 *
 * This is the database, read through an endpoint that has nothing to do with
 * the import. It is the only evidence the journey accepts.
 */
async function readDepartments(
  request: APIRequestContext,
  token: string
): Promise<Department[]> {
  const response = await request.get(`${apiBaseUrl()}/departments/`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(response.status(), "reading the departments table").toBe(200)
  return (await response.json()) as Department[]
}

/** Read the audit trail. */
async function readAudit(
  request: APIRequestContext,
  token: string
): Promise<AuditRow[]> {
  const response = await request.get(`${apiBaseUrl()}/reports/audit?limit=200`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(response.status(), "reading the audit trail").toBe(200)
  return (await response.json()) as AuditRow[]
}

/**
 * The number the dry-run panel shows under a label.
 *
 * The panel is four boxes, each a label and a figure. The figure is the
 * label's next sibling, so it is read from the panel the operator looked at
 * rather than from the response that produced it.
 */
async function previewCount(page: Page, label: string): Promise<number> {
  const value = page
    .locator(`p:text-is("${label}")`)
    .locator("xpath=following-sibling::p[1]")
  await expect(value, `the dry-run panel has no "${label}" figure`).toBeVisible()
  const text = (await value.textContent())?.trim()
  return Number(text)
}

/** Upload the fixture and run the dry run. */
async function dryRun(page: Page, code: string) {
  await page.getByRole("button", { name: "departments", exact: true }).click()
  await page
    .locator('input[type="file"]')
    .setInputFiles({
      name: "departments.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(fixtureCsv(code), "utf8"),
    })
  await page.getByRole("button", { name: /run dry run/i }).click()
  await expect(
    page.getByRole("heading", { name: /dry run results/i })
  ).toBeVisible({ timeout: 30_000 })
}

/**
 * Commit the import the dry run produced.
 *
 * The screen no longer pops a browser `alert`: a `200` commit renders its
 * panel with the words "Import committed successfully" — words that are
 * only ever truthful for a `200`, because a `202` renders the queued panel
 * instead. The words themselves are what this helper waits for.
 */
async function commit(page: Page) {
  await page.getByRole("button", { name: /commit import/i }).click()
  await expect(
    page.getByText(/import committed successfully/i)
  ).toBeVisible({ timeout: 30_000 })
}

test.describe("CSV import", () => {
  test("a previewed import commits exactly what it previewed, and re-importing it changes nothing", async ({
    page,
    request,
  }) => {
    // The guard, asserted for this journey as well as for the run: the
    // browser's own traffic has to go somewhere that is not production.
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")

    const traffic: string[] = []
    page.on("request", (r) => traffic.push(r.url()))

    const code = uniqueCode()

    await signIn(page)
    const token = await bearerToken(page)

    // Every request the browser made must have gone to a host that is not
    // production. This is the property the guard is there to protect.
    const apiCalls = traffic.filter((u) => u.includes("/api/v1/"))
    expect(apiCalls.length, "the journey made no API call").toBeGreaterThan(0)
    for (const call of apiCalls) {
      assertNotProduction(call, "an API call the journey made")
    }

    // --- the table, before ---------------------------------------------
    const before = await readDepartments(request, token)
    expect(
      before.some((d) => d.code === code),
      "the fixture is already in the table before the import"
    ).toBe(false)

    // --- the preview ----------------------------------------------------
    await page.goto("/import")
    await dryRun(page, code)

    const previewCreated = await previewCount(page, "Created")
    const previewRejected = await previewCount(page, "Rejected")
    const previewUnchanged = await previewCount(page, "Unchanged")

    expect(previewCreated, "the preview says one row would be created").toBe(1)
    expect(previewRejected, "the preview rejects nothing").toBe(0)
    expect(previewUnchanged, "the preview says nothing is unchanged yet").toBe(0)

    // --- the dry run wrote nothing --------------------------------------
    const afterDryRun = await readDepartments(request, token)
    expect(
      afterDryRun.length,
      "the dry run changed the number of rows in the table"
    ).toBe(before.length)
    expect(
      afterDryRun.some((d) => d.code === code),
      "the dry run wrote the row it previewed"
    ).toBe(false)

    // --- the commit -----------------------------------------------------
    const auditBefore = await readAudit(request, token)
    await commit(page)

    // --- the table, after ------------------------------------------------
    const after = await readDepartments(request, token)
    const written = after.filter((d) => d.code === code)

    expect(
      written.length,
      "the committed department is not in the table exactly once"
    ).toBe(1)
    expect(written[0].name).toBe(FIXTURE_NAME)
    expect(written[0].description).toBe(FIXTURE_DESCRIPTION)

    // The preview and the table have to agree. The change in the table is
    // the evidence; the preview is the claim.
    const created = after.length - before.length
    expect(
      created,
      "the table gained a different number of rows than the preview promised"
    ).toBe(previewCreated)

    // --- the audit trail agrees with the table ---------------------------
    const auditAfter = await readAudit(request, token)
    const beforeIds = new Set(auditBefore.map((a) => a.id))
    const newAuditRows = auditAfter.filter((a) => !beforeIds.has(a.id))
    const commitRows = newAuditRows.filter(
      (a) => a.action === "import_commit" && a.entity_type === "departments"
    )

    expect(
      commitRows.length,
      "the commit wrote no audit row"
    ).toBe(1)
    const details = commitRows[0].details ?? ""
    expect(
      details,
      "the audit row does not carry the number of rows that were created"
    ).toContain(`created=${created}`)
    expect(details).toContain("updated=0")
    expect(details).toContain("unchanged=0")

    // --- and the screen agrees too ---------------------------------------
    await page.goto("/people/departments")
    const table = page.getByRole("table", { name: "Departments" })
    await expect(table).toBeVisible()
    await expect(table).toContainText(code)
    await expect(table).toContainText(FIXTURE_NAME)

    // --- the same file again ---------------------------------------------
    // The upsert finds the row already there, so the second commit is a
    // no-op: the table does not change, and the audit says so.
    await page.goto("/import")
    await dryRun(page, code)

    expect(
      await previewCount(page, "Created"),
      "the second preview says a row would be created"
    ).toBe(0)
    expect(
      await previewCount(page, "Unchanged"),
      "the second preview does not see the row that is already there"
    ).toBe(1)

    const auditBeforeSecond = await readAudit(request, token)
    const rowsBeforeSecond = (await readDepartments(request, token)).length

    await commit(page)

    const rowsAfterSecond = (await readDepartments(request, token)).length
    expect(
      rowsAfterSecond,
      "re-importing the same file changed the number of rows in the table"
    ).toBe(rowsBeforeSecond)

    const stillThere = (await readDepartments(request, token)).filter(
      (d) => d.code === code
    )
    expect(
      stillThere.length,
      "re-importing the same file duplicated the row"
    ).toBe(1)

    const auditAfterSecond = await readAudit(request, token)
    const secondIds = new Set(auditBeforeSecond.map((a) => a.id))
    const secondCommitRows = auditAfterSecond
      .filter((a) => !secondIds.has(a.id))
      .filter(
        (a) => a.action === "import_commit" && a.entity_type === "departments"
      )
    expect(
      secondCommitRows.length,
      "the second commit wrote no audit row"
    ).toBe(1)
    expect(secondCommitRows[0].details ?? "").toContain("created=0")
  })
})
