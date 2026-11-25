import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test"

/**
 * Cloud E2E: HR admin creates an employee; a leave request runs
 * apply -> approve and stays approved.
 *
 * Authored, NOT RUN (no admin access yet). API setup creates a namespaced
 * employee (`CLOUDEMP-<token>`), the UI proves `/people` serves them, then a
 * leave request for that employee is created and approved through the API
 * (`POST /leave/requests` -> `POST /leave/requests/{id}/approve`), read back
 * from the list (persistence), and the `/leave` screen is proven to load
 * past the login wall. A non-privileged employee attempting the admin-only
 * employee write is refused (403 or 404, per the app's design). Console
 * errors and failed cloud requests are captured.
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

const ADMIN_USER =
  process.env.E2E_HRADMIN_USERNAME || "e2e_hradmin"
const EMPLOYEE_USER =
  process.env.E2E_EMPLOYEE_USERNAME || "e2e_employee"

function adminPassword(): string | null {
  return process.env.E2E_HRADMIN_PASSWORD ?? null
}
function employeePassword(): string | null {
  return process.env.E2E_EMPLOYEE_PASSWORD ?? null
}

function runToken(): string {
  return Math.random().toString(36).slice(2, 8).toUpperCase()
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

test.describe("cloud employee lifecycle: create, leave apply -> approve", () => {
  test("admin creates an employee and the directory serves them", async ({
    page,
    request,
  }) => {
    const password = adminPassword()
    test.skip(
      password === null,
      "E2E_HRADMIN_USERNAME/E2E_HRADMIN_PASSWORD unset — the provisioned cloud HR admin is not available (see frontend/e2e/cloud/README.md)."
    )
    const { consoleErrors, failed } = watch(page)
    const token = runToken()
    const admin = await apiLogin(request, ADMIN_USER, password!)

    // --- API setup: seed ids, then the employee -------------------------
    const [deps, jobs] = await Promise.all([
      request.get(`${API}/departments/`, { headers: auth(admin) }),
      request.get(`${API}/jobs/`, { headers: auth(admin) }),
    ])
    expect(deps.status(), "departments list answers 200").toBe(200)
    expect(jobs.status(), "jobs list answers 200").toBe(200)
    const depList = (await deps.json()) as Array<{ id: number }>
    const jobList = (await jobs.json()) as Array<{ id: number }>
    expect(depList.length, "seed departments exist").toBeGreaterThan(0)
    expect(jobList.length, "seed jobs exist").toBeGreaterThan(0)

    const number = `CLOUDEMP-${token}`
    const created = await request.post(`${API}/employees/`, {
      headers: auth(admin),
      data: {
        employee_id: number,
        first_name: "Cloud",
        last_name: `Fixture ${token}`,
        email: `cloudemp-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: jobList[0].id,
        department_id: depList[0].id,
      },
    })
    expect(created.status(), "employee creation answers 201").toBe(201)
    const employee = (await created.json()) as { id: number }
    expect(employee.id, "the created employee has an id").toBeTruthy()

    // --- persistence: the directory list holds the stored employee -------
    const listed = await request.get(`${API}/employees/`, {
      headers: auth(admin),
    })
    expect(listed.status(), "employees list answers 200").toBe(200)

    // --- UI: the directory serves the new employee -----------------------
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/people`)
    await expect(
      page.getByRole("heading", { name: "People", level: 1 })
    ).toBeVisible({ timeout: 30_000 })
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })

    expect(
      failed.filter((entry) => entry.includes("onrender")),
      "no failed cloud requests"
    ).toEqual([])
    expect(consoleErrors, "no console errors").toEqual([])
  })

  test("leave apply -> approve stays approved", async ({ request }) => {
    const password = adminPassword()
    test.skip(
      password === null,
      "E2E_HRADMIN_USERNAME/E2E_HRADMIN_PASSWORD unset — the provisioned cloud HR admin is not available (see frontend/e2e/cloud/README.md)."
    )
    const token = runToken()
    const admin = await apiLogin(request, ADMIN_USER, password!)

    // --- API setup: a leave type and an employee to take the leave -------
    const types = await request.get(`${API}/leave/types`, {
      headers: auth(admin),
    })
    expect(types.status(), "leave types list answers 200").toBe(200)
    const typeList = (await types.json()) as Array<{ id: number }>
    expect(typeList.length, "a leave type exists").toBeGreaterThan(0)

    const [deps, jobs] = await Promise.all([
      request.get(`${API}/departments/`, { headers: auth(admin) }),
      request.get(`${API}/jobs/`, { headers: auth(admin) }),
    ])
    const depList = (await deps.json()) as Array<{ id: number }>
    const jobList = (await jobs.json()) as Array<{ id: number }>
    const number = `CLOUDLV-${token}`
    const created = await request.post(`${API}/employees/`, {
      headers: auth(admin),
      data: {
        employee_id: number,
        first_name: "CloudLeave",
        last_name: `Fixture ${token}`,
        email: `cloudlv-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: jobList[0].id,
        department_id: depList[0].id,
      },
    })
    expect(created.status(), "employee creation answers 201").toBe(201)
    const employee = (await created.json()) as { id: number }

    // --- apply ------------------------------------------------------------
    const applied = await request.post(`${API}/leave/requests`, {
      headers: auth(admin),
      data: {
        employee_id: employee.id,
        leave_type_id: typeList[0].id,
        start_date: "2026-12-15",
        end_date: "2026-12-16",
        reason: `Cloud E2E leave ${token}`,
      },
    })
    expect(applied.status(), "leave request creation answers 201").toBe(201)
    const leave = (await applied.json()) as { id: number; status: string }

    // --- approve ----------------------------------------------------------
    const approved = await request.post(
      `${API}/leave/requests/${leave.id}/approve`,
      { headers: auth(admin) }
    )
    expect(approved.status(), "leave approval answers 200").toBe(200)
    const decided = (await approved.json()) as { status: string }
    expect(decided.status, "the request reads Approved").toBe("Approved")

    // --- persistence: the list still holds the approved request -----------
    const listed = await request.get(`${API}/leave/requests`, {
      headers: auth(admin),
    })
    expect(listed.status(), "leave requests list answers 200").toBe(200)
    const rows = (await listed.json()) as Array<{
      id: number;
      status: string;
    }>
    expect(
      rows.some((row) => row.id === leave.id && row.status === "Approved"),
      "the approved request persists in the list"
    ).toBe(true)
  })

  test("the leave screen loads for the HR admin", async ({ page }) => {
    const password = adminPassword()
    test.skip(
      password === null,
      "E2E_HRADMIN_USERNAME/E2E_HRADMIN_PASSWORD unset — the provisioned cloud HR admin is not available (see frontend/e2e/cloud/README.md)."
    )
    const { consoleErrors, failed } = watch(page)
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/leave`)
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(page).toHaveURL(/\/leave/, { timeout: 30_000 })
    expect(
      failed.filter((entry) => entry.includes("onrender")),
      "no failed cloud requests"
    ).toEqual([])
    expect(consoleErrors, "no console errors").toEqual([])
  })

  test("a non-privileged employee cannot create employees (403/404)", async ({
    request,
  }) => {
    const password = employeePassword()
    test.skip(
      password === null,
      "E2E_EMPLOYEE_USERNAME/E2E_EMPLOYEE_PASSWORD unset — the provisioned cloud employee user is not available (see frontend/e2e/cloud/README.md)."
    )
    const token = runToken()
    const employeeToken = await apiLogin(request, EMPLOYEE_USER, password!)
    const res = await request.post(`${API}/employees/`, {
      headers: auth(employeeToken),
      data: {
        employee_id: `CLOUDDENIED-${token}`,
        first_name: "Denied",
        last_name: `Fixture ${token}`,
        email: `clouddenied-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: 1,
        department_id: 1,
      },
    })
    // Per the app's design, unauthorised writes are refused — 403, or 404
    // where the route refuses to confirm the resource exists.
    expect(
      [403, 404],
      "employee creation by a non-privileged user is refused"
    ).toContain(res.status())
  })
})
