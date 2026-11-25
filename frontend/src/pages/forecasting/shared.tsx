/**
 * Shared building blocks for the forecasting workspace (FD-06).
 *
 * Everything here is shaped by backend/app/schemas/forecasting.py and the
 * services behind it — values are only ever displayed as the contract
 * returns them:
 *   - MAPE is a fraction (0.10 == 10 %) and is formatted locally with the
 *     % glyph; it is never rescaled before being sent to a threshold input.
 *   - Costs are unit-less numbers (the contract returns no currency) and
 *     every cost surface carries the statutory label the response sent.
 *   - Assumptions may arrive as a JSON-encoded string (the ORM column) or
 *     a parsed list; `normaliseAssumptions` handles both.
 */
import type {
  AssumptionsWire,
  ForecastSeriesPoint,
  ScenarioAssumption,
} from "@/types"
import api, { errorMessage } from "@/lib/api"
import { saveBlob } from "@/lib/imports"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/inputs"

/** The roles the backend allows on every forecasting endpoint
 * (`MANAGER_ROLES` in `app/api/deps.py`). Below Manager the server answers
 * 403, so the screen is gated here as well — with a readable explanation. */
export const FORECAST_ROLES = ["SuperAdmin", "HR", "Manager"]

export function canForecast(role?: string | null): boolean {
  return !!role && FORECAST_ROLES.includes(role)
}

/* ------------------------------------------------------------------ *
 * Formatting
 * ------------------------------------------------------------------ */

const HOURS = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })
const MONEY = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/** Hours and counts — two decimals at most, no invented precision. */
export function fmtNum(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—"
  return HOURS.format(v)
}

/** Cost numbers. The contract returns no currency, so none is shown. */
export function fmtCost(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—"
  return MONEY.format(v)
}

/** Fraction → percentage string with the % glyph. Contract value 0.10 → "10.0%". */
export function fmtPct(fraction: number | null | undefined, digits = 1): string {
  if (fraction === null || fraction === undefined || Number.isNaN(fraction)) return "—"
  return `${(fraction * 100).toFixed(digits)}%`
}

export function fmtDate(v?: string | null): string {
  if (!v) return "—"
  return String(v).slice(0, 10)
}

export function fmtDateTime(v?: string | null): string {
  if (!v) return "—"
  return String(v).replace("T", " ").slice(0, 16)
}

/**
 * A load-failure message shaped for the role reality of this workspace:
 * every endpoint answers 403 to anything below Manager, so a rejection
 * names the likely cause instead of a bare "failed".
 * Re-exported from lib/api for global reuse; kept here for backward compat.
 */
export { readableLoadError } from "@/lib/api"

/* ------------------------------------------------------------------ *
 * Assumptions — the backend's own table, mirrored honestly
 * ------------------------------------------------------------------ */

export interface AssumptionTypeDoc {
  key: string
  unit: "ratio" | "absolute" | "days" | "method" | "percent"
  label: string
  description: string
  /** `percent` assumptions must sit in [0, 100]; `method` picks from a list. */
  kind: "number" | "method"
}

/** Mirrors ASSUMPTION_TYPES in backend/app/services/forecasting.py. */
export const ASSUMPTION_TYPES: AssumptionTypeDoc[] = [
  {
    key: "demand_multiplier",
    unit: "ratio",
    kind: "number",
    label: "Demand multiplier",
    description: "Multiply all forecast values by this ratio.",
  },
  {
    key: "demand_delta",
    unit: "absolute",
    kind: "number",
    label: "Demand delta",
    description: "Add a fixed amount (hours) to all forecast values.",
  },
  {
    key: "headcount_cap",
    unit: "absolute",
    kind: "number",
    label: "Headcount cap",
    description: "Cap forecast values at this maximum.",
  },
  {
    key: "seasonality_override",
    unit: "days",
    kind: "number",
    label: "Seasonality override",
    description: "Change the seasonality period, in days.",
  },
  {
    key: "method_override",
    unit: "method",
    kind: "method",
    label: "Method override",
    description: "Force a specific forecasting method.",
  },
  {
    key: "attrition_rate",
    unit: "percent",
    kind: "number",
    label: "Attrition rate (% / year)",
    description:
      "Annualised attrition as a percent per year: compounds demand DOWN day by day.",
  },
  {
    key: "hire_rate",
    unit: "percent",
    kind: "number",
    label: "Hire rate (% / year)",
    description:
      "Annualised hiring growth as a percent per year: compounds demand UP day by day.",
  },
  {
    key: "leave_rate",
    unit: "percent",
    kind: "number",
    label: "Leave rate (%)",
    description: "Share of hours lost to leave — scales every period down.",
  },
  {
    key: "wage_growth_pct",
    unit: "percent",
    kind: "number",
    label: "Wage growth (% / year)",
    description:
      "Compounds the hourly RATE of cost projections month by month; no demand change.",
  },
]

export const PERCENT_ASSUMPTION_KEYS = new Set([
  "attrition_rate",
  "hire_rate",
  "leave_rate",
  "wage_growth_pct",
])

export const METHOD_OVERRIDE_VALUES = ["seasonal_naive", "holt_winters", "auto"] as const

export function assumptionTypeOf(key: string): AssumptionTypeDoc | undefined {
  return ASSUMPTION_TYPES.find((t) => t.key === key)
}

/**
 * Assumptions arrive as a JSON string or a list depending on the response
 * path; this returns the list either way (never inventing values).
 */
export function normaliseAssumptions(raw: AssumptionsWire | null | undefined): ScenarioAssumption[] {
  if (raw == null) return []
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw || "[]")
      return Array.isArray(parsed) ? (parsed as ScenarioAssumption[]) : []
    } catch {
      return []
    }
  }
  return Array.isArray(raw) ? raw : []
}

/** Clients-side mirror of the backend's validate_assumptions, for inline errors. */
export function validateAssumptionsInline(
  assumptions: ScenarioAssumption[]
): string | null {
  if (assumptions.length === 0) return "At least one assumption is required."
  for (const a of assumptions) {
    const doc = assumptionTypeOf(a.key)
    if (!doc) return `Unknown assumption type: ${a.key}`
    if (doc.unit !== a.unit) return `Assumption "${doc.label}" expects unit "${doc.unit}", got "${a.unit}"`
    if (PERCENT_ASSUMPTION_KEYS.has(a.key)) {
      const v = Number(a.value)
      if (!Number.isFinite(v)) return `Assumption "${doc.label}" expects a numeric percent`
      if (v < 0 || v > 100) return `Assumption "${doc.label}" must be between 0 and 100 (percent)`
    }
  }
  return null
}

/* ------------------------------------------------------------------ *
 * Accuracy statuses
 * ------------------------------------------------------------------ */

export const ACCURACY_STATUS_TONE: Record<string, "green" | "amber" | "rose" | "slate"> = {
  ok: "green",
  review: "amber",
  degraded: "rose",
}

export function statusToneOf(status: string): "green" | "amber" | "rose" | "slate" {
  return ACCURACY_STATUS_TONE[status] ?? "slate"
}

/**
 * The honest explanation of an accuracy row's missing MAPE
 * (backend/app/services/forecast_accuracy.py): a ratio against a zero
 * actual is undefined, so when every measured day recorded zero actual
 * hours the MAPE cannot be computed — the row is flagged `review`, never
 * promoted to `ok`.
 */
export function explainMissingMape(row: {
  mape?: number | null
  sample_size: number
}): string | null {
  if (row.mape == null) {
    if (row.sample_size === 0) {
      return "No measurable day pairs existed for this window, so no error could be computed; the row is flagged review rather than ok."
    }
    return "MAPE is unavailable: every measured day recorded zero actual hours, so a percentage error cannot be formed. The row is flagged review, never promoted to ok."
  }
  return null
}

/* ------------------------------------------------------------------ *
 * CSV download for the cost forecast (the released /csv op)
 * ------------------------------------------------------------------ */

/**
 * Fetched with the shared client — the endpoint needs the bearer token,
 * a navigation could never carry one.
 */
export async function fetchCostForecastCSV(
  runId: number,
  version: number
): Promise<{ blob: Blob; filename: string }> {
  const response = await api.get(`/forecasting/runs/${runId}/cost-forecast/csv?version=${version}`, {
    responseType: "blob",
  })
  const disposition = (response.headers?.["content-disposition"] as string | undefined) ?? ""
  const match = /filename="?([^";]+)"?/.exec(disposition)
  return {
    blob: response.data as Blob,
    filename: match?.[1] ?? `cost_forecast_run${runId}_v${version}.csv`,
  }
}

export async function downloadCostForecastCSV(runId: number, version: number): Promise<void> {
  const { blob, filename } = await fetchCostForecastCSV(runId, version)
  saveBlob(blob, filename)
}

/* ------------------------------------------------------------------ *
 * Tiny presentational helpers (same idiom as People / RosterBuilder)
 * ------------------------------------------------------------------ */

export function Field({
  id,
  label,
  required,
  hint,
  children,
}: {
  id: string
  label: string
  required?: boolean
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium text-text-secondary mb-1">
        {label}
        {required && (
          <span className="text-error-text ml-0.5" aria-hidden="true">
            *
          </span>
        )}
      </label>
      {children}
      {hint && (
        <p className="mt-1 text-xs text-text-secondary">{hint}</p>
      )}
    </div>
  )
}

export function SimpleTable({
  caption,
  columns,
  rows,
  empty,
}: {
  caption: string
  columns: string[]
  rows: React.ReactNode[][]
  empty?: string
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <caption className="sr-only">{caption}</caption>
        <thead className="border-b border-border">
          <tr>
            {columns.map((c) => (
              <th key={c} scope="col" className="px-3 py-2 text-text-secondary">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-2">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
          {rows.length === 0 && empty && (
            <tr>
              <td colSpan={columns.length} className="px-3 py-6 text-center text-text-secondary">
                {empty}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

/* ------------------------------------------------------------------ *
 * The one chart: dependency-free SVG bars with a confidence band
 * ------------------------------------------------------------------ */

export interface ChartPoint {
  label: string
  value: number
  lower?: number | null
  upper?: number | null
}

/**
 * Bars for the predicted value with the lower/upper bound drawn as a band
 * behind them. Built in the component, by hand, with no dependency — a huge
 * series is capped (and says so) so the SVG stays renderable.
 */
export function SeriesChart({
  points,
  caption,
  maxBars = 60,
}: {
  points: ChartPoint[]
  caption: string
  maxBars?: number
}) {
  if (points.length === 0) return null
  const shown = points.slice(0, maxBars)
  const hasBand = shown.every((p) => p.upper != null && p.lower != null)
  const bandUpper = hasBand ? shown.map((p) => p.upper as number) : []
  const bandLower = hasBand ? shown.map((p) => p.lower as number) : []
  const maxVal = Math.max(0.0001, ...shown.map((p) => p.value), ...bandUpper)
  const minVal = hasBand ? Math.min(0, ...bandLower) : 0
  const range = maxVal - minVal || 1

  const W = 640
  const H = 190
  const padL = 8
  const padR = 8
  const padT = 14
  const padB = 30
  const plotH = H - padT - padB
  const slot = (W - padL - padR) / shown.length
  const barW = Math.max(2, Math.min(18, slot * 0.7))
  const y = (v: number) => padT + plotH - ((v - minVal) / range) * plotH

  return (
    <figure className="m-0">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        height={190}
        role="img"
        aria-label={caption}
      >
        {/* zero line */}
        {(() => { const lineStyle = { stroke: "var(--border-strong)", strokeWidth: 1 } as React.CSSProperties; return (
        <line
          x1={padL}
          x2={W - padR}
          y1={y(minVal)}
          y2={y(minVal)}
          style={lineStyle}
        />
        )})()}
        {hasBand &&
          shown.map((p, i) => {
            const lo = y(p.lower as number)
            const hi = y(p.upper as number)
            const x = padL + i * slot + (slot - barW) / 2
            const bandStyle = { fill: "var(--brand-100)" } as React.CSSProperties
            return (
              <rect
                key={`band-${i}`}
                x={x}
                y={hi}
                width={barW}
                height={Math.max(1, lo - hi)}
                rx={1}
                style={bandStyle}
              />
            )
          })}
        {shown.map((p, i) => {
          const x = padL + i * slot + (slot - barW) / 2
          const top = y(Math.max(p.value, minVal))
          const h = Math.max(1, y(minVal) - top)
          const barStyle = { fill: "var(--brand-600)" } as React.CSSProperties
          return (
            <rect
              key={`bar-${i}`}
              x={x}
              y={top}
              width={barW}
              height={h}
              rx={2}
              style={barStyle}
            >
              <title>{`${p.label}: ${fmtNum(p.value)}`}</title>
            </rect>
          )
        })}
        {(() => { const labelStyle = { fill: "var(--fg-muted)", fontSize: 10 } as React.CSSProperties; return (<>
        <text
          x={padL}
          y={H - 8}
          style={labelStyle}
        >
          {shown[0].label}
        </text>
        <text
          x={W - padR}
          y={H - 8}
          textAnchor="end"
          style={labelStyle}
        >
          {shown[shown.length - 1].label}
        </text>
        <text
          x={padL}
          y={padT - 3}
          style={labelStyle}
        >
          max {fmtNum(maxVal)} {hasBand ? "· band = lower–upper bounds" : ""}
        </text>
        </>)})()}
      </svg>
      {points.length > shown.length && (
        <figcaption className="text-xs text-text-secondary mt-1">
          Showing the first {shown.length} of {points.length} points — narrow the window to see more.
        </figcaption>
      )}
    </figure>
  )
}

/** ChartPoint from the API's series shape (date + value + optional bounds). */
export function toChartPoints<T extends { date: string; value: number; lower_bound?: number | null; upper_bound?: number | null }>(
  rows: T[]
): ChartPoint[] {
  return rows.map((r) => ({
    label: fmtDate(r.date),
    value: r.value,
    lower: r.lower_bound ?? null,
    upper: r.upper_bound ?? null,
  }))
}

/** Convenience: {date, value} pairs (e.g. POST /runs body from a series). */
export function toSeriesData(points: { date: string; value: number }[]): ForecastSeriesPoint[] {
  return points.map((p) => ({ date: p.date, value: p.value }))
}
/* ------------------------------------------------------------------ *
 * Assumption editor — rows of key / value / note, unit derived from key
 * ------------------------------------------------------------------ */

export interface AssumptionRowDraft {
  key: string
  value: string
  note: string
}

export function assumptionsToDrafts(list: ScenarioAssumption[]): AssumptionRowDraft[] {
  return list.map((a) => ({
    key: a.key,
    value: a.value == null ? "" : String(a.value),
    note: a.note ?? "",
  }))
}

/** Serialise drafts → contract shape; the error names the first problem. */
export function draftsToAssumptions(
  rows: AssumptionRowDraft[]
): { assumptions: ScenarioAssumption[]; error: string | null } {
  const out: ScenarioAssumption[] = []
  for (const [i, row] of rows.entries()) {
    if (!row.key) {
      if (!row.value && !row.note) continue // untouched blank row
      return { assumptions: [], error: `Row ${i + 1}: pick an assumption type first.` }
    }
    const doc = assumptionTypeOf(row.key)
    if (!doc) return { assumptions: [], error: `Row ${i + 1}: unknown assumption type "${row.key}".` }
    if (row.value === "") {
      return { assumptions: [], error: `Row ${i + 1}: value is required for ${doc.label}.` }
    }
    if (doc.kind === "method") {
      if (!(METHOD_OVERRIDE_VALUES as readonly string[]).includes(row.value)) {
        return { assumptions: [], error: `Row ${i + 1}: ${row.value} is not a valid method.` }
      }
      out.push({ key: doc.key, unit: doc.unit, value: row.value, note: row.note || null })
      continue
    }
    const num = Number(row.value)
    if (!Number.isFinite(num)) {
      return { assumptions: [], error: `Row ${i + 1}: "${row.value}" is not a number.` }
    }
    if (PERCENT_ASSUMPTION_KEYS.has(doc.key) && (num < 0 || num > 100)) {
      return {
        assumptions: [],
        error: `Row ${i + 1}: ${doc.label} must be between 0 and 100 (percent).`,
      }
    }
    out.push({ key: doc.key, unit: doc.unit, value: num, note: row.note || null })
  }
  if (out.length === 0) {
    return { assumptions: [], error: "At least one named assumption is required." }
  }
  return { assumptions: out, error: null }
}

/**
 * The assumption builder: an explicit, named set. Nothing is applied
 * silently — every key, value, unit and note the server returns is shown.
 */
export function AssumptionEditor({
  rows,
  onChange,
  compact = false,
}: {
  rows: AssumptionRowDraft[]
  onChange: (rows: AssumptionRowDraft[]) => void
  compact?: boolean
}) {
  const update = (i: number, patch: Partial<AssumptionRowDraft>) => {
    onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)))
  }
  return (
    <div className="space-y-2">
      {rows.length === 0 && (
        <p className="text-xs text-text-secondary">No assumptions yet — add at least one.</p>
      )}
      {rows.map((row, i) => {
        const doc = assumptionTypeOf(row.key)
        const gridStyle = { gridTemplateColumns: compact ? "1fr 1fr 1fr auto" : "2fr 1fr 2fr auto" } as React.CSSProperties
        return (
          <div
            key={i}
            className="grid gap-2 items-end align-middle"
            style={gridStyle}
          >
            <label className="text-xs font-medium text-text-secondary">
              <span className="sr-only">Assumption type</span>
              <select
                className="input"
                aria-label={`Assumption type, row ${i + 1}`}
                value={row.key}
                onChange={(e) => {
                  const nextDoc = assumptionTypeOf(e.target.value)
                  update(i, { key: e.target.value, value: nextDoc?.kind === "method" ? "" : row.value })
                }}
              >
                <option value="">Pick a type…</option>
                {ASSUMPTION_TYPES.map((t) => (
                  <option key={t.key} value={t.key}>
                    {t.label} ({t.unit})
                  </option>
                ))}
              </select>
            </label>
            {doc?.kind === "method" ? (
              <select
                className="input"
                aria-label={`Assumption value, row ${i + 1}`}
                value={row.value}
                onChange={(e) => update(i, { value: e.target.value })}
              >
                <option value="">Pick a method…</option>
                {METHOD_OVERRIDE_VALUES.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <Input
                type={doc ? "number" : "text"}
                step="any"
                aria-label={`Assumption value, row ${i + 1}`}
                value={row.value}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => update(i, { value: e.target.value })}
                disabled={!row.key}
              />
            )}
            <Input
              aria-label={`Assumption note, row ${i + 1}`}
              placeholder="why (shown with the numbers)"
              value={row.note}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => update(i, { note: e.target.value })}
            />
            <Button
              variant="ghost"
              size="xs"
              type="button"
              aria-label={`Remove assumption row ${i + 1}`}
              onClick={() => onChange(rows.filter((_, j) => j !== i))}
            >
              ✕
            </Button>
          </div>
        )
      })}
      <Button
        variant="secondary"
        size="sm"
        type="button"
        onClick={() => onChange([...rows, { key: "", value: "", note: "" }])}
      >
        Add assumption
      </Button>
    </div>
  )
}
