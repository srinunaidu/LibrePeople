import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test"
import { completeMfaIfRequired, mfaSecretFor } from "./totp"

/**
 * Cloud E2E: ER case lifecycle, extended asset custody, expense revise.
 *
 * Genuinely new vs the existing pack (register/assign core lives in
 * `cloud-assets-documents.spec.ts`, interview schedule→complete in
 * `cloud-interview-scheduling.spec.ts` — both run as regression, not
 * duplicated here):
 *
 * 1. ER (new `/admin/er-cases` module, gap #9): HR opens a case, classifies
 *    and assigns it, appends an investigation note, and walks it
 *    Open→Triaged→Investigating→ActionTaken→Resolved→Closed through the
 *    UI, with history and final state read back from the API. An associate
 *    sees nothing: the queue screen is HR-gated and the API answers 404
 *    (never 403) for a stranger's case.
 * 2. Assets extended: HR registers and assigns to the associate's linked
 *    employee; the associate acknowledges in My Assets (self-only); HR
 *    transfers, returns as damaged (→ maintenance), completes maintenance
 *    (→ in_stock) and retires with a reason. Every transition is asserted
 *    on the API; acknowledgement and the final state are proven in the UI.
 * 3. Expense revise: submit → L1 approve → reject → rework → resubmit →
 *    final approve → mark paid, through the existing expenses UI, with the
 *    decided/paid state read back from the API.
 *
 * Associate flows gate on a linked employee record (`GET /employees/` as
 * the associate): when unlinked the test SKIPS with the provisioning
 * reason (owner must set `User.employee_id`), never fails.
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

test.describe("cloud ER, extended custody, expense revise", () => {
  test("ER case runs open to closed with notes and history", async ({
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
    const { depId, jobId } = await ensureDeptAndJob(request, admin, token)
    const subj = await request.post(`${API}/employees/`, {
      headers: auth(admin),
      data: {
        employee_id: `CLOUDER-${token}`,
        first_name: "CloudEr",
        last_name: `Subject ${token}`,
        email: `clouder-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: jobId,
        department_id: depId,
      },
    })
    expect(subj.status(), "subject employee creation answers 201").toBe(201)
    const subject = (await subj.json()) as { id: number }

    // --- open with classification, assigned to the HR admin ------------------
    const opened = await request.post(`${API}/er-cases`, {
      headers: auth(admin),
      data: {
        case_type: "grievance",
        subject_employee_id: subject.id,
        severity: "High",
        classification: `Cloud E2E ${token}`,
        assigned_to: ADMIN_USER,
      },
    })
    expect(opened.status(), "ER case creation answers 201").toBe(201)
    const kase = (await opened.json()) as { id: number; status: string }
    expect(kase.status, "a new ER case is Open").toBe("Open")

    // --- UI: the queue serves the row; open the detail -------------------------
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/admin/er-cases`)
    await expect(
      page.getByRole("heading", { name: "Employee Relations" })
    ).toBeVisible({ timeout: 30_000 })
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await page
      .getByRole("row", { name: new RegExp(`#${kase.id}`) })
      .getByRole("button", { name: "Open" })
      .click()
    await expect(
      page.getByRole("heading", { name: `Case #${kase.id} — grievance` })
    ).toBeVisible({ timeout: 30_000 })

    // --- investigation note (append-only history) --------------------------------
    const noteText = `Cloud E2E note ${token}: interview scheduled`
    await page
      .getByPlaceholder("Add an investigation note")
      .fill(noteText)
    await page.getByRole("button", { name: "Add note" }).click()
    await expect(page.getByText("Note recorded.")).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByText(noteText)).toBeVisible({ timeout: 30_000 })

    // --- walk the machine to Closed (outcome required at Resolved) ---------------
    const moves = ["Triaged", "Investigating", "ActionTaken", "Resolved", "Closed"]
    for (const next of moves) {
      if (next === "Resolved") {
        await page
          .getByPlaceholder("Recorded action / finding")
          .fill(`Cloud E2E outcome ${token}`)
      }
      await page.getByRole("button", { name: `Move to ${next}` }).click()
      await expect(
        page.getByText(`Case #${kase.id} moved to ${next}.`)
      ).toBeVisible({ timeout: 30_000 })
    }

    // --- persistence: Closed with the full history ---------------------------------
    const stored = await request.get(`${API}/er-cases/${kase.id}`, {
      headers: auth(admin),
    })
    expect(stored.status(), "ER case read answers 200").toBe(200)
    expect(
      (await stored.json()) as { status: string },
      "the case persists as Closed"
    ).toMatchObject({ status: "Closed" })
    const history = await request.get(`${API}/er-cases/${kase.id}/comments`, {
      headers: auth(admin),
    })
    expect(history.status(), "ER comments read answers 200").toBe(200)
    const notes = (await history.json()) as Array<{ comment: string }>
    expect(
      notes.some((row) => row.comment === noteText),
      "the investigation note persists in the history"
    ).toBe(true)

    quiet(consoleErrors, failed, "ER open→closed")
  })

  test("an associate sees no ER case (API 404, HR-gated screen)", async ({
    page,
    request,
  }) => {
    const adminPw = adminPassword()
    const employeePw = employeePassword()
    test.skip(
      adminPw === null || employeePw === null,
      "E2E_HRADMIN_* and E2E_EMPLOYEE_* variables unset — the ER visibility probe needs both provisioned users (see frontend/e2e/cloud/README.md)."
    )
    const { consoleErrors, failed } = watch(page)
    const token = runToken()
    const admin = await apiLogin(
      request,
      ADMIN_USER,
      adminPw!,
      mfaSecretFor("HRADMIN")
    )
    const opened = await request.post(`${API}/er-cases`, {
      headers: auth(admin),
      data: {
        case_type: "investigation",
        severity: "Medium",
        classification: `Cloud E2E private ${token}`,
      },
    })
    expect(opened.status(), "ER case creation answers 201").toBe(201)
    const kase = (await opened.json()) as { id: number }

    // ER subjects see NOTHING — not even cases about themselves. A stranger
    // reads 404, never 403, so the response cannot confirm the case exists.
    // API-only here: no page traffic, so no console noise to filter.
    const employeeToken = await apiLogin(request, EMPLOYEE_USER, employeePw!)
    const res = await request.get(`${API}/er-cases/${kase.id}`, {
      headers: auth(employeeToken),
    })
    expect(res.status(), "a stranger's ER case reads as 404").toBe(404)

    // The queue screen itself is HR-gated (ProtectedRoute + canView).
    await signIn(page, EMPLOYEE_USER, employeePw!)
    await page.goto(`${APP}/admin/er-cases`)
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(
      page.getByText("Not visible for your role").first(),
      "an associate is refused the ER queue"
    ).toBeVisible({ timeout: 30_000 })

    quiet(consoleErrors, failed, "ER associate denial")
  })

  test("extended custody: ack, transfer, damaged return, maintenance, retire", async ({
    page,
    request,
  }) => {
    const hrPw = adminPassword()
    const empPw = employeePassword()
    test.skip(
      hrPw === null || empPw === null,
      "E2E_HRADMIN_* and E2E_EMPLOYEE_* variables unset — the custody chain needs both provisioned users (see frontend/e2e/cloud/README.md)."
    )
    const { consoleErrors, failed } = watch(page)
    const token = runToken()
    const admin = await apiLogin(
      request,
      ADMIN_USER,
      hrPw!,
      mfaSecretFor("HRADMIN")
    )
    const { depId, jobId } = await ensureDeptAndJob(request, admin, token)
    const employeeToken = await apiLogin(request, EMPLOYEE_USER, empPw!)
    const dir = await request.get(`${API}/employees/`, {
      headers: auth(employeeToken),
    })
    expect(dir.status(), "associate directory read answers 200").toBe(200)
    const dirBody = (await dir.json()) as {
      items?: Array<{ id: number }>
    } & Array<{ id: number }>
    const ownId = (Array.isArray(dirBody) ? dirBody : (dirBody.items ?? []))[0]?.id
    test.skip(
      ownId === undefined,
      "e2e_employee has no linked employee record (User.employee_id) — owner must provision the link; custody chain NOT TESTED."
    )
    const second = await request.post(`${API}/employees/`, {
      headers: auth(admin),
      data: {
        employee_id: `CLOUDEXT-${token}`,
        first_name: "CloudExt",
        last_name: `Second ${token}`,
        email: `cloudext-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: jobId,
        department_id: depId,
      },
    })
    expect(second.status(), "employee creation answers 201").toBe(201)
    const secondId = ((await second.json()) as { id: number }).id

    // --- register + assign to the associate's linked employee ----------------------
    const tag = `CLOUDEXT-${token}`
    const regRes = await request.post(`${API}/assets`, {
      headers: auth(admin),
      data: { tag, name: `Cloud E2E custody ${token}`, category: "IT" },
    })
    expect(regRes.status(), "asset creation answers 201").toBe(201)
    const asset = (await regRes.json()) as { id: number }
    const assignRes = await request.post(`${API}/assets/${asset.id}/assign`, {
      headers: auth(admin),
      data: { employee_id: ownId },
    })
    expect(assignRes.status(), "asset assignment answers 200").toBe(200)
    const assignment = (await assignRes.json()) as { id: number }

    // --- UI: the associate acknowledges in My Assets (self-only) ---------------------
    await signIn(page, EMPLOYEE_USER, empPw!)
    await page.goto(`${APP}/my-assets`)
    await page
      .getByRole("button", { name: "Acknowledge receipt" })
      .first()
      .click()
    await expect(
      page.getByText("Receipt acknowledged.")
    ).toBeVisible({ timeout: 30_000 })
    const acked = await request.get(
      `${API}/assets/assignments?asset_id=${asset.id}`,
      { headers: auth(admin) }
    )
    expect(acked.status(), "assignments read answers 200").toBe(200)
    const spells = (await acked.json()) as Array<{
      id: number;
      acknowledged_at?: string | null;
    }>
    expect(
      spells.some((row) => row.id === assignment.id && Boolean(row.acknowledged_at)),
      "the acknowledgement persists on the spell"
    ).toBe(true)

    // --- transfer → damaged return (→ maintenance) → complete → retire ----------------
    const moved = await request.post(`${API}/assets/${asset.id}/transfer`, {
      headers: auth(admin),
      data: { employee_id: secondId },
    })
    expect(moved.status(), "transfer answers 200").toBe(200)
    const returned = await request.post(`${API}/assets/${asset.id}/return`, {
      headers: auth(admin),
      data: { condition: "damaged" },
    })
    expect(returned.status(), "damaged return answers 200").toBe(200)
    let state = (await (
      await request.get(`${API}/assets/${asset.id}`, { headers: auth(admin) })
    ).json()) as { status: string }
    expect(state.status, "damaged return parks the asset in maintenance").toBe(
      "maintenance"
    )
    const completed = await request.post(
      `${API}/assets/${asset.id}/maintenance/complete`,
      { headers: auth(admin), data: {} }
    )
    expect(completed.status(), "maintenance completion answers 200").toBe(200)
    state = (await (
      await request.get(`${API}/assets/${asset.id}`, { headers: auth(admin) })
    ).json()) as { status: string }
    expect(state.status, "completion returns the asset in stock").toBe("in_stock")
    const retired = await request.post(`${API}/assets/${asset.id}/retire`, {
      headers: auth(admin),
      data: { reason: `Cloud E2E chain ${token}` },
    })
    expect(retired.status(), "retire answers 200").toBe(200)

    // --- final UI + API proof ----------------------------------------------------------
    await signIn(page, ADMIN_USER, hrPw!)
    await page.goto(`${APP}/assets`)
    await expect(page.getByText(tag).first()).toBeVisible({
      timeout: 30_000,
    })
    const stored = (await (
      await request.get(`${API}/assets/${asset.id}`, { headers: auth(admin) })
    ).json()) as { status: string }
    expect(stored.status, "the asset rests retired").toBe("retired")

    quiet(consoleErrors, failed, "extended custody chain")
  })

  test("expense revise: submit, L1, reject, rework, resubmit, final, paid", async ({
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
    const catList = await request.get(`${API}/expenses/categories`, {
      headers: auth(admin),
    })
    expect(catList.status(), "categories list answers 200").toBe(200)
    const catRows = (await catList.json()) as Array<{ id: number }>
    expect(catRows.length, "a category exists").toBeGreaterThan(0)
    const { depId, jobId } = await ensureDeptAndJob(request, admin, token)
    const empRes = await request.post(`${API}/employees/`, {
      headers: auth(admin),
      data: {
        employee_id: `CLOUDEXR-${token}`,
        first_name: "CloudExpR",
        last_name: `Fixture ${token}`,
        email: `cloudexpr-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: jobId,
        department_id: depId,
      },
    })
    expect(empRes.status(), "employee creation answers 201").toBe(201)
    const employee = (await empRes.json()) as { id: number }
    const filed = await request.post(`${API}/expenses/claims`, {
      headers: auth(admin),
      data: {
        employee_id: employee.id,
        category_id: catRows[0].id,
        expense_date: "2026-12-01",
        amount: 1200,
        currency: "INR",
        description: `Cloud E2E revise ${token}`,
      },
    })
    expect(filed.status(), "claim creation answers 201").toBe(201)
    const claim = (await filed.json()) as { id: number }

    // --- UI: submit → L1 → reject → back to draft → submit → L1 → final → paid --
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/expenses/${claim.id}`)
    await expect(
      page.getByRole("heading", { name: `Expense claim #${claim.id}` })
    ).toBeVisible({ timeout: 30_000 })

    await page.getByRole("button", { name: "Submit for approval" }).click()
    await expect(page.getByText("Claim submitted.")).toBeVisible({
      timeout: 30_000,
    })
    await page.getByRole("button", { name: "Approve (L1)" }).click()
    await expect(page.getByText("L1 approval recorded.")).toBeVisible({
      timeout: 30_000,
    })
    await page.getByLabel("Rejection reason").fill(`Cloud E2E recheck ${token}`)
    await page.getByRole("button", { name: "Reject" }).click()
    await expect(page.getByText("Claim rejected.")).toBeVisible({
      timeout: 30_000,
    })
    await page.getByRole("button", { name: "Send back to draft" }).click()
    await expect(page.getByText("Claim sent back to draft.")).toBeVisible({
      timeout: 30_000,
    })
    await page.getByRole("button", { name: "Submit for approval" }).click()
    await expect(page.getByText("Claim submitted.")).toBeVisible({
      timeout: 30_000,
    })
    await page.getByRole("button", { name: "Approve (L1)" }).click()
    await expect(page.getByText("L1 approval recorded.")).toBeVisible({
      timeout: 30_000,
    })
    await page.getByRole("button", { name: "Approve (final)" }).click()
    await expect(page.getByText("Final approval recorded.")).toBeVisible({
      timeout: 30_000,
    })
    await page.getByRole("button", { name: "Mark paid" }).click()
    await expect(page.getByText("Claim marked paid.")).toBeVisible({
      timeout: 30_000,
    })

    // --- persistence: decided and paid --------------------------------------------------
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

    quiet(consoleErrors, failed, "expense revise chain")
  })
})
