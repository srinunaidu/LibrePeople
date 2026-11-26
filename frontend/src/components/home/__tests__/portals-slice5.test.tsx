/* portals-completion slice 5 — SuperAdminHome + gates + rail (AC1+AC4+D1).
 *
 * No fake KPIs (D3); needs + admin quick links route via router. D1
 * FAIL-CLOSED: App.tsx admits HR to UserAdmin only (backend users CRUD
 * allows ADMIN_ROLES=(SuperAdmin,HR), impersonate is SuperAdmin-only) while
 * branding/entitlements (+ aliases) are SuperAdmin-only to match the
 * SuperAdmin-only settings/flags backend (client_onboarding.py). WorkspaceRail
 * admin list has <20 entries and no double aliases.
 */

import { readFileSync } from "fs"
import { join } from "path"
import { describe, expect, test, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom"
import SuperAdminHome from "../SuperAdminHome"

const authBox = vi.hoisted(() => ({ user: null as unknown }))

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: authBox.user as never }),
}))

const apiMocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>
  return { ...actual, default: { get: apiMocks.get, post: apiMocks.post, put: vi.fn(), delete: vi.fn(), patch: vi.fn() } }
})

function setRole(role: string) {
  authBox.user = { id: 1, username: "u", email: "u@x.test", role, is_active: true } as never
}

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="loc">{loc.pathname}</div>
}

function renderAt(path: string, ui: React.ReactElement) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      {ui}
      <Routes><Route path="*" element={<LocationProbe />} /></Routes>
    </MemoryRouter>
  )
}

const read = (p: string) => readFileSync(join(process.cwd(), p), "utf8")

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal("__BUILD__", { version: "test", commit: "testcommit", time: "2026-01-01T00:00:00Z" })
  authBox.user = { id: 1, username: "u", email: "u@x.test", role: "SuperAdmin", is_active: true } as never
  apiMocks.get.mockImplementation((url: string) => {
    if (url === "/onboarding-portal/clients") return Promise.resolve({ data: [{ id: 1, name: "Acme", slug: "acme", status: "active", primary_color: "#000" }] })
    if (url === "/reports/audit") return Promise.resolve({ data: [] })
    if (url === "/core-hr/cases") return Promise.resolve({ data: [{ id: 1, status: "Open" }] })
    if (url === "/requisitions/") return Promise.resolve({ data: [{ id: 2, status: "Open" }] })
    if (url === "/compliance/compliance-violations") return Promise.resolve({ data: [] })
    if (url === "/onboarding-portal/clients/1/integrations") return Promise.resolve({ data: [{ id: 1, name: "IdP", kind: "sso", status: "failed", has_secret: true }] })
    if (url === "/onboarding-portal/clients/1/feature-flags") return Promise.resolve({ data: [{ id: 1, key: "payroll", enabled: true }] })
    return Promise.resolve({ data: [] })
  })
})

describe("slice 5 — SuperAdminHome + gates + rail", () => {
  test("AC1: live values with hints, no fake trend text", async () => {
    setRole("SuperAdmin")
    render(<MemoryRouter><SuperAdminHome /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText("Tenants")).toBeInTheDocument())
    expect(screen.getByText("1 active")).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/vs last quarter|health score|resolution rate/)
    expect(screen.queryByLabelText(/Trend:/)).not.toBeInTheDocument()
  })

  test("AC4: needs + admin quick links route correctly", async () => {
    setRole("SuperAdmin")
    renderAt("/admin", <SuperAdminHome />)
    await waitFor(() => expect(screen.getByText("Administration")).toBeInTheDocument())
    fireEvent.click(screen.getByText("Module entitlements"))
    await waitFor(() => expect(screen.getByTestId("loc").textContent).toBe("/admin/entitlements"))
  })

  test("D1 fail-closed: App.tsx gates match the backend", () => {
    const app = read("src/App.tsx")
    // SuperAdmin-only backend (settings + feature-flags) → SuperAdmin-only routes.
    for (const p of ["/admin/branding", "/admin/entitlements", "/admin/module-entitlements", "/admin/tenant-branding"]) {
      const m = app.match(new RegExp(`path="${p}" element=\\{<ProtectedRoute roles=\\{\\[(.*?)\\]\\}>`))
      expect(m, p).not.toBeNull()
      expect(m![1]).toBe('"SuperAdmin"')
    }
    // Users CRUD backend allows ADMIN_ROLES (SuperAdmin, HR) → HR stays admitted.
    for (const p of ["/admin/users", "/admin/user-admin"]) {
      expect(app).toContain(`path="${p}" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}>`)
    }
  })

  test("AC4: WorkspaceRail admin list de-duplicated (<20, no double aliases)", () => {
    const src = read("src/components/shell/WorkspaceRail.tsx")
    const start = src.indexOf("const ADMIN_ITEMS")
    const block = src.slice(start, src.indexOf("\n]", start))
    const tos = [...block.matchAll(/to: "(\/admin\/[a-z0-9-]+)"/g)].map((m) => m[1])
    expect(tos.length).toBeGreaterThan(0)
    expect(tos.length).toBeLessThan(20)
    expect(new Set(tos).size).toBe(tos.length)
    for (const alias of ["user-admin", "tenant-branding", "module-entitlements", "workflow-approval", "integration-credentials", "backup-restore", "locale-config", "ad-03", "ad-09", "project-status", "design-gallery", "platform-showcase", "hr-01", "data-quality"]) {
      expect(tos.some((t) => t.includes(alias)), alias).toBe(false)
    }
  })

  test("AC4: ModuleEntitlements copy matches the SuperAdmin-only gate", () => {
    expect(read("src/pages/admin/ModuleEntitlements.tsx")).not.toContain("SuperAdmin / HR writable")
  })
})
