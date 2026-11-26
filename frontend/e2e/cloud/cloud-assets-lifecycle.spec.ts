import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test"
import { completeMfaIfRequired, mfaSecretFor } from "./totp"

/**
 * Cloud E2E: asset lifecycle completion (backlog item C UI slice).
 *
 * The register/assign/custody core is covered by
 * `cloud-assets-documents.spec.ts` (run as regression on this HEAD); this
 * file adds only what is genuinely new: server-side filters
 * (`?status=`/`?category=` via `#ast-fstatus`/`#ast-fcat`), metadata edit
 * through `PATCH /assets/{id}` (status is never editable), the per-asset
 * custody history (`GET /assets/assignments?asset_id=`), the clearance
 * projection (`GET /assets/clearance/{employee_id}`), and the retire
 * confirm gate (`#ast-retire-reason` + `#ast-retire-confirm` must both be
 * satisfied before Retire enables).
 *
 * The retire flow runs against a DEDICATED synthetic asset that nothing
 * else uses; it is retired for real (final state) and left in place —
 * there is no delete route, and the tag stays namespaced `CLOUDRT-*`.
 * Interview schedule→complete is NOT duplicated here: it is covered by
 * `cloud-interview-scheduling.spec.ts`, run as regression below.
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

test.describe("cloud asset lifecycle: filters, edit, history, clearance, retire", () => {
  test("filters narrow the register; metadata edit persists; history and clearance read back", async ({
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
    const empRes = await request.post(`${API}/employees/`, {
      headers: auth(admin),
      data: {
        employee_id: `CLOUDLC-${token}`,
        first_name: "CloudLc",
        last_name: `Holder ${token}`,
        email: `cloudlc-${token.toLowerCase()}@example.com`,
        hire_date: "2026-01-05",
        job_id: jobId,
        department_id: depId,
      },
    })
    expect(empRes.status(), "employee creation answers 201").toBe(201)
    const employee = (await empRes.json()) as { id: number }

    // --- API setup: a namespaced, assigned IT asset -------------------------
    const tag = `CLOUDLC-${token}`
    const regRes = await request.post(`${API}/assets`, {
      headers: auth(admin),
      data: { tag, name: `Cloud E2E laptop ${token}`, category: "IT" },
    })
    expect(regRes.status(), "asset creation answers 201").toBe(201)
    const asset = (await regRes.json()) as { id: number }
    const assignRes = await request.post(`${API}/assets/${asset.id}/assign`, {
      headers: auth(admin),
      data: { employee_id: employee.id },
    })
    expect(assignRes.status(), "asset assignment answers 200").toBe(200)

    // --- UI: server-side filters narrow the register -----------------------
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/assets`)
    await expect(page.getByText(tag).first()).toBeVisible({
      timeout: 30_000,
    })
    await page.locator("#ast-fcat").selectOption("IT")
    await expect(page.getByText(tag).first()).toBeVisible({
      timeout: 30_000,
    })
    await page.locator("#ast-fstatus").selectOption("in_stock")
    // An assigned asset must drop out of the in-stock filter.
    await expect(page.getByText(tag)).toHaveCount(0, { timeout: 30_000 })
    await page.getByRole("button", { name: "Clear filters" }).click()
    await expect(page.getByText(tag).first()).toBeVisible({
      timeout: 30_000,
    })

    // --- UI: manage the asset, edit metadata (status never editable) --------
    const row = page.getByRole("row", { name: new RegExp(tag) }).first()
    await row.getByRole("button", { name: "Manage" }).click()
    await expect(
      page.getByRole("heading", { name: `Manage ${tag}` })
    ).toBeVisible({ timeout: 30_000 })
    const newName = `Cloud E2E laptop LC ${token}`
    await page.locator("#ast-edit-name").fill(newName)
    await page.getByRole("button", { name: "Save metadata" }).click()
    await expect(page.getByText("Asset metadata updated.")).toBeVisible({
      timeout: 30_000,
    })
    const stored = await request.get(`${API}/assets/${asset.id}`, {
      headers: auth(admin),
    })
    expect(stored.status(), "asset read answers 200").toBe(200)
    const updated = (await stored.json()) as {
      name: string;
      status: string;
    }
    expect(updated.name, "the edited name persists").toBe(newName)
    expect(updated.status, "the status did not move on edit").toBe("assigned")

    // --- UI: custody history names the holder --------------------------------
    const history = page.getByRole("table", {
      name: `Custody history for ${tag}`,
    })
    await expect(
      history.getByText(`CloudLc Holder ${token}`).first(),
      "the custody history names the holder"
    ).toBeVisible({ timeout: 30_000 })

    // --- UI: clearance projection for the holder ------------------------------
    await page.locator("#ast-clear-emp").fill(String(employee.id))
    await page.getByRole("button", { name: "Check clearance" }).click()
    await expect(
      page.getByText(new RegExp(`Employee ${employee.id}`)).first(),
      "the clearance projection names the employee"
    ).toBeVisible({ timeout: 30_000 })

    quiet(consoleErrors, failed, "filters→edit→history→clearance")
  })

  test("retire requires reason plus explicit confirm, on a dedicated asset", async ({
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

    // --- dedicated synthetic: nothing else touches it, it stays retired -----
    const tag = `CLOUDRT-${token}`
    const regRes = await request.post(`${API}/assets`, {
      headers: auth(admin),
      data: { tag, name: `Cloud E2E retire ${token}`, category: "IT" },
    })
    expect(regRes.status(), "asset creation answers 201").toBe(201)
    const asset = (await regRes.json()) as { id: number; status: string }
    expect(asset.status, "a fresh asset starts in_stock").toBe("in_stock")

    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/assets`)
    await expect(page.getByText(tag).first()).toBeVisible({
      timeout: 30_000,
    })
    const row = page.getByRole("row", { name: new RegExp(tag) }).first()
    await row.getByRole("button", { name: "Manage" }).click()
    await expect(
      page.getByRole("heading", { name: `Manage ${tag}` })
    ).toBeVisible({ timeout: 30_000 })

    // --- the confirm gate: reason AND checkbox, in that order -----------------
    const retire = page.getByRole("button", { name: "Retire", exact: true })
    await expect(retire, "Retire starts disabled").toBeDisabled()
    await page
      .locator("#ast-retire-reason")
      .fill(`Cloud E2E end of life ${token}`)
    await expect(
      retire,
      "a reason alone does not enable Retire"
    ).toBeDisabled()
    await page.locator("#ast-retire-confirm").check()
    await expect(
      retire,
      "reason plus explicit confirm enables Retire"
    ).toBeEnabled()
    await retire.click()
    await expect(page.getByText("Asset retired.")).toBeVisible({
      timeout: 30_000,
    })

    // --- persistence: the asset rests retired ---------------------------------
    const stored = await request.get(`${API}/assets/${asset.id}`, {
      headers: auth(admin),
    })
    expect(stored.status(), "asset read answers 200").toBe(200)
    expect(
      (await stored.json()) as { status: string },
      "the dedicated asset stays retired"
    ).toMatchObject({ status: "retired" })

    quiet(consoleErrors, failed, "retire confirm gate")
  })
})
