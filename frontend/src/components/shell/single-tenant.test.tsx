/* Single-tenant slice — AC-1 legacy redirect + AC-2 switcher absence.
 *
 * AC-1: /t/:slug/* redirects to the bare path (slug dropped, remainder and
 * query preserved). AC-2: the workspace switcher renders nowhere in the
 * shell; the admin console and brand header stay.
 */
import { describe, expect, test, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom"
import { TenantRedirect } from "@/App"
import { WorkspaceRail } from "@/components/shell/WorkspaceRail"
import {
  ADMIN_ALIASES,
  ADMIN_GROUPS,
  GOTO_ENTRIES,
  NAV_SECTIONS,
  allAdminTargets,
  paletteItemsFor,
} from "@/lib/nav"

const authBox = vi.hoisted(() => ({ user: { id: 1, username: "u", role: "SuperAdmin" } as { role: string } }))

function setRole(role: string) {
  authBox.user = { id: 1, username: "u", role } as { role: string }
}

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

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: authBox.user }),
}))

function LocationProbe() {
  const { pathname, search } = useLocation()
  return <div data-testid="loc">{`${pathname}${search}`}</div>
}

function renderRedirectAt(initial: string) {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route path="/t/:slug/*" element={<TenantRedirect />} />
        <Route path="*" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>
  )
}

describe("AC-1 legacy /t/:slug redirect", () => {
  test("drops the slug and lands on the bare sub-route", async () => {
    renderRedirectAt("/t/acme/leave")
    await waitFor(() => {
      expect(screen.getByTestId("loc").textContent).toBe("/leave")
    })
  })

  test("preserves nested remainder and query string", async () => {
    renderRedirectAt("/t/acme/leave/ledger?page=2")
    await waitFor(() => {
      expect(screen.getByTestId("loc").textContent).toBe("/leave/ledger?page=2")
    })
  })

  test("bare root maps to /", async () => {
    renderRedirectAt("/t/acme")
    await waitFor(() => {
      expect(screen.getByTestId("loc").textContent).toBe("/")
    })
  })
})

describe("AC-2 workspace switcher absent", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setRole("SuperAdmin")
  })

  test("the rail renders no switcher control or workspace menu", () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <WorkspaceRail />
      </MemoryRouter>
    )
    // The removed TenantSwitcher exposed a "Switch workspace" button and a
    // "Workspaces" menu; neither may exist anymore.
    expect(screen.queryByLabelText(/switch workspace/i)).toBeNull()
    expect(screen.queryByRole("menu", { name: /workspace/i })).toBeNull()
    expect(screen.queryByText(/no tenant scope/i)).toBeNull()
    // No link may point back into a /t/:slug workspace.
    for (const a of screen.getAllByRole("link")) {
      expect((a as HTMLAnchorElement).getAttribute("href") ?? "").not.toMatch(/^\/t\//)
    }
    // The shell itself still renders: brand + admin console entry point.
    expect(screen.getByText("Acme")).toBeTruthy()
    expect(screen.getByText("Admin console")).toBeTruthy()
  })
})

describe("AC-1b Phase C: no /t/ targets anywhere in the nav", () => {
  beforeEach(() => {
    setRole("SuperAdmin")
  })

  test("nav config points at bare paths only (sections, subs, console, palette, gotos)", () => {
    const targets = [
      ...NAV_SECTIONS.map((s) => s.to),
      ...NAV_SECTIONS.flatMap((s) => (s.sub ?? []).map((sub) => sub.to)),
      ...allAdminTargets(),
      ...paletteItemsFor("SuperAdmin").map((i) => i.to),
      ...GOTO_ENTRIES.map((g) => g.to),
      ...Object.values(ADMIN_ALIASES),
    ]
    expect(targets.length).toBeGreaterThan(100)
    for (const t of targets) expect(t, t).not.toMatch(/^\/t\//)
  })

  test("alias table covers legacy paths but is never linked from the nav", () => {
    const aliasPaths = Object.keys(ADMIN_ALIASES)
    expect(aliasPaths.length).toBeGreaterThan(20)
    const linked = new Set([
      ...NAV_SECTIONS.map((s) => s.to),
      ...NAV_SECTIONS.flatMap((s) => (s.sub ?? []).map((sub) => sub.to)),
      ...allAdminTargets(),
    ])
    for (const a of aliasPaths) expect(linked.has(a), a).toBe(false)
  })

  test("the rail renders no /t/ link for a restricted role either", () => {
    setRole("Associate")
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <WorkspaceRail />
      </MemoryRouter>
    )
    for (const a of screen.getAllByRole("link")) {
      expect((a as HTMLAnchorElement).getAttribute("href") ?? "").not.toMatch(/^\/t\//)
    }
  })

  test("admin group names are the contract's eight (never a flat list)", () => {
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
  })
})
