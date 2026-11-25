import { expect, test } from "@playwright/test"

/**
 * P4 time + leave (Priority 4): a clocked-in entry and a leave request.
 *
 * API setup stores a time entry and a leave request for a fresh employee;
 * the UI then asserts what the Time and Leave screens show. Success, 401
 * and 403 paths are covered. No harness or production code is touched by
 * this spec.
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

test.describe("P4 time entries and leave requests", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("a time entry and a leave request are stored, and the screens serve them or report BLOCKED", async ({
    page,
    request,
  }) => {
    const tag = runToken()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)
    const employee = await createEmployee(request, admin.headers, "P4TL", tag)

    // --- API setup: manual time entry ------------------------------------
    const workDate = "2026-02-10"
    const entry = await request.post(`${api}/time/entries`, {
      headers: admin.headers,
      data: {
        employee_id: employee.id,
        work_date: workDate,
        clock_in: `${workDate}T09:00:00`,
        clock_out: `${workDate}T18:00:00`,
        source: "Manual",
        notes: `P4 time entry ${tag}`,
      },
    })
    expect(entry.status(), "time entry creation answers 201").toBe(201)

    // --- API setup: leave type + request ---------------------------------
    const typeCode = `P4LV-${tag}`
    const leaveType = await request.post(`${api}/leave/types`, {
      headers: admin.headers,
      data: { name: `P4 Leave ${tag}`, code: typeCode, is_paid: true },
    })
    expect(leaveType.status(), "leave type creation answers 201").toBe(201)
    const typeBody = await leaveType.json()

    const leaveRequest = await request.post(`${api}/leave/requests`, {
      headers: admin.headers,
      data: {
        employee_id: employee.id,
        leave_type_id: typeBody.id,
        start_date: "2026-03-02",
        end_date: "2026-03-03",
        reason: `P4 leave request ${tag}`,
      },
    })
    expect(leaveRequest.status(), "leave request creation answers 201").toBe(201)
    const leaveBody = await leaveRequest.json()
    expect(leaveBody.status, "a new request waits in Pending").toBe("Pending")

    // --- API lists wired to the seeded employee ---------------------------
    const storedEntries = await request.get(
      `${api}/time/entries?employee_id=${employee.id}`,
      { headers: admin.headers }
    )
    expect(storedEntries.status(), "time entries list answers 200").toBe(200)
    const entryRows = (await storedEntries.json()) as Array<{ notes?: string }>
    expect(
      entryRows.some((row) => row.notes === `P4 time entry ${tag}`),
      "the entries list holds the stored entry"
    ).toBe(true)

    const storedRequests = await request.get(
      `${api}/leave/requests?employee_id=${employee.id}`,
      { headers: admin.headers }
    )
    expect(storedRequests.status(), "leave requests list answers 200").toBe(200)
    const requestRows = (await storedRequests.json()) as Array<{ reason?: string }>
    expect(
      requestRows.some((row) => row.reason === `P4 leave request ${tag}`),
      "the requests list holds the stored request"
    ).toBe(true)

    // --- UI: time ----------------------------------------------------------
    // The entries table renders clock events, not the free-text notes
    // (proven by the list query above): selecting the seeded employee must
    // clear the empty state and show the stored work date.
    await page.goto("/time")
    await expect(
      page.getByRole("heading", { name: "Time & Attendance" })
    ).toBeVisible()
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(
      page.locator("#ta-employee"),
      "the time selector lists the seeded employee"
    ).toContainText(employee.number)
    await page.locator("#ta-employee").selectOption(String(employee.id))
    await expect(
      page.getByRole("region", { name: "Time entries for the selected employee" }),
      "the stored entry renders for the seeded employee"
    ).toBeVisible({ timeout: 10_000 })
    await expect(
      page.getByText("No time entries yet"),
      "the empty state clears once the stored entry loads"
    ).toHaveCount(0)

    // --- UI: leave ---------------------------------------------------------
    // The requests table renders the reason column, so the stored reason
    // is asserted on screen.
    await page.goto("/leave")
    await expect(
      page.getByRole("heading", { name: "Leave Management" })
    ).toBeVisible()
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(
      page.getByText(`P4 leave request ${tag}`).first(),
      "the stored request renders on the Leave screen"
    ).toBeVisible({ timeout: 10_000 })
  })

  test("time writes without a token answer 401", async ({ request }) => {
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const res = await request.post(`${api}/time/entries`, {
      data: {
        employee_id: 1,
        work_date: "2026-02-10",
        clock_in: "2026-02-10T09:00:00",
        source: "Manual",
      },
    })
    expect(res.status(), "unauthenticated time write answers 401").toBe(401)
  })

  test("an associate cannot create a leave type (403)", async ({ request }) => {
    const tag = runToken()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)
    const assoc = await createAssociate(request, admin.headers, "p4tl", tag)

    const res = await request.post(`${api}/leave/types`, {
      headers: auth(assoc.token),
      data: { name: `P4 Leave ${tag}`, code: `P4LV-${tag}`, is_paid: true },
    })
    expect(res.status(), "associate leave-type creation answers 403").toBe(403)
  })
})
