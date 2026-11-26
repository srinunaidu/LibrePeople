import { useEffect, useState } from "react"
import {
  Button,
  Table,
  EmptyState,
  LoadingRegion,
  SectionCard,
  RetryableAlert,
} from "@/components/ui"
import { IconChart, IconRefresh } from "@/components/icons"
import api, { errorMessage } from "@/lib/api"
import { useAuth } from "@/context/AuthContext"

// Saved views + scheduled reporting (reporting-personalization, Parts E/F).
//
// The screens below are the personal layer over the existing read-only
// reports (joiners/leavers/attrition/payroll-summary): named filter sets a
// REPORTS_ROLES user keeps for themselves or publishes to their role, and
// recurring deliveries that run as the owner through the existing job queue.
// They change no report calculation, masking or file bytes — the server
// builds every run runs-as-owner with the owner's visibility and mask.

export const REPORT_KEYS = ["joiners", "leavers", "attrition", "payroll-summary"] as const
export type ReportKey = (typeof REPORT_KEYS)[number]

export const REPORT_KEY_LABELS: Record<ReportKey, string> = {
  joiners: "Joiners",
  leavers: "Leavers",
  attrition: "Attrition",
  "payroll-summary": "Payroll summary",
}

export const FREQUENCIES = ["daily", "weekly", "monthly"] as const
export const OUTPUT_FORMATS = ["csv", "xlsx"] as const

export const EMPTY_VIEWS_TITLE = "No saved views yet"
export const EMPTY_VIEWS_DESCRIPTION =
  "Name the filter set you use most — the report, the range, the scope — and reopen it in one click."
export const EMPTY_VIEWS_CTA = "Save your first view"

export const EMPTY_SCHEDULES_TITLE = "No scheduled reports yet"
export const EMPTY_SCHEDULES_DESCRIPTION =
  "Pick a report, a rhythm and the people who should receive it. Deliveries run as you, through the job queue."
export const EMPTY_SCHEDULES_CTA = "Schedule your first report"

/** REPORTS_ROLES (reports.py): SuperAdmin, HR, PayrollViewer. */
export function canUsePersonalization(role?: string | null): boolean {
  return role === "SuperAdmin" || role === "HR" || role === "PayrollViewer"
}

/** Publishing a shared view needs HR/SuperAdmin — a Manager or Associate
 *  publish attempt is refused 403, as is a PayrollViewer one. */
export function canShareView(role?: string | null): boolean {
  return role === "SuperAdmin" || role === "HR"
}

export interface ScheduleDraft {
  report_key: string
  frequency: string
  timezone: string
  recipient_user_ids: string
  output_format: string
}

/** Client-side validation mirroring the server's 422s. Returns the first
 *  problem, or null when the draft is submittable. */
export function validateScheduleInput(draft: ScheduleDraft): string | null {
  if (!(REPORT_KEYS as readonly string[]).includes(draft.report_key)) {
    return "Choose one of joiners, leavers, attrition or payroll-summary."
  }
  if (!(FREQUENCIES as readonly string[]).includes(draft.frequency)) {
    return "Frequency must be daily, weekly or monthly."
  }
  try {
    Intl.DateTimeFormat(undefined, { timeZone: draft.timezone })
  } catch {
    return "Timezone must be a valid IANA name, for example Asia/Kolkata."
  }
  const ids = draft.recipient_user_ids
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
  if (ids.length > 0 && ids.some((s) => !/^\d+$/.test(s))) {
    return "Recipients must be a comma-separated list of user ids."
  }
  if (!(OUTPUT_FORMATS as readonly string[]).includes(draft.output_format)) {
    return "Format must be csv or xlsx."
  }
  return null
}

export function parseRecipientIds(raw: string): number[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map(Number)
    .filter((n) => Number.isInteger(n) && n > 0)
}

export interface SavedView {
  id: number
  owner_id: number
  name: string
  report_key: string
  filters: Record<string, unknown>
  visibility: string
  created_at?: string | null
}

export interface ReportSchedule {
  id: number
  owner_id: number
  report_key: string
  filters: Record<string, unknown>
  frequency: string
  timezone: string
  recipient_user_ids: number[]
  output_format: string
  next_due_at?: string | null
  active: boolean
}

export interface ReportRun {
  id: number
  schedule_id: number
  job_id?: number | null
  status: string
  recipient_count: number
  payload_format?: string | null
  has_payload: boolean
  error?: string | null
}

// ---------------------------------------------------------------------------
// Presentational panels (props in, markup out — the empty states AC4 names
// are asserted here, independent of the network).
// ---------------------------------------------------------------------------

export function SavedViewsPanel(props: {
  views: SavedView[]
  canShare: boolean
  onCreate: () => void
  onDelete: (id: number) => void
  onToggleShare: (view: SavedView) => void
}) {
  const { views, canShare, onCreate, onDelete, onToggleShare } = props
  if (views.length === 0) {
    return (
      <EmptyState
        title={EMPTY_VIEWS_TITLE}
        description={EMPTY_VIEWS_DESCRIPTION}
        action={
          <Button variant="primary" type="button" onClick={onCreate}>
            {EMPTY_VIEWS_CTA}
          </Button>
        }
      />
    )
  }
  return (
    <Table
      columns={[
        { key: "name", header: "View", accessor: (v) => <span className="font-medium">{v.name}</span> },
        { key: "report", header: "Report", accessor: (v) => REPORT_KEY_LABELS[v.report_key as ReportKey] ?? v.report_key },
        { key: "visibility", header: "Visibility", accessor: (v) => (v.visibility === "shared" ? "Shared with role" : "Personal") },
        {
          key: "actions", header: "Actions", accessor: (v) => (
            <span className="flex gap-2">
              {canShare && (
                <Button variant="secondary" type="button" onClick={() => onToggleShare(v)}>
                  {v.visibility === "shared" ? "Make personal" : "Share"}
                </Button>
              )}
              <Button variant="secondary" type="button" onClick={() => onDelete(v.id)}>
                Delete
              </Button>
            </span>
          ),
        },
      ]}
      data={views}
      keyAccessor={(v) => v.id}
      caption="Saved report views"
      sortable={false}
    />
  )
}

export function SchedulesPanel(props: {
  schedules: ReportSchedule[]
  runs: ReportRun[]
  onCreate: () => void
  onRunNow: (id: number) => void
  onToggleActive: (schedule: ReportSchedule) => void
  onDelete: (id: number) => void
  onDownload: (run: ReportRun) => void
  busy: boolean
}) {
  const { schedules, runs, onCreate, onRunNow, onToggleActive, onDelete, onDownload, busy } = props
  if (schedules.length === 0) {
    return (
      <EmptyState
        title={EMPTY_SCHEDULES_TITLE}
        description={EMPTY_SCHEDULES_DESCRIPTION}
        action={
          <Button variant="primary" type="button" onClick={onCreate}>
            {EMPTY_SCHEDULES_CTA}
          </Button>
        }
      />
    )
  }
  return (
    <div className="flex flex-col gap-4">
      <Table
        columns={[
          { key: "report", header: "Report", accessor: (s) => <span className="font-medium">{REPORT_KEY_LABELS[s.report_key as ReportKey] ?? s.report_key}</span> },
          { key: "rhythm", header: "Rhythm", accessor: (s) => `${s.frequency} · ${s.timezone}` },
          { key: "recipients", header: "Recipients", accessor: (s) => s.recipient_user_ids.length },
          { key: "next", header: "Next due", accessor: (s) => s.next_due_at ?? "—" },
          { key: "status", header: "Status", accessor: (s) => (s.active ? "Active" : "Paused") },
          {
            key: "actions", header: "Actions", accessor: (s) => (
              <span className="flex flex-wrap gap-2">
                <Button variant="secondary" type="button" disabled={busy} onClick={() => onRunNow(s.id)}>
                  Run now
                </Button>
                <Button variant="secondary" type="button" disabled={busy} onClick={() => onToggleActive(s)}>
                  {s.active ? "Pause" : "Resume"}
                </Button>
                <Button variant="secondary" type="button" disabled={busy} onClick={() => onDelete(s.id)}>
                  Delete
                </Button>
              </span>
            ),
          },
        ]}
        data={schedules}
        keyAccessor={(s) => s.id}
        caption="Scheduled reports"
        sortable={false}
      />
      {runs.length > 0 && (
        <Table
          columns={[
            { key: "run", header: "Run", accessor: (r) => `#${r.id}` },
            { key: "schedule", header: "Schedule", accessor: (r) => `#${r.schedule_id}` },
            { key: "outcome", header: "Outcome", accessor: (r) => r.status },
            { key: "recipients", header: "Recipients", accessor: (r) => r.recipient_count },
            {
              key: "file", header: "File", accessor: (r) => (
                r.has_payload ? (
                  <Button variant="secondary" type="button" onClick={() => onDownload(r)}>
                    Download {r.payload_format ?? "csv"}
                  </Button>
                ) : (
                  <span className="text-text-secondary">No file yet</span>
                )
              ),
            },
          ]}
          data={runs.slice(0, 10)}
          keyAccessor={(r) => r.id}
          caption="Recent deliveries"
          sortable={false}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Wired sections (fetch through the axios instance, which already carries
// the base URL and the session token).
// ---------------------------------------------------------------------------

export function SavedViewsSection() {
  const { user } = useAuth()
  const [views, setViews] = useState<SavedView[] | null>(null)
  const [error, setError] = useState<unknown | null>(null)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState("")
  const [reportKey, setReportKey] = useState<ReportKey>("joiners")
  const [share, setShare] = useState(false)
  const canShare = canShareView(user?.role)

  const load = async () => {
    setError(null)
    try {
      const res = await api.get("/report-views")
      setViews(res.data.views ?? [])
    } catch (err) {
      setViews([])
      setError(err)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const create = async () => {
    if (!name.trim()) return
    try {
      await api.post("/report-views", {
        name: name.trim(),
        report_key: reportKey,
        filters: {},
        visibility: share && canShare ? "shared" : "personal",
      })
      setName("")
      setShare(false)
      setCreating(false)
      await load()
    } catch (err) {
      setError(err)
    }
  }

  const remove = async (id: number) => {
    try {
      await api.delete(`/report-views/${id}`)
      await load()
    } catch (err) {
      setError(err)
    }
  }

  const toggleShare = async (view: SavedView) => {
    try {
      await api.patch(`/report-views/${view.id}`, {
        visibility: view.visibility === "shared" ? "personal" : "shared",
      })
      await load()
    } catch (err) {
      setError(err)
    }
  }

  return (
    <SectionCard compact icon={<IconChart />} title="Saved views"
      description="Your named filter sets for the read-only reports. Shared views open for every role that may view the report.">
      <div className="px-5 py-4" aria-live="polite">
        {error ? (
          <div className="mb-3">
            <RetryableAlert err={error} title="Saved views unavailable" fallback="Saved views unavailable." onRetry={load} />
          </div>
        ) : null}
        {views === null ? (
          <LoadingRegion label="Loading saved views">
            <p className="text-sm text-text-secondary">Loading saved views…</p>
          </LoadingRegion>
        ) : views.length === 0 && !creating ? (
          <SavedViewsPanel views={[]} canShare={canShare} onCreate={() => setCreating(true)} onDelete={remove} onToggleShare={toggleShare} />
        ) : (
          <div className="flex flex-col gap-4">
            {views.length > 0 && (
              <SavedViewsPanel views={views} canShare={canShare} onCreate={() => setCreating(true)} onDelete={remove} onToggleShare={toggleShare} />
            )}
            {creating || views.length === 0 ? (
              <form className="flex flex-wrap items-end gap-2" aria-label="Save a view"
                onSubmit={(e) => { e.preventDefault(); create() }}>
                <label className="text-xs">Name
                  <input className="input" aria-label="View name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Q1 joiners" />
                </label>
                <label className="text-xs">Report
                  <select className="input" aria-label="Report" value={reportKey} onChange={(e) => setReportKey(e.target.value as ReportKey)}>
                    {REPORT_KEYS.map((k) => (
                      <option key={k} value={k}>{REPORT_KEY_LABELS[k]}</option>
                    ))}
                  </select>
                </label>
                {canShare && (
                  <label className="text-xs flex items-center gap-1">Share with role
                    <input type="checkbox" aria-label="Share with role" checked={share} onChange={(e) => setShare(e.target.checked)} />
                  </label>
                )}
                <Button variant="primary" type="submit" disabled={!name.trim()}>{EMPTY_VIEWS_CTA}</Button>
                {views.length > 0 && (
                  <Button variant="secondary" type="button" onClick={() => setCreating(false)}>Cancel</Button>
                )}
              </form>
            ) : (
              <div>
                <Button variant="secondary" type="button" onClick={() => setCreating(true)}>{EMPTY_VIEWS_CTA}</Button>
              </div>
            )}
          </div>
        )}
      </div>
    </SectionCard>
  )
}

export function SchedulesSection() {
  const [schedules, setSchedules] = useState<ReportSchedule[] | null>(null)
  const [runs, setRuns] = useState<ReportRun[]>([])
  const [error, setError] = useState<unknown | null>(null)
  const [creating, setCreating] = useState(false)
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState<ScheduleDraft>({
    report_key: "joiners",
    frequency: "weekly",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone ?? "UTC",
    recipient_user_ids: "",
    output_format: "csv",
  })
  const draftError = validateScheduleInput(draft)

  const load = async () => {
    setError(null)
    try {
      const [s, r] = await Promise.all([
        api.get("/report-schedules"),
        api.get("/report-schedules/runs"),
      ])
      setSchedules(s.data.schedules ?? [])
      setRuns(r.data.runs ?? [])
    } catch (err) {
      setSchedules([])
      setError(err)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const create = async () => {
    if (draftError) return
    setBusy(true)
    try {
      await api.post("/report-schedules", {
        report_key: draft.report_key,
        filters: {},
        frequency: draft.frequency,
        timezone: draft.timezone,
        recipient_user_ids: parseRecipientIds(draft.recipient_user_ids),
        output_format: draft.output_format,
      })
      setCreating(false)
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id: number) => {
    setBusy(true)
    try {
      await api.delete(`/report-schedules/${id}`)
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const toggleActive = async (schedule: ReportSchedule) => {
    setBusy(true)
    try {
      await api.patch(`/report-schedules/${schedule.id}`, { active: !schedule.active })
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const runNow = async (id: number) => {
    setBusy(true)
    try {
      await api.post(`/report-schedules/${id}/run-now`)
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const download = async (run: ReportRun) => {
    try {
      const response = await api.get(`/report-schedules/runs/${run.id}/download`, { responseType: "blob" })
      const url = URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement("a")
      link.href = url
      link.download = `scheduled-report-${run.id}.${run.payload_format ?? "csv"}`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err)
    }
  }

  const set = (key: keyof ScheduleDraft) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => setDraft((d) => ({ ...d, [key]: e.target.value }))

  return (
    <SectionCard compact icon={<IconRefresh />} title="Scheduled reports"
      description="Recurring deliveries that run as you through the job queue. Recipients outside a report's role set get a notice instead of data.">
      <div className="px-5 py-4" aria-live="polite">
        {error ? (
          <div className="mb-3">
            <RetryableAlert err={error} title="Scheduled reports unavailable" fallback="Scheduled reports unavailable." onRetry={load} />
          </div>
        ) : null}
        {schedules === null ? (
          <LoadingRegion label="Loading scheduled reports">
            <p className="text-sm text-text-secondary">Loading scheduled reports…</p>
          </LoadingRegion>
        ) : schedules.length === 0 && !creating ? (
          <SchedulesPanel schedules={[]} runs={[]} onCreate={() => setCreating(true)} onRunNow={runNow} onToggleActive={toggleActive} onDelete={remove} onDownload={download} busy={busy} />
        ) : (
          <div className="flex flex-col gap-4">
            {schedules.length > 0 && (
              <SchedulesPanel schedules={schedules} runs={runs} onCreate={() => setCreating(true)} onRunNow={runNow} onToggleActive={toggleActive} onDelete={remove} onDownload={download} busy={busy} />
            )}
            {creating || schedules.length === 0 ? (
              <form className="flex flex-wrap items-end gap-2" aria-label="Schedule a report"
                onSubmit={(e) => { e.preventDefault(); create() }}>
                <label className="text-xs">Report
                  <select className="input" aria-label="Scheduled report" value={draft.report_key} onChange={set("report_key")}>
                    {REPORT_KEYS.map((k) => (
                      <option key={k} value={k}>{REPORT_KEY_LABELS[k]}</option>
                    ))}
                  </select>
                </label>
                <label className="text-xs">Frequency
                  <select className="input" aria-label="Frequency" value={draft.frequency} onChange={set("frequency")}>
                    {FREQUENCIES.map((f) => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                </label>
                <label className="text-xs">Timezone
                  <input className="input" aria-label="Timezone" value={draft.timezone} onChange={set("timezone")} placeholder="Asia/Kolkata" />
                </label>
                <label className="text-xs">Recipient user ids
                  <input className="input" aria-label="Recipient user ids" value={draft.recipient_user_ids} onChange={set("recipient_user_ids")} placeholder="12, 34" />
                </label>
                <label className="text-xs">Format
                  <select className="input" aria-label="Format" value={draft.output_format} onChange={set("output_format")}>
                    {OUTPUT_FORMATS.map((f) => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                </label>
                <Button variant="primary" type="submit" disabled={busy || draftError !== null}>{EMPTY_SCHEDULES_CTA}</Button>
                {schedules.length > 0 && (
                  <Button variant="secondary" type="button" onClick={() => setCreating(false)}>Cancel</Button>
                )}
                {draftError && <p className="text-xs text-error-text w-full">{draftError}</p>}
              </form>
            ) : (
              <div>
                <Button variant="secondary" type="button" onClick={() => setCreating(true)}>{EMPTY_SCHEDULES_CTA}</Button>
              </div>
            )}
          </div>
        )}
      </div>
    </SectionCard>
  )
}
