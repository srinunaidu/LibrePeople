/* portals-completion slice 4 — PayrollHome contract tests (AC1+AC3).
 *
 * No fake KPIs (no trend/sparkline props, D3); no gross≈net×1.3 client-side
 * derivation — totals come from the runs/payslips endpoints only. Run rows
 * link to /platform/payroll/runs/:id; needs route to the runs list; the old
 * "Read-only … Platform module" banner is replaced by an accurate per-role
 * note (PayRunDetail already gates process/approve/finalize per role).
 */

import { describe, expect, test, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom"
import PayrollHome from "../PayrollHome"

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
  authBox.user = { id: 1, username: "u", email: "u@x.test", role: "PayrollViewer", is_active: true } as never
  apiMocks.get.mockImplementation((url: string) => {
    if (url === "/payroll/runs") return Promise.resolve({ data: [{ id: 7, status: "Draft", total_gross: 100000, total_net: 80000, headcount: 10 }] })
    if (url === "/payroll/payslips") return Promise.resolve({ data: [{ id: 1, employee_id: 9, net_pay: 80000, status: "Paid", period_start: "2026-11-01", period_end: "2026-11-30" }] })
    if (url === "/reports/labor-cost") return Promise.resolve({ data: { by_department: [{ department: "Eng", employees: 5, monthly_cost: 50000 }], monthly_payroll: 50000 } })
    return Promise.resolve({ data: [] })
  })
})

describe("slice 4 — PayrollHome", () => {
  test("AC1: live values, no gross derivation, no fake trends", async () => {
    setRole("PayrollViewer")
    render(<MemoryRouter><PayrollHome /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText("Total Pay Runs")).toBeInTheDocument())
    expect(screen.getByText("Across 1 payslip")).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/vs last (quarter|period)|payroll growth|Gross:/)
    expect(screen.queryByLabelText(/Trend:/)).not.toBeInTheDocument()
  })

  test("AC3: run row links to run detail; needs route to runs list", async () => {
    setRole("PayrollViewer")
    renderAt("/payroll", <PayrollHome />)
    await waitFor(() => expect(screen.getByText("#7")).toBeInTheDocument())
    expect(screen.getByText("#7").closest("a")?.getAttribute("href")).toContain("/platform/payroll/runs/7")
    fireEvent.click(screen.getByText("Open runs"))
    await waitFor(() => expect(screen.getByTestId("loc").textContent).toBe("/platform/payroll/runs"))
  })

  test("AC3: banner is accurate (no stale read-only claim), setup link works", async () => {
    setRole("PayrollViewer")
    renderAt("/payroll", <PayrollHome />)
    await waitFor(() => expect(screen.getByText("Pay runs")).toBeInTheDocument())
    expect(screen.queryByText("Read-only")).not.toBeInTheDocument()
    expect(screen.getByText(/PayrollViewer reads/)).toBeInTheDocument()
    // "Pay setup" also exists in the workspace rail — target this page's button.
    const setupBtn = screen.getAllByText("Pay setup").find((el) => el.tagName === "BUTTON")
    expect(setupBtn).toBeDefined()
    fireEvent.click(setupBtn!)
    await waitFor(() => expect(screen.getByTestId("loc").textContent).toBe("/platform/payroll/setup"))
    expect(screen.getByText("Open payroll overview")).toBeInTheDocument()
  })
})
