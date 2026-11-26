/* LP-EXP-001/002/003 — expenses UI contract tests (18, api mocked).
 * Each acceptance criterion in spec/features/expenses-ui/contract.md §2 maps
 * to at least one test below; the backend is untouched and mocked out.
 */
import { describe, expect, test, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import { MemoryRouter, Routes, Route } from "react-router-dom"
import Expenses from "../Expenses"
import ExpenseDetail from "../ExpenseDetail"
import ExpenseNew from "../ExpenseNew"

const authBox = vi.hoisted(() => ({ user: null as unknown }))
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: authBox.user as never }),
}))

const apiMocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>
  return { ...actual, default: { get: apiMocks.get, post: apiMocks.post } }
})

function setRole(role: string) {
  authBox.user = { id: 1, username: "u", email: "u@x.test", role, is_active: true } as never
}

function claim(over: Record<string, unknown> = {}) {
  return {
    id: 7,
    employee_id: 12,
    category_id: 3,
    expense_date: "2026-11-20",
    amount: 2500,
    currency: "INR",
    description: "Taxi",
    status: "DRAFT",
    payment_status: "UNPAID",
    rejection_reason: null,
    ...over,
  }
}

function err(status: number, detail: unknown) {
  return { response: { status, data: { detail } } }
}

function renderList() {
  return render(
    <MemoryRouter>
      <Expenses />
    </MemoryRouter>,
  )
}

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={["/expenses/7"]}>
      <Routes>
        <Route path="/expenses/:id" element={<ExpenseDetail />} />
      </Routes>
    </MemoryRouter>,
  )
}

function renderNew() {
  return render(
    <MemoryRouter>
      <ExpenseNew />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  setRole("Associate")
})

describe("expenses list", () => {
  test("(1) list renders rows", async () => {
    apiMocks.get.mockResolvedValue({ data: [claim(), claim({ id: 8, amount: 99 })] })
    renderList()
    expect(await screen.findByText("#7")).toBeInTheDocument()
    expect(screen.getByText("2500 INR")).toBeInTheDocument()
    expect(screen.getAllByText("View")).toHaveLength(2)
    // Associate scope: the list call never carries an employee_id.
    expect(apiMocks.get).toHaveBeenCalledWith("/expenses/claims", { params: {} })
  })

  test("(2) empty-state on zero rows", async () => {
    apiMocks.get.mockResolvedValue({ data: [] })
    renderList()
    expect(await screen.findByText("No expense claims")).toBeInTheDocument()
    expect(screen.queryByText("#7")).not.toBeInTheDocument()
  })

  test("(3) loading skeleton", () => {
    apiMocks.get.mockReturnValue(new Promise(() => {}))
    renderList()
    expect(screen.getByText("Loading expense claims")).toBeInTheDocument()
  })

  test("(4) load-error RetryableAlert + retry", async () => {
    apiMocks.get
      .mockRejectedValueOnce(err(500, "Server error"))
      .mockResolvedValueOnce({ data: [] })
    renderList()
    expect(await screen.findByText("The expense claims could not be read.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /retry/i }))
    await waitFor(() => expect(apiMocks.get).toHaveBeenCalledTimes(2))
  })

  test("(6) HR shows queue + status filter", async () => {
    setRole("HR")
    apiMocks.get.mockResolvedValue({ data: [claim()] })
    renderList()
    expect(await screen.findByText("Expense claims queue")).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("Filter by status"), { target: { value: "APPROVED" } })
    await waitFor(() =>
      expect(apiMocks.get).toHaveBeenCalledWith("/expenses/claims", { params: { status: "APPROVED" } }),
    )
  })
})

describe("expense detail — role gates and state machine", () => {
  test("(5) Associate hides approve/pay buttons", async () => {
    setRole("Associate")
    apiMocks.get.mockImplementation((url: string) =>
      Promise.resolve({ data: url.endsWith("/receipts") ? [] : claim({ status: "SUBMITTED" }) }),
    )
    renderDetail()
    await screen.findByText("Expense claim #7")
    expect(screen.queryByText("Approve (L1)")).not.toBeInTheDocument()
    expect(screen.queryByText("Approve (final)")).not.toBeInTheDocument()
    expect(screen.queryByText("Mark paid")).not.toBeInTheDocument()
    expect(screen.queryByText("Reject")).not.toBeInTheDocument()
  })

  test("(9) submit posts the exact path", async () => {
    let state: Record<string, unknown> = claim({ status: "DRAFT" })
    apiMocks.get.mockImplementation((url: string) =>
      Promise.resolve({ data: url.endsWith("/receipts") ? [] : state }),
    )
    apiMocks.post.mockImplementation(() => {
      state = claim({ status: "SUBMITTED" })
      return Promise.resolve({ data: state })
    })
    renderDetail()
    fireEvent.click(await screen.findByText("Submit for approval"))
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/expenses/claims/7/submit"))
    expect(await screen.findByText(/Submitted · payment UNPAID/)).toBeInTheDocument()
  })

})

describe("expense detail — approvals, reject, rework, paid", () => {
  test("(11) l1-approve posts the exact path", async () => {
    setRole("Manager")
    let state: Record<string, unknown> = claim({ status: "SUBMITTED" })
    apiMocks.get.mockImplementation((url: string) =>
      Promise.resolve({ data: url.endsWith("/receipts") ? [] : state }),
    )
    apiMocks.post.mockImplementation(() => {
      state = claim({ status: "L1_APPROVED" })
      return Promise.resolve({ data: state })
    })
    renderDetail()
    fireEvent.click(await screen.findByText("Approve (L1)"))
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/expenses/claims/7/l1-approve"))
    expect(await screen.findByText(/L1 approved · payment UNPAID/)).toBeInTheDocument()
  })

  test("(12) approve then mark-paid sequence + invalid-state 409", async () => {
    setRole("HR")
    let state: Record<string, unknown> = claim({ status: "L1_APPROVED" })
    apiMocks.get.mockImplementation((url: string) =>
      Promise.resolve({ data: url.endsWith("/receipts") ? [] : state }),
    )
    apiMocks.post.mockImplementation((url: string) => {
      if (url.endsWith("/approve")) {
        state = claim({ status: "APPROVED" })
        return Promise.resolve({ data: state })
      }
      return Promise.reject(err(409, "Only an approved claim can be marked paid; claim 7 is DRAFT."))
    })
    renderDetail()
    fireEvent.click(await screen.findByText("Approve (final)"))
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/expenses/claims/7/approve"))
    fireEvent.click(await screen.findByText("Mark paid"))
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/expenses/claims/7/mark-paid"))
    expect(
      await screen.findByText("Only an approved claim can be marked paid; claim 7 is DRAFT."),
    ).toBeInTheDocument()
  })

  test("(13) reject sends reason + shows it", async () => {
    setRole("Manager")
    let state: Record<string, unknown> = claim({ status: "SUBMITTED" })
    apiMocks.get.mockImplementation((url: string) =>
      Promise.resolve({ data: url.endsWith("/receipts") ? [] : state }),
    )
    apiMocks.post.mockImplementation((_url: string, body: unknown) => {
      state = claim({ status: "REJECTED", rejection_reason: (body as { reason?: string }).reason })
      return Promise.resolve({ data: state })
    })
    renderDetail()
    fireEvent.change(await screen.findByLabelText("Rejection reason"), { target: { value: "No bill" } })
    fireEvent.click(screen.getByText("Reject"))
    await waitFor(() =>
      expect(apiMocks.post).toHaveBeenCalledWith("/expenses/claims/7/reject", { reason: "No bill" }),
    )
    expect(await screen.findByText("No bill")).toBeInTheDocument()
  })

  test("(14) rework returns the claim to DRAFT", async () => {
    let state: Record<string, unknown> = claim({ status: "REJECTED", rejection_reason: "No bill" })
    apiMocks.get.mockImplementation((url: string) =>
      Promise.resolve({ data: url.endsWith("/receipts") ? [] : state }),
    )
    apiMocks.post.mockImplementation(() => {
      state = claim({ status: "DRAFT", rejection_reason: null })
      return Promise.resolve({ data: state })
    })
    renderDetail()
    fireEvent.click(await screen.findByText("Send back to draft"))
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/expenses/claims/7/rework"))
    expect(await screen.findByText(/Draft · payment UNPAID/)).toBeInTheDocument()
  })
})

describe("expense detail — receipts, errors", () => {
  test("(15) receipt upload multipart + list + download_url", async () => {
    const receipt = {
      id: 1,
      claim_id: 7,
      file_name: "bill.pdf",
      content_type: "application/pdf",
      size_bytes: 42,
      download_url: "/api/v1/files/abc123",
    }
    apiMocks.get.mockImplementation((url: string) =>
      Promise.resolve({ data: url.endsWith("/receipts") ? [receipt] : claim({ status: "DRAFT" }) }),
    )
    apiMocks.post.mockResolvedValue({ data: receipt })
    renderDetail()
    const link = await screen.findByText("Download")
    expect(link).toHaveAttribute("href", "/api/v1/files/abc123")
    const upload = screen.getByLabelText("Receipt file") as HTMLInputElement
    fireEvent.change(upload, { target: { files: [new File(["x"], "bill.pdf", { type: "application/pdf" })] } })
    fireEvent.click(screen.getByText("Upload receipt"))
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/expenses/claims/7/receipts", expect.any(FormData), expect.anything()))
    const sent = apiMocks.post.mock.calls[0][1] as FormData
    expect(sent.get("file")).toBeInstanceOf(File)
  })

  test("(16) 403 permission-denied EmptyState names the role", async () => {
    setRole("Associate")
    apiMocks.get.mockRejectedValue(err(403, "Forbidden"))
    renderDetail()
    expect(await screen.findByText("Not visible for your role")).toBeInTheDocument()
    expect(screen.getByText(/your role is Associate/)).toBeInTheDocument()
  })

  test("(17) 404 removed-record message + reload", async () => {
    apiMocks.get.mockRejectedValue(err(404, "Not found"))
    renderDetail()
    expect(await screen.findByText("Expense claim not found")).toBeInTheDocument()
    expect(screen.getByText(/removed or never existed/)).toBeInTheDocument()
    fireEvent.click(screen.getByText("Reload"))
    await waitFor(() => expect(apiMocks.get).toHaveBeenCalledTimes(4))
  })
})

describe("expense create", () => {
  const cats = [
    { id: 3, code: "TRV", name: "Travel", is_active: true },
    { id: 4, code: "ML", name: "Meals", is_active: true },
  ]

  test("(7) create posts the exact body, no status fields", async () => {
    apiMocks.get.mockResolvedValue({ data: cats })
    apiMocks.post.mockResolvedValue({ data: claim({ status: "DRAFT", payment_status: "UNPAID" }) })
    renderNew()
    expect(await screen.findByText("TRV — Travel")).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Employee ID/), { target: { value: "12" } })
    fireEvent.change(screen.getByLabelText("Category"), { target: { value: "3" } })
    fireEvent.change(screen.getByLabelText(/Expense date/), { target: { value: "2026-11-20" } })
    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "2500" } })
    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Taxi" } })
    fireEvent.click(screen.getByText("File claim"))
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledTimes(1))
    expect(apiMocks.post).toHaveBeenCalledWith("/expenses/claims", {
      employee_id: 12,
      category_id: 3,
      expense_date: "2026-11-20",
      amount: 2500,
      currency: "INR",
      description: "Taxi",
    })
  })

  test("(8) 422 maps to per-field errors", async () => {
    apiMocks.get.mockResolvedValue({ data: cats })
    apiMocks.post.mockRejectedValue(
      err(422, [
        { loc: ["body", "amount"], msg: "greater than zero" },
        { loc: ["body", "category_id"], msg: "archived category" },
      ]),
    )
    renderNew()
    expect(await screen.findByText("TRV — Travel")).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Employee ID/), { target: { value: "12" } })
    fireEvent.change(screen.getByLabelText("Category"), { target: { value: "3" } })
    fireEvent.change(screen.getByLabelText(/Expense date/), { target: { value: "2026-11-20" } })
    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "-5" } })
    fireEvent.click(screen.getByText("File claim"))
    expect(await screen.findByText("greater than zero")).toBeInTheDocument()
    expect(screen.getByText("archived category")).toBeInTheDocument()
  })

  test("(18) categories dropdown comes from GET /expenses/categories", async () => {
    apiMocks.get.mockResolvedValue({ data: cats })
    renderNew()
    expect(await screen.findByText("TRV — Travel")).toBeInTheDocument()
    expect(screen.getByText("ML — Meals")).toBeInTheDocument()
    expect(apiMocks.get).toHaveBeenCalledWith("/expenses/categories")
  })

  test("(10) locked-claim 409 text surfaces verbatim on submit", async () => {
    apiMocks.get.mockImplementation((url: string) =>
      Promise.resolve({ data: url.endsWith("/receipts") ? [] : claim({ status: "DRAFT" }) }),
    )
    apiMocks.post.mockRejectedValue(err(409, "Only a draft claim can be edited; claim 7 is SUBMITTED."))
    renderDetail()
    fireEvent.click(await screen.findByText("Submit for approval"))
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/expenses/claims/7/submit"))
    expect(
      await screen.findByText("Only a draft claim can be edited; claim 7 is SUBMITTED."),
    ).toBeInTheDocument()
  })
})
