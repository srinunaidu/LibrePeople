import { expect, test, type Page } from "@playwright/test"

/**
 * The audit screen can check the chain (FD-13, PS-12).
 *
 * The defect this guards against
 * ------------------------------
 * `PS-04` made the audit trail tamper-evident: every entry carries the hash
 * of the one before it, so an edited row breaks the link at that row and a
 * removed row breaks it at the next. The contract declared
 * `GET /admin/audit/verify` and the server had **no such route**, so the
 * property existed and an operator could only see it with a shell. `PS-12`
 * served the operation; this journey is the screen.
 *
 * What is asserted, and why the answers are stubbed
 * -------------------------------------------------
 * The chain of the local e2e database is honest, so a real call can only
 * prove the intact wording. The broken and failed answers are stubbed: the
 * stub is the *input* to the screen, and what is asserted is the screen's
 * answer. `backend/admin_audit_test_suite.py` proves the operation those
 * stubs imitate, so the screen is not asserting a shape nobody serves.
 */

const ADMIN_USERNAME = "admin"
const ADMIN_PASSWORD = "E2e!Bootstrap#2026"

async function signIn(page: Page) {
  await page.goto("/login")
  await page.locator("#login-username").fill(ADMIN_USERNAME)
  await page.locator("#login-password").fill(ADMIN_PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 })
}

const HEAD = "9f2c1d7a4b6e8f0a2c4e6f8a0b1d3f5a7c9e1b3d5f7a9c1e3b5d7f9a1c3e5b7d"

function verification(overrides: Record<string, unknown> = {}) {
  return {
    verified: true,
    checked_entries: 1234,
    head: HEAD,
    head_id: 1234,
    first_broken: null,
    verified_at: "2026-10-27T04:15:00+00:00",
    ...overrides,
  }
}

test.describe("audit chain verification", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  test("the check is an action, and an intact chain says so with its head", async ({ page }) => {
    await page.route("**/api/v1/admin/audit/verify", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(verification()),
      })
    )

    // Count the calls the page makes on its own, before the button exists in
    // the operator's hands. A walk of the whole log on every visit is a cost
    // nobody asked for, and a stored verdict would be a claim the screen
    // cannot support.
    let calls = 0
    page.on("request", (request) => {
      if (request.url().includes("/admin/audit/verify")) calls += 1
    })

    await page.goto("/reports")
    await expect(page.getByRole("heading", { name: "Audit trail" })).toBeVisible()
    await expect(page.getByRole("table", { name: /audit trail of the 25 most recent/i })).toBeVisible()
    expect(calls, "the page checked the chain without being asked").toBe(0)
    await expect(page.getByText(/Run the check to see whether it still holds/i)).toBeVisible()

    await page.getByRole("button", { name: "Verify the chain" }).click()

    const verdict = page.getByRole("status").filter({ hasText: "The chain is intact" })
    await expect(verdict).toBeVisible()
    await expect(verdict).toContainText("1234 entries verified")
    await expect(verdict).toContainText(HEAD)
    await expect(verdict).toContainText(/Record this entry count and head hash outside the database/i)
    expect(calls, "the button did not make the request").toBe(1)
  })

  test("a broken chain names the entry and does not use a success tone", async ({ page }) => {
    await page.route("**/api/v1/admin/audit/verify", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          verification({
            verified: false,
            checked_entries: 7,
            first_broken: { id: "42", index: 7, reason: "hash_mismatch" },
          })
        ),
      })
    )

    await page.goto("/reports")
    await page.getByRole("button", { name: "Verify the chain" }).click()

    const broken = page.getByRole("alert").filter({ hasText: "The chain is broken" })
    await expect(broken).toBeVisible()
    await expect(broken).toContainText("Entry #42 was edited after it was written.")
    await expect(broken).toContainText("7 entries verified before the break")
    await expect(broken).toContainText(/does not repair the chain/i)
    await expect(broken).toContainText(HEAD)

    // Not a green pill, and not the intact sentence.
    await expect(page.getByText("The chain is intact")).toHaveCount(0)
    await expect(page.locator(".alert-success")).toHaveCount(0)
  })

  test("each way a chain can break has its own plain-language answer", async ({ page }) => {
    // Two different breaks, answered in turn. The wording is the screen's,
    // keyed on the server's stable reason code.
    const answers = [
      {
        body: verification({
          verified: false,
          checked_entries: 2,
          first_broken: { id: null, index: 2, reason: "head_mismatch" },
        }),
        expected: /entries were removed from the end, or the head was rewritten/i,
      },
      {
        body: verification({
          verified: false,
          checked_entries: 2,
          first_broken: { id: "9", index: 2, reason: "missing_predecessor" },
        }),
        expected: /Entry #9 does not follow the entry before it — a row was inserted, removed or reordered/i,
      },
    ]
    let call = 0
    await page.route("**/api/v1/admin/audit/verify", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(answers[Math.min(call++, answers.length - 1)].body),
      })
    )

    await page.goto("/reports")
    for (const answer of answers) {
      await page.getByRole("button", { name: "Verify the chain" }).click()
      await expect(page.getByRole("alert").filter({ hasText: "The chain is broken" })).toContainText(
        answer.expected
      )
    }
  })

  test("a failed request is an error, not an intact chain and not an empty one", async ({ page }) => {
    await page.route("**/api/v1/admin/audit/verify", (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "dependency_unavailable",
            category: "infrastructure",
            message: "The database is temporarily unavailable.",
            retryable: true,
          },
        }),
      })
    )

    await page.goto("/reports")
    await page.getByRole("button", { name: "Verify the chain" }).click()

    const failure = page.getByRole("alert").filter({ hasText: "The chain could not be verified" })
    await expect(failure).toBeVisible()
    await expect(failure).toContainText(/Nothing is claimed about the chain until a check succeeds/i)
    await expect(page.getByText("The chain is intact")).toHaveCount(0)
    await expect(page.getByText(/0 entries verified/)).toHaveCount(0)
  })
})
