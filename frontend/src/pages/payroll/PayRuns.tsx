/**
 * Pay runs — the payroll lifecycle, driven (FD-08).
 *
 * Why this page exists
 * --------------------
 * The pay-run lifecycle was served and had no operator surface: a run could be
 * created, processed, approved and finalized only by calling the API. The
 * Payroll tab in `Platform.tsx` lists runs and reads a payslip panel, but it
 * offers no verb. This page is the verb surface; it does not replace the tab.
 *
 * What the screen claims
 * ----------------------
 * Only what it read. The list is the served `GET /payroll/runs` (a plain array,
 * newest first — the contract still declares a paged envelope, recorded as a
 * contract gap in `agents/requests/PY-04.md`). Creating a run is offered to the
 * roles the server accepts it from (`ADMIN_ROLES`); a viewer is told so rather
 * than shown a button that would be refused.
 */
import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Layout } from "@/components/Layout"
import {
  Input,
  Select,
  Alert,
  Button,
  EmptyState,
  LoadingRegion,
  PageHeader,
  RetryableAlert,
  PendingVerificationAlert,
  SectionCard,
  TableSkeleton,
} from "@/components/ui"

import { StatusPill } from "@/components/ui/status-pill"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { errorMessage, isPendingVerification } from "@/lib/api"
import { useFieldErrors } from "@/lib/useFieldErrors"
import { useTenantNav } from "@/lib/tenantPath"
import type { PayRunRow, PayrollPeriodRow } from "@/types"
import { fmtDate, money, PayrollLinks } from "./shared"

/** `REPORTS_ROLES` in `app/api/deps.py`: who may read a pay run. */
const READ_ROLES = ["SuperAdmin", "HR", "PayrollViewer"]
/** `ADMIN_ROLES` in `app/api/deps.py`: who may create or move one. */
const MANAGE_ROLES = ["SuperAdmin", "HR"]

export default function PayRuns() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const tenantCurrency = tenant?.currency || "INR"
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const canRead = READ_ROLES.includes(user?.role ?? "")
  const canManage = MANAGE_ROLES.includes(user?.role ?? "")

  const [runs, setRuns] = useState<PayRunRow[]>([])
  const [periods, setPeriods] = useState<PayrollPeriodRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [periodsError, setPeriodsError] = useState<unknown>(null)
  const [formError, setFormError] = useState<unknown>(null)
  const fieldErrors = useFieldErrors(formError)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState("")
  const [periodId, setPeriodId] = useState("")
  const [jurisdiction, setJurisdiction] = useState("")
  const [runType, setRunType] = useState("regular")
  const [reversalOf, setReversalOf] = useState("")
  const [currency, setCurrency] = useState("INR")
  const [jurisFilter, setJurisFilter] = useState("")

  const load = useCallback(async () => {
    if (!canRead) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError("")
    setPeriodsError("")
    const [runsResult, periodsResult] = await Promise.allSettled([
      api.get<PayRunRow[]>("/payroll/runs"),
      api.get<PayrollPeriodRow[]>("/payroll/periods"),
    ])
    if (runsResult.status === "fulfilled") {
      setRuns(runsResult.value.data)
    } else {
      setError(runsResult.reason)
      setRuns([])
    }
    if (periodsResult.status === "fulfilled") {
      setPeriods(periodsResult.value.data)
    } else {
      setPeriodsError(periodsResult.reason)
      setPeriods([])
    }
    setLoading(false)
  }, [canRead])

  useEffect(() => {
    void load()
  }, [load])

  const periodName = (id: number) =>
    periods.find((period) => period.id === id)?.name ?? `Period #${id}`

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    if (saving) return
    setFormError("")
    setNotice("")
    const code = jurisdiction.trim().toUpperCase()
    const cur = (currency || tenantCurrency).trim().toUpperCase()
    if (!periodId) {
      setFormError("Choose the pay period the run belongs to.")
      return
    }
    if (!/^[A-Z]{2}$/.test(code)) {
      setFormError("The jurisdiction is a two-letter ISO 3166-1 country code.")
      return
    }
    if (!/^[A-Z]{3}$/.test(cur)) {
      setFormError("Currency must be a three-letter ISO 4217 code.")
      return
    }
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        period_id: Number(periodId),
        jurisdiction: code,
        currency: cur,
        run_type: (runType || "regular").trim().toLowerCase(),
      }
      if (reversalOf.trim() !== "") payload.reversal_of_run_id = Number(reversalOf)
      const response = await api.post<PayRunRow>("/payroll/runs", payload)
      setPeriodId("")
      setJurisdiction("")
      setCurrency("INR")
      setRunType("regular")
      setReversalOf("")
      setNotice(`Run #${response.data.id} was created in Draft. Nothing has been calculated yet.`)
      await load()
      navigate(tenantNav.to(`/platform/payroll/runs/${response.data.id}`))
    } catch (err) {
      setFormError(err)
    } finally {
      setSaving(false)
    }
  }

  if (!canRead) {
    return (
      <Layout>
        <PageHeader compact
          title="Pay runs"
          description="The payroll lifecycle: create, process, reconcile, approve and finalize."
        />
        <EmptyState
          title="Pay runs are read by SuperAdmin, HR and PayrollViewer"
          description="Your role does not read the organisation's pay runs. A person's own payslip is read from the payroll overview."
        />
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader compact
        title="Pay runs"
        description="One run per pay period and jurisdiction. A run moves Draft → Processing → Approved → Finalized; every move is made by the server and recorded against the operator who made it."
      />

      {error ? (
        isPendingVerification(error) ? <PendingVerificationAlert /> : <RetryableAlert err={error} title="The pay runs could not be read" fallback="The pay runs could not be read." onRetry={load} />
      ) : null}
      {periodsError ? (
        <RetryableAlert err={periodsError} title="The pay periods could not be read" fallback="The pay periods could not be read." onRetry={load} />
      ) : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}

      {canManage ? (
        <SectionCard compact
          title="Create a draft run"
          description="Creating a run calculates nothing. The jurisdiction names the rule pack the run may later be calculated from."
        >
          <form onSubmit={handleCreate} className="p-4">
            {formError ? (
              fieldErrors.hasFieldErrors ? (
                fieldErrors.globalError ? <p className="text-sm text-error-text mb-3" role="alert">{fieldErrors.globalError}</p> : null
              ) : (
                isPendingVerification(formError) ? <div className="mb-3"><PendingVerificationAlert /></div> : <div className="mb-3"><RetryableAlert err={formError} title="The pay run could not be created" fallback="The pay run could not be created." /></div>
              )
            ) : null}
            {periodsError ? (
              <p className="text-sm text-text-secondary mb-3" role="status">
                {errorMessage(periodsError, "The pay periods could not be read.")} A run cannot be created until a period can be chosen.
              </p>
            ) : null}
            <div className="flex flex-wrap gap-3 items-end">
              <div className="flex-1 min-w-[220px]">
                <label htmlFor="run-period" className="block text-xs font-medium text-text-secondary mb-1">
                  Pay period
                </label>
                <Select
                  id="run-period"
                  value={periodId}
                  onChange={(event) => setPeriodId(event.target.value)}
                  required
                  disabled={periods.length === 0}
                  error={!!fieldErrors.get("period_id")}
                >
                  <option value="">
                    {periods.length === 0 ? "No period is available" : "Select a period…"}
                  </option>
                  {periods.map((period) => (
                    <option key={period.id} value={period.id}>
                      {period.name} · pay date {fmtDate(period.pay_date)}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="flex-1 min-w-[180px]">
                <label
                  htmlFor="run-jurisdiction"
                  className="block text-xs font-medium text-text-secondary mb-1"
                >
                  Jurisdiction
                </label>
                <Input
                  id="run-jurisdiction"
                  value={jurisdiction}
                  onChange={(event) => {
                    const v = event.target.value.toUpperCase()
                    setJurisdiction(v)
                    if (v === "IN" && !currency) setCurrency("INR")
                  }}
                  maxLength={2}
                  placeholder="e.g. GB"
                  autoComplete="off"
                  required
                  error={!!fieldErrors.get("jurisdiction")}
                />
                {fieldErrors.get("jurisdiction") && <p role="alert" className="text-xs text-error-text mt-1">{fieldErrors.get("jurisdiction")}</p>}
                {jurisdiction.toUpperCase() === "IN" && (
                  <span className="inline-flex mt-1 text-xs px-2 py-0.5 rounded border border-[var(--warning-border)] bg-[var(--warning-light)] text-[var(--warning-text)]" data-testid="in-pending-badge">
                    IN · pending_verification — configurable calculation, cannot calculate (409 rule_pack_not_verified)
                  </span>
                )}
              </div>
              <div className="min-w-[120px]">
                <label htmlFor="run-currency" className="block text-xs font-medium text-text-secondary mb-1">
                  Currency
                </label>
                <Input
                  id="run-currency"
                  value={currency}
                  onChange={(event) => setCurrency(event.target.value.toUpperCase())}
                  maxLength={3}
                  placeholder={jurisdiction.toUpperCase() === "IN" ? "INR" : tenantCurrency}
                  autoComplete="off"
                  required
                  error={!!fieldErrors.get("currency")}
                />
                {fieldErrors.get("currency") && <p role="alert" className="text-xs text-error-text mt-1">{fieldErrors.get("currency")}</p>}
              </div>
              <Button type="submit" loading={saving} disabled={periods.length === 0}>
                Create draft run
              </Button>
            </div>
            <p className="text-xs text-text-secondary mt-2">
              The two-letter code is the country whose rule pack applies. Pay setup is where
              periods and pay profiles are created. IN runs are INR only; the pack is pending_verification per docs/PAYROLL.md §3.3 — Process will be refused with 409 rule_pack_not_verified.
            </p>
          </form>
        </SectionCard>
      ) : (
        <Alert tone="info">
          You can read pay runs. Creating, processing, approving and finalizing them is limited
          to SuperAdmin and HR.
        </Alert>
      )}

      <SectionCard compact title="All pay runs" description="Newest first, as the server returns them. History shows rule_pack_id/version/jurisdiction/currency per run; IN monthly runs are monthly and filterable; each entry links to recon + export.">
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
          <>
            <div className="flex flex-wrap gap-2 p-3 border-b border-border text-xs">
              <span className="text-text-secondary">Filter:</span>
              <button onClick={() => setJurisFilter("")} className={`px-2 py-0.5 rounded border ${jurisFilter==="" ? "bg-brand-50 border-brand-200" : "bg-surface border-border"}`}>All</button>
              <button onClick={() => setJurisFilter("IN")} className={`px-2 py-0.5 rounded border ${jurisFilter==="IN" ? "bg-[var(--warning-light)] border-[var(--warning-border)] text-[var(--warning-text)]" : "bg-surface border-border"}`}>IN (monthly · INR)</button>
              <button onClick={() => setJurisFilter("US")} className={`px-2 py-0.5 rounded border ${jurisFilter==="US" ? "bg-slate-50 border-slate-200" : "bg-surface border-border"}`}>US</button>
              {jurisFilter==="IN" && <span className="text-warning-text">Showing India monthly runs — currency INR, PT column where applicable</span>}
            </div>
            <div className="table-scroll">
              <table className="table-base table-compact w-full text-sm">
                <caption className="sr-only">Pay runs of this deployment</caption>
                <thead>
                  <tr>
                    <th scope="col">Run</th>
                    <th scope="col">Period</th>
                    <th scope="col">Jurisdiction</th>
                    <th scope="col">Rule pack</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="num">Headcount</th>
                    <th scope="col" className="num">Gross</th>
                    <th scope="col" className="num">Net</th>
                    <th scope="col">Currency</th>
                    <th scope="col">Created</th>
                    <th scope="col"><span className="sr-only">Open</span></th>
                    <th scope="col"><span className="sr-only">Recon/Export</span></th>
                  </tr>
                </thead>
                <tbody>
                  {(jurisFilter ? runs.filter(r => (r.jurisdiction||"").toUpperCase()===jurisFilter) : runs).map((run) => (
                    <tr key={run.id}>
                      <td>#{run.id}</td>
                      <td>{periodName(run.period_id)}</td>
                      <td>
                        {run.jurisdiction ?? "—"}{" "}
                        <span className="ml-1 inline-flex text-xs px-1.5 py-0.5 rounded border">{(run as any).run_type || "regular"}</span>
                        {run.jurisdiction === "IN" && (
                          <span className="ml-2 inline-flex text-xs px-1.5 py-0.5 rounded border border-[var(--warning-border)] bg-[var(--warning-light)] text-[var(--warning-text)]">
                            pending_verification
                          </span>
                        )}
                        {run.currency && <span className="ml-1 text-xs text-text-secondary">· {run.currency}</span>}
                      </td>
                      <td className="font-mono text-xs">{run.rule_pack_id ? `${run.rule_pack_id} v1.0.0` : "—"} {run.jurisdiction==="IN" && <span className="text-warning-text">· monthly</span>}</td>
                      <td>
                        <StatusPill status={run.status} dot />
                      </td>
                      <td className="num tabular-nums">{run.headcount}</td>
                      <td className="num tabular-nums">{money(run.total_gross)}</td>
                      <td className="num tabular-nums">{money(run.total_net)}</td>
                      <td className="text-xs">{run.currency || tenantCurrency}{run.jurisdiction==="IN" && <span className="ml-1 text-warning-text">· PT where applicable</span>}</td>
                      <td>{fmtDate(run.created_at)}</td>
                      <td>
                        <Link
                          to={tenantNav.to(`/platform/payroll/runs/${run.id}`)}
                          className="text-brand-700 hover:underline"
                        >
                          Open run #{run.id}
                        </Link>
                      </td>
                      <td className="text-xs">
                        <Link to={tenantNav.to(`/platform/payroll/runs/${run.id}`)} className="text-brand-700 hover:underline mr-2">Recon</Link>
                        {run.status==="Approved" && <span className="text-text-secondary">· {run.jurisdiction==="IN" ? "NEFT" : "NACHA"}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </SectionCard>

      <PayrollLinks current="runs" />
    </Layout>
  )
}
