import { expect, test, type Page } from "@playwright/test"

/**
 * The employment lifecycle and its effective-dated history (HR-12).
 *
 * The defect this guards against
 * ------------------------------
 * The employee record held one current value per field and no record of how it
 * got there. A lifecycle move was an overwrite with no rule about which moves
 * were legal, so "when did this person leave?" had no answer and a terminated
 * employee could be made `Active` again in one request.
 *
 * What is asserted
 * ----------------
 * The screen sends the change to the server and renders the server's answer:
 * a recorded move appends a history row with its date, reason and actor; a move
 * the lifecycle does not allow is refused with the allowed next states and
 * changes nothing; termination records the date, and a rehire clears it.
 *
 * The journey is real end to end: it creates an employee through the form and
 * changes the employment through the panel. No response is stubbed.
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

const today = () => new Date().toISOString().slice(0, 10)

test.describe("employment lifecycle and history", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("a move is recorded and an illegal move is refused with the allowed moves", async ({
    page,
  }) => {
    const token = runToken()
    const employeeNumber = `HR12-${token}`
    const firstName = "Lifecycle"
    const lastName = `Fixture ${token}`

    await page.goto("/people")
    await expect(page.getByRole("heading", { name: "People", level: 1 })).toBeVisible()

    // --- the employee the changes belong to ------------------------------
    await page.getByRole("button", { name: "Add employee" }).click()
    await page.locator("#new-employee-id").fill(employeeNumber)
    await page.locator("#new-first-name").fill(firstName)
    await page.locator("#new-last-name").fill(lastName)
    await page.locator("#new-email").fill(`hr12-${token.toLowerCase()}@example.com`)
    await page.locator("#new-hire-date").fill("2026-01-05")
    await page.locator("#new-department").selectOption({ label: "Operations" })
    await page.locator("#new-job").selectOption({ label: "Operations Manager" })
    await page.getByRole("button", { name: "Add employee" }).last().click()
    await expect(page.getByText("Employee added to the directory.")).toBeVisible()

    await page.getByRole("button", { name: `${firstName} ${lastName}` }).click()
    const panel = page.getByRole("dialog")
    await expect(
      panel.getByRole("heading", { name: `${firstName} ${lastName}` }),
    ).toBeVisible()
    await expect(panel.getByText("No employment changes recorded yet.")).toBeVisible()

    // --- Active -> On Leave: recorded, with the reason and today ----------
    await panel.locator("#employment-status").selectOption("On Leave")
    await panel.locator("#employment-reason").fill("Medical leave approved")
    await panel.getByRole("button", { name: "Record the change" }).click()
    await expect(
      panel.getByText("Employment updated. The change is in the history below."),
    ).toBeVisible()

    await expect(panel.locator("dl").getByText("On Leave")).toBeVisible()
    const history = panel.getByRole("region", { name: "Employment history" })
    const recorded = history
      .getByRole("row")
      .filter({ hasText: "status" })
      .filter({ hasText: "Medical leave approved" })
    await expect(recorded).toBeVisible()
    await expect(recorded).toContainText("On Leave")
    await expect(recorded).toContainText(today())
    await expect(recorded).toContainText("admin")

    // --- On Leave -> Rehired is not a lifecycle move ----------------------
    await panel.locator("#employment-status").selectOption("Rehired")
    await panel.locator("#employment-reason").fill("Skip the process")
    await panel.getByRole("button", { name: "Record the change" }).click()

    const refusal = panel.getByRole("alert")
    await expect(refusal).toContainText(/cannot move from 'On Leave' to 'Rehired'/)
    await expect(refusal).toContainText(/allowed next states are Active, Terminated/)
    // The refusal changed nothing: the status is still On Leave and the
    // refused reason is not history.
    await expect(panel.locator("dl").getByText("On Leave")).toBeVisible()
    await expect(history.getByText("Skip the process")).toHaveCount(0)

    // --- On Leave -> Terminated: the termination date is recorded ---------
    await panel.locator("#employment-status").selectOption("Terminated")
    await panel.locator("#employment-reason").fill("Resigned")
    await panel.getByRole("button", { name: "Record the change" }).click()
    await expect(
      panel.getByText("Employment updated. The change is in the history below."),
    ).toBeVisible()
    await expect(panel.locator("dl").getByText("Termination date")).toBeVisible()
    await expect(panel.locator("dl").getByText(today())).toBeVisible()

    // --- Terminated -> Active is refused; Terminated -> Rehired is not ----
    await panel.locator("#employment-status").selectOption("Active")
    await panel.locator("#employment-reason").fill("Straight back")
    await panel.getByRole("button", { name: "Record the change" }).click()
    await expect(panel.getByRole("alert")).toContainText(
      /cannot move from 'Terminated' to 'Active'/,
    )
    await expect(panel.getByRole("alert")).toContainText(/allowed next states are Rehired/)

    await panel.locator("#employment-status").selectOption("Rehired")
    await panel.locator("#employment-reason").fill("Returned as a contractor")
    await panel.getByRole("button", { name: "Record the change" }).click()
    await expect(
      panel.getByText("Employment updated. The change is in the history below."),
    ).toBeVisible()
    await expect(panel.locator("dl").getByText("Termination date")).toHaveCount(0)

    // The history now carries the moves. A reason can appear on more than
    // one row (a termination writes `status` and `termination_date`), so the
    // assertion names the field as well as the reason.
    await expect(
      history
        .getByRole("row")
        .filter({ hasText: "status" })
        .filter({ hasText: "Rehired" })
        .filter({ hasText: "Returned as a contractor" }),
    ).toBeVisible()
    await expect(
      history
        .getByRole("row")
        .filter({ hasText: "status" })
        .filter({ hasText: "Terminated" })
        .filter({ hasText: "Resigned" }),
    ).toBeVisible()
  })
})
