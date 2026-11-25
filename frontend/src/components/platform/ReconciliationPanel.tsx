import { useState, useEffect } from "react"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, SectionCard } from "@/components/ui/card"
import { Table, type Column } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Skeleton, LoadingRegion } from "@/components/ui/skeleton"
import { Alert } from "@/components/ui/feedback"
import { Input, Select } from "@/components/ui/inputs"
import { Field } from "@/components/ui/layout"
import type { PayRunReconciliation } from "@/types"
import { formatCurrency } from "@/lib/format"
import { cn } from "@/lib/utils"

interface Row {
  id: number
  [k: string]: any
}

const RECONCILIATION_ROLES = ["SuperAdmin", "HR", "PayrollViewer"]

interface ReconciliationPanelProps {
  runs: Row[]
  refreshRuns: () => void
}

export function ReconciliationPanel({ runs, refreshRuns }: ReconciliationPanelProps) {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const localeOpts = { locale: tenant?.locale, timeZone: tenant?.timezone }
  const currency = tenant?.currency || undefined
  const money = (value: unknown): string =>
    formatCurrency(value as number | string | null | undefined, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const allowed = RECONCILIATION_ROLES.includes(user?.role ?? "")
  const [runId, setRunId] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [report, setReport] = useState<PayRunReconciliation | null>(null)

  const load = async (id: string) => {
    setRunId(id)
    setReport(null)
    setError("")
    if (!id) return
    setLoading(true)
    try {
      const r = await api.get(`/payroll/runs/${id}/reconciliation`)
      setReport(r.data)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === "string" ? detail : "Reconciliation could not be loaded")
    } finally {
      setLoading(false)
    }
  }

  if (!allowed) {
    return (
      <SectionCard
        title="Pay run reconciliation"
        className="mb-4"
      >
        <p className="text-sm text-fg-muted">
          Reconciliation is available to SuperAdmin, HR and PayrollViewer roles.
        </p>
      </SectionCard>
    )
  }

  return (
    <SectionCard
      title="Pay run reconciliation"
      description="Compares the computed payslip values of a processed run against the rule-pack recalculation. Draft runs have no reconciliation yet."
      className="mb-4"
    >
      <div className="flex flex-wrap items-end gap-4 mb-4">
        <Field label="Pay run" htmlFor="recon-run" className="flex-1 min-w-[240px]">
          <Select
            id="recon-run"
            value={runId}
            onChange={(e) => load(e.target.value)}
          >
            <option value="">Select a pay run…</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                Run #{r.id} · {r.status}{r.jurisdiction ? ` · ${r.jurisdiction}` : ""}
              </option>
            ))}
          </Select>
        </Field>
        <Button
          variant="secondary"
          onClick={() => {
            refreshRuns()
            if (runId) load(runId)
          }}
        >
          Refresh
        </Button>
      </div>

      {loading && (
        <LoadingRegion label="Loading reconciliation…">
          <Skeleton className="h-24" />
        </LoadingRegion>
      )}

      {!loading && error && <Alert tone="error" role="alert" className="mb-4">{error}</Alert>}

      {!loading && !error && !report && (
        <p className="text-sm text-fg-muted mb-4">
          Choose a processed pay run to load its reconciliation.
        </p>
      )}

      {!loading && report && (
        <div className="space-y-6">
          <div className="flex items-center gap-3 flex-wrap">
            <Badge variant={report.matched ? "green" : "rose"} size="md">
              {report.matched ? "Matched" : `Discrepancies: ${report.discrepancies.length}`}
            </Badge>
            <span className="text-sm text-fg-muted">
              rule pack {report.rule_pack_id ?? "—"} v{report.rule_pack_version ?? "—"} · generated{" "}
              {report.generated_at?.replace("T", " ").slice(0, 16)}
            </span>
          </div>

          <h3 className="text-xs font-semibold uppercase tracking-wider text-fg-muted">Totals</h3>
          <Table
            columns={[
              { key: "component", header: "Component", accessor: (row: any) => row.label },
              { key: "amount", header: "Amount", accessor: (row: any) => money(row.value), cellClassName: "num tabular-nums" },
            ]}
            data={[
              { label: "Total gross", value: report.totals.total_gross },
              { label: "Total deductions", value: report.totals.total_deductions },
              { label: "Employee contributions", value: report.totals.total_employee_contributions },
              { label: "Employer contributions", value: report.totals.total_employer_contributions },
              { label: "Total net", value: report.totals.total_net },
            ]}
            keyAccessor={(row) => row.label}
            caption="Reconciliation totals"
            sortable={false}
            filterable={false}
          />

          <h3 className="text-xs font-semibold uppercase tracking-wider text-fg-muted">Discrepancies</h3>
          {report.discrepancies.length === 0 ? (
            <p className="text-sm text-fg-muted mb-4">
              No discrepancies — every payslip matches its rule-pack recalculation.
            </p>
          ) : (
            <Table
              columns={[
                { key: "code", header: "Code", accessor: (d: any) => <Badge variant="rose" size="sm">{d.code}</Badge> },
                { key: "message", header: "Message", accessor: (d: any) => d.message },
              ]}
              data={report.discrepancies.map((d, i) => ({ ...d, _index: i }))}
              keyAccessor={(d) => d._index}
              caption="Variance entries the payroll team has to look at"
              sortable={false}
              filterable={false}
            />
          )}

          <h3 className="text-xs font-semibold uppercase tracking-wider text-fg-muted">Payslips compared</h3>
          {report.payslips.length === 0 ? (
            <p className="text-sm text-fg-muted">No payslips recorded for this run yet.</p>
          ) : (
            <Table
              columns={[
                { key: "payslip", header: "Payslip", accessor: (ps: any) => <span className="font-mono text-xs">#{ps.payslip_id}</span> },
                { key: "employee", header: "Employee", accessor: (ps: any) => ps.employee_id },
                { key: "gross", header: "Gross", accessor: (ps: any) => money(ps.gross), cellClassName: "num tabular-nums" },
                { key: "deductions", header: "Deductions", accessor: (ps: any) => money(ps.total_deductions), cellClassName: "num tabular-nums" },
                { key: "net", header: "Net", accessor: (ps: any) => money(ps.net), cellClassName: "num tabular-nums" },
              ]}
              data={report.payslips}
              keyAccessor={(ps) => ps.payslip_id}
              caption="Per-payslip recalculation results"
              sortable={false}
              filterable={false}
            />
          )}
        </div>
      )}
    </SectionCard>
  )
}