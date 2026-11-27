import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useTenantNav } from "@/lib/tenantPath"
import { Layout } from "@/components/Layout"
import {
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  KPICard,
  StatusPill, Table } from "@/components/ui"
import { NeedsAction, type NeedItem } from "@/components/home/NeedsAction"
import { IconChart, IconFile, IconWallet } from "@/components/icons"
import api from "@/lib/api"
import { useTenant } from "@/context/TenantContext"
import { formatCurrency } from "@/lib/format"

interface PayRun { id: number; status: string; total_gross?: number; total_net?: number; headcount?: number; period_id?: number }
interface Payslip { id: number; employee_id: number; net_pay?: number; status: string; period_start: string; period_end: string }

// D3 (portals-completion): no sparkline/trend props on portal KPIs — there is
// no backend aggregation for deltas, so every KPI shows a live value + hint.
// Gross pay is NOT derived client-side (net×1.3 was a fake); totals come from
// the runs/payslips endpoints only.

export default function PayrollHome() {
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const { tenant } = useTenant()
  const localeOpts = { locale: tenant?.locale, timeZone: tenant?.timezone }
  const currency = tenant?.currency || undefined
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [runs, setRuns] = useState<PayRun[]>([])
  const [payslips, setPayslips] = useState<Payslip[]>([])
  const [labor, setLabor] = useState<any>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [r, p, l] = await Promise.all([
          api.get("/payroll/runs").catch(() => ({ data: [] })),
          api.get("/payroll/payslips").catch(() => ({ data: [] })),
          api.get("/reports/labor-cost").catch(() => ({ data: null })),
        ])
        if (cancelled) return
        setRuns(r.data || [])
        setPayslips(p.data || [])
        setLabor(l.data)
      } catch {
        if (!cancelled) setError("We couldn't load the payroll workspace.")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const draftRuns = runs.filter((r) => r.status === "Draft").length
  const processingRuns = runs.filter((r) => r.status === "Processing").length
  const pendingApprovals = runs.filter((r) => r.status === "Draft" || r.status === "Processing").length
  const totalPayslips = payslips.length
  const totalNet = payslips.reduce((s, p) => s + (p.net_pay ?? 0), 0)

  const needs: NeedItem[] = [
    { id: "draft-runs", label: "Pay runs in draft", count: draftRuns, description: "Pay runs awaiting processing", actionLabel: "Process", onAction: () => { navigate(tenantNav.to("/platform/payroll/runs")) }, tone: "amber" },
    { id: "processing", label: "Runs processing", count: processingRuns, description: "Pay runs currently being processed", actionLabel: "Review", onAction: () => { navigate(tenantNav.to("/platform/payroll/runs")) }, tone: "brand" },
  ]

  if (loading) {
    return (
      <Layout>
        <PageHeader compact icon={<IconWallet />} title="Payroll" description="Your payroll workspace." />
        <LoadingRegion label="Loading payroll data">
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
        icon={<IconWallet />}
        title="Payroll"
        description="Pay run status, payslip summary, and labour cost analysis."
      />

      {error && <Alert tone="error">{error}</Alert>}

      {needs.length > 0 && <NeedsAction title="Needs your action" items={needs} emptyMessage="No pending payroll actions." />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-0">
        <KPICard
          label="Total Pay Runs"
          value={runs.length}
          hint={`${draftRuns} draft, ${processingRuns} processing`}
          icon={<IconWallet className="w-5 h-5" />}
          tone="brand"
        />
        <KPICard
          label="Pending Approval"
          value={pendingApprovals}
          hint="Requires action"
          icon={<IconFile className="w-5 h-5" />}
          tone="amber"
        />
        <KPICard
          label="Payslips Issued"
          value={totalPayslips}
          hint="This period"
          icon={<IconFile className="w-5 h-5" />}
          tone="green"
        />
        <KPICard
          label="Total Net Pay"
          value={formatCurrency(totalNet, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          hint={`Across ${totalPayslips} payslip${totalPayslips !== 1 ? "s" : ""}`}
          icon={<IconChart className="w-5 h-5" />}
          tone="violet"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-0">
        <SectionCard compact icon={<IconWallet />} title="Pay runs" description="Recent payroll runs and their status.">
          {runs.length === 0 ? (
            <EmptyState title="No pay runs" description="Create a pay run from payroll setup." />
          ) : (
            <Table
              columns={[
                { key: "run", header: "Run", accessor: (r) => <span className="font-medium"><Link className="action-link" to={tenantNav.to(`/platform/payroll/runs/${r.id}`)}>#{r.id}</Link></span> },
                { key: "status", header: "Status", accessor: (r) => <StatusPill status={r.status} /> },
                {
                  key: "gross",
                  header: "Gross",
                  accessor: (r) => formatCurrency(r.total_gross, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }),
                  cellClassName: "num",
                },
                {
                  key: "net",
                  header: "Net",
                  accessor: (r) => formatCurrency(r.total_net, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }),
                  cellClassName: "num font-semibold",
                },
                { key: "headcount", header: "Headcount", accessor: (r) => r.headcount ?? "—", cellClassName: "num" },
              ]}
              data={runs.slice(0, 8)}
              keyAccessor={(r) => r.id}
              caption="Pay runs"
              sortable={false}
            />
          )}
          <div className="flex flex-wrap justify-end gap-x-4 gap-y-1 px-5 py-3">
            <button className="action-link" onClick={() => { navigate(tenantNav.to("/platform/payroll/runs")) }}>View all runs</button>
            <button className="action-link" onClick={() => { navigate(tenantNav.to("/platform/payroll/setup")) }}>Pay setup</button>
          </div>
        </SectionCard>

        <SectionCard compact icon={<IconFile />} title="Labour cost" description="Monthly payroll cost by department.">
          {!labor?.by_department || labor.by_department.length === 0 ? (
            <EmptyState title="No labour cost data" description="Cost appears once payroll is processed." />
          ) : (
            <Table
              columns={[
                { key: "department", header: "Department", accessor: (r: any) => r.department || "(none)" },
                { key: "staff", header: "Staff", accessor: (r: any) => r.employees, cellClassName: "num" },
                {
                  key: "cost",
                  header: "Monthly cost",
                  accessor: (r: any) => formatCurrency(r.monthly_cost, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }),
                  cellClassName: "num font-medium",
                },
              ]}
              data={[...labor.by_department.map((r: any) => ({ ...r })), { department: "Total", employees: "", monthly_cost: labor.monthly_payroll ?? 0 }]}
              keyAccessor={(r: any) => r.department || "none"}
              caption="Labour cost by department"
              sortable={false}
            />
          )}
          <div className="flex justify-end px-5 py-3">
            <button className="action-link" onClick={() => { navigate(tenantNav.to("/platform/payroll/overview")) }}>Open payroll overview</button>
          </div>
        </SectionCard>
      </div>

      <div className="card p-4 text-xs text-fg-muted flex flex-wrap items-center gap-x-3 gap-y-1">
        <StatusPill status="Payroll workspace" />
        <span>Open a run to process, approve or finalize it (SuperAdmin and HR; PayrollViewer reads).</span>
        <button className="action-link" onClick={() => { navigate(tenantNav.to("/platform/payroll/runs")) }}>Open runs</button>
      </div>
    </Layout>
  )
}
