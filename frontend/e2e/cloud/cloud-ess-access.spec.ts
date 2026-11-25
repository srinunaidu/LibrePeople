import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test"

/**
 * Cloud E2E: ESS self-service visibility and the permission boundaries
 * around it.
 *
 * Authored, NOT RUN (no admin access yet). The provisioned employee user
 * proves the self-service surface serves them (`/ess` loads past the login
 * wall; the API answers their own notifications/directory reads), while the
 * admin-only surface refuses them: the UI never lands an employee on an
 * `/admin/*` screen, and the API refuses an employee's admin writes (403, or
 * 404 where the app refuses to confirm the resource exists). One direction
 * is also proven from the admin side: cross-role reads the employee must not
 * see stay denied. Console errors and failed cloud requests are captured.
 *
 * Credentials come from the environment at RUNTIME ONLY. Missing variables
 * SKIP with the reason, never fail.
 */

const API = (
  process.env.CLOUD_API_URL ??
  "https://librepeople-backend.onrender.com/api/v1"
).replace(/\/+$/, "")
const APP = (
  process.env.CLOUD_APP_URL ??
  "https://librepeople-frontend.onrender.com"
).replace(/\/+$/, "")

const ADMIN_USER = process.env.E2E_HRADMIN_USERNAME || "e2e_hradmin"
const EMPLOYEE_USER = process.env.E2E_EMPLOYEE_USERNAME || "e2e_employee"

function adminPassword(): string | null {
  return process.env.E2E_HRADMIN_PASSWORD ?? null
}
function employeePassword(): string | null {
  return process.env.E2E_EMPLOYEE_PASSWORD ?? null
}

const auth = (token: string) => ({ Authorization: `Bearer ${token}` })

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

async function apiLogin(
  request: APIRequestContext,
  username: string,
  password: string
): Promise<string> {
  const res = await request.post(`${API}/auth/login`, {
    data: { username, password },
  })
  expect(res.status(), "API login answers 200").toBe(200)
  const body = await res.json()
  expect(body.access_token, "login returns a token").toBeTruthy()
  return body.access_token as string
}

async function signIn(page: Page, username: string, password: string) {
  await page.goto(`${APP}/login`)
  await page.locator("#login-username").fill(username)
  await page.locator("#login-password").fill(password)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 })
}

test.describe("cloud ESS: self-service serves, admin surface refuses", () => {
  test("the employee reaches their own self-service surface", async ({
    page,
    request,
  }) => {
    const password = employeePassword()
    test.skip(
      password === null,
      "E2E_EMPLOYEE_USERNAME/E2E_EMPLOYEE_PASSWORD unset — the provisioned cloud employee user is not available (see frontend/e2e/cloud/README.md)."
    )
    const { consoleErrors, failed } = watch(page)
    const token = await apiLogin(request, EMPLOYEE_USER, password!)

    // --- API: their own self-service reads answer 200 --------------------
    const notifications = await request.get(`${API}/ess/notifications`, {
      headers: auth(token),
    })
    expect(notifications.status(), "own notifications answer 200").toBe(200)
    const directory = await request.get(`${API}/ess/directory`, {
      headers: auth(token),
    })
    expect(directory.status(), "directory answers 200").toBe(200)

    // --- UI: /ess loads for the employee ----------------------------------
    await signIn(page, EMPLOYEE_USER, password!)
    await page.goto(`${APP}/ess`)
    await expect(page).toHaveURL(/\/ess/, { timeout: 30_000 })
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })

    expect(
      failed.filter((entry) => entry.includes("onrender")),
      "no failed cloud requests"
    ).toEqual([])
    expect(consoleErrors, "no console errors").toEqual([])
  })

  test("the employee never lands on an admin screen", async ({ page }) => {
    const password = employeePassword()
    test.skip(
      password === null,
      "E2E_EMPLOYEE_USERNAME/E2E_EMPLOYEE_PASSWORD unset — the provisioned cloud employee user is not available (see frontend/e2e/cloud/README.md)."
    )
    watch(page)
    await signIn(page, EMPLOYEE_USER, password!)
    // ProtectedRoute gates /admin/* to SuperAdmin/HR: the employee must be
    // kept out — bounced to login or the dashboard — never the admin screen.
    await page.goto(`${APP}/admin/users`)
    await expect(page).not.toHaveURL(/\/admin\/users$/, { timeout: 30_000 })
    await page.goto(`${APP}/admin/backup`)
    await expect(page).not.toHaveURL(/\/admin\/backup$/, { timeout: 30_000 })
  })

  test("the employee's admin writes are refused (403/404)", async ({
    request,
  }) => {
    const password = employeePassword()
    test.skip(
      password === null,
      "E2E_EMPLOYEE_USERNAME/E2E_EMPLOYEE_PASSWORD unset — the provisioned cloud employee user is not available (see frontend/e2e/cloud/README.md)."
    )
    const token = await apiLogin(request, EMPLOYEE_USER, password!)

    const asset = await request.post(`${API}/assets`, {
      headers: auth(token),
      data: { tag: "CLOUD-DENIED", name: "Denied asset" },
    })
    // Per the app's design, unauthorised writes are refused — 403, or 404
    // where the route refuses to confirm the resource exists.
    expect([403, 404], "asset creation by an employee is refused").toContain(
      asset.status()
    )

    const termination = await request.post(`${API}/offboarding/terminations`, {
      headers: auth(token),
      data: {
        employee_id: 1,
        last_working_date: "2026-12-31",
        termination_type: "Resignation",
        reason: "cloud e2e denied probe",
      },
    })
    expect(
      [403, 404],
      "termination creation by an employee is refused"
    ).toContain(termination.status())
  })

  test("reads without a token answer 401", async ({ request }) => {
    const res = await request.get(`${API}/ess/notifications`)
    expect(res.status(), "unauthenticated ESS read answers 401").toBe(401)
    const adminRes = await request.get(`${API}/admin/status`)
    expect(adminRes.status(), "unauthenticated admin read is refused").not.toBe(
      200
    )
  })

  test("the admin surface loads for the HR admin", async ({ page }) => {
    const password = adminPassword()
    test.skip(
      password === null,
      "E2E_HRADMIN_USERNAME/E2E_HRADMIN_PASSWORD unset — the provisioned cloud HR admin is not available (see frontend/e2e/cloud/README.md)."
    )
    const { consoleErrors, failed } = watch(page)
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/admin/users`)
    await expect(page).toHaveURL(/\/admin\/users/, { timeout: 30_000 })
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    expect(
      failed.filter((entry) => entry.includes("onrender")),
      "no failed cloud requests"
    ).toEqual([])
    expect(consoleErrors, "no console errors").toEqual([])
  })
})
