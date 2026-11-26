/* LP-EXP-002 — file a new expense claim.
 * POST /expenses/claims sends only {employee_id, category_id, expense_date,
 * amount, currency, description} — never status/payment_status (the schemas
 * expose neither, expenses.py:3-11). New claims come back DRAFT/UNPAID.
 * Categories load from GET /expenses/categories for the dropdown.
 */
import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Layout } from "@/components/Layout"
import {
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  TableSkeleton,
} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { errorMessage, fieldErrors } from "@/lib/api"
import type { ExpenseCategory } from "./shared"

export default function ExpenseNew() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [categories, setCategories] = useState<ExpenseCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<unknown | null>(null)
  const [employeeId, setEmployeeId] = useState("")
  const [categoryId, setCategoryId] = useState("")
  const [expenseDate, setExpenseDate] = useState("")
  const [amount, setAmount] = useState("")
  const [currency, setCurrency] = useState("INR")
  const [description, setDescription] = useState("")
  const [fieldErrs, setFieldErrs] = useState<Map<string, string>>(new Map())
  const [formError, setFormError] = useState("")
  const [notice, setNotice] = useState("")
  const [saving, setSaving] = useState(false)

  const loadCategories = async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const { data } = await api.get("/expenses/categories")
      setCategories(Array.isArray(data) ? data : [])
    } catch (e) {
      setLoadError(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCategories()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const field = (name: string) => fieldErrs.get(name)

  const submit = async () => {
    setSaving(true)
    setFormError("")
    setNotice("")
    setFieldErrs(new Map())
    // Exact create body — status/payment_status must never be sent.
    const body = {
      employee_id: Number(employeeId),
      category_id: Number(categoryId),
      expense_date: expenseDate,
      amount: Number(amount),
      currency: currency.trim() || "INR",
      description: description.trim() || undefined,
    }
    try {
      const { data } = await api.post("/expenses/claims", body)
      setNotice(`Claim #${data.id} filed as Draft (unpaid).`)
      navigate(`/expenses/${data.id}`, { replace: true })
    } catch (e) {
      // 422 arrays render per-field; archived-category 422 names the category.
      const fe = fieldErrors(e)
      if (fe.size > 0) setFieldErrs(fe)
      setFormError(errorMessage(e, "The claim could not be filed."))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <Layout>
        <LoadingRegion label="Loading expense form">
          <TableSkeleton rows={4} cols={2} />
        </LoadingRegion>
      </Layout>
    )
  }

  if (loadError) {
    return (
      <Layout>
        <PageHeader compact title="New expense claim" description="File a claim for reimbursement." />
        <Alert tone="error">{errorMessage(loadError, "The expense categories could not be read.")}</Alert>
        <button type="button" className="btn btn-secondary btn-sm mt-4" onClick={loadCategories}>
          Reload
        </button>
      </Layout>
    )
  }

  const globalError = field("_global")

  return (
    <Layout>
      <PageHeader
        compact
        title="New expense claim"
        description="Filed as Draft (unpaid); submit it for approval from the claim detail."
        actions={
          <Link to=".." className="btn btn-secondary btn-sm">
            Back to claims
          </Link>
        }
      />
      {notice && <Alert tone="success">{notice}</Alert>}
      {formError && <Alert tone="error">{formError}</Alert>}
      {globalError && <Alert tone="error">{globalError}</Alert>}
      {user?.role === "PayrollViewer" && (
        <EmptyState
          title="Not visible for your role"
          description={`Filing claims needs a workforce role; your role is ${user?.role || "unknown"}.`}
        />
      )}
      <SectionCard compact title="Claim details" description="Only these fields are sent; status stays server-side.">
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="exp-employee" className="field-label">
              Employee ID (required)
            </label>
            <input
              id="exp-employee"
              className="input"
              inputMode="numeric"
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              placeholder="e.g. 12"
            />
            {field("employee_id") && <p className="text-sm text-rose-600 mt-1">{field("employee_id")}</p>}
          </div>
          <div>
            <label htmlFor="exp-category" className="field-label">
              Category (required)
            </label>
            <select
              id="exp-category"
              aria-label="Category"
              className="rounded border px-3 py-2 w-full"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
            >
              <option value="">Select a category</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} — {c.name}
                </option>
              ))}
            </select>
            {field("category_id") && <p className="text-sm text-rose-600 mt-1">{field("category_id")}</p>}
          </div>
          <div>
            <label htmlFor="exp-date" className="field-label">
              Expense date (required)
            </label>
            <input
              id="exp-date"
              type="date"
              className="input"
              value={expenseDate}
              onChange={(e) => setExpenseDate(e.target.value)}
            />
            {field("expense_date") && <p className="text-sm text-rose-600 mt-1">{field("expense_date")}</p>}
          </div>
          <div>
            <label htmlFor="exp-amount" className="field-label">
              Amount (required, greater than zero)
            </label>
            <input
              id="exp-amount"
              className="input"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="e.g. 2500"
            />
            {field("amount") && <p className="text-sm text-rose-600 mt-1">{field("amount")}</p>}
          </div>
          <div>
            <label htmlFor="exp-currency" className="field-label">
              Currency
            </label>
            <input
              id="exp-currency"
              className="input font-mono"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              maxLength={3}
              placeholder="INR"
            />
            {field("currency") && <p className="text-sm text-rose-600 mt-1">{field("currency")}</p>}
          </div>
          <div>
            <label htmlFor="exp-desc" className="field-label">
              Description
            </label>
            <input
              id="exp-desc"
              className="input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What was this for?"
            />
            {field("description") && <p className="text-sm text-rose-600 mt-1">{field("description")}</p>}
          </div>
        </div>
        <button
          type="button"
          className="btn btn-primary mt-4"
          disabled={saving || !employeeId.trim() || !categoryId || !expenseDate || !amount.trim()}
          onClick={submit}
        >
          {saving ? "Filing…" : "File claim"}
        </button>
      </SectionCard>
    </Layout>
  )
}
