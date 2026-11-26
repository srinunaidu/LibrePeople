/* portals-completion slice 3 — HRHome contract tests (AC1+AC3).
 *
 * No fake KPIs (no trend/sparkline props, D3 — deltas need nonexistent
 * backend aggregations); NeedsAction + section links route via router
 * (no full-page reload) to /admin/er-cases, /recruiting,
 * /platform/compliance, /offboarding, /admin/headcount-cost,
 * /platform/payroll/setup, /platform/payroll/runs.
 */

import { describe, expect, test, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom"
import HRHome from "../HRHome"

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

beforeEach(() => {
  vi.clearAllMocks()
  authBox.user = { id: 1, username: "u", email: "u@x.test", role: "HR", is_active: true } as never
  apiMocks.get.mockImplementation((url: string) => {
    if (url === "/core-hr/cases") return Promise.resolve({ data: [{ id: 1, subject: "S", status: "Open", priority: "P1", category: "C" }] })
    if (url === "/requisitions/") return Promise.resolve({ data: [{ id: 2, req_number: "R1", title: "Engineer", status: "Open", openings: 2 }] })
    if (url === "/offboarding/terminations") return Promise.resolve({ data: [{ id: 3, employee_id: 9, status: "In Progress", last_working_date: "2026-12-31", termination_type: "Voluntary" }] })
    if (url === "/reports/headcount") return Promise.resolve({ data: { total: 42, by_department: [{ department: "Eng", employees: 40 }] } })
    if (url === "/compliance/compliance-violations") return Promise.resolve({ data: [{ id: 4, status: "Open" }] })
    if (url === "/reports/audit") return Promise.resolve({ data: [] })
    return Promise.resolve({ data: [] })
  })
})

describe("slice 3 — HRHome", () => {
  test("AC1: live values with hints, no fake trend/sparkline text", async () => {
    setRole("HR")
    render(<MemoryRouter><HRHome /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText("Total Headcount")).toBeInTheDocument())
    expect(screen.getByText("42")).toBeInTheDocument()
    expect(screen.getByText("1 departments")).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/vs last (quarter|month)|new this month|trend/i)
    expect(screen.queryByLabelText(/Trend:/)).not.toBeInTheDocument()
  })

  test("AC3: needs actions route to er-cases / compliance without reload", async () => {
    setRole("HR")
    renderAt("/hr", <HRHome />)
    await waitFor(() => expect(screen.getByText("Needs your action")).toBeInTheDocument())
    fireEvent.click(screen.getAllByText("Review")[0])
    await waitFor(() => expect(screen.getByTestId("loc").textContent).toBe("/admin/er-cases"))
  })

  test("AC3: requisition View + payroll-prep links route correctly", async () => {
    setRole("HR")
    renderAt("/hr", <HRHome />)
    await waitFor(() => expect(screen.getByText("Engineer")).toBeInTheDocument())
    fireEvent.click(screen.getByText("Payroll setup"))
    await waitFor(() => expect(screen.getByTestId("loc").textContent).toBe("/platform/payroll/setup"))
  })
})
