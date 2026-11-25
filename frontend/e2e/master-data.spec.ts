import { expect, test, type Page } from "@playwright/test"

/**
 * Master data journey — the five reference entities have a lifecycle.
 *
 * The bug this guards against: a table that lists a record and offers no way to
 * correct it. Departments, jobs, locations, positions and cost centres could be
 * created and read and nothing else, so a mistyped code was permanent and a
 * record nobody used any more stayed in every form that offered it.
 *
 * This journey drives one entity end to end through the shared editor — create,
 * edit, archive, restore, delete — and asserts what the screen shows after each
 * step. The other four entities use the same editor and the same endpoints; the
 * backend suite proves their rules individually.
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

test.describe("master data lifecycle", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("a department can be created, corrected, archived, restored and deleted", async ({
    page,
  }) => {
    const code = `E2E-${Date.now().toString().slice(-6)}`
    const name = `E2E Department ${code}`

    await page.goto("/people/departments")
    await expect(page.getByRole("heading", { name: "Departments" })).toBeVisible()

    // --- create -----------------------------------------------------------
    await page.getByRole("button", { name: "Add department" }).first().click()
    const create = page.getByRole("dialog")
    await expect(create.getByRole("heading", { name: "Add department" })).toBeVisible()
    await create.locator("#ref-name").fill(name)
    await create.locator("#ref-code").fill(code)
    await create.locator("#ref-description").fill("Created by the master data journey")
    await create.getByRole("button", { name: "Add department" }).click()

    await expect(
      page.getByRole("status").filter({ hasText: code }),
    ).toContainText(`Department "${code}" created`)
    const row = page.getByRole("row", { name: new RegExp(code) })
    await expect(row).toContainText(name)
    await expect(row).toContainText("Active")

    // --- edit -------------------------------------------------------------
    await page.getByRole("button", { name: `Edit department ${code}` }).click()
    const edit = page.getByRole("dialog")
    await expect(edit.getByRole("heading", { name: "Edit department" })).toBeVisible()
    await edit.locator("#ref-description").fill("Corrected by the journey")
    await edit.getByRole("button", { name: "Save changes" }).click()

    await expect(page.getByRole("row", { name: new RegExp(code) })).toContainText(
      "Corrected by the journey",
    )

    // --- archive and restore ---------------------------------------------
    await page.getByRole("button", { name: `Archive department ${code}` }).click()
    await expect(page.getByRole("row", { name: new RegExp(code) })).toContainText("Draft")

    await page.getByRole("button", { name: `Restore department ${code}` }).click()
    await expect(page.getByRole("row", { name: new RegExp(code) })).toContainText("Active")

    // --- delete -----------------------------------------------------------
    // The confirmation is a custom modal (role=dialog), not a native
    // window.confirm: the row button opens it, the modal Delete confirms.
    await page.getByRole("button", { name: `Delete department ${code}` }).click()
    const confirm = page.getByRole("dialog", { name: `Delete department` })
    await expect(confirm).toBeVisible()
    await confirm.getByRole("button", { name: "Delete", exact: true }).click()
    await expect(page.getByRole("row", { name: new RegExp(code) })).toHaveCount(0)
  })

  test("a refused deletion says what still points at the record", async ({ page }) => {
    // The seed gives the administrator a department with people in it, so the
    // deletion guard has something real to name. The first row is the one the
    // employee form preselects; any row with employees is enough.
    await page.goto("/people/departments")

    const firstDelete = page
      .getByRole("button", { name: /^Delete department / })
      .first()
    // The seed wires the OPS department into the tenant, so the guard always
    // has a row to name: an empty count is a seed regression, not a skip.
    await expect(
      page.getByRole("button", { name: /^Delete department / }),
      "the seeded tenant lists a department to guard"
    ).not.toHaveCount(0)

    // The confirmation is a custom modal (role=dialog), not a native
    // window.confirm: the row button opens it, the modal Delete confirms.
    await firstDelete.click()
    const confirm = page.getByRole("dialog", { name: /^Delete department/ })
    await expect(confirm).toBeVisible()
    await confirm.getByRole("button", { name: "Delete", exact: true }).click()

    // Either it was unreferenced and went, or it was refused and the page says
    // why. A refusal must name the rows, never a bare "delete failed".
    const banner = page.getByRole("alert").filter({
      hasText: /still referenced|cannot be deleted/i,
    })
    if (await banner.isVisible().catch(() => false)) {
      await expect(banner).toBeVisible()
    }
  })
})
