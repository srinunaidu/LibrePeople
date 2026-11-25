/**
 * Demand & drivers — ad-hoc demand series (POST /forecasting/demand/series),
 * driver CSV validation (POST /forecasting/drivers/import) and the honest
 * state of a "driver list".
 *
 * There is NO driver-list read operation in the released contract: the
 * /forecasting/drivers op validates a file and answers with the parsed
 * series, it does not persist anything to list. This screen says so instead
 * of inventing an empty table — a validated file's series stays on screen
 * until it is dismissed.
 */
import { useEffect, useRef, useState } from "react"
import {Alert,
  Button,
  Input,
  SectionCard,
  TableSkeleton, RetryableAlert} from "@/components/ui"
import api, { isRetryable } from "@/lib/api" // RetryableAlert gate
import type { DemandSeriesResponse, DriverCSVResponse } from "@/types"
import {
  Field,
  fmtDate,
  fmtNum,
  readableLoadError,
  SeriesChart,
  SimpleTable,
  toChartPoints,
} from "./shared"

interface RunFromSeriesState {
  name: string
  running: boolean
  error: string
}

/** The column families the validator accepts (demand_importer.py). */
const DATE_COLUMNS = "date, day, work_date, period, ds"
const VALUE_COLUMNS = "value, hours, demand, quantity, amount, y"
const EXTRA_COLUMNS = "location / location_id, role / role_code (optional)"

export default function DemandTab() {
  /* ---- reference data for the location picker ---------------------- */
  const [locations, setLocations] = useState<{ id: number; name: string; code: string }[]>([])
  const [locError, setLocError] = useState("")
  const locAttempt = useRef(-1)
  const [locLoading, setLocLoading] = useState(true)

  useEffect(() => {
    if (locAttempt.current === 1) return
    locAttempt.current = 1
    let cancelled = false
    setLocLoading(true)
    api
      .get<{ id: number; name: string; code: string }[]>("/core-hr/locations")
      .then((res) => {
        if (!cancelled) setLocations(res.data)
      })
      .catch((err) => {
        if (!cancelled)
          setLocError(
            readableLoadError(err, "Locations could not be loaded; the query stays unscoped.")
          )
      })
      .finally(() => {
        if (!cancelled) setLocLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  /* ---- ad-hoc series ---------------------------------------------- */
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [locationId, setLocationId] = useState("")
  const [role, setRole] = useState("")
  const [includeTimeEntries, setIncludeTimeEntries] = useState(true)
  const [includeLeave, setIncludeLeave] = useState(true)
  const [includeRoster, setIncludeRoster] = useState(true)
  const [seriesLoading, setSeriesLoading] = useState(false)
  const [seriesError, setSeriesError] = useState("")
  const [series, setSeries] = useState<DemandSeriesResponse | null>(null)

  async function handleBuildSeries(e: React.FormEvent) {
    e.preventDefault()
    if (seriesLoading) return
    setSeriesLoading(true)
    setSeriesError("")
    setSeries(null)
    try {
      const res = await api.post<DemandSeriesResponse>("/forecasting/demand/series", {
        start_date: startDate,
        end_date: endDate,
        location_id: locationId ? Number(locationId) : null,
        role: role.trim() || null,
        include_time_entries: includeTimeEntries,
        include_leave: includeLeave,
        include_roster: includeRoster,
      })
      setSeries(res.data)
    } catch (err) {
      setSeriesError(readableLoadError(err, "The demand series could not be built."))
    } finally {
      setSeriesLoading(false)
    }
  }

  /* ---- driver CSV validate ----------------------------------------- */
  const [file, setFile] = useState<File | null>(null)
  const [driverLoading, setDriverLoading] = useState(false)
  const [driverError, setDriverError] = useState("")
  const [driver, setDriver] = useState<DriverCSVResponse | null>(null)

  async function handleDriverUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!file || driverLoading) return
    setDriverLoading(true)
    setDriverError("")
    setDriver(null)
    try {
      const form = new FormData()
      form.append("file", file)
      const res = await api.post<DriverCSVResponse>("/forecasting/drivers/import", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      setDriver(res.data)
    } catch (err) {
      setDriverError(readableLoadError(err, "The driver CSV could not be validated."))
    } finally {
      setDriverLoading(false)
    }
  }

  /* ---- start a run from either series ------------------------------ */
  const available = series?.series?.length
    ? series.series.map((p) => ({ date: p.date, value: p.value }))
    : driver?.series?.length
      ? driver.series.map((p) => ({ date: p.date, value: p.value }))
      : []
  const [runFromSeries, setRunFromSeries] = useState<RunFromSeriesState>({
    name: "",
    running: false,
    error: "",
  })
  const [notice, setNotice] = useState("")

  async function handleRunFromSeries() {
    if (!available.length || runFromSeries.running) return
    setRunFromSeries({ name: runFromSeries.name, running: true, error: "" })
    try {
      const res = await api.post<{ id: number; name: string }>("/forecasting/runs", {
        name: runFromSeries.name.trim() || null,
        series_data: available,
        horizon_days: 30,
        method: "auto",
        seasonality: 7,
        location_id: null,
        role_id: null,
      })
      setRunFromSeries({ name: "", running: false, error: "" })
      // The list lives on the Runs tab; say where to look, never fake it here.
      setNotice(`Run #${res.data.id} "${res.data.name}" created — open the Runs tab to read it.`)
    } catch (err) {
      setRunFromSeries({
        name: runFromSeries.name,
        running: false,
        error: readableLoadError(err, "The forecast run could not be created."),
      })
    }
  }

  return (
    <div className="space-y-5">
      {notice && (
        null /* toast.success replaces Alert success */
      )}

      <SectionCard
        title="Build a demand series from records"
        description="POST /forecasting/demand/series — queries time entries, leave and roster the window covers, and answers the layered hours each day."
      >
        <form onSubmit={handleBuildSeries} className="p-5 space-y-4" aria-label="Build demand series">
          {locError && (
            <div className="alert alert-info" role="status">
              {locError}
            </div>
          )}
          {seriesError && (
            <RetryableAlert err={seriesError} title="The series could not be built" fallback="The series could not be built." />
          )}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Field id="ds-start" label="Start date" required>
              <Input
                id="ds-start"
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </Field>
            <Field id="ds-end" label="End date" required>
              <Input
                id="ds-end"
                type="date"
                required
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </Field>
            <Field id="ds-location" label="Location">
              <select
                id="ds-location"
                className="input"
                value={locationId}
                onChange={(e) => setLocationId(e.target.value)}
                disabled={locLoading}
              >
                <option value="">Any location</option>
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name} ({l.code})
                  </option>
                ))}
              </select>
            </Field>
            <Field
              id="ds-role"
              label="Role (title or code)"
              hint="Exactly what the endpoint accepts — a role title or code, not a job id."
            >
              <Input
                id="ds-role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g. Nurse"
              />
            </Field>
            <div className="flex items-center gap-4 text-xs self-end pb-2">
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
          <div>
            <Button type="submit" loading={seriesLoading} disabled={!startDate || !endDate}>
              Build series
            </Button>
          </div>
          {series && (
            <div className="space-y-3">
              <p className="text-xs text-text-secondary" role="status">
                {series.count} points returned
                {series.series.length > 0 && (
                  <>
                    {" "}
                    · {fmtDate(series.series[0].date)} → {fmtDate(series.series[series.series.length - 1].date)}
                  </>
                )}
                .
              </p>
              {series.series.length > 0 && (
                <>
                  <SeriesChart
                    points={toChartPoints(series.series)}
                    caption={`Demand series: ${series.count} points`}
                  />
                  <SimpleTable
                    caption="Demand series layers, per date"
                    columns={["Date", "Value", "Actual hours", "Leave hours", "Scheduled hours", "Location", "Role"]}
                    rows={series.series.slice(0, 30).map((p) => [
                      fmtDate(p.date),
                      fmtNum(p.value),
                      fmtNum(p.actual_hours ?? null),
                      fmtNum(p.leave_hours ?? null),
                      fmtNum(p.scheduled_hours ?? null),
                      p.location_id ?? "—",
                      p.role ?? "—",
                    ])}
                  />
                  {series.series.length > 30 && (
                    <p className="text-xs text-text-secondary">
                      Showing the first 30 of {series.series.length} rows.
                    </p>
                  )}
                </>
              )}
            </div>
          )}
        </form>
      </SectionCard>

      <SectionCard
        title="Validate a driver CSV"
        description={`POST /forecasting/drivers/import — parses and returns the series; nothing is stored. Accepted columns — date: ${DATE_COLUMNS}; value: ${VALUE_COLUMNS}; extras: ${EXTRA_COLUMNS}.`}
      >
        <form onSubmit={handleDriverUpload} className="p-5 space-y-4" aria-label="Validate driver CSV">
          {driverError && (
            <Alert tone="error" title="The driver CSV was refused">
              {driverError}
            </Alert>
          )}
          <label
            htmlFor="driver-file"
            className="block text-xs font-medium text-text-secondary mb-1"
          >
            Driver CSV (POS sales, foot traffic, census, …)
          </label>
          <Input
            id="driver-file"
            type="file"
            accept=".csv"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null)
              setDriver(null)
            }}
          />
          <div>
            <Button type="submit" loading={driverLoading} disabled={!file}>
              Validate file
            </Button>
          </div>
          {driver && (
            <div className="space-y-3">
              <p className="text-xs text-text-secondary" role="status">
                {driver.count} rows parsed — the screen holds them until you dismiss or replace the
                file; the backend stores nothing.
              </p>
              {driver.series.length > 0 && (
                <>
                  <SeriesChart
                    points={driver.series.map((p) => ({
                      label: fmtDate(p.date),
                      value: p.value,
                    }))}
                    caption={`Driver series: ${driver.count} points`}
                  />
                  <SimpleTable
                    caption="Parsed driver series"
                    columns={["Date", "Value", "Location", "Role"]}
                    rows={driver.series.slice(0, 30).map((p) => [
                      fmtDate(p.date),
                      fmtNum(p.value),
                      p.location_code ?? (p.location_id != null ? String(p.location_id) : "—"),
                      p.role ?? "—",
                    ])}
                  />
                  {driver.series.length > 30 && (
                    <p className="text-xs text-text-secondary">
                      Showing the first 30 of {driver.series.length} rows.
                    </p>
                  )}
                </>
              )}
            </div>
          )}
        </form>
      </SectionCard>

      <SectionCard
        title="Start a forecast run from the series above"
        description="The same series the runs tab fits — handy right after a validated driver import."
      >
        <div className="p-5 space-y-3">
          {available.length === 0 ? (
            <p className="text-xs text-text-secondary">
              Build a series or validate a driver CSV above; the "run" action appears once points
              are on screen.
            </p>
          ) : (
            <>
              {runFromSeries.error && (
                <Alert tone="error" title="The run was refused">
                  {runFromSeries.error}
                </Alert>
              )}
              <div className="flex flex-wrap items-end gap-3">
                <label className="text-xs font-medium text-text-secondary">
                  Run name (optional)
                  <Input
                    value={runFromSeries.name}
                    onChange={(e) =>
                      setRunFromSeries({ ...runFromSeries, name: e.target.value })
                    }
                    className="mt-1 block w-64"
                  />
                </label>
                <Button loading={runFromSeries.running} onClick={handleRunFromSeries}>
                  Run forecast on {available.length} points
                </Button>
              </div>
            </>
          )}
        </div>
      </SectionCard>
    </div>
  )
}
