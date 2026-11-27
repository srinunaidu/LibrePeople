/**
 * Accuracy (AN-06) — sync a window (POST /forecasting/accuracy/sync) and
 * read the history (GET /forecasting/accuracy) with adjustable thresholds.
 *
 * The honest states the backend documents (forecast_accuracy.py):
 *  - MAPE is a fraction; thresholds too (0.10 == 10 %). Formatted locally
 *    with the % glyph, sent to the server exactly as entered.
 *  - status is RECOMPUTED per request from the row's stored MAPE against
 *    THIS request's thresholds — re-reading under new thresholds works
 *    without re-syncing, and this screen says so.
 *  - a missing MAPE is never "ok": when every measured day recorded zero
 *    actual hours the row is flagged "review" and explains itself inline.
 *  - degraded rows are visually distinct, not just a different word.
 */
import { useEffect, useRef, useState } from "react"
import {Alert,
  Button,
  EmptyState,
  Input,
  SectionCard,
  TableSkeleton, RetryableAlert, StatusPill } from "@/components/ui"
import api from "@/lib/api"
import type { ForecastAccuracyRecordOut, ForecastAccuracySyncResult, PaginatedForecastAccuracy } from "@/types"
import {
  explainMissingMape,
  fmtDate,
  fmtNum,
  fmtPct,
  readableLoadError,
  SimpleTable,
  statusToneOf,
} from "./shared"

const DEFAULT_REVIEW = "0.10"
const DEFAULT_DEGRADED = "0.25"

export default function AccuracyTab() {
  /* ---- history read ------------------------------------------------- */
  const [rows, setRows] = useState<ForecastAccuracyRecordOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState("")
  const [attempt, setAttempt] = useState(0)
  const loadedAttempt = useRef(-1)

  const [reviewThreshold, setReviewThreshold] = useState(DEFAULT_REVIEW)
  const [degradedThreshold, setDegradedThreshold] = useState(DEFAULT_DEGRADED)
  const [windowStart, setWindowStart] = useState("")
  const [windowEnd, setWindowEnd] = useState("")
  const [statusFilter, setStatusFilter] = useState("")

  const thresholdError =
    Number(degradedThreshold) < Number(reviewThreshold)
      ? "The degraded threshold must be at or above the review threshold — the server would refuse, so the read is not sent."
      : null

  useEffect(() => {
    if (loadedAttempt.current === attempt) return
    loadedAttempt.current = attempt
    if (thresholdError) {
      // The thresholds are client-validated exactly as the server does;
      // an invalid pair is never sent.
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setListError("")
    const params = new URLSearchParams()
    params.set("page", String(page))
    params.set("page_size", String(pageSize))
    params.set("review_threshold", reviewThreshold)
    params.set("degraded_threshold", degradedThreshold)
    if (windowStart) params.set("start_date", windowStart)
    if (windowEnd) params.set("end_date", windowEnd)
    if (statusFilter) params.set("status", statusFilter)
    api
      .get<PaginatedForecastAccuracy>(`/forecasting/accuracy?${params.toString()}`)
      .then((res) => {
        if (cancelled) return
        setRows(res.data.items ?? [])
        setTotal(res.data.total ?? 0)
        setPage(res.data.page ?? page)
      })
      .catch((err) => {
        if (cancelled)
          return
        setListError(readableLoadError(err, "The accuracy history could not be loaded."))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [attempt, page, reviewThreshold, degradedThreshold, windowStart, windowEnd, statusFilter, pageSize, thresholdError])

  /* A threshold change re-reads under the new rules. */
  useEffect(() => {
    setAttempt((a) => a + 1)
  }, [reviewThreshold, degradedThreshold, windowStart, windowEnd, statusFilter])
  // `page` participates in the attempt guard through the same attempt key.

  function changePage(next: number) {
    setPage(next)
    setAttempt((a) => a + 1)
  }
  function refresh() {
    setAttempt((a) => a + 1)
  }

  /* ---- window sync -------------------------------------------------- */
  const [syncStart, setSyncStart] = useState("")
  const [syncEnd, setSyncEnd] = useState("")
  const [syncReview, setSyncReview] = useState(DEFAULT_REVIEW)
  const [syncDegraded, setSyncDegraded] = useState(DEFAULT_DEGRADED)
  const [syncing, setSyncing] = useState(false)
  const [syncError, setSyncError] = useState("")
  const [syncResult, setSyncResult] = useState<ForecastAccuracySyncResult | null>(null)

  const syncThresholdError =
    Number(syncDegraded) < Number(syncReview)
      ? "The degraded threshold must be at or above the review threshold."
      : null

  async function handleSync(e: React.FormEvent) {
    e.preventDefault()
    if (syncing || !syncStart || !syncEnd || syncThresholdError) return
    setSyncing(true)
    setSyncError("")
    try {
      const res = await api.post<ForecastAccuracySyncResult>("/forecasting/accuracy/sync", {
        start_date: syncStart,
        end_date: syncEnd,
        review_threshold: Number(syncReview),
        degraded_threshold: Number(syncDegraded),
      })
      setSyncResult(res.data)
      setPage(1)
      refresh()
    } catch (err) {
      setSyncError(readableLoadError(err, "The sync was refused — nothing was written."))
    } finally {
      setSyncing(false)
    }
  }

  /* ------------------------------------------------------------------ */
  return (
    <div className="space-y-5">
      <SectionCard
        title="Sync a window"
        description="Compares each completed run's forecast hours with the actual hours the same window measured (from the demand layer) and writes one row per month bucket. Re-running a window replaces its rows — nothing is stacked twice."
      >
        <form onSubmit={handleSync} className="p-5 space-y-4" aria-label="Run accuracy sync">
          {syncError && (
            <RetryableAlert err={syncError} title="The sync was refused" fallback="The sync was refused." />
          )}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <label className="text-xs font-medium text-text-secondary">
              Window start <span className="text-error-text" aria-hidden="true">*</span>
              <Input type="date" required value={syncStart} onChange={(e) => setSyncStart(e.target.value)} className="mt-1" />
            </label>
            <label className="text-xs font-medium text-text-secondary">
              Window end <span className="text-error-text" aria-hidden="true">*</span>
              <Input type="date" required value={syncEnd} onChange={(e) => setSyncEnd(e.target.value)} className="mt-1" />
            </label>
            <label className="text-xs font-medium text-text-secondary">
              Review threshold (fraction)
              <Input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={syncReview}
                onChange={(e) => setSyncReview(e.target.value)}
                className="mt-1"
              />
            </label>
            <label className="text-xs font-medium text-text-secondary">
              Degraded threshold (fraction)
              <Input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={syncDegraded}
                onChange={(e) => setSyncDegraded(e.target.value)}
                className="mt-1"
              />
            </label>
          </div>
          {syncThresholdError && (
            <p className="text-sm text-error-text" role="alert">
              {syncThresholdError}
            </p>
          )}
          <p className="text-xs text-text-secondary">
            MAPE and thresholds are fractions: 0.10 reads as 10 %. A row reads
            ok at or under the review threshold, review at or under the degraded
            threshold, and degraded beyond it.
          </p>
          <Button type="submit" loading={syncing} disabled={!syncStart || !syncEnd || !!syncThresholdError}>
            Run sync
          </Button>
          {syncResult && (
            <div className="border-t border-border pt-3" role="status">
              <p className="text-sm text-fg font-medium">
                Sync complete: {syncResult.records.length} row(s) written for{" "}
                {fmtDate(syncResult.start_date)} → {fmtDate(syncResult.end_date)},{" "}
                {syncResult.replaced} stored row(s) replaced under thresholds{" "}
                {fmtPct(syncResult.review_threshold)} / {fmtPct(syncResult.degraded_threshold)}.
              </p>
              {syncResult.records.length === 0 && (
                <p className="text-xs text-text-secondary mt-1">
                  No rows: no completed run had forecast results inside the window (or every pair
                  measured zero on both sides), so nothing was written.
                </p>
              )}
            </div>
          )}
        </form>
      </SectionCard>

      <SectionCard
        title="Accuracy history"
        description="Newest first. Status is recomputed on every read from each row's stored MAPE against the thresholds entered here — changing them re-reads without re-syncing."
      >
        <div className="p-5 space-y-4">
          {thresholdError && (
            <Alert tone="error" title="Thresholds are not ordered">
              {thresholdError}
            </Alert>
          )}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <label className="text-xs font-medium text-text-secondary">
              Review threshold
              <Input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={reviewThreshold}
                onChange={(e) => {
                  setReviewThreshold(e.target.value)
                  setPage(1)
                }}
                className="mt-1"
              />
            </label>
            <label className="text-xs font-medium text-text-secondary">
              Degraded threshold
              <Input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={degradedThreshold}
                onChange={(e) => {
                  setDegradedThreshold(e.target.value)
                  setPage(1)
                }}
                className="mt-1"
              />
            </label>
            <label className="text-xs font-medium text-text-secondary">
              Window start
              <Input
                type="date"
                value={windowStart}
                onChange={(e) => {
                  setWindowStart(e.target.value)
                  setPage(1)
                }}
                className="mt-1"
              />
            </label>
            <label className="text-xs font-medium text-text-secondary">
              Window end
              <Input
                type="date"
                value={windowEnd}
                onChange={(e) => {
                  setWindowEnd(e.target.value)
                  setPage(1)
                }}
                className="mt-1"
              />
            </label>
            <label className="text-xs font-medium text-text-secondary">
              Status
              <select
                className="input mt-1"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value)
                  setPage(1)
                }}
              >
                <option value="">All statuses</option>
                <option value="ok">ok</option>
                <option value="review">review</option>
                <option value="degraded">degraded</option>
              </select>
            </label>
          </div>

          {listError && (
            <Alert tone="error" title="The history failed to load">
              <p>{listError}</p>
              <p className="mt-2">
                <Button variant="outline" size="sm" onClick={refresh}>
                  Try again
                </Button>
              </p>
            </Alert>
          )}

          {loading ? (
            <TableSkeleton rows={5} cols={10} />
          ) : rows.length === 0 && !listError && !thresholdError ? (
            <EmptyState
              title="No accuracy rows yet"
              description="Run a sync above for a completed forecast run's window — the rows compare forecast hours with the actual hours the demand layer measured."
            />
          ) : (
            <>
              <p className="text-xs text-text-secondary" role="status">
                {rows.length} of {total} row(s), page {page}
                {" "}· thresholds in force: review ≤ {fmtPct(Number(reviewThreshold))}, degraded ≤ {fmtPct(Number(degradedThreshold))}
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <caption className="sr-only">
                    Forecast-vs-actual accuracy rows with recomputed status
                  </caption>
                  <thead className="border-b border-border">
                    <tr>
                      <th scope="col" colSpan={9} className="px-3 py-2 text-xs text-text-secondary font-normal">
                        Accuracy history — every row's status is recomputed for this request
                      </th>
                    </tr>
                    <tr>
                      <th scope="col" className="px-3 py-2 text-text-secondary">Run</th>
                      <th scope="col" className="px-3 py-2 text-text-secondary">Period</th>
                      <th scope="col" className="px-3 py-2 text-text-secondary">Model version</th>
                      <th scope="col" className="px-3 py-2 text-text-secondary">Method</th>
                      <th scope="col" className="px-3 py-2 text-text-secondary">Forecast h</th>
                      <th scope="col" className="px-3 py-2 text-text-secondary">Actual h</th>
                      <th scope="col" className="px-3 py-2 text-text-secondary">MAPE</th>
                      <th scope="col" className="px-3 py-2 text-text-secondary">MAE / bias</th>
                      <th scope="col" className="px-3 py-2 text-text-secondary">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => {
                      const degraded = row.status === "degraded"
                      const missing = explainMissingMape(row)
                      return (
                        <tr
                          key={row.id}
                          className={`border-b ${degraded ? "bg-error-light" : "border-b border-border"}`}
                        >
                          <td className="px-3 py-2">#{row.forecast_run_id}</td>
                          <td className="px-3 py-2 font-mono text-xs">{row.period}</td>
                          <td className="px-3 py-2 text-xs">{row.model_version}</td>
                          <td className="px-3 py-2 text-xs">{row.method_used}</td>
                          <td className="px-3 py-2">{fmtNum(row.forecast_hours)}</td>
                          <td className="px-3 py-2">{fmtNum(row.actual_hours)}</td>
                          <td className="px-3 py-2">
                            {row.mape == null ? (
                              <span className="text-text-secondary">—</span>
                            ) : (
                              fmtPct(row.mape)
                            )}
                            {missing && (
                              <p className="text-xs text-warning-text mt-0.5 max-w-64" role="note">
                                {missing}
                              </p>
                            )}
                          </td>
                          <td className="px-3 py-2 text-xs">
                            {fmtNum(row.mae)} / {fmtNum(row.bias)}
                            <span className="block text-text-secondary">{row.sample_size} pairs</span>
                          </td>
                          <td className="px-3 py-2">
                            <StatusPill status={row.status} tone={statusToneOf(row.status)} dot />
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center gap-3">
                <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => changePage(page - 1)}>
                  Previous
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page * pageSize >= total}
                  onClick={() => changePage(page + 1)}
                >
                  Next
                </Button>
                <span className="text-xs text-text-secondary">
                  page {page} of {Math.max(1, Math.ceil(total / pageSize))}
                </span>
              </div>
            </>
          )}
        </div>
      </SectionCard>
    </div>
  )
}
