import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTenantNav } from "@/lib/tenantPath"
import { Layout } from "@/components/Layout"
import {
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  KPICard,
} from "@/components/ui"
import { NeedsAction, type NeedItem } from "@/components/home/NeedsAction"
import {
  IconExit,
  IconInbox,
  IconShield,
  IconTarget,
  IconUsers,
} from "@/components/icons"
import api from "@/lib/api"
import { StatusPill } from "@/components/ui/status-pill"

interface HrCase { id: number; subject: string; status: string; priority: string; category: string }
interface Requisition { id: number; req_number: string; title: string; status: string; openings: number }
interface Termination { id: number; employee_id: number; status: string; last_working_date: string; termination_type: string }

// D3 (portals-completion): no sparkline/trend props on portal KPIs — there is
// no backend aggregation for deltas, so every KPI shows a live value + hint.

export default function HRHome() {
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [cases, setCases] = useState<HrCase[]>([])
  const [requisitions, setRequisitions] = useState<Requisition[]>([])
  const [terminations, setTerminations] = useState<Termination[]>([])
  const [headcount, setHeadcount] = useState<any>(null)
  const [violations, setViolations] = useState<any[]>([])
  const [audit, setAudit] = useState<any[]>([])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [c, r, t, h, v, a] = await Promise.all([
          api.get("/core-hr/cases").catch(() => ({ data: [] })),
          api.get("/requisitions/").catch(() => ({ data: [] })),
          api.get("/offboarding/terminations").catch(() => ({ data: [] })),
          api.get("/reports/headcount").catch(() => ({ data: null })),
          api.get("/compliance/compliance-violations").catch(() => ({ data: [] })),
          api.get("/reports/audit?limit=10").catch(() => ({ data: [] })),
        ])
        if (cancelled) return
        setCases(c.data || [])
        setRequisitions(r.data || [])
        setTerminations(t.data || [])
        setHeadcount(h.data)
        setViolations(v.data || [])
        setAudit(a.data || [])
      } catch {
        if (!cancelled) setError("We couldn't load the HR command center.")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const openCases = cases.filter((c) => c.status === "Open" || c.status === "In Progress").length
  const openReqs = requisitions.filter((r) => r.status === "Open").length
  const activeTerms = terminations.filter((t) => t.status !== "Completed" && t.status !== "Cancelled").length
  const openViolations = violations.filter((v) => v.status === "Open").length
  const totalHeadcount = headcount?.total ?? headcount?.by_status?.Active ?? 0
  const deptCount = (headcount?.by_department || []).length

  const needs: NeedItem[] = [
    { id: "cases", label: "Open HR cases", count: openCases, description: "Employee cases needing resolution", actionLabel: "Review", onAction: () => { navigate(tenantNav.to("/admin/er-cases")) }, tone: "rose" },
    { id: "requisitions", label: "Open requisitions", count: openReqs, description: "Roles awaiting candidates or approval", actionLabel: "View", onAction: () => { navigate(tenantNav.to("/recruiting")) }, tone: "brand" },
    { id: "violations", label: "Compliance violations", count: openViolations, description: "Policy or rule violations needing attention", actionLabel: "Review", onAction: () => { navigate(tenantNav.to("/platform/compliance")) }, tone: "rose" },
    { id: "terminations", label: "Terminations in progress", count: activeTerms, description: "Exit checklists not yet complete", actionLabel: "View", onAction: () => { navigate(tenantNav.to("/offboarding")) }, tone: "amber" },
  ]

  if (loading) {
    return (
      <Layout>
        <PageHeader compact icon={<IconUsers />} title="HR Command Center" description="Your workforce action inbox." />
        <LoadingRegion label="Loading HR data">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-0">
            {Array.from({ length: 8 }).map((_, i) => <div key={i} className="skeleton h-28" />)}
          </div>
        </LoadingRegion>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader
        compact
        icon={<IconUsers />}
        title="HR Command Center"
        description="Action inbox, headcount snapshot, and recent hires and exits."
      />

      {error && <Alert tone="error">{error}</Alert>}

      {needs.length > 0 && <NeedsAction title="Needs your action" items={needs} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-0">
        <KPICard
          label="Total Headcount"
          value={totalHeadcount}
          hint={`${deptCount} departments`}
          icon={<IconUsers className="w-5 h-5" />}
          tone="brand"
        />
        <KPICard
          label="Open HR Cases"
          value={openCases}
          hint={`${cases.length} total`}
          icon={<IconInbox className="w-5 h-5" />}
          tone="rose"
        />
        <KPICard
          label="Open Requisitions"
          value={openReqs}
          hint={`${requisitions.length} total`}
          icon={<IconTarget className="w-5 h-5" />}
          tone="amber"
        />
        <KPICard
          label="Compliance Violations"
          value={openViolations}
          hint={`${violations.length} total`}
          icon={<IconShield className="w-5 h-5" />}
          tone="violet"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-0">
        <SectionCard compact icon={<IconUsers />} title="Headcount by department" description="Workforce composition across the organisation.">
          <div className="flex justify-end px-5 pt-3">
            <button className="action-link" onClick={() => { navigate(tenantNav.to("/admin/headcount-cost")) }}>View cost report</button>
          </div>
          {!headcount?.by_department || headcount.by_department.length === 0 ? (
            <EmptyState title="No headcount data" description="Headcount appears once employees are assigned to departments." />
          ) : (
            <div className="table-scroll">
              <table className="table-base table-compact table-striped">
                <caption className="sr-only">Headcount by department</caption>
                <thead>
                  <tr>
                    <th scope="col">Department</th>
                    <th scope="col" className="num">Employees</th>
                  </tr>
                </thead>
                <tbody>
                  {headcount.by_department.map((r: any) => (
                    <tr key={r.department || "none"}>
                      <td>{r.department || "(none)"}</td>
                      <td className="num font-semibold">{r.employees}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard compact icon={<IconInbox />} title="Recent activity" description="Latest changes across the workspace.">
          {audit.length === 0 ? (
            <EmptyState title="No activity yet" description="Actions will appear here as they happen." />
          ) : (
            <ul className="divide-y divide-border-subtle">
              {audit.slice(0, 8).map((a: any) => (
                <li key={a.id} className="flex items-center gap-3 px-5 py-3 hover:bg-surface-hover">
                  <span className="text-xs text-fg-muted whitespace-nowrap w-32 shrink-0">{a.created_at ? new Date(a.created_at).toLocaleDateString() : "—"}</span>
                  <span className="text-sm text-fg flex-1 truncate">{a.actor_name || "System"} · {a.action}</span>
                  <span className="text-xs text-fg-muted shrink-0">{a.entity_type}</span>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <SectionCard compact icon={<IconExit />} title="Recent terminations" description="Exits in progress or completed.">
          {terminations.length === 0 ? (
            <EmptyState title="No terminations" description="Exit records will appear here." />
          ) : (
            <div className="table-scroll">
              <table className="table-base table-compact table-striped">
                <caption className="sr-only">Recent terminations</caption>
                <thead>
                  <tr>
                    <th scope="col">Employee</th>
                    <th scope="col">Last day</th>
                    <th scope="col">Type</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {terminations.slice(0, 6).map((t) => (
                    <tr key={t.id}>
                      <td>#{t.employee_id}</td>
                      <td className="whitespace-nowrap">{t.last_working_date}</td>
                      <td>{t.termination_type}</td>
                      <td><StatusPill status={t.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="flex justify-end px-5 py-3">
            <button className="action-link" onClick={() => { navigate(tenantNav.to("/offboarding")) }}>View all exits</button>
          </div>
        </SectionCard>

        <SectionCard compact icon={<IconTarget />} title="Open requisitions" description="Roles currently being recruited.">
          {requisitions.filter((r) => r.status === "Open").length === 0 ? (
            <EmptyState title="No open requisitions" description="Create a requisition to start hiring." />
          ) : (
            <ul className="divide-y divide-border-subtle">
              {requisitions.filter((r) => r.status === "Open").slice(0, 6).map((r) => (
                <li key={r.id} className="flex items-center gap-3 px-5 py-3 hover:bg-surface-hover">
                  <span className="text-sm font-medium text-fg flex-1 truncate">{r.title}</span>
                  <span className="text-xs text-fg-muted">{r.openings} opening{r.openings !== 1 ? "s" : ""}</span>
                  <button className="action-link" onClick={() => { navigate(tenantNav.to("/recruiting")) }}>View</button>
                </li>
              ))}
            </ul>
          )}
          <div className="flex justify-end px-5 py-3">
            <button className="action-link" onClick={() => { navigate(tenantNav.to("/recruiting")) }}>View all requisitions</button>
          </div>
        </SectionCard>
      </div>

      <div className="card p-4 text-xs text-fg-muted flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="font-semibold text-fg">Payroll prep</span>
        <button className="action-link" onClick={() => { navigate(tenantNav.to("/platform/payroll/setup")) }}>Payroll setup</button>
        <button className="action-link" onClick={() => { navigate(tenantNav.to("/platform/payroll/runs")) }}>Pay runs</button>
      </div>
    </Layout>
  )
}
