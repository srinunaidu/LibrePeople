import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Layout } from "@/components/Layout"
import {Alert, EmptyState, PageHeader, SectionCard, StatusPill, TableSkeleton, LoadingRegion, RetryableAlert} from "@/components/ui"
import { Button } from "@/components/ui/button"
import { Input, Select, Checkbox, Textarea } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { formatDate, formatDateTime } from "@/lib/format"
import api, { errorMessage } from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import type {
  Employee,
  CourseRow,
  EnrollmentRow,
  CertificationRow,
  TalentPoolRow,
  SuccessionPlanRow,
} from "@/types"

const ADMIN_ROLES = ["SuperAdmin", "HR"]
const WORKFORCE_ROLES = ["SuperAdmin", "HR", "Manager", "Associate"]
const MANAGER_ROLES = ["SuperAdmin", "HR", "Manager"]

const READINESS_OPTIONS = [
  "Ready now",
  "Ready in 1 year",
  "Ready in 2-3 years",
  "Ready in 3-5 years",
]

export default function LearningHub() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const localeOpts = { locale: tenant?.locale, timeZone: tenant?.timezone }
  // Dates render in the tenant locale/timezone via format.ts —
  // never the browser default.
  const fmtDate = (value?: string | null) => formatDate(value, localeOpts)
  const fmtDateTime = (value?: string | null) => formatDateTime(value, localeOpts)
  const role = user?.role ?? ""
  const canAdmin = ADMIN_ROLES.includes(role)
  const canWorkforce = WORKFORCE_ROLES.includes(role)
  const canManager = MANAGER_ROLES.includes(role)

  const [courses, setCourses] = useState<CourseRow[]>([])
  const [enrollments, setEnrollments] = useState<EnrollmentRow[]>([])
  const [certifications, setCertifications] = useState<CertificationRow[]>([])
  const [pools, setPools] = useState<TalentPoolRow[]>([])
  const [succession, setSuccession] = useState<SuccessionPlanRow[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [positions, setPositions] = useState<{ id: number; code: string; title: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState("")

  const [courseForm, setCourseForm] = useState({ title: "", code: "", description: "", category: "General", duration_hours: "", is_mandatory: false, is_active: true })
  const [enrollForm, setEnrollForm] = useState({ employee_id: "", course_id: "", status: "Enrolled", score: "" })
  const [certForm, setCertForm] = useState({ employee_id: "", name: "", issuer: "", issued_date: "", expiry_date: "", certificate_url: "" })
  const [poolForm, setPoolForm] = useState({ name: "", description: "" })
  const [memberForm, setMemberForm] = useState({ pool_id: "", employee_id: "", readiness: "Ready in 2-3 years", notes: "" })
  const [successionForm, setSuccessionForm] = useState({ position_id: "", primary_successor_id: "", backup_successor_id: "", readiness: "Ready in 2-3 years", notes: "" })
  const [busy, setBusy] = useState<"" | "course" | "enroll" | "cert" | "pool" | "member" | "succession" | string>("")
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [completeScores, setCompleteScores] = useState<Record<number, string>>({})

  const load = useCallback(async () => {
    setLoading(true)
    setErrors({})
    const [courseRes, enrollRes, certRes, poolRes, successionRes, empRes, posRes] = await Promise.allSettled([
      api.get<CourseRow[]>("/learning/courses"),
      canWorkforce ? api.get<EnrollmentRow[]>("/learning/course-enrollments") : Promise.resolve(null as any),
      canWorkforce ? api.get<CertificationRow[]>("/learning/certifications") : Promise.resolve(null as any),
      canManager ? api.get<TalentPoolRow[]>("/learning/talent-pools") : Promise.resolve(null as any),
      canManager ? api.get<SuccessionPlanRow[]>("/learning/succession-plans") : Promise.resolve(null as any),
      fetchAllEmployees(),
      canManager ? api.get<{ id: number; code: string; title: string }[]>("/core-hr/positions").catch(() => ({ data: [] as any })) : Promise.resolve({ data: [] as any }),
    ])
    const next: Record<string, string> = {}
    if (courseRes.status === "fulfilled") {
      setCourses(courseRes.value?.data ?? [])
    } else {
      setCourses([])
      next.courses = errorMessage(courseRes.reason, "The courses could not be read.")
    }
    if (enrollRes.status === "fulfilled") {
      setEnrollments((enrollRes.value as any)?.data ?? [])
    } else {
      setEnrollments([])
      next.enrollments = errorMessage((enrollRes as PromiseRejectedResult).reason, "The enrollments could not be read.")
    }
    if (certRes.status === "fulfilled") {
      setCertifications((certRes.value as any)?.data ?? [])
    } else {
      setCertifications([])
      next.certifications = errorMessage((certRes as PromiseRejectedResult).reason, "The certifications could not be read.")
    }
    if (poolRes.status === "fulfilled") {
      setPools((poolRes.value as any)?.data ?? [])
    } else {
      setPools([])
      next.pools = errorMessage((poolRes as PromiseRejectedResult).reason, "The talent pools could not be read.")
    }
    if (successionRes.status === "fulfilled") {
      setSuccession((successionRes.value as any)?.data ?? [])
    } else {
      setSuccession([])
      next.succession = errorMessage((successionRes as PromiseRejectedResult).reason, "The succession plans could not be read.")
    }
    if (empRes.status === "fulfilled") {
      setEmployees(empRes.value.items)
    } else {
      setEmployees([])
    }
    if (posRes.status === "fulfilled") {
      const v: any = posRes.value
      // posRes may be axios response or null
      const data = v?.data ?? []
      setPositions(Array.isArray(data) ? data : [])
    } else {
      setPositions([])
    }
    setErrors(next)
    setLoading(false)
  }, [canManager, canWorkforce])

  useEffect(() => { void load() }, [load])

  const employeeName = (id: number) => {
    const f = employees.find((r) => r.id === id)
    return f ? `${f.first_name} ${f.last_name}` : `Employee #${id}`
  }
  const courseTitle = (id: number) => {
    const f = courses.find((r) => r.id === id)
    return f ? f.title : `Course #${id}`
  }
  const poolName = (id: number) => {
    const f = pools.find((r) => r.id === id)
    return f ? f.name : `Pool #${id}`
  }
  const positionLabel = (id: number) => {
    const f = positions.find((r) => r.id === id)
    return f ? `${f.code} — ${f.title}` : `Position #${id}`
  }

  async function submitCourse(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, course: "" }))
    setNotice("")
    if (!courseForm.title.trim() || !courseForm.code.trim()) {
      setFormErrors((c) => ({ ...c, course: "Title and code are required." }))
      return
    }
    setBusy("course")
    try {
      await api.post("/learning/courses", {
        title: courseForm.title.trim(),
        code: courseForm.code.trim(),
        description: courseForm.description.trim() || null,
        category: courseForm.category.trim() || "General",
        duration_hours: Number(courseForm.duration_hours || 0),
        is_mandatory: courseForm.is_mandatory,
        is_active: courseForm.is_active,
      })
      setCourseForm({ title: "", code: "", description: "", category: "General", duration_hours: "", is_mandatory: false, is_active: true })
      setNotice("Course created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, course: errorMessage(err, "The course could not be created.") }))
    } finally { setBusy("") }
  }

  async function submitEnrollment(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, enroll: "" }))
    setNotice("")
    if (!enrollForm.employee_id || !enrollForm.course_id) {
      setFormErrors((c) => ({ ...c, enroll: "Choose an employee and a course." }))
      return
    }
    setBusy("enroll")
    try {
      await api.post("/learning/course-enrollments", {
        employee_id: Number(enrollForm.employee_id),
        course_id: Number(enrollForm.course_id),
        status: enrollForm.status.trim() || "Enrolled",
        score: enrollForm.score ? Number(enrollForm.score) : null,
      })
      setEnrollForm({ employee_id: "", course_id: "", status: "Enrolled", score: "" })
      setNotice("Enrollment created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, enroll: errorMessage(err, "The enrollment could not be created.") }))
    } finally { setBusy("") }
  }

  async function completeEnrollment(id: number) {
    if (busy) return
    setBusy(`complete-${id}`)
    setNotice("")
    setFormErrors((c) => ({ ...c, enroll: "" }))
    try {
      const scoreVal = completeScores[id]
      const params = scoreVal ? { score: Number(scoreVal) } : {}
      await api.put(`/learning/course-enrollments/${id}/complete`, null, { params })
      setNotice("Enrollment marked completed.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, enroll: errorMessage(err, "The enrollment could not be completed.") }))
    } finally { setBusy("") }
  }

  async function submitCert(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, cert: "" }))
    setNotice("")
    if (!certForm.employee_id || !certForm.name.trim() || !certForm.issued_date) {
      setFormErrors((c) => ({ ...c, cert: "Employee, name and issued date are required." }))
      return
    }
    setBusy("cert")
    try {
      await api.post("/learning/certifications", {
        employee_id: Number(certForm.employee_id),
        name: certForm.name.trim(),
        issuer: certForm.issuer.trim() || null,
        issued_date: certForm.issued_date,
        expiry_date: certForm.expiry_date || null,
        certificate_url: certForm.certificate_url.trim() || null,
      })
      setCertForm({ employee_id: "", name: "", issuer: "", issued_date: "", expiry_date: "", certificate_url: "" })
      setNotice("Certification created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, cert: errorMessage(err, "The certification could not be created.") }))
    } finally { setBusy("") }
  }

  async function submitPool(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, pool: "" }))
    setNotice("")
    if (!poolForm.name.trim()) {
      setFormErrors((c) => ({ ...c, pool: "Pool name is required." }))
      return
    }
    setBusy("pool")
    try {
      await api.post("/learning/talent-pools", {
        name: poolForm.name.trim(),
        description: poolForm.description.trim() || null,
      })
      setPoolForm({ name: "", description: "" })
      setNotice("Talent pool created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, pool: errorMessage(err, "The talent pool could not be created.") }))
    } finally { setBusy("") }
  }

  async function submitMember(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, member: "" }))
    setNotice("")
    if (!memberForm.pool_id || !memberForm.employee_id) {
      setFormErrors((c) => ({ ...c, member: "Choose a pool and an employee." }))
      return
    }
    setBusy("member")
    try {
      await api.post("/learning/talent-pool-members", {
        pool_id: Number(memberForm.pool_id),
        employee_id: Number(memberForm.employee_id),
        readiness: memberForm.readiness,
        notes: memberForm.notes.trim() || null,
      })
      setMemberForm({ pool_id: "", employee_id: "", readiness: "Ready in 2-3 years", notes: "" })
      setNotice("Member added to pool.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, member: errorMessage(err, "The pool member could not be added.") }))
    } finally { setBusy("") }
  }

  async function submitSuccession(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, succession: "" }))
    setNotice("")
    if (!successionForm.position_id) {
      setFormErrors((c) => ({ ...c, succession: "Choose a position." }))
      return
    }
    setBusy("succession")
    try {
      await api.post("/learning/succession-plans", {
        position_id: Number(successionForm.position_id),
        primary_successor_id: successionForm.primary_successor_id ? Number(successionForm.primary_successor_id) : null,
        backup_successor_id: successionForm.backup_successor_id ? Number(successionForm.backup_successor_id) : null,
        readiness: successionForm.readiness,
        notes: successionForm.notes.trim() || null,
      })
      setSuccessionForm({ position_id: "", primary_successor_id: "", backup_successor_id: "", readiness: "Ready in 2-3 years", notes: "" })
      setNotice("Succession plan created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, succession: errorMessage(err, "The succession plan could not be created.") }))
    } finally { setBusy("") }
  }

  return (
    <Layout>
      <PageHeader compact title="Learning" description="Courses, enrollments, certifications, talent pools and succession" />

      {notice && <Alert tone="success">{notice}</Alert>}

      {/* Courses */}
      <SectionCard compact title="Courses" description="The catalogue. Creating a course is limited to SuperAdmin and HR.">
        {loading ? (
          <LoadingRegion label="Loading courses…"><TableSkeleton rows={3} cols={6} /></LoadingRegion>
        ) : errors.courses ? (
          <div className="p-5"><RetryableAlert err={errors.courses} title="The courses could not be read" fallback="The courses could not be read" onRetry={load} /></div>
        ) : (
          <>
            {canAdmin && (
              <form onSubmit={submitCourse} className="p-5 border-b border-border">
                {formErrors.course && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.course}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="min-w-[120px]">
                    <label htmlFor="course-code" className="block text-xs font-medium text-text-secondary mb-1">Code</label>
                    <Input id="course-code" value={courseForm.code} onChange={(e) => setCourseForm((f) => ({ ...f, code: e.target.value }))} placeholder="e.g. SEC-101" required />
                  </div>
                  <div className="flex-1 min-w-[200px]">
                    <label htmlFor="course-title" className="block text-xs font-medium text-text-secondary mb-1">Title</label>
                    <Input id="course-title" value={courseForm.title} onChange={(e) => setCourseForm((f) => ({ ...f, title: e.target.value }))} placeholder="Course title" required />
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="course-category" className="block text-xs font-medium text-text-secondary mb-1">Category</label>
                    <Input id="course-category" value={courseForm.category} onChange={(e) => setCourseForm((f) => ({ ...f, category: e.target.value }))} placeholder="General" />
                  </div>
                  <div className="min-w-[130px]">
                    <label htmlFor="course-duration" className="block text-xs font-medium text-text-secondary mb-1">Duration (hours)</label>
                    <Input id="course-duration" type="number" min="0" step="0.5" value={courseForm.duration_hours} onChange={(e) => setCourseForm((f) => ({ ...f, duration_hours: e.target.value }))} />
                  </div>
                  <Checkbox id="course-mandatory" label="Mandatory" checked={courseForm.is_mandatory} onChange={(e) => setCourseForm((f) => ({ ...f, is_mandatory: e.target.checked }))} />
                  <Checkbox id="course-active" label="Active" checked={courseForm.is_active} onChange={(e) => setCourseForm((f) => ({ ...f, is_active: e.target.checked }))} />
                  <Button type="submit" loading={busy === "course"}>Create course</Button>
                </div>
                <div className="mt-3">
                  <label htmlFor="course-description" className="block text-xs font-medium text-text-secondary mb-1">Description</label>
                  <Textarea id="course-description" value={courseForm.description} onChange={(e) => setCourseForm((f) => ({ ...f, description: e.target.value }))} placeholder="Optional description" rows={2} />
                </div>
              </form>
            )}
            {courses.length === 0 ? (
              <div className="p-5"><EmptyState title="No courses" description="No courses exist yet." /></div>
            ) : (
              <div className="table-scroll">
                <table className="table-base w-full text-sm">
                  <caption className="sr-only">Learning courses</caption>
                  <thead><tr><th scope="col">Code</th><th scope="col">Title</th><th scope="col">Category</th><th scope="col" className="num">Duration</th><th scope="col">Mandatory</th><th scope="col">Active</th></tr></thead>
                  <tbody>
                    {courses.map((c) => (
                      <tr key={c.id}>
                        <td className="font-mono text-xs">{c.code}</td>
                        <td>{c.title}</td>
                        <td>{c.category}</td>
                        <td className="num tabular-nums">{c.duration_hours}</td>
                        <td>{c.is_mandatory ? <span className="badge badge-amber">Mandatory</span> : <span className="badge badge-slate">Optional</span>}</td>
                        <td>{c.is_active ? <span className="badge badge-green">Active</span> : <span className="badge badge-slate">Inactive</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      {/* Enrollments */}
      <SectionCard compact title="Enrollments" description="Who is enrolled in what. Enrolling and completing is available to the workforce.">
        {loading ? (
          <LoadingRegion label="Loading enrollments…"><TableSkeleton rows={3} cols={6} /></LoadingRegion>
        ) : errors.enrollments ? (
          <div className="p-5"><RetryableAlert err={errors.enrollments} title="The enrollments could not be read" fallback="The enrollments could not be read" onRetry={load} /></div>
        ) : (
          <>
            {!canWorkforce && <div className="p-5"><Alert tone="info">Enrollments are visible to SuperAdmin, HR, Manager and Associate.</Alert></div>}
            {canWorkforce && (
              <form onSubmit={submitEnrollment} className="p-5 border-b border-border">
                {formErrors.enroll && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.enroll}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="enroll-employee" className="block text-xs font-medium text-text-secondary mb-1">Employee</label>
                    <Select id="enroll-employee" value={enrollForm.employee_id} onChange={(e) => setEnrollForm((f) => ({ ...f, employee_id: e.target.value }))} required>
                      <option value="">Select an employee…</option>
                      {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} · {emp.employee_id}</option>)}
                    </Select>
                  </div>
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="enroll-course" className="block text-xs font-medium text-text-secondary mb-1">Course</label>
                    <Select id="enroll-course" value={enrollForm.course_id} onChange={(e) => setEnrollForm((f) => ({ ...f, course_id: e.target.value }))} required>
                      <option value="">Select a course…</option>
                      {courses.map((c) => <option key={c.id} value={c.id}>{c.code} — {c.title}</option>)}
                    </Select>
                  </div>
                  <div className="min-w-[140px]">
                    <label htmlFor="enroll-status" className="block text-xs font-medium text-text-secondary mb-1">Status</label>
                    <Input id="enroll-status" value={enrollForm.status} onChange={(e) => setEnrollForm((f) => ({ ...f, status: e.target.value }))} placeholder="Enrolled" />
                  </div>
                  <div className="min-w-[120px]">
                    <label htmlFor="enroll-score" className="block text-xs font-medium text-text-secondary mb-1">Score</label>
                    <Input id="enroll-score" type="number" step="0.01" value={enrollForm.score} onChange={(e) => setEnrollForm((f) => ({ ...f, score: e.target.value }))} placeholder="Optional" />
                  </div>
                  <Button type="submit" loading={busy === "enroll"}>Enroll</Button>
                </div>
              </form>
            )}
            {canWorkforce && enrollments.length === 0 ? (
              <div className="p-5"><EmptyState title="No enrollments" description="No course enrollments recorded yet." /></div>
            ) : canWorkforce && enrollments.length > 0 ? (
              <div className="table-scroll">
                <table className="table-base w-full text-sm">
                  <caption className="sr-only">Course enrollments</caption>
                  <thead><tr><th scope="col">Employee</th><th scope="col">Course</th><th scope="col">Status</th><th scope="col">Score</th><th scope="col">Started</th><th scope="col">Completed</th>{canWorkforce && <th scope="col">Actions</th>}</tr></thead>
                  <tbody>
                    {enrollments.map((en) => (
                      <tr key={en.id}>
                        <td>{employeeName(en.employee_id)}</td>
                        <td>{courseTitle(en.course_id)}</td>
                        <td><StatusPill status={en.status} /></td>
                        <td>{en.score ?? "—"}</td>
                        <td>{fmtDateTime(en.started_at)}</td>
                        <td>{fmtDateTime(en.completed_at)}</td>
                        {canWorkforce && (
                          <td>
                            <div className="flex items-center gap-2">
                              <Input aria-label={`Score for enrollment ${en.id}`} type="number" step="0.01" placeholder="Score" className="w-20" value={completeScores[en.id] ?? ""} onChange={(e) => setCompleteScores((s) => ({ ...s, [en.id]: e.target.value }))} />
                              <Button size="xs" variant="secondary" loading={busy === `complete-${en.id}`} disabled={en.status === "Completed"} onClick={() => completeEnrollment(en.id)}>Complete</Button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </>
        )}
      </SectionCard>

      {/* Certifications */}
      <SectionCard compact title="Certifications" description="Credentials held. Creating and reading is available to the workforce.">
        {loading ? (
          <LoadingRegion label="Loading certifications…"><TableSkeleton rows={3} cols={5} /></LoadingRegion>
        ) : errors.certifications ? (
          <div className="p-5"><RetryableAlert err={errors.certifications} title="The certifications could not be read" fallback="The certifications could not be read" onRetry={load} /></div>
        ) : (
          <>
            {!canWorkforce && <div className="p-5"><Alert tone="info">Certifications are visible to SuperAdmin, HR, Manager and Associate.</Alert></div>}
            {canWorkforce && (
              <form onSubmit={submitCert} className="p-5 border-b border-border">
                {formErrors.cert && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.cert}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="cert-employee" className="block text-xs font-medium text-text-secondary mb-1">Employee</label>
                    <Select id="cert-employee" value={certForm.employee_id} onChange={(e) => setCertForm((f) => ({ ...f, employee_id: e.target.value }))} required>
                      <option value="">Select an employee…</option>
                      {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} · {emp.employee_id}</option>)}
                    </Select>
                  </div>
                  <div className="flex-1 min-w-[180px]">
                    <label htmlFor="cert-name" className="block text-xs font-medium text-text-secondary mb-1">Name</label>
                    <Input id="cert-name" value={certForm.name} onChange={(e) => setCertForm((f) => ({ ...f, name: e.target.value }))} placeholder="Certification name" required />
                  </div>
                  <div className="min-w-[160px]">
                    <label htmlFor="cert-issuer" className="block text-xs font-medium text-text-secondary mb-1">Issuer</label>
                    <Input id="cert-issuer" value={certForm.issuer} onChange={(e) => setCertForm((f) => ({ ...f, issuer: e.target.value }))} placeholder="Issuer" />
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="cert-issued" className="block text-xs font-medium text-text-secondary mb-1">Issued date</label>
                    <Input id="cert-issued" type="date" value={certForm.issued_date} onChange={(e) => setCertForm((f) => ({ ...f, issued_date: e.target.value }))} required />
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="cert-expiry" className="block text-xs font-medium text-text-secondary mb-1">Expiry date</label>
                    <Input id="cert-expiry" type="date" value={certForm.expiry_date} onChange={(e) => setCertForm((f) => ({ ...f, expiry_date: e.target.value }))} />
                  </div>
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="cert-url" className="block text-xs font-medium text-text-secondary mb-1">Certificate URL</label>
                    <Input id="cert-url" value={certForm.certificate_url} onChange={(e) => setCertForm((f) => ({ ...f, certificate_url: e.target.value }))} placeholder="https://…" />
                  </div>
                  <Button type="submit" loading={busy === "cert"}>Add certification</Button>
                </div>
              </form>
            )}
            {canWorkforce && certifications.length === 0 ? (
              <div className="p-5"><EmptyState title="No certifications" description="No certifications recorded yet." /></div>
            ) : canWorkforce && certifications.length > 0 ? (
              <div className="table-scroll">
                <table className="table-base w-full text-sm">
                  <caption className="sr-only">Certifications</caption>
                  <thead><tr><th scope="col">Employee</th><th scope="col">Name</th><th scope="col">Issuer</th><th scope="col">Issued</th><th scope="col">Expiry</th></tr></thead>
                  <tbody>
                    {certifications.map((c) => (
                      <tr key={c.id}>
                        <td>{employeeName(c.employee_id)}</td>
                        <td>{c.name}</td>
                        <td>{c.issuer ?? "—"}</td>
                        <td>{fmtDate(c.issued_date)}</td>
                        <td>{fmtDate(c.expiry_date)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </>
        )}
      </SectionCard>

      {/* Talent pools */}
      <SectionCard compact title="Talent pools" description="Pools of high-potential talent. Reading is limited to SuperAdmin, HR and Manager; creating and adding members is limited to SuperAdmin and HR.">
        {loading ? (
          <LoadingRegion label="Loading talent pools…"><TableSkeleton rows={3} cols={2} /></LoadingRegion>
        ) : errors.pools ? (
          <div className="p-5"><RetryableAlert err={errors.pools} title="The talent pools could not be read" fallback="The talent pools could not be read" onRetry={load} /></div>
        ) : (
          <>
            {!canManager && <div className="p-5"><Alert tone="info">Talent pools are visible to SuperAdmin, HR and Manager.</Alert></div>}
            {canManager && canAdmin && (
              <form onSubmit={submitPool} className="p-5 border-b border-border">
                {formErrors.pool && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.pool}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[200px]">
                    <label htmlFor="pool-name" className="block text-xs font-medium text-text-secondary mb-1">Pool name</label>
                    <Input id="pool-name" value={poolForm.name} onChange={(e) => setPoolForm((f) => ({ ...f, name: e.target.value }))} placeholder="e.g. Future Leaders" required />
                  </div>
                  <div className="flex-1 min-w-[260px]">
                    <label htmlFor="pool-desc" className="block text-xs font-medium text-text-secondary mb-1">Description</label>
                    <Input id="pool-desc" value={poolForm.description} onChange={(e) => setPoolForm((f) => ({ ...f, description: e.target.value }))} placeholder="Optional description" />
                  </div>
                  <Button type="submit" loading={busy === "pool"}>Create pool</Button>
                </div>
              </form>
            )}
            {canAdmin && pools.length > 0 && (
              <form onSubmit={submitMember} className="p-5 border-b border-border">
                {formErrors.member && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.member}</p>}
                <p className="text-xs font-medium text-text-secondary mb-2">Add member to pool (SuperAdmin and HR only)</p>
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[200px]">
                    <label htmlFor="member-pool" className="block text-xs font-medium text-text-secondary mb-1">Pool</label>
                    <Select id="member-pool" value={memberForm.pool_id} onChange={(e) => setMemberForm((f) => ({ ...f, pool_id: e.target.value }))} required>
                      <option value="">Select a pool…</option>
                      {pools.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </Select>
                  </div>
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="member-employee" className="block text-xs font-medium text-text-secondary mb-1">Employee</label>
                    <Select id="member-employee" value={memberForm.employee_id} onChange={(e) => setMemberForm((f) => ({ ...f, employee_id: e.target.value }))} required>
                      <option value="">Select an employee…</option>
                      {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} · {emp.employee_id}</option>)}
                    </Select>
                  </div>
                  <div className="min-w-[180px]">
                    <label htmlFor="member-readiness" className="block text-xs font-medium text-text-secondary mb-1">Readiness</label>
                    <Select id="member-readiness" value={memberForm.readiness} onChange={(e) => setMemberForm((f) => ({ ...f, readiness: e.target.value }))}>
                      {READINESS_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                    </Select>
                  </div>
                  <div className="flex-1 min-w-[200px]">
                    <label htmlFor="member-notes" className="block text-xs font-medium text-text-secondary mb-1">Notes</label>
                    <Input id="member-notes" value={memberForm.notes} onChange={(e) => setMemberForm((f) => ({ ...f, notes: e.target.value }))} placeholder="Optional" />
                  </div>
                  <Button type="submit" loading={busy === "member"}>Add member</Button>
                </div>
              </form>
            )}
            {canManager && pools.length === 0 ? (
              <div className="p-5"><EmptyState title="No talent pools" description="No talent pools exist yet." /></div>
            ) : canManager && pools.length > 0 ? (
              <div className="table-scroll">
                <table className="table-base w-full text-sm">
                  <caption className="sr-only">Talent pools</caption>
                  <thead><tr><th scope="col">Name</th><th scope="col">Description</th></tr></thead>
                  <tbody>
                    {pools.map((p) => (
                      <tr key={p.id}>
                        <td>{p.name}</td>
                        <td>{p.description ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </>
        )}
      </SectionCard>

      {/* Succession plans */}
      <SectionCard compact title="Succession plans" description="Ready-now successors per position. Reading is limited to SuperAdmin, HR and Manager; creating is limited to SuperAdmin and HR.">
        {loading ? (
          <LoadingRegion label="Loading succession plans…"><TableSkeleton rows={3} cols={5} /></LoadingRegion>
        ) : errors.succession ? (
          <div className="p-5"><RetryableAlert err={errors.succession} title="The succession plans could not be read" fallback="The succession plans could not be read" onRetry={load} /></div>
        ) : (
          <>
            {!canManager && <div className="p-5"><Alert tone="info">Succession plans are visible to SuperAdmin, HR and Manager.</Alert></div>}
            {canManager && canAdmin && (
              <form onSubmit={submitSuccession} className="p-5 border-b border-border">
                {formErrors.succession && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.succession}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="succ-position" className="block text-xs font-medium text-text-secondary mb-1">Position</label>
                    {positions.length > 0 ? (
                      <Select id="succ-position" value={successionForm.position_id} onChange={(e) => setSuccessionForm((f) => ({ ...f, position_id: e.target.value }))} required>
                        <option value="">Select a position…</option>
                        {positions.map((pos) => <option key={pos.id} value={pos.id}>{pos.code} — {pos.title}</option>)}
                      </Select>
                    ) : (
                      <Input id="succ-position" type="number" value={successionForm.position_id} onChange={(e) => setSuccessionForm((f) => ({ ...f, position_id: e.target.value }))} placeholder="Position ID" required />
                    )}
                  </div>
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="succ-primary" className="block text-xs font-medium text-text-secondary mb-1">Primary successor</label>
                    <Select id="succ-primary" value={successionForm.primary_successor_id} onChange={(e) => setSuccessionForm((f) => ({ ...f, primary_successor_id: e.target.value }))}>
                      <option value="">None</option>
                      {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} · {emp.employee_id}</option>)}
                    </Select>
                  </div>
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="succ-backup" className="block text-xs font-medium text-text-secondary mb-1">Backup successor</label>
                    <Select id="succ-backup" value={successionForm.backup_successor_id} onChange={(e) => setSuccessionForm((f) => ({ ...f, backup_successor_id: e.target.value }))}>
                      <option value="">None</option>
                      {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} · {emp.employee_id}</option>)}
                    </Select>
                  </div>
                  <div className="min-w-[180px]">
                    <label htmlFor="succ-readiness" className="block text-xs font-medium text-text-secondary mb-1">Readiness</label>
                    <Select id="succ-readiness" value={successionForm.readiness} onChange={(e) => setSuccessionForm((f) => ({ ...f, readiness: e.target.value }))}>
                      {READINESS_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                    </Select>
                  </div>
                  <div className="flex-1 min-w-[200px]">
                    <label htmlFor="succ-notes" className="block text-xs font-medium text-text-secondary mb-1">Notes</label>
                    <Input id="succ-notes" value={successionForm.notes} onChange={(e) => setSuccessionForm((f) => ({ ...f, notes: e.target.value }))} placeholder="Optional" />
                  </div>
                  <Button type="submit" loading={busy === "succession"}>Create plan</Button>
                </div>
              </form>
            )}
            {canManager && succession.length === 0 ? (
              <div className="p-5"><EmptyState title="No succession plans" description="No succession plans exist yet." /></div>
            ) : canManager && succession.length > 0 ? (
              <div className="table-scroll">
                <table className="table-base w-full text-sm">
                  <caption className="sr-only">Succession plans</caption>
                  <thead><tr><th scope="col">Position</th><th scope="col">Primary</th><th scope="col">Backup</th><th scope="col">Readiness</th><th scope="col">Notes</th></tr></thead>
                  <tbody>
                    {succession.map((s) => (
                      <tr key={s.id}>
                        <td>{positionLabel(s.position_id)}</td>
                        <td>{s.primary_successor_id ? employeeName(s.primary_successor_id) : "—"}</td>
                        <td>{s.backup_successor_id ? employeeName(s.backup_successor_id) : "—"}</td>
                        <td>{s.readiness}</td>
                        <td>{s.notes ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </>
        )}
      </SectionCard>
    </Layout>
  )
}
