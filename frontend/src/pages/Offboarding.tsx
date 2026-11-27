import { useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {
  Button,
  Alert,
  EmptyState,
  LoadingRegion,
  Meter,
  PageHeader,
  SectionCard,
  KPICard,
  StatusPill,
} from "@/components/ui"
import { IconExit, IconCheck, IconX } from "@/components/icons"
import api from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import { useAuth } from "@/context/AuthContext"
import type { Employee, OffboardingTask, Termination } from "@/types"

type TerminationWithProgress = Termination & {
  progress?: { total: number; completed: number; progress_percent: number }
}

export default function Offboarding() {
  const { user } = useAuth()
  // Mirrors backend/app/api/v1/endpoints/offboarding.py: starting,
  // completing and cancelling a termination (`:105/:141/:164`), checklist
  // item updates (`:195`) and template creation (`:42`) are ADMIN_ROLES;
  // Managers and Associates can READ terminations and progress
  // (`:72/:93/:181→WORKFORCE_ROLES`) but see read-only cards. The template
  // list itself (`:33→ADMIN_ROLES`) 403s below admin.
  const isAdmin = user?.role === "SuperAdmin" || user?.role === "HR"
  const [tasks, setTasks] = useState<OffboardingTask[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [terminations, setTerminations] = useState<Termination[]>([])
  // Per-collection failure flags — the admin-only template list must not
  // blank the terminations table below it.
  type LoadKey = "tasks" | "employees" | "terminations"
  const LOAD_LABELS: Record<LoadKey, string> = {
    tasks: "checklist templates",
    employees: "employees",
    terminations: "terminations",
  }
  const [failed, setFailed] = useState<LoadKey[]>([])
  const [selected, setSelected] = useState<TerminationWithProgress | null>(null)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState("")

  const [form, setForm] = useState({
    employee_id: "",
    last_working_date: "",
    termination_type: "Resignation",
    reason: "",
  })
  const [taskForm, setTaskForm] = useState({ name: "", category: "General", description: "" })

  const openTermination = async (id: number) => {
    // The checklist and its progress meter settle separately: a failed
    // progress call must not blank the items the user asked for.
    const [t, p] = await Promise.allSettled([
      api.get(`/offboarding/terminations/${id}`),
      api.get(`/offboarding/terminations/${id}/progress`),
    ])
    if (t.status !== "fulfilled") {
      setError("Could not open the termination checklist — use an Open link above to retry.")
      setSelected(null)
      return
    }
    setSelected({
      ...t.value.data,
      progress: p.status === "fulfilled" ? p.value.data : undefined,
    })
  }

  const load = async () => {
    setLoading(true)
    const keys: LoadKey[] = ["tasks", "employees", "terminations"]
    const results = await Promise.allSettled([
      api.get("/offboarding/tasks"),
      fetchAllEmployees().then(({ items }) => ({ data: items })),
      api.get("/offboarding/terminations"),
    ])
    const failedKeys: LoadKey[] = []
    let firstTerminationId: number | null = null
    results.forEach((r, i) => {
      const key = keys[i]
      if (r.status === "fulfilled") {
        const data = r.value.data
        if (key === "tasks") setTasks(data)
        else if (key === "employees") setEmployees(data)
        else if (key === "terminations") {
          setTerminations(data)
          if (data.length) firstTerminationId = data[0].id
        }
      } else {
        failedKeys.push(key)
      }
    })
    setFailed(failedKeys)
    setError(
      failedKeys.length > 0
        ? `Some offboarding data could not be loaded: ${failedKeys
            .map((k) => LOAD_LABELS[k])
            .join(", ")}. Check your connection or use Reload to retry.`
        : "",
    )
    setLoading(false)
    if (firstTerminationId !== null && !selected) await openTermination(firstTerminationId)
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
      if (selected) await openTermination(selected.id)
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Action failed")
    } finally {
      setBusy("")
    }
  }

  const empName = (id: number) => {
    const e = employees.find((x) => x.id === id)
    return e ? `${e.first_name} ${e.last_name} (${e.employee_id})` : `#${id}`
  }

  const openTerms = terminations.filter((t) => t.status !== "Completed" && t.status !== "Cancelled").length

  /**
   * Empty state that separates "no rows yet" from "this collection failed to
   * load" — e.g. the template list 403s below SuperAdmin/HR.
   */
  const emptyDesc = (key: LoadKey, noneDesc: string) =>
    failed.includes(key)
      ? `The ${LOAD_LABELS[key]} list could not be loaded — it may be not visible for your role (${user?.role || "unknown"}). Use Reload to retry.`
      : noneDesc

  return (
    <Layout>
      <PageHeader compact
        icon={<IconExit />}
        title="Offboarding & Termination"
        description="Run the exit checklist and close out employment records."
      />

      {error && (
        <Alert
          tone="error"
          title="Offboarding data incomplete"
          action={
            <Button variant="secondary" size="sm" type="button" onClick={load}>
              Reload
            </Button>
          }
        >
          {error}
        </Alert>
      )}
      {notice && <Alert tone="success">{notice}</Alert>}

      {loading ? (
        <LoadingRegion label="Loading offboarding data">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="skeleton h-24" />
            ))}
          </div>
        </LoadingRegion>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
          <KPICard tone="brand" label="Total terminations" value={terminations.length} />
          <KPICard tone={openTerms > 0 ? "amber" : "green"} label="In progress" value={openTerms} />
          <KPICard tone="slate" label="Checklist templates" value={tasks.length} />
          <KPICard
            tone="violet"
            label="Selected progress"
            value={selected?.progress ? `${selected.progress.progress_percent}%` : "—"}
          />
        </div>
      )}

      {/* Start a termination — POST /offboarding/terminations is
          ADMIN_ROLES (offboarding.py:105) */}
      {isAdmin ? (
        <section className="card mb-5">
          <div className="toolbar">
          <div className="field min-w-[200px]">
            <label htmlFor="ob-emp" className="field-label">Employee (required)</label>
            <select id="ob-emp" className="input" value={form.employee_id}
              onChange={(e) => setForm({ ...form, employee_id: e.target.value })}>
              <option value="">Select employee…</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.first_name} {e.last_name} ({e.employee_id})
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="ob-date" className="field-label">Last working day (required)</label>
            <input id="ob-date" type="date" className="input" value={form.last_working_date}
              onChange={(e) => setForm({ ...form, last_working_date: e.target.value })} />
          </div>
          <div className="field min-w-[150px]">
            <label htmlFor="ob-type" className="field-label">Type (required)</label>
            <select id="ob-type" className="input" value={form.termination_type}
              onChange={(e) => setForm({ ...form, termination_type: e.target.value })}>
              {["Resignation", "Termination", "Layoff", "Retirement", "End of Contract"].map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </div>
          <div className="field grow min-w-[180px]">
            <label htmlFor="ob-reason" className="field-label">Reason (required)</label>
            <input id="ob-reason" className="input" value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })} />
          </div>
          <Button variant="primary" disabled={!form.employee_id || !form.last_working_date || busy === "init"}
            onClick={() => act("init", () => api.post("/offboarding/terminations", {
              employee_id: Number(form.employee_id),
              last_working_date: form.last_working_date,
              termination_type: form.termination_type,
              reason: form.reason || undefined,
            }), "Termination initiated with default checklist")}>
            {busy === "init" ? "Initiating…" : "Initiate termination"}
          </Button>
          </div>
        </section>
      ) : (
        <section className="card mb-5" aria-label="Initiate a termination">
          <p className="px-5 py-4 text-sm text-text-secondary" role="note">
            Starting, completing and cancelling terminations requires the
            SuperAdmin or HR role — your role ({user?.role || "unknown"}) sees
            the exit records and checklists read-only.
          </p>
        </section>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 mb-5">
        <SectionCard compact icon={<IconExit />} title="Terminations"
          description="Every exit record and its current state.">
          {terminations.length === 0 ? (
            <EmptyState title={failed.includes("terminations") ? "Terminations unavailable" : "No terminations"}
              description={emptyDesc("terminations", "Initiate a termination above to start the exit checklist.")} />
          ) : (
            <div className="table-scroll max-h-[380px] overflow-y-auto">
              <table className="table-base table-striped">
                <caption className="sr-only">All termination records</caption>
                <thead>
                  <tr>
                    <th scope="col">Employee</th>
                    <th scope="col">Last day</th>
                    <th scope="col">Type</th>
                    <th scope="col">Status</th>
                    <th scope="col"></th>
                  </tr>
                </thead>
                <tbody>
                  {terminations.map((t) => (
                    <tr key={t.id} className={selected?.id === t.id ? "bg-[rgba(239,246,255,0.6)]" : ""}>
                      <td>{empName(t.employee_id)}</td>
                      <td className="whitespace-nowrap">{t.last_working_date}</td>
                      <td>{t.termination_type}</td>
                      <td><StatusPill status={t.status} /></td>
                      <td className="text-right">
                        <Button variant="ghost" onClick={() => openTermination(t.id)}>
                          Open
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard compact
          icon={<IconCheck />}
          title={selected ? `Exit checklist #${selected.id}` : "Exit checklist"}
          description={selected ? `For ${empName(selected.employee_id)}` : "Select a termination to view its checklist."}
          actions={
            isAdmin && selected && selected.status !== "Completed" ? (
              /* complete/cancel are ADMIN_ROLES (offboarding.py:141/164) */
              <div className="flex items-center gap-2">
                <Button variant="primary" size="sm" disabled={busy === "done"}
                  onClick={() => act("done", () => api.post(`/offboarding/terminations/${selected.id}/complete`), "Termination completed")}>
                  {busy === "done" ? "Completing…" : "Complete"}
                </Button>
                <Button variant="secondary" size="sm" disabled={busy === "cancel"}
                  onClick={() => act("cancel", () => api.post(`/offboarding/terminations/${selected.id}/cancel`), "Termination cancelled")}>
                  Cancel
                </Button>
              </div>
            ) : undefined
          }
        >
          {selected?.progress && (
            <div className="px-5 py-4 border-b border-border">
              <Meter
                percent={selected.progress.progress_percent}
                label={`${selected.progress.completed} of ${selected.progress.total} exit tasks complete`}
              />
            </div>
          )}

          {!selected || selected.items.length === 0 ? (
            <EmptyState
              title="No checklist items"
              description="Exit tasks are generated from the template set when a termination is initiated."
            />
          ) : (
            <div className="table-scroll max-h-[320px] overflow-y-auto">
              <table className="table-base table-striped">
                <caption className="sr-only">Exit checklist items</caption>
                <thead>
                  <tr>
                    <th scope="col">Task</th>
                    <th scope="col">Category</th>
                    <th scope="col">Owner</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.items.map((i) => {
                    const done = i.status === "Completed"
                    return (
                      <tr key={i.id}>
                        <td>{i.name}</td>
                        <td className="text-text-secondary">{i.category}</td>
                        <td className="text-text-secondary">{i.assigned_to || "—"}</td>
                        <td>
                          {/* PUT /offboarding/items/{id} is ADMIN_ROLES
                              (offboarding.py:195) — other roles read a
                              status badge instead of a button that 403s. */}
                          {isAdmin ? (
                            <button
                              className={done ? "badge badge-green cursor-default" : "action-link"}
                              disabled={done || busy === `i${i.id}`}
                              onClick={() =>
                                act(`i${i.id}`, () => api.put(`/offboarding/items/${i.id}`, {
                                  status: done ? "Pending" : "Completed",
                                }), "Checklist updated")
                              }
                            >
                              {done ? (
                                <>Completed</>
                              ) : busy === `i${i.id}` ? (
                                "Saving…"
                              ) : (
                                "Mark complete"
                              )}
                            </button>
                          ) : (
                            <span className={`badge ${done ? "badge-green" : "badge-slate"}`}>
                              {i.status}
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>

      {/* Checklist templates — GET /offboarding/tasks is ADMIN_ROLES
          (offboarding.py:33) and creating one is (:42); below admin the
          card explains itself instead of silently listing nothing. */}
      <section className="card">
        {isAdmin ? (
          <div className="toolbar">
            <div className="field grow min-w-[180px]">
              <label htmlFor="obt-name" className="field-label">Template name (required)</label>
              <input id="obt-name" className="input" value={taskForm.name}
                onChange={(e) => setTaskForm({ ...taskForm, name: e.target.value })} />
            </div>
            <div className="field w-40">
              <label htmlFor="obt-cat" className="field-label">Category (required)</label>
              <select id="obt-cat" className="input" value={taskForm.category}
                onChange={(e) => setTaskForm({ ...taskForm, category: e.target.value })}>
                {["IT", "HR", "Finance", "Facilities", "General"].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </div>
            <Button variant="primary" disabled={!taskForm.name || busy === "tt"}
              onClick={() => act("tt", () => api.post("/offboarding/tasks", taskForm), "Checklist template created")}>
              {busy === "tt" ? "Adding…" : "Add template"}
            </Button>
          </div>
        ) : (
          <p className="px-5 pt-4 pb-2 text-sm text-text-secondary" role="note">
            Checklist templates are defined by SuperAdmin or HR. New exits reuse
            the admin-defined template set automatically.
          </p>
        )}

        {tasks.length === 0 ? (
          <EmptyState title={failed.includes("tasks") ? "Templates unavailable" : "No checklist templates"}
            description={emptyDesc("tasks", "Templates defined here are applied to every new termination.")} />
        ) : (
          <div className="table-scroll">
            <table className="table-base table-striped">
              <caption className="sr-only">Offboarding checklist templates</caption>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Category</th>
                  <th scope="col">Required</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.id}>
                    <td>{t.name}</td>
                    <td className="text-text-secondary">{t.category}</td>
                    <td>
                      <span className={`badge ${t.is_required ? "badge-amber" : "badge-slate"}`}>
                        {t.is_required ? "Required" : "Optional"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </Layout>
  )
}