/**
 * Payroll overview — the operator's landing surface for payroll (FD-08).
 *
 * Aggregates the served runs into headline cards, lists the most recent
 * runs, and offers quick actions. Nothing here is recalculated in the
 * browser: every figure is what the run recorded.
 */
import { useCallback, useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Layout } from "@/components/Layout"
import {
  Button,
  EmptyState,
  KPICard,
  LoadingRegion,
  PageHeader,
  RetryableAlert,
  SectionCard,
  StatusPill,
  Table,
  TableSkeleton,
} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api from "@/lib/api"
import { useTenantNav } from "@/lib/tenantPath"
import type { PayRunRow } from "@/types"
import { fmtDate, money, PayrollLinks } from "./shared"

/** `REPORTS_ROLES` in `app/api/deps.py`: who may read a pay run. */
const READ_ROLES = ["SuperAdmin", "HR", "PayrollViewer"]

export default function PayrollOverview() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const tenantCurrency = tenant?.currency || "INR"
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const canRead = READ_ROLES.includes(user?.role ?? "")

  const [runs, setRuns] = useState<PayRunRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)

  const load = useCallback(async () => {
    if (!canRead) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError("")
    try {
      const result = await api.get<PayRunRow[]>("/payroll/runs")
      setRuns(result.data)
    } catch (err) {
      setError(err)
      setRuns([])
    } finally {
      setLoading(false)
    }
  }, [canRead])

  useEffect(() => {
    void load()
  }, [load])

  const totals = runs.reduce(
    (acc, run) => ({
      headcount: acc.headcount + run.headcount,
      gross: acc.gross + run.total_gross,
      deductions: acc.deductions + run.total_deductions,
      net: acc.net + run.total_net,
    }),
    { headcount: 0, gross: 0, deductions: 0, net: 0 },
  )

  if (!canRead) {
    return (
      <Layout>
        <PageHeader compact
          title="Payroll overview"
          description="Headcount, gross, deductions and net across the organisation's pay runs."
        />
        <EmptyState
          title="Payroll overview is read by SuperAdmin, HR and PayrollViewer"
          description="Your role does not read the organisation's pay runs."
        />
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader compact
        title="Payroll overview"
        description="Headcount, gross, deductions and net across the organisation's pay runs, with the most recent runs below."
      />

      {error ? (
        <RetryableAlert err={error} title="The pay runs could not be read" fallback="The pay runs could not be read." onRetry={load} />
      ) : null}

      <SectionCard compact
        title="Run summary"
        description="Aggregated from the served pay runs. Money is shown as the server recorded it, with no currency symbol."
      >
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <KPICard tone="brand" label="Headcount" value={totals.headcount} hint="summed over served runs" />
          <KPICard tone="violet" label="Gross" value={money(totals.gross)} hint="summed over served runs" />
          <KPICard tone="teal" label="Deductions" value={money(totals.deductions)} hint="summed over served runs" />
          <KPICard tone="green" label="Net" value={money(totals.net)} hint="summed over served runs" />
        </div>
      </SectionCard>

      {loading ? (
        <LoadingRegion label="Loading pay runs…">
          <TableSkeleton rows={4} cols={6} />
        </LoadingRegion>
      ) : error ? null : runs.length === 0 ? (
        <EmptyState
          title="No pay runs yet"
          description="A run is created for one pay period and one jurisdiction. Nothing is calculated until the run is processed."
          action={<Button onClick={load}>Retry</Button>}
        />
      ) : (
        <SectionCard compact
          title="Recent pay runs"
          description="Newest first, as the server returns them. History shows rule_pack_id/version/jurisdiction/currency per run; IN runs show INR and PT where applicable; each links to recon + export."
        >
          <Table
            columns={[
              { key: "run", header: "Run", accessor: (run) => `#${run.id}` },
              { key: "period", header: "Period", accessor: (run) => `Period #${run.period_id}` },
              {
                key: "jurisdiction",
                header: "Jurisdiction",
                accessor: (run) => (
                  <>{run.jurisdiction ?? "—"}{run.jurisdiction === "IN" && <span className="ml-1 text-xs px-1 py-0.5 rounded border border-[var(--warning-border)] bg-[var(--warning-light)] text-[var(--warning-text)]">IN</span>}</>
                ),
              },
              { key: "pack", header: "Pack", accessor: (run) => <span className="font-mono text-xs">{run.rule_pack_id ? `${run.rule_pack_id} v1.0.0` : "—"}</span> },
              { key: "status", header: "Status", accessor: (run) => <StatusPill status={run.status} dot /> },
              { key: "headcount", header: "Headcount", accessor: (run) => run.headcount, cellClassName: "num tabular-nums" },
              { key: "gross", header: "Gross", accessor: (run) => money(run.total_gross), cellClassName: "num tabular-nums" },
              { key: "net", header: "Net", accessor: (run) => money(run.total_net), cellClassName: "num tabular-nums" },
              { key: "currency", header: "Currency", accessor: (run) => <span className="text-xs">{run.currency || tenantCurrency}</span> },
              { key: "created", header: "Created", accessor: (run) => fmtDate(run.created_at) },
              {
                key: "open",
                header: "",
                accessor: (run) => (
                  <Link
                    to={tenantNav.to(`/platform/payroll/runs/${run.id}`)}
                    className="text-primary hover:underline underline-offset-2"
                  >
                    Open run #{run.id}
                  </Link>
                ),
              },
              {
                key: "links",
                header: "Links",
                accessor: (run) => (
                  <span className="text-xs"><Link to={tenantNav.to(`/platform/payroll/runs/${run.id}`)} className="text-primary hover:underline underline-offset-2">Recon</Link> {run.status === "Approved" ? <span className="text-text-secondary">· Export</span> : null}</span>
                ),
              },
            ]}
            data={runs}
            keyAccessor={(run) => run.id}
            caption="Recent pay runs of this deployment"
            sortable={false}
          />
        </SectionCard>
      )}

      <SectionCard compact
        title="Quick actions"
        description="Create a draft run, or open a run to view its reconciliation."
      >
        <div className="flex flex-wrap gap-3">
          <Button
            onClick={() => navigate(tenantNav.to("/platform/payroll/runs"))}
          >
            Create run
          </Button>
          <Button variant="outline" onClick={() => navigate(tenantNav.to("/platform/payroll/runs"))}>
            View reconciliation
          </Button>
        </div>
      </SectionCard>

      <PayrollLinks current="overview" />
    </Layout>
  )
}
