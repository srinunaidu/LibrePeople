import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { addDays, eachDayOfInterval, format } from "date-fns"
import { Layout } from "@/components/Layout"
import {
  Button,
  Table,
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  StatusPill,
  type Tone, RetryableAlert, TableSkeleton} from "@/components/ui"
import {
  IconAlert,
  IconCalendar,
  IconCheck,
  IconClock,
  IconRefresh,
  IconUsers,
} from "@/components/icons"
import api from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import { useAuth } from "@/context/AuthContext"
import type {
  AutoCreateAttendanceResponse,
  DraftAdjustmentResponse,
  Employee,
  RosterAssignment,
  RosterAttendanceResponse,
  RosterDeviationsResponse,
  RosterDraftDetail,
  RosterGenerateResponse,
  RosterUnfilledSlot,
  RosterVersionDetail,
  RosterVersionRow,
  RosterWeightBreakdown,
  ShiftTemplate,
  VersionCompareResponse,
} from "@/types"

/**
 * The roles the backend allows on the solver-driven roster endpoints
 * (`MANAGER_ROLES` in `app/api/deps.py`). Anything below Manager is served a
 * 403, so the screen is gated here as well rather than with a wall of errors.
 */
const ROSTER_ROLES = ["SuperAdmin", "HR", "Manager"]

/** The demand grid and the solver payload are capped at one month. */
const MAX_DAYS = 31

interface DraftReviewState {
  draft_id: number
  status?: string
  solver_status?: string
  timed_out?: boolean
  objective_value?: number | null
  weight_breakdown?: RosterWeightBreakdown
  assignments: RosterAssignment[]
  unfilled_slots: RosterUnfilledSlot[]
  violations?: string[]
  valid?: boolean
  input_hash?: string
}

interface VersionListMeta {
  page?: number
  page_size?: number
  total?: number
  total_pages?: number
}

type TabKey = "draft" | "versions" | "attendance"

const TABS: { key: TabKey; label: string }[] = [
  { key: "draft", label: "Draft" },
  { key: "versions", label: "Versions" },
  { key: "attendance", label: "Attendance" },
]

const SEVERITY_TONE: Record<string, string> = {
  critical: "badge-rose",
  warning: "badge-amber",
  info: "badge-slate",
}

const DIFF_TONE: Record<string, string> = {
  added: "badge-green",
  removed: "badge-rose",
  changed: "badge-amber",
}

/** Read a displayable message out of any HTTP error the backend raises. */
function errText(e: unknown, fallback: string): string {
  const anyE = e as {
    response?: { data?: { detail?: unknown; error?: { message?: string } } }
  }
  const data = anyE?.response?.data
  if (typeof data?.detail === "string" && data.detail) return data.detail
  if (typeof data?.error?.message === "string" && data.error.message) return data.error.message
  const detail = data?.detail
  if (detail && typeof detail === "object") {
    const d = detail as { message?: string; error?: string }
    if (typeof d.message === "string" && d.message) return d.message
    if (typeof d.error === "string" && d.error) return d.error
  }
  return fallback
}

const iso = (d: Date) => format(d, "yyyy-MM-dd")

function shortTime(v?: string | null) {
  if (!v) return "\u2014"
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v.replace("T", " ").slice(0, 16)
  return new Intl.DateTimeFormat(undefined, { dateStyle: "short", timeStyle: "short" }).format(d)
}

export default function RosterBuilder() {
  const { user } = useAuth()
  const allowed = ROSTER_ROLES.includes(user?.role ?? "")

  const [activeTab, setActiveTab] = useState<TabKey>("draft")

  /* Lookups ---------------------------------------------------------- */
  const [lookupsLoading, setLookupsLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
  const [locations, setLocations] = useState<{ id: number; code: string; name: string }[]>([])
  const [templates, setTemplates] = useState<ShiftTemplate[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [selectedEmployees, setSelectedEmployees] = useState<number[]>([])

  /* Draft: generate form --------------------------------------------- */
  const [locationCode, setLocationCode] = useState("")
  const [from, setFrom] = useState(iso(new Date()))
  const [to, setTo] = useState(iso(addDays(new Date(), 6)))
  const [demand, setDemand] = useState<Record<number, number>>({})
  const [maxShifts, setMaxShifts] = useState("")
  const [maxWeeklyHours, setMaxWeeklyHours] = useState("")
  const [minRestHours, setMinRestHours] = useState("11")
  const [maxConsecutiveDays, setMaxConsecutiveDays] = useState("6")
  const [timeLimit, setTimeLimit] = useState("30")
  const [generating, setGenerating] = useState(false)
  const [draftError, setDraftError] = useState("")
  const [notice, setNotice] = useState("")

  /* Draft: review ----------------------------------------------------- */
  const [draft, setDraft] = useState<DraftReviewState | null>(null)
  const [adjustPick, setAdjustPick] = useState<Record<string, string>>({})
  const [adjusting, setAdjusting] = useState("")
  const [publishing, setPublishing] = useState(false)

  const restDates = useMemo<string[]>(() => {
    try {
      const start = new Date(`${from}T00:00:00`)
      const end = new Date(`${to}T00:00:00`)
      if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) return []
      const span = eachDayOfInterval({ start, end })
      // A quarter-long range would produce endless grid columns and a solver
      // problem nobody can review in one screen.
      if (span.length > MAX_DAYS) return []
      return span.map((d) => iso(d))
    } catch {
      return []
    }
  }, [from, to])
  const rangeTooLong = restDates.length === 0
  const hasDemand = templates.some((t) => (demand[t.id] ?? 0) > 0) && restDates.length > 0

  /* Versions ---------------------------------------------------------- */
  const [versions, setVersions] = useState<RosterVersionRow[]>([])
  const [versionMeta, setVersionMeta] = useState<VersionListMeta>({})
  const [versionPage, setVersionPage] = useState(1)
  const [versionsLoading, setVersionsLoading] = useState(false)
  const [versionsError, setVersionsError] = useState("")
  const [versionDetail, setVersionDetail] = useState<RosterVersionDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [compare, setCompare] = useState<VersionCompareResponse | null>(null)
  const [compareBase, setCompareBase] = useState("")
  const [compareLoading, setCompareLoading] = useState(false)
  const [compareError, setCompareError] = useState("")
  const [rolling, setRolling] = useState("")
  const versionsLoaded = useRef(false)

  /* Attendance --------------------------------------------------------- */
  const [attendanceVersion, setAttendanceVersion] = useState("")
  const [attendance, setAttendance] = useState<RosterAttendanceResponse | null>(null)
  const [attendanceLoading, setAttendanceLoading] = useState(false)
  const [attendanceError, setAttendanceError] = useState("")
  const [autoCreating, setAutoCreating] = useState(false)
  const [grace, setGrace] = useState("5")
  const [deviations, setDeviations] = useState<RosterDeviationsResponse | null>(null)
  const [deviationsLoading, setDeviationsLoading] = useState(false)
  const [deviationsError, setDeviationsError] = useState("")

  /* ------------------------------------------------------------------ *
   * Lookups                                                             *
   * ------------------------------------------------------------------ */

  const loadLookups = useCallback(async () => {
    setLookupsLoading(true)
    setLoadError("")
    try {
      const safe = async (path: string) => {
        try {
          const r = await api.get(path)
          return Array.isArray(r.data) ? r.data : []
        } catch {
          return []
        }
      }
      const [locData, tplData, employeeData] = await Promise.all([
        safe("/core-hr/locations"),
        safe("/scheduling/shift-templates"),
        fetchAllEmployees()
          .then(({ items }) => items)
          .catch(() => []),
      ])
      const locs = locData as { id: number; code: string; name: string }[]
      const tpls = tplData as ShiftTemplate[]
      const emps = employeeData as Employee[]
      setLocations(locs)
      setTemplates(tpls)
      setEmployees(emps)
      setSelectedEmployees(emps.map((x) => x.id))
      if (locs.length) setLocationCode(locs[0].code)
    } finally {
      setLookupsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (allowed) void loadLookups()
    else setLookupsLoading(false)
  }, [allowed, loadLookups])

  /* ------------------------------------------------------------------ *
   * Names helper — employee ids are numeric everywhere on these screens. *
   * ------------------------------------------------------------------ */

  const employeeName = useCallback(
    (id?: number | null) => {
      if (id === undefined || id === null || Number.isNaN(id)) return "\u2014"
      const e = employees.find((x) => x.id === id)
      return e ? `${e.first_name} ${e.last_name}` : `Employee #${id}`
    },
    [employees]
  )

  const applyDraftResult = (data: RosterGenerateResponse | RosterDraftDetail, timedOut?: boolean) => {
    setAdjustPick({})
    setDraft({
      draft_id: data.draft_id,
      status: data.status,
      solver_status: data.solver_status ?? undefined,
      timed_out: timedOut,
      objective_value: data.objective_value,
      weight_breakdown: data.weight_breakdown,
      unfilled_slots: data.unfilled_slots ?? data.unfilled ?? [],
      assignments: data.assignments ?? [],
      violations: [],
      valid: true,
      input_hash: data.input_hash,
    })
  }

  /* ------------------------------------------------------------------ *
   * Draft: generate, review, adjust, publish                            *
   * ------------------------------------------------------------------ */

  const generate = async () => {
    setDraftError("")
    setNotice("")
    setGenerating(true)
    try {
      const slots: Record<string, unknown>[] = []
      templates.forEach((tpl: ShiftTemplate) => {
        const headcount = demand[tpl.id] ?? 0
        if (headcount <= 0) return
        restDates.forEach((date, i) => {
          slots.push({
            id: `${tpl.code}_${date}_${i}`,
            date,
            location: locationCode,
            role: tpl.code,
            start_time: tpl.start_time,
            end_time: tpl.end_time,
            is_night: tpl.is_night,
            headcount: Number(headcount),
            required: false,
          })
        })
      })
      const constraints: Record<string, unknown> = {
        min_rest_hours: Number(minRestHours) || 11,
        max_consecutive_days: Number(maxConsecutiveDays) || 6,
      }
      if (maxShifts) constraints.max_shifts_per_employee = Number(maxShifts)
      if (maxWeeklyHours) constraints.max_weekly_hours = Number(maxWeeklyHours)
      const payload = {
        start_date: from,
        end_date: to,
        location_code: locationCode,
        employees: employees
          .filter((e: Employee) => selectedEmployees.includes(e.id))
          .map((e) => ({ id: e.id, night_ok: true })),
        slots,
        constraints,
        time_limit_seconds: Number(timeLimit) || 30,
      }
      const r = await api.post<RosterGenerateResponse>("/scheduling/rosters/generate", payload)
      applyDraftResult(r.data, r.data.timed_out)
      if (r.data.timed_out) {
        setNotice(
          "The solver reached its time limit — the draft is partial and shows which slots were left unfilled."
        )
      } else {
        setNotice(
          `Draft roster ${r.data.draft_id} generated — review it below, then publish it as an immutable version.`
        )
      }
    } catch (e) {
      setDraftError(errText(e, "The solver could not generate a roster"))
    } finally {
      setGenerating(false)
    }
  }

  const adjust = async (slotInstance: string, action: "reassign" | "unassign") => {
    if (!draft) return
    setDraftError("")
    if (action === "reassign" && !adjustPick[slotInstance]) {
      setDraftError("Choose an employee before applying the change.")
      return
    }
    setAdjusting(slotInstance)
    try {
      const body: { slot_instance_id: string; action: string; employee_id?: number } = {
        slot_instance_id: slotInstance,
        action,
      }
      if (action === "reassign") body.employee_id = Number(adjustPick[slotInstance])
      const r = await api.post<DraftAdjustmentResponse>(
        `/scheduling/rosters/draft/${draft.draft_id}/adjust`,
        body
      )
      setDraft((prev) =>
        prev
          ? {
              ...prev,
              draft_id: r.data.draft_id,
              assignments: r.data.assignments,
              unfilled_slots: r.data.unfilled_slots,
              violations: r.data.violations,
              valid: r.data.valid,
              timed_out: false,
            }
          : prev
      )
      setNotice(
        r.data.valid
          ? "Adjustment applied — all hard constraints still hold."
          : `Adjustment saved ${r.data.violations.length} violation(s); the server will refuse to publish until they are resolved.`
      )
    } catch (e) {
      setDraftError(errText(e, "The adjustment was refused"))
    } finally {
      setAdjusting("")
    }
  }

  const publish = async () => {
    if (!draft) return
    setDraftError("")
    setNotice("")
    setPublishing(true)
    try {
      // Caller-generated key so a retry after a network failure cannot
      // publish the roster twice.
      const key = crypto.randomUUID()
      const r = await api.post<{ id?: number }>(
        "/scheduling/rosters/publish",
        { draft_id: draft.draft_id, notify: true },
        { headers: { "Idempotency-Key": key } }
      )
      setNotice(
        r.data?.id !== undefined
          ? `Roster version ${r.data.id} is published — the published version is immutable.`
          : "The roster version is published."
      )
      setDraft(null)
      versionsLoaded.current = false
      void loadVersions(1)
    } catch (e) {
      setDraftError(errText(e, "Publishing was refused — the draft may violate a hard constraint"))
    } finally {
      setPublishing(false)
    }
  }

  /* ------------------------------------------------------------------ *
   * Versions                                                            *
   * ------------------------------------------------------------------ */

  const loadVersions = useCallback(async (page: number) => {
    setVersionsLoading(true)
    setVersionsError("")
    try {
      const r = await api.get("/scheduling/rosters/versions", { params: { page, page_size: 20 } })
      const body = r.data as { items?: RosterVersionRow[]; meta?: VersionListMeta } | RosterVersionRow[]
      const items: RosterVersionRow[] = Array.isArray(body)
        ? body
        : ((body as { items?: RosterVersionRow[] }).items ?? [])
      setVersions(items)
      setVersionMeta(Array.isArray(body) ? {} : ((body as { meta?: VersionListMeta }).meta ?? {}))
      setVersionPage(page)
      versionsLoaded.current = true
    } catch (e) {
      // Mark the list as attempted even on failure: the effect below fires
      // on every render while the guards are open, and a persistent failure
      // must surface as the error alert, not as an infinite retry loop.
      versionsLoaded.current = true
      setVersionsError(errText(e, "Failed to load roster versions"))
    } finally {
      setVersionsLoading(false)
    }
  }, [])

  const loadVersionDetail = async (id: number) => {
    setDetailLoading(true)
    setVersionsError("")
    setCompare(null)
    try {
      const r = await api.get<RosterVersionDetail>(`/scheduling/rosters/versions/${id}`)
      setVersionDetail(r.data)
      setCompareBase("")
    } catch (e) {
      setVersionsError(errText(e, "Failed to load the roster version"))
    } finally {
      setDetailLoading(false)
    }
  }

  const loadCompare = async () => {
    if (!versionDetail || !compareBase) return
    setCompareLoading(true)
    setCompareError("")
    try {
      const r = await api.get<VersionCompareResponse>(
        `/scheduling/rosters/versions/${versionDetail.id}/compare`,
        { params: { base_version_id: Number(compareBase) } }
      )
      setCompare(r.data)
    } catch (e) {
      setCompareError(errText(e, "The comparison failed"))
    } finally {
      setCompareLoading(false)
    }
  }

  const rollForward = async (version: RosterVersionRow) => {
    setRolling(`v${version.id}`)
    setVersionsError("")
    try {
      const r = await api.post<{ draft_id: number }>(
        `/scheduling/rosters/versions/${version.id}/draft`,
        {}
      )
      setNotice(`Draft ${r.data.draft_id} copied from version ${version.id} — review it in the Draft tab.`)
      const d = await api.get<RosterDraftDetail>(`/scheduling/rosters/draft/${r.data.draft_id}`)
      applyDraftResult(d.data)
      setActiveTab("draft")
    } catch (e) {
      setVersionsError(errText(e, "The draft could not be copied"))
    } finally {
      setRolling("")
    }
  }

  const reviewDraft = async (id: number) => {
    setDraftError("")
    try {
      const r = await api.get<RosterDraftDetail>(`/scheduling/rosters/draft/${id}`)
      applyDraftResult(r.data)
      setNotice(`Draft ${id} loaded for review — adjust and publish it below.`)
      setActiveTab("draft")
    } catch (e) {
      setVersionsError(errText(e, "The draft could not be loaded"))
    }
  }

  /* ------------------------------------------------------------------ *
   * Attendance                                                          *
   * ------------------------------------------------------------------ */

  const publishedVersions = versions.filter((v) => v.status === "published")

  const loadAttendance = useCallback(async (versionId: string) => {
    setAttendanceLoading(true)
    setAttendanceError("")
    setDeviations(null)
    setAttendance(null)
    try {
      const r = await api.get<RosterAttendanceResponse>(`/scheduling/rosters/${versionId}/attendance`)
      setAttendance(r.data)
    } catch (e) {
      setAttendanceError(errText(e, "Failed to load attendance for this version"))
    } finally {
      setAttendanceLoading(false)
    }
  }, [])

  const loadDeviations = async () => {
    if (!attendanceVersion || !attendance) return
    setDeviationsLoading(true)
    setDeviationsError("")
    try {
      const r = await api.get<RosterDeviationsResponse>(
        `/scheduling/rosters/${attendanceVersion}/attendance/deviations`,
        { params: { grace_minutes: Number(grace) || 5 } }
      )
      setDeviations(r.data)
    } catch (e) {
      setDeviationsError(errText(e, "Failed to load deviations for this version"))
    } finally {
      setDeviationsLoading(false)
    }
  }

  const autoCreate = async () => {
    if (!attendanceVersion) return
    setAutoCreating(true)
    setAttendanceError("")
    try {
      const r = await api.post<AutoCreateAttendanceResponse>(
        `/scheduling/rosters/${attendanceVersion}/attendance/auto-create`,
        { source: "Roster Builder" }
      )
      setNotice(
        `Kiosk entries written: ${r.data.created_count} created, ${r.data.skipped_count} already had a time entry.`
      )
      await loadAttendance(attendanceVersion)
    } catch (e) {
      setAttendanceError(errText(e, "Auto-create was refused"))
    } finally {
      setAutoCreating(false)
    }
  }

  // Versions back the Versions tab and the version pickers of the other tabs,
  // so they are loaded once when either tab becomes active.
  useEffect(() => {
    if (
      (activeTab === "versions" || activeTab === "attendance") &&
      !versionsLoaded.current &&
      !versionsLoading
    ) {
      void loadVersions(1)
    }
  }, [activeTab, versionsLoaded, versionsLoading, loadVersions])

  if (!allowed) {
    return (
      <Layout>
        <PageHeader compact
          icon={<IconCalendar />}
          title="Roster Builder"
          description="Generate a draft roster with the solver, adjust it manually and publish it as an immutable version."
        />
        <RetryableAlert err={user?.role || "unknown"} title="Not permitted" fallback="Not permitted." />
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader compact
        icon={<IconCalendar />}
        title="Roster Builder"
        description="Generate a draft roster with the solver, review and adjust the assignments, then publish an immutable version."
        actions={
          <Link to="/scheduling" className="btn btn-secondary">
            Shift templates & swaps
          </Link>
        }
      />

      {notice && <Alert tone="success">{notice}</Alert>}
      {draftError && (
        <Alert tone="error" title="Roster action failed">
          {draftError}
        </Alert>
      )}
      {versionsError && (
        <Alert tone="error" title="Versions action failed">
          {versionsError}
        </Alert>
      )}
      {attendanceError && (
        <Alert tone="error" title="Attendance action failed">
          {attendanceError}
        </Alert>
      )}

      <div className="tablist" role="tablist" aria-label="Roster builder views">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            id={`rb-tab-${t.key}`}
            aria-selected={activeTab === t.key}
            aria-controls={`rb-panel-${t.key}`}
            onClick={() => setActiveTab(t.key)}
            className={`tab ${activeTab === t.key ? "tab-active" : "tab-idle"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`rb-panel-${activeTab}`} aria-labelledby={`rb-tab-${activeTab}`} className="mt-4">
        {activeTab === "draft" && (
          <>
            <SectionCard compact
              icon={<IconRefresh />}
              title="Generate a draft"
              description="Pick the period and the headcount per shift template, set the constraints, and run the solver. Nothing goes live until you publish."
            >
              {lookupsLoading ? (
                <LoadingRegion label="Loading locations, shift templates and employees">
                  <div className="skeleton h-24 m-4" />
                </LoadingRegion>
              ) : loadError ? (
                <Alert
                  tone="error"
                  title="Reference data unavailable"
                  action={
                    <Button variant="secondary" size="sm" type="button" onClick={loadLookups}>
                      Try again
                    </Button>
                  }
                >
                  {loadError}
                </Alert>
              ) : (
                <>
                  {templates.length === 0 && (
                    <EmptyState
                      title="No shift templates yet"
                      description="A draft is generated from demand defined by shift templates. Define templates on the Scheduling screen first."
                      action={
                        <Link to="/scheduling" className="btn btn-primary btn-sm">
                          Open Scheduling
                        </Link>
                      }
                    />
                  )}
                  <div className="toolbar flex-wrap">
                    <div className="field min-w-[180px]">
                      <label htmlFor="rb-location" className="field-label">Location</label>
                      <select
                        id="rb-location"
                        className="input"
                        value={locationCode}
                        onChange={(e) => setLocationCode(e.target.value)}
                      >
                        {locations.map((l) => (
                          <option key={l.id} value={l.code}>
                            {l.code} — {l.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor="rb-from" className="field-label">Period start</label>
                      <input
                        id="rb-from"
                        type="date"
                        className="input"
                        value={from}
                        max={to}
                        onChange={(e) => setFrom(e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="rb-to" className="field-label">Period end</label>
                      <input
                        id="rb-to"
                        type="date"
                        className="input"
                        value={to}
                        min={from}
                        onChange={(e) => setTo(e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="rb-limit" className="field-label">Solver limit (s)</label>
                      <input
                        id="rb-limit"
                        type="number"
                        min={1}
                        className="input w-24"
                        value={timeLimit}
                        onChange={(e) => setTimeLimit(e.target.value)}
                      />
                    </div>
                  </div>

                  {rangeTooLong && from > to && (
                    <div className="px-4 pt-3">
                      <Alert tone="error">The period start is after its end. Pick a valid range.</Alert>
                    </div>
                  )}

                  {rangeTooLong && to >= from && from && to && (
                    <div className="px-4 pt-3">
                      <Alert tone="error">
                        The period stretches past {MAX_DAYS} days. Pick a range of at most {MAX_DAYS} days — a
                        longer draft cannot be reviewed in one screen.
                      </Alert>
                    </div>
                  )}

                  {templates.length > 0 && restDates.length > 0 && (
                    <>
                      <Table
                        className="border-t border-border"
                        columns={[
                          { key: "tpl", header: "Shift template", accessor: (tpl) => (
                            <span>
                              <span className="font-medium whitespace-nowrap">{tpl.code} — {tpl.name}</span>
                              <span className="block text-xs text-text-secondary font-normal">
                                {tpl.start_time}–{tpl.end_time}{tpl.is_night ? " · night" : ""}
                              </span>
                            </span>
                          ) },
                          ...restDates.map((d, i) => ({
                            key: d,
                            header: d.slice(5),
                            headerClassName: "num",
                            accessor: (tpl: ShiftTemplate) => (
                              <>
                                <label className="sr-only" htmlFor={`rb-dem-${tpl.id}-${i}`}>
                                  Headcount for {tpl.code} on {d}
                                </label>
                                <input
                                  id={`rb-dem-${tpl.id}-${i}`}
                                  type="number"
                                  min={0}
                                  max={12}
                                  className="input w-16 px-1.5 text-right"
                                  aria-label={`Headcount for ${tpl.code} on ${d}`}
                                  value={demand[tpl.id] ?? 0}
                                  onChange={(e) =>
                                    setDemand((prev) => ({
                                      ...prev,
                                      [tpl.id]: Math.max(0, Math.floor(Number(e.target.value) || 0)),
                                    }))
                                  }
                                />
                              </>
                            ),
                          })),
                        ]}
                        data={templates}
                        keyAccessor={(tpl) => tpl.id}
                        caption="Headcount demand per shift template"
                        sortable={false}
                      />
                      <p className="px-4 py-2 text-xs text-text-secondary border-b border-border">
                        The headcount applies to every day of the period. {restDates.length} day(s) in scope.
                      </p>
                    </>
                  )}

                  <div className="px-4 pt-3">
                    <div className="toolbar rounded-md border border-border p-0">
                      <div className="field">
                        <label htmlFor="rb-mxshifts" className="field-label">Max shifts / employee</label>
                        <input
                          id="rb-mxshifts"
                          type="number"
                          min={0}
                          className="input w-36"
                          value={maxShifts}
                          onChange={(e) => setMaxShifts(e.target.value)}
                        />
                      </div>
                      <div className="field">
                        <label htmlFor="rb-mxhours" className="field-label">Max weekly hours</label>
                        <input
                          id="rb-mxhours"
                          type="number"
                          min={0}
                          className="input w-36"
                          value={maxWeeklyHours}
                          onChange={(e) => setMaxWeeklyHours(e.target.value)}
                        />
                      </div>
                      <div className="field">
                        <label htmlFor="rb-rest" className="field-label">Min rest (h)</label>
                        <input
                          id="rb-rest"
                          type="number"
                          min={0}
                          className="input w-28"
                          value={minRestHours}
                          onChange={(e) => setMinRestHours(e.target.value)}
                        />
                      </div>
                      <div className="field">
                        <label htmlFor="rb-consec" className="field-label">Max days in a row</label>
                        <input
                          id="rb-consec"
                          type="number"
                          min={1}
                          className="input w-28"
                          value={maxConsecutiveDays}
                          onChange={(e) => setMaxConsecutiveDays(e.target.value)}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="px-4 pt-3">
                    <details>
                      <summary className="cursor-pointer text-sm font-medium">
                        Employees available to the solver ({selectedEmployees.length} of {employees.length} selected)
                      </summary>
                      <ul className="grid grid-cols-2 md:grid-cols-4 gap-2 py-2">
                        {employees.map((e) => (
                          <li key={e.id} className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              id={`rb-emp-${e.id}`}
                              checked={selectedEmployees.includes(e.id)}
                              onChange={(ev) =>
                                setSelectedEmployees((prev) =>
                                  ev.target.checked ? [...prev, e.id] : prev.filter((x) => x !== e.id)
                                )
                              }
                            />
                            <label htmlFor={`rb-emp-${e.id}`}>
                              {e.first_name} {e.last_name}
                            </label>
                          </li>
                        ))}
                      </ul>
                    </details>
                  </div>

                  <div className="px-4 py-4">
                    <Button variant="primary" disabled={generating || rangeTooLong || !locationCode || hasDemand === false}
                      onClick={generate}>
                      <IconCalendar className="w-4 h-4" />
                      {generating ? "Solving…" : "Generate draft roster"}
                    </Button>
                    <p className="field-hint mt-1">
                      The solver runs server-side and can take the whole time limit for a heavy range.
                    </p>
                  </div>
                </>
              )}
            </SectionCard>

            {draft && (
              <SectionCard compact
                icon={<IconClock />}
                title={`Draft ${draft.draft_id} — review`}
                description={`Status ${draft.status ?? "draft"} · solver ${draft.solver_status ?? "\u2014"}${
                  draft.objective_value != null ? ` · objective ${Number(draft.objective_value).toFixed(2)}` : ""
                }`}
                actions={
                  <Button variant="primary" disabled={publishing || draft.valid === false}
                    onClick={publish}>
                    <IconCheck className="w-4 h-4" />
                    {publishing ? "Publishing…" : "Publish version"}
                  </Button>
                }
              >
                {draft.timed_out && (
                  <div className="px-4 pt-4">
                    <Alert tone="info" title="Solver time limit reached">
                      The draft is partial: the slots below could not be filled in time. Generate again
                      with a longer time limit or softer constraints.
                    </Alert>
                  </div>
                )}
                {draft.violations && draft.violations.length > 0 && (
                  <div className="px-4 pt-4">
                    <Alert tone="error" title={`${draft.violations.length} constraint violation(s)`}>
                      <ul className="list-disc pl-5">
                        {draft.violations.map((v, i) => (
                          <li key={i}>{v}</li>
                        ))}
                      </ul>
                    </Alert>
                  </div>
                )}
                {draft.valid === false && (
                  <div className="px-4 pt-4">
                    <Alert tone="error">
                      The draft is not valid — the server would refuse to publish it.
                    </Alert>
                  </div>
                )}

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 px-4 pt-4">
                  <SummaryBox tone="brand" label="Assignments" value={draft.assignments.length} />
                  <SummaryBox
                    tone={draft.unfilled_slots.length > 0 ? "amber" : "green"}
                    label="Unfilled slots"
                    value={draft.unfilled_slots.length}
                  />
                  <div className="card p-4 relative overflow-hidden">
                    <span className="stat-rail stat-rail-teal" aria-hidden="true" />
                    <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">Input hash</p>
                    <p className="text-xs font-mono break-all mt-2">{draft.input_hash || "\u2014"}</p>
                  </div>
                </div>

                <Table
                  className="max-h-[420px] overflow-y-auto mt-4"
                  columns={[
                    { key: "date", header: "Date", accessor: (a) => <span className="whitespace-nowrap">{a.date}</span> },
                    { key: "slot", header: "Slot", accessor: (a) => <span className="font-mono text-xs">{a.slot_id}</span> },
                    { key: "shift", header: "Shift", accessor: (a) => (
                      <span className="whitespace-nowrap">
                        {a.start}–{a.end}
                        {a.is_night ? " (night)" : ""}
                      </span>
                    ) },
                    { key: "employee", header: "Employee", accessor: (a) => employeeName(a.employee_id) },
                    { key: "adjust", header: "Adjust", accessor: (a) => (
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <label className="sr-only" htmlFor={`rb-pick-${a.slot_instance}`}>
                          Change employee for slot {a.slot_id}
                        </label>
                        <select
                          id={`rb-pick-${a.slot_instance}`}
                          className="input w-40 py-1"
                          value={adjustPick[a.slot_instance] ?? String(a.employee_id)}
                          onChange={(e) =>
                            setAdjustPick((p) => ({ ...p, [a.slot_instance]: e.target.value }))
                          }
                        >
                          {employees.map((e) => (
                            <option key={e.id} value={e.id}>
                              {e.first_name} {e.last_name}
                            </option>
                          ))}
                        </select>
                        <Button variant="ghost" disabled={adjusting === a.slot_instance || employees.length === 0}
                          onClick={() => adjust(a.slot_instance, "reassign")}>
                          {adjusting === a.slot_instance ? "Applying…" : "Apply"}
                        </Button>
                        <Button variant="danger" disabled={adjusting === a.slot_instance}
                          onClick={() => adjust(a.slot_instance, "unassign")}>
                          Unassign
                        </Button>
                      </div>
                    ) },
                  ]}
                  data={draft.assignments.slice(0, 200)}
                  keyAccessor={(a) => a.slot_instance}
                  caption="Solver assignments for the draft"
                  sortable={false}
                />
                {draft.assignments.length > 200 && (
                  <p className="px-4 py-2 text-xs text-text-secondary border-t border-border">
                    Showing the first 200 of {draft.assignments.length} assignments. Adjustments are applied per slot.
                  </p>
                )}

                <h3 className="font-semibold px-4 mt-4">Unfilled slots</h3>
                {draft.unfilled_slots.length === 0 ? (
                  <div className="px-4 pb-4">
                    {<Alert tone="success">All slots filled — no further action.</Alert>}
                  </div>
                ) : (
                  <Table
                    className="mt-2"
                    columns={[
                      { key: "date", header: "Date", accessor: (u) => <span className="whitespace-nowrap">{u.date}</span> },
                      { key: "slot", header: "Slot", accessor: (u) => (
                        <span className="font-mono text-xs">
                          {u.slot_id}
                          {u.role ? ` · ${u.role}` : ""}
                        </span>
                      ) },
                      { key: "headcount", header: "Headcount", accessor: (u) => u.headcount, cellClassName: "num" },
                      { key: "cause", header: "Cause", accessor: (u) => (
                        <span className="badge badge-amber" title={u.blocking_constraint ?? undefined}>
                          {u.cause}
                        </span>
                      ) },
                    ]}
                    data={draft.unfilled_slots.map((u, i) => ({ ...u, _k: `${u.slot_id}-${i}` }))}
                    keyAccessor={(u) => u._k}
                    caption="Slots the solver could not fill, with the blocking cause"
                    sortable={false}
                  />
                )}
              </SectionCard>
            )}
          </>
        )}

        {activeTab === "versions" && (
          <SectionCard compact
            icon={<IconCalendar />}
            title="Roster versions"
            description="Every draft and published version. A published version is immutable; new work goes through a draft."
            actions={
              <Button variant="secondary" size="sm" onClick={() => loadVersions(versionPage)}
                disabled={versionsLoading}>
                <IconRefresh className="w-4 h-4" /> Refresh
              </Button>
            }
          >
            {versionsLoading ? (
              <LoadingRegion label="Loading roster versions">
                <div className="skeleton h-24 m-4" />
              </LoadingRegion>
            ) : versions.length === 0 ? (
              <EmptyState
                title="No roster versions yet"
                description="Generate a draft in the Draft tab. It becomes an immutable version once you publish it."
              />
            ) : (
              <>
                <Table
                  columns={[
                    { key: "version", header: "Version", accessor: (v) => <span className="whitespace-nowrap">#{v.id}</span> },
                    { key: "location", header: "Location", accessor: (v) => v.location_code || "\u2014" },
                    { key: "period", header: "Period", accessor: (v) => (
                      <span className="whitespace-nowrap">
                        {v.period_start} {"\u2192"} {v.period_end}
                      </span>
                    ) },
                    { key: "status", header: "Status", accessor: (v) => <StatusPill status={v.status} /> },
                    { key: "entries", header: "Entries", accessor: (v) => v.entry_count, cellClassName: "num" },
                    { key: "unfilled", header: "Unfilled", accessor: (v) => v.unfilled_count, cellClassName: "num" },
                    { key: "actions", header: "Actions", accessor: (v) => (
                      <div className="flex items-center gap-3 flex-wrap">
                        <Button variant="ghost" onClick={() => loadVersionDetail(v.id)}>
                          Detail
                        </Button>
                        {v.status === "published" && (
                          <Button variant="ghost" disabled={rolling === `v${v.id}`}
                            onClick={() => rollForward(v)}>
                            {rolling === `v${v.id}` ? "Copying\u2026" : "Roll forward"}
                          </Button>
                        )}
                        {v.status === "draft" && (
                          <Button variant="ghost" onClick={() => reviewDraft(v.id)}>
                            Review draft
                          </Button>
                        )}
                      </div>
                    ) },
                  ]}
                  data={versions}
                  keyAccessor={(v) => v.id}
                  caption="Roster versions, newest first"
                  sortable={false}
                />
                {(versionMeta.total_pages ?? 0) > 1 && (
                  <div className="px-4 py-2 border-t border-border flex items-center gap-3 flex-wrap">
                    <Button variant="secondary" size="sm" disabled={versionPage <= 1 || versionsLoading}
                      onClick={() => loadVersions(versionPage - 1)}>
                      Previous
                    </Button>
                    <span className="text-sm text-text-secondary">
                      Page {versionPage} of {versionMeta.total_pages ?? "?"}
                      {versionMeta.total ? ` · ${versionMeta.total} versions` : ""}
                    </span>
                    <Button variant="secondary" size="sm" disabled={
                        versionPage >= (versionMeta.total_pages ?? 1) || versionsLoading
                      }
                      onClick={() => loadVersions(versionPage + 1)}>
                      Next
                    </Button>
                  </div>
                )}
              </>
            )}

            {detailLoading && (
              <div className="px-4 py-4">
                <LoadingRegion label="Loading version detail"><div className="skeleton h-24 w-full" /></LoadingRegion>
              </div>
            )}

            {versionDetail && !detailLoading && (
              <div className="mt-4 border-t border-border pt-4">
                <h3 className="section-title px-4">Version #{versionDetail.id} — entries</h3>
                {versionDetail.entries.length === 0 ? (
                  <div className="mt-2">
                    <EmptyState
                      title="No entries stored"
                      description="This version holds no roster entries."
                    />
                  </div>
                ) : (
                  <Table
                    className="max-h-[320px] overflow-y-auto mt-2"
                    columns={[
                      { key: "employee", header: "Employee", accessor: (e) => employeeName(e.employee_id) },
                      { key: "date", header: "Date", accessor: (e) => <span className="whitespace-nowrap">{e.work_date}</span> },
                      { key: "shift", header: "Shift", accessor: (e) => (
                        <span className="whitespace-nowrap">
                          {e.start_time}{"\u2013"}{e.end_time}
                        </span>
                      ) },
                      { key: "night", header: "Night", accessor: (e) => (
                        e.is_night ? (
                          <span className="badge badge-violet">Night</span>
                        ) : (
                          <span className="badge badge-slate">Day</span>
                        )
                      ) },
                      { key: "status", header: "Status", accessor: (e) => <StatusPill status={e.status} /> },
                    ]}
                    data={versionDetail.entries.slice(0, 200)}
                    keyAccessor={(e) => e.id}
                    caption="Roster entries of the selected version"
                    sortable={false}
                  />
                )}

                {versionDetail.unfilled_slots && versionDetail.unfilled_slots.length > 0 && (
                  <div className="mt-2">
                    <h4 className="font-semibold px-4">
                      Unfilled slots of this version ({versionDetail.unfilled_slots.length})
                    </h4>
                    <Table
                      className="mt-1"
                      columns={[
                        { key: "date", header: "Date", accessor: (u) => <span className="whitespace-nowrap">{u.date}</span> },
                        { key: "slot", header: "Slot", accessor: (u) => <span className="font-mono text-xs">{u.slot_id}</span> },
                        { key: "headcount", header: "Headcount", accessor: (u) => u.headcount, cellClassName: "num" },
                        { key: "cause", header: "Cause", accessor: (u) => <span className="badge badge-amber">{u.cause}</span> },
                      ]}
                      data={versionDetail.unfilled_slots.map((u, i) => ({ ...u, _k: `${u.slot_id}-${i}` }))}
                      keyAccessor={(u) => u._k}
                      caption="Unfilled slots stored with the version"
                      sortable={false}
                    />
                  </div>
                )}

                <div className="px-4 mt-4 flex flex-wrap items-end gap-3 border-t border-border pt-3">
                  <div className="field">
                    <label htmlFor="rb-compare-base" className="field-label">Compare against</label>
                    <select
                      id="rb-compare-base"
                      className="input min-w-[240px]"
                      value={compareBase}
                      onChange={(e) => setCompareBase(e.target.value)}
                    >
                      <option value="">Choose a base version…</option>
                      {versions
                        .filter((v) => v.status !== "draft" && v.id !== versionDetail.id)
                        .map((v) => (
                          <option key={v.id} value={v.id}>
                            #{v.id} · {v.status} · {v.period_start}–{v.period_end}
                          </option>
                        ))}
                    </select>
                  </div>
                  <Button variant="secondary" disabled={!compareBase || compareLoading}
                    onClick={loadCompare}>
                    {compareLoading ? "Comparing…" : "Compare versions"}
                  </Button>
                </div>
              </div>
            )}

            {compareError && (
              <div className="px-4 pb-2">
                <Alert tone="error">{compareError}</Alert>
              </div>
            )}

            {compare && (
              <div className="mt-4 border-t border-border pt-3">
                <h3 className="section-title px-4">
                  Diff: version #{compare.version_id} against #{compare.base_version_id}
                </h3>
                <div className="px-4 py-2 flex flex-wrap gap-2">
                  {Object.entries(compare.summary).map(([k, v]) => (
                    <span key={k} className={`badge ${DIFF_TONE[k] ?? "badge-slate"}`}>
                      {k}: {v}
                    </span>
                  ))}
                </div>
                {compare.added.length + compare.removed.length + compare.changed.length === 0 ? (
                  <div className="mt-2">
                    <EmptyState
                      title="No differences"
                      description="The two rosters hold the same shifts."
                    />
                  </div>
                ) : (
                  <Table
                    className="max-h-[320px] overflow-y-auto"
                    columns={[
                      { key: "type", header: "Type", accessor: (d) => (
                        <span className={`badge ${DIFF_TONE[d.type] ?? "badge-slate"}`}>
                          {d.type}
                        </span>
                      ) },
                      { key: "employee", header: "Employee", accessor: (d) => employeeName(
                        d.type === "removed" ? d.base_entry?.employee_id : d.entry?.employee_id
                      ) },
                      { key: "date", header: "Date", accessor: (d) => (
                        <span className="whitespace-nowrap">
                          {d.type === "removed" ? d.base_entry?.work_date : d.entry?.work_date}
                        </span>
                      ) },
                      { key: "current", header: "Current", accessor: (d) => (
                        <span className="whitespace-nowrap">
                          {d.entry ? `${d.entry.start_time}\u2013${d.entry.end_time}` : "\u2014"}
                        </span>
                      ) },
                      { key: "base", header: "Base", accessor: (d) => (
                        <span className="whitespace-nowrap">
                          {d.base_entry ? `${d.base_entry.start_time}\u2013${d.base_entry.end_time}` : "\u2014"}
                        </span>
                      ) },
                    ]}
                    data={[...compare.added, ...compare.removed, ...compare.changed].map((d, i) => ({ ...d, _k: i }))}
                    keyAccessor={(d) => d._k}
                    caption="Added, removed and changed shifts between the two versions"
                    sortable={false}
                  />
                )}
              </div>
            )}
          </SectionCard>
        )}

        {activeTab === "attendance" && (
          <>
            <SectionCard compact
              icon={<IconClock />}
              title="Attendance against the roster"
              description="Pick a published version to see which scheduled shifts have a recorded working period."
            >
              {publishedVersions.length === 0 ? (
                <EmptyState
                  title="No published version yet"
                  description="Attendance is recorded against a published roster version. Publish a draft first."
                />
              ) : (
                <>
                  <div className="toolbar flex-wrap">
                    <div className="field min-w-[240px]">
                      <label htmlFor="rb-att-version" className="field-label">Published version</label>
                      <select
                        id="rb-att-version"
                        className="input"
                        value={attendanceVersion}
                        onChange={(e) => {
                          setAttendanceVersion(e.target.value)
                          setDeviations(null)
                          setAttendance(null)
                          if (e.target.value) void loadAttendance(e.target.value)
                        }}
                      >
                        <option value="">Choose a version…</option>
                        {publishedVersions.map((v) => (
                          <option key={v.id} value={v.id}>
                            #{v.id} · {v.period_start} → {v.period_end}
                          </option>
                        ))}
                      </select>
                    </div>
                    <Button variant="primary" disabled={!attendanceVersion || autoCreating}
                      onClick={autoCreate}>
                      <IconUsers className="w-4 h-4" />
                      {autoCreating ? "Creating…" : "Auto-create time entries"}
                    </Button>
                  </div>
                  <p className="px-4 py-2 text-xs text-text-secondary border-b border-border">
                    Auto-create writes clock in/out records for every scheduled shift that has none yet —
                    the kiosk bootstrap.
                  </p>

                  {attendanceLoading ? (
                    <LoadingRegion label="Loading attendance">
                      <div className="skeleton h-24 m-4" />
                    </LoadingRegion>
                  ) : attendance ? (
                    <>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4">
                        <SummaryBox
                          tone="brand"
                          label="Scheduled"
                          value={attendance.summary.total ?? attendance.entries.length}
                        />
                        <SummaryBox tone="green" label="Matched" value={attendance.summary.matched ?? 0} />
                        <SummaryBox tone="amber" label="Missing" value={attendance.summary.missing ?? 0} />
                        <SummaryBox tone="rose" label="Extra" value={attendance.summary.extra ?? 0} />
                      </div>
                      <Table
                        className="max-h-[420px] overflow-y-auto"
                        columns={[
                          { key: "employee", header: "Employee", accessor: (row) => employeeName(row.roster_entry.employee_id) },
                          { key: "date", header: "Date", accessor: (row) => <span className="whitespace-nowrap">{row.roster_entry.work_date}</span> },
                          { key: "scheduled", header: "Scheduled", accessor: (row) => (
                            <span className="whitespace-nowrap">
                              {row.roster_entry.start_time}{"\u2013"}{row.roster_entry.end_time}
                            </span>
                          ) },
                          { key: "in", header: "Clocked in", accessor: (row) => (
                            <span className="text-text-secondary whitespace-nowrap">
                              {shortTime(row.time_entry?.clock_in)}
                            </span>
                          ) },
                          { key: "out", header: "Clocked out", accessor: (row) => (
                            <span className="text-text-secondary whitespace-nowrap">
                              {shortTime(row.time_entry?.clock_out)}
                            </span>
                          ) },
                          { key: "hours", header: "Hours", accessor: (row) => row.time_entry?.worked_hours ?? "\u2014", cellClassName: "num" },
                        ]}
                        data={attendance.entries}
                        keyAccessor={(row) => `${row.roster_entry.id}-${row.time_entry?.id ?? "none"}`}
                        caption="Scheduled shifts with their recorded working periods"
                        sortable={false}
                      />
                    </>
                  ) : null}
                </>
              )}
            </SectionCard>

            {attendance && (
              <SectionCard compact
                icon={<IconAlert />}
                title="Deviations from the schedule"
                description="Early or late arrivals and departures, missing and extra shifts — measured against the published roster."
                actions={
                  <>
                    <div className="field">
                      <label htmlFor="rb-grace" className="field-label">Grace (min)</label>
                      <input
                        id="rb-grace"
                        type="number"
                        min={0}
                        className="input w-24"
                        value={grace}
                        onChange={(e) => setGrace(e.target.value)}
                      />
                    </div>
                    <Button variant="secondary" disabled={deviationsLoading}
                      onClick={loadDeviations}>
                      <IconRefresh className="w-4 h-4" />
                      {deviationsLoading ? "Checking…" : "Check deviations"}
                    </Button>
                  </>
                }
              >
                {deviationsError && (
                  <div className="px-4 pb-2">
                    <Alert tone="error">{deviationsError}</Alert>
                  </div>
                )}
                {deviationsLoading && (
                  <LoadingRegion label="Measuring deviations">
                    <div className="skeleton h-24 w-full" />
                  </LoadingRegion>
                )}
                {!deviationsLoading && !deviations && (
                  <EmptyState
                    title="Not checked yet"
                    description="Choose a grace period and run the check to compare actual working time against the schedule."
                  />
                )}
                {deviations && deviations.deviations.length === 0 ? (
                  <div className="px-4 pb-4">
                    {<Alert tone="success">No deviations recorded for this check.</Alert>}
                  </div>
                ) : deviations ? (
                  <>
                    <div className="px-4 py-2 flex flex-wrap gap-2">
                      {Object.entries(deviations.summary).map(([k, v]) => (
                        <span key={k} className={`badge ${SEVERITY_TONE[k] ?? "badge-slate"}`}>
                          {k}: {v}
                        </span>
                      ))}
                    </div>
                    <Table
                      className="max-h-[380px] overflow-y-auto"
                      columns={[
                        { key: "employee", header: "Employee", accessor: (d) => employeeName(d.roster_entry.employee_id) },
                        { key: "date", header: "Date", accessor: (d) => <span className="whitespace-nowrap">{d.roster_entry.work_date}</span> },
                        { key: "scheduled", header: "Scheduled", accessor: (d) => (
                          <span className="whitespace-nowrap">
                            {d.roster_entry.start_time}{"\u2013"}{d.roster_entry.end_time}
                          </span>
                        ) },
                        { key: "actual", header: "Actual", accessor: (d) => (
                          <span className="whitespace-nowrap">
                            {d.time_entry
                              ? `${shortTime(d.time_entry.clock_in)}\u2013${shortTime(d.time_entry.clock_out)}`
                              : "\u2014"}
                          </span>
                        ) },
                        { key: "violations", header: "Violations", accessor: (d) => (
                          <div className="flex flex-wrap gap-1.5">
                            {d.violations.map((v) => (
                              <span
                                key={v.id}
                                className={`badge ${SEVERITY_TONE[v.severity] ?? "badge-slate"}`}
                              >
                                {v.kind}
                                {v.minutes ? ` \u00b7 ${v.minutes}m` : ""}
                              </span>
                            ))}
                          </div>
                        ) },
                      ]}
                      data={deviations.deviations.map((d, i) => ({ ...d, _k: `${d.roster_entry.id}-${i}` }))}
                      keyAccessor={(d) => d._k}
                      caption="Working time deviations per roster entry"
                      sortable={false}
                    />
                  </>
                ) : null}
              </SectionCard>
            )}
          </>
        )}
      </div>
    </Layout>
  )
}

function SummaryBox({ tone, label, value }: { tone: Tone; label: string; value: number }) {
  return (
    <div className="card p-4 relative overflow-hidden">
      <span className={`stat-rail stat-rail-${tone}`} aria-hidden="true" />
      <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">{label}</p>
      <p className="stat-value">{value}</p>
    </div>
  )
}
