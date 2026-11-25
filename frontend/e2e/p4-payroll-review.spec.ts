import { expect, test } from "@playwright/test"

/**
 * P4 payroll review (Priority 4): a pay run is stored in Draft and reviewed.
 *
 * The slice under test is stored-only: the run is created and read back, and
 * the test asserts it sits in Draft with no calculation, approval or
 * finalization — process/approve/finalize are never called, so pay cannot be
 * activated by this spec. The UI asserts the runs screen serves the draft.
 * Success, 401 and 403 paths are covered. No harness or production code is
 * touched by this spec.
 */

import { apiBaseUrl, assertNotProduction } from "./support/environment"
import {
  adminSession,
  auth,
  createAssociate,
  runToken,
  signIn,
} from "./support/p4-helpers"

test.describe("P4 pay-run review (stored-only, never activated)", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("a draft run is stored and reviewable, and the runs screen serves it or reports BLOCKED", async ({
    page,
    request,
  }) => {
    const tag = runToken()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)

    // --- API setup: a fresh pay period ------------------------------------
    const periodName = `P4 review period ${tag}`
    const period = await request.post(`${api}/payroll/periods`, {
      headers: admin.headers,
      data: {
        name: periodName,
        start_date: "2026-04-01",
        end_date: "2026-04-30",
        pay_date: "2026-05-05",
      },
    })
    expect(period.status(), "pay period creation answers 201").toBe(201)
    const periodBody = await period.json()

    // --- the run is created and stays Draft: process, approve and ---------
    // --- finalize are deliberately never called by this spec --------------
    const run = await request.post(`${api}/payroll/runs`, {
      headers: admin.headers,
      data: { period_id: periodBody.id, jurisdiction: "IN", currency: "INR" },
    })
    expect(run.status(), "pay-run creation answers 201").toBe(201)
    const runBody = await run.json()
    expect(runBody.status, "a new run starts in Draft").toBe("Draft")

    const readBack = await request.get(`${api}/payroll/runs/${runBody.id}`, {
      headers: admin.headers,
    })
    expect(readBack.status(), "pay-run read answers 200").toBe(200)
    const readBody = await readBack.json()
    expect(readBody.status, "the run is still Draft: never activated").toBe(
      "Draft"
    )

    // --- API list wired to the seeded tenant: the runs list holds it -----
    const listed = await request.get(`${api}/payroll/runs`, {
      headers: admin.headers,
    })
    expect(listed.status(), "pay-run list answers 200").toBe(200)
    const rows = (await listed.json()) as Array<{ id: number }>
    expect(
      rows.some((row) => row.id === runBody.id),
      "the runs list holds the stored draft"
    ).toBe(true)

    // --- UI: pay runs ------------------------------------------------------
    // The Period column renders the period name, so the stored draft is
    // asserted by its period. Scoped to the runs table: the create form's
    // period <select> holds the same name in a hidden <option>.
    await page.goto("/platform/payroll/runs")
    await expect(page.getByRole("heading", { name: "Pay runs", exact: true })).toBeVisible()
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(
      page
        .getByRole("table", { name: "Pay runs of this deployment" })
        .getByText(periodName),
      "the runs screen serves the stored draft"
    ).toBeVisible({ timeout: 10_000 })
  })

  test("pay-run reads without a token answer 401", async ({ request }) => {
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const res = await request.get(`${api}/payroll/runs`)
    expect(res.status(), "unauthenticated pay-run read answers 401").toBe(401)
  })

  test("an associate cannot create a pay run (403)", async ({ request }) => {
    const tag = runToken()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)
    const assoc = await createAssociate(request, admin.headers, "p4pr", tag)

    // The role gate answers before the body is validated, so the run is
    // refused without a period ever being named.
    const res = await request.post(`${api}/payroll/runs`, {
      headers: auth(assoc.token),
      data: { period_id: 1, jurisdiction: "IN" },
    })
    expect(res.status(), "associate pay-run creation answers 403").toBe(403)
  })
})
