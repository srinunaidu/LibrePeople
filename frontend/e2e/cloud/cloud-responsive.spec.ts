import { expect, test, type APIRequestContext, type Page } from "@playwright/test"
import { completeMfaIfRequired } from "./totp"

/**
 * Cloud E2E: responsive sweep of the deployed frontend at 360 / 768 /
 * 1024 / 1440 px.
 *
 * Two logins total (one associate, one HR — the mandate budget); each test
 * signs in once, then loops widths with `setViewportSize` and visits every
 * page fresh at that viewport. The login page is swept without auth.
 *
 * Per width × page, asserted:
 * - no horizontal overflow (`max(body, documentElement).scrollWidth` within
 *   `innerWidth + 1px`; the failure message carries the px overflow);
 * - the nav pattern the code specifies (WorkspaceRail sidebar
 *   `hidden lg:flex` — visible only at >= 1024; TopBar drawer trigger
 *   `lg:hidden` "Open navigation" — visible only below 1024).
 *
 * At 360 px additionally: named primary actions are visible and enabled,
 * and a tap-target scan flags visible interactive elements whose boxes
 * overlap without containment (nested icons excluded), with selector +
 * px evidence. Geometry findings are recorded as defects with viewport +
 * px; product code is NOT touched by this task.
 *
 * Credentials come from the environment at RUNTIME ONLY. Missing variables
 * SKIP with the reason, never fail.
 */

const APP = (
  process.env.CLOUD_APP_URL ??
  "https://librepeople-frontend.onrender.com"
).replace(/\/+$/, "")
const API = (
  process.env.CLOUD_API_URL ??
  "https://librepeople-backend.onrender.com/api/v1"
).replace(/\/+$/, "")

const WIDTHS = [360, 768, 1024, 1440] as const

const ADMIN_USER = process.env.E2E_HRADMIN_USERNAME || "e2e_hradmin"
const EMPLOYEE_USER = process.env.E2E_EMPLOYEE_USERNAME || "e2e_employee"

function adminPassword(): string | null {
  return process.env.E2E_HRADMIN_PASSWORD ?? null
}
function employeePassword(): string | null {
  return process.env.E2E_EMPLOYEE_PASSWORD ?? null
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

interface WidthOverflow {
  width: number
  page: string
  scrollWidth: number
  innerWidth: number
}

async function checkNoOverflow(
  page: Page,
  pageName: string,
  width: number
): Promise<void> {
  await page.waitForLoadState("networkidle").catch(() => undefined)
  const dims = await page.evaluate(() => ({
    scrollWidth: Math.max(
      document.body.scrollWidth,
      document.documentElement.scrollWidth
    ),
    innerWidth: window.innerWidth,
  }))
  expect(
    dims.scrollWidth,
    `${pageName} @${width}px overflows by ${dims.scrollWidth - dims.innerWidth}px`
  ).toBeLessThanOrEqual(dims.innerWidth + 1)
}

/** The nav pattern the shell code specifies (WorkspaceRail + TopBar). */
async function checkNavPattern(
  page: Page,
  pageName: string,
  width: number
): Promise<void> {
  const wide = width >= 1024
  const sidebar = page.locator(".sidebar-obsidian").first()
  const drawerTrigger = page.getByRole("button", {
    name: "Open navigation",
  })
  if (wide) {
    await expect(
      sidebar,
      `${pageName} @${width}px: sidebar visible at lg+`
    ).toBeVisible({ timeout: 10_000 })
    await expect(
      drawerTrigger,
      `${pageName} @${width}px: drawer trigger hidden at lg+`
    ).toBeHidden({ timeout: 10_000 })
  } else {
    await expect(
      sidebar,
      `${pageName} @${width}px: sidebar hidden below lg`
    ).toBeHidden({ timeout: 10_000 })
    await expect(
      drawerTrigger,
      `${pageName} @${width}px: drawer trigger visible below lg`
    ).toBeVisible({ timeout: 10_000 })
  }
}

interface TapOverlap {
  page: string
  a: string
  b: string
  overlapPx: number
}

/** Visible interactive elements whose boxes overlap without containment.
 * Pairs involving `position: fixed` chrome (the mobile bottom nav) are
 * excluded by design: scrolled content passes beneath fixed chrome and
 * `main` reserves `pb-20` so every row scrolls clear — flagging those
 * would fail every scrollable page at 360px. */
async function scanTapTargets(page: Page, pageName: string): Promise<TapOverlap[]> {
  return page.evaluate((name) => {
    const inFixedChrome = (el: Element): boolean => {
      let node: Element | null = el
      while (node && node !== document.body) {
        if (getComputedStyle(node).position === "fixed") return true
        node = node.parentElement
      }
      return false
    }
    const label = (el: Element): string => {
      const aria = el.getAttribute("aria-label")
      if (aria) return aria
      const text = (el.textContent || "").trim().slice(0, 40)
      return `${el.tagName.toLowerCase()}${text ? ` "${text}"` : ""}`
    }
    const boxes = Array.from(
      document.querySelectorAll("button, a[href]")
    )
      .filter((el) => {
        if (el.closest("button, a[href]") !== el) return false // nested icon/link
        if (inFixedChrome(el)) return false // designed fixed chrome
        const rect = el.getBoundingClientRect()
        return rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < window.innerHeight
      })
      .map((el) => ({ label: label(el), box: el.getBoundingClientRect() }))
    const out: TapOverlap[] = []
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length; j++) {
        const A = boxes[i].box
        const B = boxes[j].box
        const contains =
          (A.left <= B.left && A.top <= B.top && A.right >= B.right && A.bottom >= B.bottom) ||
          (B.left <= A.left && B.top <= A.top && B.right >= A.right && B.bottom >= A.bottom)
        if (contains) continue
        const iw = Math.min(A.right, B.right) - Math.max(A.left, B.left)
        const ih = Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top)
        if (iw <= 0 || ih <= 0) continue
        const area = iw * ih
        const smaller =
          Math.min(A.width * A.height, B.width * B.height)
        if (smaller > 0 && area / smaller > 0.3) {
          out.push({
            page: name,
            a: boxes[i].label,
            b: boxes[j].label,
            overlapPx: Math.round(area),
          })
        }
      }
    }
    return out
  }, pageName)
}

test.describe("cloud responsive sweep", () => {
  test("login page has no overflow at any width", async ({ page }) => {
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 800 })
      await page.goto(`${APP}/login`)
      await expect(
        page.getByRole("button", { name: "Sign in" })
      ).toBeVisible({ timeout: 30_000 })
      await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
      await checkNoOverflow(page, "login", width)
    }
  })

  test("associate sweep: pages fit, nav collapses, primaries hold", async ({
    page,
    request,
  }) => {
    const password = employeePassword()
    test.skip(
      password === null,
      "E2E_EMPLOYEE_USERNAME/E2E_EMPLOYEE_PASSWORD unset — the provisioned cloud employee user is not available (see frontend/e2e/cloud/README.md)."
    )
    // Login #1 of the 2-login budget (associate is not MFA-enforced).
    await apiLogin(request, EMPLOYEE_USER, password!, null)
    await signIn(page, EMPLOYEE_USER, password!)
    const overlaps: TapOverlap[] = []

    const pages = [
      { path: "/dashboard", name: "associate dashboard" },
      { path: "/people", name: "people directory" },
      { path: "/leave", name: "leave" },
      { path: "/expenses", name: "expenses list" },
      { path: "/ess", name: "ESS hub" },
    ]
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 800 })
      for (const { path, name } of pages) {
        await page.goto(`${APP}${path}`)
        await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
        await checkNavPattern(page, name, width)
        await checkNoOverflow(page, name, width)
        if (width === 360) {
          overlaps.push(...(await scanTapTargets(page, name)))
        }
      }
      // 360 px spot-check: the associate's primary lane stays actionable.
      if (width === 360) {
        await page.goto(`${APP}/expenses`)
        const cta = page.getByRole("link", { name: "New claim" })
        await expect(cta, "New claim reachable at 360px").toBeVisible({
          timeout: 30_000,
        })
        await expect(cta, "New claim enabled at 360px").toBeEnabled()
      }
    }
    expect(
      overlaps,
      `tap-target overlaps at 360px: ${JSON.stringify(overlaps)}`
    ).toEqual([])
  })

  test("HR sweep: pages fit, nav collapses, primaries hold", async ({
    page,
    request,
  }) => {
    const password = adminPassword()
    test.skip(
      password === null,
      "E2E_HRADMIN_USERNAME/E2E_HRADMIN_PASSWORD unset — the provisioned cloud HR admin is not available (see frontend/e2e/cloud/README.md)."
    )
    // Login #2 of the 2-login budget.
    await apiLogin(
      request,
      ADMIN_USER,
      password!,
      process.env.E2E_HRADMIN_MFA_SECRET ?? null
    )
    await signIn(page, ADMIN_USER, password!)
    const overlaps: TapOverlap[] = []

    const pages = [
      { path: "/dashboard", name: "HR dashboard" },
      { path: "/people", name: "people directory" },
      { path: "/leave", name: "leave" },
      { path: "/expenses", name: "expenses list" },
      { path: "/ess", name: "ESS hub" },
    ]
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 800 })
      for (const { path, name } of pages) {
        await page.goto(`${APP}${path}`)
        await expect(page).not.toHaveURL(/\/$/, { timeout: 5_000 })
        await checkNavPattern(page, name, width)
        await checkNoOverflow(page, name, width)
        if (width === 360) {
          overlaps.push(...(await scanTapTargets(page, name)))
        }
      }
      // 360 px spot-checks: the HR lane's primary actions stay actionable.
      if (width === 360) {
        await page.goto(`${APP}/people`)
        const add = page.getByRole("button", { name: "Add employee" })
        await expect(add, "Add employee reachable at 360px").toBeVisible({
          timeout: 30_000,
        })
        await expect(add, "Add employee enabled at 360px").toBeEnabled()
        await page.goto(`${APP}/expenses`)
        const cta = page.getByRole("link", { name: "New claim" })
        await expect(cta, "New claim reachable at 360px").toBeVisible({
          timeout: 30_000,
        })
        await expect(cta, "New claim enabled at 360px").toBeEnabled()
      }
    }
    expect(
      overlaps,
      `tap-target overlaps at 360px: ${JSON.stringify(overlaps)}`
    ).toEqual([])
  })
})
