import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test"
import { completeMfaIfRequired, mfaSecretFor } from "./totp"

/**
 * Cloud E2E: reports load, and the exit workflow runs through the
 * supported surface.
 *
 * Authored, NOT RUN (no admin access yet). Reports are read-only proof:
 * the dashboard/headcount/leave summaries answer 200 through the API and
 * `/reports` loads past the login wall. The exit workflow runs through
 * terminations — create (`POST /offboarding/terminations` answers 201 with
 * a namespaced reason), read back from the list (persistence), attach the
 * exit-interview notes (`PUT /offboarding/terminations/{id}` answers 200
 * and the notes persist), and `/offboarding` serves the record. Exit
 * interviews have no dedicated backend endpoint (see README: NOT COVERED),
 * so the notes-on-termination path is the supported surface and the one
 * asserted here. Console errors and failed cloud requests are captured.
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

function adminPassword(): string | null {
  return process.env.E2E_HRADMIN_PASSWORD ?? null
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
 * Reuse-or-create the master data the exit test needs (see lifecycle spec:
 * the deployed tenant ships no departments or jobs).
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

test.describe("cloud reports and exit workflow", () => {
  test("reports answer and the screen loads", async ({ page, request }) => {
    const password = adminPassword()
    test.skip(
      password === null,
      "E2E_HRADMIN_USERNAME/E2E_HRADMIN_PASSWORD unset — the provisioned cloud HR admin is not available (see frontend/e2e/cloud/README.md)."
    )
    const { consoleErrors, failed } = watch(page)
    const admin = await apiLogin(
      request,
      ADMIN_USER,
      password!,
      mfaSecretFor("HRADMIN")
    )

    // --- API: the read-only summaries answer 200 --------------------------
    for (const path of ["/reports/dashboard", "/reports/headcount", "/reports/leave"]) {
      const res = await request.get(`${API}${path}`, {
        headers: auth(admin),
      })
      expect(res.status(), `GET ${path} answers 200`).toBe(200)
    }

    // --- UI: /reports loads past the login wall ----------------------------
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/reports`)
    await expect(page).toHaveURL(/\/reports/, { timeout: 30_000 })
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })

    expect(
      failed.filter((entry) => entry.includes("onrender")),
      "no failed cloud requests"
    ).toEqual([])
    expect(consoleErrors, "no console errors").toEqual([])
  })

  test("exit: termination created, listed, and interview notes attached", async ({
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

    // --- API setup: master-data ids, then the employee to exit ------------
    const { depId, jobId } = await ensureDeptAndJob(request, admin, token)

    const number = `CLOUDEXIT-${token}`
    const created = await request.post(`${API}/employees/`, {
      headers: auth(admin),
      data: {
        employee_id: number,
        first_name: "CloudExit",
        last_name: `Fixture ${token}`,
        email: `cloudexit-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: jobId,
        department_id: depId,
      },
    })
    expect(created.status(), "employee creation answers 201").toBe(201)
    const employee = (await created.json()) as { id: number }

    // --- exit: the termination row ------------------------------------------
    const reason = `Cloud E2E exit ${token}`
    const term = await request.post(`${API}/offboarding/terminations`, {
      headers: auth(admin),
      data: {
        employee_id: employee.id,
        last_working_date: "2026-12-31",
        termination_type: "Resignation",
        reason,
      },
    })
    expect(term.status(), "termination creation answers 201").toBe(201)
    const termination = (await term.json()) as { id: number }

    // --- persistence: the terminations list holds the stored row ------------
    const termList = await request.get(`${API}/offboarding/terminations`, {
      headers: auth(admin),
    })
    expect(termList.status(), "terminations list answers 200").toBe(200)
    const termRows = (await termList.json()) as Array<{
      id: number;
      reason?: string;
    }>
    expect(
      termRows.some((row) => row.id === termination.id && row.reason === reason),
      "the list holds the stored termination"
    ).toBe(true)

    // --- exit-interview notes ride the supported surface: the termination --
    const notes = `Cloud E2E exit interview ${token}: handover complete`
    const noted = await request.put(
      `${API}/offboarding/terminations/${termination.id}`,
      { headers: auth(admin), data: { exit_interview_notes: notes } }
    )
    expect(noted.status(), "interview notes update answers 200").toBe(200)
    const readBack = await request.get(
      `${API}/offboarding/terminations/${termination.id}`,
      { headers: auth(admin) }
    )
    expect(readBack.status(), "termination read answers 200").toBe(200)
    const stored = (await readBack.json()) as { exit_interview_notes?: string }
    expect(stored.exit_interview_notes, "the interview notes persist").toBe(
      notes
    )

    // --- UI: /offboarding serves the termination record --------------------
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/offboarding`)
    await expect(
      page.getByRole("heading", { name: "Offboarding & Termination" })
    ).toBeVisible({ timeout: 30_000 })
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(
      page
        .getByRole("table", { name: "All termination records" })
        .getByText(number),
      "the terminations table lists the exited employee"
    ).toBeVisible({ timeout: 30_000 })

    expect(
      failed.filter((entry) => entry.includes("onrender")),
      "no failed cloud requests"
    ).toEqual([])
    expect(consoleErrors, "no console errors").toEqual([])
  })

  test("a non-privileged employee cannot mint a termination (403/404)", async ({
    request,
  }) => {
    const password = process.env.E2E_EMPLOYEE_PASSWORD ?? null
    test.skip(
      password === null,
      "E2E_EMPLOYEE_USERNAME/E2E_EMPLOYEE_PASSWORD unset — the provisioned cloud employee user is not available (see frontend/e2e/cloud/README.md)."
    )
    const token = runToken()
    const employeeToken = await apiLogin(
      request,
      process.env.E2E_EMPLOYEE_USERNAME || "e2e_employee",
      password!
    )
    const res = await request.post(`${API}/offboarding/terminations`, {
      headers: auth(employeeToken),
      data: {
        employee_id: 1,
        last_working_date: "2026-12-31",
        termination_type: "Resignation",
        reason: `Cloud E2E denied exit ${token}`,
      },
    })
    // Per the app's design, unauthorised writes are refused — 403, or 404
    // where the route refuses to confirm the resource exists.
    expect(
      [403, 404],
      "termination creation by a non-privileged user is refused"
    ).toContain(res.status())
  })
})
