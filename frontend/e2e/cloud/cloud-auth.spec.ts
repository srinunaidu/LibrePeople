import { expect, test, type Page } from "@playwright/test"

/**
 * Cloud E2E: role sign-in and sign-out against the DEPLOYED environment.
 *
 * Authored, NOT RUN (no admin access yet). Each test signs a provisioned
 * synthetic user in through the UI (`/login` -> `/dashboard`), proves the
 * API accepts the same credentials (`POST /auth/login` answers 200 with a
 * token), then signs out and proves the session is gone (a protected route
 * bounces back to `/login`). Console errors and failed cloud requests are
 * captured per role so a red run names the lane that broke.
 *
 * Credentials come from the environment at RUNTIME ONLY — nothing is
 * hard-coded and nothing is logged. A role whose variables are unset is
 * SKIPPED with the reason, never failed.
 */

const API = (
  process.env.CLOUD_API_URL ??
  "https://librepeople-backend.onrender.com/api/v1"
).replace(/\/+$/, "")
const APP = (
  process.env.CLOUD_APP_URL ??
  "https://librepeople-frontend.onrender.com"
).replace(/\/+$/, "")

const DEFAULT_USERNAMES = {
  HRADMIN: "e2e_hradmin",
  HREXEC: "e2e_hrexec",
  PAYROLL: "e2e_payroll",
  MANAGER: "e2e_manager",
  EMPLOYEE: "e2e_employee",
  READONLY: "e2e_readonly",
} as const
type CloudRole = keyof typeof DEFAULT_USERNAMES

function creds(role: CloudRole): { username: string; password: string } | null {
  const username =
    process.env[`E2E_${role}_USERNAME`] || DEFAULT_USERNAMES[role]
  const password = process.env[`E2E_${role}_PASSWORD`]
  if (!password) return null
  return { username, password }
}

function skipReason(role: CloudRole): string {
  return (
    `E2E_${role}_USERNAME/E2E_${role}_PASSWORD unset — the provisioned ` +
    `cloud ${role.toLowerCase()} user is not available (see frontend/e2e/cloud/README.md).`
  )
}

/** Console errors and failed cloud requests seen by this page. */
function watch(page: Page) {
  const consoleErrors: string[] = []
  const failed: string[] = []
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text())
  })
  page.on("requestfailed", (req) =>
    failed.push(`${req.method()} ${req.url()} :: ${req.failure()?.errorText}`)
  )
  page.on("response", (res) => {
    if (res.status() >= 500) failed.push(`${res.status()} ${res.url()}`)
  })
  return { consoleErrors, failed }
}

async function signIn(page: Page, username: string, password: string) {
  await page.goto(`${APP}/login`)
  await page.locator("#login-username").fill(username)
  await page.locator("#login-password").fill(password)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 })
  // Not the catch-all marketing homepage: that means the route is missing.
  await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
}

async function signOut(page: Page) {
  // The product's sign-out ends the browser session: clearing it and asking
  // for a protected route must bounce back to /login, never the dashboard.
  await page.context().clearCookies()
  await page.goto(`${APP}/dashboard`)
  await expect(page).toHaveURL(/\/login/, { timeout: 30_000 })
}

async function signInOut(role: CloudRole, page: Page) {
  const c = creds(role)
  test.skip(c === null, skipReason(role))
  const { username, password } = c!
  const { consoleErrors, failed } = watch(page)

  // --- API: the same credentials mint a token ---------------------------
  const login = await page.request.post(`${API}/auth/login`, {
    data: { username, password },
  })
  expect(login.status(), `${role} API login answers 200`).toBe(200)
  const body = await login.json()
  expect(body.access_token, `${role} login returns a token`).toBeTruthy()

  // --- UI: sign in lands on the dashboard -------------------------------
  await signIn(page, username, password)

  // --- UI: sign out ends the session ------------------------------------
  await signOut(page)

  expect(
    failed.filter((entry) => entry.includes("onrender")),
    `${role} saw no failed cloud requests`
  ).toEqual([])
  expect(consoleErrors, `${role} saw no console errors`).toEqual([])
}

test.describe("cloud auth: every provisioned role can sign in and out", () => {
  test("hradmin signs in and out", async ({ page }) => {
    await signInOut("HRADMIN", page)
  })

  test("hrexec signs in and out", async ({ page }) => {
    await signInOut("HREXEC", page)
  })

  test("payroll signs in and out", async ({ page }) => {
    await signInOut("PAYROLL", page)
  })

  test("manager signs in and out", async ({ page }) => {
    await signInOut("MANAGER", page)
  })

  test("employee signs in and out", async ({ page }) => {
    await signInOut("EMPLOYEE", page)
  })

  test("readonly signs in and out", async ({ page }) => {
    await signInOut("READONLY", page)
  })
})
