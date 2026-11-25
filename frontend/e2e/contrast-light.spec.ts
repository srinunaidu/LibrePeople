import { expect, test, type Page } from "@playwright/test"

/**
 * Contrast journey — light theme.
 *
 * Duplicates contrast.spec.ts but with setTheme('light') for both
 * PUBLIC_PAGES and AUTHENTICATED_PAGES and asserts same AA thresholds
 * (4.5:1 normal, 3:1 large). Catches regressions like fg-muted #64748b
 * on surface-sunken.
 */

const ADMIN_USERNAME = "admin"
const ADMIN_PASSWORD = "E2e!Bootstrap#2026"

/** Pages that need no session. */
const PUBLIC_PAGES = ["/login", "/change-password", "/"]

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

/** WCAG AA minimum for normal text. */
const AA_NORMAL_TEXT = 4.5
/** WCAG AA minimum for large text (18.66px bold or 24px regular). */
const AA_LARGE_TEXT = 3.0

const PARSE_COLOR = `
  const parse = (value) => {
    const m = String(value || '').match(/^rgba?\\(([^)]+)\\)$/);
    if (!m) return null;
    const parts = m[1].split(',').map((p) => parseFloat(p.trim()));
    return {
      rgb: [parts[0] || 0, parts[1] || 0, parts[2] || 0],
      alpha: parts.length > 3 ? parts[3] : 1,
    };
  };
  const luminance = (rgb) => {
    const f = (c) => {
      const s = c / 255;
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2]);
  };
`

async function allTextContrasts(page: Page): Promise<
  {
    ratio: number
    fontSize: number
    fontWeight: number
    color: string
    background: string
    text: string
  }[]
> {
  return page.evaluate((parser) => {
    const parse = eval(parser + "; parse")
    const luminance = eval(parser + "; luminance")

    const results: {
      ratio: number
      fontSize: number
      fontWeight: number
      color: string
      background: string
      text: string
    }[] = []

    const elements = Array.from(
      document.querySelectorAll<HTMLElement>(
        "h1, h2, h3, h4, h5, h6, p, span, a, label, li, td, th, button, code, kbd, legend, small, strong, em"
      )
    )

    for (const el of elements) {
      const text = (el.textContent || "").trim()
      if (!text) continue
      if (text.length > 120) continue
      const style = getComputedStyle(el)
      if (style.display === "none" || style.visibility === "hidden") continue
      if (Number(style.opacity) < 0.1) continue
      if (el.getAttribute("aria-hidden") === "true") continue
      if (el.closest(".sr-only")) continue
      const rect = el.getBoundingClientRect()
      if (rect.width <= 1 || rect.height <= 1) continue

      const rendersText = Array.from(el.childNodes).some(
        (node) => node.nodeType === 3 && (node.textContent || "").trim().length > 0
      )
      if (!rendersText) continue

      const color = parse(style.color)
      if (!color) continue

      // Form controls are NOT skipped: the application's buttons, inputs
      // and selects are custom-styled (`.btn`, `.input`, …) with an
      // author-specified opaque face, and skipping them measured the text
      // against the surface behind the control instead of the face the
      // reader sees — every white primary-button label failed 1:1 against
      // the page behind it. axe-core, the companion gate, measures the
      // rendered face; this walk matches it.
      let node: HTMLElement | null = el
      let bg = [255, 255, 255]
      while (node) {
        const nodeStyle = getComputedStyle(node)
        const c = parse(nodeStyle.backgroundColor)
        if (c && c.alpha > 0.95) {
          bg = c.rgb
          break
        }
        node = node.parentElement
      }

      const l1 = luminance(color.rgb)
      const l2 = luminance(bg)
      const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)

      results.push({
        ratio: Math.round(ratio * 100) / 100,
        fontSize: parseFloat(style.fontSize),
        fontWeight: parseInt(style.fontWeight, 10) || 400,
        color: style.color,
        background: `rgb(${bg.join(", ")})`,
        text: text.slice(0, 60),
      })
    }

    return results
  }, PARSE_COLOR)
}

async function setTheme(page: Page, theme: "light" | "dark") {
  await page.evaluate((t) => {
    document.documentElement.classList.toggle("dark", t === "dark")
    localStorage.setItem("karmathy_theme", t)
  }, theme)
}

test.describe("contrast-light", () => {
  test("the signed-in pages keep their text legible in light mode", async ({
    page,
  }) => {
    await page.goto("/login")
    await page.locator("#login-username").fill(ADMIN_USERNAME)
    await page.locator("#login-password").fill(ADMIN_PASSWORD)
    await page.getByRole("button", { name: "Sign in" }).click()
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 })

    const failures: string[] = []

    for (const path of AUTHENTICATED_PAGES) {
      await page.goto(path)
      await page.waitForLoadState("networkidle").catch(() => undefined)
      await setTheme(page, "light")

      for (const measured of await allTextContrasts(page)) {
        const isLarge =
          measured.fontSize >= 24 ||
          (measured.fontSize >= 18.66 && measured.fontWeight >= 700)
        const required = isLarge ? AA_LARGE_TEXT : AA_NORMAL_TEXT
        if (measured.ratio < required) {
          failures.push(
            `${path} "${measured.text}": ${measured.ratio}:1 (needs ${required}:1) ` +
              `color=${measured.color} background=${measured.background} ` +
              `size=${measured.fontSize}px weight=${measured.fontWeight}`
          )
        }
      }
    }

    expect(failures, failures.join("\n")).toEqual([])
  })

  test("the public pages keep their text legible in light mode", async ({
    page,
  }) => {
    const failures: string[] = []

    for (const path of PUBLIC_PAGES) {
      await page.goto(path)
      await page.waitForLoadState("networkidle").catch(() => undefined)
      await setTheme(page, "light")

      for (const measured of await allTextContrasts(page)) {
        const isLarge =
          measured.fontSize >= 24 ||
          (measured.fontSize >= 18.66 && measured.fontWeight >= 700)
        const required = isLarge ? AA_LARGE_TEXT : AA_NORMAL_TEXT
        if (measured.ratio < required) {
          failures.push(
            `${path} "${measured.text}": ${measured.ratio}:1 (needs ${required}:1) ` +
              `color=${measured.color} background=${measured.background}`
          )
        }
      }
    }

    expect(failures, failures.join("\n")).toEqual([])
  })
})
