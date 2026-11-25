import { useState, useEffect } from "react"
import api, { errorMessage } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, SectionCard } from "@/components/ui/card"
import { Table, type Column } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Skeleton, LoadingRegion } from "@/components/ui/skeleton"
import { Alert } from "@/components/ui/feedback"
import { Input, Select } from "@/components/ui/inputs"
import { Field } from "@/components/ui/layout"
import { cn } from "@/lib/utils"

interface Row {
  id: number
  [k: string]: any
}

interface PayLine {
  code: string
  name: string
  amount: string
  type: string
  rule_id: string
  rule_version: string
  input_source: string
  calculation: string
}

interface PayInputs {
  approved_time_entries?: number
  approved_worked_hours?: number
  approved_overtime_hours?: number
  unapproved_time_entries?: number
  approved_leave_requests?: number
  paid_leave_days?: number
  unpaid_leave_days?: number
}

function parseJson<T>(raw?: string | null): T | null {
  if (!raw) return null
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

const money = (value?: number | string | null) =>
  // Payslip figures render exactly as the run wrote them, two decimals and
  // no grouping: the journey pins the API's synthetic figures
  // ("4210.37", never "4210.38") to prove the screen recalculates nothing.
  // A thousands separator would break the contiguous figure the test reads.
  value === null || value === undefined || value === "" ? "—" : Number(value).toFixed(2)

interface PayslipPanelProps {
  runs: Row[]
}

export function PayslipPanel({ runs }: PayslipPanelProps) {
  const [runId, setRunId] = useState("")
  const [slips, setSlips] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [selected, setSelected] = useState<Row | null>(null)

  const load = async (id: string) => {
    setRunId(id)
    setSlips([])
    setSelected(null)
    setError("")
    if (!id) return
    setLoading(true)
    try {
      const response = await api.get<Row[]>("/payroll/payslips", {
        params: { pay_run_id: id },
      })
      setSlips(response.data)
    } catch (err) {
      setError(errorMessage(err, "The payslips of this run could not be read."))
    } finally {
      setLoading(false)
    }
  }

  const earnings = selected ? parseJson<PayLine[]>(selected.earnings_json) : null
  const deductions = selected ? parseJson<PayLine[]>(selected.deductions_json) : null
  const inputs = selected ? parseJson<PayInputs>(selected.inputs_json) : null

  const payslipColumns: Column<Row>[] = [
    { key: "employee", header: "Employee", accessor: (row) => `#${row.employee_id}` },
    { key: "gross", header: "Gross", accessor: (row) => money(row.gross_pay), cellClassName: "num" },
    { key: "deductions", header: "Deductions", accessor: (row) => money(row.total_deductions), cellClassName: "num" },
    { key: "net", header: "Net", accessor: (row) => money(row.net_pay), cellClassName: "num" },
    { key: "status", header: "Status", accessor: (row) => row.status },
    { key: "actions", header: "Actions", accessor: (row) => (
      <button
        type="button"
        className="action-link"
        onClick={(event) => {
          event.stopPropagation()
          setSelected(row)
        }}
      >
        What it used
      </button>
    ), cellClassName: "text-right" },
  ]

  return (
    <SectionCard
      title="Payslips and what they were paid from"
      description="The approved time and leave each payslip consumed, and the rule behind every line. Nothing on this panel is recalculated — these are the figures the run wrote."
      className="mb-4"
    >
      <div className="flex flex-wrap items-end gap-4 mb-4">
        <Field label="Pay run" htmlFor="payslip-run" className="flex-1 min-w-[240px]">
          <Select
            id="payslip-run"
            value={runId}
            onChange={(event) => load(event.target.value)}
          >
            <option value="">Select a pay run…</option>
            {runs.map((run) => (
              <option key={run.id} value={run.id}>
                Run #{run.id} · {run.status}
                {run.rule_pack_id ? ` · ${run.rule_pack_id}` : ""}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      {loading && (
        <LoadingRegion label="Loading payslips…">
          <Skeleton className="h-24" />
        </LoadingRegion>
      )}

      {!loading && error && <Alert tone="error" role="alert" className="mb-4">{error}</Alert>}

      {!loading && !error && runId && slips.length === 0 && (
        <p className="text-sm text-fg-muted px-4 pb-4">
          This run has no payslips. A draft run is calculated by processing it.
        </p>
      )}

      {!loading && !error && slips.length > 0 && (
        <Table
          columns={payslipColumns}
          data={slips}
          keyAccessor={(row) => row.id}
          caption="Payslips of the selected pay run"
          sortable={false}
          filterable={false}
          onRowClick={(row) => setSelected(row)}
        />
      )}

      {selected && (
        <div className="border-t border-border pt-4 space-y-6 mt-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="mk-h2 text-fg">
                Payslip #{selected.id} · employee #{selected.employee_id}
              </h3>
              <p className="text-sm text-fg-muted">
                Contributions: employee {money(selected.employee_contributions)} ·
                employer {money(selected.employer_contributions)}
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setSelected(null)}>
              Close
            </Button>
          </div>

          <section aria-labelledby="payslip-inputs">
            <h4 id="payslip-inputs" className="mk-h3 text-fg mb-3">
              What this payslip was calculated from
            </h4>
            {inputs ? (
              <>
                <div className="mb-4">
                  <Table
                    columns={[
                      { key: "input", header: "Input", accessor: (row: any) => row.label },
                      { key: "value", header: "Value", accessor: (row: any) => money(row.value), cellClassName: "num" },
                      { key: "used", header: "Used?", accessor: (row: any) => row.used },
                    ]}
                    data={[
                      { label: "Approved time entries", value: inputs.approved_time_entries, used: "Yes — paid" },
                      { label: "Approved hours worked", value: inputs.approved_worked_hours, used: "Yes — paid" },
                      { label: "Approved overtime hours", value: inputs.approved_overtime_hours, used: "Yes — paid" },
                      { label: "Time entries not approved", value: inputs.unapproved_time_entries, used: "No — excluded" },
                      { label: "Approved leave requests", value: inputs.approved_leave_requests, used: "Yes — paid or deducted" },
                      { label: "Paid leave days", value: inputs.paid_leave_days, used: "Yes — paid" },
                      { label: "Unpaid leave days", value: inputs.unpaid_leave_days, used: "Yes — deducted" },
                    ]}
                    keyAccessor={(row) => row.label}
                    caption="Approved time and leave consumed by this payslip"
                    sortable={false}
                    filterable={false}
                  />
                </div>
                <p className="text-sm text-fg-muted">
                  A time entry that is still a draft does not pay anybody. The excluded
                  count is here so that it is visible, not silently absent.
                </p>
              </>
            ) : (
              <p className="text-sm text-fg-muted">
                This payslip carries no inputs record. It was written before the inputs
                were stored, so there is no trace of the time and leave it consumed —
                and the product will not invent one.
              </p>
            )}
          </section>

          {[
            { title: "Earnings", lines: earnings },
            { title: "Deductions", lines: deductions },
          ].map(({ title, lines }) => (
            <section key={title} aria-labelledby={`payslip-${title.toLowerCase()}`}>
              <h4 id={`payslip-${title.toLowerCase()}`} className="mk-h3 text-fg mb-3">
                {title}
              </h4>
              {lines && lines.length > 0 ? (
                <Table
                  columns={[
                    { key: "line", header: "Line", accessor: (line: PayLine) => line.name || line.code },
                    { key: "amount", header: "Amount", accessor: (line: PayLine) => line.amount, cellClassName: "num" },
                    { key: "rule", header: "Rule", accessor: (line: PayLine) => (
                      <span className="text-fg-muted">{line.rule_id} v{line.rule_version}</span>
                    ) },
                    { key: "calculation", header: "Calculation", accessor: (line: PayLine) => (
                      <span className="text-fg-muted">{line.calculation || line.input_source || "—"}</span>
                    ) },
                  ]}
                  data={lines}
                  keyAccessor={(line) => `${line.code}-${line.rule_id}`}
                  caption={`${title} lines and the rule behind each`}
                  sortable={false}
                  filterable={false}
                />
              ) : (
                <p className="text-sm text-fg-muted">No {title.toLowerCase()} lines were stored for this payslip.</p>
              )}
            </section>
          ))}
        </div>
      )}
    </SectionCard>
  )
}