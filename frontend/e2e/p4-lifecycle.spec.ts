import { expect, test } from "@playwright/test"

/**
 * P4 lifecycle (Priority 4): onboarding checklist + offboarding termination.
 *
 * API setup creates an employee, its onboarding checklist and a termination;
 * the UI then asserts what the screens show. Success, 401 and 403 paths are
 * covered. No harness or production code is touched by this spec.
 */

import { apiBaseUrl, assertNotProduction } from "./support/environment"
import {
  adminSession,
  auth,
  createAssociate,
  createEmployee,
  runToken,
  signIn,
} from "./support/p4-helpers"

test.describe("P4 employee lifecycle (onboarding + offboarding)", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("checklist and termination are stored, and the screens serve them or report BLOCKED", async ({
    page,
    request,
  }) => {
    const tag = runToken()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)
    const employee = await createEmployee(request, admin.headers, "P4LC", tag)

    // --- API setup: onboarding checklist ---------------------------------
    const checklist = await request.post(
      `${api}/onboarding/${employee.id}/checklist`,
      { headers: admin.headers }
    )
    expect(checklist.status(), "checklist creation answers 201").toBe(201)
    const tasks = (await checklist.json()) as unknown[]
    expect(tasks.length, "the checklist has tasks").toBeGreaterThan(0)

    // --- API setup: termination ------------------------------------------
    const reason = `P4 lifecycle exit ${tag}`
    const term = await request.post(`${api}/offboarding/terminations`, {
      headers: admin.headers,
      data: {
        employee_id: employee.id,
        last_working_date: "2026-12-31",
        termination_type: "Resignation",
        reason,
      },
    })
    expect(term.status(), "termination creation answers 201").toBe(201)

    // --- API list wired to the seeded tenant: the stored rows read back --
    const storedTasks = await request.get(`${api}/onboarding/${employee.id}/tasks`, {
      headers: admin.headers,
    })
    expect(storedTasks.status(), "checklist tasks list answers 200").toBe(200)
    const storedRows = (await storedTasks.json()) as unknown[]
    expect(storedRows.length, "the checklist is stored against the employee").toBeGreaterThan(0)

    const termList = await request.get(`${api}/offboarding/terminations`, {
      headers: admin.headers,
    })
    expect(termList.status(), "terminations list answers 200").toBe(200)
    const termRows = (await termList.json()) as Array<{ reason?: string }>
    expect(
      termRows.some((row) => row.reason === reason),
      "the list holds the stored termination"
    ).toBe(true)

    // --- UI: onboarding ---------------------------------------------------
    // The screen is an employee selector plus its checklist: the selector
    // lists the seeded employee and selecting it renders a default task.
    await page.goto("/onboarding")
    await expect(page.getByRole("heading", { name: "Onboarding" })).toBeVisible()
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(
      page.locator("#on-emp"),
      "the onboarding selector lists the seeded employee"
    ).toContainText(employee.number)
    await page.locator("#on-emp").selectOption(String(employee.id))
    await expect(
      page.getByText("Collect signed offer letter").first(),
      "the stored checklist renders for the seeded employee"
    ).toBeVisible({ timeout: 10_000 })

    // --- UI: offboarding --------------------------------------------------
    // The terminations table names the employee (name plus number in
    // parentheses); the free-text reason lives on the record, proven by the
    // list query above. Scoped to the table: the employee <select> above it
    // holds the same number in a hidden <option>.
    await page.goto("/offboarding")
    await expect(
      page.getByRole("heading", { name: "Offboarding & Termination" })
    ).toBeVisible()
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(
      page
        .getByRole("table", { name: "All termination records" })
        .getByText(employee.number),
      "the terminations table lists the seeded employee"
    ).toBeVisible({ timeout: 10_000 })
  })

  test("lifecycle reads without a token answer 401", async ({ request }) => {
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const res = await request.get(`${api}/onboarding/1/tasks`)
    expect(res.status(), "unauthenticated lifecycle read answers 401").toBe(401)
  })

  test("an associate cannot mint an onboarding checklist (403)", async ({
    request,
  }) => {
    const tag = runToken()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)
    const employee = await createEmployee(request, admin.headers, "P4LC", tag)
    const assoc = await createAssociate(request, admin.headers, "p4lc", tag)

    const res = await request.post(
      `${api}/onboarding/${employee.id}/checklist`,
      { headers: auth(assoc.token) }
    )
    expect(res.status(), "associate checklist creation answers 403").toBe(403)
  })
})
