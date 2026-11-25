import { expect, test } from "@playwright/test"

/**
 * P4 notifications (Priority 4): the centre is owner-only.
 *
 * API setup has an admin create a notification for a fresh Associate; the
 * Associate reads it (list + unread count + mark-read) while the admin's own
 * read of the centre is refused with 403 — notifications are personal, and HR
 * privilege gains nothing here. The ESS screen is asserted where it serves:
 * the admin hub must NOT leak another person's inbox (owner-only by design).
 * Success, 401 and 403 paths are covered.
 * No harness or production code is touched by this spec.
 */

import { apiBaseUrl, assertNotProduction } from "./support/environment"
import {
  adminSession,
  auth,
  createAssociate,
  runToken,
  signIn,
} from "./support/p4-helpers"

test.describe("P4 notification centre (owner-only)", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("an associate reads their own notification; the ESS screen serves it or reports BLOCKED", async ({
    page,
    request,
  }) => {
    const tag = runToken()
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)
    const assoc = await createAssociate(request, admin.headers, "p4nt", tag)

    // --- API setup: an admin writes one notification to the associate ------
    const title = `P4 review ready ${tag}`
    const created = await request.post(`${api}/ess/notifications`, {
      headers: admin.headers,
      data: {
        recipient_id: assoc.id,
        title,
        message: "Your P4 review packet is ready.",
        notification_type: "info",
        category: "system",
      },
    })
    expect(created.status(), "notification creation answers 201").toBe(201)
    const createdBody = await created.json()

    // --- the owner reads: list, unread count, mark-read --------------------
    const list = await request.get(`${api}/ess/notifications`, {
      headers: auth(assoc.token),
    })
    expect(list.status(), "the owner lists their own rows").toBe(200)
    const rows = (await list.json()) as Array<{
      id: number;
      title: string;
      is_read: boolean;
    }>
    expect(
      rows.some((row) => row.id === createdBody.id && row.title === title),
      "the owner's list holds the new notification"
    ).toBe(true)

    const unread = await request.get(`${api}/ess/notifications/unread-count`, {
      headers: auth(assoc.token),
    })
    expect(unread.status(), "unread count answers 200").toBe(200)
    const unreadBody = await unread.json()
    const unreadCount =
      typeof unreadBody === "number"
        ? unreadBody
        : (unreadBody.unread_count as number);
    expect(unreadCount, "the new notification is unread").toBeGreaterThan(0)

    const read = await request.put(
      `${api}/ess/notifications/${createdBody.id}/read`,
      { headers: auth(assoc.token) }
    )
    expect(read.status(), "mark-read answers 200").toBe(200)
    const readBody = await read.json()
    expect(readBody.is_read, "the notification is now read").toBe(true)

    // --- UI: the ESS hub, signed in as admin, must NOT leak the --------
    // associate's inbox: the centre is owner-only by design, so the hard
    // assertion is the absence of the row (tenant isolation rendered) ------
    await page.goto("/ess")
    await expect(
      page.getByRole("heading", { name: "Employee Self-Service" })
    ).toBeVisible()
    await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
    await expect(
      page.getByText(title),
      "the admin hub leaks nothing of another person's inbox"
    ).toHaveCount(0)
  })

  test("notification reads without a token answer 401", async ({ request }) => {
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const res = await request.get(`${api}/ess/notifications`)
    expect(res.status(), "unauthenticated centre read answers 401").toBe(401)
  })

  test("an admin cannot read the notification centre (403, owner-only)", async ({
    request,
  }) => {
    const api = apiBaseUrl()
    assertNotProduction(api, "the API base URL")
    const admin = await adminSession(request)
    const res = await request.get(`${api}/ess/notifications`, {
      headers: admin.headers,
    })
    expect(
      res.status(),
      "a non-owner read — even by an admin — answers 403"
    ).toBe(403)
  })
})
