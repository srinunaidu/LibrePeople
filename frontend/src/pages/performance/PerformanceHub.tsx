/**
 * Performance hub — goals, reviews, feedback and compensation (B1).
 *
 * This is the operational surface for the six served performance collections.
 * The bare Platform tab stays read-only; this page owns the verbs.
 *
 * Role gates mirror `backend/app/api/deps.py` and `backend/app/api/v1/endpoints/performance.py`:
 *  ADMIN_ROLES     = SuperAdmin, HR
 *  MANAGER_ROLES   = SuperAdmin, HR, Manager
 *  WORKFORCE_ROLES = SuperAdmin, HR, Manager, Associate
 *  - goals, reviews, feedback  GET/POST : WORKFORCE (create/update goals+reviews is MANAGER)
 *  - compensation-bands, merit-cycles, merit-allocations : ADMIN
 *  - finalize review : MANAGER
 * A viewer is told why a section is not theirs rather than shown a form that
 * would answer 403.
 *
 * Reads are independent (`Promise.allSettled`) — one failed GET must not blank
 * the others. Each section distinguishes "could not be read" from "no rows".
 */
import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Layout } from "@/components/Layout"
import {Alert,
  Button,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  TableSkeleton, RetryableAlert} from "@/components/ui"
import { Field } from "@/components/ui/layout"
import { Meter } from "@/components/ui/feedback"
import { Input, Select, Textarea } from "@/components/ui/inputs"
import { StatusPill } from "@/components/ui/status-pill"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { errorMessage } from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import { formatCurrency, formatDate as formatDateLib, formatDateTime as formatDateTimeLib } from "@/lib/format"
import type {
  BandRow,
  Employee,
  FeedbackRow,
  GoalRow,
  Job,
  MeritAllocationRow,
  MeritCycleRow,
  ReviewRow,
} from "@/types"

const WORKFORCE_ROLES = ["SuperAdmin", "HR", "Manager", "Associate"] as const
const MANAGER_ROLES = ["SuperAdmin", "HR", "Manager"] as const
const ADMIN_ROLES = ["SuperAdmin", "HR"] as const

function money(
  value: number | string | null | undefined,
  opts?: { locale?: string | null; currency?: string | null },
): string {
  return formatCurrency(value, {
    locale: opts?.locale,
    currency: opts?.currency || undefined,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function fmtDate(value?: string | null, opts?: { locale?: string | null; timeZone?: string | null }): string {
  return formatDateLib(value, opts)
}

function fmtDateTime(value?: string | null, opts?: { locale?: string | null; timeZone?: string | null }): string {
  return formatDateTimeLib(value, opts)
}

export default function PerformanceHub() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const tenantLocale = tenant?.locale
  const tenantCurrency = tenant?.currency || undefined
  const tenantDateOpts = { locale: tenant?.locale, timeZone: tenant?.timezone }
  const role = user?.role ?? ""
  const canWorkforce = (WORKFORCE_ROLES as readonly string[]).includes(role)
  const canManager = (MANAGER_ROLES as readonly string[]).includes(role)
  const canAdmin = (ADMIN_ROLES as readonly string[]).includes(role)

  const [goals, setGoals] = useState<GoalRow[]>([])
  const [reviews, setReviews] = useState<ReviewRow[]>([])
  const [feedback, setFeedback] = useState<FeedbackRow[]>([])
  const [bands, setBands] = useState<BandRow[]>([])
  const [cycles, setCycles] = useState<MeritCycleRow[]>([])
  const [allocations, setAllocations] = useState<MeritAllocationRow[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [jobs, setJobs] = useState<Job[]>([])

  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState("")

  // per-section form errors
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState<string>("")
  // inline finalize busy per review
  const [finalizing, setFinalizing] = useState<number | null>(null)
  // inline goal update
  const [goalEdits, setGoalEdits] = useState<Record<number, { progress: string; status: string }>>({})

  const [goalForm, setGoalForm] = useState({
    employee_id: "",
    title: "",
    description: "",
    weight: "",
    progress: "",
    status: "Not Started",
    due_date: "",
  })
  const [reviewForm, setReviewForm] = useState({
    employee_id: "",
    reviewer_id: "",
    period: "",
    status: "Draft",
    overall_rating: "",
    manager_comments: "",
    employee_comments: "",
  })
  const [feedbackForm, setFeedbackForm] = useState({
    review_id: "",
    from_employee_id: "",
    feedback_type: "Peer",
    rating: "",
    comments: "",
  })
  const [bandForm, setBandForm] = useState({
    job_id: "",
    level: "",
    min_salary: "",
    mid_salary: "",
    max_salary: "",
    currency: "INR",
  })
  const [cycleForm, setCycleForm] = useState({
    name: "",
    year: "",
    budget_percent: "",
    start_date: "",
    end_date: "",
    status: "Draft",
  })
  const [allocationForm, setAllocationForm] = useState({
    cycle_id: "",
    employee_id: "",
    current_salary: "",
    proposed_salary: "",
    increase_percent: "",
    status: "Draft",
  })

  const employeeName = (id: number) => {
    const e = employees.find((r) => r.id === id)
    return e ? `${e.first_name} ${e.last_name}` : `Employee #${id}`
  }
  const jobName = (id: number) => {
    const j = jobs.find((r) => r.id === id)
    return j ? `${j.title} (${j.code})` : `Job #${id}`
  }

  const load = useCallback(async () => {
    setLoading(true)
    setErrors({})
    const next: Record<string, string> = {}

    const goalsP = canWorkforce
      ? api.get<GoalRow[]>("/performance/goals")
      : Promise.resolve({ data: [] as GoalRow[] })
    const reviewsP = canWorkforce
      ? api.get<ReviewRow[]>("/performance/reviews")
      : Promise.resolve({ data: [] as ReviewRow[] })
    const feedbackP = canWorkforce
      ? api.get<FeedbackRow[]>("/performance/feedback")
      : Promise.resolve({ data: [] as FeedbackRow[] })
    const bandsP = canAdmin
      ? api.get<BandRow[]>("/performance/compensation-bands")
      : Promise.resolve({ data: [] as BandRow[] })
    const cyclesP = canAdmin
      ? api.get<MeritCycleRow[]>("/performance/merit-cycles")
      : Promise.resolve({ data: [] as MeritCycleRow[] })
    const allocationsP = canAdmin
      ? api.get<MeritAllocationRow[]>("/performance/merit-allocations")
      : Promise.resolve({ data: [] as MeritAllocationRow[] })

    const [goalsR, reviewsR, feedbackR, bandsR, cyclesR, allocationsR, employeesR, jobsR] =
      await Promise.allSettled([
        goalsP,
        reviewsP,
        feedbackP,
        bandsP,
        cyclesP,
        allocationsP,
        fetchAllEmployees(),
        canAdmin
          ? api.get<Job[]>("/jobs/", { params: { include_inactive: true } })
          : Promise.resolve({ data: [] as Job[] } as unknown as { data: Job[] }),
      ])

    if (goalsR.status === "fulfilled") {
      const v = goalsR.value as { data: GoalRow[] }
      setGoals(v.data ?? [])
    } else if (canWorkforce) {
      setGoals([])
      next.goals = errorMessage(goalsR.reason, "The goals could not be read.")
    }

    if (reviewsR.status === "fulfilled") {
      const v = reviewsR.value as { data: ReviewRow[] }
      setReviews(v.data ?? [])
    } else if (canWorkforce) {
      setReviews([])
      next.reviews = errorMessage(reviewsR.reason, "The reviews could not be read.")
    }

    if (feedbackR.status === "fulfilled") {
      const v = feedbackR.value as { data: FeedbackRow[] }
      setFeedback(v.data ?? [])
    } else if (canWorkforce) {
      setFeedback([])
      next.feedback = errorMessage(feedbackR.reason, "The feedback could not be read.")
    }

    if (bandsR.status === "fulfilled") {
      const v = bandsR.value as { data: BandRow[] }
      setBands(v.data ?? [])
    } else if (canAdmin) {
      setBands([])
      next.bands = errorMessage(bandsR.reason, "The compensation bands could not be read.")
    }

    if (cyclesR.status === "fulfilled") {
      const v = cyclesR.value as { data: MeritCycleRow[] }
      setCycles(v.data ?? [])
    } else if (canAdmin) {
      setCycles([])
      next.cycles = errorMessage(cyclesR.reason, "The merit cycles could not be read.")
    }

    if (allocationsR.status === "fulfilled") {
      const v = allocationsR.value as { data: MeritAllocationRow[] }
      setAllocations(v.data ?? [])
    } else if (canAdmin) {
      setAllocations([])
      next.allocations = errorMessage(allocationsR.reason, "The merit allocations could not be read.")
    }

    if (employeesR.status === "fulfilled") {
      const v = employeesR.value as { items: Employee[] }
      // fetchAllEmployees returns {items, total, complete}
      if (v && Array.isArray((v as unknown as { items: unknown }).items)) {
        setEmployees(v.items)
      } else {
        // fallback for mocked shape
        setEmployees([])
      }
    } else {
      setEmployees([])
      // not a section error — employees are auxiliary; silence unless workforce cares
    }

    if (jobsR.status === "fulfilled") {
      const v = jobsR.value as { data: Job[] | { items: Job[] } }
      const raw: unknown = v.data
      if (Array.isArray(raw)) setJobs(raw as Job[])
      else if (raw && typeof raw === "object" && Array.isArray((raw as { items: Job[] }).items))
        setJobs((raw as { items: Job[] }).items)
      else setJobs([])
    } else if (canAdmin) {
      setJobs([])
    }

    // Seed inline edits for goals
    if (goalsR.status === "fulfilled") {
      const v = goalsR.value as { data: GoalRow[] }
      const seed: Record<number, { progress: string; status: string }> = {}
      for (const g of v.data ?? []) seed[g.id] = { progress: String(g.progress ?? 0), status: g.status ?? "Not Started" }
      setGoalEdits(seed)
    }

    setErrors(next)
    setLoading(false)
  }, [canAdmin, canWorkforce])

  useEffect(() => {
    void load()
  }, [load])

  async function handleCreateGoal(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, goal: "" }))
    setNotice("")
    if (!goalForm.employee_id) {
      setFormErrors((c) => ({ ...c, goal: "Choose the employee for this goal." }))
      return
    }
    if (!goalForm.title.trim()) {
      setFormErrors((c) => ({ ...c, goal: "A goal needs a title." }))
      return
    }
    setBusy("goal")
    try {
      await api.post("/performance/goals", {
        employee_id: Number(goalForm.employee_id),
        title: goalForm.title.trim(),
        description: goalForm.description.trim() || null,
        weight: goalForm.weight === "" ? 0 : Number(goalForm.weight),
        progress: goalForm.progress === "" ? 0 : Number(goalForm.progress),
        status: goalForm.status || "Not Started",
        due_date: goalForm.due_date || null,
      })
      setGoalForm({ employee_id: "", title: "", description: "", weight: "", progress: "", status: "Not Started", due_date: "" })
      setNotice("Goal created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, goal: errorMessage(err, "The goal could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function handleUpdateGoal(id: number) {
    if (busy) return
    const edit = goalEdits[id]
    if (!edit) return
    setFormErrors((c) => ({ ...c, goal: "" }))
    setNotice("")
    setBusy(`goal-${id}`)
    try {
      await api.put(`/performance/goals/${id}`, {
        progress: Number(edit.progress),
        status: edit.status,
      })
      setNotice(`Goal #${id} updated.`)
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, goal: errorMessage(err, "The goal could not be updated.") }))
    } finally {
      setBusy("")
    }
  }

  async function handleCreateReview(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, review: "" }))
    setNotice("")
    if (!reviewForm.employee_id) {
      setFormErrors((c) => ({ ...c, review: "Choose the employee for this review." }))
      return
    }
    if (!reviewForm.period.trim()) {
      setFormErrors((c) => ({ ...c, review: "A review needs a period." }))
      return
    }
    setBusy("review")
    try {
      await api.post("/performance/reviews", {
        employee_id: Number(reviewForm.employee_id),
        reviewer_id: reviewForm.reviewer_id ? Number(reviewForm.reviewer_id) : null,
        period: reviewForm.period.trim(),
        status: reviewForm.status || "Draft",
        overall_rating: reviewForm.overall_rating === "" ? null : Number(reviewForm.overall_rating),
        manager_comments: reviewForm.manager_comments.trim() || null,
        employee_comments: reviewForm.employee_comments.trim() || null,
      })
      setReviewForm({
        employee_id: "",
        reviewer_id: "",
        period: "",
        status: "Draft",
        overall_rating: "",
        manager_comments: "",
        employee_comments: "",
      })
      setNotice("Performance review created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, review: errorMessage(err, "The review could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function handleFinalizeReview(id: number) {
    if (finalizing !== null) return
    setFormErrors((c) => ({ ...c, review: "" }))
    setNotice("")
    setFinalizing(id)
    try {
      await api.post(`/performance/reviews/${id}/finalize`)
      setNotice(`Review #${id} finalized.`)
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, review: errorMessage(err, "The review could not be finalized.") }))
    } finally {
      setFinalizing(null)
    }
  }

  async function handleCreateFeedback(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, feedback: "" }))
    setNotice("")
    if (!feedbackForm.review_id) {
      setFormErrors((c) => ({ ...c, feedback: "Choose the review this feedback belongs to." }))
      return
    }
    setBusy("feedback")
    try {
      await api.post("/performance/feedback", {
        review_id: Number(feedbackForm.review_id),
        from_employee_id: feedbackForm.from_employee_id ? Number(feedbackForm.from_employee_id) : null,
        feedback_type: feedbackForm.feedback_type || "Peer",
        rating: feedbackForm.rating === "" ? null : Number(feedbackForm.rating),
        comments: feedbackForm.comments.trim() || null,
      })
      setFeedbackForm({ review_id: "", from_employee_id: "", feedback_type: "Peer", rating: "", comments: "" })
      setNotice("Feedback submitted.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, feedback: errorMessage(err, "The feedback could not be submitted.") }))
    } finally {
      setBusy("")
    }
  }

  async function handleCreateBand(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, band: "" }))
    setNotice("")
    if (!bandForm.job_id) {
      setFormErrors((c) => ({ ...c, band: "Choose the job for this band." }))
      return
    }
    if (!bandForm.level.trim()) {
      setFormErrors((c) => ({ ...c, band: "A band needs a level." }))
      return
    }
    setBusy("band")
    try {
      await api.post("/performance/compensation-bands", {
        job_id: Number(bandForm.job_id),
        level: bandForm.level.trim(),
        min_salary: Number(bandForm.min_salary || 0),
        mid_salary: Number(bandForm.mid_salary || 0),
        max_salary: Number(bandForm.max_salary || 0),
        currency: bandForm.currency.trim() || "INR",
      })
      setBandForm({ job_id: "", level: "", min_salary: "", mid_salary: "", max_salary: "", currency: "INR" })
      setNotice("Compensation band created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, band: errorMessage(err, "The band could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function handleCreateCycle(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, cycle: "" }))
    setNotice("")
    if (!cycleForm.name.trim() || !cycleForm.year || !cycleForm.start_date || !cycleForm.end_date) {
      setFormErrors((c) => ({ ...c, cycle: "A cycle needs a name, year, start date and end date." }))
      return
    }
    if (cycleForm.end_date < cycleForm.start_date) {
      setFormErrors((c) => ({ ...c, cycle: "The end date cannot be before the start date." }))
      return
    }
    setBusy("cycle")
    try {
      await api.post("/performance/merit-cycles", {
        name: cycleForm.name.trim(),
        year: Number(cycleForm.year),
        budget_percent: Number(cycleForm.budget_percent || 0),
        start_date: cycleForm.start_date,
        end_date: cycleForm.end_date,
        status: cycleForm.status || "Draft",
      })
      setCycleForm({ name: "", year: "", budget_percent: "", start_date: "", end_date: "", status: "Draft" })
      setNotice("Merit cycle created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, cycle: errorMessage(err, "The merit cycle could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function handleCreateAllocation(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, allocation: "" }))
    setNotice("")
    if (!allocationForm.cycle_id || !allocationForm.employee_id) {
      setFormErrors((c) => ({ ...c, allocation: "Choose the cycle and the employee." }))
      return
    }
    setBusy("allocation")
    try {
      await api.post("/performance/merit-allocations", {
        cycle_id: Number(allocationForm.cycle_id),
        employee_id: Number(allocationForm.employee_id),
        current_salary: Number(allocationForm.current_salary || 0),
        proposed_salary: Number(allocationForm.proposed_salary || 0),
        increase_percent: Number(allocationForm.increase_percent || 0),
        status: allocationForm.status || "Draft",
      })
      setAllocationForm({
        cycle_id: "",
        employee_id: "",
        current_salary: "",
        proposed_salary: "",
        increase_percent: "",
        status: "Draft",
      })
      setNotice("Merit allocation created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, allocation: errorMessage(err, "The allocation could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  return (
    <Layout>
      <PageHeader
        compact
        title="Performance"
        description="Goals, reviews, feedback and compensation — every operator sees what their role allows."
      />

      {notice && <Alert tone="success">{notice}</Alert>}

      {/* Goals */}
      <SectionCard
        compact
        title="Goals"
        description="A goal belongs to one employee. Creating or updating one requires SuperAdmin, HR or Manager."
      >
        {!canWorkforce ? (
          <div className="p-5">
            <EmptyState
              title="Goals are read by SuperAdmin, HR, Manager and Associate"
              description="Your role does not read performance goals. An administrator can grant a workforce role."
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading goals…">
            <TableSkeleton rows={3} cols={5} />
          </LoadingRegion>
        ) : errors.goals ? (
          <div className="p-5">
            <RetryableAlert err={errors.goals} title="The goals could not be read" fallback="The goals could not be read" onRetry={load} />
          </div>
        ) : (
          <>
            {canManager && (
              <form onSubmit={handleCreateGoal} className="p-5 border-b border-border">
                {formErrors.goal && (
                  <p className="text-sm text-error-text mb-3" role="alert">
                    {formErrors.goal}
                  </p>
                )}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[200px]">
                    <Field label="Employee" htmlFor="goal-employee" required>
                      <Select
                        id="goal-employee"
                        value={goalForm.employee_id}
                        onChange={(e) => setGoalForm((f) => ({ ...f, employee_id: e.target.value }))}
                        required
                      >
                        <option value="">Select an employee…</option>
                        {employees.map((emp) => (
                          <option key={emp.id} value={emp.id}>
                            {emp.first_name} {emp.last_name} · {emp.employee_id}
                          </option>
                        ))}
                      </Select>
                    </Field>
                  </div>
                  <div className="flex-1 min-w-[200px]">
                    <Field label="Title" htmlFor="goal-title" required>
                      <Input
                        id="goal-title"
                        value={goalForm.title}
                        onChange={(e) => setGoalForm((f) => ({ ...f, title: e.target.value }))}
                        placeholder="e.g. Ship onboarding flow"
                        required
                      />
                    </Field>
                  </div>
                  <div className="min-w-[120px]">
                    <Field label="Weight" htmlFor="goal-weight">
                      <Input
                        id="goal-weight"
                        type="number"
                        min="0"
                        step="0.1"
                        value={goalForm.weight}
                        onChange={(e) => setGoalForm((f) => ({ ...f, weight: e.target.value }))}
                        placeholder="0"
                      />
                    </Field>
                  </div>
                  <div className="min-w-[120px]">
                    <Field label="Progress %" htmlFor="goal-progress">
                      <Input
                        id="goal-progress"
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        value={goalForm.progress}
                        onChange={(e) => setGoalForm((f) => ({ ...f, progress: e.target.value }))}
                        placeholder="0"
                      />
                    </Field>
                  </div>
                  <div className="min-w-[150px]">
                    <Field label="Status" htmlFor="goal-status">
                      <Select
                        id="goal-status"
                        value={goalForm.status}
                        onChange={(e) => setGoalForm((f) => ({ ...f, status: e.target.value }))}
                      >
                        <option value="Not Started">Not Started</option>
                        <option value="In Progress">In Progress</option>
                        <option value="Completed">Completed</option>
                        <option value="Cancelled">Cancelled</option>
                      </Select>
                    </Field>
                  </div>
                  <div className="min-w-[150px]">
                    <Field label="Due date" htmlFor="goal-due">
                      <Input
                        id="goal-due"
                        type="date"
                        value={goalForm.due_date}
                        onChange={(e) => setGoalForm((f) => ({ ...f, due_date: e.target.value }))}
                      />
                    </Field>
                  </div>
                  <Button type="submit" loading={busy === "goal"}>
                    Create goal
                  </Button>
                </div>
                <div className="mt-3">
                  <Field label="Description" htmlFor="goal-description">
                    <Textarea
                      id="goal-description"
                      value={goalForm.description}
                      onChange={(e) => setGoalForm((f) => ({ ...f, description: e.target.value }))}
                      placeholder="What does done look like?"
                      rows={2}
                    />
                  </Field>
                </div>
              </form>
            )}

            {goals.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No goals recorded yet.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base w-full text-sm">
                  <caption className="sr-only">Performance goals of this deployment</caption>
                  <thead>
                    <tr>
                      <th scope="col">Title</th>
                      <th scope="col">Employee</th>
                      <th scope="col">Progress</th>
                      <th scope="col">Status</th>
                      <th scope="col">Weight</th>
                      <th scope="col">Due</th>
                      {canManager && <th scope="col">Update</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {goals.map((g) => (
                      <tr key={g.id}>
                        <td className="font-medium">{g.title}</td>
                        <td>{employeeName(g.employee_id)}</td>
                        <td className="min-w-[160px]">
                          <Meter percent={Number(g.progress) || 0} label={`${g.progress ?? 0}%`} />
                        </td>
                        <td>
                          <StatusPill status={g.status} dot />
                        </td>
                        <td className="tabular-nums">{g.weight ?? "—"}</td>
                        <td>{fmtDate(g.due_date, tenantDateOpts)}</td>
                        {canManager && (
                          <td>
                            <div className="flex items-center gap-1">
                              <Input
                                aria-label={`Progress for goal ${g.id}`}
                                type="number"
                                min="0"
                                max="100"
                                step="1"
                                className="w-20"
                                value={goalEdits[g.id]?.progress ?? String(g.progress ?? 0)}
                                onChange={(e) =>
                                  setGoalEdits((m) => ({
                                    ...m,
                                    [g.id]: { progress: e.target.value, status: m[g.id]?.status ?? g.status },
                                  }))
                                }
                              />
                              <Select
                                aria-label={`Status for goal ${g.id}`}
                                className="w-36"
                                value={goalEdits[g.id]?.status ?? g.status}
                                onChange={(e) =>
                                  setGoalEdits((m) => ({
                                    ...m,
                                    [g.id]: { progress: m[g.id]?.progress ?? String(g.progress ?? 0), status: e.target.value },
                                  }))
                                }
                              >
                                <option value="Not Started">Not Started</option>
                                <option value="In Progress">In Progress</option>
                                <option value="Completed">Completed</option>
                                <option value="Cancelled">Cancelled</option>
                              </Select>
                              <Button
                                size="xs"
                                onClick={() => handleUpdateGoal(g.id)}
                                loading={busy === `goal-${g.id}`}
                              >
                                Save
                              </Button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      {/* Reviews */}
      <SectionCard
        compact
        title="Performance reviews"
        description="One review per employee per period. Finalizing is limited to SuperAdmin, HR and Manager."
      >
        {!canWorkforce ? (
          <div className="p-5">
            <EmptyState
              title="Reviews are read by SuperAdmin, HR, Manager and Associate"
              description="Your role does not read performance reviews."
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading reviews…">
            <TableSkeleton rows={3} cols={6} />
          </LoadingRegion>
        ) : errors.reviews ? (
          <div className="p-5">
            <RetryableAlert err={errors.reviews} title="The reviews could not be read" fallback="The reviews could not be read" onRetry={load} />
          </div>
        ) : (
          <>
            {formErrors.review && (
              <div className="px-5 pt-4">
                <Alert tone="error">{formErrors.review}</Alert>
              </div>
            )}
            {canManager && (
              <form onSubmit={handleCreateReview} className="p-5 border-b border-border">
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[200px]">
                    <Field label="Employee" htmlFor="review-employee" required>
                      <Select
                        id="review-employee"
                        value={reviewForm.employee_id}
                        onChange={(e) => setReviewForm((f) => ({ ...f, employee_id: e.target.value }))}
                        required
                      >
                        <option value="">Select an employee…</option>
                        {employees.map((emp) => (
                          <option key={emp.id} value={emp.id}>
                            {emp.first_name} {emp.last_name} · {emp.employee_id}
                          </option>
                        ))}
                      </Select>
                    </Field>
                  </div>
                  <div className="flex-1 min-w-[200px]">
                    <Field label="Reviewer" htmlFor="review-reviewer">
                      <Select
                        id="review-reviewer"
                        value={reviewForm.reviewer_id}
                        onChange={(e) => setReviewForm((f) => ({ ...f, reviewer_id: e.target.value }))}
                      >
                        <option value="">No reviewer</option>
                        {employees.map((emp) => (
                          <option key={emp.id} value={emp.id}>
                            {emp.first_name} {emp.last_name}
                          </option>
                        ))}
                      </Select>
                    </Field>
                  </div>
                  <div className="min-w-[160px]">
                    <Field label="Period" htmlFor="review-period" required>
                      <Input
                        id="review-period"
                        value={reviewForm.period}
                        onChange={(e) => setReviewForm((f) => ({ ...f, period: e.target.value }))}
                        placeholder="e.g. 2026-H1"
                        required
                      />
                    </Field>
                  </div>
                  <div className="min-w-[130px]">
                    <Field label="Status" htmlFor="review-status">
                      <Select
                        id="review-status"
                        value={reviewForm.status}
                        onChange={(e) => setReviewForm((f) => ({ ...f, status: e.target.value }))}
                      >
                        <option value="Draft">Draft</option>
                        <option value="In Progress">In Progress</option>
                        <option value="Submitted">Submitted</option>
                        <option value="Finalized">Finalized</option>
                      </Select>
                    </Field>
                  </div>
                  <div className="min-w-[120px]">
                    <Field label="Rating" htmlFor="review-rating">
                      <Input
                        id="review-rating"
                        type="number"
                        min="0"
                        max="5"
                        step="0.1"
                        value={reviewForm.overall_rating}
                        onChange={(e) => setReviewForm((f) => ({ ...f, overall_rating: e.target.value }))}
                        placeholder="—"
                      />
                    </Field>
                  </div>
                  <Button type="submit" loading={busy === "review"}>
                    Create review
                  </Button>
                </div>
                <div className="flex flex-wrap gap-3 mt-3">
                  <div className="flex-1 min-w-[240px]">
                    <Field label="Manager comments" htmlFor="review-mc">
                      <Textarea
                        id="review-mc"
                        value={reviewForm.manager_comments}
                        onChange={(e) => setReviewForm((f) => ({ ...f, manager_comments: e.target.value }))}
                        rows={2}
                      />
                    </Field>
                  </div>
                  <div className="flex-1 min-w-[240px]">
                    <Field label="Employee comments" htmlFor="review-ec">
                      <Textarea
                        id="review-ec"
                        value={reviewForm.employee_comments}
                        onChange={(e) => setReviewForm((f) => ({ ...f, employee_comments: e.target.value }))}
                        rows={2}
                      />
                    </Field>
                  </div>
                </div>
              </form>
            )}

            {reviews.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No reviews recorded yet.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base w-full text-sm">
                  <caption className="sr-only">Performance reviews of this deployment</caption>
                  <thead>
                    <tr>
                      <th scope="col">Period</th>
                      <th scope="col">Employee</th>
                      <th scope="col">Reviewer</th>
                      <th scope="col">Status</th>
                      <th scope="col" className="num">Rating</th>
                      <th scope="col">Finalized</th>
                      {canManager && <th scope="col">Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {reviews.map((r) => (
                      <tr key={r.id}>
                        <td className="font-medium">{r.period}</td>
                        <td>{employeeName(r.employee_id)}</td>
                        <td>{r.reviewer_id ? employeeName(r.reviewer_id) : "—"}</td>
                        <td>
                          <StatusPill status={r.status} dot />
                        </td>
                        <td className="num tabular-nums">{r.overall_rating ?? "—"}</td>
                        <td>{fmtDateTime(r.finalized_at, tenantDateOpts)}</td>
                        {canManager && (
                          <td>
                            {r.status === "Finalized" || r.finalized_at ? (
                              <span className="text-xs text-text-secondary">Finalized</span>
                            ) : (
                              <Button
                                size="xs"
                                loading={finalizing === r.id}
                                onClick={() => handleFinalizeReview(r.id)}
                              >
                                Finalize
                              </Button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      {/* Feedback */}
      <SectionCard
        compact
        title="Review feedback"
        description="Feedback on a review. Any workforce role may read and submit feedback."
      >
        {!canWorkforce ? (
          <div className="p-5">
            <EmptyState
              title="Feedback is available to SuperAdmin, HR, Manager and Associate"
              description="Your role does not read review feedback."
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading feedback…">
            <TableSkeleton rows={3} cols={5} />
          </LoadingRegion>
        ) : errors.feedback ? (
          <div className="p-5">
            <RetryableAlert err={errors.feedback} title="The feedback could not be read" fallback="The feedback could not be read" onRetry={load} />
          </div>
        ) : (
          <>
            <form onSubmit={handleCreateFeedback} className="p-5 border-b border-border">
              {formErrors.feedback && (
                <p className="text-sm text-error-text mb-3" role="alert">
                  {formErrors.feedback}
                </p>
              )}
              <div className="flex flex-wrap gap-3 items-end">
                <div className="flex-1 min-w-[200px]">
                  <Field label="Review" htmlFor="feedback-review" required>
                    <Select
                      id="feedback-review"
                      value={feedbackForm.review_id}
                      onChange={(e) => setFeedbackForm((f) => ({ ...f, review_id: e.target.value }))}
                      required
                    >
                      <option value="">Select a review…</option>
                      {reviews.map((r) => (
                        <option key={r.id} value={r.id}>
                          Review #{r.id} · {r.period} · {employeeName(r.employee_id)}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
                <div className="flex-1 min-w-[200px]">
                  <Field label="From employee" htmlFor="feedback-from">
                    <Select
                      id="feedback-from"
                      value={feedbackForm.from_employee_id}
                      onChange={(e) => setFeedbackForm((f) => ({ ...f, from_employee_id: e.target.value }))}
                    >
                      <option value="">Anonymous / not stated</option>
                      {employees.map((emp) => (
                        <option key={emp.id} value={emp.id}>
                          {emp.first_name} {emp.last_name}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
                <div className="min-w-[140px]">
                  <Field label="Type" htmlFor="feedback-type">
                    <Select
                      id="feedback-type"
                      value={feedbackForm.feedback_type}
                      onChange={(e) => setFeedbackForm((f) => ({ ...f, feedback_type: e.target.value }))}
                    >
                      <option value="Peer">Peer</option>
                      <option value="Manager">Manager</option>
                      <option value="Self">Self</option>
                      <option value="Upward">Upward</option>
                    </Select>
                  </Field>
                </div>
                <div className="min-w-[120px]">
                  <Field label="Rating" htmlFor="feedback-rating">
                    <Input
                      id="feedback-rating"
                      type="number"
                      min="0"
                      max="5"
                      step="0.1"
                      value={feedbackForm.rating}
                      onChange={(e) => setFeedbackForm((f) => ({ ...f, rating: e.target.value }))}
                      placeholder="—"
                    />
                  </Field>
                </div>
                <Button type="submit" loading={busy === "feedback"}>
                  Submit feedback
                </Button>
              </div>
              <div className="mt-3">
                <Field label="Comments" htmlFor="feedback-comments">
                  <Textarea
                    id="feedback-comments"
                    value={feedbackForm.comments}
                    onChange={(e) => setFeedbackForm((f) => ({ ...f, comments: e.target.value }))}
                    rows={2}
                    placeholder="What went well? What could be better?"
                  />
                </Field>
              </div>
            </form>

            {feedback.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No feedback recorded yet.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base w-full text-sm">
                  <caption className="sr-only">Feedback on performance reviews</caption>
                  <thead>
                    <tr>
                      <th scope="col">Review</th>
                      <th scope="col">From</th>
                      <th scope="col">Type</th>
                      <th scope="col" className="num">Rating</th>
                      <th scope="col">Comments</th>
                      <th scope="col">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {feedback.map((fb) => (
                      <tr key={fb.id}>
                        <td>#{fb.review_id}</td>
                        <td>{fb.from_employee_id ? employeeName(fb.from_employee_id) : "—"}</td>
                        <td>{fb.feedback_type}</td>
                        <td className="num tabular-nums">{fb.rating ?? "—"}</td>
                        <td className="max-w-[260px] truncate" title={fb.comments ?? ""}>
                          {fb.comments ?? "—"}
                        </td>
                        <td>{fmtDate(fb.created_at, tenantDateOpts)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      {/* Compensation bands */}
      <SectionCard
        compact
        title="Compensation bands"
        description="Salary bands by job and level. Viewing and creating bands requires SuperAdmin or HR."
      >
        {!canAdmin ? (
          <div className="p-5">
            <EmptyState
              title="Compensation bands are managed by SuperAdmin and HR"
              description="Your role does not read compensation bands. They are visible only to SuperAdmin and HR."
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading compensation bands…">
            <TableSkeleton rows={3} cols={5} />
          </LoadingRegion>
        ) : errors.bands ? (
          <div className="p-5">
            <RetryableAlert err={errors.bands} title="The compensation bands could not be read" fallback="The compensation bands could not be read" onRetry={load} />
          </div>
        ) : (
          <>
            <form onSubmit={handleCreateBand} className="p-5 border-b border-border">
              {formErrors.band && (
                <p className="text-sm text-error-text mb-3" role="alert">
                  {formErrors.band}
                </p>
              )}
              <div className="flex flex-wrap gap-3 items-end">
                <div className="flex-1 min-w-[220px]">
                  <Field label="Job" htmlFor="band-job" required>
                    <Select
                      id="band-job"
                      value={bandForm.job_id}
                      onChange={(e) => setBandForm((f) => ({ ...f, job_id: e.target.value }))}
                      required
                    >
                      <option value="">Select a job…</option>
                      {jobs.map((j) => (
                        <option key={j.id} value={j.id}>
                          {j.title} · {j.code}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
                <div className="min-w-[140px]">
                  <Field label="Level" htmlFor="band-level" required>
                    <Input
                      id="band-level"
                      value={bandForm.level}
                      onChange={(e) => setBandForm((f) => ({ ...f, level: e.target.value }))}
                      placeholder="e.g. L3"
                      required
                    />
                  </Field>
                </div>
                <div className="min-w-[130px]">
                  <Field label="Min salary" htmlFor="band-min">
                    <Input
                      id="band-min"
                      type="number"
                      min="0"
                      step="0.01"
                      value={bandForm.min_salary}
                      onChange={(e) => setBandForm((f) => ({ ...f, min_salary: e.target.value }))}
                      placeholder="0"
                    />
                  </Field>
                </div>
                <div className="min-w-[130px]">
                  <Field label="Mid salary" htmlFor="band-mid">
                    <Input
                      id="band-mid"
                      type="number"
                      min="0"
                      step="0.01"
                      value={bandForm.mid_salary}
                      onChange={(e) => setBandForm((f) => ({ ...f, mid_salary: e.target.value }))}
                      placeholder="0"
                    />
                  </Field>
                </div>
                <div className="min-w-[130px]">
                  <Field label="Max salary" htmlFor="band-max">
                    <Input
                      id="band-max"
                      type="number"
                      min="0"
                      step="0.01"
                      value={bandForm.max_salary}
                      onChange={(e) => setBandForm((f) => ({ ...f, max_salary: e.target.value }))}
                      placeholder="0"
                    />
                  </Field>
                </div>
                <div className="min-w-[100px]">
                  <Field label="Currency" htmlFor="band-currency">
                    <Input
                      id="band-currency"
                      value={bandForm.currency}
                      onChange={(e) => setBandForm((f) => ({ ...f, currency: e.target.value.toUpperCase() }))}
                      maxLength={3}
                      placeholder="INR"
                    />
                  </Field>
                </div>
                <Button type="submit" loading={busy === "band"}>
                  Create band
                </Button>
              </div>
            </form>

            {bands.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No compensation bands exist yet.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base w-full text-sm">
                  <caption className="sr-only">Compensation bands of this deployment</caption>
                  <thead>
                    <tr>
                      <th scope="col">Job</th>
                      <th scope="col">Level</th>
                      <th scope="col" className="num">Min</th>
                      <th scope="col" className="num">Mid</th>
                      <th scope="col" className="num">Max</th>
                      <th scope="col">Currency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bands.map((b) => (
                      <tr key={b.id}>
                        <td>{jobName(b.job_id)}</td>
                        <td>{b.level}</td>
                        <td className="num tabular-nums">{money(b.min_salary, { locale: tenantLocale, currency: b.currency || tenantCurrency })}</td>
                        <td className="num tabular-nums">{money(b.mid_salary, { locale: tenantLocale, currency: b.currency || tenantCurrency })}</td>
                        <td className="num tabular-nums">{money(b.max_salary, { locale: tenantLocale, currency: b.currency || tenantCurrency })}</td>
                        <td>{b.currency}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      {/* Merit cycles */}
      <SectionCard
        compact
        title="Merit cycles"
        description="Annual compensation review cycles. Viewing and creating cycles requires SuperAdmin or HR."
      >
        {!canAdmin ? (
          <div className="p-5">
            <EmptyState
              title="Merit cycles are managed by SuperAdmin and HR"
              description="Your role does not read merit cycles."
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading merit cycles…">
            <TableSkeleton rows={3} cols={5} />
          </LoadingRegion>
        ) : errors.cycles ? (
          <div className="p-5">
            <RetryableAlert err={errors.cycles} title="The merit cycles could not be read" fallback="The merit cycles could not be read" onRetry={load} />
          </div>
        ) : (
          <>
            <form onSubmit={handleCreateCycle} className="p-5 border-b border-border">
              {formErrors.cycle && (
                <p className="text-sm text-error-text mb-3" role="alert">
                  {formErrors.cycle}
                </p>
              )}
              <div className="flex flex-wrap gap-3 items-end">
                <div className="flex-1 min-w-[180px]">
                  <Field label="Name" htmlFor="cycle-name" required>
                    <Input
                      id="cycle-name"
                      value={cycleForm.name}
                      onChange={(e) => setCycleForm((f) => ({ ...f, name: e.target.value }))}
                      placeholder="e.g. FY26 Merit"
                      required
                    />
                  </Field>
                </div>
                <div className="min-w-[110px]">
                  <Field label="Year" htmlFor="cycle-year" required>
                    <Input
                      id="cycle-year"
                      type="number"
                      min="2000"
                      max="2100"
                      value={cycleForm.year}
                      onChange={(e) => setCycleForm((f) => ({ ...f, year: e.target.value }))}
                      placeholder="2026"
                      required
                    />
                  </Field>
                </div>
                <div className="min-w-[130px]">
                  <Field label="Budget %" htmlFor="cycle-budget">
                    <Input
                      id="cycle-budget"
                      type="number"
                      min="0"
                      step="0.1"
                      value={cycleForm.budget_percent}
                      onChange={(e) => setCycleForm((f) => ({ ...f, budget_percent: e.target.value }))}
                      placeholder="0"
                    />
                  </Field>
                </div>
                <div className="min-w-[150px]">
                  <Field label="Start date" htmlFor="cycle-start" required>
                    <Input
                      id="cycle-start"
                      type="date"
                      value={cycleForm.start_date}
                      onChange={(e) => setCycleForm((f) => ({ ...f, start_date: e.target.value }))}
                      required
                    />
                  </Field>
                </div>
                <div className="min-w-[150px]">
                  <Field label="End date" htmlFor="cycle-end" required>
                    <Input
                      id="cycle-end"
                      type="date"
                      value={cycleForm.end_date}
                      onChange={(e) => setCycleForm((f) => ({ ...f, end_date: e.target.value }))}
                      required
                    />
                  </Field>
                </div>
                <div className="min-w-[130px]">
                  <Field label="Status" htmlFor="cycle-status">
                    <Select
                      id="cycle-status"
                      value={cycleForm.status}
                      onChange={(e) => setCycleForm((f) => ({ ...f, status: e.target.value }))}
                    >
                      <option value="Draft">Draft</option>
                      <option value="Open">Open</option>
                      <option value="Closed">Closed</option>
                    </Select>
                  </Field>
                </div>
                <Button type="submit" loading={busy === "cycle"}>
                  Create cycle
                </Button>
              </div>
            </form>

            {cycles.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No merit cycles exist yet.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base w-full text-sm">
                  <caption className="sr-only">Merit cycles of this deployment</caption>
                  <thead>
                    <tr>
                      <th scope="col">Name</th>
                      <th scope="col">Year</th>
                      <th scope="col" className="num">Budget %</th>
                      <th scope="col">Starts</th>
                      <th scope="col">Ends</th>
                      <th scope="col">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cycles.map((c) => (
                      <tr key={c.id}>
                        <td className="font-medium">{c.name}</td>
                        <td>{c.year}</td>
                        <td className="num tabular-nums">{c.budget_percent ?? "—"}</td>
                        <td>{fmtDate(c.start_date, tenantDateOpts)}</td>
                        <td>{fmtDate(c.end_date, tenantDateOpts)}</td>
                        <td>
                          <StatusPill status={c.status} dot />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      {/* Allocations */}
      <SectionCard
        compact
        title="Merit allocations"
        description="Proposed increases inside a merit cycle. Viewing and creating allocations requires SuperAdmin or HR."
      >
        {!canAdmin ? (
          <div className="p-5">
            <EmptyState
              title="Merit allocations are managed by SuperAdmin and HR"
              description="Your role does not read merit allocations."
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading merit allocations…">
            <TableSkeleton rows={3} cols={6} />
          </LoadingRegion>
        ) : errors.allocations ? (
          <div className="p-5">
            <RetryableAlert err={errors.allocations} title="The merit allocations could not be read" fallback="The merit allocations could not be read" onRetry={load} />
          </div>
        ) : (
          <>
            <form onSubmit={handleCreateAllocation} className="p-5 border-b border-border">
              {formErrors.allocation && (
                <p className="text-sm text-error-text mb-3" role="alert">
                  {formErrors.allocation}
                </p>
              )}
              <div className="flex flex-wrap gap-3 items-end">
                <div className="flex-1 min-w-[200px]">
                  <Field label="Cycle" htmlFor="alloc-cycle" required>
                    <Select
                      id="alloc-cycle"
                      value={allocationForm.cycle_id}
                      onChange={(e) => setAllocationForm((f) => ({ ...f, cycle_id: e.target.value }))}
                      required
                      disabled={cycles.length === 0}
                    >
                      <option value="">{cycles.length === 0 ? "No cycle available" : "Select a cycle…"}</option>
                      {cycles.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} · {c.year}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
                <div className="flex-1 min-w-[200px]">
                  <Field label="Employee" htmlFor="alloc-employee" required>
                    <Select
                      id="alloc-employee"
                      value={allocationForm.employee_id}
                      onChange={(e) => setAllocationForm((f) => ({ ...f, employee_id: e.target.value }))}
                      required
                    >
                      <option value="">Select an employee…</option>
                      {employees.map((emp) => (
                        <option key={emp.id} value={emp.id}>
                          {emp.first_name} {emp.last_name} · {emp.employee_id}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
                <div className="min-w-[130px]">
                  <Field label="Current salary" htmlFor="alloc-current">
                    <Input
                      id="alloc-current"
                      type="number"
                      min="0"
                      step="0.01"
                      value={allocationForm.current_salary}
                      onChange={(e) => setAllocationForm((f) => ({ ...f, current_salary: e.target.value }))}
                      placeholder="0"
                    />
                  </Field>
                </div>
                <div className="min-w-[130px]">
                  <Field label="Proposed salary" htmlFor="alloc-proposed">
                    <Input
                      id="alloc-proposed"
                      type="number"
                      min="0"
                      step="0.01"
                      value={allocationForm.proposed_salary}
                      onChange={(e) => setAllocationForm((f) => ({ ...f, proposed_salary: e.target.value }))}
                      placeholder="0"
                    />
                  </Field>
                </div>
                <div className="min-w-[120px]">
                  <Field label="Increase %" htmlFor="alloc-pct">
                    <Input
                      id="alloc-pct"
                      type="number"
                      min="0"
                      step="0.1"
                      value={allocationForm.increase_percent}
                      onChange={(e) => setAllocationForm((f) => ({ ...f, increase_percent: e.target.value }))}
                      placeholder="0"
                    />
                  </Field>
                </div>
                <div className="min-w-[130px]">
                  <Field label="Status" htmlFor="alloc-status">
                    <Select
                      id="alloc-status"
                      value={allocationForm.status}
                      onChange={(e) => setAllocationForm((f) => ({ ...f, status: e.target.value }))}
                    >
                      <option value="Draft">Draft</option>
                      <option value="Proposed">Proposed</option>
                      <option value="Approved">Approved</option>
                    </Select>
                  </Field>
                </div>
                <Button type="submit" loading={busy === "allocation"} disabled={cycles.length === 0}>
                  Create allocation
                </Button>
              </div>
              {cycles.length === 0 && (
                <p className="text-xs text-text-secondary mt-2">A cycle must exist before an allocation can be created.</p>
              )}
            </form>

            {allocations.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No merit allocations exist yet.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base w-full text-sm">
                  <caption className="sr-only">Merit allocations of this deployment</caption>
                  <thead>
                    <tr>
                      <th scope="col">Cycle</th>
                      <th scope="col">Employee</th>
                      <th scope="col" className="num">Current</th>
                      <th scope="col" className="num">Proposed</th>
                      <th scope="col" className="num">Increase %</th>
                      <th scope="col">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allocations.map((a) => (
                      <tr key={a.id}>
                        <td>
                          {cycles.find((c) => c.id === a.cycle_id)?.name ?? `Cycle #${a.cycle_id}`}
                        </td>
                        <td>{employeeName(a.employee_id)}</td>
                        <td className="num tabular-nums">{money(a.current_salary, { locale: tenantLocale, currency: tenantCurrency })}</td>
                        <td className="num tabular-nums">{money(a.proposed_salary, { locale: tenantLocale, currency: tenantCurrency })}</td>
                        <td className="num tabular-nums">{a.increase_percent ?? "—"}</td>
                        <td>
                          <StatusPill status={a.status} dot />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>
    </Layout>
  )
}
