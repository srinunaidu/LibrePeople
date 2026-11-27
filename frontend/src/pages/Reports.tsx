import { useEffect, useState, type ChangeEvent } from "react"
import { Layout } from "@/components/Layout"
import {
  Button,
  Table,
  Alert,
  CardSkeleton,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  KPICard,
  TableSkeleton, RetryableAlert} from "@/components/ui"
import { IconChart, IconRefresh, IconShield, IconUsers, IconWallet } from "@/components/icons"
import api, { errorMessage } from "@/lib/api"
import { SavedViewsSection, SchedulesSection } from "@/pages/reports/ReportPersonalization"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { formatCurrency, formatDateTime, type LocaleOptions } from "@/lib/format"
import type { AuditFirstBroken, AuditLog, AuditVerification } from "@/types"

interface DashboardData {
  employees: { active: number; terminated: number; total: number }
  recruiting: { open_requisitions: number; candidates: number; offers: number }
  approvals: { pending_leave: number; pending_timesheets: number; pending_shift_swaps: number }
  attendance_today: { present: number; total_hours: number; overtime_hours: number }
  recent_audit: AuditLog[]
}

function formatTimestamp(value?: string, options?: LocaleOptions) {
  return formatDateTime(value, options)
}

/**
 * What a broken link means, in the operator's language.
 *
 * The reason is the server's stable code, not prose: the screen decides how
 * to say it, and a code it does not know is still shown rather than hidden.
 */
function brokenSentence(broken?: AuditFirstBroken | null): string {
  if (!broken) return "The chain did not verify."
  const where = broken.id ? `Entry #${broken.id}` : `The gap at position ${broken.index}`
  switch (broken.reason) {
    case "hash_mismatch":
      return `${where} was edited after it was written.`
    case "missing_predecessor":
      return `${where} does not follow the entry before it — a row was inserted, removed or reordered.`
    case "head_mismatch":
      return "The last entries do not match the recorded head — entries were removed from the end, or the head was rewritten."
    default:
      return `${where} did not verify (${broken.reason}).`
  }
}

function Bar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-2.5">
      <div className="h-1.5 w-16 rounded-full bg-surface-inset overflow-hidden shrink-0">
        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-text-secondary tabular-nums w-9 text-right">{pct}%</span>
    </div>
  )
}

interface MovementFilters {
  from: string
  to: string
  year: string
  entity_id: string
  department_id: string
  location_id: string
}

const EMPTY_FILTERS: MovementFilters = { from: "", to: "", year: "", entity_id: "", department_id: "", location_id: "" }

/** Workforce movement (joiners / leavers / attrition) with a filter bar and a team view (LP-REP-003). */
function MovementSection({ teamOnly }: { teamOnly: boolean }) {
  const { user } = useAuth()
  const [filters, setFilters] = useState<MovementFilters>(EMPTY_FILTERS)
  const [joiners, setJoiners] = useState<any[] | null>(null)
  const [leavers, setLeavers] = useState<any[] | null>(null)
  const [attrition, setAttrition] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)
  const [mvError, setMvError] = useState<unknown | null>(null)

  const params = () => {
    const p: Record<string, string> = {}
    if (filters.from) p.from = filters.from
    if (filters.to) p.to = filters.to
    if (filters.entity_id) p.entity_id = filters.entity_id
    if (filters.department_id) p.department_id = filters.department_id
    if (filters.location_id) p.location_id = filters.location_id
    return p
  }

  const apply = async () => {
    setLoading(true)
    setMvError(null)
    try {
      const [j, l, a] = await Promise.all([
        api.get("/reports/joiners", { params: params() }),
        api.get("/reports/leavers", { params: params() }),
        api.get("/reports/attrition", { params: { ...(filters.year ? { year: filters.year } : {}), entity_id: filters.entity_id || undefined, department_id: filters.department_id || undefined, location_id: filters.location_id || undefined } }),
      ])
      setJoiners(j.data.rows ?? [])
      setLeavers(l.data.rows ?? [])
      setAttrition(a.data)
    } catch (err) {
      setMvError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    apply()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const download = async (which: "joiners" | "leavers" | "attrition", fmt: "csv" | "xlsx") => {
    try {
      const response = await api.get(`/reports/${which}`, {
        params: which === "attrition"
          ? { ...(filters.year ? { year: filters.year } : {}), format: fmt }
          : { ...params(), format: fmt },
        responseType: "blob",
      })
      const url = URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement("a")
      link.href = url
      link.download = `report_${which}.${fmt}`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setMvError(err)
    }
  }

  const set = (key: keyof MovementFilters) => (e: ChangeEvent<HTMLInputElement>) =>
    setFilters((f) => ({ ...f, [key]: e.target.value }))

  return (
    <SectionCard compact icon={<IconUsers />} title={teamOnly ? "Team movement" : "Workforce movement"}
      description={teamOnly
        ? `Joiners, leavers and attrition scoped to your reporting line${user?.role ? ` (${user.role})` : ""} — the same filters HQ uses, limited to the people you manage.`
        : "Joiners, leavers and attrition with entity, department and location filters. Exports are masked and audit-logged."}
      actions={
        <div className="flex gap-2">
          <Button variant="secondary" type="button" onClick={() => download("joiners", "csv")} disabled={loading || !joiners}>Joiners CSV</Button>
          <Button variant="secondary" type="button" onClick={() => download("leavers", "csv")} disabled={loading || !leavers}>Leavers CSV</Button>
        </div>
      }>
      <form className="flex flex-wrap gap-2 px-5 pt-4" onSubmit={(e) => { e.preventDefault(); apply() }}
        aria-label="Movement filters">
        <label className="text-xs">From <input type="date" value={filters.from} onChange={set("from")} className="input" aria-label="From date" /></label>
        <label className="text-xs">To <input type="date" value={filters.to} onChange={set("to")} className="input" aria-label="To date" /></label>
        <label className="text-xs">Year <input type="number" min={1900} max={2100} value={filters.year} onChange={set("year")} className="input w-24" aria-label="Attrition year" placeholder="2026" /></label>
        {!teamOnly && (
          <>
            <label className="text-xs">Entity ID <input type="number" value={filters.entity_id} onChange={set("entity_id")} className="input w-24" aria-label="Legal entity ID" /></label>
            <label className="text-xs">Dept ID <input type="number" value={filters.department_id} onChange={set("department_id")} className="input w-24" aria-label="Department ID" /></label>
            <label className="text-xs">Location ID <input type="number" value={filters.location_id} onChange={set("location_id")} className="input w-24" aria-label="Location ID" /></label>
          </>
        )}
        <Button variant="primary" className="self-end" type="submit" disabled={loading}>{loading ? "Loading…" : "Apply"}</Button>
      </form>
      <div className="px-5 py-4" aria-live="polite">
        {mvError ? (
          <RetryableAlert err={mvError} title="Movement reports unavailable" fallback="Movement reports unavailable." />
        ) : loading ? (
          <TableSkeleton rows={4} cols={3} />
        ) : (
          <>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <KPICard tone="green" label="Joiners" value={joiners?.length ?? 0} hint="Hired in range" />
              <KPICard tone="amber" label="Leavers" value={leavers?.length ?? 0} hint="Terminated in range" />
              <KPICard tone="brand" label="Attrition" value={attrition ? `${attrition.attrition_pct}%` : "—"} hint={attrition ? `${attrition.leavers} leavers · avg headcount ${attrition.average_headcount}` : "Annual"} />
            </div>
            {(joiners?.length ?? 0) + (leavers?.length ?? 0) === 0 && (
              <EmptyState title="No movement in range" description="Nobody joined or left under these filters in the selected period." />
            )}
          </>
        )}
      </div>
    </SectionCard>
  )
}

export default function Reports() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const localeOpts: LocaleOptions = {
    locale: tenant?.locale,
    timeZone: tenant?.timezone,
  }
  const currency = tenant?.currency || undefined
  // Mirrors backend/app/api/v1/endpoints/reports.py: dashboard, headcount,
  // leave and labour-cost are REPORTS_ROLES (SuperAdmin, HR, PayrollViewer
  // — `:20/:29/:37/:45`); the audit trail is ADMIN_ROLES (`:63`). A Manager
  // is outside REPORTS_ROLES and gets a role card instead of four blank
  // cards; a PayrollViewer still sees the org stats even though
  // /reports/audit answers 403.
  const orgRole = ["SuperAdmin", "HR", "PayrollViewer"].includes(user?.role ?? "")
  const isAdmin = user?.role === "SuperAdmin" || user?.role === "HR"

  const [dash, setDash] = useState<DashboardData | null>(null)
  const [headcount, setHeadcount] = useState<any>(null)
  const [leave, setLeave] = useState<any>(null)
  const [labor, setLabor] = useState<any>(null)
  const [audit, setAudit] = useState<AuditLog[]>([])
  // Which of the five report sources failed, so the audit trail's role
  // restriction never blanks the headcount, leave or labour cards.
  type LoadKey = "dashboard" | "headcount" | "leave" | "labor" | "audit"
  const [failed, setFailed] = useState<LoadKey[]>([])
  const [error, setError] = useState<unknown | null>(null)
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading")

  // The chain check is an action, not a page load. A walk of the whole log on
  // every visit is a cost the customer did not ask for, and a stored verdict
  // would be a claim the screen cannot support: the answer belongs to one
  // request at one moment.
  const [chain, setChain] = useState<AuditVerification | null>(null)
  const [chainChecking, setChainChecking] = useState(false)
  const [chainError, setChainError] = useState<unknown | null>(null)

  const verifyChain = async () => {
    if (chainChecking) return
    setChainChecking(true)
    setChainError(null)
    try {
      const response = await api.get<AuditVerification>("/admin/audit/verify")
      setChain(response.data)
    } catch (err) {
      setChain(null)
      setChainError(
        `${errorMessage(err, "The chain could not be verified.")} Nothing is claimed about the chain until a check succeeds.`,
      )
    } finally {
      setChainChecking(false)
    }
  }

  const load = async () => {
    setStatus("loading")
    setError(null)
    const results = await Promise.allSettled([
      api.get("/reports/dashboard"),
      api.get("/reports/headcount"),
      api.get("/reports/leave"),
      api.get("/reports/labor-cost"),
      api.get("/reports/audit?limit=25"),
    ])
    const keys: LoadKey[] = ["dashboard", "headcount", "leave", "labor", "audit"]
    const failedKeys: LoadKey[] = []
    results.forEach((r, i) => {
      const key = keys[i]
      if (r.status === "fulfilled") {
        const data = r.value.data
        if (key === "dashboard") setDash(data)
        else if (key === "headcount") setHeadcount(data)
        else if (key === "leave") setLeave(data)
        else if (key === "labor") setLabor(data)
        else if (key === "audit") setAudit(data)
      } else {
        failedKeys.push(key)
      }
    })
    setFailed(failedKeys)
    if (failedKeys.includes("dashboard")) {
      // Without the dashboard the page has nothing truthful to show.
      setError(
        "We couldn't load the reports. This is usually a temporary connection problem.",
      )
      setStatus("error")
    } else {
      setStatus("ready")
    }
  }

  useEffect(() => {
    load()
  }, [])

  const deptRows: any[] = headcount?.by_department || []
  const maxDept = deptRows.reduce((m, r) => Math.max(m, Number(r.employees) || 0), 0)
  const laborRows: any[] = labor?.by_department || []
  const maxLabor = laborRows.reduce((m, r) => Math.max(m, Number(r.monthly_cost) || 0), 0)

  const leaveByStatus: [string, number][] = leave?.by_status
    ? Object.entries(leave.by_status).map(([k, v]) => [k, Number(v)] as [string, number])
    : []

  return (
    <Layout>
      <PageHeader compact
        icon={<IconChart />}
        title="Reporting & Analytics"
        description="Workforce composition, leave usage, labour cost and the audit trail."
        actions={
          orgRole ? (
            <Button variant="secondary" type="button" onClick={load} disabled={status === "loading"}>
              <IconRefresh className="w-4 h-4" />
              Refresh
            </Button>
          ) : undefined
        }
      />

      {!orgRole ? (
        user?.role === "Manager" ? (
          /* Team view (LP-REP-003): a manager is outside REPORTS_ROLES and
             never sees org stats — but joiners/leavers/attrition answer 200
             for Manager scoped to the reporting line. */
          <MovementSection teamOnly />
        ) : (
        /* REPORTS_ROLES gate (reports.py:20-45): managers get the team view
           above; associates get an explicit role card — the four org stats
           they never received would otherwise read as four empty modules. */
        <Alert
          tone="error"
          title="Reports are for HR, payroll and the owner role"
        >
          Workforce reports are visible to SuperAdmin, HR and PayrollViewer
          accounts only — your role ({user?.role || "unknown"}) is outside that
          set. As a manager you can see team-level figures in the team views
          (People › Directory, Time &amp; Attendance, Leave).
        </Alert>
        )
      ) : (
        <>
      {status === "error" && !!error && <RetryableAlert err={error} title="The report could not be read" fallback="The report could not be read." onRetry={() => window.location.reload()} />}

      {status === "loading" && (
        <LoadingRegion label="Loading reports">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            {Array.from({ length: 4 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
        </LoadingRegion>
      )}

      {status === "ready" && dash && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
          <KPICard tone="brand" icon={<IconUsers />} label="Active employees" value={dash.employees.active} hint={`${dash.employees.total} total records`} />
          <KPICard tone="violet" label="Open requisitions" value={dash.recruiting.open_requisitions} hint={`${dash.recruiting.candidates} candidates · ${dash.recruiting.offers} offers`} />
          <KPICard tone="amber" label="Pending approvals" value={dash.approvals.pending_leave + dash.approvals.pending_timesheets + dash.approvals.pending_shift_swaps} hint="Leave, timesheets and swaps" />
          <KPICard tone="green" label="Present today" value={dash.attendance_today.present} hint={`${dash.attendance_today.total_hours || 0}h logged`} />
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-5">
        <SectionCard compact icon={<IconUsers />} title="Headcount by department"
          description="Share of total headcount per department.">
          {status === "loading" ? (
            <TableSkeleton rows={4} cols={3} />
          ) : failed.includes("headcount") ? (
            <EmptyState title="Headcount unavailable"
              description="The headcount report could not be loaded — use Reload to retry." />
          ) : deptRows.length === 0 ? (
            <EmptyState title="No headcount data"
              description="Headcount appears once employees are assigned to departments." />
          ) : (
            <Table
              columns={[
                { key: "dept", header: "Department", accessor: (r) => r.department || "(none)" },
                { key: "employees", header: "Employees", accessor: (r) => r.employees, cellClassName: "num font-semibold" },
                { key: "share", header: "Share", accessor: (r) => <Bar value={Number(r.employees) || 0} max={maxDept} />, cellClassName: "num" },
              ]}
              data={deptRows}
              keyAccessor={(r) => r.department || "none"}
              caption="Headcount by department"
              sortable={false}
            />
          )}
        </SectionCard>

        <SectionCard compact icon={<IconChart />} title="Leave"
          description="Request volume by status and day totals.">
          {status === "loading" ? (
            <TableSkeleton rows={4} cols={2} />
          ) : failed.includes("leave") ? (
            <EmptyState title="Leave report unavailable"
              description="The leave report could not be loaded — use Reload to retry." />
          ) : (
            <Table
              columns={[
                { key: "status", header: "Status", accessor: (r) => r.status },
                { key: "requests", header: "Requests", accessor: (r) => r.requests, cellClassName: "num font-semibold" },
              ]}
              data={[
                ...leaveByStatus.map(([k, v]) => ({ status: k, requests: v })),
                { status: "Entitled days", requests: leave?.entitled_days_total ?? 0 },
                { status: "Used days", requests: leave?.used_days_total ?? 0 },
              ]}
              keyAccessor={(r) => r.status}
              caption="Leave requests by status"
              sortable={false}
            />
          )}
        </SectionCard>

        <SectionCard compact icon={<IconWallet />} title="Monthly labour cost"
          description="Payroll cost per department for the current month.">
          {status === "loading" ? (
            <TableSkeleton rows={4} cols={3} />
          ) : failed.includes("labor") ? (
            <EmptyState title="Labour cost unavailable"
              description="The labour-cost report could not be loaded — use Reload to retry." />
          ) : laborRows.length === 0 ? (
            <EmptyState title="No labour cost data"
              description="Cost appears once payroll is processed for a pay run." />
          ) : (
            <Table
              columns={[
                { key: "department", header: "Department", accessor: (r) => r.department || "(none)" },
                { key: "staff", header: "Staff", accessor: (r) => r.employees, cellClassName: "num" },
                {
                  key: "cost",
                  header: "Cost",
                  accessor: (r) => (
                    <span className="font-medium">
                      {formatCurrency(r.monthly_cost, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  ),
                  cellClassName: "num",
                },
              ]}
              data={[...laborRows, { department: "Total", employees: "", monthly_cost: labor?.monthly_payroll ?? 0 }]}
              keyAccessor={(r) => r.department || "none"}
              caption="Monthly labour cost by department"
              sortable={false}
            />
          )}
        </SectionCard>
      </div>

      {/* Workforce movement (LP-REP-003): filter bar + export for org roles. */}
      <div className="mb-5">
        <MovementSection teamOnly={false} />
      </div>

      {/* Saved views + scheduled reports (reporting-personalization): the
          personal layer over the read-only reports above. REPORTS_ROLES
          only — the same gate as the org stats (reports.py:20-45); a
          Manager never reaches these routes (403) and an Associate gets
          the role card instead. */}
      <div className="mb-5">
        <SavedViewsSection />
      </div>
      <div className="mb-5">
        <SchedulesSection />
      </div>

      {/* /reports/audit is ADMIN_ROLES (reports.py:63): a PayrollViewer
          still gets every org stat above, and this card names the reason
          instead of silently listing nothing. */}
      <SectionCard compact icon={<IconShield />} title="Audit trail"
        description={
          isAdmin
            ? "The 25 most recent recorded actions, with actor and entity. The trail is a hash chain; the check below proves it still holds."
            : "The audit trail is an admin record and is not part of every role."
        }
        actions={
          isAdmin ? (
            <Button variant="secondary" type="button"
              onClick={verifyChain}
              disabled={chainChecking}>
              <IconShield className="w-4 h-4" />
              {chainChecking ? "Checking…" : "Verify the chain"}
            </Button>
          ) : undefined
        }>
        {isAdmin && (
          <div className="px-5 py-4 border-b border-border" aria-live="polite">
            {chainChecking ? (
              <p className="text-sm text-text-secondary">Walking every entry in the chain…</p>
            ) : chainError ? (
              <Alert tone="error" title="The chain could not be verified">
                {typeof chainError === "string" ? chainError : "The chain could not be verified. Nothing is claimed about the chain until a check succeeds."}
              </Alert>
            ) : chain ? (
              chain.verified ? (
                <div role="status" className="rounded-lg bg-success-bg border border-success-border px-3.5 py-2.5 text-sm text-success-text">
                  <p className="font-semibold">The chain is intact</p>
                  <p className="mt-1">
                    {chain.checked_entries} entries verified. Head {chain.head} (entry #{chain.head_id}).
                    Record this entry count and head hash outside the database so a rebuilt chain can be compared.
                  </p>
                </div>
              ) : (
                <div role="alert" className="rounded-lg bg-error-bg border border-error-border px-3.5 py-2.5 text-sm text-error">
                  <p className="font-semibold">The chain is broken</p>
                  <p className="mt-1">
                    {chain.first_broken?.reason === "hash_mismatch" && chain.first_broken?.id
                      ? `Entry #${chain.first_broken.id} was edited after it was written. `
                      : chain.first_broken?.reason === "head_mismatch"
                        ? `Entries were removed from the end, or the head was rewritten. `
                        : chain.first_broken?.id
                          ? `Entry #${chain.first_broken.id} does not follow the entry before it — a row was inserted, removed or reordered. `
                          : `The chain does not follow — a row was inserted, removed or reordered. `}
                    {chain.checked_entries} entries verified before the break. Head {chain.head}.
                    Re-running the check does not repair the chain — restore from a known-good anchor.
                  </p>
                </div>
              )
            ) : (
              <p className="text-sm text-text-secondary">
                Every entry carries the hash of the one before it, so an edited or removed row
                breaks the chain at that point. Run the check to see whether it still holds. It
                walks every entry, so it is an action, not something this page does on load.
              </p>
            )}
          </div>
        )}
        {status === "loading" ? (
          <TableSkeleton rows={8} cols={4} />
        ) : failed.includes("audit") ? (
          <EmptyState
            title={isAdmin ? "Audit trail unavailable" : "Not visible for your role"}
            description={
              isAdmin
                ? "The audit trail could not be loaded — use Reload to retry."
                : `The audit trail requires the SuperAdmin or HR role; your role is ${user?.role || "unknown"}. The workforce reports above are unaffected.`
            }
          />
        ) : audit.length === 0 ? (
          <EmptyState title="No activity yet"
            description="Recorded actions will appear here." />
        ) : (
          <Table
            columns={[
              { key: "when", header: "When", accessor: (a) => <span className="whitespace-nowrap text-text-secondary">{formatTimestamp(a.created_at, localeOpts)}</span> },
              { key: "actor", header: "Actor", accessor: (a) => <span className="font-medium">{a.actor_name || "—"}</span> },
              { key: "action", header: "Action", accessor: (a) => a.action },
              { key: "entity", header: "Entity", accessor: (a) => (
                <span className="text-text-secondary">
                  {a.entity_type}
                  {a.entity_id ? ` #${a.entity_id}` : ""}
                </span>
              ) },
            ]}
            data={audit}
            keyAccessor={(a) => a.id}
            caption="Audit trail of the 25 most recent actions"
            sortable={false}
          />
          )}
      </SectionCard>
        </>
      )}
    </Layout>
  )
}