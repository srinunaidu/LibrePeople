import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test"

/**
 * Cloud E2E: the helpdesk (HR cases) opens, takes a comment, and keeps the
 * history; visibility follows the LP-SVC-003 design.
 *
 * Authored, NOT RUN (no admin access yet). The HR admin opens a namespaced
 * case (`POST /core-hr/cases` answers 201), appends a comment (`POST
 * /core-hr/cases/{id}/comments` answers 201), reads the history back
 * (persistence), and the `/admin/hrhelp-cases` screen is proven to load. The
 * cross-role boundary is the point of the design — HR sees every case while
 * anyone else sees only cases about themselves or assigned to them, and a
 * stranger's case reads as 404, never 403 — so an uninvolved employee
 * reading the new case must get 404, and an unauthenticated read gets 401.
 * Console errors and failed cloud requests are captured.
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

test.describe("cloud helpdesk: open, comment, history, visibility", () => {
  test("a case opens, takes a comment, and keeps its history", async ({
    request,
  }) => {
    const password = adminPassword()
    test.skip(
      password === null,
      "E2E_HRADMIN_USERNAME/E2E_HRADMIN_PASSWORD unset — the provisioned cloud HR admin is not available (see frontend/e2e/cloud/README.md)."
    )
    const token = runToken()
    const admin = await apiLogin(request, ADMIN_USER, password!)
    const subject = `Cloud E2E case ${token}`

    // --- open -------------------------------------------------------------
    const opened = await request.post(`${API}/core-hr/cases`, {
      headers: auth(admin),
      data: {
        subject,
        category: "General",
        priority: "Medium",
      },
    })
    expect(opened.status(), "case creation answers 201").toBe(201)
    const kase = (await opened.json()) as { id: number; status: string }
    expect(kase.id, "the case has an id").toBeTruthy()

    // --- comment ----------------------------------------------------------
    const commentText = `Cloud E2E follow-up ${token}`
    const commented = await request.post(
      `${API}/core-hr/cases/${kase.id}/comments`,
      {
        headers: auth(admin),
        data: {
          case_id: kase.id,
          author: ADMIN_USER,
          comment: commentText,
        },
      }
    )
    expect(commented.status(), "comment creation answers 201").toBe(201)

    // --- persistence: the history reads back ------------------------------
    const history = await request.get(
      `${API}/core-hr/cases/${kase.id}/comments`,
      { headers: auth(admin) }
    )
    expect(history.status(), "comment history answers 200").toBe(200)
    const rows = (await history.json()) as Array<{ comment: string }>
    expect(
      rows.some((row) => row.comment === commentText),
      "the comment persists in the case history"
    ).toBe(true)

    const queue = await request.get(`${API}/core-hr/cases`, {
      headers: auth(admin),
    })
    expect(queue.status(), "case queue answers 200").toBe(200)
    const cases = (await queue.json()) as Array<{
      id: number;
      subject: string;
    }>
    expect(
      cases.some((row) => row.id === kase.id && row.subject === subject),
      "the queue holds the opened case"
    ).toBe(true)
  })

  test("the helpdesk queue screen loads for the HR admin", async ({
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
    const subject = `Cloud E2E queue ${token}`
    const opened = await request.post(`${API}/core-hr/cases`, {
      headers: auth(admin),
      data: { subject, category: "General", priority: "Medium" },
    })
    expect(opened.status(), "case creation answers 201").toBe(201)

    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/admin/hrhelp-cases`)
    await expect(page).toHaveURL(/\/admin\/hrhelp-cases/, {
      timeout: 30_000,
    })
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(page.getByText(subject).first()).toBeVisible({
      timeout: 30_000,
    })

    expect(
      failed.filter((entry) => entry.includes("onrender")),
      "no failed cloud requests"
    ).toEqual([])
    expect(consoleErrors, "no console errors").toEqual([])
  })

  test("an uninvolved employee reads a stranger's case as 404 (never 403)", async ({
    request,
  }) => {
    const adminPw = adminPassword()
    const employeePw = employeePassword()
    test.skip(
      adminPw === null || employeePw === null,
      "E2E_HRADMIN_* and E2E_EMPLOYEE_* variables unset — the visibility probe needs both provisioned users (see frontend/e2e/cloud/README.md)."
    )
    const token = runToken()
    const admin = await apiLogin(request, ADMIN_USER, adminPw!)
    const opened = await request.post(`${API}/core-hr/cases`, {
      headers: auth(admin),
      data: {
        subject: `Cloud E2E private ${token}`,
        category: "General",
        priority: "Medium",
      },
    })
    expect(opened.status(), "case creation answers 201").toBe(201)
    const kase = (await opened.json()) as { id: number }

    // LP-SVC-003: anyone outside the case reads 404, so the response cannot
    // confirm the case exists. 403 here would leak it.
    const employeeToken = await apiLogin(request, EMPLOYEE_USER, employeePw!)
    const res = await request.get(
      `${API}/core-hr/cases/${kase.id}/comments`,
      { headers: auth(employeeToken) }
    )
    expect(res.status(), "a stranger's case reads as 404").toBe(404)
  })

  test("case reads without a token answer 401", async ({ request }) => {
    const res = await request.get(`${API}/core-hr/cases`)
    expect(res.status(), "unauthenticated case read answers 401").toBe(401)
  })
})
