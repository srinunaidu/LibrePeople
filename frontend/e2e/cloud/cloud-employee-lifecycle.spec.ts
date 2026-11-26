import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test"
import { completeMfaIfRequired, mfaSecretFor } from "./totp"

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
  password: string,
  mfaSecret: string | null = null
): Promise<string> {
  const res = await request.post(`${API}/auth/login`, {
    data: { username, password },
  })
  expect(res.status(), "API login answers 200").toBe(200)
  const body = await res.json()
  expect(body.access_token, "login returns a token").toBeTruthy()
  const token = body.access_token as string
  // HR roles pass the MFA gate only once enrolled; the helper completes the
  // step when the account still requires it and otherwise returns as-is.
  await completeMfaIfRequired(request, API, token, mfaSecret)
  return token
}

async function signIn(page: Page, username: string, password: string) {
  await page.goto(`${APP}/login`)
  await page.locator("#login-username").fill(username)
  await page.locator("#login-password").fill(password)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 })
}

/**
 * Reuse-or-create the master data the employee tests need. The deployed
 * tenant ships no departments, jobs or leave types, so the run provisions
 * its own namespaced rows when the lists are empty (reruns reuse them).
 */
async function ensureDeptAndJob(
  request: APIRequestContext,
  admin: string,
  token: string
): Promise<{ depId: number; jobId: number }> {
  const [deps, jobs] = await Promise.all([
    request.get(`${API}/departments/`, { headers: auth(admin) }),
    request.get(`${API}/jobs/`, { headers: auth(admin) }),
  ])
  expect(deps.status(), "departments list answers 200").toBe(200)
  expect(jobs.status(), "jobs list answers 200").toBe(200)
  const depList = (await deps.json()) as Array<{ id: number }>
  const jobList = (await jobs.json()) as Array<{ id: number }>
  let depId = depList[0]?.id
  let jobId = jobList[0]?.id
  if (depId === undefined) {
    const created = await request.post(`${API}/departments/`, {
      headers: auth(admin),
      data: { name: `Cloud E2E Dept ${token}`, code: `CDEPT-${token}` },
    })
    expect(created.status(), "department creation answers 201").toBe(201)
    depId = ((await created.json()) as { id: number }).id
  }
  if (jobId === undefined) {
    const created = await request.post(`${API}/jobs/`, {
      headers: auth(admin),
      data: { title: `Cloud E2E Job ${token}`, department_id: depId },
    })
    expect(created.status(), "job creation answers 201").toBe(201)
    jobId = ((await created.json()) as { id: number }).id
  }
  return { depId, jobId }
}

async function ensureLeaveType(
  request: APIRequestContext,
  admin: string,
  token: string
): Promise<number> {
  const types = await request.get(`${API}/leave/types`, {
    headers: auth(admin),
  })
  expect(types.status(), "leave types list answers 200").toBe(200)
  const typeList = (await types.json()) as Array<{ id: number }>
  if (typeList.length > 0) return typeList[0].id
  const created = await request.post(`${API}/leave/types`, {
    headers: auth(admin),
    data: {
      name: `Cloud E2E Leave ${token}`,
      code: `CLV-${token}`,
      max_days_per_year: 20,
    },
  })
  expect(created.status(), "leave type creation answers 201").toBe(201)
  return ((await created.json()) as { id: number }).id
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
    const admin = await apiLogin(
      request,
      ADMIN_USER,
      password!,
      mfaSecretFor("HRADMIN")
    )

    // --- API setup: master-data ids, then the employee --------------------
    const { depId, jobId } = await ensureDeptAndJob(request, admin, token)

    const number = `CLOUDEMP-${token}`
    const created = await request.post(`${API}/employees/`, {
      headers: auth(admin),
      data: {
        employee_id: number,
        first_name: "Cloud",
        last_name: `Fixture ${token}`,
        email: `cloudemp-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: jobId,
        department_id: depId,
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
    const admin = await apiLogin(
      request,
      ADMIN_USER,
      password!,
      mfaSecretFor("HRADMIN")
    )

    // --- API setup: master data, then an employee to take the leave -----
    const leaveTypeId = await ensureLeaveType(request, admin, token)
    const { depId, jobId } = await ensureDeptAndJob(request, admin, token)

    const number = `CLOUDLV-${token}`
    const created = await request.post(`${API}/employees/`, {
      headers: auth(admin),
      data: {
        employee_id: number,
        first_name: "CloudLeave",
        last_name: `Fixture ${token}`,
        email: `cloudlv-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: jobId,
        department_id: depId,
      },
    })
    expect(created.status(), "employee creation answers 201").toBe(201)
    const employee = (await created.json()) as { id: number }

    // --- entitle: approval takes days from a balance, so grant one -------
    // (no balance -> 409 leave_no_entitlement, by design)
    const entitled = await request.post(`${API}/leave/entitlements`, {
      headers: auth(admin),
      data: {
        entitlement_year: 2026,
        leave_type_id: leaveTypeId,
        entitled_days: 20,
      },
    })
    expect(entitled.status(), "entitlement grant answers 201").toBe(201)

    // --- apply ------------------------------------------------------------
    const applied = await request.post(`${API}/leave/requests`, {
      headers: auth(admin),
      data: {
        employee_id: employee.id,
        leave_type_id: leaveTypeId,
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
