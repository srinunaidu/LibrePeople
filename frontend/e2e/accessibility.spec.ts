import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page } from "@playwright/test"

/**
 * Accessibility journey (QA-04, X-14).
 *
 * The contrast journey proves the text is legible. It does not prove that a
 * form field has a name, that a button is a button, that a table has headers
 * or that a dialog traps focus — the semantics a screen reader depends on.
 * This journey runs axe-core against every page and fails on a violation of
 * WCAG 2.2 A or AA, naming the page, the rule and the nodes.
 *
 * The report of the first run is recorded in
 * `docs/validation/ACCESSIBILITY.md`. A violation is a defect report, not a
 * reason to relax the rule set.
 */

const ADMIN_USERNAME = "admin"
const ADMIN_PASSWORD = "E2e!Bootstrap#2026"

/** The rules the product claims: WCAG 2.2 levels A and AA. */
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]

/** Pages that need no session. */
const PUBLIC_PAGES = ["/login", "/"]

/** Pages that need a signed-in session. */
const AUTHENTICATED_PAGES = [
  "/dashboard",
  "/people",
  "/people/departments",
  "/people/jobs",
  "/people/locations",
  "/time",
  "/leave",
  "/recruiting",
  "/reports",
  "/client-onboarding",
  "/scheduling",
  "/offboarding",
  "/onboarding",
  "/platform",
  "/platform/payroll",
  "/platform/performance",
  "/platform/learning",
  "/platform/compliance",
  "/platform/integrations",
  "/import",
  "/jobs",
  "/mfa",
]

interface Violation {
  id: string
  impact?: string | null
  help: string
  nodes: { target: string[] }[]
}

/** The failure message: one block per rule, with the nodes it names. */
function describe(path: string, violations: Violation[]): string {
  const lines = violations.map((violation) => {
    const nodes = violation.nodes
      .slice(0, 5)
      .map((node) => `      ${node.target.join(" ")}`)
      .join("\n")
    const more =
      violation.nodes.length > 5
        ? `\n      … and ${violation.nodes.length - 5} more`
        : ""
    return `  ${violation.id} (${violation.impact ?? "unknown"}) — ${violation.help}\n${nodes}${more}`
  })
  return `${path}: ${violations.length} accessibility violation(s)\n${lines.join("\n")}`
}

async function scan(page: Page) {
  return new AxeBuilder({ page }).withTags(TAGS).analyze()
}

async function signIn(page: Page) {
  await page.goto("/login")
  await page.locator("#login-username").fill(ADMIN_USERNAME)
  await page.locator("#login-password").fill(ADMIN_PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 })
}

test.describe("accessibility — public pages", () => {
  for (const path of PUBLIC_PAGES) {
    test(`${path} has no WCAG 2.2 A/AA violation`, async ({ page }) => {
      await page.goto(path)
      await page.waitForLoadState("networkidle")
      const results = await scan(page)
      expect(results.violations, describe(path, results.violations)).toEqual([])
    })
  }
})

test.describe("accessibility — signed-in pages", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  for (const path of AUTHENTICATED_PAGES) {
    test(`${path} has no WCAG 2.2 A/AA violation`, async ({ page }) => {
      await page.goto(path)
      await page.waitForLoadState("networkidle")
      const results = await scan(page)
      expect(results.violations, describe(path, results.violations)).toEqual([])
    })
  }
})

test.describe("accessibility — create flows", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
  })

  /** Create a leave type via the inline form on /leave, then scan the result. */
  test("leave type create flow has no WCAG 2.2 critical/serious violation", async ({ page }) => {
    await page.goto("/leave")
    await page.waitForLoadState("networkidle")

    // The create form is inline on /leave for admin/HR roles. Fill it and submit.
    await page.locator("#lt-name").fill("QA Test Leave")
    await page.locator("#lt-code").fill("QA")
    await page.locator("#lt-days").fill("5")
    await page.getByRole("button", { name: /Add type/i }).click()
    await page.waitForLoadState("networkidle")

    const results = await scan(page)
    const criticalSerious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    )
    expect(criticalSerious, describe("/leave create flow", criticalSerious)).toEqual([])
  })
})

test.describe("the harness itself", () => {
  test("an image without a name is a violation", async ({ page }) => {
    // The negative test: if axe stops reporting, this fails rather than the
    // suite passing because nothing was measured.
    await page.goto("/login")
    await page.setContent(
      "<main><h1>Probe</h1><img src=\"data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7\"></main>",
    )
    const results = await scan(page)
    expect(results.violations.map((violation) => violation.id)).toContain(
      "image-alt",
    )
  })
})
