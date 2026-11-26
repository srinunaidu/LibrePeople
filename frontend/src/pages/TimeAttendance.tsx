import { useEffect, useState } from "react"
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
  TableSkeleton, RetryableAlert} from "@/components/ui"
import { IconCalendar, IconCheck, IconClock, IconFile } from "@/components/icons"
import api from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import { useAuth } from "@/context/AuthContext"
import type { Employee, PeriodLockStatus, TimeCorrection, TimeEntry, Timesheet } from "@/types"

const fmt = (v?: string | null) => {
  if (!v) return "—"
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v.replace("T", " ").slice(0, 16)
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(d)
}

const fmtDate = (v?: string | null) => {
  if (!v) return "—"
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(d)
}

export default function TimeAttendance() {
  const { user } = useAuth()
  // Mirrors backend/app/api/v1/endpoints/time_attendance.py: clock in/out
  // (`:69/:92→WORKFORCE_ROLES`), entries and timesheet reads
  // (`:37/:165→WORKFORCE_ROLES`). Timesheet GENERATION
  // (`:192→ADMIN_ROLES`) belongs to SuperAdmin/HR only. A PayrollViewer is
  // outside WORKFORCE_ROLES and gets a workload-visible explanation instead
  // of 403 buttons.
  const isAdmin = user?.role === "SuperAdmin" || user?.role === "HR"
  const isWorkforce =
    isAdmin ||
    user?.role === "Manager" ||
    user?.role === "Associate"
  // Timesheet approval is MANAGER_ROLES (time_attendance.py:231); an
  // Associate may submit but must not be offered approve.
  const isManager = isAdmin || user?.role === "Manager"
  const [employees, setEmployees] = useState<Employee[]>([])
  const [selected, setSelected] = useState<number | "">("")
  const [entries, setEntries] = useState<TimeEntry[]>([])
  const [timesheets, setTimesheets] = useState<Timesheet[]>([])
  const [corrections, setCorrections] = useState<TimeCorrection[]>([])
  const [lockStatus, setLockStatus] = useState<PeriodLockStatus | null>(null)
  const [corrDate, setCorrDate] = useState("")
  const [corrIn, setCorrIn] = useState("")
  const [corrOut, setCorrOut] = useState("")
  const [corrReason, setCorrReason] = useState("")
  const [corrEntry, setCorrEntry] = useState("")
  const [start, setStart] = useState("")
  const [end, setEnd] = useState("")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState("")

  useEffect(() => {
    fetchAllEmployees()
      .then(({ items }) => {
        setEmployees(items)
        if (items.length) setSelected(items[0].id)
      })
      .catch(() =>
        setError(
          "The employee list could not be loaded — it may be temporarily unavailable or restricted for your role.",
        ),
      )
      .finally(() => setLoading(false))
  }, [])

  const load = async (id: number) => {
    // Entries, timesheets, corrections and the lock status settle
    // independently: a failure in one card's source must not erase the
    // other cards' numbers.
    const [e, t, c] = await Promise.allSettled([
      api.get(`/time/entries?employee_id=${id}`),
      api.get(`/time/timesheets?employee_id=${id}`),
      api.get(`/time/corrections?employee_id=${id}`),
    ])
    if (e.status === "fulfilled") setEntries(e.value.data)
    else setError("Time entries could not be loaded for the selected employee.")
    if (t.status === "fulfilled") setTimesheets(t.value.data)
    else setError("Timesheets could not be loaded for the selected employee.")
    if (c.status === "fulfilled") setCorrections(c.value.data)
    else setError("Correction requests could not be loaded for the selected employee.")
    if (start && end) {
      try {
        const s = await api.get(
          `/time/period-locks/status?period_start=${start}&period_end=${end}`,
        )
        setLockStatus(s.data)
      } catch {
        setLockStatus(null)
      }
    }
  }

  useEffect(() => {
    if (selected !== "") load(Number(selected))
  }, [selected])

  const act = async (key: string, fn: () => Promise<unknown>, msg: string) => {
    setError("")
    setNotice("")
    setBusy(key)
    try {
      await fn()
      setNotice(msg)
      if (selected !== "") await load(Number(selected))
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Action failed")
    } finally {
      setBusy("")
    }
  }

  const selectedEmployee = employees.find((e) => e.id === selected)
  const totalHours = entries.reduce((s, t) => s + (t.worked_hours ?? 0), 0)
  const totalOvertime = entries.reduce((s, t) => s + (t.overtime_hours ?? 0), 0)

  return (
    <Layout>
      <PageHeader
        compact
        icon={<IconClock />}
        title="Time & Attendance"
        description="Clock in and out, review daily entries, and prepare timesheets for payroll."
      />

      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      {/* Employee + clock controls */}
      <section className="card mb-5">
        {!isWorkforce ? (
          <p className="px-5 py-4 text-sm text-text-secondary" role="note">
            Clock entries and timesheets are workforce records — they are not
            visible for your role ({user?.role || "unknown"}). Payroll roles read
            processed payslips and aggregate leave data instead.
          </p>
        ) : (
          <div className="toolbar">
            <div className="field min-w-[220px]">
              <label htmlFor="ta-employee" className="field-label">
                Employee (required)
              </label>
              <select
                id="ta-employee"
                className="input"
                value={selected}
                onChange={(e) => setSelected(Number(e.target.value))}
              >
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.first_name} {e.last_name} ({e.employee_id})
                  </option>
                ))}
              </select>
              {!loading && employees.length === 0 && (
                <p className="mt-1 text-xs text-warning-text" role="note">
                  No employees are visible to your account yet — ask an HR or SuperAdmin user.
                </p>
              )}
            </div>

            <div className="flex items-end gap-2">
              <Button variant="primary" disabled={selected === "" || busy === "in"}
                onClick={() => act("in", () => api.post("/time/clock-in", { employee_id: selected }), "Clocked in")}>
                <IconClock className="w-4 h-4" />
                {busy === "in" ? "Clocking in…" : "Clock in"}
              </Button>
              <Button variant="secondary" disabled={selected === "" || busy === "out"}
                onClick={() => act("out", () => api.post("/time/clock-out", { employee_id: selected }), "Clocked out")}>
                <IconCheck className="w-4 h-4" />
                {busy === "out" ? "Clocking out…" : "Clock out"}
              </Button>
            </div>

            <div className="flex items-end gap-2 ml-auto flex-wrap">
              <div className="field">
                <label htmlFor="ta-start" className="field-label">Period start (required)</label>
                <input id="ta-start" type="date" className="input" value={start} onChange={(e) => setStart(e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="ta-end" className="field-label">Period end (required)</label>
                <input id="ta-end" type="date" className="input" value={end} onChange={(e) => setEnd(e.target.value)} />
              </div>
              {isAdmin ? (
                /* POST /time/timesheets/generate is ADMIN_ROLES
                   (time_attendance.py:192) */
                <Button variant="primary" disabled={!start || !end || selected === "" || busy === "gen"}
                  onClick={() =>
                    act(
                      "gen",
                      () =>
                        api.post("/time/timesheets/generate", {
                          employee_id: selected,
                          period_start: start,
                          period_end: end,
                        }),
                      "Timesheet generated"
                    )
                  }>
                  <IconFile className="w-4 h-4" />
                  {busy === "gen" ? "Generating…" : "Generate timesheet"}
                </Button>
              ) : (
                <p className="text-xs text-text-secondary max-w-[220px]" role="note">
                  Payroll-period timesheets are generated by HR or SuperAdmin; timesheet submission appears below once one exists.
                </p>
              )}
            </div>
          </div>
        )}
      </section>

      {/* Summary strip */}
      {selectedEmployee && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
          {[
            { label: "Employee", value: `${selectedEmployee.first_name} ${selectedEmployee.last_name}`, tone: "brand" },
            { label: "Entries recorded", value: entries.length, tone: "teal" },
            { label: "Total hours", value: `${totalHours}h`, tone: "green" },
            { label: "Overtime", value: `${totalOvertime}h`, tone: totalOvertime > 0 ? "amber" : "slate" },
          ].map((s) => (
            <div key={s.label} className="card p-4 relative overflow-hidden">
              <span className={`stat-rail stat-rail-${s.tone}`} aria-hidden="true" />
              <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                {s.label}
              </p>
              <p className="stat-value text-[var(--font-size-2xl)]">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <SectionCard
          compact
          icon={<IconClock />}
          title="Time entries"
          description="Daily clock events recorded for this employee."
        >
          {loading ? (
            <TableSkeleton rows={5} cols={5} />
          ) : entries.length === 0 ? (
            <EmptyState
              title="No time entries yet"
              description="Clock this employee in to start recording daily hours."
            />
          ) : (
            <Table
              columns={[
                { key: "date", header: "Date", accessor: (t) => <span className="whitespace-nowrap">{fmtDate(t.work_date)}</span> },
                { key: "in", header: "Clock in", accessor: (t) => <span className="text-text-secondary whitespace-nowrap">{fmt(t.clock_in)}</span> },
                { key: "out", header: "Clock out", accessor: (t) => <span className="text-text-secondary whitespace-nowrap">{fmt(t.clock_out)}</span> },
                { key: "hours", header: "Hours", accessor: (t) => t.worked_hours, cellClassName: "num font-medium" },
                { key: "ot", header: "OT", accessor: (t) => t.overtime_hours || "—", cellClassName: "num" },
                { key: "status", header: "Status", accessor: (t) => <StatusPill status={t.status} /> },
              ]}
              data={entries}
              keyAccessor={(t) => t.id}
              caption="Time entries for the selected employee"
              sortable={false}
            />
          )}
        </SectionCard>

        <SectionCard
          compact
          icon={<IconCalendar />}
          title="Timesheets"
          description="Payroll-period totals awaiting submission or approval."
        >
          {loading ? (
            <TableSkeleton rows={4} cols={4} />
          ) : timesheets.length === 0 ? (
            <EmptyState
              title="No timesheets"
              description="Generate a timesheet using the period dates above."
            />
          ) : (
            <Table
              columns={[
                { key: "period", header: "Period", accessor: (t) => (
                  <span className="whitespace-nowrap">
                    {fmtDate(t.period_start)} → {fmtDate(t.period_end)}
                  </span>
                ) },
                { key: "hours", header: "Hours", accessor: (t) => t.total_hours, cellClassName: "num font-medium" },
                { key: "ot", header: "OT", accessor: (t) => t.overtime_hours || "—", cellClassName: "num" },
                { key: "status", header: "Status", accessor: (t) => <StatusPill status={t.status} /> },
                { key: "actions", header: "Actions", accessor: (t) => (
                  <div className="flex items-center gap-3">
                    {t.status === "Draft" && (
                      <Button variant="ghost" disabled={busy === `s${t.id}`}
                        onClick={() => act(`s${t.id}`, () => api.post(`/time/timesheets/${t.id}/submit`), "Submitted")}>
                        Submit
                      </Button>
                    )}
                    {t.status === "Submitted" &&
                      (isManager ? (
                        /* POST /time/timesheets/{id}/approve is
                           MANAGER_ROLES (time_attendance.py:223) */
                        <Button variant="ghost" disabled={busy === `a${t.id}`}
                          onClick={() => act(`a${t.id}`, () => api.post(`/time/timesheets/${t.id}/approve`), "Approved")}>
                          Approve
                        </Button>
                      ) : (
                        <span className="text-xs text-text-secondary">Awaiting manager approval</span>
                      ))}
                    {t.status !== "Draft" && t.status !== "Submitted" && (
                      <span className="text-xs text-text-secondary">Complete</span>
                    )}
                  </div>
                ) },
              ]}
              data={timesheets}
              keyAccessor={(t) => t.id}
              caption="Timesheets for the selected employee"
              sortable={false}
            />
          )}
        </SectionCard>
      </div>

      {/* Correction requests + period lock */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-4">
        <SectionCard
          compact
          icon={<IconFile />}
          title="Correction requests"
          description="Ask for a clock record to be fixed. A manager approves or rejects it; the approval applies the times."
        >
          {isWorkforce && (
            <form
              className="flex flex-wrap items-end gap-2 mb-4"
              onSubmit={(ev) => {
                ev.preventDefault()
                if (!corrDate || selected === "") return
                void act("corr", () =>
                  api.post("/time/corrections", {
                    employee_id: selected,
                    time_entry_id: corrEntry ? Number(corrEntry) : undefined,
                    work_date: corrDate,
                    requested_clock_in: corrIn || undefined,
                    requested_clock_out: corrOut || undefined,
                    reason: corrReason || undefined,
                  }).then(() => {
                    setCorrDate("")
                    setCorrIn("")
                    setCorrOut("")
                    setCorrReason("")
                    setCorrEntry("")
                  }),
                  "Correction requested",
                )
              }}
            >
              <div className="field">
                <label htmlFor="ta-corr-date" className="field-label">Work date (required)</label>
                <input id="ta-corr-date" type="date" className="input" value={corrDate} onChange={(e) => setCorrDate(e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="ta-corr-in" className="field-label">Clock in</label>
                <input id="ta-corr-in" type="datetime-local" className="input" value={corrIn} onChange={(e) => setCorrIn(e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="ta-corr-out" className="field-label">Clock out</label>
                <input id="ta-corr-out" type="datetime-local" className="input" value={corrOut} onChange={(e) => setCorrOut(e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="ta-corr-entry" className="field-label">Entry (optional)</label>
                <select id="ta-corr-entry" className="input" value={corrEntry} onChange={(e) => setCorrEntry(e.target.value)}>
                  <option value="">No linked entry</option>
                  {entries.map((t) => (
                    <option key={t.id} value={t.id}>
                      #{t.id} — {fmtDate(t.work_date)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field min-w-[200px]">
                <label htmlFor="ta-corr-reason" className="field-label">Reason</label>
                <input id="ta-corr-reason" className="input" value={corrReason} onChange={(e) => setCorrReason(e.target.value)} placeholder="Missed clock-out" />
              </div>
              <Button variant="secondary" disabled={!corrDate || selected === "" || busy === "corr"}>
                {busy === "corr" ? "Requesting…" : "Request correction"}
              </Button>
            </form>
          )}
          {corrections.length === 0 ? (
            <EmptyState
              title="No correction requests"
              description="Request a fix above when a clock record is wrong."
            />
          ) : (
            <Table
              columns={[
                { key: "date", header: "Date", accessor: (c) => <span className="whitespace-nowrap">{fmtDate(c.work_date)}</span> },
                { key: "requested", header: "Requested", accessor: (c) => (
                  <span className="text-text-secondary whitespace-nowrap">
                    {fmt(c.requested_clock_in)} → {fmt(c.requested_clock_out)}
                  </span>
                ) },
                { key: "status", header: "Status", accessor: (c) => <StatusPill status={c.status} /> },
                { key: "decision", header: "Decision", accessor: (c) => (
                  <span className="text-text-secondary whitespace-nowrap">
                    {c.decided_at ? fmt(c.decided_at) : "—"}
                  </span>
                ) },
                { key: "actions", header: "Actions", accessor: (c) => (
                  c.status === "Pending" && isManager ? (
                    <div className="flex items-center gap-3">
                      <Button variant="ghost" disabled={busy === `ca${c.id}`}
                        onClick={() => act(`ca${c.id}`, () => api.post(`/time/corrections/${c.id}/approve`), "Correction approved")}>
                        Approve
                      </Button>
                      <Button variant="ghost" disabled={busy === `cr${c.id}`}
                        onClick={() => act(`cr${c.id}`, () => api.post(`/time/corrections/${c.id}/reject`), "Correction rejected")}>
                        Reject
                      </Button>
                    </div>
                  ) : c.status === "Pending" ? (
                    <span className="text-xs text-text-secondary">Awaiting manager decision</span>
                  ) : (
                    <span className="text-xs text-text-secondary">Decided</span>
                  )
                ) },
              ]}
              data={corrections}
              keyAccessor={(c) => c.id}
              caption="Time correction requests for the selected employee"
              sortable={false}
            />
          )}
        </SectionCard>

        <SectionCard
          compact
          icon={<IconCalendar />}
          title="Attendance period lock"
          description="Locked periods refuse every time write inside them — clock in/out, manual edits, timesheets and corrections."
        >
          {lockStatus ? (
            <p className="mb-3 text-sm" role="status">
              Period {fmtDate(lockStatus.period_start)} → {fmtDate(lockStatus.period_end)}:{" "}
              <StatusPill status={lockStatus.is_locked ? "Locked" : "Open"} />
            </p>
          ) : (
            <p className="mb-3 text-sm text-text-secondary" role="note">
              Enter the period dates above and check whether the period is locked.
            </p>
          )}
          <div className="flex flex-wrap items-end gap-2">
            {isAdmin ? (
              <>
                {/* POST /time/period-locks/lock and /reopen are ADMIN_ROLES */}
                <Button variant="primary" disabled={!start || !end || busy === "lock"}
                  onClick={() =>
                    act("lock", () => api.post("/time/period-locks/lock", { period_start: start, period_end: end }), "Period locked")
                  }>
                  {busy === "lock" ? "Locking…" : "Lock period"}
                </Button>
                <Button variant="secondary" disabled={!start || !end || busy === "reopen"}
                  onClick={() =>
                    act("reopen", () => api.post("/time/period-locks/reopen", { period_start: start, period_end: end }), "Period reopened")
                  }>
                  {busy === "reopen" ? "Reopening…" : "Reopen period"}
                </Button>
              </>
            ) : (
              <p className="text-xs text-text-secondary max-w-[260px]" role="note">
                Periods are locked and reopened by HR or SuperAdmin; the status above tells you whether writes will be refused.
              </p>
            )}
            <Button variant="secondary" disabled={!start || !end || busy === "status"}
              onClick={() =>
                act("status", () =>
                  api
                    .get(`/time/period-locks/status?period_start=${start}&period_end=${end}`)
                    .then((r) => setLockStatus(r.data)),
                  "Status refreshed",
                )
              }>
              {busy === "status" ? "Checking…" : "Check status"}
            </Button>
          </div>
        </SectionCard>
      </div>
    </Layout>
  )
}