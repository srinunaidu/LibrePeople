/**
 * Runs — list forecast runs and create a new one.
 *
 * Create flow honesty: the engine needs an actual series (`series_data` is
 * required by the contract), so this screen builds it from one of two
 * explicit sources — the deployment's own demand layer
 * (POST /forecasting/demand/series, previewed BEFORE anything is run) or a
 * pasted `date,value` CSV — and every run links to its detail page.
 */
import { useCallback, useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import {Alert,
  Button,
  EmptyState,
  Input,
  LoadingRegion,
  SectionCard,
  TableSkeleton, RetryableAlert} from "@/components/ui"
import { StatusPill } from "@/components/ui/status-pill"
import api, { isRetryable } from "@/lib/api" // RetryableAlert gate
import { useTenantNav } from "@/lib/tenantPath"
import type { ForecastRunOut } from "@/types"
import {
  Field,
  fmtDate,
  fmtDateTime,
  fmtNum,
  fmtPct,
  readableLoadError,
  SimpleTable,
  toChartPoints,
  SeriesChart,
} from "./shared"

interface LooseLocation {
  id: number
  name: string
  code: string
}
interface LooseJob {
  id: number
  title: string
}

interface PreviewSeries {
  count: number
  points: { date: string; value: number }[]
  role?: string | null
}

const METHODS = [
  { value: "auto", label: "Auto (server resolves the method)" },
  { value: "seasonal_naive", label: "Seasonal naive" },
  { value: "holt_winters", label: "Holt-Winters" },
]

export default function RunsTab() {
  const tenantNav = useTenantNav()

  /* ---- loads ------------------------------------------------------ */
  const [runs, setRuns] = useState<ForecastRunOut[]>([])
  const [locations, setLocations] = useState<LooseLocation[]>([])
  const [jobs, setJobs] = useState<LooseJob[]>([])
  const [runsError, setRunsError] = useState("")
  const [refError, setRefError] = useState("")
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)
  const loadedAttempt = useRef(-1)

  useEffect(() => {
    if (loadedAttempt.current === attempt) return
    loadedAttempt.current = attempt
    let cancelled = false
    setLoading(true)
    setRunsError("")
    setRefError("")
    const [runRes, locRes, jobRes] = [
      api.get<ForecastRunOut[]>("/forecasting/runs?limit=100"),
      api.get<LooseLocation[]>("/core-hr/locations"),
      api.get<LooseJob[]>("/jobs/"),
    ]
    void Promise.allSettled([runRes, locRes, jobRes]).then((settled) => {
      if (cancelled) return
      // One endpoint failing must not blank the tab: the list keeps rolling
      // while the reference data for the create form degrades with a note.
      const [withRuns, withLoc, withJob] = settled
      if (withRuns.status === "fulfilled") {
        setRuns(withRuns.value.data)
      } else {
        setRunsError(readableLoadError(withRuns.reason, "Could not load the forecast runs."))
      }
      if (withLoc.status === "fulfilled") setLocations(withLoc.value.data)
      if (withJob.status === "fulfilled") setJobs(withJob.value.data)
      const refFailures = [withLoc, withJob].filter((r) => r.status === "rejected")
      if (refFailures.length > 0) {
        setRefError(
          `Location and job lists could not be loaded (${readableLoadError(
            (refFailures[0] as { reason: unknown }).reason,
            "the reference service answered an error",
          )}) — the create form still works, but series pulled from records will not be scoped by location or role.`
        )
      }
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [attempt])

  /* ---- create form ------------------------------------------------ */
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [method, setMethod] = useState("auto")
  const [horizonDays, setHorizonDays] = useState("30")
  const [seasonality, setSeasonality] = useState("7")
  const [source, setSource] = useState<"records" | "paste">("records")

  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [locationId, setLocationId] = useState("")
  const [jobId, setJobId] = useState("")
  const [includeTimeEntries, setIncludeTimeEntries] = useState(true)
  const [includeLeave, setIncludeLeave] = useState(true)
  const [includeRoster, setIncludeRoster] = useState(true)

  const [pasteText, setPasteText] = useState("")

  const [preview, setPreview] = useState<PreviewSeries | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const [previewError, setPreviewError] = useState("")
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState("")
  const [notice, setNotice] = useState("")

  const parsedPaste = useRef<{ points: { date: string; value: number }[]; error: string | null }>({
    points: [],
    error: null,
  })
  if (source === "paste") {
    // Parsed on every render of the paste value — cheap for the sizes a
    // human pastes, and it keeps the "Create" button honest.
    const lines = pasteText.split("\n").map((l) => l.trim()).filter(Boolean)
    const points: { date: string; value: number }[] = []
    let error: string | null = null
    for (let i = 0; i < lines.length; i++) {
      const [d, v, ...extra] = lines[i].split(/[,\t; ]+/)
      if (!d || !v || extra.length > 0) {
        error = `Line ${i + 1} ("${lines[i]}") is not "date,value".`
        break
      }
      const value = Number(v)
      if (!Number.isFinite(value)) {
        error = `Line ${i + 1}: value "${v}" is not a number.`
        break
      }
      if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) {
        error = `Line ${i + 1}: date "${d}" must be YYYY-MM-DD.`
        break
      }
      points.push({ date: d, value })
    }
    parsedPaste.current = { points, error }
  }

  const previewPoints =
    source === "paste"
      ? parsedPaste.current.points
      : preview?.points ?? []

  const runSeriesSource =
    source === "paste" ? parsedPaste.current.error : previewError || null

  async function handlePreview() {
    if (!startDate || !endDate) return
    setPreviewing(true)
    setPreviewError("")
    setPreview(null)
    try {
      const job = jobs.find((j) => String(j.id) === jobId)
      const res = await api.post<{
        count: number
        series: { date: string; value: number; role?: string | null }[]
      }>("/forecasting/demand/series", {
        start_date: startDate,
        end_date: endDate,
        location_id: locationId ? Number(locationId) : null,
        role: job ? job.title : null,
        include_time_entries: includeTimeEntries,
        include_leave: includeLeave,
        include_roster: includeRoster,
      })
      setPreview({
        count: res.data.count,
        points: res.data.series.map((p) => ({ date: p.date, value: p.value })),
        role: job?.title ?? null,
      })
    } catch (err) {
      setPreviewError(readableLoadError(err, "The demand series could not be built."))
    } finally {
      setPreviewing(false)
    }
  }

  async function handleCreateRun(e: React.FormEvent) {
    e.preventDefault()
    if (!previewPoints.length || creating) return
    setCreating(true)
    setCreateError("")
    try {
      const res = await api.post<ForecastRunOut>("/forecasting/runs", {
        name: name.trim() || null,
        description: description.trim() || null,
        series_data: previewPoints.map((p) => ({ date: p.date, value: p.value })),
        horizon_days: Number(horizonDays) || 30,
        method,
        seasonality: Number(seasonality) || 7,
        location_id: locationId ? Number(locationId) : null,
        role_id: jobId ? Number(jobId) : null,
      })
      setPreview(null)
      setPasteText("")
      setName("")
      setDescription("")
      setNotice(`Run #${res.data.id} "${res.data.name}" completed with ${res.data.results.length} forecast points.`)
      setAttempt((a) => a + 1)
    } catch (err) {
      setCreateError(readableLoadError(err, "The forecast run could not be created."))
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-5">
      {notice && (
        null /* toast.success replaces Alert success */
      )}

      {runsError && (
        <RetryableAlert err={runsError} title="The run list failed to load" fallback="The run list failed to load." />
      )}

      <section className="card p-5" aria-label="Forecast runs">
        <header className="flex items-start justify-between gap-3 mb-4">
          <div>
            <h2 className="font-semibold text-fg">Forecast runs</h2>
            <p className="text-xs text-text-secondary mt-0.5">
              Newest first. A completed run carries its method, window and backtest error.
            </p>
          </div>
          <Button variant="secondary" size="sm" loading={loading} onClick={() => setAttempt((a) => a + 1)}>
            Refresh
          </Button>
        </header>
        {loading ? (
          <TableSkeleton rows={4} cols={7} />
        ) : runs.length === 0 ? (
          <EmptyState
            title="No forecast runs yet"
            description="Create the first run below: pick a window, preview the demand series, then run the model."
          />
        ) : (
          <SimpleTable
            caption="Forecast runs, newest first"
            columns={["Name", "Status", "Method", "Horizon", "Data window", "Backtest MAPE", "Backtest MASE", "Created", ""]}
            rows={runs.map((r) => [
              <span key="n" className="font-medium text-fg">{r.name}</span>,
              <StatusPill key="s" status={r.status} dot />,
              r.method,
              `${r.horizon_days} d`,
              `${fmtDate(r.data_start_date)} → ${fmtDate(r.data_end_date)}`,
              fmtPct(r.backtest_mape),
              fmtNum(r.backtest_mase),
              fmtDateTime(r.created_at),
              <Link
                key="open"
                to={tenantNav.to(`/forecasting/runs/${r.id}`)}
                className="text-brand-700 hover:underline text-sm font-medium"
              >
                Open
              </Link>,
            ])}
          />
        )}
      </section>

      <SectionCard
        icon={<span aria-hidden="true">＋</span>}
        title="Create a forecast run"
        description={
          refError
            ? "Reference data is degraded — the form still runs, but record-based series will be unscoped."
            : "Preview the demand series first; nothing is fitted until you run it."
        }
      >
        <form onSubmit={handleCreateRun} className="p-5 space-y-4" aria-label="Create forecast run">
          {refError && (
            <div className="alert alert-info" role="status">
              {refError}
            </div>
          )}
          {createError && (
            <Alert tone="error" title="The run was refused">
              {createError}
            </Alert>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="run-name" label="Run name">
              <Input
                id="run-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Defaults to the date/time"
                maxLength={200}
              />
            </Field>
            <Field id="run-description" label="Description">
              <Input
                id="run-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </Field>
            <Field id="run-method" label="Method">
              <select
                id="run-method"
                className="input"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
              >
                {METHODS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field id="run-horizon" label="Horizon (days)" required>
                <Input
                  id="run-horizon"
                  type="number"
                  min={1}
                  max={365}
                  required
                  value={horizonDays}
                  onChange={(e) => setHorizonDays(e.target.value)}
                />
              </Field>
              <Field id="run-seasonality" label="Seasonality (days)">
                <Input
                  id="run-seasonality"
                  type="number"
                  min={2}
                  max={365}
                  value={seasonality}
                  onChange={(e) => setSeasonality(e.target.value)}
                />
              </Field>
            </div>
          </div>

          {/* Series source */}
          <div className="flex gap-2" role="tablist" aria-label="Series source">
            <button
              type="button"
              role="tab"
              aria-selected={source === "records"}
              onClick={() => setSource("records")}
              className={`tab ${source === "records" ? "tab-active" : "tab-idle"}`}
            >
              From records
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={source === "paste"}
              onClick={() => setSource("paste")}
              className={`tab ${source === "paste" ? "tab-active" : "tab-idle"}`}
            >
              Paste values
            </button>
          </div>

          {source === "records" ? (
            <fieldset className="border border-border rounded-lg p-4">
              <legend className="text-xs font-medium text-text-secondary px-1">
                Window read from the demand layer (POST /forecasting/demand/series)
              </legend>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <Field id="run-start" label="Start date" required>
                  <Input
                    id="run-start"
                    type="date"
                    required
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </Field>
                <Field id="run-end" label="End date" required>
                  <Input
                    id="run-end"
                    type="date"
                    required
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </Field>
                <Field id="run-location" label="Location">
                  <select
                    id="run-location"
                    className="input"
                    value={locationId}
                    onChange={(e) => setLocationId(e.target.value)}
                  >
                    <option value="">Any location</option>
                    {locations.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.name} ({l.code})
                      </option>
                    ))}
                  </select>
                </Field>
                <Field id="run-job" label="Role (job)">
                  <select
                    id="run-job"
                    className="input"
                    value={jobId}
                    onChange={(e) => setJobId(e.target.value)}
                  >
                    <option value="">Any role</option>
                    {jobs.map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.title}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="flex items-center gap-4 text-xs">
                  <label className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={includeTimeEntries}
                      onChange={(e) => setIncludeTimeEntries(e.target.checked)}
                    />
                    Time entries
                  </label>
                  <label className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={includeLeave}
                      onChange={(e) => setIncludeLeave(e.target.checked)}
                    />
                    Leave
                  </label>
                  <label className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={includeRoster}
                      onChange={(e) => setIncludeRoster(e.target.checked)}
                    />
                    Roster
                  </label>
                </div>
              </div>
            </fieldset>
          ) : (
            <Field
              id="run-paste"
              label="Series values — one `date,value` per line"
              required
              hint="Dates in YYYY-MM-DD. The server fits the engine on exactly these numbers."
            >
              <textarea
                id="run-paste"
                className="input min-h-[120px] font-mono text-xs"
                rows={6}
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                placeholder={"2026-09-01,48\n2026-09-02,52"}
              />
            </Field>
          )}

          {runSeriesSource && (
            <Alert tone="error" title="The series is not ready">
              {runSeriesSource}
            </Alert>
          )}

          {source === "records" && (
            <div>
              <Button
                type="button"
                variant="secondary"
                loading={previewing}
                disabled={!startDate || !endDate}
                onClick={handlePreview}
              >
                {previewing ? "Building series…" : "Preview series"}
              </Button>
              {preview && (
                <p className="text-xs text-text-secondary mt-2" role="status">
                  {preview.count} points
                  {preview.role ? <> for role “{preview.role}”</> : ""}
                  {preview.points.length > 0 && (
                    <>
                      {" "}
                      · {fmtDate(preview.points[0].date)} → {fmtDate(preview.points[preview.points.length - 1].date)}
                    </>
                  )}
                  {" "}· previewed, not yet fitted.
                </p>
              )}
              {preview && preview.points.length > 0 && (
                <div className="mt-3">
                  <SeriesChart
                    points={toChartPoints(preview.points.map((p) => ({ ...p })))}
                    caption={`Demand series preview: ${preview.count} points`}
                  />
                </div>
              )}
            </div>
          )}

          <div className="flex items-center gap-3">
            <Button
              type="submit"
              loading={creating}
              disabled={previewPoints.length === 0}
            >
              Run the forecast
            </Button>
            <p className="text-xs text-text-secondary">
              {previewPoints.length === 0
                ? "Preview a series first — the engine needs an actual time series."
                : `${previewPoints.length} points staged.`}
            </p>
          </div>
        </form>
      </SectionCard>
    </div>
  )
}
