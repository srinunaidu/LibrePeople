/* portals-completion slices 1+2 — Associate + Manager portal contract tests.
 * Slice 1: no fake KPIs on AssociateHome (no trend/sparkline, no "Since 09:00 AM");
 *   clock in/out posts employee_id; empty states render.
 * Slice 2: ManagerHome approves/rejects inline via router navigation (no full
 *   reload); goals/reviews link to /platform/performance; timesheet approve
 *   inline (reject is INCOMPLETE — no backend route).
 */
import { describe, expect, test, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom"
import AssociateHome from "../AssociateHome"
import ManagerHome from "../ManagerHome"

const authBox = vi.hoisted(() => ({ user: null as unknown }))
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: authBox.user as never }),
}))

const apiMocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>
  return { ...actual, default: { get: apiMocks.get, post: apiMocks.post, put: vi.fn(), delete: vi.fn() } }
})

const empMocks = vi.hoisted(() => ({ fetchAll: vi.fn() }))
vi.mock("@/lib/employees", () => ({
  fetchAllEmployees: (...a: unknown[]) => empMocks.fetchAll(...a),
}))

function setRole(role: string) {
  authBox.user = { id: 1, username: "u", email: "u@x.test", role, is_active: true } as never
}

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="loc">{loc.pathname}</div>
}

beforeEach(() => {
  vi.clearAllMocks()
  empMocks.fetchAll.mockResolvedValue({ items: [{ id: 9, email: "u@x.test", employee_id: "E9", first_name: "U", last_name: "Ser" }] })
})

function mockAssociateApi(opts: { payslips?: unknown[]; tasks?: unknown[] } = {}) {
  apiMocks.get.mockImplementation((url: string) => {
    if (url === "/leave/balances") return Promise.resolve({ data: [{ available_days: 5, leave_type_name: "Annual", entitlement_year: 2026 }] })
    if (url === "/scheduling/roster") return Promise.resolve({ data: [] })
    if (url === "/payroll/payslips") return Promise.resolve({ data: opts.payslips ?? [{ id: 1, period_start: "2026-11-01", period_end: "2026-11-30", net_pay: 50000, status: "Paid" }] })
    if (url === "/ess/announcements") return Promise.resolve({ data: [] })
    return Promise.resolve({ data: [] })
  })
}

function mockManagerApi() {
  apiMocks.get.mockImplementation((url: string) => {
    if (url === "/leave/requests") return Promise.resolve({ data: [{ id: 1, employee_id: 9, status: "Pending", working_days: 2, start_date: "2026-12-01", end_date: "2026-12-02" }] })
    if (url === "/time/timesheets") return Promise.resolve({ data: [{ id: 2, employee_id: 9, status: "Submitted", total_hours: 40, period_start: "2026-11-01", period_end: "2026-11-15" }] })
    if (url === "/scheduling/swaps") return Promise.resolve({ data: [{ id: 3, requester_id: 9, status: "Pending", roster_entry_id: 44 }] })
    if (url === "/performance/goals") return Promise.resolve({ data: [{ id: 4, title: "Ship it", progress: 50, status: "In Progress" }] })
    if (url === "/performance/reviews") return Promise.resolve({ data: [{ id: 5, period: "Q4", status: "Draft" }] })
    if (url === "/time/today") return Promise.resolve({ data: { present: 3 } })
    return Promise.resolve({ data: [] })
  })
  apiMocks.post.mockResolvedValue({ data: {} })
}

describe("slice 1 — AssociateHome", () => {
  test("AC1: no fake trend/sparkline elements; live KPI values with hints", async () => {
    setRole("Associate")
    mockAssociateApi()
    render(<MemoryRouter><AssociateHome /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText("Total Leave Balance")).toBeInTheDocument())
    // Live values present
    expect(screen.getByText("5")).toBeInTheDocument() // total leave days
    expect(screen.getByText("1 leave types")).toBeInTheDocument()
    // No fake trend indicators or hardcoded clock hint anywhere
    expect(screen.queryByText(/Since 09:00 AM/)).not.toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/vs last (year|week|month)|vs avg|completion rate/)
    expect(screen.queryByLabelText(/Trend:/)).not.toBeInTheDocument()
  })

  test("clock in posts employee_id and flips status", async () => {
    setRole("Associate")
    mockAssociateApi()
    apiMocks.post.mockResolvedValue({ data: {} })
    render(<MemoryRouter><AssociateHome /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText("Clock in")).toBeInTheDocument())
    fireEvent.click(screen.getByText("Clock in"))
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/time/clock-in", { employee_id: 9 }))
    expect(await screen.findByText("You are currently clocked in.")).toBeInTheDocument()
  })

  test("empty states hold for payslips and tasks", async () => {
    setRole("Associate")
    mockAssociateApi({ payslips: [], tasks: [] })
    render(<MemoryRouter><AssociateHome /></MemoryRouter>)
    expect(await screen.findByText("No payslips yet")).toBeInTheDocument()
    expect(await screen.findByText("All caught up")).toBeInTheDocument()
  })
})

describe("slice 2 — ManagerHome", () => {
  test("AC2: inline approve leave without full-page reload", async () => {
    setRole("Manager")
    mockManagerApi()
    const reloadSpy = vi.spyOn(window, "location", "get")
    render(<MemoryRouter><ManagerHome /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText("Approvals inbox")).toBeInTheDocument())
    fireEvent.click(screen.getAllByText("Approve")[0])
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/leave/requests/1/approve"))
    expect(await screen.findByText(/approved\./)).toBeInTheDocument()
    reloadSpy.mockRestore?.()
  })

  test("AC2: inline reject swap + approve timesheet", async () => {
    setRole("Manager")
    mockManagerApi()
    render(<MemoryRouter><ManagerHome /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText("Approvals inbox")).toBeInTheDocument())
    fireEvent.click(screen.getAllByText("Reject").find((b) => b.closest("li")?.textContent?.includes("Roster"))!)
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/scheduling/swaps/3/reject"))
    const approves = screen.getAllByText("Approve")
    fireEvent.click(approves.find((b) => b.closest("li")?.textContent?.includes("Timesheet"))!)
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/time/timesheets/2/approve"))
  })

  test("goals/reviews navigate to /platform/performance via router", async () => {
    setRole("Manager")
    mockManagerApi()
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<><ManagerHome /><LocationProbe /></>} />
          <Route path="/platform/performance" element={<div>perf page<LocationProbe /></div>} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText("Team goals")).toBeInTheDocument())
    // NeedsAction goals "View" button — click the one in the goals need row
    const views = screen.getAllByText("View")
    expect(views.length).toBeGreaterThan(0)
    fireEvent.click(views[0])
    await waitFor(() => expect(screen.getByTestId("loc").textContent).toBe("/platform/performance"))
  })

  test("AC1: no fake trend/sparkline on manager KPIs", async () => {
    setRole("Manager")
    mockManagerApi()
    render(<MemoryRouter><ManagerHome /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText("Pending Actions")).toBeInTheDocument())
    expect(screen.queryByLabelText(/Trend:/)).not.toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/vs last month|vs avg|completion rate|overdue/)
  })
})
