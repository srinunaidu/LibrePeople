import { useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  KPICard,
  StatCard,
} from "@/components/ui"
import { NeedsAction, type NeedItem } from "@/components/home/NeedsAction"
import { IconChart, IconFile, IconWallet, IconTrendingUp } from "@/components/icons"
import api from "@/lib/api"
import { StatusPill } from "@/components/ui/status-pill"
import { useTenant } from "@/context/TenantContext"
import { formatCurrency } from "@/lib/format"

interface PayRun { id: number; status: string; total_gross?: number; total_net?: number; headcount?: number; period_id?: number }
interface Payslip { id: number; employee_id: number; net_pay?: number; status: string; period_start: string; period_end: string }

const mockSparklineData = [45, 52, 48, 55, 52, 58, 55, 62, 58, 65, 62, 68]
const mockPayslipSparkline = [120, 135, 128, 145, 138, 152, 145, 160, 152, 168, 160, 175]

export default function PayrollHome() {
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
  const totalGross = payslips.reduce((s, p) => s + (p.net_pay ?? 0) * 1.3, 0) // approximate

  const needs: NeedItem[] = [
    { id: "draft-runs", label: "Pay runs in draft", count: draftRuns, description: "Pay runs awaiting processing", actionLabel: "Process", onAction: () => { window.location.href = "/platform" }, tone: "amber" },
    { id: "processing", label: "Runs processing", count: processingRuns, description: "Pay runs currently being processed", actionLabel: "Review", onAction: () => { window.location.href = "/platform" }, tone: "brand" },
  ]

  if (loading) {
    return (
      <Layout>
        <PageHeader icon={<IconWallet />} title="Payroll" description="Your payroll workspace." />
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
          sparklineData={mockSparklineData}
          trendValue={15}
          trendLabel="vs last quarter"
        />
        <KPICard
          label="Pending Approval"
          value={pendingApprovals}
          hint="Requires action"
          icon={<IconFile className="w-5 h-5" />}
          tone="amber"
          sparklineData={mockSparklineData}
          trendValue={-5}
          trendLabel="processing"
        />
        <KPICard
          label="Payslips Issued"
          value={totalPayslips}
          hint="This period"
          icon={<IconFile className="w-5 h-5" />}
          tone="green"
          sparklineData={mockPayslipSparkline}
          trendValue={12}
          trendLabel="vs last period"
        />
        <KPICard
          label="Total Net Pay"
          value={formatCurrency(totalNet, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          hint={`Gross: ${formatCurrency(totalGross, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          icon={<IconChart className="w-5 h-5" />}
          tone="violet"
          sparklineData={mockSparklineData}
          trendValue={8}
          trendLabel="payroll growth"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-0">
        <SectionCard compact icon={<IconWallet />} title="Pay runs" description="Recent payroll runs and their status.">
          {runs.length === 0 ? (
            <EmptyState title="No pay runs" description="Create a pay run from the Platform module." />
          ) : (
            <div className="table-scroll">
              <table className="table-base table-compact table-striped">
                <caption className="sr-only">Pay runs</caption>
                <thead>
                  <tr>
                    <th scope="col">Run</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="num">Gross</th>
                    <th scope="col" className="num">Net</th>
                    <th scope="col" className="num">Headcount</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.slice(0, 8).map((r) => (
                    <tr key={r.id}>
                      <td className="font-medium">#{r.id}</td>
                      <td><StatusPill status={r.status} /></td>
                      <td className="num">{formatCurrency(r.total_gross, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className="num font-semibold">{formatCurrency(r.total_net, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className="num">{r.headcount ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard compact icon={<IconFile />} title="Labour cost" description="Monthly payroll cost by department.">
          {!labor?.by_department || labor.by_department.length === 0 ? (
            <EmptyState title="No labour cost data" description="Cost appears once payroll is processed." />
          ) : (
            <div className="table-scroll">
              <table className="table-base table-compact table-striped">
                <caption className="sr-only">Labour cost by department</caption>
                <thead>
                  <tr>
                    <th scope="col">Department</th>
                    <th scope="col" className="num">Staff</th>
                    <th scope="col" className="num">Monthly cost</th>
                  </tr>
                </thead>
                <tbody>
                  {labor.by_department.map((r: any) => (
                    <tr key={r.department || "none"}>
                      <td>{r.department || "(none)"}</td>
                      <td className="num">{r.employees}</td>
                      <td className="num font-medium">{formatCurrency(r.monthly_cost, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    </tr>
                  ))}
                  <tr className="bg-surface-sunken">
                    <td className="font-semibold" colSpan={2}>Total</td>
                    <td className="num font-bold">{formatCurrency(labor.monthly_payroll ?? 0, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>

      <div className="card p-4 text-xs text-fg-muted flex items-center gap-2">
        <span className="badge badge-slate">Read-only</span>
        Payroll data is viewed here. Processing and approval actions are in the Platform module.
      </div>
    </Layout>
  )
}
