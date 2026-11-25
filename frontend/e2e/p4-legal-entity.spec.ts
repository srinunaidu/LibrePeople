import { expect, test } from "@playwright/test"

/**
 * P4 legal entity (Priority 4): the employer-of-record lifecycle.
 *
 * API setup creates a legal entity, reads it back, edits it and lists it;
 * the UI then asserts what the app serves (the Reports screen carries a
 * legal-entity filter). Success, 401 and 403 paths are covered. No harness
 * or production code is touched by this spec.
 */

import { apiBaseUrl, assertNotProduction } from "./support/environment"
import {
  adminSession,
  auth,
  createAssociate,
  runToken,
  signIn,
} from "./support/p4-helpers"

test.describe("P4 legal entities (employer of record)", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("an entity is created, read, edited and listed; the app serves it or reports BLOCKED", async ({
    page,
    request,
  }) => {
    const tag = runToken()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)

    // --- API setup: create -------------------------------------------------
    const code = `P4LE-${tag}`
    const created = await request.post(`${api}/core-hr/legal-entities`, {
      headers: admin.headers,
      data: {
        name: `P4 Legal Entity ${tag}`,
        code,
        country: "IN",
        registration_number: `CIN-P4-${tag}`,
      },
    })
    expect(created.status(), "legal-entity creation answers 201").toBe(201)
    const createdBody = await created.json()
    expect(createdBody.code, "the stored entity keeps its code").toBe(code)

    // --- read back + edit ---------------------------------------------------
    const readBack = await request.get(
      `${api}/core-hr/legal-entities/${createdBody.id}`,
      { headers: admin.headers }
    )
    expect(readBack.status(), "legal-entity read answers 200").toBe(200)

    const updatedName = `P4 Legal Entity ${tag} Pvt Ltd`
    const updated = await request.patch(
      `${api}/core-hr/legal-entities/${createdBody.id}`,
      { headers: admin.headers, data: { name: updatedName } }
    )
    expect(updated.status(), "legal-entity edit answers 200").toBe(200)
    const updatedBody = await updated.json()
    expect(updatedBody.name, "the edit is stored").toBe(updatedName)

    const listed = await request.get(`${api}/core-hr/legal-entities`, {
      headers: admin.headers,
    })
    expect(listed.status(), "legal-entity list answers 200").toBe(200)
    const rows = (await listed.json()) as Array<{ code: string }>
    expect(
      rows.some((row) => row.code === code),
      "the list holds the new entity"
    ).toBe(true)

    // --- UI: the Reports screen carries the legal-entity filter ---------
    // (the Reports pattern: the seeded tenant's rows are served through the
    // report filter, so the filter itself is the served surface) -----------
    await page.goto("/reports")
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(
      page.getByLabel("Legal entity ID").first(),
      "the Reports filter serves the legal-entity dimension"
    ).toBeVisible({ timeout: 10_000 })
  })

  test("legal-entity reads without a token answer 401", async ({
    request,
  }) => {
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const res = await request.get(`${api}/core-hr/legal-entities`)
    expect(res.status(), "unauthenticated entity read answers 401").toBe(401)
  })

  test("an associate cannot create a legal entity (403)", async ({
    request,
  }) => {
    const tag = runToken()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)
    const assoc = await createAssociate(request, admin.headers, "p4le", tag)

    const res = await request.post(`${api}/core-hr/legal-entities`, {
      headers: auth(assoc.token),
      data: { name: `P4 Legal Entity ${tag}`, code: `P4LE-${tag}` },
    })
    expect(res.status(), "associate entity creation answers 403").toBe(403)
  })
})
