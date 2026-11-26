import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test"
import { completeMfaIfRequired, mfaSecretFor } from "./totp"

/**
 * Cloud E2E: interview scheduling (RC-04 live ledger).
 *
 * The HR admin schedules an interview through the UI
 * (`/admin/interview-scheduling` → `POST /api/v1/interviews`), the ledger
 * row is proven in the table and read back from the API, then status and
 * feedback are updated through the row controls (`PUT
 * /api/v1/interviews/{id}`) and proven persisted. The negative is shaped by
 * design (backend suites own the API 403): an associate opening the admin
 * screen meets the denial, never the ledger. An interview names a real
 * candidate, so setup creates a namespaced one first (`POST /candidates`
 * 201) — no fabricated ids.
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

test.describe("cloud interview scheduling: schedule, update, deny", () => {
  test("HR schedules an interview and the ledger shows it", async ({
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

    // --- API setup: a real candidate to schedule against ------------------
    const made = await request.post(`${API}/candidates/`, {
      headers: auth(admin),
      data: {
        first_name: "CloudInt",
        last_name: `Candidate ${token}`,
        email: `cloudint-${token.toLowerCase()}@example.com`,
        source: `cloud-e2e-${token}`,
      },
    })
    expect(made.status(), "candidate creation answers 201").toBe(201)
    const candidate = (await made.json()) as { id: number }

    // --- UI: schedule through the admin screen -----------------------------
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/admin/interview-scheduling`)
    await expect(
      page.getByRole("heading", { name: "Interview Scheduling" })
    ).toBeVisible({ timeout: 30_000 })
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })

    await page.locator("#interview-candidate").fill(String(candidate.id))
    await page
      .locator("#interview-stage")
      .selectOption("Technical Interview")
    await page.locator("#interview-when").fill("2026-12-10T10:00")
    await page.locator("#interview-panel").fill("e2e_hradmin, e2e_hrexec")
    await page.getByRole("button", { name: "Schedule interview" }).click()
    await expect(page.getByText("Interview scheduled.")).toBeVisible({
      timeout: 30_000,
    })

    // --- the ledger names the stored row ------------------------------------
    const row = page.getByRole("row", {
      name: new RegExp(`Technical Interview.*${candidate.id}|${candidate.id}.*Technical Interview`),
    })
    await expect(row.first(), "the ledger shows the stored interview").toBeVisible({
      timeout: 30_000,
    })

    // --- persistence: the API reads the row back as Scheduled --------------
    const listed = await request.get(
      `${API}/interviews?candidate_id=${candidate.id}`,
      { headers: auth(admin) }
    )
    expect(listed.status(), "interviews list answers 200").toBe(200)
    const rows = (await listed.json()) as Array<{
      id: number;
      candidate_id: number;
      stage: string;
      status: string;
    }>
    expect(
      rows.some(
        (iv) =>
          iv.candidate_id === candidate.id &&
          iv.stage === "Technical Interview" &&
          iv.status === "Scheduled"
      ),
      "the API holds the scheduled interview"
    ).toBe(true)

    quiet(consoleErrors, failed, "HR schedules an interview")
  })

  test("status and feedback persist through the row controls", async ({
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

    const made = await request.post(`${API}/candidates/`, {
      headers: auth(admin),
      data: {
        first_name: "CloudIntUpd",
        last_name: `Candidate ${token}`,
        email: `cloudintupd-${token.toLowerCase()}@example.com`,
      },
    })
    expect(made.status(), "candidate creation answers 201").toBe(201)
    const candidate = (await made.json()) as { id: number }

    const filed = await request.post(`${API}/interviews`, {
      headers: auth(admin),
      data: {
        candidate_id: candidate.id,
        stage: "Screening",
        interviewers: ["e2e_hradmin"],
      },
    })
    expect(filed.status(), "interview creation answers 201").toBe(201)
    const interview = (await filed.json()) as { id: number }

    // --- UI: decide the interview through its row ---------------------------
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/admin/interview-scheduling`)
    await expect(
      page.getByRole("heading", { name: "Interview Scheduling" })
    ).toBeVisible({ timeout: 30_000 })

    const statusBox = page.getByLabel(`Status for interview ${interview.id}`)
    await expect(statusBox, "the row offers a status control").toBeVisible({
      timeout: 30_000,
    })
    await statusBox.selectOption("Completed")
    const feedbackText = `Strong hire signal ${token}`
    await page
      .getByLabel(`Feedback for interview ${interview.id}`)
      .fill(feedbackText)
    const row = page.getByRole("row", {
      name: new RegExp(`${interview.id}`),
    })
    await row.getByRole("button", { name: "Save" }).click()
    await expect(page.getByText("Interview updated.")).toBeVisible({
      timeout: 30_000,
    })

    // --- persistence: the decision reads back --------------------------------
    const stored = await request.get(`${API}/interviews/${interview.id}`, {
      headers: auth(admin),
    })
    expect(stored.status(), "interview read answers 200").toBe(200)
    const decided = (await stored.json()) as {
      status: string;
      feedback?: string | null;
    }
    expect(decided.status, "the interview persists as Completed").toBe(
      "Completed"
    )
    expect(decided.feedback, "the feedback persists verbatim").toBe(
      feedbackText
    )

    quiet(consoleErrors, failed, "HR updates an interview")
  })

  test("an associate meets the role denial, never the ledger", async ({
    page,
  }) => {
    const password = employeePassword()
    test.skip(
      password === null,
      "E2E_EMPLOYEE_USERNAME/E2E_EMPLOYEE_PASSWORD unset — the provisioned cloud employee user is not available (see frontend/e2e/cloud/README.md)."
    )
    const { consoleErrors, failed } = watch(page)
    await signIn(page, EMPLOYEE_USER, password!)
    // ProtectedRoute gates /admin/* to SuperAdmin/HR with an in-place 403
    // card at the same URL (ProtectedRoute.tsx), so the component's own
    // EmptyState never mounts: denial is proven by the forbidden content.
    await page.goto(`${APP}/admin/interview-scheduling`)
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(
      page.getByRole("heading", { name: "403 — Forbidden" }),
      "an associate is refused the interview screen"
    ).toBeVisible({ timeout: 30_000 })

    quiet(consoleErrors, failed, "associate meets the denial")
  })

  test("interview reads without a token answer 401", async ({ request }) => {
    const res = await request.get(`${API}/interviews`)
    expect(res.status(), "unauthenticated interview read answers 401").toBe(
      401
    )
  })
})
