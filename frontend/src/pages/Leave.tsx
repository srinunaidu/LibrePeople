import { useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  StatCard,
  StatusPill, RetryableAlert} from "@/components/ui"
import { IconCheck, IconPalm, IconPlus, IconX } from "@/components/icons"
import { Link } from "react-router-dom"
import { useTenantNav } from "@/lib/tenantPath"
import api from "@/lib/api"
import { summarizeBulk } from "@/lib/bulk"
import { fetchAllEmployees } from "@/lib/employees"
import { useAuth } from "@/context/AuthContext"
import type { Employee, LeaveBalance, LeaveRequest, LeaveType } from "@/types"
import { AccordionItem } from "@/components/ui/accordion"
import { BulkBar } from "@/components/ui/bulk-bar"
import { useAutosave } from "@/hooks/useAutosave"

export default function Leave() {
  const { user } = useAuth()
  const tenantNav = useTenantNav()
  // Mirrors backend/app/api/v1/endpoints/leave.py: leave-type creation
  // (`:67→ADMIN_ROLES`) and entitlement assignment (`:241→ADMIN_ROLES`) are
  // admin-only; request approve/reject (`:303/:356→MANAGER_ROLES`) is
  // manager-and-above; balances and requests are read by WORKFORCE_ROLES
  // (SuperAdmin, HR, Manager, Associate) — a PayrollViewer is outside that
  // set and cannot load balances at all.
  const isAdmin = user?.role === "SuperAdmin" || user?.role === "HR"
  const isManager = isAdmin || user?.role === "Manager"
  const isWorkforce =
    isAdmin ||
    user?.role === "Manager" ||
    user?.role === "Associate"
  const [types, setTypes] = useState<LeaveType[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [balances, setBalances] = useState<LeaveBalance[]>([])
  const [requests, setRequests] = useState<LeaveRequest[]>([])
  // Which of the four source lists failed to load, so one role-forbidden GET
  // (e.g. /leave/balances for a PayrollViewer) never blanks the whole tab.
  type LoadKey = "types" | "employees" | "balances" | "requests"
  const LOAD_LABELS: Record<LoadKey, string> = {
    types: "leave types",
    employees: "employees",
    balances: "leave balances",
    requests: "leave requests",
  }
  const [failed, setFailed] = useState<LoadKey[]>([])
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState("")

  const [typeForm, setTypeForm] = useState({ name: "", code: "", max_days_per_year: 12, is_paid: true })
  const [entitle, setEntitle] = useState({ entitlement_year: new Date().getFullYear(), leave_type_id: "" })
  const initialReqForm = { employee_id: "", leave_type_id: "", start_date: "", end_date: "", reason: "" }
  const [reqForm, setReqForm] = useState(() => {
    try {
      const raw = localStorage.getItem("leave-req-draft")
      if (raw) return JSON.parse(raw).data as typeof initialReqForm
    } catch { /* no stored draft — start blank */ }
    return initialReqForm
  })
  const { savedAt: draftSavedAt } = useAutosave("leave-req-draft", reqForm, 800)
  const [reqErrors, setReqErrors] = useState<Record<string, string>>({})
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [showDraftRestore, setShowDraftRestore] = useState(() => {
    try { return !!localStorage.getItem("leave-req-draft") } catch { return false }
  })

  const load = async () => {
    setLoading(true)
    const keys: LoadKey[] = ["types", "employees", "balances", "requests"]
    const results = await Promise.allSettled([
      api.get("/leave/types"),
      fetchAllEmployees().then(({ items }) => ({ data: items })),
      api.get("/leave/balances"),
      api.get("/leave/requests"),
    ])
    const failedKeys: LoadKey[] = []
    results.forEach((r, i) => {
      const key = keys[i]
      if (r.status === "fulfilled") {
        const data = r.value.data
        if (key === "types") setTypes(data)
        else if (key === "employees") setEmployees(data)
        else if (key === "balances") setBalances(data)
        else if (key === "requests") setRequests(data)
      } else {
        failedKeys.push(key)
      }
    })
    setFailed(failedKeys)
    setError(
      failedKeys.length > 0
        ? `Some leave data could not be loaded: ${failedKeys
            .map((k) => LOAD_LABELS[k])
            .join(", ")}. Check your connection or use Reload to retry.`
        : "",
    )
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  const act = async (key: string, fn: () => Promise<unknown>, msg: string) => {
    setError("")
    setNotice("")
    setBusy(key)
    try {
      await fn()
      setNotice(msg)
      await load()
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Action failed")
    } finally {
      setBusy("")
    }
  }

  const empName = (id: number) => {
    const e = employees.find((x) => x.id === id)
    return e ? `${e.first_name} ${e.last_name}` : `#${id}`
  }

  const validateReq = (field: string, value: string) => {
    if (field === "reason" && value && value.length < 3) return "Reason must be at least 3 characters"
    if (field === "start_date" || field === "end_date") {
      if (value && reqForm.start_date && reqForm.end_date && reqForm.start_date > reqForm.end_date) return "End date must be after start date"
    }
    return ""
  }

  const runBulk = async (verbPast: string, endpoint: (id: number) => string) => {
    const pending = requests.filter((r) => selectedIds.has(r.id) && r.status === "Pending")
    if (pending.length === 0) return
    setError("")
    setNotice("")
    const ids = pending.map((r) => r.id)
    const results = await Promise.allSettled(ids.map((id) => api.post(endpoint(id))))
    const { failures, notice: bulkNotice, error: bulkError } = summarizeBulk(ids, results, verbPast, "request")
    // Keep failures selected so the operator can adjust and retry them.
    setSelectedIds(new Set(failures.map((f) => f.id)))
    await load()
    if (bulkNotice) setNotice(bulkNotice)
    if (bulkError) setError(bulkError)
  }

  const handleBulkApprove = () => runBulk("Approved", (id) => `/leave/requests/${id}/approve`)

  const handleBulkReject = () => runBulk("Rejected", (id) => `/leave/requests/${id}/reject`)

  const pending = requests.filter((r) => r.status === "Pending").length
  const approvedDays = requests
    .filter((r) => r.status === "Approved")
    .reduce((s, r) => s + (r.working_days ?? 0), 0)
  const availableDays = balances.reduce((s, b) => s + (b.available_days ?? 0), 0)

  /**
   * Empty state that separates "no rows yet" from "this collection failed to
   * load" — a 403 on one leave dataset must not read as an empty module.
   */
  const emptyDesc = (key: LoadKey, noneDesc: string) =>
    failed.includes(key)
      ? `The ${LOAD_LABELS[key]} list could not be loaded — it may be temporarily unavailable or not visible for your role. Use Reload to retry.`
      : noneDesc

  return (
    <Layout>
      <PageHeader
        compact
        icon={<IconPalm />}
        title="Leave Management"
        description="Configure leave types, assign entitlements, and approve requests."
      />

      {error && (
        <Alert
          tone="error"
          title="Leave data incomplete"
          action={
            <button type="button" className="btn btn-secondary btn-sm" onClick={load}>
              Reload
            </button>
          }
        >
          {error}
        </Alert>
      )}
      {notice && <Alert tone="success">{notice}</Alert>}

      {loading ? (
        <LoadingRegion label="Loading leave data">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="skeleton h-24" />
            ))}
          </div>
        </LoadingRegion>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
          <StatCard tone="brand" label="Leave types" value={types.length} />
          <StatCard tone="amber" label="Pending requests" value={pending} />
          <StatCard tone="green" label="Days approved" value={`${approvedDays}d`} />
          <StatCard tone="violet" label="Days available" value={`${availableDays}d`} />
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 mb-5">
        {/* Leave types + entitlement — creation and assignment are
            ADMIN_ROLES server-side (leave.py:67/241) */}
        <div className="space-y-5">
          <section className="card">
            {isAdmin ? (
              <div className="toolbar">
                <div className="field grow min-w-[140px]">
                  <label htmlFor="lt-name" className="field-label">Name (required)</label>
                  <input id="lt-name" className="input" value={typeForm.name}
                    onChange={(e) => setTypeForm({ ...typeForm, name: e.target.value })} />
                </div>
                <div className="field w-28">
                  <label htmlFor="lt-code" className="field-label">Code (required)</label>
                  <input id="lt-code" className="input" value={typeForm.code}
                    onChange={(e) => setTypeForm({ ...typeForm, code: e.target.value })} />
                </div>
                <div className="field w-28">
                  <label htmlFor="lt-days" className="field-label">Days/yr (required)</label>
                  <input id="lt-days" type="number" className="input" value={typeForm.max_days_per_year}
                    onChange={(e) => setTypeForm({ ...typeForm, max_days_per_year: Number(e.target.value) })} />
                </div>
                <button className="btn btn-primary" disabled={!typeForm.name || !typeForm.code || busy === "lt"}
                  onClick={() => act("lt", () => api.post("/leave/types", typeForm), "Leave type created")}>
                  <IconPlus className="w-4 h-4" />
                  {busy === "lt" ? "Adding…" : "Add type"}
                </button>
              </div>
            ) : (
              <p className="px-5 pt-4 pb-2 text-sm text-text-secondary" role="note">
                Leave types are configured by SuperAdmin or HR — you can view the configured
                types and entitlements below, but creating them is not part of
                {user?.role ? ` the ${user.role}` : " your"} role.
              </p>
            )}

            {types.length === 0 ? (
              <EmptyState title={failed.includes("types") ? "Leave types unavailable" : "No leave types yet — you're all set"}
                description={emptyDesc("types", "Add a leave type above to start assigning entitlements.")} />
            ) : (
              <div className="table-scroll">
                <table className="table-base table-striped table-compact">
                  <caption className="sr-only">Configured leave types</caption>
                  <thead>
                    <tr>
                      <th scope="col">Code</th>
                      <th scope="col">Name</th>
                      <th scope="col" className="num">Days/yr</th>
                      <th scope="col">Paid</th>
                    </tr>
                  </thead>
                  <tbody>
                    {types.map((t) => (
                      <tr key={t.id}>
                        <td className="font-mono text-xs">{t.code}</td>
                        <td>{t.name}</td>
                        <td className="num">{t.max_days_per_year}</td>
                        <td>
                          <span className={`badge ${t.is_paid ? "badge-green" : "badge-slate"}`}>
                            {t.is_paid ? "Paid" : "Unpaid"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="card">
            {isAdmin ? (
              <div className="toolbar">
                <div className="field w-32">
                  <label htmlFor="en-year" className="field-label">Year (required)</label>
                  <input id="en-year" type="number" className="input" value={entitle.entitlement_year}
                    onChange={(e) => setEntitle({ ...entitle, entitlement_year: Number(e.target.value) })} />
                </div>
                <div className="field min-w-[160px]">
                  <label htmlFor="en-type" className="field-label">Type</label>
                  <select id="en-type" className="input" value={entitle.leave_type_id}
                    onChange={(e) => setEntitle({ ...entitle, leave_type_id: e.target.value })}>
                    <option value="">All active types</option>
                    {types.map((t) => (
                      <option key={t.id} value={t.id}>{t.code} — {t.name}</option>
                    ))}
                  </select>
                </div>
                <button className="btn btn-secondary" disabled={busy === "en"}
                  onClick={() => act("en", () => api.post("/leave/entitlements", {
                    entitlement_year: entitle.entitlement_year,
                    leave_type_id: entitle.leave_type_id ? Number(entitle.leave_type_id) : null,
                  }), "Entitlements assigned")}>
                  Assign entitlements
                </button>
              </div>
            ) : (
              <p className="px-5 py-4 text-sm text-text-secondary" role="note">
                Entitlement assignment requires the SuperAdmin or HR role — annual
                entitlements are assigned by HR, not by managers or associates.
              </p>
            )}
          </section>
        </div>

        {/* Balances — /leave/balances is WORKFORCE_ROLES (leave.py:100); a
            PayrollViewer is outside that set and must read the reason, not
            a silent empty card. */}
        <SectionCard compact icon={<IconPalm />} title="Balances"
          description="Available days per employee and leave type.">
          {!isWorkforce ? (
            <EmptyState title="Balances are not part of your role"
              description={`Leave balances are per-employee workforce records and are not visible for your role (${user?.role || "unknown"}). Your role can read organisational leave reports instead — see Reporting & Analytics.`} />
          ) : balances.length === 0 ? (
            <EmptyState title={failed.includes("balances") ? "Balances unavailable" : "No balances assigned"}
              description={emptyDesc("balances", "Assign entitlements above to populate leave balances.")} />
          ) : (
            <div
              className="table-scroll max-h-[420px] overflow-y-auto"
              tabIndex={0}
              role="region"
              aria-label="Leave balances by employee and type"
            >
              <table className="table-base table-striped table-compact">
                <caption className="sr-only">Leave balances by employee and type</caption>
                <thead>
                  <tr>
                    <th scope="col">Employee</th>
                    <th scope="col">Type</th>
                    <th scope="col" className="num">Year</th>
                    <th scope="col" className="num">Entitled</th>
                    <th scope="col" className="num">Used</th>
                    <th scope="col" className="num">Available</th>
                    <th scope="col">Ledger</th>
                  </tr>
                </thead>
                <tbody>
                  {balances.map((b) => (
                    <tr key={b.id}>
                      <td>{empName(b.employee_id)}</td>
                      <td>{b.leave_type_name || `#${b.leave_type_id}`}</td>
                      <td className="num">{b.entitlement_year}</td>
                      <td className="num">{b.entitled_days}</td>
                      <td className="num">{b.used_days}</td>
                      <td className="num font-semibold">{b.available_days}</td>
                      <td>
                        <Link to={tenantNav.to(`/leave/ledger/${b.employee_id}`)} className="action-link whitespace-nowrap">
                          View ledger →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>

      {/* New request — POST /leave/requests is WORKFORCE_ROLES
          (leave.py:286); a PayrollViewer never got balances so they also
          cannot submit a request. */}
      {isWorkforce ? (
        <section className="card mb-5">
          {showDraftRestore && (
            <div className="px-4 py-2 bg-warning-light border-b border-border flex items-center justify-between text-sm">
              <span className="text-warning-text">Draft restored from previous session.</span>
              <button type="button" className="text-xs font-medium text-warning-text hover:underline" onClick={() => { localStorage.removeItem("leave-req-draft"); setReqForm(initialReqForm); setShowDraftRestore(false) }}>Discard</button>
            </div>
          )}
          <div className="toolbar">
          <div className="field min-w-[180px]">
            <label htmlFor="lr-emp" className="field-label">Employee (required)</label>
            <select id="lr-emp" className="input" value={reqForm.employee_id}
              onChange={(e) => setReqForm({ ...reqForm, employee_id: e.target.value })}
              onBlur={() => setReqErrors((s) => ({ ...s, employee_id: !reqForm.employee_id ? "Select an employee" : "" }))}>
              <option value="">Select employee…</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>
              ))}
            </select>
            {reqErrors.employee_id && <span className="text-xs text-error-text">{reqErrors.employee_id}</span>}
          </div>
          <div className="field min-w-[160px]">
            <label htmlFor="lr-type" className="field-label">Leave type (required)</label>
            <select id="lr-type" className="input" value={reqForm.leave_type_id}
              onChange={(e) => setReqForm({ ...reqForm, leave_type_id: e.target.value })}
              onBlur={() => setReqErrors((s) => ({ ...s, leave_type_id: !reqForm.leave_type_id ? "Select a leave type" : "" }))}>
              <option value="">Select type…</option>
              {types.map((t) => (
                <option key={t.id} value={t.id}>{t.code} — {t.name}</option>
              ))}
            </select>
            {reqErrors.leave_type_id && <span className="text-xs text-error-text">{reqErrors.leave_type_id}</span>}
          </div>
          <div className="field">
            <label htmlFor="lr-start" className="field-label">Start (required)</label>
            <input id="lr-start" type="date" className="input" value={reqForm.start_date}
              onChange={(e) => setReqForm({ ...reqForm, start_date: e.target.value })}
              onBlur={() => setReqErrors((s) => ({ ...s, start_date: validateReq("start_date", reqForm.start_date) }))} />
            {reqErrors.start_date && <span className="text-xs text-error-text">{reqErrors.start_date}</span>}
          </div>
          <div className="field">
            <label htmlFor="lr-end" className="field-label">End (required)</label>
            <input id="lr-end" type="date" className="input" value={reqForm.end_date}
              onChange={(e) => setReqForm({ ...reqForm, end_date: e.target.value })}
              onBlur={() => setReqErrors((s) => ({ ...s, end_date: validateReq("end_date", reqForm.end_date) }))} />
            {reqErrors.end_date && <span className="text-xs text-error-text">{reqErrors.end_date}</span>}
          </div>
          <div className="field grow min-w-[160px]">
            <label htmlFor="lr-reason" className="field-label">Reason (required)</label>
            <input id="lr-reason" className="input" value={reqForm.reason}
              onChange={(e) => setReqForm({ ...reqForm, reason: e.target.value })}
              onBlur={() => setReqErrors((s) => ({ ...s, reason: validateReq("reason", reqForm.reason) }))} />
            {reqErrors.reason && <span className="text-xs text-error-text">{reqErrors.reason}</span>}
          </div>
          <button className="btn btn-primary"
            disabled={!reqForm.employee_id || !reqForm.leave_type_id || !reqForm.start_date || !reqForm.end_date || busy === "lr"}
            onClick={() => {
              localStorage.removeItem("leave-req-draft"); setShowDraftRestore(false);
              act("lr", () => api.post("/leave/requests", {
              employee_id: Number(reqForm.employee_id),
              leave_type_id: Number(reqForm.leave_type_id),
              start_date: reqForm.start_date,
              end_date: reqForm.end_date,
              reason: reqForm.reason || undefined,
            }), "Leave request created").then(() => setReqForm(initialReqForm))
            }}>
            {busy === "lr" ? "Submitting…" : "Submit request"}
          </button>
          </div>
          {draftSavedAt && <p className="px-4 py-1 text-xs text-fg-muted">Draft saved</p>}
        </section>
      ) : (
        <section className="card mb-5" aria-label="Submit a leave request">
          <p className="px-5 py-4 text-sm text-text-secondary" role="note">
            Leave requests are raised by workforce members (your role is{" "}
            {user?.role || "unknown"}); payroll monitoring roles read leave
            usage in <strong>Reporting &amp; Analytics</strong> instead.
          </p>
        </section>
      )}

      {/* Requests — approve/reject is MANAGER_ROLES (leave.py:303/356);
          cancellation is WORKFORCE. Non-manager roles see status, not
          buttons. */}
      <SectionCard compact icon={<IconCheck />} title="Requests"
        description="Approve, reject or cancel submitted leave requests.">
        {requests.length === 0 ? (
          <EmptyState title={failed.includes("requests") ? "Leave requests unavailable" : "No pending requests — you're all caught up"}
            description={emptyDesc("requests", "Requests submitted above will appear here for approval.")} />
        ) : (
          <>
            <BulkBar
              selectedCount={selectedIds.size}
              totalCount={requests.length}
              allSelected={selectedIds.size === requests.length}
              onSelectAll={() => setSelectedIds(selectedIds.size === requests.length ? new Set() : new Set(requests.map((r) => r.id)))}
              actions={
                isManager ? (
                  <>
                    <button type="button" className="btn btn-primary btn-xs min-h-[44px]" onClick={handleBulkApprove} disabled={selectedIds.size === 0}>Approve selected</button>
                    <button type="button" className="btn btn-secondary btn-xs min-h-[44px]" onClick={handleBulkReject} disabled={selectedIds.size === 0}>Reject selected</button>
                  </>
                ) : undefined
              }
            />
            <div className="table-scroll mt-3">
            <table className="table-base table-striped table-compact">
              <caption className="sr-only">Leave requests and their approval actions</caption>
              <thead>
                <tr>
                  <th scope="col"><input type="checkbox" aria-label="Select all" checked={selectedIds.size === requests.length && requests.length > 0} onChange={() => setSelectedIds(selectedIds.size === requests.length ? new Set() : new Set(requests.map((r) => r.id)))} className="rounded border-border" /></th>
                  <th scope="col">Employee</th>
                  <th scope="col">Dates</th>
                  <th scope="col" className="num">Days</th>
                  <th scope="col">Reason</th>
                  <th scope="col">Status</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((r) => (
                  <tr key={r.id}>
                    <td><input type="checkbox" aria-label={`Select request ${r.id}`} checked={selectedIds.has(r.id)} onChange={(e) => { const s = new Set(selectedIds); if (e.target.checked) s.add(r.id); else s.delete(r.id); setSelectedIds(s) }} className="rounded border-border" /></td>
                    <td>{empName(r.employee_id)}</td>
                    <td className="whitespace-nowrap">{r.start_date} → {r.end_date}</td>
                    <td className="num font-medium">{r.working_days}</td>
                    <td className="text-fg-muted">{r.reason || "—"}</td>
                    <td><StatusPill status={r.status} /></td>
                    <td>
                      <div className="flex items-center gap-2">
                        {r.status === "Pending" && isManager && (
                          <>
                            <button className="btn btn-primary btn-xs min-h-[44px]" disabled={busy === `ap${r.id}`}
                              onClick={() => act(`ap${r.id}`, () => api.post(`/leave/requests/${r.id}/approve`), "Approved")}>
                              Approve
                            </button>
                            <button className="btn btn-ghost btn-xs min-h-[44px]" disabled={busy === `rj${r.id}`}
                              onClick={() => act(`rj${r.id}`, () => api.post(`/leave/requests/${r.id}/reject`), "Rejected")}>
                              Reject
                            </button>
                          </>
                        )}
                        {(r.status === "Pending" || r.status === "Approved") && (
                          <button className="action-link text-fg-muted min-h-[44px] inline-flex items-center" disabled={busy === `cx${r.id}`}
                            onClick={() => act(`cx${r.id}`, () => api.post(`/leave/requests/${r.id}/cancel`), "Cancelled")}>
                            Cancel
                          </button>
                        )}
                        {r.status === "Pending" && !isManager && (
                          <span className="text-xs text-fg-muted">Awaiting a manager</span>
                        )}
                        {r.status !== "Pending" && r.status !== "Approved" && (
                          <span className="text-xs text-fg-muted">Closed</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </>
        )}
        <div className="mt-4">
          <AccordionItem title="Advanced Options">
            <p className="text-sm text-fg-muted">Bulk import leave balances via CSV or configure approval workflows in Admin → Workflow Approval.</p>
          </AccordionItem>
        </div>
      </SectionCard>
    </Layout>
  )
}