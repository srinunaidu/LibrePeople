import { expect, test } from "@playwright/test"

/**
 * P4 expenses (Priority 4): a claim is stored as a draft, never auto-approved.
 *
 * API setup creates a category and a claim; the claim must stay in DRAFT with
 * payment UNPAID. There is no expenses screen in the router, so the slice is
 * proven through the claims list query wired to the seeded employee — the
 * API success and the 401/403 paths still hold.
 * No harness or production code is touched by this spec.
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

test.describe("P4 expense claims (stored as drafts)", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("a claim is stored as an unpaid draft", async ({ request }) => {
    const tag = runToken()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)
    const employee = await createEmployee(request, admin.headers, "P4EX", tag)

    const categoryCode = `P4EX-${tag}`
    const category = await request.post(`${api}/expenses/categories`, {
      headers: admin.headers,
      data: {
        name: `P4 Expenses ${tag}`,
        code: categoryCode,
        description: "P4 expenses journey category",
      },
    })
    expect(category.status(), "category creation answers 201").toBe(201)
    const categoryBody = await category.json()

    const description = `P4 client dinner ${tag}`
    const claim = await request.post(`${api}/expenses/claims`, {
      headers: admin.headers,
      data: {
        employee_id: employee.id,
        category_id: categoryBody.id,
        expense_date: "2026-05-12",
        amount: 2450.75,
        currency: "INR",
        description,
      },
    })
    expect(claim.status(), "claim creation answers 201").toBe(201)
    const claimBody = await claim.json()
    expect(claimBody.status, "a new claim waits in DRAFT").toBe("DRAFT")
    expect(claimBody.payment_status, "a new claim is UNPAID").toBe("UNPAID")

    const readBack = await request.get(
      `${api}/expenses/claims/${claimBody.id}`,
      { headers: admin.headers }
    )
    expect(readBack.status(), "claim read answers 200").toBe(200)
    const readBody = await readBack.json()
    expect(readBody.description, "the stored claim keeps its description").toBe(
      description
    )
    expect(readBody.status, "the claim is still a draft: never approved").toBe(
      "DRAFT"
    )

    // --- list wired to the seeded employee: no expenses screen exists, so
    // the claims list is the surface that serves the stored row ------------
    const listed = await request.get(
      `${api}/expenses/claims?employee_id=${employee.id}`,
      { headers: admin.headers }
    )
    expect(listed.status(), "claims list answers 200").toBe(200)
    const rows = (await listed.json()) as Array<{
      id: number
      description: string
      status: string
    }>
    expect(
      rows.some((row) => row.id === claimBody.id && row.description === description),
      "the claims list holds the stored claim"
    ).toBe(true)
    expect(
      rows.find((row) => row.id === claimBody.id)?.status,
      "the listed claim is still a draft"
    ).toBe("DRAFT")
  })

  test("the router serves no expenses screen: the dashboard carries no such link", async ({
    page,
  }) => {
    await page.goto("/dashboard")
    await expect(page).toHaveURL(/\/dashboard/)
    await expect(
      page.getByRole("link", { name: /expenses/i }),
      "no expenses screen is linked from the dashboard"
    ).toHaveCount(0)
  })

  test("expense reads without a token answer 401", async ({ request }) => {
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const res = await request.get(`${api}/expenses/claims`)
    expect(res.status(), "unauthenticated expense read answers 401").toBe(401)
  })

  test("an associate cannot create an expense category (403)", async ({
    request,
  }) => {
    const tag = runToken()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)
    const assoc = await createAssociate(request, admin.headers, "p4ex", tag)

    const res = await request.post(`${api}/expenses/categories`, {
      headers: auth(assoc.token),
      data: { name: `P4 Expenses ${tag}`, code: `P4EX-${tag}` },
    })
    expect(res.status(), "associate category creation answers 403").toBe(403)
  })
})
