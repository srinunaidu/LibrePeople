/**
 * Leave Ledger & Reconciliation — every accrual, usage and reversal.
 *
 * Role gates mirror backend/app/api/v1/endpoints/leave.py and backend/app/api/deps.py:
 *  WORKFORCE_ROLES = SuperAdmin, HR, Manager, Associate → ledger + balances
 *  MANAGER_ROLES  = SuperAdmin, HR, Manager            → reconciliation
 *  REPORTS_ROLES  = SuperAdmin, HR, PayrollViewer      → payroll-input
 *
 * Reads are independent (Promise.allSettled-ish: ledger is employee-driven,
 * reconciliation and payroll-input are period-driven). Each section tells the
 * viewer why it is not theirs rather than showing a form that would answer 403.
 */
import { useCallback, useEffect, useState } from "react"
import { useParams, Link } from "react-router-dom"
import { useTenantNav } from "@/lib/tenantPath"
import { Layout } from "@/components/Layout"
import {
  Input,
  Select,Alert,
  Button,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  Table,
  TableSkeleton, RetryableAlert, StatusPill } from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { formatDate, formatDateTime } from "@/lib/format"
import api, { errorMessage } from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import type {
  Employee,
  LeaveBalance,
  LeaveLedgerEntry,
  LeavePayrollInput,
  LeaveReconciliation,
} from "@/types"

const WORKFORCE_ROLES = ["SuperAdmin", "HR", "Manager", "Associate"] as const
const MANAGER_ROLES = ["SuperAdmin", "HR", "Manager"] as const
const REPORTS_ROLES = ["SuperAdmin", "HR", "PayrollViewer"] as const

function isNotFound(err: unknown): boolean {
  return (err as { response?: { status?: number } })?.response?.status === 404
}

export default function LeaveLedger() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const localeOpts = { locale: tenant?.locale, timeZone: tenant?.timezone }
  // Dates render in the tenant locale/timezone via format.ts —
  // never the browser default.
  const fmtDate = (value?: string | null) => formatDate(value, localeOpts)
  const fmtDateTime = (value?: string | null) => formatDateTime(value, localeOpts)
  const role = user?.role ?? ""
  const tenantNav = useTenantNav()
  const canWorkforce = (WORKFORCE_ROLES as readonly string[]).includes(role)
  const canManager = (MANAGER_ROLES as readonly string[]).includes(role)
  const canReports = (REPORTS_ROLES as readonly string[]).includes(role)
  const { employeeId: routeEmployeeId } = useParams<{ employeeId: string }>()

  const [employees, setEmployees] = useState<Employee[]>([])
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>(routeEmployeeId ?? "")
  const [ledger, setLedger] = useState<LeaveLedgerEntry[]>([])
  const [balances, setBalances] = useState<LeaveBalance[]>([])
  const [ledgerLoading, setLedgerLoading] = useState(false)
  const [ledgerError, setLedgerError] = useState("")
  const [ledgerNotFound, setLedgerNotFound] = useState(false)

  const [reconciliation, setReconciliation] = useState<LeaveReconciliation | null>(null)
  const [reconLoading, setReconLoading] = useState(false)
  const [reconError, setReconError] = useState("")
  const [reconNotFound, setReconNotFound] = useState(false)
  const [reconYear, setReconYear] = useState<string>("")

  const [payrollInput, setPayrollInput] = useState<LeavePayrollInput | null>(null)
  const [payrollLoading, setPayrollLoading] = useState(false)
  const [payrollError, setPayrollError] = useState("")
  const [payrollNotFound, setPayrollNotFound] = useState(false)
  const [periodStart, setPeriodStart] = useState<string>("")
  const [periodEnd, setPeriodEnd] = useState<string>("")

  const [employeesLoading, setEmployeesLoading] = useState(true)

  // Load employees + initial reconciliation/payroll-input (without ledger which needs a picker)
  const loadEmployees = useCallback(async () => {
    setEmployeesLoading(true)
    try {
      const { items } = await fetchAllEmployees()
      setEmployees(items)
      if (!selectedEmployeeId && items.length > 0 && !routeEmployeeId) {
        // leave picker empty until user chooses, or use first if not deep-linked
      }
      if (routeEmployeeId && !selectedEmployeeId) setSelectedEmployeeId(routeEmployeeId)
    } catch {
      setEmployees([])
    } finally {
      setEmployeesLoading(false)
    }
  }, [routeEmployeeId, selectedEmployeeId])

  useEffect(() => {
    void loadEmployees()
  }, [loadEmployees])

  // Keep selectedEmployeeId in sync with route param
  useEffect(() => {
    if (routeEmployeeId && routeEmployeeId !== selectedEmployeeId) setSelectedEmployeeId(routeEmployeeId)
  }, [routeEmployeeId, selectedEmployeeId])

  const loadLedger = useCallback(async (employeeId: number) => {
    if (!canWorkforce) return
    setLedgerLoading(true)
    setLedgerError("")
    setLedgerNotFound(false)
    const [ledgerR, balancesR] = await Promise.allSettled([
      api.get<LeaveLedgerEntry[]>(`/leave/balances/${employeeId}/ledger`),
      api.get<LeaveBalance[]>("/leave/balances", { params: { employee_id: employeeId } }),
    ])
    if (ledgerR.status === "fulfilled") {
      const data = (ledgerR.value as { data: LeaveLedgerEntry[] }).data ?? []
      // Ledger is chronological (oldest first) per leave.py — sort defensively by created_at
      const sorted = [...data].sort((a, b) => {
        const da = a.created_at ? new Date(a.created_at).getTime() : 0
        const db = b.created_at ? new Date(b.created_at).getTime() : 0
        return da - db
      })
      setLedger(sorted)
    } else {
      setLedger([])
      if (isNotFound(ledgerR.reason)) setLedgerNotFound(true)
      else setLedgerError(errorMessage(ledgerR.reason, "The ledger could not be read."))
    }
    if (balancesR.status === "fulfilled") {
      setBalances((balancesR.value as { data: LeaveBalance[] }).data ?? [])
    } else {
      setBalances([])
    }
    setLedgerLoading(false)
  }, [canWorkforce])

  useEffect(() => {
    if (selectedEmployeeId) void loadLedger(Number(selectedEmployeeId))
    else {
      setLedger([])
      setBalances([])
      setLedgerError("")
      setLedgerNotFound(false)
    }
  }, [selectedEmployeeId, loadLedger])

  const loadReconciliation = useCallback(async () => {
    if (!canManager) return
    setReconLoading(true)
    setReconError("")
    setReconNotFound(false)
    try {
      const params: Record<string, string | number> = {}
      if (reconYear) params.year = Number(reconYear)
      if (selectedEmployeeId) params.employee_id = Number(selectedEmployeeId)
      const { data } = await api.get<LeaveReconciliation>("/leave/reconciliation", { params })
      setReconciliation(data)
    } catch (err) {
      setReconciliation(null)
      if (isNotFound(err)) setReconNotFound(true)
      else setReconError(errorMessage(err, "The reconciliation report could not be read."))
    } finally {
      setReconLoading(false)
    }
  }, [canManager, reconYear, selectedEmployeeId])

  const loadPayrollInput = useCallback(async () => {
    if (!canReports) return
    if (!periodStart || !periodEnd) {
      setPayrollError("Choose a start and end date to query payroll input.")
      return
    }
    if (periodEnd < periodStart) {
      setPayrollError("The end date cannot be before the start date.")
      return
    }
    setPayrollLoading(true)
    setPayrollError("")
    setPayrollNotFound(false)
    try {
      const { data } = await api.get<LeavePayrollInput>("/leave/payroll-input", {
        params: { period_start: periodStart, period_end: periodEnd },
      })
      setPayrollInput(data)
    } catch (err) {
      setPayrollInput(null)
      if (isNotFound(err)) setPayrollNotFound(true)
      else setPayrollError(errorMessage(err, "The payroll input could not be read."))
    } finally {
      setPayrollLoading(false)
    }
  }, [canReports, periodStart, periodEnd])

  // Auto-load reconciliation once (and when year/employee changes via explicit action)
  useEffect(() => {
    if (canManager) void loadReconciliation()
  }, [canManager, loadReconciliation])

  const employeeName = (id: number) => {
    const e = employees.find((r) => r.id === id)
    return e ? `${e.first_name} ${e.last_name}` : `Employee #${id}`
  }

  const leaveTypeName = (id: number) => {
    const b = balances.find((x) => x.leave_type_id === id)
    return b?.leave_type_name ?? `#${id}`
  }

  return (
    <Layout>
      <PageHeader
        compact
        title="Leave Ledger & Reconciliation"
        description="Every accrual, usage and reversal — the ledger that proves the balance."
      />

      {/* Ledger timeline */}
      <SectionCard
        compact
        title="Ledger timeline"
        description="One employee's leave history, oldest first. The running balance after each movement is stored, so the balance is recomputed from the ledger alone."
      >
        {!canWorkforce ? (
          <div className="p-5">
            <EmptyState
              title="The ledger is available to SuperAdmin, HR, Manager and Associate"
              description="Your role does not read leave ledgers. An administrator can grant a workforce role."
            />
          </div>
        ) : (
          <>
            <div className="p-5 border-b border-border">
              <div className="flex flex-wrap gap-3 items-end">
                <div className="flex-1 min-w-[240px]">
                  <label htmlFor="ledger-employee" className="block text-xs font-medium text-text-secondary mb-1">Employee</label>
                  <Select
                    id="ledger-employee"
                    value={selectedEmployeeId}
                    onChange={(e) => setSelectedEmployeeId(e.target.value)}
                  >
                    <option value="">Select an employee…</option>
                    {employees.map((emp) => (
                      <option key={emp.id} value={emp.id}>
                        {emp.first_name} {emp.last_name} · {emp.employee_id}
                      </option>
                    ))}
                  </Select>
                  {employeesLoading && <p className="text-xs text-text-secondary mt-1">Loading employees…</p>}
                </div>
                {selectedEmployeeId && (
                  <Link to={tenantNav.to("/leave")} className="text-xs action-link">← Back to Leave</Link>
                )}
              </div>
            </div>

            {!selectedEmployeeId ? (
              <div className="p-5 text-sm text-text-secondary">Choose an employee above to see their ledger. You can also follow “View ledger →” from the balances table on <Link to={tenantNav.to("/leave")} className="action-link">Leave</Link>.</div>
            ) : ledgerLoading ? (
              <LoadingRegion label="Loading ledger…">
                <TableSkeleton rows={4} cols={6} />
              </LoadingRegion>
            ) : ledgerNotFound ? (
              <div className="p-5">
                <EmptyState title="Ledger — not yet served" description="This is planned on the server — not yet served." />
              </div>
            ) : ledgerError ? (
              <div className="p-5">
                <RetryableAlert err={ledgerError} title="The ledger could not be read" fallback="The ledger could not be read" onRetry={() => window.location.reload()} />
              </div>
            ) : (
              <>
                {balances.length > 0 && (
                  <div className="px-5 py-3 border-b border-border bg-surface-sunken">
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Current balances for {employeeName(Number(selectedEmployeeId))}</p>
                    <div className="flex flex-wrap gap-2">
                      {balances.map((b) => (
                        <span key={b.id} className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1 text-xs">
                          <span className="font-medium">{b.leave_type_name ?? `#${b.leave_type_id}`}</span>
                          <span className="text-text-secondary">{b.entitlement_year}</span>
                          <span className="font-semibold">{b.available_days}d available</span>
                          <span className="text-text-secondary">({b.entitled_days} entitled · {b.used_days} used)</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {ledger.length === 0 ? (
                  <div className="p-5 text-sm text-text-secondary">No ledger entries for this employee — an entitlement or a leave movement has not yet been recorded.</div>
                ) : (
                  <Table
                    columns={[
                      { key: "date", header: "Date", accessor: (entry) => <span className="whitespace-nowrap">{fmtDateTime(entry.created_at)}</span> },
                      { key: "type", header: "Entry type", accessor: (entry) => <StatusPill status={entry.entry_type} /> },
                      { key: "leavetype", header: "Leave type", accessor: (entry) => <span>{leaveTypeName(entry.leave_type_id)} <span className="text-xs text-text-secondary">({entry.entitlement_year})</span></span> },
                      { key: "days", header: "Days", accessor: (entry) => (
                        <span className={`num tabular-nums font-medium ${entry.signed_days < 0 ? "text-error-text" : entry.signed_days > 0 ? "text-success-text" : ""}`}>
                          {entry.signed_days > 0 ? `+${entry.signed_days}` : String(entry.signed_days)}
                        </span>
                      ) },
                      { key: "balance", header: "Balance after", accessor: (entry) => entry.running_balance, cellClassName: "num tabular-nums font-semibold" },
                      { key: "reason", header: "Reason / description", accessor: (entry) => <span className="max-w-[260px] truncate text-xs text-text-secondary" title={entry.description ?? ""}>{entry.description ?? "\u2014"}</span> },
                    ]}
                    data={ledger}
                    keyAccessor={(entry) => entry.id}
                    caption="Leave ledger for the selected employee"
                    sortable={false}
                  />
                )}
              </>
            )}
          </>
        )}
      </SectionCard>

      {/* Reconciliation */}
      <SectionCard
        compact
        title="Reconciliation"
        description="The balances of this deployment against the ledgers that explain them — numbers that disagree and nothing else."
      >
        {!canManager ? (
          <div className="p-5">
            <EmptyState
              title="Reconciliation requires Manager"
              description="Reconciliation is limited to SuperAdmin, HR and Manager — the roles that may see leave and approve it. Your role does not read reconciliation reports."
            />
          </div>
        ) : (
          <>
            <div className="p-5 border-b border-border">
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[120px]">
                  <label htmlFor="recon-year" className="block text-xs font-medium text-text-secondary mb-1">Year</label>
                  <Input
                    id="recon-year"
                    type="number"
                    min="2000"
                    max="2100"
                    placeholder="All years"
                    value={reconYear}
                    onChange={(e) => setReconYear(e.target.value)}
                  />
                </div>
                <Button size="sm" onClick={() => void loadReconciliation()} loading={reconLoading}>
                  Run reconciliation
                </Button>
                <span className="text-xs text-text-secondary">Scoped to the reporting line your role may see. Add an employee filter via the ledger picker above.</span>
              </div>
            </div>
            {reconLoading ? (
              <LoadingRegion label="Loading reconciliation…">
                <TableSkeleton rows={4} cols={6} />
              </LoadingRegion>
            ) : reconNotFound ? (
              <div className="p-5">
                <EmptyState title="Reconciliation — not yet served" description="This is planned on the server — not yet served." />
              </div>
            ) : reconError ? (
              <div className="p-5">
                <RetryableAlert err={reconError} title="The reconciliation report could not be read" fallback="The reconciliation report could not be read" onRetry={() => window.location.reload()} />
              </div>
            ) : !reconciliation ? (
              <div className="p-5 text-sm text-text-secondary">No reconciliation has been loaded yet. The report is generated on demand and scoped to your visibility.</div>
            ) : (
              <div className="p-5 space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <div className="card p-3 text-center">
                    <p className="text-xs text-text-secondary">Balances</p>
                    <p className="text-[var(--font-size-lg)] font-semibold">{reconciliation.summary.balances}</p>
                  </div>
                  <div className="card p-3 text-center">
                    <p className="text-xs text-text-secondary">In sync</p>
                    <p className="text-[var(--font-size-lg)] font-semibold text-success-text">{reconciliation.summary.in_sync}</p>
                  </div>
                  <div className="card p-3 text-center">
                    <p className="text-xs text-text-secondary">Out of sync</p>
                    <p className="text-[var(--font-size-lg)] font-semibold text-error-text">{reconciliation.summary.out_of_sync}</p>
                  </div>
                  <div className="card p-3 text-center">
                    <p className="text-xs text-text-secondary">No ledger</p>
                    <p className="text-[var(--font-size-lg)] font-semibold text-warning-text">{reconciliation.summary.no_ledger}</p>
                  </div>
                  <div className="card p-3 text-center">
                    <p className="text-xs text-text-secondary">Difference</p>
                    <p className="text-[var(--font-size-lg)] font-semibold">{reconciliation.summary.difference_days}d</p>
                  </div>
                </div>
                {reconciliation.rows.length === 0 ? (
                  <p className="text-sm text-text-secondary">No balances matched the current filter.</p>
                ) : (
                  <Table
                    columns={[
                      { key: "employee", header: "Employee", accessor: (r) => employeeName(r.employee_id) },
                      { key: "type", header: "Leave type", accessor: (r) => r.leave_type_name ?? `#${r.leave_type_id}` },
                      { key: "year", header: "Year", accessor: (r) => r.entitlement_year, cellClassName: "num" },
                      { key: "cached", header: "Cached", accessor: (r) => r.cached_available_days, cellClassName: "num tabular-nums" },
                      { key: "ledger", header: "Ledger", accessor: (r) => r.ledger_available_days, cellClassName: "num tabular-nums" },
                      { key: "diff", header: "Difference", accessor: (r) => (
                        <span className={`num tabular-nums font-medium ${r.difference_days !== 0 ? "text-error-text" : ""}`}>{r.difference_days}</span>
                      ) },
                      { key: "state", header: "State", accessor: (r) => <StatusPill status={r.state} /> },
                    ]}
                    data={reconciliation.rows}
                    keyAccessor={(r) => r.balance_id}
                    caption="Leave reconciliation rows"
                    sortable={false}
                  />
                )}
                {reconciliation.year && <p className="text-xs text-text-secondary">Year {reconciliation.year}</p>}
              </div>
            )}
          </>
        )}
      </SectionCard>

      {/* Payroll input */}
      <SectionCard
        compact
        title="Payroll input"
        description="The approved leave of a period, quantified, for the payroll lane — leave that straddles two periods is split between them."
      >
        {!canReports ? (
          <div className="p-5">
            <EmptyState
              title="Payroll input requires HR/PayrollViewer"
              description="Payroll input is limited to SuperAdmin, HR and PayrollViewer — the organisation-wide figures and read-only payroll. Your role does not read payroll input."
            />
          </div>
        ) : (
          <>
            <div className="p-5 border-b border-border">
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[150px]">
                  <label htmlFor="pi-start" className="block text-xs font-medium text-text-secondary mb-1">Period start</label>
                  <Input
                    id="pi-start"
                    type="date"
                    value={periodStart}
                    onChange={(e) => setPeriodStart(e.target.value)}
                  />
                </div>
                <div className="min-w-[150px]">
                  <label htmlFor="pi-end" className="block text-xs font-medium text-text-secondary mb-1">Period end</label>
                  <Input
                    id="pi-end"
                    type="date"
                    value={periodEnd}
                    onChange={(e) => setPeriodEnd(e.target.value)}
                  />
                </div>
                <Button size="sm" onClick={() => void loadPayrollInput()} loading={payrollLoading}>
                  Query payroll input
                </Button>
                {payrollError && <span className="text-xs text-error-text" role="alert">{payrollError}</span>}
              </div>
            </div>
            {payrollLoading ? (
              <LoadingRegion label="Loading payroll input…">
                <TableSkeleton rows={4} cols={5} />
              </LoadingRegion>
            ) : payrollNotFound ? (
              <div className="p-5">
                <EmptyState title="Payroll input — not yet served" description="This is planned on the server — not yet served." />
              </div>
            ) : payrollError && !payrollInput ? (
              <div className="p-5">
                <Alert tone="error">{payrollError}</Alert>
              </div>
            ) : !payrollInput ? (
              <div className="p-5 text-sm text-text-secondary">Choose a start and end date above and query — the leave that falls inside the period is returned, split across periods when it straddles.</div>
            ) : (
              <div className="p-5 space-y-4">
                <div className="flex flex-wrap gap-3 items-center">
                  <span className="text-sm">
                    Period {fmtDate(payrollInput.period_start)} → {fmtDate(payrollInput.period_end)}
                  </span>
                  <span className="badge badge-slate">{payrollInput.total_days}d total</span>
                  <span className="text-xs text-text-secondary">{payrollInput.entries.length} entries</span>
                </div>
                {payrollInput.entries.length === 0 ? (
                  <p className="text-sm text-text-secondary">No approved leave falls inside this period.</p>
                ) : (
                  <Table
                    columns={[
                      { key: "employee", header: "Employee", accessor: (e) => employeeName(e.employee_id) },
                      { key: "type", header: "Leave type", accessor: (e) => <span className="font-mono text-xs">{e.leave_type_code}</span> },
                      { key: "dates", header: "Dates", accessor: (e) => <span className="whitespace-nowrap">{fmtDate(e.start_date)} {"\u2192"} {fmtDate(e.end_date)}</span> },
                      { key: "qty", header: "Quantity", accessor: (e) => `${e.quantity_days}d`, cellClassName: "num tabular-nums font-medium" },
                      { key: "paid", header: "Paid", accessor: (e) => e.is_paid ? <span className="badge badge-green">Paid</span> : <span className="badge badge-slate">Unpaid</span> },
                    ]}
                    data={payrollInput.entries}
                    keyAccessor={(e) => e.leave_request_id}
                    caption="Approved leave for the payroll period"
                    sortable={false}
                  />
                )}
              </div>
            )}
          </>
        )}
      </SectionCard>
    </Layout>
  )
}
