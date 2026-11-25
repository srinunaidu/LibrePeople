import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Layout } from "@/components/Layout"
import {
  Alert,
  EmptyState,
  LoadingRegion,
  Meter,
  PageHeader,
  SectionCard,
  StatCard,
  StatusPill,
  ShiftTemplateTable,
  ShiftSwapTable, RetryableAlert} from "@/components/ui"
import { IconCalendar, IconClock, IconPlus, IconUsers } from "@/components/icons"
import { AccordionItem } from "@/components/ui/accordion"
import api from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import { useAuth } from "@/context/AuthContext"
import type { Employee, RosterEntry, ShiftSwap, ShiftTemplate } from "@/types"

export default function Scheduling() {
  const { user } = useAuth()
  // Mirrors backend/app/api/v1/endpoints/scheduling.py: template create
  // (`:84→ADMIN_ROLES`) and the legacy single-shift roster generate
  // (`:161→ADMIN_ROLES`) are admin-only; swap approve/reject
  // (`:554/:572→MANAGER_ROLES`) is manager-and-above. Every other endpoint
  // on this screen is read-scoped by role rather than forbidden.
  const isAdmin = user?.role === "SuperAdmin" || user?.role === "HR"
  const isManager = isAdmin || user?.role === "Manager"
  const [templates, setTemplates] = useState<ShiftTemplate[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [roster, setRoster] = useState<RosterEntry[]>([])
  const [swaps, setSwaps] = useState<ShiftSwap[]>([])
  // Which of the four source lists failed to load — a shift-template 403
  // must not blank the roster table, and each card tells its own story.
  const [failed, setFailed] = useState<string[]>([])
  type LoadKey = "templates" | "employees" | "roster" | "swaps"
  const LOAD_LABELS: Record<LoadKey, string> = {
    templates: "shift templates",
    employees: "employees",
    roster: "roster entries",
    swaps: "shift swaps",
  }
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState("")

  const [form, setForm] = useState({
    employee_id: "",
    start_date: "",
    end_date: "",
    shift_template_id: "",
  })
  const [tpl, setTpl] = useState({
    name: "",
    code: "",
    start_time: "09:00",
    end_time: "17:00",
    break_minutes: 60,
    is_night: false,
  })

  const load = async () => {
    setLoading(true)
    const keys: LoadKey[] = ["templates", "employees", "roster", "swaps"]
    const results = await Promise.allSettled([
      api.get("/scheduling/shift-templates"),
      fetchAllEmployees().then(({ items }) => ({ data: items })),
      api.get("/scheduling/roster"),
      api.get("/scheduling/swaps"),
    ])
    const failedKeys: LoadKey[] = []
    results.forEach((r, i) => {
      const key = keys[i]
      if (r.status === "fulfilled") {
        const data = r.value.data
        if (key === "templates") setTemplates(data)
        else if (key === "employees") setEmployees(data)
        else if (key === "roster") setRoster(data)
        else if (key === "swaps") setSwaps(data)
      } else {
        failedKeys.push(key)
      }
    })
    setFailed(failedKeys)
    setError(
      failedKeys.length > 0
        ? `Some scheduling data could not be loaded: ${failedKeys
            .map((k) => LOAD_LABELS[k])
            .join(", ")}. Check your connection or use Reload to retry.`
        : "",
    )
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  const act = async (key: string, fn: () => Promise<unknown>, msg: string) => {
    setError("")
    setNotice("")
    setBusy(key)
    try {
      await fn()
      setNotice(msg)
      await load()
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Action failed")
    } finally {
      setBusy("")
    }
  }

  const empName = (id: number) => {
    const e = employees.find((x) => x.id === id)
    return e ? `${e.first_name} ${e.last_name}` : `#${id}`
  }

  const handleEditTemplate = (id: number) => {
    const t = templates.find((x) => x.id === id)
    if (!t) return
    act(`e${id}`, () => api.put(`/scheduling/shift-templates/${id}`, t), "Shift template updated")
  }

  const handleDeleteTemplate = (id: number) => {
    if (!window.confirm("Delete this shift template?")) return
    act(`d${id}`, () => api.delete(`/scheduling/shift-templates/${id}`), "Shift template deleted")
  }

  /**
   * Empty state that separates "no rows yet" from "this collection failed to
   * load" so a role-scoped 403 never reads as an empty module.
   */
  const emptyDesc = (key: LoadKey, noneDesc: string) =>
    failed.includes(key)
      ? `The ${LOAD_LABELS[key]} list could not be loaded — it may be temporarily unavailable or not visible for your role. Use Reload to retry.`
      : noneDesc

  const nightShifts = templates.filter((t) => t.is_night).length
  const pendingSwaps = swaps.filter((s) => s.status === "Pending").length
  const scheduledPeople = new Set(roster.map((r) => r.employee_id)).size

  return (
    <Layout>
      <PageHeader compact
        icon={<IconCalendar />}
        title="Scheduling & Rostering"
        description="Define shift templates, build rosters, and handle shift swap requests."
        actions={
          <Link to="/scheduling/roster" className="btn btn-primary">
            Open Roster Builder
          </Link>
        }
      />

      {error && (
        <Alert
          tone="error"
          title="Scheduling data incomplete"
          action={
            <button type="button" className="btn btn-secondary btn-sm" onClick={load}>
              Reload
            </button>
          }
        >
          {error}
        </Alert>
      )}
      {notice && <Alert tone="success">{notice}</Alert>}

      {loading ? (
        <LoadingRegion label="Loading scheduling data">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="skeleton h-24" />
            ))}
          </div>
        </LoadingRegion>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
          <StatCard tone="brand" label="Shift templates" value={templates.length} />
          <StatCard tone="violet" label="Night shifts" value={nightShifts} />
          <StatCard tone="teal" label="Scheduled people" value={scheduledPeople} hint={`${roster.length} roster entries`} />
          <StatCard tone={pendingSwaps > 0 ? "amber" : "slate"} label="Pending swaps" value={pendingSwaps} />
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 mb-5">
        {/* Shift templates */}
        <section className="card">
          {isAdmin ? (
            <div className="toolbar">
              <div className="field grow min-w-[140px]">
                <label htmlFor="st-name" className="field-label">Name (required)</label>
                <input id="st-name" className="input" value={tpl.name}
                  onChange={(e) => setTpl({ ...tpl, name: e.target.value })} />
              </div>
              <div className="field w-24">
                <label htmlFor="st-code" className="field-label">Code (required)</label>
                <input id="st-code" className="input" value={tpl.code}
                  onChange={(e) => setTpl({ ...tpl, code: e.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="st-start" className="field-label">Start (required)</label>
                <input id="st-start" type="time" className="input" value={tpl.start_time}
                  onChange={(e) => setTpl({ ...tpl, start_time: e.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="st-end" className="field-label">End (required)</label>
                <input id="st-end" type="time" className="input" value={tpl.end_time}
                  onChange={(e) => setTpl({ ...tpl, end_time: e.target.value })} />
              </div>
              <button className="btn btn-primary" disabled={!tpl.name || !tpl.code || busy === "tpl"}
                onClick={() => act("tpl", () => api.post("/scheduling/shift-templates", tpl), "Shift template created")}>
                <IconPlus className="w-4 h-4" />
                {busy === "tpl" ? "Adding…" : "Add template"}
              </button>
            </div>
          ) : (
            <p className="px-5 pt-4 pb-2 text-sm text-text-secondary" role="note">
              Adding shift templates requires the SuperAdmin or HR role — ask an administrator to define
              templates you need.
            </p>
          )}

          {templates.length === 0 ? (
            <EmptyState title={failed.includes("templates") ? "Templates unavailable" : "No shift templates"}
              description={emptyDesc("templates", "Define a template above, then use it to generate rosters.")} />
          ) : (
            <div className="table-scroll">
              <ShiftTemplateTable
                templates={templates}
                onEdit={handleEditTemplate}
                onDelete={handleDeleteTemplate}
              />
            </div>
          )}
        </section>

        {/* Roster generation — the legacy single-shift generator */}
        <section className="card">
          <h2 className="px-5 pt-4 font-semibold">Roster generation (legacy single-shift)</h2>
          <p className="px-5 pt-1 pb-2 text-xs text-text-secondary">
            Expands one shift for one employee. Whole-team rosters are generated with the
            constraint solver in the{" "}
            <Link to="/scheduling/roster" className="text-primary underline underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600">
              Roster Builder
            </Link>{" "}
            — prefer that screen for real schedules.
          </p>
          {isAdmin ? (
            <div className="toolbar">
              <div className="field min-w-[160px]">
                <label htmlFor="rg-emp" className="field-label">Employee (required)</label>
                <select id="rg-emp" className="input" value={form.employee_id}
                  onChange={(e) => setForm({ ...form, employee_id: e.target.value })}>
                  <option value="">Select employee…</option>
                  {employees.map((e) => (
                    <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>
                  ))}
                </select>
              </div>
              <div className="field min-w-[160px]">
                <label htmlFor="rg-shift" className="field-label">Shift (required)</label>
                <select id="rg-shift" className="input" value={form.shift_template_id}
                  onChange={(e) => setForm({ ...form, shift_template_id: e.target.value })}>
                  <option value="">Select shift…</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>{t.code} — {t.name}</option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="rg-from" className="field-label">From (required)</label>
                <input id="rg-from" type="date" className="input" value={form.start_date}
                  onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="rg-to" className="field-label">To (required)</label>
                <input id="rg-to" type="date" className="input" value={form.end_date}
                  onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
              </div>
              <button className="btn btn-primary"
                disabled={!form.employee_id || !form.shift_template_id || !form.start_date || !form.end_date || busy === "rg"}
                onClick={() => act("rg", () => api.post("/scheduling/roster/generate", {
                  employee_id: Number(form.employee_id),
                  shift_template_id: Number(form.shift_template_id),
                  start_date: form.start_date,
                  end_date: form.end_date,
                }), "Roster generated")}>
                {busy === "rg" ? "Generating…" : "Generate roster"}
              </button>
            </div>
          ) : (
            <p className="px-5 pb-4 text-sm text-text-secondary" role="note">
              This legacy generator requires the SuperAdmin or HR role. Managers build drafts
              with the solver in the{" "}
              <Link to="/scheduling/roster" className="text-primary underline underline-offset-2 hover:underline">Roster Builder</Link>.
            </p>
          )}
          {isAdmin && (
            <div className="px-5 py-4 text-sm text-text-secondary border-t border-border">
              Roster generation expands the selected shift across the date range for the chosen employee.
            </div>
          )}
        </section>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <SectionCard compact icon={<IconUsers />} title="Roster"
          description="Generated shift assignments across the organisation.">
          {roster.length === 0 ? (
            <EmptyState title={failed.includes("roster") ? "Roster unavailable" : "No roster entries"}
              description={emptyDesc("roster", "Generate a roster above to schedule an employee.")} />
          ) : (
            <div
              className="table-scroll max-h-[420px] overflow-y-auto"
              tabIndex={0}
              role="region"
              aria-label="Roster entries"
            >
              <table className="table-base table-striped table-compact">
                <caption className="sr-only">Roster entries</caption>
                <thead>
                  <tr>
                    <th scope="col">Employee</th>
                    <th scope="col">Date</th>
                    <th scope="col">Shift</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {roster.slice(0, 50).map((r) => (
                    <tr key={r.id}>
                      <td>{empName(r.employee_id)}</td>
                      <td className="whitespace-nowrap">{r.work_date}</td>
                      <td className="whitespace-nowrap">{r.start_time}–{r.end_time}</td>
                      <td><StatusPill status={r.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {roster.length > 50 && (
            <p className="px-5 py-2.5 text-xs text-text-secondary border-t border-border">
              Showing the first 50 of {roster.length} roster entries.
            </p>
          )}
        </SectionCard>

        <SectionCard compact icon={<IconClock />} title="Shift swaps"
          description="Requests to hand a shift to a colleague.">
          {swaps.length === 0 ? (
            <EmptyState title={failed.includes("swaps") ? "Swap requests unavailable" : "No swap requests"}
              description={emptyDesc("swaps", "Swap requests raised by employees will appear here.")} />
          ) : (
            <div
              className="table-scroll max-h-[420px] overflow-y-auto"
              tabIndex={0}
              role="region"
              aria-label="Shift swap requests"
            >
              <ShiftSwapTable
                swaps={swaps.map((s) => ({
                  id: s.id,
                  entry: s.roster_entry_id,
                  requester: empName(s.requester_id),
                  target: s.target_id ? empName(s.target_id) : "—",
                  proposed_date: s.proposed_date,
                  status: s.status,
                }))}
                canManage={isManager}
                onApprove={(id) => act(`a${id}`, () => api.post(`/scheduling/swaps/${id}/approve`), "Swap approved")}
                onReject={(id) => act(`r${id}`, () => api.post(`/scheduling/swaps/${id}/reject`), "Swap rejected")}
              />
            </div>
          )}
        </SectionCard>
      </div>
      <div className="mt-4">
        <AccordionItem title="Advanced Options">
          <p className="text-sm text-fg-muted">Configure solver constraints, soft preferences and roster templates in detail. Templates can also be managed via the Roster Builder solver.</p>
        </AccordionItem>
      </div>
    </Layout>
  )
}