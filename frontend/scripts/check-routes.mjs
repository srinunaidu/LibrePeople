/**
 * Route integrity check.
 *
 * Scans the frontend source for internal navigation targets and verifies that
 * every one of them is a route actually registered in App.tsx. This catches the
 * silent-redirect class of bug (a <Link> to an unregistered path hits the `*`
 * catch-all and drops the user on the homepage with no error).
 *
 * Run with: npm run check:routes
 */
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"

const SRC = new URL("../src/", import.meta.url).pathname
const APP = join(SRC, "App.tsx")

/** Routes registered as <Route path="..."> in App.tsx, minus the catch-all. */
function registeredRoutes() {
  const source = readFileSync(APP, "utf8")
  const routes = new Set()
  const re = /<Route\s+path="([^"]+)"/g
  let m
  while ((m = re.exec(source))) {
    if (m[1] !== "*") routes.add(m[1])
  }
  return routes
}

/** Turn a route pattern into a regex ("/compare/:competitor" → ^/compare/([^/]+)$). */
function patternToRegExp(pattern) {
  const source = pattern.replace(/:([A-Za-z0-9_]+)/g, (_m, key) => `(?<${key}>[^/]+)`)
  return new RegExp(`^${source}$`)
}

function matchesRoute(pattern, target) {
  const re = patternToRegExp(pattern)
  const clean = target.split("#")[0].split("?")[0]
  const m = re.exec(clean)
  if (!m) return false
  // Static segments must line up positionally with static segments.
  const pSegs = pattern.split("/").filter(Boolean)
  const tSegs = clean.split("/").filter(Boolean)
  if (pSegs.length !== tSegs.length) return false
  for (let i = 0; i < pSegs.length; i++) {
    const p = pSegs[i]
    if (p.startsWith(":")) continue
    if (p !== tSegs[i]) return false
  }
  return true
}

/** Every source file that can contain a <Link to="...">. */
function sourceFiles(dir = SRC) {
  const out = []
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      out.push(...sourceFiles(full))
    } else if (/\.tsx?$/.test(entry)) {
      out.push(full)
    }
  }
  return out
}

const routes = registeredRoutes()
const problems = []

for (const file of sourceFiles()) {
  const source = readFileSync(file, "utf8")
  const rel = relative(SRC, file)

  // <Link to="/x">, navigate("/x"), href="/x"
  const re = /\b(?:to|href)=["'](\/[^"'#?]*)["']|\bnavigate\(\s*["'](\/[^"'#?]*)["']/g
  let m
  while ((m = re.exec(source))) {
    const target = m[1] ?? m[2]
    if (!target) continue
    // Template-literal / dynamic targets can't be checked statically.
    if (target.includes("${") || target.includes("{")) continue
    if (target === "/") continue // homepage is registered explicitly
    const ok = [...routes].some((p) => matchesRoute(p, target))
    if (!ok) {
      const line = source.slice(0, m.index).split("\n").length
      problems.push({ file: rel, line, target })
    }
  }

  // Navigation declared as an object property: { label: "People", to: "/x" }.
  // The workspace rail, the secondary sidebar, the command palette and the
  // mobile bar all use this form, and a wrong value there is exactly the
  // "clicking People goes somewhere unrelated" bug.
  const propRe = /\bto:\s*["'](\/[^"'#?]*)["']/g
  while ((m = propRe.exec(source))) {
    const target = m[1]
    if (target.includes("${") || target.includes("{")) continue
    if (target === "/") continue
    const ok = [...routes].some((p) => matchesRoute(p, target))
    if (!ok) {
      const line = source.slice(0, m.index).split("\n").length
      problems.push({ file: rel, line, target })
    }
  }

  // Full-page navigations: window.location.href = "/x"
  const hrefRe = /window\.location\.(?:href|assign)\s*=\s*["'](\/[^"'#?]*)["']/g
  while ((m = hrefRe.exec(source))) {
    const target = m[1]
    if (target.includes("${") || target.includes("{")) continue
    if (target === "/") continue
    const ok = [...routes].some((p) => matchesRoute(p, target))
    if (!ok) {
      const line = source.slice(0, m.index).split("\n").length
      problems.push({ file: rel, line, target })
    }
  }
}

// A marketing CTA that sends anonymous visitors to the login screen.
const LOGIN_MISDIRECTS = [
  "pages/Homepage.tsx",
  "pages/Solutions.tsx",
  "pages/Industries.tsx",
  "pages/Resources.tsx",
  "pages/About.tsx",
  "pages/Careers.tsx",
]
for (const f of LOGIN_MISDIRECTS) {
  try {
    const source = readFileSync(join(SRC, f), "utf8")
    source.split("\n").forEach((line, i) => {
      if (/to="\/login"/.test(line) && !/sign in|login/i.test(line)) {
        problems.push({
          file: f,
          line: i + 1,
          target: "/login (marketing link — use a public route instead)",
        })
      }
    })
  } catch {
    /* file may not exist */
  }
}

// A protected screen that does not render inside <Layout> has no navigation
// at all: no workspace rail, no secondary sidebar, no way back. The user
// sees that as "clicking the link does nothing".
const PUBLIC_PAGES = new Set([
  "About.tsx",
  "Careers.tsx",
  "ChangePassword.tsx",
  "Contact.tsx",
  "Dashboard.tsx", // renders a role home component, each of which has the shell
  "Documentation.tsx",
  "Homepage.tsx",
  "Industries.tsx",
  "Login.tsx",
  "NotFound.tsx",
  "Privacy.tsx",
  "Resources.tsx",
  "Solutions.tsx",
  "Terms.tsx",
])

const PAGES_DIR = join(SRC, "pages")
for (const entry of readdirSync(PAGES_DIR)) {
  if (!entry.endsWith(".tsx")) continue
  if (entry.endsWith(".test.tsx") || entry.endsWith(".spec.tsx")) continue
  if (PUBLIC_PAGES.has(entry)) continue
  const source = readFileSync(join(PAGES_DIR, entry), "utf8")
  if (!/from\s+["']@\/components\/Layout["']/.test(source)) {
    problems.push({
      file: `pages/${entry}`,
      line: 1,
      target: "this protected page does not render inside <Layout>",
    })
  }
}

// Full-page reloads inside the app chrome lose SPA state and, in a
// tenant workspace (/t/:slug/...), the tenant scope itself. The shell
// must navigate client-side with <Link> or navigate().
const SHELL_FILES = [
  "components/shell/WorkspaceRail.tsx",
  "components/shell/TopBar.tsx",
  "components/shell/MobileBar.tsx",
  "components/shell/SecondarySidebar.tsx",
  "components/Layout.tsx",
  "components/ui/mobile-bottom-nav.tsx",
]
for (const f of SHELL_FILES) {
  try {
    const source = readFileSync(join(SRC, f), "utf8")
    source.split("\n").forEach((line, i) => {
      if (/window\.location\.(?:href|assign)\s*=/.test(line)) {
        problems.push({
          file: f,
          line: i + 1,
          target:
            "full-page reload in the app shell — use <Link> or navigate() (a reload loses app state and the /t/:slug tenant scope)",
        })
      }
    })
  } catch {
    /* file may not exist */
  }
}

// Navigation completeness: every core area must be reachable from the
// persistent chrome (desktop rail or mobile drawer). A page that is
// registered but that no menu item reaches reads to the user as
// "the menu is missing" or "the link is a dummy".
const NAV_EXPECTED = [
  ["/dashboard", "Home"],
  ["/people", "People"],
  ["/time", "Time & Attendance"],
  ["/scheduling", "Scheduling"],
  ["/forecasting", "Forecast"],
  ["/leave", "Leave"],
  ["/recruiting", "Recruiting"],
  ["/platform/payroll", "Payroll"],
  ["/reports", "Reports"],
  ["/import", "Import / Export"],
  ["/client-onboarding", "Admin"],
]
for (const [path, label] of NAV_EXPECTED) {
  let inRail = false
  let inDrawer = false
  try {
    inRail = readFileSync(join(SRC, "components/shell/WorkspaceRail.tsx"), "utf8").includes(
      `to: "${path}"`,
    )
  } catch {
    /* rail must exist; dead-target checks above cover it */
  }
  try {
    inDrawer = readFileSync(join(SRC, "components/Layout.tsx"), "utf8").includes(
      `tenantNav.to("${path}")`,
    )
  } catch {
    /* layout must exist at this point */
  }
  if (!inRail && !inDrawer) {
    problems.push({
      file: "components/shell/WorkspaceRail.tsx",
      line: 0,
      target: `${path} (${label}) is a registered route that no persistent nav item reaches`,
    })
  }
}

if (problems.length) {
  console.error(`\n✗ ${problems.length} navigation problem(s) found:\n`)
  for (const p of problems) console.error(`  ${p.file}:${p.line}  →  ${p.target}`)
  console.error("\n")
  process.exit(1)
}

console.log(`✓ Route integrity OK — all internal links resolve to ${routes.size} registered routes.`)