import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Layout } from "@/components/Layout"
import { Button, Input, Select, Checkbox,Alert, EmptyState, PageHeader, SectionCard, StatusPill, Table, TableSkeleton, LoadingRegion, RetryableAlert} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { errorMessage } from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import { formatCurrency } from "@/lib/format"
import type {
  Employee,
  BenefitPlanRow,
  BenefitEnrollmentRow,
  LifeEventRow,
  LeaveOfAbsenceRow,
} from "@/types"

const ADMIN_ROLES = ["SuperAdmin", "HR"]
const WORKFORCE_ROLES = ["SuperAdmin", "HR", "Manager", "Associate"]

function fmtDate(v?: string | null) { if (!v) return "—"; return v.slice(0, 10) }
function money(
  v: number | string | null | undefined,
  opts?: { locale?: string | null; currency?: string | null },
) {
  return formatCurrency(v, {
    locale: opts?.locale,
    currency: opts?.currency || undefined,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export default function BenefitsHub() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const tenantLocale = tenant?.locale
  const tenantCurrency = tenant?.currency || undefined
  const role = user?.role ?? ""
  const canAdmin = ADMIN_ROLES.includes(role)
  const canWorkforce = WORKFORCE_ROLES.includes(role)

  const [plans, setPlans] = useState<BenefitPlanRow[]>([])
  const [enrollments, setEnrollments] = useState<BenefitEnrollmentRow[]>([])
  const [lifeEvents, setLifeEvents] = useState<LifeEventRow[]>([])
  const [leaves, setLeaves] = useState<LeaveOfAbsenceRow[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState("")

  const [planForm, setPlanForm] = useState({ name: "", code: "", plan_type: "", provider: "", employer_contribution: "", employee_contribution: "", is_active: true })
  const [enrollForm, setEnrollForm] = useState({ employee_id: "", plan_id: "", effective_date: "", end_date: "", status: "Active" })
  const [lifeEventForm, setLifeEventForm] = useState({ employee_id: "", event_type: "", event_date: "", description: "", status: "Pending" })
  const [leaveForm, setLeaveForm] = useState({ employee_id: "", leave_type: "", start_date: "", end_date: "", status: "Pending", notes: "" })
  const [busy, setBusy] = useState<"" | "plan" | "enroll" | "life" | "leave" | string>("")
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})

  const load = useCallback(async () => {
    setLoading(true)
    setErrors({})
    const [planRes, enrollRes, lifeRes, leaveRes, empRes] = await Promise.allSettled([
      api.get<BenefitPlanRow[]>("/benefits/benefit-plans"),
      canWorkforce ? api.get<BenefitEnrollmentRow[]>("/benefits/benefit-enrollments") : Promise.resolve(null as any),
      canWorkforce ? api.get<LifeEventRow[]>("/benefits/life-events") : Promise.resolve(null as any),
      canWorkforce ? api.get<LeaveOfAbsenceRow[]>("/benefits/leaves-of-absence") : Promise.resolve(null as any),
      fetchAllEmployees(),
    ])
    const next: Record<string, string> = {}
    if (planRes.status === "fulfilled") {
      setPlans(planRes.value.data ?? [])
    } else {
      setPlans([])
      next.plans = errorMessage(planRes.reason, "The benefit plans could not be read.")
    }
    if (enrollRes.status === "fulfilled") {
      setEnrollments((enrollRes.value as any)?.data ?? [])
    } else {
      setEnrollments([])
      next.enrollments = errorMessage((enrollRes as PromiseRejectedResult).reason, "The benefit enrollments could not be read.")
    }
    if (lifeRes.status === "fulfilled") {
      setLifeEvents((lifeRes.value as any)?.data ?? [])
    } else {
      setLifeEvents([])
      next.lifeEvents = errorMessage((lifeRes as PromiseRejectedResult).reason, "The life events could not be read.")
    }
    if (leaveRes.status === "fulfilled") {
      setLeaves((leaveRes.value as any)?.data ?? [])
    } else {
      setLeaves([])
      next.leaves = errorMessage((leaveRes as PromiseRejectedResult).reason, "The leaves of absence could not be read.")
    }
    if (empRes.status === "fulfilled") {
      setEmployees(empRes.value.items)
    } else setEmployees([])
    setErrors(next)
    setLoading(false)
  }, [canWorkforce])

  useEffect(() => { void load() }, [load])

  const employeeName = (id: number) => {
    const f = employees.find((r) => r.id === id)
    return f ? `${f.first_name} ${f.last_name}` : `Employee #${id}`
  }
  const planName = (id: number) => {
    const f = plans.find((r) => r.id === id)
    return f ? f.name : `Plan #${id}`
  }

  async function submitPlan(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, plan: "" }))
    setNotice("")
    if (!planForm.name.trim() || !planForm.code.trim() || !planForm.plan_type.trim()) {
      setFormErrors((c) => ({ ...c, plan: "Name, code and plan type are required." }))
      return
    }
    setBusy("plan")
    try {
      await api.post("/benefits/benefit-plans", {
        name: planForm.name.trim(),
        code: planForm.code.trim(),
        plan_type: planForm.plan_type.trim(),
        provider: planForm.provider.trim() || null,
        employer_contribution: Number(planForm.employer_contribution || 0),
        employee_contribution: Number(planForm.employee_contribution || 0),
        is_active: planForm.is_active,
      })
      setPlanForm({ name: "", code: "", plan_type: "", provider: "", employer_contribution: "", employee_contribution: "", is_active: true })
      setNotice("Benefit plan created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, plan: errorMessage(err, "The benefit plan could not be created.") }))
    } finally { setBusy("") }
  }

  async function submitEnrollment(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, enroll: "" }))
    setNotice("")
    if (!enrollForm.employee_id || !enrollForm.plan_id || !enrollForm.effective_date) {
      setFormErrors((c) => ({ ...c, enroll: "Employee, plan and effective date are required." }))
      return
    }
    setBusy("enroll")
    try {
      await api.post("/benefits/benefit-enrollments", {
        employee_id: Number(enrollForm.employee_id),
        plan_id: Number(enrollForm.plan_id),
        effective_date: enrollForm.effective_date,
        end_date: enrollForm.end_date || null,
        status: enrollForm.status.trim() || "Active",
      })
      setEnrollForm({ employee_id: "", plan_id: "", effective_date: "", end_date: "", status: "Active" })
      setNotice("Benefit enrollment created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, enroll: errorMessage(err, "The benefit enrollment could not be created.") }))
    } finally { setBusy("") }
  }

  async function submitLifeEvent(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, life: "" }))
    setNotice("")
    if (!lifeEventForm.employee_id || !lifeEventForm.event_type.trim() || !lifeEventForm.event_date) {
      setFormErrors((c) => ({ ...c, life: "Employee, event type and event date are required." }))
      return
    }
    setBusy("life")
    try {
      await api.post("/benefits/life-events", {
        employee_id: Number(lifeEventForm.employee_id),
        event_type: lifeEventForm.event_type.trim(),
        event_date: lifeEventForm.event_date,
        description: lifeEventForm.description.trim() || null,
        status: lifeEventForm.status.trim() || "Pending",
      })
      setLifeEventForm({ employee_id: "", event_type: "", event_date: "", description: "", status: "Pending" })
      setNotice("Life event created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, life: errorMessage(err, "The life event could not be created.") }))
    } finally { setBusy("") }
  }

  async function submitLeave(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, leave: "" }))
    setNotice("")
    if (!leaveForm.employee_id || !leaveForm.leave_type.trim() || !leaveForm.start_date) {
      setFormErrors((c) => ({ ...c, leave: "Employee, leave type and start date are required." }))
      return
    }
    setBusy("leave")
    try {
      await api.post("/benefits/leaves-of-absence", {
        employee_id: Number(leaveForm.employee_id),
        leave_type: leaveForm.leave_type.trim(),
        start_date: leaveForm.start_date,
        end_date: leaveForm.end_date || null,
        status: leaveForm.status.trim() || "Pending",
        notes: leaveForm.notes.trim() || null,
      })
      setLeaveForm({ employee_id: "", leave_type: "", start_date: "", end_date: "", status: "Pending", notes: "" })
      setNotice("Leave of absence created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, leave: errorMessage(err, "The leave of absence could not be created.") }))
    } finally { setBusy("") }
  }

  async function approveLeave(id: number) {
    if (busy) return
    setBusy(`approve-${id}`)
    setNotice("")
    setFormErrors((c) => ({ ...c, leave: "" }))
    try {
      await api.put(`/benefits/leaves-of-absence/${id}/approve`)
      setNotice("Leave of absence approved.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, leave: errorMessage(err, "The leave could not be approved.") }))
    } finally { setBusy("") }
  }

  return (
    <Layout>
      <PageHeader compact title="Benefits" description="Plans, enrollments, life events and leaves of absence" />
      {notice && <Alert tone="success">{notice}</Alert>}

      {/* Benefit plans */}
      <SectionCard compact title="Benefit plans" description="The plans on offer. Creating a plan is limited to SuperAdmin and HR.">
        {loading ? (
          <LoadingRegion label="Loading benefit plans…"><TableSkeleton rows={3} cols={7} /></LoadingRegion>
        ) : errors.plans ? (
          <div className="p-5"><RetryableAlert err={errors.plans} title="The benefit plans could not be read" fallback="The benefit plans could not be read" onRetry={load} /></div>
        ) : (
          <>
            {canAdmin && (
              <form onSubmit={submitPlan} className="p-5 border-b border-border">
                {formErrors.plan && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.plan}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="min-w-[120px]">
                    <label htmlFor="bplan-code" className="block text-xs font-medium text-text-secondary mb-1">Code</label>
                    <Input id="bplan-code" value={planForm.code} onChange={(e) => setPlanForm((f) => ({ ...f, code: e.target.value }))} placeholder="e.g. MED-01" required />
                  </div>
                  <div className="flex-1 min-w-[180px]">
                    <label htmlFor="bplan-name" className="block text-xs font-medium text-text-secondary mb-1">Name</label>
                    <Input id="bplan-name" value={planForm.name} onChange={(e) => setPlanForm((f) => ({ ...f, name: e.target.value }))} placeholder="Plan name" required />
                  </div>
                  <div className="min-w-[140px]">
                    <label htmlFor="bplan-type" className="block text-xs font-medium text-text-secondary mb-1">Plan type</label>
                    <Input id="bplan-type" value={planForm.plan_type} onChange={(e) => setPlanForm((f) => ({ ...f, plan_type: e.target.value }))} placeholder="e.g. Health" required />
                  </div>
                  <div className="min-w-[160px]">
                    <label htmlFor="bplan-provider" className="block text-xs font-medium text-text-secondary mb-1">Provider</label>
                    <Input id="bplan-provider" value={planForm.provider} onChange={(e) => setPlanForm((f) => ({ ...f, provider: e.target.value }))} placeholder="Optional" />
                  </div>
                  <div className="min-w-[140px]">
                    <label htmlFor="bplan-employer" className="block text-xs font-medium text-text-secondary mb-1">Employer contrib.</label>
                    <Input id="bplan-employer" type="number" min="0" step="0.01" value={planForm.employer_contribution} onChange={(e) => setPlanForm((f) => ({ ...f, employer_contribution: e.target.value }))} />
                  </div>
                  <div className="min-w-[140px]">
                    <label htmlFor="bplan-employee" className="block text-xs font-medium text-text-secondary mb-1">Employee contrib.</label>
                    <Input id="bplan-employee" type="number" min="0" step="0.01" value={planForm.employee_contribution} onChange={(e) => setPlanForm((f) => ({ ...f, employee_contribution: e.target.value }))} />
                  </div>
                  <Checkbox id="bplan-active" label="Active" checked={planForm.is_active} onChange={(e) => setPlanForm((f) => ({ ...f, is_active: e.target.checked }))} />
                  <Button type="submit" loading={busy === "plan"}>Create plan</Button>
                </div>
              </form>
            )}
            {plans.length === 0 ? (
              <div className="p-5"><EmptyState title="No benefit plans" description="No benefit plans exist yet." /></div>
            ) : (
              <Table
                columns={[
                  { key: "code", header: "Code", accessor: (p) => <span className="font-mono text-xs">{p.code}</span> },
                  { key: "name", header: "Name", accessor: (p) => p.name },
                  { key: "type", header: "Plan type", accessor: (p) => p.plan_type },
                  { key: "provider", header: "Provider", accessor: (p) => p.provider ?? "\u2014" },
                  { key: "employer", header: "Employer", accessor: (p) => money(p.employer_contribution, { locale: tenantLocale, currency: tenantCurrency }), cellClassName: "num tabular-nums" },
                  { key: "employee", header: "Employee", accessor: (p) => money(p.employee_contribution, { locale: tenantLocale, currency: tenantCurrency }), cellClassName: "num tabular-nums" },
                  { key: "active", header: "Active", accessor: (p) => p.is_active ? <span className="badge badge-green">Active</span> : <span className="badge badge-slate">Inactive</span> },
                ]}
                data={plans}
                keyAccessor={(p) => p.id}
                caption="Benefit plans"
                sortable={false}
              />
            )}
          </>
        )}
      </SectionCard>

      {/* Enrollments */}
      <SectionCard compact title="Enrollments" description="Who is enrolled in which plan. Reading is available to the workforce; creating is limited to SuperAdmin and HR.">
        {loading ? (
          <LoadingRegion label="Loading benefit enrollments…"><TableSkeleton rows={3} cols={5} /></LoadingRegion>
        ) : errors.enrollments ? (
          <div className="p-5"><RetryableAlert err={errors.enrollments} title="The benefit enrollments could not be read" fallback="The benefit enrollments could not be read" onRetry={load} /></div>
        ) : (
          <>
            {!canWorkforce && <div className="p-5"><Alert tone="info">Benefit enrollments are visible to SuperAdmin, HR, Manager and Associate.</Alert></div>}
            {canAdmin && canWorkforce && (
              <form onSubmit={submitEnrollment} className="p-5 border-b border-border">
                {formErrors.enroll && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.enroll}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="benroll-employee" className="block text-xs font-medium text-text-secondary mb-1">Employee</label>
                    <Select id="benroll-employee" value={enrollForm.employee_id} onChange={(e) => setEnrollForm((f) => ({ ...f, employee_id: e.target.value }))} required>
                      <option value="">Select an employee…</option>
                      {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} · {emp.employee_id}</option>)}
                    </Select>
                  </div>
                  <div className="flex-1 min-w-[200px]">
                    <label htmlFor="benroll-plan" className="block text-xs font-medium text-text-secondary mb-1">Plan</label>
                    <Select id="benroll-plan" value={enrollForm.plan_id} onChange={(e) => setEnrollForm((f) => ({ ...f, plan_id: e.target.value }))} required>
                      <option value="">Select a plan…</option>
                      {plans.map((pl) => <option key={pl.id} value={pl.id}>{pl.code} — {pl.name}</option>)}
                    </Select>
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="benroll-effective" className="block text-xs font-medium text-text-secondary mb-1">Effective date</label>
                    <Input id="benroll-effective" type="date" value={enrollForm.effective_date} onChange={(e) => setEnrollForm((f) => ({ ...f, effective_date: e.target.value }))} required />
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="benroll-end" className="block text-xs font-medium text-text-secondary mb-1">End date</label>
                    <Input id="benroll-end" type="date" value={enrollForm.end_date} onChange={(e) => setEnrollForm((f) => ({ ...f, end_date: e.target.value }))} />
                  </div>
                  <div className="min-w-[120px]">
                    <label htmlFor="benroll-status" className="block text-xs font-medium text-text-secondary mb-1">Status</label>
                    <Input id="benroll-status" value={enrollForm.status} onChange={(e) => setEnrollForm((f) => ({ ...f, status: e.target.value }))} placeholder="Active" />
                  </div>
                  <Button type="submit" loading={busy === "enroll"}>Enroll</Button>
                </div>
              </form>
            )}
            {canWorkforce && enrollments.length === 0 ? (
              <div className="p-5"><EmptyState title="No enrollments" description="No benefit enrollments recorded yet." /></div>
            ) : canWorkforce && enrollments.length > 0 ? (
              <Table
                columns={[
                  { key: "employee", header: "Employee", accessor: (en) => employeeName(en.employee_id) },
                  { key: "plan", header: "Plan", accessor: (en) => planName(en.plan_id) },
                  { key: "effective", header: "Effective", accessor: (en) => fmtDate(en.effective_date) },
                  { key: "end", header: "End", accessor: (en) => fmtDate(en.end_date) },
                  { key: "status", header: "Status", accessor: (en) => <StatusPill status={en.status} /> },
                ]}
                data={enrollments}
                keyAccessor={(en) => en.id}
                caption="Benefit enrollments"
                sortable={false}
              />
            ) : null}
          </>
        )}
      </SectionCard>

      {/* Life events */}
      <SectionCard compact title="Life events" description="Qualifying events that may change benefits. Creating and reading is available to the workforce.">
        {loading ? (
          <LoadingRegion label="Loading life events…"><TableSkeleton rows={3} cols={4} /></LoadingRegion>
        ) : errors.lifeEvents ? (
          <div className="p-5"><RetryableAlert err={errors.lifeEvents} title="The life events could not be read" fallback="The life events could not be read" onRetry={load} /></div>
        ) : (
          <>
            {!canWorkforce && <div className="p-5"><Alert tone="info">Life events are visible to SuperAdmin, HR, Manager and Associate.</Alert></div>}
            {canWorkforce && (
              <form onSubmit={submitLifeEvent} className="p-5 border-b border-border">
                {formErrors.life && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.life}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="life-employee" className="block text-xs font-medium text-text-secondary mb-1">Employee</label>
                    <Select id="life-employee" value={lifeEventForm.employee_id} onChange={(e) => setLifeEventForm((f) => ({ ...f, employee_id: e.target.value }))} required>
                      <option value="">Select an employee…</option>
                      {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} · {emp.employee_id}</option>)}
                    </Select>
                  </div>
                  <div className="min-w-[160px]">
                    <label htmlFor="life-type" className="block text-xs font-medium text-text-secondary mb-1">Event type</label>
                    <Input id="life-type" value={lifeEventForm.event_type} onChange={(e) => setLifeEventForm((f) => ({ ...f, event_type: e.target.value }))} placeholder="e.g. Marriage" required />
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="life-date" className="block text-xs font-medium text-text-secondary mb-1">Event date</label>
                    <Input id="life-date" type="date" value={lifeEventForm.event_date} onChange={(e) => setLifeEventForm((f) => ({ ...f, event_date: e.target.value }))} required />
                  </div>
                  <div className="min-w-[140px]">
                    <label htmlFor="life-status" className="block text-xs font-medium text-text-secondary mb-1">Status</label>
                    <Input id="life-status" value={lifeEventForm.status} onChange={(e) => setLifeEventForm((f) => ({ ...f, status: e.target.value }))} placeholder="Pending" />
                  </div>
                  <div className="flex-1 min-w-[200px]">
                    <label htmlFor="life-desc" className="block text-xs font-medium text-text-secondary mb-1">Description</label>
                    <Input id="life-desc" value={lifeEventForm.description} onChange={(e) => setLifeEventForm((f) => ({ ...f, description: e.target.value }))} placeholder="Optional" />
                  </div>
                  <Button type="submit" loading={busy === "life"}>Add event</Button>
                </div>
              </form>
            )}
            {canWorkforce && lifeEvents.length === 0 ? (
              <div className="p-5"><EmptyState title="No life events" description="No life events recorded yet." /></div>
            ) : canWorkforce && lifeEvents.length > 0 ? (
              <Table
                columns={[
                  { key: "employee", header: "Employee", accessor: (ev) => employeeName(ev.employee_id) },
                  { key: "type", header: "Event type", accessor: (ev) => ev.event_type },
                  { key: "date", header: "Event date", accessor: (ev) => fmtDate(ev.event_date) },
                  { key: "status", header: "Status", accessor: (ev) => <StatusPill status={ev.status} /> },
                ]}
                data={lifeEvents}
                keyAccessor={(ev) => ev.id}
                caption="Life events"
                sortable={false}
              />
            ) : null}
          </>
        )}
      </SectionCard>

      {/* Leaves of absence */}
      <SectionCard compact title="Leaves of absence" description="Extended leaves. Creating and reading is available to the workforce; approving is limited to SuperAdmin and HR.">
        {loading ? (
          <LoadingRegion label="Loading leaves of absence…"><TableSkeleton rows={3} cols={5} /></LoadingRegion>
        ) : errors.leaves ? (
          <div className="p-5"><RetryableAlert err={errors.leaves} title="The leaves of absence could not be read" fallback="The leaves of absence could not be read" onRetry={load} /></div>
        ) : (
          <>
            {!canWorkforce && <div className="p-5"><Alert tone="info">Leaves of absence are visible to SuperAdmin, HR, Manager and Associate.</Alert></div>}
            {canWorkforce && (
              <form onSubmit={submitLeave} className="p-5 border-b border-border">
                {formErrors.leave && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.leave}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="loa-employee" className="block text-xs font-medium text-text-secondary mb-1">Employee</label>
                    <Select id="loa-employee" value={leaveForm.employee_id} onChange={(e) => setLeaveForm((f) => ({ ...f, employee_id: e.target.value }))} required>
                      <option value="">Select an employee…</option>
                      {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} · {emp.employee_id}</option>)}
                    </Select>
                  </div>
                  <div className="min-w-[160px]">
                    <label htmlFor="loa-type" className="block text-xs font-medium text-text-secondary mb-1">Leave type</label>
                    <Input id="loa-type" value={leaveForm.leave_type} onChange={(e) => setLeaveForm((f) => ({ ...f, leave_type: e.target.value }))} placeholder="e.g. Parental" required />
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="loa-start" className="block text-xs font-medium text-text-secondary mb-1">Start date</label>
                    <Input id="loa-start" type="date" value={leaveForm.start_date} onChange={(e) => setLeaveForm((f) => ({ ...f, start_date: e.target.value }))} required />
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="loa-end" className="block text-xs font-medium text-text-secondary mb-1">End date</label>
                    <Input id="loa-end" type="date" value={leaveForm.end_date} onChange={(e) => setLeaveForm((f) => ({ ...f, end_date: e.target.value }))} />
                  </div>
                  <div className="min-w-[120px]">
                    <label htmlFor="loa-status" className="block text-xs font-medium text-text-secondary mb-1">Status</label>
                    <Input id="loa-status" value={leaveForm.status} onChange={(e) => setLeaveForm((f) => ({ ...f, status: e.target.value }))} placeholder="Pending" />
                  </div>
                  <div className="flex-1 min-w-[200px]">
                    <label htmlFor="loa-notes" className="block text-xs font-medium text-text-secondary mb-1">Notes</label>
                    <Input id="loa-notes" value={leaveForm.notes} onChange={(e) => setLeaveForm((f) => ({ ...f, notes: e.target.value }))} placeholder="Optional" />
                  </div>
                  <Button type="submit" loading={busy === "leave"}>Add leave</Button>
                </div>
              </form>
            )}
            {canWorkforce && leaves.length === 0 ? (
              <div className="p-5"><EmptyState title="No leaves of absence" description="No leaves of absence recorded yet." /></div>
            ) : canWorkforce && leaves.length > 0 ? (
              <Table
                columns={[
                  { key: "employee", header: "Employee", accessor: (lv) => employeeName(lv.employee_id) },
                  { key: "type", header: "Leave type", accessor: (lv) => lv.leave_type },
                  { key: "start", header: "Start", accessor: (lv) => fmtDate(lv.start_date) },
                  { key: "end", header: "End", accessor: (lv) => fmtDate(lv.end_date) },
                  { key: "status", header: "Status", accessor: (lv) => <StatusPill status={lv.status} /> },
                  ...(canAdmin ? [{
                    key: "actions", header: "Actions", accessor: (lv: (typeof leaves)[number]) => (
                      <Button size="xs" variant="secondary" loading={busy === `approve-${lv.id}`} disabled={lv.status !== "Pending"} onClick={() => approveLeave(lv.id)}>Approve</Button>
                    ),
                  }] : []),
                ]}
                data={leaves}
                keyAccessor={(lv) => lv.id}
                caption="Leaves of absence"
                sortable={false}
              />
            ) : null}
          </>
        )}
      </SectionCard>
    </Layout>
  )
}
