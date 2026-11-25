/**
 * Run detail — one forecast run with its results, its demand-series shape
 * and its cost forecasts (with versions and the /csv download).
 *
 * Every independent endpoint is settled on its own: a demand-series 404 must
 * not blank the results, and a cost-forecast permission problem must not
 * hide the numbers that did load (People-style allSettled + degraded banner).
 */
import { useEffect, useRef, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import {Alert,
  Button,
  EmptyState,
  Input,
  LoadingRegion,
  PageHeader,
  SectionCard,
  StatCard,
  TableSkeleton, RetryableAlert} from "@/components/ui"
import api, { isRetryable } from "@/lib/api" // RetryableAlert gate
import { useTenantNav } from "@/lib/tenantPath"
import { Layout } from "@/components/Layout"
import type {
  CostForecastOut,
  CostForecastVersionSummary,
  CostForecastVersionSummaryList,
  ForecastResultOut,
  ForecastRunOut,
} from "@/types"
import {
  fmtCost,
  fmtDate,
  fmtDateTime,
  fmtNum,
  fmtPct,
  readableLoadError,
  SeriesChart,
  SimpleTable,
  downloadCostForecastCSV,
} from "./forecasting/shared"

interface DemandSeriesPayload {
  forecast_run_id: number
  metadata: Record<string, unknown>
  count: number
  series: {
    date: string
    value: number
    lower_bound?: number | null
    upper_bound?: number | null
    location_id?: number | null
    location_code?: string | null
    role_id?: number | null
    role?: string | null
  }[]
}

export default function ForecastRunDetail() {
  const { runId: runIdParam } = useParams()
  const runId = Number(runIdParam)
  const navigate = useNavigate()
  const tenantNav = useTenantNav()

  const [run, setRun] = useState<ForecastRunOut | null>(null)
  const [results, setResults] = useState<ForecastResultOut[]>([])
  const [demand, setDemand] = useState<DemandSeriesPayload | null>(null)
  const [costVersions, setCostVersions] = useState<CostForecastVersionSummary[]>([])
  const [loadErrors, setLoadErrors] = useState<string[]>([])
  const [fatalError, setFatalError] = useState("")
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)
  const loadedAttempt = useRef(-1)

  useEffect(() => {
    if (loadedAttempt.current === attempt) return
    loadedAttempt.current = attempt
    if (!Number.isFinite(runId) || runId <= 0) {
      setFatalError("That run id is not a number; the run cannot be opened.")
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setLoadErrors([])
    const runRes = api.get<ForecastRunOut>(`/forecasting/runs/${runId}`)
    const resultsRes = api.get<ForecastResultOut[]>(`/forecasting/runs/${runId}/results`)
    const demandRes = api.get<DemandSeriesPayload>(`/forecasting/runs/${runId}/demand-series`)
    const costRes = api.get<CostForecastVersionSummaryList>(
      `/forecasting/runs/${runId}/cost-forecast`
    )
    void Promise.allSettled([runRes, resultsRes, demandRes, costRes]).then((settled) => {
      if (cancelled) return
      const [sRun, sResults, sDemand, sCost] = settled
      const errors: string[] = []
      if (sRun.status === "fulfilled") {
        setRun(sRun.value.data)
      } else {
        const msg = readableLoadError(sRun.reason, "The forecast run could not be loaded.")
        setFatalError(msg)
      }
      if (sResults.status === "fulfilled") setResults(sResults.value.data)
      else errors.push(`Results: ${readableLoadError(sResults.reason, "")}`)
      if (sDemand.status === "fulfilled") setDemand(sDemand.value.data)
      else errors.push(`Demand series: ${readableLoadError(sDemand.reason, "")}`)
      if (sCost.status === "fulfilled") setCostVersions(sCost.value.data.items ?? [])
      else errors.push(`Cost versions: ${readableLoadError(sCost.reason, "")}`)
      if (errors.length > 0) setLoadErrors(errors)
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [attempt, runId])

  /* ---- cost forecast selection ------------------------------------ */
  const latestVersion = costVersions.length > 0 ? costVersions[0].version : null
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null)
  const [costDetail, setCostDetail] = useState<CostForecastOut | null>(null)
  const [costDetailError, setCostDetailError] = useState("")
  const [costLoading, setCostLoading] = useState(false)
  const [downloadError, setDownloadError] = useState("")
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (selectedVersion == null) return
    let cancelled = false
    setCostLoading(true)
    setCostDetailError("")
    api
      .get<CostForecastOut>(`/forecasting/runs/${runId}/cost-forecast/${selectedVersion}`)
      .then((res) => {
        if (!cancelled) setCostDetail(res.data)
      })
      .catch((err) => {
        if (!cancelled)
          setCostDetailError(readableLoadError(err, "The cost forecast version could not be loaded."))
      })
      .finally(() => {
        if (!cancelled) setCostLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedVersion, runId])

  const [creatingCost, setCreatingCost] = useState(false)
  const [costFormError, setCostFormError] = useState("")
  const [defaultRate, setDefaultRate] = useState("")
  const [roleRates, setRoleRates] = useState<Record<string, string>>({})

  const demandRoles = demand
    ? Array.from(
        new Set(demand.series.map((p) => p.role).filter((r): r is string => !!r))
      )
    : []

  async function handleCreateCost(e: React.FormEvent) {
    e.preventDefault()
    if (!defaultRate || creatingCost) return
    setCreatingCost(true)
    setCostFormError("")
    try {
      const hourly: Record<string, number> = { default: Number(defaultRate) }
      for (const [role, rate] of Object.entries(roleRates)) {
        if (rate !== "" && rate != null) hourly[role] = Number(rate)
      }
      const res = await api.post<CostForecastOut>(`/forecasting/runs/${runId}/cost-forecast`, {
        hourly_costs: hourly,
        start_date: costStartDate || null,
        end_date: costEndDate || null,
      })
      setCostVersions((prev) => [resToSummary(res.data), ...prev])
      setSelectedVersion(res.data.version)
      setNotice(`Cost forecast version ${res.data.version} computed and stored.`)
    } catch (err) {
      setCostFormError(readableLoadError(err, "The cost forecast was refused."))
    } finally {
      setCreatingCost(false)
    }
  }

  const [costStartDate, setCostStartDate] = useState("")
  const [costEndDate, setCostEndDate] = useState("")
  const [notice, setNotice] = useState("")

  function resToSummary(out: CostForecastOut): CostForecastVersionSummary {
    return {
      id: out.id,
      forecast_run_id: out.forecast_run_id,
      version: out.version,
      label: out.label,
      cost_basis: out.cost_basis,
      hourly_costs: out.hourly_costs,
      input_hash: out.input_hash,
      start_date: out.start_date,
      end_date: out.end_date,
      periods: out.periods,
      total_hours: out.total_hours,
      total_cost: out.total_cost,
      created_at: out.created_at,
    }
  }

  useEffect(() => {
    if (selectedVersion == null && latestVersion != null) setSelectedVersion(latestVersion)
  }, [latestVersion, selectedVersion])

  async function handleDownload() {
    if (selectedVersion == null) return
    setDownloading(true)
    setDownloadError("")
    void downloadCostForecastCSV(runId, selectedVersion)
      .catch((err: unknown) => {
        setDownloadError(readableLoadError(err, "The CSV could not be downloaded."))
      })
      .finally(() => setDownloading(false))
  }

  /* ------------------------------------------------------------------ */
  if (fatalError && !run) {
    return (
      <Layout>
        <div className="space-y-4">
          <RetryableAlert err={fatalError} title="Run unavailable" fallback="Run unavailable." />
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
    <div>
      <PageHeader compact
        icon={<span aria-hidden="true">📈</span>}
        title={run ? `Run — ${run.name}` : "Forecast run"}
        description={
          run
            ? `#${run.id} · ${run.method} · horizon ${run.horizon_days} days · data ${fmtDate(
                run.data_start_date
              )} → ${fmtDate(run.data_end_date)}`
            : "Loading…"
        }
        actions={
          <Button variant="secondary" onClick={() => navigate(tenantNav.to("/forecasting"))}>
            Back to runs
          </Button>
        }
      />

      <nav aria-label="Breadcrumb" className="sr-only">
        <Link to="/forecasting">All runs</Link>
      </nav>

      {loading && (
        <LoadingRegion label="Loading the run, its results, demand series and cost forecasts">
          <TableSkeleton rows={3} cols={6} />
        </LoadingRegion>
      )}

      {loadErrors.length > 0 && (
        <div className="alert alert-error mb-4" role="alert">
          <p className="font-semibold">Some parts of this run failed to load.</p>
          <ul className="list-disc pl-5 text-sm mt-1">
            {loadErrors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
          <p className="mt-2">
            <Button variant="outline" size="sm" onClick={() => setAttempt((a) => a + 1)}>
              Try again
            </Button>
          </p>
        </div>
      )}

      {notice && (
        null /* toast.success replaces Alert success */
      )}

      {run && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 my-5">
            <StatCard label="Status" value={run.status} />
            <StatCard
              label="Backtest MAPE"
              value={fmtPct(run.backtest_mape)}
              hint={run.backtest_holdout_days != null ? `${run.backtest_holdout_days}-day holdout` : undefined}
            />
            <StatCard label="Backtest MASE" value={fmtNum(run.backtest_mase)} />
            <StatCard label="Created" value={fmtDateTime(run.created_at)} />
          </div>

          {/* Results */}
          <SectionCard compact
            title="Forecast results"
            description={
              results.length > 0
                ? `${results.length} horizon points, ordered by step. The band is the confidence interval the model returned.`
                : "This run carries no forecast values."
            }
            className="mb-5"
          >
            <div className="p-5">
              {results.length > 0 ? (
                <>
                  <SeriesChart
                    points={results.map((r) => ({
                      label: fmtDate(r.forecast_date),
                      value: r.predicted_value,
                      lower: r.lower_bound ?? null,
                      upper: r.upper_bound ?? null,
                    }))}
                    caption="Predicted hours per date with the confidence band"
                  />
                  <SimpleTable
                    caption="Forecast results by horizon step"
                    columns={["Step", "Date", "Predicted (h)", "Lower", "Upper", "Method", "Rule version"]}
                    rows={results.map((r) => [
                      r.horizon_step,
                      fmtDate(r.forecast_date),
                      fmtNum(r.predicted_value),
                      fmtNum(r.lower_bound ?? null),
                      fmtNum(r.upper_bound ?? null),
                      r.method_used ?? "—",
                      r.rule_version ?? "—",
                    ])}
                  />
                </>
              ) : (
                <EmptyState
                  title="No results"
                  description="The run completed with no per-period predictions (or the results endpoint was unavailable — see the banner above)."
                />
              )}
            </div>
          </SectionCard>

          {/* Demand series */}
          <SectionCard compact
            title="Demand series"
            description="The run's results formatted for the scheduler (lower/upper carried through as bounds)."
            className="mb-5"
          >
            <div className="p-5">
              {demand && demand.series.length > 0 ? (
                <>
                  <SeriesChart
                    points={demand.series.map((p) => ({
                      label: fmtDate(p.date),
                      value: p.value,
                      lower: p.lower_bound ?? null,
                      upper: p.upper_bound ?? null,
                    }))}
                    caption={`Demand series: ${demand.count} points`}
                  />
                  <p className="text-xs text-text-secondary">
                    {demand.count} points
                    {demandRoles.length > 0 ? <> · roles: {demandRoles.join(", ")}</> : ""}
                  </p>
                </>
              ) : (
                <EmptyState
                  title="No demand series returned"
                  description="The run has results but no scheduler-format series (or the endpoint failed — see the banner above)."
                />
              )}
            </div>
          </SectionCard>

          {/* Cost forecast */}
          <SectionCard compact
            title="Cost forecast"
            description="Forecast hours × the hourly rates YOU supply — rates are never guessed, and every version stays retrievable."
          >
            <div className="p-5 space-y-5">
              {/* Create a new version */}
              <form onSubmit={handleCreateCost} aria-label="Create cost forecast" className="border border-border rounded-lg p-4">
                <h3 className="text-sm font-semibold text-fg mb-2">Cost this run (creates a new version)</h3>
                <p className="text-xs text-text-secondary mb-3">
                  The catch-all <em>default</em> rate is required; role-specific rates are optional
                  extra assumptions. The result and every row are labelled{" "}
                  <em>“excludes statutory on-costs”</em>.
                </p>
                {costFormError && (
                  <Alert tone="error" title="The costing was refused">
                    {costFormError}
                  </Alert>
                )}
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <label className="text-xs font-medium text-text-secondary">
                    Default hourly rate
                    <Input
                      type="number"
                      step="any"
                      min="0"
                      required
                      value={defaultRate}
                      onChange={(e) => setDefaultRate(e.target.value)}
                      className="mt-1"
                    />
                  </label>
                  <label className="text-xs font-medium text-text-secondary">
                    Window start (optional)
                    <Input
                      type="date"
                      value={costStartDate}
                      onChange={(e) => setCostStartDate(e.target.value)}
                      className="mt-1"
                    />
                  </label>
                  <label className="text-xs font-medium text-text-secondary">
                    Window end (optional)
                    <Input
                      type="date"
                      value={costEndDate}
                      onChange={(e) => setCostEndDate(e.target.value)}
                      className="mt-1"
                    />
                  </label>
                </div>
                {demandRoles.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-medium text-text-secondary mb-1">
                      Optional role-specific rates (found in the run's demand series)
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {demandRoles.map((role) => (
                        <label key={role} className="text-xs font-medium text-text-secondary">
                          {role}
                          <Input
                            type="number"
                            step="any"
                            min="0"
                            value={roleRates[role] ?? ""}
                            onChange={(e) => setRoleRates({ ...roleRates, [role]: e.target.value })}
                            className="mt-1"
                            placeholder="uses the default"
                          />
                        </label>
                      ))}
                    </div>
                  </div>
                )}
                <div className="mt-3">
                  <Button type="submit" loading={creatingCost} disabled={!defaultRate}>
                    Compute & store version
                  </Button>
                </div>
              </form>

              {/* Version list */}
              {costVersions.length === 0 ? (
                <EmptyState
                  title="No cost forecasts stored for this run"
                  description="Compute one above — each call stores a new version; earlier versions stay intact."
                />
              ) : (
                <SimpleTable
                  caption="Stored cost forecast versions, newest first"
                  columns={["Version", "Window", "Periods", "Total hours", "Total cost", "Rates", "Created", ""]}
                  rows={costVersions.map((v) => [
                    `v${v.version}`,
                    v.start_date || v.end_date
                      ? `${fmtDate(v.start_date)} → ${fmtDate(v.end_date)}`
                      : "whole horizon",
                    v.periods,
                    fmtNum(v.total_hours),
                    fmtCost(v.total_cost),
                    Object.entries(v.hourly_costs)
                      .map(([k, r]) => `${k}:${fmtNum(r)}`)
                      .join(" · "),
                    fmtDateTime(v.created_at),
                    <div key="act" className="flex gap-2">
                      <Button
                        variant={selectedVersion === v.version ? "primary" : "outline"}
                        size="xs"
                        onClick={() => setSelectedVersion(v.version)}
                      >
                        {selectedVersion === v.version ? "Viewing" : "View"}
                      </Button>
                      <Button variant="secondary" size="xs" loading={downloading} onClick={handleDownload}>
                        CSV
                      </Button>
                    </div>,
                  ])}
                />
              )}

              {costDetailError && (
                <Alert tone="error" title="The version could not be loaded">
                  {costDetailError}
                </Alert>
              )}

              {costDetail && (
                <div>
                  <p className="text-xs text-text-secondary mb-2">
                    Version {costDetail.version} · {costDetail.rows.length} rows · labelled “
                    {costDetail.label}” — the model_version behind every row is the run's rule version
                    ({costDetail.input_hash.slice(0, 12)}…).
                  </p>
                  {costLoading ? (
                    <TableSkeleton rows={4} cols={6} />
                  ) : costDetail.rows.length > 0 ? (
                    <SimpleTable
                      caption={`Cost forecast version ${costDetail.version} rows — excludes statutory on-costs`}
                      columns={["Period", "Location", "Role", "Hours", "Hourly cost", "Cost — excludes statutory on-costs"]}
                      rows={costDetail.rows.map((r, i) => [
                        r.period,
                        `${r.location_code ?? r.location_id ?? "—"}`,
                        r.role ?? r.role_code ?? "—",
                        fmtNum(r.hours),
                        fmtCost(r.hourly_cost),
                        <strong key={`c${i}`}>{fmtCost(r.cost)}</strong>,
                      ])}
                    />
                  ) : (
                    <p className="text-xs text-text-secondary">This version has no rows.</p>
                  )}
                  {downloadError && (
                    <Alert tone="error" title="The CSV could not be downloaded">
                      {downloadError}
                    </Alert>
                  )}
                </div>
              )}
            </div>
          </SectionCard>
        </>
      )}
    </div>
    </Layout>
  )
}
