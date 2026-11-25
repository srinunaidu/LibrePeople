import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test"

/**
 * Cloud E2E: asset assignment and employee documents.
 *
 * Authored, NOT RUN (no admin access yet). The HR admin registers a
 * namespaced asset (`POST /assets` answers 201 — every asset starts
 * `in_stock`), assigns it to a namespaced employee (`POST
 * /assets/{id}/assign`), and the assignment list holds the row
 * (persistence); `/assets` is proven to load. Documents follow the metadata
 * path the product serves: record the document (`POST
 * /core-hr/employee-documents` answers 201, version 1), upload a second
 * version (`POST .../versions` answers 201), and the version history reads
 * back oldest-first with the document moved onto version 2 (upload and
 * download history). The People detail panel is proven to list the recorded
 * document. Cross-role checks: an employee's asset creation is refused
 * (403/404), and an asset the employee has never held reads as 404 (never
 * 403), per the asset visibility design.
 *
 * There is no binary file upload and no document/comment DELETE route: the
 * "small synthetic file" is a synthetic record (no real bytes leave the
 * runner), and fixtures are namespaced `CLOUD-*` so they never collide.
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

async function makeEmployee(
  request: APIRequestContext,
  admin: string,
  prefix: string,
  token: string
): Promise<{ id: number; number: string }> {
  const [deps, jobs] = await Promise.all([
    request.get(`${API}/departments/`, { headers: auth(admin) }),
    request.get(`${API}/jobs/`, { headers: auth(admin) }),
  ])
  expect(deps.status(), "departments list answers 200").toBe(200)
  expect(jobs.status(), "jobs list answers 200").toBe(200)
  const depList = (await deps.json()) as Array<{ id: number }>
  const jobList = (await jobs.json()) as Array<{ id: number }>
  const number = `${prefix}-${token}`
  const created = await request.post(`${API}/employees/`, {
    headers: auth(admin),
    data: {
      employee_id: number,
      first_name: "Cloud",
      last_name: `Fixture ${token}`,
      email: `${prefix}-${token.toLowerCase()}@example.com`,
      hire_date: "2026-01-05",
      job_id: jobList[0].id,
      department_id: depList[0].id,
    },
  })
  expect(created.status(), "employee creation answers 201").toBe(201)
  const body = (await created.json()) as { id: number }
  return { id: body.id, number }
}

test.describe("cloud assets and documents", () => {
  test("an asset is registered, assigned, and the custody persists", async ({
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
    const employee = await makeEmployee(request, admin, "CLOUDAS", token)

    // --- register: every asset starts in_stock, status is not settable ----
    const tag = `CLOUD-${token}`
    const registered = await request.post(`${API}/assets`, {
      headers: auth(admin),
      data: {
        tag,
        name: `Cloud E2E laptop ${token}`,
        category: "IT",
      },
    })
    expect(registered.status(), "asset creation answers 201").toBe(201)
    const asset = (await registered.json()) as { id: number; status: string }
    expect(asset.status, "a new asset starts in_stock").toBe("in_stock")

    // --- assign ------------------------------------------------------------
    const assigned = await request.post(`${API}/assets/${asset.id}/assign`, {
      headers: auth(admin),
      data: { employee_id: employee.id },
    })
    expect(assigned.status(), "asset assignment answers 201").toBe(201)

    // --- persistence: the assignment list holds the custody row ------------
    const custody = await request.get(`${API}/assets/assignments`, {
      headers: auth(admin),
    })
    expect(custody.status(), "assignments list answers 200").toBe(200)
    const rows = (await custody.json()) as Array<{
      asset_id: number;
      employee_id: number;
    }>
    expect(
      rows.some(
        (row) => row.asset_id === asset.id && row.employee_id === employee.id
      ),
      "the assignment persists in the custody list"
    ).toBe(true)

    // --- UI: /assets loads and names the registered asset ------------------
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/assets`)
    await expect(page).toHaveURL(/\/assets/, { timeout: 30_000 })
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(page.getByText(tag).first()).toBeVisible({
      timeout: 30_000,
    })

    expect(
      failed.filter((entry) => entry.includes("onrender")),
      "no failed cloud requests"
    ).toEqual([])
    expect(consoleErrors, "no console errors").toEqual([])
  })

  test("a document is recorded, versioned, and the history reads back", async ({
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
    const employee = await makeEmployee(request, admin, "CLOUDDC", token)

    // --- record: the synthetic file is metadata, no real bytes ------------
    const fileName = `contract-${token}.pdf`
    const recorded = await request.post(`${API}/core-hr/employee-documents`, {
      headers: auth(admin),
      data: {
        employee_id: employee.id,
        document_type: "Contract",
        file_name: fileName,
        storage_url: `https://files.example.test/${token}/contract.pdf`,
      },
    })
    expect(recorded.status(), "document record answers 201").toBe(201)
    const doc = (await recorded.json()) as {
      id: number;
      current_version: number;
    }
    expect(doc.current_version, "the first upload is version 1").toBe(1)

    // --- second upload: the document moves onto version 2 ------------------
    const v2Name = `contract-${token}-v2.pdf`
    const uploaded = await request.post(
      `${API}/core-hr/employee-documents/${doc.id}/versions`,
      {
        headers: auth(admin),
        data: {
          file_name: v2Name,
          storage_url: `https://files.example.test/${token}/contract-v2.pdf`,
        },
      }
    )
    expect(uploaded.status(), "version upload answers 201").toBe(201)
    const v2 = (await uploaded.json()) as { version_no: number }
    expect(v2.version_no, "the upload appends version 2").toBe(2)

    // --- download history: oldest first, both rows present ------------------
    const history = await request.get(
      `${API}/core-hr/employee-documents/${doc.id}/versions`,
      { headers: auth(admin) }
    )
    expect(history.status(), "version history answers 200").toBe(200)
    const versions = (await history.json()) as Array<{
      version_no: number;
      file_name: string;
    }>
    expect(versions.length, "both versions persist").toBe(2)
    expect(
      versions.map((v) => v.version_no),
      "history reads oldest first"
    ).toEqual([1, 2])

    // --- UI: the People detail panel lists the recorded document -----------
    await signIn(page, ADMIN_USER, password!)
    await page.goto(`${APP}/people`)
    await expect(
      page.getByRole("heading", { name: "People", level: 1 })
    ).toBeVisible({ timeout: 30_000 })
    const personRow = page.getByRole("button", {
      name: `Cloud Fixture ${token}`,
    })
    const loadMore = page.getByRole("button", { name: "Load more employees" })
    for (let attempt = 0; attempt < 20 && !(await personRow.isVisible()); attempt++) {
      if (!(await loadMore.isVisible())) break
      await loadMore.click()
    }
    await expect(personRow, "the directory lists the new employee").toBeVisible()
    await personRow.click()
    const panel = page.getByRole("dialog")
    const documents = panel.getByRole("region", {
      name: "Documents recorded for this employee",
    })
    await expect(
      documents.getByRole("row", { name: new RegExp(v2Name) }),
      "the panel lists the newest document version"
    ).toBeVisible({ timeout: 30_000 })

    expect(
      failed.filter((entry) => entry.includes("onrender")),
      "no failed cloud requests"
    ).toEqual([])
    expect(consoleErrors, "no console errors").toEqual([])
  })

  test("asset boundaries hold for the employee (refused create, 404 stranger asset)", async ({
    request,
  }) => {
    const adminPw = adminPassword()
    const employeePw = employeePassword()
    test.skip(
      adminPw === null || employeePw === null,
      "E2E_HRADMIN_* and E2E_EMPLOYEE_* variables unset — the boundary probe needs both provisioned users (see frontend/e2e/cloud/README.md)."
    )
    const token = runToken()
    const admin = await apiLogin(request, ADMIN_USER, adminPw!)
    const registered = await request.post(`${API}/assets`, {
      headers: auth(admin),
      data: { tag: `CLOUD-PVT-${token}`, name: `Private asset ${token}` },
    })
    expect(registered.status(), "asset creation answers 201").toBe(201)
    const asset = (await registered.json()) as { id: number }

    const employeeToken = await apiLogin(request, EMPLOYEE_USER, employeePw!)
    const created = await request.post(`${API}/assets`, {
      headers: auth(employeeToken),
      data: { tag: `CLOUD-NO-${token}`, name: "No asset" },
    })
    expect([403, 404], "asset creation by an employee is refused").toContain(
      created.status()
    )

    // Assets the employee has never held read as 404, never 403: the
    // response must not confirm the asset exists.
    const stranger = await request.get(`${API}/assets/${asset.id}`, {
      headers: auth(employeeToken),
    })
    expect(stranger.status(), "a stranger's asset reads as 404").toBe(404)
  })
})
