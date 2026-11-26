import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test"
import { completeMfaIfRequired, mfaSecretFor } from "./totp"

/**
 * Cloud E2E: expenses — file, receipt, submit, L1 + final approve, mark paid.
 *
 * Authored against the DEPLOYED environment (expenses UI slice at
 * `frontend/src/pages/expenses/*`, API at `POST|GET /expenses/claims*`).
 * The associate files their own claim through the UI (`/expenses/new` →
 * detail), attaches a small synthetic receipt while it is a draft, and
 * submits it; the API proves each state persists. HR then drives the same
 * claim family through L1 approve → final approve → mark paid in the UI,
 * with `Approved` / `Paid` proven in the UI and read back from the API.
 * The negative is UI-shaped by design (backend suites own the API 403):
 * an associate opening a claim they cannot decide sees no approve/pay
 * buttons at all.
 *
 * Provisioning note: an Associate may only act on their own linked employee
 * (`_ensure_owner`, `expenses.py:148-153`), and no API links users to
 * employees. The associate tests therefore resolve the associate's visible
 * employee first and SKIP with the reason (NOT TESTED, owner provisioning)
 * when `e2e_employee` has no linked employee record. Categories and
 * departments/jobs are provisioned-or-reused namespaced, as in the other
 * cloud specs.
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

/** Reuse-or-create an active expense category (HR-only write). */
async function ensureCategory(
  request: APIRequestContext,
  admin: string,
  token: string
): Promise<number> {
  const list = await request.get(`${API}/expenses/categories`, {
    headers: auth(admin),
  })
  expect(list.status(), "categories list answers 200").toBe(200)
  const rows = (await list.json()) as Array<{ id: number; is_active: boolean }>
  const active = rows.find((row) => row.is_active)
  if (active) return active.id
  const created = await request.post(`${API}/expenses/categories`, {
    headers: auth(admin),
    data: { name: `Cloud E2E Cat ${token}`, code: `CEXP-${token}` },
  })
  expect(created.status(), "category creation answers 201").toBe(201)
  return ((await created.json()) as { id: number }).id
}

/** Reuse-or-create master data for the claimant's employee row. */
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

/**
 * The employee the associate may act on: Associates see only their own
 * linked row. Empty means the provisioned user has no linked employee
 * record, and every owner-gated write would 403 by design.
 */
async function associateEmployeeId(
  request: APIRequestContext,
  employeeToken: string
): Promise<number | null> {
  const res = await request.get(`${API}/employees/`, {
    headers: auth(employeeToken),
  })
  expect(res.status(), "associate directory read answers 200").toBe(200)
  const body = (await res.json()) as {
    items?: Array<{ id: number }>
  } & Array<{ id: number }>
  const items = Array.isArray(body) ? body : (body.items ?? [])
  return items[0]?.id ?? null
}

function quiet(
  consoleErrors: string[],
  failed: string[],
  where: string
): void {
  expect(
    failed.filter((entry) => entry.includes("onrender")),
    `${where}: no failed cloud requests`
  ).toEqual([])
  expect(consoleErrors, `${where}: no console errors`).toEqual([])
}

test.describe("cloud expenses: file, receipt, submit, approve, pay", () => {
  test("associate files a claim, attaches a receipt, and submits it", async ({
    page,
    request,
  }) => {
    const hrPw = adminPassword()
    const empPw = employeePassword()
    test.skip(
      hrPw === null || empPw === null,
      "E2E_HRADMIN_* and E2E_EMPLOYEE_* variables unset — the expenses flow needs both provisioned users (see frontend/e2e/cloud/README.md)."
    )
    const { consoleErrors, failed } = watch(page)
    const token = runToken()
    const admin = await apiLogin(
      request,
      ADMIN_USER,
      hrPw!,
      mfaSecretFor("HRADMIN")
    )
    const employeeToken = await apiLogin(request, EMPLOYEE_USER, empPw!)
    const ownId = await associateEmployeeId(request, employeeToken)
    test.skip(
      ownId === null,
      "e2e_employee has no linked employee record (User.employee_id) — the owner must provision the link; associate filing NOT TESTED."
    )
    const categoryId = await ensureCategory(request, admin, token)
    const fileName = `receipt-${token}.txt`
    const fileText = `Cloud E2E synthetic receipt ${token}`

    // --- UI: file the claim as a draft ------------------------------------
    await signIn(page, EMPLOYEE_USER, empPw!)
    await page.goto(`${APP}/expenses/new`)
    await expect(
      page.getByRole("heading", { name: "New expense claim" })
    ).toBeVisible({ timeout: 30_000 })
    await page.locator("#exp-employee").fill(String(ownId))
    await page.locator("#exp-category").selectOption(String(categoryId))
    await page.locator("#exp-date").fill("2026-12-01")
    await page.locator("#exp-amount").fill("2500")
    await page.locator("#exp-desc").fill(`Cloud E2E trip ${token}`)
    await page.getByRole("button", { name: "File claim" }).click()
    await expect(page).toHaveURL(/\/expenses\/\d+/, { timeout: 30_000 })
    const claimId = Number(new URL(page.url()).pathname.split("/").pop())

    // --- UI: attach the receipt while the claim is a draft ---------------
    await page
      .getByLabel("Receipt file")
      .setInputFiles({
        name: fileName,
        mimeType: "text/plain",
        buffer: Buffer.from(fileText),
      })
    await page.getByRole("button", { name: "Upload receipt" }).click()
    await expect(page.getByText("Receipt uploaded.")).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByText(fileName).first()).toBeVisible()
    const download = page.getByRole("link", { name: "Download" }).first()
    await expect(download, "the receipt offers a download link").toBeVisible()
    expect(
      await download.getAttribute("href"),
      "the download link points at the server"
    ).toBeTruthy()

    // --- UI: submit, then API proves the persisted state ------------------
    await page.getByRole("button", { name: "Submit for approval" }).click()
    await expect(page.getByText("Claim submitted.")).toBeVisible({
      timeout: 30_000,
    })

    const stored = await request.get(`${API}/expenses/claims/${claimId}`, {
      headers: auth(admin),
    })
    expect(stored.status(), "claim read answers 200").toBe(200)
    const claim = (await stored.json()) as { status: string }
    expect(claim.status, "the claim persists as SUBMITTED").toBe("SUBMITTED")

    const receipts = await request.get(
      `${API}/expenses/claims/${claimId}/receipts`,
      { headers: auth(admin) }
    )
    expect(receipts.status(), "receipts list answers 200").toBe(200)
    const rows = (await receipts.json()) as Array<{
      file_name: string;
      download_url: string;
    }>
    expect(
      rows.some(
        (row) => row.file_name === fileName && Boolean(row.download_url)
      ),
      "the receipt persists with a server download URL"
    ).toBe(true)

    quiet(consoleErrors, failed, "associate file→receipt→submit")
  })

  test("HR approves L1, then final, then marks paid", async ({
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
    const categoryId = await ensureCategory(request, admin, token)
    const { depId, jobId } = await ensureDeptAndJob(request, admin, token)
    const number = `CLOUDEXP-${token}`
    const created = await request.post(`${API}/employees/`, {
      headers: auth(admin),
      data: {
        employee_id: number,
        first_name: "CloudExp",
        last_name: `Fixture ${token}`,
        email: `cloudexp-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: jobId,
        department_id: depId,
      },
    })
    expect(created.status(), "employee creation answers 201").toBe(201)
    const employee = (await created.json()) as { id: number }

    // --- API setup: a draft claim with a receipt attached -----------------
    const filed = await request.post(`${API}/expenses/claims`, {
      headers: auth(admin),
      data: {
        employee_id: employee.id,
        category_id: categoryId,
        expense_date: "2026-12-01",
        amount: 2500,
        currency: "INR",
        description: `Cloud E2E approval ${token}`,
      },
    })
    expect(filed.status(), "claim creation answers 201").toBe(201)
    const claim = (await filed.json()) as { id: number; status: string }
    expect(claim.status, "a new claim is DRAFT").toBe("DRAFT")

    const fileName = `receipt-${token}.txt`
    const uploaded = await request.post(
      `${API}/expenses/claims/${claim.id}/receipts`,
      {
        headers: auth(admin),
        multipart: {
          file: {
            name: fileName,
            mimeType: "text/plain",
            buffer: Buffer.from(`Cloud E2E synthetic receipt ${token}`),
          },
        },
      }
    )
    expect(uploaded.status(), "receipt upload answers 201").toBe(201)
    const receipt = (await uploaded.json()) as { download_url: string }
    expect(
      receipt.download_url,
      "the receipt carries a server download URL"
    ).toBeTruthy()

    // --- UI: submit → L1 → final → paid, each refetched from the server ---
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/expenses/${claim.id}`)
    await expect(
      page.getByRole("heading", { name: `Expense claim #${claim.id}` })
    ).toBeVisible({ timeout: 30_000 })

    await page.getByRole("button", { name: "Submit for approval" }).click()
    await expect(page.getByText("Claim submitted.")).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByText("Submitted · payment UNPAID")).toBeVisible()

    await page.getByRole("button", { name: "Approve (L1)" }).click()
    await expect(page.getByText("L1 approval recorded.")).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByText("L1 approved · payment UNPAID")).toBeVisible()

    await page.getByRole("button", { name: "Approve (final)" }).click()
    await expect(page.getByText("Final approval recorded.")).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByText("Approved · payment UNPAID")).toBeVisible()

    await page.getByRole("button", { name: "Mark paid" }).click()
    await expect(page.getByText("Claim marked paid.")).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByText("Approved · payment PAID")).toBeVisible()

    // --- persistence: the decided, paid claim reads back ------------------
    const stored = await request.get(`${API}/expenses/claims/${claim.id}`, {
      headers: auth(admin),
    })
    expect(stored.status(), "claim read answers 200").toBe(200)
    const decided = (await stored.json()) as {
      status: string;
      payment_status: string;
    };
    expect(decided.status, "the claim persists as APPROVED").toBe("APPROVED")
    expect(decided.payment_status, "the claim persists as PAID").toBe("PAID")

    quiet(consoleErrors, failed, "HR submit→L1→final→paid")
  })

  test("an associate cannot approve: no approve or pay buttons", async ({
    page,
    request,
  }) => {
    const hrPw = adminPassword()
    const empPw = employeePassword()
    test.skip(
      hrPw === null || empPw === null,
      "E2E_HRADMIN_* and E2E_EMPLOYEE_* variables unset — the negative probe needs both provisioned users (see frontend/e2e/cloud/README.md)."
    )
    const { consoleErrors, failed } = watch(page)
    const token = runToken()
    const admin = await apiLogin(
      request,
      ADMIN_USER,
      hrPw!,
      mfaSecretFor("HRADMIN")
    )
    const categoryId = await ensureCategory(request, admin, token)
    const { depId, jobId } = await ensureDeptAndJob(request, admin, token)
    const number = `CLOUDEXPN-${token}`
    const created = await request.post(`${API}/employees/`, {
      headers: auth(admin),
      data: {
        employee_id: number,
        first_name: "CloudExpNeg",
        last_name: `Fixture ${token}`,
        email: `cloudexpn-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: jobId,
        department_id: depId,
      },
    })
    expect(created.status(), "employee creation answers 201").toBe(201)
    const employee = (await created.json()) as { id: number }
    const filed = await request.post(`${API}/expenses/claims`, {
      headers: auth(admin),
      data: {
        employee_id: employee.id,
        category_id: categoryId,
        expense_date: "2026-12-01",
        amount: 1000,
        currency: "INR",
        description: `Cloud E2E denied ${token}`,
      },
    })
    expect(filed.status(), "claim creation answers 201").toBe(201)
    const claim = (await filed.json()) as { id: number }
    const submitted = await request.post(
      `${API}/expenses/claims/${claim.id}/submit`,
      { headers: auth(admin) }
    )
    expect(submitted.status(), "claim submission answers 200").toBe(200)

    // --- UI as associate: the decision buttons are never rendered ---------
    // (showApproveActions is Manager+; ExpenseDetail only renders approve/pay
    // inside that gate). An unlinked associate instead meets the visibility
    // denial — either way no decision can be clicked.
    await signIn(page, EMPLOYEE_USER, empPw!)
    await page.goto(`${APP}/expenses/${claim.id}`)
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(
      page.getByRole("button", {
        name: /Approve \(L1\)|Approve \(final\)|Mark paid/,
      }),
      "an associate is offered no approve or pay action"
    ).toHaveCount(0)

    quiet(consoleErrors, failed, "associate cannot approve")
  })
})
