import { expect, test } from "@playwright/test"

/**
 * The first-sign-in journey for a SuperAdmin whose password was set by an
 * administrator.
 *
 * The account must reach the password-change screen before it can use the
 * rest of the application, and it must land on the dashboard afterwards.
 */

const FIRST_LOGIN_USERNAME = "firstlogin"
const BOOTSTRAP_PASSWORD = "E2e!FirstLogin#2026"
const ROTATED_PASSWORD = "E2e!Rotated#2026x"

// A separate account so this journey does not depend on the one above,
// which rotates its password.
const PENDING_USERNAME = "pendingchange"
const PENDING_PASSWORD = "E2e!Pending#2026"

test("a first sign-in must replace the administrator-set password", async ({ page }) => {
  await page.goto("/login")
  await page.locator("#login-username").fill(FIRST_LOGIN_USERNAME)
  await page.locator("#login-password").fill(BOOTSTRAP_PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()

  // The server refuses every other route for this account, and the client
  // sends it to the one screen that can help.
  await expect(page).toHaveURL(/\/change-password/, { timeout: 20_000 })
  await expect(
    page.getByRole("heading", { name: /set a new password/i })
  ).toBeVisible()

  await page.locator("#current-password").fill(BOOTSTRAP_PASSWORD)
  await page.locator("#new-password").fill(ROTATED_PASSWORD)
  await page.locator("#confirm-password").fill(ROTATED_PASSWORD)
  await page.getByRole("button", { name: /change password|update password|save/i }).click()

  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 })
})

test("a protected route cannot be reached before the password is replaced", async ({
  page,
}) => {
  // Sign in, then try to navigate straight to a protected route. The
  // account is still flagged, so the client must bounce it back.
  await page.goto("/login")
  await page.locator("#login-username").fill(PENDING_USERNAME)
  await page.locator("#login-password").fill(PENDING_PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/change-password/, { timeout: 20_000 })

  await page.goto("/people")
  await expect(page).toHaveURL(/\/change-password/, { timeout: 20_000 })
})
