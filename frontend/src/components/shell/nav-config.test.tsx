/* Phase C — shell + navigation rebuild (contract: spec/features/shell-navigation).
 *
 * - every nav `to` exists in App.tsx (sections, subs, console, gotos, palette)
 * - no alias path appears in the palette, rail, drawer, gotos or help sheet
 * - rail↔routes parity: every canonical /admin/* route is listed exactly
 *   once in the named console groups, with the same role gate as App.tsx
 * - ShortcutHelp renders from the same GOTO registry the rail registers
 * - role tests render the rail per role per the AC2 mapping table
 */
import { readFileSync } from "fs"
import { join } from "path"
import { describe, expect, test, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, act } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import { MemoryRouter } from "react-router-dom"
import { WorkspaceRail } from "@/components/shell/WorkspaceRail"
import { ShortcutHelp } from "@/components/shell/ShortcutHelp"
import { Layout } from "@/components/Layout"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import {
  ADMIN_ALIASES,
  ADMIN_GROUPS,
  GOTO_ENTRIES,
  NAV_SECTIONS,
  allAdminTargets,
  bottomNavSections,
  breadcrumbFor,
  lensForRole,
  paletteItemsFor,
  sectionsForLens,
  visibleAdminGroups,
  visibleSections,
  type NavRole,
} from "@/lib/nav"

const authBox = vi.hoisted(() => ({ user: null as unknown }))

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: authBox.user,
    isAuthenticated: !!authBox.user,
    mustChangePassword: false,
  }),
}))

vi.mock("@/context/TenantContext", () => ({
  useTenant: () => ({
    tenant: {
      slug: "acme",
      name: "Acme",
      primary_color: "#2563EB",
      secondary_color: "#1F2937",
      timezone: "Asia/Kolkata",
      locale: "en-IN",
      currency: "INR",
      status: "Active",
    },
    loading: false,
    isMultiTenant: false,
    themeError: null,
  }),
}))

function setRole(role: string | null) {
  authBox.user = role
    ? ({ id: 1, username: "u", email: "u@x.test", role, is_active: true } as never)
    : (null as never)
}

const read = (p: string) => readFileSync(join(process.cwd(), p), "utf8")

/** Route paths registered as <Route path="..."> in App.tsx. */
function appRoutes(): string[] {
  const src = read("src/App.tsx")
  return [...src.matchAll(/<Route path="([^"]+)"/g)].map((m) => m[1])
}

/** Pattern-aware match ("/compare/:competitor" matches "/compare/acme"). */
function routeExists(routes: string[], target: string): boolean {
  const clean = target.split("#")[0].split("?")[0]
  return routes.some((pattern) => {
    if (pattern === "*") return false
    const re = new RegExp(
      `^${pattern.replace(/:[A-Za-z0-9_]+/g, "[^/]+")}$`
    )
    return re.test(clean)
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  setRole("SuperAdmin")
})

describe("nav targets all exist in App.tsx", () => {
  test("sections, subs, console, gotos and palette resolve to registered routes", () => {
    const routes = appRoutes()
    const targets = [
      ...NAV_SECTIONS.map((s) => s.to),
      ...NAV_SECTIONS.flatMap((s) => (s.sub ?? []).map((sub) => sub.to)),
      ...allAdminTargets(),
      ...GOTO_ENTRIES.map((g) => g.to),
      ...paletteItemsFor("SuperAdmin").map((i) => i.to),
      ...Object.values(ADMIN_ALIASES),
    ]
    expect(targets.length).toBeGreaterThan(100)
    for (const t of targets) expect(routeExists(routes, t), t).toBe(true)
  })
})

describe("aliases never surface in the nav", () => {
  const aliasPaths = Object.keys(ADMIN_ALIASES)

  test("no nav target is an alias path", () => {
    const linked = new Set([
      ...NAV_SECTIONS.map((s) => s.to),
      ...NAV_SECTIONS.flatMap((s) => (s.sub ?? []).map((sub) => sub.to)),
      ...allAdminTargets(),
      ...GOTO_ENTRIES.map((g) => g.to),
    ])
    for (const a of aliasPaths) expect(linked.has(a), a).toBe(false)
  })

  test("palette contains no alias for any role", () => {
    for (const role of ["SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer"]) {
      for (const item of paletteItemsFor(role)) {
        expect(aliasPaths.includes(item.to), `${role}: ${item.to}`).toBe(false)
      }
    }
  })

  test("alias values are all canonical registered routes", () => {
    const routes = appRoutes()
    for (const [alias, canonical] of Object.entries(ADMIN_ALIASES)) {
      expect(routeExists(routes, alias), alias).toBe(true)
      expect(routeExists(routes, canonical), canonical).toBe(true)
    }
  })
})

describe("rail↔routes parity", () => {
  test("console lists every canonical /admin/* route exactly once", () => {
    const adminRoutes = appRoutes().filter((p) => p.startsWith("/admin/"))
    const canonical = adminRoutes.filter((p) => !(p in ADMIN_ALIASES))
    const listed = allAdminTargets()
    expect(new Set(listed).size).toBe(listed.length)
    expect([...listed].sort()).toEqual([...canonical].sort())
  })

  test("console role gates match the App.tsx ProtectedRoute gates", () => {
    const src = read("src/App.tsx")
    const byPath = new Map<string, string[]>()
    for (const g of ADMIN_GROUPS) for (const i of g.items) byPath.set(i.to, i.roles)
    for (const [path, roles] of byPath) {
      const m = src.match(
        new RegExp(`path="${path.replace(/[./]/g, (c) => `\\${c}`)}" element=\\{<ProtectedRoute roles=\\{\\[(.*?)\\]\\}>`)
      )
      expect(m, path).not.toBeNull()
      expect(
        [...(m![1].matchAll(/"([^"]+)"/g))].map((x) => x[1]).sort(),
        path
      ).toEqual([...roles].sort())
    }
  })

  test("eight named groups, none empty, ~full coverage", () => {
    expect(ADMIN_GROUPS.map((g) => g.name)).toEqual([
      "Organization",
      "Talent",
      "Time & Scheduling",
      "Leave",
      "Pay & Benefits",
      "Performance & Learning",
      "Platform",
      "Compliance & Audit",
    ])
    for (const g of ADMIN_GROUPS) expect(g.items.length, g.name).toBeGreaterThan(0)
    expect(allAdminTargets().length).toBeGreaterThanOrEqual(90)
  })
})

describe("ShortcutHelp renders from the GOTO registry", () => {
  test("every registry entry appears as a g-letter row", () => {
    render(
      <MemoryRouter>
        <ShortcutHelp />
      </MemoryRouter>
    )
    act(() => {
      window.dispatchEvent(new CustomEvent("karmathy:open-shortcut-help"))
    })
    expect(screen.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeInTheDocument()
    const seen = new Set<string>()
    for (const entry of GOTO_ENTRIES) {
      expect(entry.gKey, entry.label).toBeTruthy()
      expect(seen.has(entry.gKey), `duplicate g-key ${entry.gKey}`).toBe(false)
      seen.add(entry.gKey)
      expect(screen.getByText(`g ${entry.gKey}`)).toBeInTheDocument()
      expect(screen.getByText(`Go to ${entry.label}`)).toBeInTheDocument()
    }
  })

  test("D4 g-letters are assigned as resolved", () => {
    const byLabel = new Map(GOTO_ENTRIES.map((e) => [e.label, e.gKey]))
    expect(byLabel.get("Org")).toBe("o")
    expect(byLabel.get("Comp")).toBe("c")
    expect(byLabel.get("Documents")).toBe("d")
    expect(byLabel.get("ER")).toBe("v")
    expect(byLabel.get("Helpdesk")).toBe("i")
    expect(byLabel.get("Workflows")).toBe("w")
  })
})

/* AC2 mapping table: section → canonical path + roles that may see it. */
const SECTION_ACCESS: { key: string; to: string; roles: NavRole[] }[] = [
  { key: "overview", to: "/dashboard", roles: ["SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer"] },
  { key: "people", to: "/people", roles: ["SuperAdmin", "HR", "Manager", "Associate"] },
  { key: "org", to: "/admin/org-chart", roles: ["SuperAdmin", "HR", "Manager", "Associate"] },
  { key: "recruit", to: "/recruiting", roles: ["SuperAdmin", "HR", "Manager"] },
  { key: "onboard", to: "/onboarding", roles: ["SuperAdmin", "HR", "Manager", "Associate"] },
  { key: "time", to: "/time", roles: ["SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer"] },
  { key: "leave", to: "/leave", roles: ["SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer"] },
  { key: "comp", to: "/platform/benefits", roles: ["SuperAdmin", "HR", "PayrollViewer"] },
  { key: "payroll", to: "/platform/payroll", roles: ["SuperAdmin", "HR", "PayrollViewer"] },
  { key: "expenses", to: "/expenses", roles: ["SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer"] },
  { key: "documents", to: "/admin/documents", roles: ["SuperAdmin", "HR", "Manager", "Associate"] },
  { key: "assets", to: "/assets", roles: ["SuperAdmin", "HR", "Manager", "Associate"] },
  { key: "er", to: "/admin/er-cases", roles: ["SuperAdmin", "HR", "Manager"] },
  { key: "performance", to: "/platform/performance", roles: ["SuperAdmin", "HR", "Manager", "Associate"] },
  { key: "learning", to: "/platform/learning", roles: ["SuperAdmin", "HR", "Manager", "Associate"] },
  { key: "helpdesk", to: "/admin/hrhelp-cases", roles: ["SuperAdmin", "HR", "Manager", "Associate"] },
  { key: "reports", to: "/reports", roles: ["SuperAdmin", "HR", "Manager", "PayrollViewer"] },
  { key: "workflows", to: "/admin/workflow", roles: ["SuperAdmin", "HR", "Manager"] },
  { key: "integrations", to: "/platform/integrations", roles: ["SuperAdmin", "HR", "Manager"] },
  { key: "admin", to: "/client-onboarding", roles: ["SuperAdmin", "HR"] },
]

const ALL_ROLES: NavRole[] = ["SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer"]

describe("AC2: rail per role per the mapping table", () => {
  test("nav config roles match the mapping table", () => {
    for (const row of SECTION_ACCESS) {
      const section = NAV_SECTIONS.find((s) => s.section === row.key)!
      expect(section, row.key).toBeTruthy()
      expect(section.to, row.key).toBe(row.to)
      expect([...section.roles].sort(), row.key).toEqual([...row.roles].sort())
    }
  })

  for (const role of ALL_ROLES) {
    test(`rail for ${role}: lands on its canonical paths, hides the rest`, () => {
      setRole(role)
      render(
        <MemoryRouter initialEntries={["/dashboard"]}>
          <WorkspaceRail />
        </MemoryRouter>
      )
      const hrefs = new Set(
        screen
          .getAllByRole("link")
          .map((a) => (a as HTMLAnchorElement).getAttribute("href") ?? "")
      )
      for (const row of SECTION_ACCESS) {
        if (row.roles.includes(role)) {
          expect(hrefs.has(row.to), `${role} should link ${row.to}`).toBe(true)
        } else {
          expect(hrefs.has(row.to), `${role} should hide ${row.to}`).toBe(false)
        }
      }
    })
  }

  test("admin console is grouped; roles see only their permitted items", () => {
    // PayrollViewer passes no console gate → no console at all.
    expect(visibleAdminGroups("PayrollViewer")).toEqual([])
    setRole("PayrollViewer")
    const pv = render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <WorkspaceRail />
      </MemoryRouter>
    )
    expect(pv.queryByText("Admin console")).toBeNull()
    pv.unmount()

    // Manager/Associate (D2): only the widened section-canonical links.
    const mgrTos = visibleAdminGroups("Manager").flatMap((g) => g.items.map((i) => i.to))
    expect(mgrTos.sort()).toEqual(
      ["/admin/org-chart", "/admin/documents", "/admin/er-cases", "/admin/hrhelp-cases", "/admin/workflow"].sort()
    )
    const ascTos = visibleAdminGroups("Associate").flatMap((g) => g.items.map((i) => i.to))
    expect(ascTos.sort()).toEqual(
      ["/admin/org-chart", "/admin/documents", "/admin/hrhelp-cases"].sort()
    )

    setRole("SuperAdmin")
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <WorkspaceRail />
      </MemoryRouter>
    )
    fireEvent.click(screen.getAllByText("Admin console")[0])
    for (const g of ADMIN_GROUPS) {
      // Group headers share names with sections (e.g. "Leave"); the
      // console copy must exist alongside the section link.
      expect(screen.getAllByText(g.name).length, g.name).toBeGreaterThanOrEqual(1)
    }
    // Console copy of a group adds a second "Leave" node next to the section.
    expect(screen.getAllByText("Leave").length).toBe(2)
  })

  test("403s otherwise: guarded canonicals refuse excluded roles", () => {
    // Spot-check the real gate: Associate is refused on ER cases, Manager passes.
    setRole("Associate")
    const denied = render(
      <MemoryRouter>
        <ProtectedRoute roles={["SuperAdmin", "HR", "Manager"]}>
          <span>secret</span>
        </ProtectedRoute>
      </MemoryRouter>
    )
    expect(denied.queryByText("secret")).toBeNull()
    expect(denied.getByText(/403 — Forbidden/)).toBeInTheDocument()
    denied.unmount()

    setRole("Manager")
    const allowed = render(
      <MemoryRouter>
        <ProtectedRoute roles={["SuperAdmin", "HR", "Manager"]}>
          <span>secret</span>
        </ProtectedRoute>
      </MemoryRouter>
    )
    expect(allowed.getByText("secret")).toBeInTheDocument()
    allowed.unmount()
  })
})

describe("D6 lenses are pure filters over the config", () => {
  test("lens membership matches the resolved lists", () => {
    const keys = (lens: Parameters<typeof sectionsForLens>[0]) =>
      sectionsForLens(lens).map((s) => s.section).sort()
    expect(keys("manager")).toEqual(
      ["assets", "documents", "er", "expenses", "helpdesk", "integrations", "leave", "learning", "onboard", "org", "overview", "people", "performance", "recruit", "reports", "time", "workflows"].sort()
    )
    expect(keys("employee")).toEqual(
      ["assets", "documents", "expenses", "helpdesk", "leave", "learning", "onboard", "org", "overview", "people", "performance", "time"].sort()
    )
    expect(keys("payroll")).toEqual(
      ["comp", "expenses", "leave", "overview", "payroll", "reports", "time"].sort()
    )
    expect(keys("admin")).toEqual(NAV_SECTIONS.map((s) => s.section).sort())
  })

  test("automatic lens per role agrees with role filtering", () => {
    expect(lensForRole("SuperAdmin")).toBe("admin")
    expect(lensForRole("HR")).toBe("admin")
    expect(lensForRole("Manager")).toBe("manager")
    expect(lensForRole("Associate")).toBe("employee")
    expect(lensForRole("PayrollViewer")).toBe("payroll")
    expect(lensForRole(null)).toBe("employee")
    for (const role of ALL_ROLES) {
      const byRole = visibleSections(role).map((s) => s.section).sort()
      const byLens = sectionsForLens(lensForRole(role)).map((s) => s.section).sort()
      expect(byRole, role).toEqual(byLens)
    }
  })
})

describe("responsive bottom bar + breadcrumbs", () => {
  test("Layout bottom bar: one bar, max 5 config-driven items", () => {
    setRole("Manager")
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Layout>
          <div>page</div>
        </Layout>
      </MemoryRouter>
    )
    const bar = screen.getByRole("navigation", { name: "Primary navigation" })
    const links = bar.querySelectorAll("a")
    expect(links.length).toBeLessThanOrEqual(5)
    expect(links.length).toBeGreaterThan(0)
    expect([...links].map((a) => a.getAttribute("href"))).toEqual([
      "/dashboard",
      "/people",
      "/time",
      "/leave",
      "/expenses",
    ])
  })

  test("Layout drawer renders the role's config sections", () => {
    setRole("Associate")
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Layout>
          <div>page</div>
        </Layout>
      </MemoryRouter>
    )
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }))
    const drawer = screen.getByRole("navigation", { name: "Mobile navigation" })
    expect(drawer.textContent).toContain("Onboard")
    expect(drawer.textContent).toContain("My Assets")
    expect(drawer.textContent).not.toContain("Payroll overview")
  })

  test("bottom bar: max 5 items, priority order, role-filtered", () => {
    const items = bottomNavSections("SuperAdmin").map((s) => s.to)
    expect(items).toEqual(["/dashboard", "/people", "/time", "/leave", "/expenses"])
    expect(bottomNavSections("PayrollViewer").map((s) => s.to)).toEqual([
      "/dashboard",
      "/time",
      "/leave",
      "/expenses",
      "/reports",
    ])
    for (const role of ALL_ROLES) {
      expect(bottomNavSections(role).length, role).toBeLessThanOrEqual(5)
    }
  })

  test("breadcrumbs extend to the new sections", () => {
    expect(breadcrumbFor("/dashboard")).toEqual([{ label: "Home", href: "/dashboard" }])
    expect(breadcrumbFor("/admin/org-chart").map((b) => b.label)).toEqual(["Home", "Org"])
    expect(breadcrumbFor("/leave/ledger").map((b) => b.label)).toEqual(["Home", "Leave", "Ledger & Reconciliation"])
    expect(breadcrumbFor("/leave/ledger/7").map((b) => b.label)).toEqual(["Home", "Leave", "Ledger & Reconciliation"])
    expect(breadcrumbFor("/admin/documents").map((b) => b.label)).toEqual(["Home", "Documents"])
    expect(breadcrumbFor("/admin/salary-revisions").map((b) => b.label)).toEqual([
      "Home",
      "Admin",
      "Pay & Benefits",
      "Salary Revisions",
    ])
    expect(breadcrumbFor("/platform/payroll/runs").map((b) => b.label)).toEqual(["Home", "Payroll", "Pay runs"])
    expect(breadcrumbFor("/recruiting").map((b) => b.label)).toEqual(["Home", "Recruit"])
    expect(breadcrumbFor("/platform/integrations").map((b) => b.label)).toEqual(["Home", "Integrations"])
  })
})
