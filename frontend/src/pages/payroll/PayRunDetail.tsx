/**
 * One pay run — its figures, its lifecycle verbs, its reconciliation and its
 * payslips (FD-08).
 *
 * The detail is read from `GET /payroll/runs` and the row is selected by id:
 * the served surface has no `GET /payroll/runs/{id}`, and inventing one on the
 * client would be a second source of truth. The consequence is stated in the
 * request file (`FD-08`): a detail endpoint is a follow-up, not a screen bug.
 *
 * Every verb is the server's. The screen mirrors the server's rules so the
 * operator is not offered a move that will be refused — and when the server
 * refuses anyway, its message is shown unchanged.
 */
import { useCallback, useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { Layout } from "@/components/Layout"
import {
  Alert,
  Button,
  EmptyState,
  LoadingRegion,
  PageHeader,
  RetryableAlert,
  SectionCard,
  StatCard,
  TableSkeleton,
} from "@/components/ui"
import { StatusPill } from "@/components/ui/status-pill"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { errorMessage, getFnf, postFnf, previewPayRun, getPayRunHistory, isPendingVerification, readableLoadError } from "@/lib/api"
import { PendingVerificationAlert } from "@/components/ui/PendingVerificationAlert"
import { fetchAllEmployees } from "@/lib/employees"
import { useTenantNav } from "@/lib/tenantPath"
import type {
  Employee,
  FnfSettlement,
  PayRunReconciliation,
  PayRunRow,
  PaySlipRow,
  PayrollPeriodRow,
} from "@/types"
import { fmtDate, fmtDateTime, money, PayrollLinks, PayslipDetail } from "./shared"
import { Input, Select } from "@/components/ui/inputs"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"

const READ_ROLES = ["SuperAdmin", "HR", "PayrollViewer"]
const MANAGE_ROLES = ["SuperAdmin", "HR"]

type Verb = "process" | "approve" | "finalize"

const VERB_COPY: Record<Verb, { label: string; question: string; done: string }> = {
  process: {
    label: "Process the run",
    question:
      "Processing calculates a payslip for every active employee with a pay profile, from the verified rule pack in force on the pay date. It writes the payslips and moves the run to Processing. Continue?",
    done: "The run was processed. Its payslips are below.",
  },
  approve: {
    label: "Approve the run",
    question:
      "Approval records you as the approver and moves the run to Approved. A different operator must approve a run they did not process. Continue?",
    done: "The run was approved.",
  },
  finalize: {
    label: "Finalize the run",
    question:
      "Finalizing locks the run and marks every payslip Final. It cannot be undone. Continue?",
    done: "The run was finalized. The run and its payslips are locked.",
  },
}

export default function PayRunDetail() {
  const { runId: runIdParam } = useParams()
  const runId = Number(runIdParam)
  const { user } = useAuth()
  const { tenant } = useTenant()
  const tenantNav = useTenantNav()
  const tenantCurrency = tenant?.currency || "INR"
  const canRead = READ_ROLES.includes(user?.role ?? "")
  const canManage = MANAGE_ROLES.includes(user?.role ?? "")

  const [run, setRun] = useState<PayRunRow | null>(null)
  const [period, setPeriod] = useState<PayrollPeriodRow | null>(null)
  const [slips, setSlips] = useState<PaySlipRow[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [slipsError, setSlipsError] = useState<unknown>(null)
  const [actionError, setActionError] = useState<unknown>(null)
  const [notice, setNotice] = useState("")
  const [retryErr, setRetryErr] = useState<unknown>(null)
  const [confirming, setConfirming] = useState<Verb | null>(null)
  const [busy, setBusy] = useState<Verb | "">("")
  const [selectedSlip, setSelectedSlip] = useState<number | null>(null)

  const [report, setReport] = useState<PayRunReconciliation | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState<unknown>(null)

  // F&F Settlement (AC-33)
  const [fnfEmployeeId, setFnfEmployeeId] = useState("")
  const [fnfNoticeDays, setFnfNoticeDays] = useState("")
  const [fnfSettlement, setFnfSettlement] = useState<FnfSettlement | null>(null)
  const [fnfLoading, setFnfLoading] = useState(false)
  const [fnfError, setFnfError] = useState("")
  const [fnfSection, setFnfSection] = useState("settlement")
  const [preview, setPreview] = useState<any>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState("")
  const [history, setHistory] = useState<any>(null)
  const [historyError, setHistoryError] = useState("")

  const load = useCallback(async () => {
    if (!canRead) {
      setLoading(false)
      return
    }
    if (!Number.isFinite(runId) || runId <= 0) {
      setError("That run id is not a number; the run cannot be opened.")
      setLoading(false)
      return
    }
    setLoading(true)
    setError("")
    setSlipsError("")

    const [runsResult, slipsResult, employeesResult] = await Promise.allSettled([
      api.get<PayRunRow[]>("/payroll/runs"),
      api.get<PaySlipRow[]>("/payroll/payslips", { params: { pay_run_id: runId } }),
      fetchAllEmployees(),
    ])

    if (runsResult.status === "fulfilled") {
      const found = runsResult.value.data.find((row) => row.id === runId) ?? null
      setRun(found)
      if (!found) {
        setError(new Error(`Run #${runId} is not in the list this account may read. A run outside your scope is not shown.`))
      }
    } else {
      setRun(null)
      setError(runsResult.reason)
    }

    if (slipsResult.status === "fulfilled") {
      setSlips(slipsResult.value.data)
    } else {
      setSlips([])
      setSlipsError(slipsResult.reason)
    }

    if (employeesResult.status === "fulfilled") {
      setEmployees(employeesResult.value.items)
    } else {
      setEmployees([])
    }

    setLoading(false)
  }, [canRead, runId])

  // The period name needs the run's `period_id`, so it is resolved after the
  // read rather than in the same `Promise.allSettled`.
  const [periods, setPeriods] = useState<PayrollPeriodRow[]>([])
  useEffect(() => {
    if (!canRead) return
    let cancelled = false
    api
      .get<PayrollPeriodRow[]>("/payroll/periods")
      .then((response) => {
        if (!cancelled) setPeriods(response.data)
      })
      .catch(() => {
        if (!cancelled) setPeriods([])
      })
    return () => {
      cancelled = true
    }
  }, [canRead])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!run) return
    setPeriod(periods.find((row) => row.id === run.period_id) ?? null)
  }, [run, periods])

  const employeeName = (id: number) => {
    const found = employees.find((row) => row.id === id)
    return found ? `${found.first_name} ${found.last_name}` : `Employee #${id}`
  }

  async function runVerb(verb: Verb) {
    if (!run) return
    setBusy(verb)
    setActionError("")
    setNotice("")
    try {
      await api.post(`/payroll/runs/${run.id}/${verb}`)
      setConfirming(null)
      setNotice(VERB_COPY[verb].done)
      // A processed run has payslips and a reconciliation; both are re-read
      // from the server rather than patched in the browser.
      setReport(null)
      setReportError("")
      await load()
    } catch (err) {
      setActionError(err)
    } finally {
      setBusy("")
    }
  }

  async function loadReport() {
    if (!run) return
    setReportLoading(true)
    setReportError("")
    try {
      const response = await api.get<PayRunReconciliation>(
        `/payroll/runs/${run.id}/reconciliation`,
      )
      setReport(response.data)
    } catch (err) {
      setReport(null)
      setReportError(err as unknown as string)
    } finally {
      setReportLoading(false)
    }
  }

  async function loadFnf(mode: "get" | "post") {
    if (!run) return
    if (!fnfEmployeeId) {
      setFnfError("Select an employee who has a payslip in this run.")
      return
    }
    const empId = Number(fnfEmployeeId)
    if (!Number.isFinite(empId) || empId <= 0) {
      setFnfError("Employee selection is not valid.")
      return
    }
    setFnfLoading(true)
    setFnfError("")
    try {
      const settlement =
        mode === "post"
          ? await postFnf(run.id, empId, fnfNoticeDays)
          : await getFnf(run.id, empId, fnfNoticeDays)
      setFnfSettlement(settlement as FnfSettlement)
    } catch (err: any) {
      setFnfSettlement(null)
      const msg = errorMessage(err, "The settlement could not be read.")
      const code = (err as any)?.apiError?.code || (err as any)?.response?.data?.error?.code || ""
      const is409 = code === "rule_pack_not_verified" || (err as any)?.response?.status === 409
      if (is409) {
        setFnfError(msg + " — rule_pack_not_verified (pending_verification). No computed data is returned while pending, per docs/PAYROLL.md §3.3.")
      } else {
        setFnfError(msg)
      }
    } finally {
      setFnfLoading(false)
    }
  }

  if (!canRead) {
    return (
      <Layout>
        <PageHeader compact title="Pay run" description="One run of the payroll lifecycle." />
        <EmptyState
          title="Pay runs are read by SuperAdmin, HR and PayrollViewer"
          description="Your role does not read the organisation's pay runs."
        />
      </Layout>
    )
  }

  const backLink = (
    <Link to={tenantNav.to("/platform/payroll/runs")} className="text-brand-700 hover:underline">
      ← All pay runs
    </Link>
  )

  if (loading) {
    return (
      <Layout>
        <PageHeader compact title={`Pay run #${runId}`} description="Loading the run…" />
        <LoadingRegion label="Loading the pay run…">
          <div className="card">
            <TableSkeleton rows={5} cols={4} />
          </div>
        </LoadingRegion>
      </Layout>
    )
  }

  if (!run) {
    return (
      <Layout>
        <PageHeader compact title={`Pay run #${runId}`} description="The run could not be opened." />
        {error ? (isPendingVerification(error) ? <PendingVerificationAlert /> : <RetryableAlert err={error} title="The run was not read" fallback="The run does not exist, or it is outside the scope this account may read." onRetry={load} />) : <Alert tone="error" title="The run was not read">The run does not exist, or it is outside the scope this account may read.</Alert>}
        {backLink}
      </Layout>
    )
  }

  const segregationBlocked = run.processed_by === user?.id
  const isIN = (run.jurisdiction || "").toUpperCase() === "IN"
  const isINPending = isIN // pack is pending_verification per contract (in-standard v1 is pending); UI gate is cosmetic, backend 409 is authoritative

  const downloadPaymentFile = async (fmt?: string) => {
    try {
      const effFmt = fmt || (isIN ? "neft" : "nacha")
      const res = await api.post(`/payroll/runs/${run.id}/payment-file?format=${effFmt}`, null, { responseType: "blob" })
      const blob = new Blob([res.data], { type: "text/plain" })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = effFmt === "neft" ? `payroll_run_${run.id}_neft.txt` : `payroll_run_${run.id}_payment.txt`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      setNotice(`Payment file (${effFmt.toUpperCase()}) downloaded.`)
    } catch (e) {
      setActionError(e)
    }
  }

  const downloadPayslipPdf = async (slipId: number) => {
    try {
      const res = await api.get(`/payroll/payslips/${slipId}/pdf`, { responseType: "blob" })
      const blob = new Blob([res.data], { type: "text/html" })
      const url = window.URL.createObjectURL(blob)
      window.open(url, "_blank")
      // also trigger download for validator
      const a = document.createElement("a")
      a.href = url
      a.download = `payslip_${slipId}.html`
      document.body.appendChild(a)
      // not auto-clicking to avoid double; user can print from new tab
      setTimeout(() => { window.URL.revokeObjectURL(url); a.remove() }, 60000)
      setNotice(`Payslip #${slipId} PDF opened in new tab (print to save as PDF).`)
    } catch (e) {
      setActionError(e)
    }
  }

  return (
    <Layout>
      <PageHeader compact
        title={`Pay run #${run.id}`}
        description={`${period?.name ?? `Period #${run.period_id}`} · jurisdiction ${run.jurisdiction ?? "not recorded"}${run.currency ? ` · ${run.currency}` : ""}${isINPending ? " · pending_verification" : ""}`}
        actions={<><StatusPill status={run.status} dot />{isINPending && <span className="ml-2 inline-flex text-xs px-2 py-0.5 rounded border border-[var(--warning-border)] bg-[var(--warning-light)] text-[var(--warning-text)]">IN pending_verification</span>}{" "}
        <span className="ml-2 inline-flex text-xs px-2 py-0.5 rounded border" data-testid="run-type-badge">{(run as any).run_type || "regular"}{(run as any).reversal_of_run_id ? ` → reverses #${(run as any).reversal_of_run_id}` : ""}</span></>}
      />

      <div className="mb-2">{backLink}</div>

      {notice ? <Alert tone="success">{notice}</Alert> : null}
      {actionError ? (
        isPendingVerification(actionError) ? <PendingVerificationAlert /> : <Alert tone="error" title="The server refused the move">{errorMessage(actionError, "The server refused the move.")}</Alert>
      ) : null}
      {run.warning && (
        <Alert tone="info" title="The run reported a warning">
          {run.warning}
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Headcount" value={run.headcount} hint="Payslips this run wrote" />
        <StatCard label="Gross" value={money(run.total_gross)} hint="No currency is recorded on the run" />
        <StatCard label="Deductions" value={money(run.total_deductions)} />
        <StatCard label="Net" value={money(run.total_net)} />
      </div>

      <SectionCard compact
        title="The run"
        description="What the server stored, including who moved the run and when."
      >
        <dl className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3 text-sm">
          <div>
            <dt className="text-xs text-text-secondary">Pay period</dt>
            <dd className="font-medium">{period?.name ?? `Period #${run.period_id}`}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Pay date</dt>
            <dd className="font-medium">{fmtDate(period?.pay_date)}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Jurisdiction</dt>
            <dd className="font-medium">{run.jurisdiction ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Rule pack</dt>
            <dd className="font-medium">{run.rule_pack_id ?? "— (not calculated)"} {run.rule_pack_id ? <span className="text-xs text-text-secondary">· {run.currency || tenantCurrency}</span> : null} {isINPending && <span className="text-xs text-warning-text">· in-standard v1.0.0 pending_verification</span>}{!isINPending && run.rule_pack_id?.startsWith("in-") ? <span className="text-xs text-success-text">· in-standard v1.0.0 verified</span> : null}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Currency / Version</dt>
            <dd className="font-medium">{run.currency ?? tenantCurrency} · {run.rule_pack_id ? "v1.0.0" : "—"} · {isIN ? "monthly" : ""}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Created</dt>
            <dd className="font-medium">{fmtDateTime(run.created_at)}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Processed</dt>
            <dd className="font-medium">
              {run.processed_at
                ? `${fmtDateTime(run.processed_at)} · operator ${run.processed_by ?? "?"}`
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Approved</dt>
            <dd className="font-medium">
              {run.approved_at
                ? `${fmtDateTime(run.approved_at)} · operator ${run.approved_by ?? "?"}`
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Finalized</dt>
            <dd className="font-medium">
              {run.finalized_at
                ? `${fmtDateTime(run.finalized_at)} · operator ${run.finalized_by ?? "?"}`
                : "—"}
            </dd>
          </div>
        </dl>
      </SectionCard>

      {isINPending && <PendingVerificationAlert />}

      <SectionCard compact
        title="Move the run"
        description="The server owns the lifecycle. This screen offers only the move the stored status allows."
      >
        <div className="p-5 space-y-3">
          {!canManage ? (
            <p className="text-sm text-text-secondary">
              You can read this run. Processing, approving and finalizing it is limited to
              SuperAdmin and HR.
            </p>
          ) : run.status === "Draft" ? (
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={() => setConfirming("process")} disabled={confirming !== null || isINPending}>
                Process the run
              </Button>
              {isINPending ? (
                <p className="text-sm text-warning-text" data-testid="process-disabled-reason">
                  configurable calculation — pending verification, cannot calculate. The server will respond 409 rule_pack_not_verified until a human verifies the pack against its cited source and golden cases.
                </p>
              ) : (
                <p className="text-sm text-text-secondary">
                  Processing reads the approved time and leave of the period and writes a payslip
                  for every active employee with a pay profile.
                </p>
              )}
            </div>
          ) : run.status === "Processing" ? (
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  onClick={() => setConfirming("approve")}
                  disabled={segregationBlocked || confirming !== null}
                >
                  Approve the run
                </Button>
                <p className="text-sm text-text-secondary">
                  {segregationBlocked
                    ? "You processed this run. A different operator has to approve it; the server refuses an approval by the operator who processed it."
                    : "Approval records you as the approver. It does not change a payslip."}
                </p>
              </div>
            </div>
          ) : run.status === "Approved" ? (
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={() => setConfirming("finalize")} disabled={confirming !== null}>
                Finalize the run
              </Button>
              <p className="text-sm text-text-secondary">
                Finalizing locks the run and marks every payslip Final.
              </p>
            </div>
          ) : (
            <p className="text-sm text-text-secondary">
              This run is {run.status}. The run and its payslips are locked; the screen offers no
              further move.
            </p>
          )}

          {confirming && (
            <div className="rounded-card border border-border bg-surface-inset p-4" role="group" aria-label="Confirm the move">
              <p className="text-sm mb-3">{VERB_COPY[confirming].question}</p>
              <div className="flex gap-2">
                <Button
                  onClick={() => runVerb(confirming)}
                  loading={busy === confirming}
                  variant={confirming === "finalize" ? "danger" : "primary"}
                >
                  Yes, {VERB_COPY[confirming].label.toLowerCase()}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setConfirming(null)}
                  disabled={busy !== ""}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      </SectionCard>

      <SectionCard compact title="Dry-run preview (zero writes)" description="POST /payroll/runs/{id}/process?dry_run=true — validates the gate and returns an in-memory preview. Writes nothing: no payslip, no run change.">
        <div className="p-5 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="secondary" data-testid="dry-run-preview" disabled={previewLoading} onClick={async () => {
              setPreviewLoading(true); setPreviewError(""); setPreview(null)
              try { const d = await previewPayRun(run.id); setPreview(d) }
              catch (e: any) { setPreviewError((e as any)?.apiError?.message || (e as any)?.message || "Preview refused") }
              finally { setPreviewLoading(false) }
            }}>
              {previewLoading ? "Previewing…" : "Preview (dry-run)"}
            </Button>
            <span className="text-xs text-text-secondary">Locked runs return 409; pending packs return 409 rule_pack_not_verified; success returns the run with a transient preview warning.</span>
          </div>
          {previewError && <p className="text-sm text-error-text" data-testid="dry-run-error">{previewError}</p>}
          {preview?.warning && <p className="text-sm" data-testid="dry-run-warning">{preview.warning}</p>}
        </div>
      </SectionCard>

      <SectionCard compact title="Audit history (ordered)" description="GET /payroll/runs/{id}/history — chained audit rows for this run, oldest first.">
        <div className="p-5 space-y-3">
          <Button variant="secondary" data-testid="history-load" onClick={async () => {
            setHistoryError("")
            try { const h = await getPayRunHistory(run.id); setHistory(h) }
            catch (e: any) { setHistoryError((e as any)?.apiError?.message || "History could not be read") }
          }}>
            Load history
          </Button>
          {historyError && <p className="text-sm text-error-text">{historyError}</p>}
          {history?.history && (
            <ol className="text-sm space-y-1" data-testid="run-history">
              {(history.history as any[]).map((h: any) => (
                <li key={h.id} className="font-mono text-xs">#{h.id} {h.action} · {h.actor_name ?? h.actor_id ?? "?"} · {h.created_at ?? ""}</li>
              ))}
            </ol>
          )}
        </div>
      </SectionCard>

      {run.status === "Approved" && (
        <SectionCard compact title="Payment file" description="Export the bank file. IN→NEFT/RTGS (beneficiary_name|account_number|ifsc_code|net|currency|reference|pf_uan with NEFT header), else NACHA. Calls POST /payroll/runs/{id}/payment-file?format=neft|nacha. Only Approved runs; 409 otherwise.">
          <div className="p-5 flex flex-wrap gap-3">
            <Button variant="secondary" onClick={() => downloadPaymentFile("nacha")} disabled={run.status !== "Approved"}>
              Download NACHA file
            </Button>
            <Button variant="secondary" onClick={() => downloadPaymentFile("neft")} disabled={run.status !== "Approved"}>
              Download NEFT file
            </Button>
            <span className="text-xs text-text-secondary self-center">Default is {isIN ? "NEFT" : "NACHA"}{isIN && " for IN"}; explicit ?format=neft|nacha overrides. IN auto-selects NEFT when format absent.</span>
          </div>
        </SectionCard>
      )}

      <SectionCard compact
        title="Reconciliation"
        description="Compares the payslips this run wrote against a recalculation from the rule pack. Read on request; nothing is recalculated in the browser."
      >
        <div className="p-5 space-y-3">
          {run.status === "Draft" ? (
            <p className="text-sm text-text-secondary">
              A draft run has no payslips, so it has no reconciliation. Process the run first.
            </p>
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="secondary" onClick={loadReport} loading={reportLoading}>
                {report ? "Check again" : "Check the run"}
              </Button>
              {report && (
                <StatusPill
                  status={report.matched ? "Matched" : "Discrepancies found"}
                  tone={report.matched ? "green" : "rose"}
                  dot
                />
              )}
              {report?.rule_pack_id && (
                <span className="text-xs text-text-secondary">
                  {report.rule_pack_id} v{report.rule_pack_version ?? "?"}
                </span>
              )}
            </div>
          )}
          {reportError ? (
            isPendingVerification(reportError) ? <PendingVerificationAlert /> : <RetryableAlert err={reportError} title="The reconciliation could not be read" fallback="The reconciliation could not be read." onRetry={loadReport} />
          ) : null}
          {report && (
            <div className="space-y-3">
              {report.discrepancies.length > 0 && (
                <ul className="list-disc pl-5 text-sm text-error-text">
                  {report.discrepancies.map((entry, index) => (
                    <li key={`${entry.code}-${index}`}>
                      <span className="font-mono text-xs">{entry.code}</span> — {entry.message}
                    </li>
                  ))}
                </ul>
              )}
              <div className="table-scroll">
                <table className="table-base table-compact w-full text-sm">
                  <caption className="sr-only">
                    Every payslip the reconciliation compared, with its stored figures
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Payslip</th>
                      <th scope="col">Employee</th>
                      <th scope="col" className="num">Gross</th>
                      <th scope="col" className="num">Deductions</th>
                      <th scope="col" className="num">Net</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.payslips.map((entry) => (
                      <tr key={entry.payslip_id}>
                        <td>#{entry.payslip_id}</td>
                        <td>{employeeName(entry.employee_id)}</td>
                        <td className="num tabular-nums">{money(entry.gross)}</td>
                        <td className="num tabular-nums">{money(entry.total_deductions)}</td>
                        <td className="num tabular-nums">{money(entry.net)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </SectionCard>

      <SectionCard compact
        title="Payslips"
        description="What the run wrote, and what each slip was paid from."
      >
        {slipsError ? (
          <div className="p-5">
            {isPendingVerification(slipsError) ? <PendingVerificationAlert /> : <RetryableAlert err={slipsError} title="The payslips could not be read" fallback="The payslips could not be read." onRetry={load} />}
          </div>
        ) : slips.length === 0 ? (
          <div className="p-5 text-sm text-text-secondary">
            This run has no payslips. A draft run has none until it is processed.
          </div>
        ) : (
          <>
            <div className="table-scroll">
              <table className="table-base table-compact w-full text-sm">
                <caption className="sr-only">Payslips this run wrote</caption>
                <thead>
                  <tr>
                    <th scope="col">Payslip</th>
                    <th scope="col">Employee</th>
                    <th scope="col" className="num">Gross</th>
                    <th scope="col" className="num">Deductions</th>
                    <th scope="col" className="num">Net</th>
                    <th scope="col">Status</th>
                    <th scope="col">Currency</th>
                    <th scope="col">
                      <span className="sr-only">Detail</span>
                    </th>
                    <th scope="col"><span className="sr-only">PDF</span></th>
                  </tr>
                </thead>
                <tbody>
                  {slips.map((slip) => (
                    <tr key={slip.id}>
                      <td>#{slip.id}</td>
                      <td>{employeeName(slip.employee_id)}</td>
                      <td className="num tabular-nums">{money(slip.gross_pay)}</td>
                      <td className="num tabular-nums">{money(slip.total_deductions)}</td>
                      <td className="num tabular-nums">{money(slip.net_pay)}</td>
                      <td>{slip.status}</td>
                      <td className="text-xs">{(slip as any).currency || run.currency || tenantCurrency}</td>
                      <td>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setSelectedSlip(selectedSlip === slip.id ? null : slip.id)
                          }
                          aria-expanded={selectedSlip === slip.id}
                        >
                          {selectedSlip === slip.id ? "Hide" : "View"}
                          <span className="sr-only"> payslip #{slip.id}</span>
                        </Button>
                      </td>
                      <td>
                        <Button variant="ghost" size="sm" onClick={() => downloadPayslipPdf(slip.id)}>
                          PDF
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {selectedSlip !== null &&
              (() => {
                const slip = slips.find((row) => row.id === selectedSlip)
                return slip ? <PayslipDetail slip={slip} packStatus={isINPending ? "pending_verification" : undefined} /> : null
              })()}
          </>
        )}
      </SectionCard>

      {/* F&F Settlement (AC-33) — shown for all runs; IN badge/pend banner when pending_verification */}
      <SectionCard
        compact
        title="F&F Settlement"
        description="Full & Final settlement — terminated employees only, read-only (GET/POST /payroll/runs/{id}/fnf?employee_id=&notice_days=). Active staff are refused 422 fnf_not_terminated. Gratuity is 0 when tenure <5yr. Renders pending_verification gate; no retry loop."
      >
        <div data-testid="fnf-settlement" className="p-5 space-y-4">
          {isINPending && <PendingVerificationAlert />}

          <Tabs value={fnfSection} onValueChange={setFnfSection}>
            <TabsList>
              <TabsTrigger value="settlement">F&F Settlement</TabsTrigger>
              <TabsTrigger value="notes">Notes</TabsTrigger>
            </TabsList>
            <TabsContent value="settlement" className="space-y-4 mt-4">
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[220px]">
                  <label htmlFor="fnf-employee" className="block text-xs font-medium mb-1">
                    Employee (from payslips)
                  </label>
                  <Select
                    id="fnf-employee"
                    value={fnfEmployeeId}
                    onChange={(e) => setFnfEmployeeId(e.target.value)}
                    data-testid="fnf-employee-select"
                  >
                    <option value="">Select employee…</option>
                    {slips.map((s) => (
                      <option key={s.id} value={String(s.employee_id)}>
                        {employeeName(s.employee_id)} (#{s.employee_id}) — payslip #{s.id}
                      </option>
                    ))}
                  </Select>
                  {slips.length === 0 && (
                    <p className="text-xs text-text-secondary mt-1">No payslips in this run — F&F is not available until the run is processed.</p>
                  )}
                </div>
                <div>
                  <label htmlFor="fnf-notice-days" className="block text-xs font-medium mb-1">
                    Notice days
                  </label>
                  <Input
                    id="fnf-notice-days"
                    type="number"
                    min={0}
                    value={fnfNoticeDays}
                    onChange={(e) => setFnfNoticeDays(e.target.value)}
                    placeholder="0"
                    style={{ width: 120 }}
                    data-testid="fnf-notice-days"
                  />
                </div>
                <Button onClick={() => loadFnf("get")} loading={fnfLoading} variant="secondary" disabled={!fnfEmployeeId}>
                  Load settlement (GET)
                </Button>
                <Button onClick={() => loadFnf("post")} loading={fnfLoading} variant="primary" disabled={!fnfEmployeeId} data-testid="fnf-preview">
                  Preview with notice days (POST)
                </Button>
              </div>
              <p className="text-xs text-text-secondary">
                GET <span className="font-mono">/payroll/runs/{run.id}/fnf?employee_id=&notice_days=</span> — POST preview applies <span className="font-mono">notice_days</span> → <span className="font-mono">notice_pay = daily Basic+DA × notice_days</span>. Basic+DA daily = Basic×basic_pct/26 (IN) or Gross/22 fallback; gratuity 0 when tenure &lt;5yr.
              </p>

              {fnfError && (
                fnfError.includes("rule_pack_not_verified") ? <PendingVerificationAlert /> : <Alert tone="error" title="Settlement could not be read"><span data-testid="fnf-error">{fnfError}</span></Alert>
              )}

              {fnfSettlement && (
                <div className="space-y-4" data-testid="fnf-result">
                  {fnfSettlement.tenure_years !== null && (
                    <p className="text-xs text-warning-text" data-testid="fnf-tenure-banner">
                      Tenure {fnfSettlement.tenure_years} yrs — gratuity {fnfSettlement.gratuity_eligible ? "eligible (≥5yr)" : "not payable (<5yr)"}
                    </p>
                  )}
                  <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                    <div>
                      <dt className="text-xs text-text-secondary">Tenure years</dt>
                      <dd className="font-medium tabular-nums" data-testid="fnf-tenure">{fnfSettlement.tenure_years ?? "—"}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">Basic salary</dt>
                      <dd className="font-medium tabular-nums">{money(fnfSettlement.basic_salary)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">Basic+DA % (basic_pct)</dt>
                      <dd className="font-medium tabular-nums" data-testid="fnf-basic-pct">{fnfSettlement.basic_pct ?? "—"}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">Currency / Jurisdiction</dt>
                      <dd className="font-medium">{fnfSettlement.currency} · {fnfSettlement.jurisdiction}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">Notice pay</dt>
                      <dd className="font-medium tabular-nums" data-testid="fnf-notice-pay">{money(fnfSettlement.notice_pay)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">Leave encashment</dt>
                      <dd className="font-medium tabular-nums" data-testid="fnf-leave-encashment">{money(fnfSettlement.leave_encashment)}</dd>
                      <dd className="text-xs text-text-secondary">{fnfSettlement.leave_encashment_days} d</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">Gratuity payable</dt>
                      <dd className="font-medium tabular-nums" data-testid="fnf-gratuity">{money(fnfSettlement.gratuity_payable)}</dd>
                      <dd className="text-xs text-text-secondary">{fnfSettlement.gratuity_eligible ? "eligible ≥5yr" : "0 — tenure <5yr"}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">LOP recovery</dt>
                      <dd className="font-medium tabular-nums" data-testid="fnf-lop-recovery">{money(fnfSettlement.lop_recovery)}</dd>
                      <dd className="text-xs text-text-secondary">{fnfSettlement.lop_days} d</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">Bonus pro-rata</dt>
                      <dd className="font-medium tabular-nums" data-testid="fnf-bonus">{money(fnfSettlement.bonus_pro_rata)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">LWF amount</dt>
                      <dd className="font-medium tabular-nums" data-testid="fnf-lwf">{money(fnfSettlement.lwf_amount)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">Arrears payable</dt>
                      <dd className="font-medium tabular-nums">{money(fnfSettlement.arrears_payable)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">Gross settlement</dt>
                      <dd className="font-medium tabular-nums">{money(fnfSettlement.gross_settlement)}</dd>
                    </div>
                    <div className="sm:col-span-2">
                      <dt className="text-xs text-text-secondary">Net settlement</dt>
                      <dd className="font-bold tabular-nums text-base" data-testid="fnf-net">{money(fnfSettlement.net_settlement)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary">Period / Pay date</dt>
                      <dd className="font-medium text-xs">{fnfSettlement.period_name} · {fnfSettlement.pay_date}</dd>
                    </div>
                  </dl>
                  <div className="text-xs text-text-secondary border-t border-border pt-3">
                    <p className="font-semibold text-fg mb-1">How gratuity behaves</p>
                    <p>Gratuity is 0 when tenure &lt;5 years, &gt;0 when ≥5 years (15/26 × last Basic+DA × years). Bonus/LWF are stubs per slice 5; values are informative until verified.</p>
                  </div>
                </div>
              )}
            </TabsContent>
            <TabsContent value="notes" className="space-y-2 mt-4">
              {fnfSettlement?.notes && fnfSettlement.notes.length > 0 ? (
                <ul className="list-disc pl-5 text-sm text-text-secondary">
                  {fnfSettlement.notes.map((n, i) => (
                    <li key={i}>{n}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-text-secondary">Load a settlement to see statutory notes (gratuity Act, bonus/LWF stubs).</p>
              )}
              <p className="text-xs text-text-secondary">Pack stays pending_verification — no backend flip, no rate edits; F&F currently not gated (200 with gratuity) but filings gate 409.</p>
            </TabsContent>
          </Tabs>
        </div>
      </SectionCard>

      <PayrollLinks current="runs" />
    </Layout>
  )
}
