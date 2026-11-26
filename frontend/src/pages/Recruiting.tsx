import { useEffect, useState, cloneElement, isValidElement, useId, type FormEvent, type ReactNode } from "react"
import { Layout } from "@/components/Layout"
import {
  Button,
  Table,
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  StatCard,
  StatusPill, RetryableAlert} from "@/components/ui"
import { IconFile, IconPlus, IconTarget, IconUsers } from "@/components/icons"
import api, { fileUrl } from "@/lib/api"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { formatCurrency } from "@/lib/format"
import type {
  Application,
  Candidate,
  Department,
  Job,
  Offer,
  Requisition,
} from "@/types"

const TABS = [
  { key: "requisitions", label: "Requisitions" },
  { key: "candidates", label: "Candidates" },
  { key: "applications", label: "Applications" },
  { key: "offers", label: "Offers" },
] as const
type Tab = (typeof TABS)[number]["key"]

/** Labelled field used across every create form on this page. */
function Field({
  id,
  label,
  children,
  hint,
  required,
  error,
  className = "",
}: {
  id: string
  label: string
  children: ReactNode
  hint?: string
  required?: boolean
  error?: string | boolean
  className?: string
}) {
  const errorId = useId()
  const hasError = !!error
  const errorText = typeof error === "string" ? error : undefined
  return (
    <div className={`field min-w-[150px] ${className}`}>
      <label htmlFor={id} className="field-label">
        {label}
        {required && <span className="text-error ml-0.5"> (required)</span>}
      </label>
      {isValidElement(children)
        ? cloneElement(children, {
            ...(hasError ? { "aria-describedby": errorId, "aria-invalid": true } : {}),
            ...(required ? { "aria-required": true } : {}),
          })
        : children}
      {hasError ? (
        <p id={errorId} className="field-hint text-error error-box" role="alert">
          {errorText ?? "Invalid field."}
        </p>
      ) : hint ? (
        <p className="field-hint">{hint}</p>
      ) : null}
    </div>
  )
}

export default function Recruiting() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  // Every recruiting endpoint (requisitions, candidates, applications and
  // offers — list and write alike) is `require_roles(*ADMIN_ROLES)` in
  // backend/app/api/v1/endpoints/{requisitions,candidates,applications,offers}.py,
  // so below SuperAdmin/HR the screen is a role card, not a wall of 403s.
  const isAdmin = user?.role === "SuperAdmin" || user?.role === "HR"
  const [tab, setTab] = useState<Tab>("requisitions")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState("")
  const [hireOfferId, setHireOfferId] = useState<number | null>(null)
  const [hireEmployeeId, setHireEmployeeId] = useState("")

  const [departments, setDepartments] = useState<Department[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [requisitions, setRequisitions] = useState<Requisition[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [offers, setOffers] = useState<Offer[]>([])

  // Create-form state. Kept here rather than lifted so each tab's form can be
  // read on its own.
  const [reqForm, setReqForm] = useState({
    req_number: "", title: "", department_id: "", job_id: "",
    location: "", openings: 1, status: "Open",
  })
  const [candForm, setCandForm] = useState({
    first_name: "", last_name: "", email: "", phone: "", source: "Referral",
  })
  const [appForm, setAppForm] = useState({
    requisition_id: "", candidate_id: "",
    applied_date: new Date().toISOString().slice(0, 10), status: "Applied",
  })
  const [offerForm, setOfferForm] = useState({
    offer_number: "", application_id: "", job_id: "", salary_offered: "",
    start_date: new Date().toISOString().slice(0, 10),
    offer_date: new Date().toISOString().slice(0, 10),
  })

  type LoadKey =
    | "departments"
    | "jobs"
    | "requisitions"
    | "candidates"
    | "applications"
    | "offers"
  const LOAD_LABELS: Record<LoadKey, string> = {
    departments: "departments",
    jobs: "job definitions",
    requisitions: "requisitions",
    candidates: "candidates",
    applications: "applications",
    offers: "offers",
  }

  const [failed, setFailed] = useState<LoadKey[]>([])

  const load = async () => {
    setLoading(true)
    // One 403 or one failed GET must not blank every tab — each recruiting
    // dataset settles on its own and records what did not load.
    const keys: LoadKey[] = [
      "departments",
      "jobs",
      "requisitions",
      "candidates",
      "applications",
      "offers",
    ]
    const results = await Promise.allSettled([
      api.get("/departments/"),
      api.get("/jobs/"),
      api.get("/requisitions/"),
      api.get("/candidates/"),
      api.get("/applications/"),
      api.get("/offers/"),
    ])
    const failedKeys: LoadKey[] = []
    results.forEach((r, i) => {
      const key = keys[i]
      if (r.status === "fulfilled") {
        const data = r.value.data
        if (key === "departments") setDepartments(data)
        else if (key === "jobs") setJobs(data)
        else if (key === "requisitions") setRequisitions(data)
        else if (key === "candidates") setCandidates(data)
        else if (key === "applications") setApplications(data)
        else if (key === "offers") setOffers(data)
      } else {
        failedKeys.push(key)
      }
    })
    setFailed(failedKeys)
    setError(
      failedKeys.length > 0
        ? `Some recruiting data could not be loaded: ${failedKeys
            .map((k) => LOAD_LABELS[k])
            .join(", ")}. Check your connection or use Reload to retry.`
        : "",
    )
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  const run = async (key: string, fn: () => Promise<unknown>, msg: string) => {
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

  const deptName = (id?: number) => departments.find((d) => d.id === id)?.name ?? "—"
  const candName = (id: number) => {
    const c = candidates.find((x) => x.id === id)
    return c ? `${c.first_name} ${c.last_name}` : `#${id}`
  }
  const reqLabel = (id: number) =>
    requisitions.find((r) => r.id === id)?.req_number ?? `#${id}`

  /**
   * Empty state that separates "no rows yet" from "this collection failed to
   * load" — a failed GET must read as a data problem, not as emptiness.
   */
  const emptyDesc = (key: LoadKey, noneDesc: string) =>
    failed.includes(key)
      ? `The ${LOAD_LABELS[key]} list could not be loaded — it may be temporarily unavailable or not visible for your role. Use Reload to retry.`
      : noneDesc

  const openReqs = requisitions.filter((r) => r.status === "Open").length
  const hired = applications.filter((a) => a.status === "Hired").length

  if (!isAdmin) {
    return (
      <Layout>
        <PageHeader compact
          icon={<IconTarget />}
          title="Recruiting"
          description="Requisitions → candidates → applications → offers → hire."
        />
        <Alert
          tone="error"
          title="Not visible for your role"
        >
          The recruiting pipeline (requisitions, candidates, applications and offers) is
          admin-only territory in the backend: every endpoint requires SuperAdmin or HR,
          and your role is {user?.role || "unknown"}. Ask an administrator for access, or
          view team hiring status through a manager.
        </Alert>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader compact
        icon={<IconTarget />}
        title="Recruiting"
        description="Requisitions → candidates → applications → offers → hire."
      />

      {error && (
        <Alert
          tone="error"
          title="Recruiting data incomplete"
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
        <LoadingRegion label="Loading recruiting data">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="skeleton h-24" />
            ))}
          </div>
        </LoadingRegion>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
          <StatCard tone="brand" label="Open requisitions" value={openReqs} hint={`${requisitions.length} total`} />
          <StatCard tone="violet" label="Candidates" value={candidates.length} />
          <StatCard tone="teal" label="Applications" value={applications.length} />
          <StatCard tone="green" label="Hired" value={hired} hint={`${offers.length} offers issued`} />
        </div>
      )}

      <div className="tablist" role="tablist" aria-label="Recruiting pipeline stages">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            id={`tab-${t.key}`}
            aria-selected={tab === t.key}
            aria-controls={`panel-${t.key}`}
            onClick={() => setTab(t.key)}
            className={`tab ${tab === t.key ? "tab-active" : "tab-idle"}`}
          >
            {t.label}
            <span className="ml-2 text-xs text-text-secondary">
              {t.key === "requisitions" && requisitions.length}
              {t.key === "candidates" && candidates.length}
              {t.key === "applications" && applications.length}
              {t.key === "offers" && offers.length}
            </span>
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {/* ---------------- Requisitions ---------------- */}
        {tab === "requisitions" && (
          <section className="card mb-5">
            <div className="toolbar">
              <Field id="rq-num" label="Req number" required>
                <input
                  id="rq-num"
                  className="input"
                  placeholder="REQ-002"
                  value={reqForm.req_number}
                  onChange={(e) => setReqForm({ ...reqForm, req_number: e.target.value })}
                />
              </Field>
              <Field id="rq-title" label="Title" className="grow min-w-[200px]" required>
                <input
                  id="rq-title"
                  className="input"
                  value={reqForm.title}
                  onChange={(e) => setReqForm({ ...reqForm, title: e.target.value })}
                />
              </Field>
              <Field id="rq-dept" label="Department" required>
                <select
                  id="rq-dept"
                  className="input"
                  value={reqForm.department_id}
                  onChange={(e) => setReqForm({ ...reqForm, department_id: e.target.value })}
                >
                  <option value="">Select…</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </Field>
              <Field id="rq-job" label="Job (optional)">
                <select
                  id="rq-job"
                  className="input"
                  value={reqForm.job_id}
                  onChange={(e) => setReqForm({ ...reqForm, job_id: e.target.value })}
                >
                  <option value="">None</option>
                  {jobs.map((j) => (
                    <option key={j.id} value={j.id}>{j.title}</option>
                  ))}
                </select>
              </Field>
              <Field id="rq-openings" label="Openings" className="w-24" required>
                <input
                  id="rq-openings"
                  type="number"
                  min={1}
                  className="input"
                  value={reqForm.openings}
                  onChange={(e) => setReqForm({ ...reqForm, openings: Number(e.target.value) })}
                />
              </Field>
              <Field id="rq-status" label="Status" className="w-32" required>
                <select
                  id="rq-status"
                  className="input"
                  value={reqForm.status}
                  onChange={(e) => setReqForm({ ...reqForm, status: e.target.value })}
                >
                  {["Draft", "Open", "OnHold", "Closed"].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </Field>
              <Button variant="primary" disabled={!reqForm.req_number || !reqForm.title || !reqForm.department_id || busy === "rq"}
                onClick={() =>
                  run("rq", () => api.post("/requisitions/", {
                    ...reqForm,
                    department_id: Number(reqForm.department_id),
                    job_id: reqForm.job_id ? Number(reqForm.job_id) : null,
                    openings: Number(reqForm.openings),
                  }), "Requisition created")
                }>
                <IconPlus className="w-4 h-4" />
                {busy === "rq" ? "Creating…" : "Create"}
              </Button>
            </div>
          </section>
        )}

        {tab === "requisitions" && (
          <SectionCard compact icon={<IconTarget />} title="Requisitions"
            description="Open and closed roles across the organisation.">
            {requisitions.length === 0 ? (
              <EmptyState title="No requisitions yet"
                description={emptyDesc("requisitions", "Create a requisition above to open a role.")} />
            ) : (
              <Table
                columns={[
                  { key: "req", header: "Req #", accessor: (r) => <span className="font-mono text-xs">{r.req_number}</span> },
                  { key: "title", header: "Title", accessor: (r) => <span className="font-medium">{r.title}</span> },
                  { key: "dept", header: "Department", accessor: (r) => <span className="text-text-secondary">{deptName(r.department_id)}</span> },
                  { key: "loc", header: "Location", accessor: (r) => <span className="text-text-secondary">{r.location || "—"}</span> },
                  { key: "openings", header: "Openings", accessor: (r) => r.openings, cellClassName: "num" },
                  { key: "status", header: "Status", accessor: (r) => <StatusPill status={r.status} /> },
                ]}
                data={requisitions}
                keyAccessor={(r) => r.id}
                caption="All job requisitions"
                sortable={false}
              />
            )}
          </SectionCard>
        )}

        {/* ---------------- Candidates ---------------- */}
        {tab === "candidates" && (
          <section className="card mb-5">
            <div className="toolbar">
              <Field id="cd-first" label="First name" required>
                <input id="cd-first" className="input" value={candForm.first_name}
                  onChange={(e) => setCandForm({ ...candForm, first_name: e.target.value })} />
              </Field>
              <Field id="cd-last" label="Last name" required>
                <input id="cd-last" className="input" value={candForm.last_name}
                  onChange={(e) => setCandForm({ ...candForm, last_name: e.target.value })} />
              </Field>
              <Field id="cd-email" label="Email" required>
                <input id="cd-email" type="email" className="input" value={candForm.email}
                  onChange={(e) => setCandForm({ ...candForm, email: e.target.value })} />
              </Field>
              <Field id="cd-source" label="Source" className="w-36">
                <select id="cd-source" className="input" value={candForm.source}
                  onChange={(e) => setCandForm({ ...candForm, source: e.target.value })}>
                  {["Referral", "LinkedIn", "Portal", "Agency", "Other"].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </Field>
              <Button variant="primary" disabled={!candForm.first_name || !candForm.last_name || !candForm.email || busy === "cd"}
                onClick={() => run("cd", () => api.post("/candidates/", candForm), "Candidate added")}>
                <IconPlus className="w-4 h-4" />
                {busy === "cd" ? "Adding…" : "Add candidate"}
              </Button>
            </div>
          </section>
        )}

        {tab === "candidates" && (
          <SectionCard compact icon={<IconUsers />} title="Candidates"
            description="Everyone in the talent pool and their current stage.">
            {candidates.length === 0 ? (
              <EmptyState title="No candidates yet"
                description={emptyDesc("candidates", "Add a candidate above to start building your pipeline.")} />
            ) : (
              <Table
                columns={[
                  { key: "name", header: "Name", accessor: (c) => <span className="font-medium">{c.first_name} {c.last_name}</span> },
                  { key: "email", header: "Email", accessor: (c) => <span className="text-text-secondary">{c.email}</span> },
                  { key: "source", header: "Source", accessor: (c) => c.source || "—" },
                  { key: "status", header: "Status", accessor: (c) => <StatusPill status={c.status} /> },
                ]}
                data={candidates}
                keyAccessor={(c) => c.id}
                caption="All candidates in the talent pool"
                sortable={false}
              />
            )}
          </SectionCard>
        )}

        {/* ---------------- Applications ---------------- */}
        {tab === "applications" && (
          <section className="card mb-5">
            <div className="toolbar">
              <Field id="ap-req" label="Requisition" className="grow min-w-[200px]" required>
                <select id="ap-req" className="input" value={appForm.requisition_id}
                  onChange={(e) => setAppForm({ ...appForm, requisition_id: e.target.value })}>
                  <option value="">Select requisition…</option>
                  {requisitions.map((r) => (
                    <option key={r.id} value={r.id}>{r.req_number} — {r.title}</option>
                  ))}
                </select>
              </Field>
              <Field id="ap-cand" label="Candidate" className="grow min-w-[180px]" required>
                <select id="ap-cand" className="input" value={appForm.candidate_id}
                  onChange={(e) => setAppForm({ ...appForm, candidate_id: e.target.value })}>
                  <option value="">Select candidate…</option>
                  {candidates.map((c) => (
                    <option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>
                  ))}
                </select>
              </Field>
              <Field id="ap-date" label="Applied date">
                <input id="ap-date" type="date" className="input" value={appForm.applied_date}
                  onChange={(e) => setAppForm({ ...appForm, applied_date: e.target.value })} />
              </Field>
              <Field id="ap-status" label="Stage" className="w-36">
                <select id="ap-status" className="input" value={appForm.status}
                  onChange={(e) => setAppForm({ ...appForm, status: e.target.value })}>
                  {["Applied", "Screening", "Interview", "Offer", "Hired", "Rejected"].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </Field>
              <Button variant="primary" disabled={!appForm.requisition_id || !appForm.candidate_id || busy === "ap"}
                onClick={() =>
                  run("ap", () => api.post("/applications/", {
                    ...appForm,
                    requisition_id: Number(appForm.requisition_id),
                    candidate_id: Number(appForm.candidate_id),
                  }), "Application created")
                }>
                <IconPlus className="w-4 h-4" />
                {busy === "ap" ? "Creating…" : "Create application"}
              </Button>
            </div>
          </section>
        )}

        {tab === "applications" && (
          <SectionCard compact icon={<IconTarget />} title="Applications"
            description="Candidate-to-requisition pipeline with stage tracking.">
            {applications.length === 0 ? (
              <EmptyState title="No applications yet"
                description={emptyDesc("applications", "Link a candidate to a requisition above to begin tracking.")} />
            ) : (
              <Table
                columns={[
                  { key: "req", header: "Requisition", accessor: (a) => <span className="font-mono text-xs">{reqLabel(a.requisition_id)}</span> },
                  { key: "cand", header: "Candidate", accessor: (a) => <span className="font-medium">{candName(a.candidate_id)}</span> },
                  { key: "applied", header: "Applied", accessor: (a) => <span className="whitespace-nowrap text-text-secondary">{a.applied_date}</span> },
                  { key: "stage", header: "Stage", accessor: (a) => <StatusPill status={a.status} /> },
                ]}
                data={applications}
                keyAccessor={(a) => a.id}
                caption="All applications"
                sortable={false}
              />
            )}
          </SectionCard>
        )}

        {/* ---------------- Offers ---------------- */}
        {tab === "offers" && (
          <section className="card mb-5">
            <div className="toolbar">
              <Field id="of-num" label="Offer number" required>
                <input id="of-num" className="input" placeholder="OFF-002" value={offerForm.offer_number}
                  onChange={(e) => setOfferForm({ ...offerForm, offer_number: e.target.value })} />
              </Field>
              <Field id="of-app" label="Application" className="grow min-w-[220px]" required>
                <select id="of-app" className="input" value={offerForm.application_id}
                  onChange={(e) => setOfferForm({ ...offerForm, application_id: e.target.value })}>
                  <option value="">Select application…</option>
                  {applications.map((a) => (
                    <option key={a.id} value={a.id}>
                      #{a.id} — {candName(a.candidate_id)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field id="of-salary" label="Salary" className="w-36">
                <input id="of-salary" type="number" className="input" value={offerForm.salary_offered}
                  onChange={(e) => setOfferForm({ ...offerForm, salary_offered: e.target.value })} />
              </Field>
              <Field id="of-start" label="Start date">
                <input id="of-start" type="date" className="input" value={offerForm.start_date}
                  onChange={(e) => setOfferForm({ ...offerForm, start_date: e.target.value })} />
              </Field>
              <Button variant="primary" disabled={!offerForm.offer_number || !offerForm.application_id || busy === "of"}
                onClick={() =>
                  run("of", () => api.post("/offers/", {
                    offer_number: offerForm.offer_number,
                    application_id: Number(offerForm.application_id),
                    job_id: offerForm.job_id ? Number(offerForm.job_id) : null,
                    salary_offered: offerForm.salary_offered ? Number(offerForm.salary_offered) : null,
                    start_date: offerForm.start_date,
                    offer_date: offerForm.offer_date,
                    status: "Draft",
                  }), "Offer created")
                }>
                <IconPlus className="w-4 h-4" />
                {busy === "of" ? "Creating…" : "Create offer"}
              </Button>
            </div>
          </section>
        )}

        {tab === "offers" && (
          <SectionCard compact icon={<IconFile />} title="Offers"
            description="Generate letters, record acceptance and convert to an employee record.">
            {offers.length === 0 ? (
              <EmptyState title="No offers yet"
                description={emptyDesc("offers", "Create an offer from an accepted application above.")} />
            ) : (
              <Table
                columns={[
                  { key: "offer", header: "Offer #", accessor: (o) => <span className="font-mono text-xs">{o.offer_number}</span> },
                  { key: "app", header: "Application", accessor: (o) => (
                    <span>
                      <span className="font-medium">#{o.application_id}</span>
                      <span className="block text-xs text-text-secondary">
                        {candName(applications.find((a) => a.id === o.application_id)?.candidate_id ?? 0)}
                      </span>
                    </span>
                  ) },
                  { key: "salary", header: "Salary", accessor: (o) => formatCurrency(o.salary_offered, {
                    locale: tenant?.locale,
                    currency: tenant?.currency,
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  }), cellClassName: "num" },
                  { key: "status", header: "Status", accessor: (o) => <StatusPill status={o.status} /> },
                  { key: "actions", header: "Actions", accessor: (o) => (
                    <div className="flex items-center gap-3 flex-wrap">
                      <Button variant="ghost" disabled={busy === `l${o.id}`}
                        onClick={() => run(`l${o.id}`, () => api.post(`/offers/${o.id}/letter`), "Offer letter generated")}>
                        Letter
                      </Button>
                      <Button variant="ghost" disabled={busy === `a${o.id}`}
                        onClick={() => run(`a${o.id}`, () => api.post(`/offers/${o.id}/accept`), "Offer accepted")}>
                        Accept
                      </Button>
                      <Button variant="ghost" disabled={busy === `h${o.id}`}
                        onClick={() => setHireOfferId(o.id)}>
                        Hire
                      </Button>
                      {o.letter_url && (
                        <a className="action-link text-text-secondary" href={fileUrl(o.letter_url)}
                          target="_blank" rel="noreferrer">
                          PDF
                        </a>
                      )}
                    </div>
                  ) },
                ]}
                data={offers}
                keyAccessor={(o) => o.id}
                caption="All offers"
                sortable={false}
              />
            )}
          </SectionCard>
        )}
      </div>

      {/* Hire dialog — replaces window.prompt */}
      {hireOfferId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Hire candidate">
          <div className="absolute inset-0 bg-[rgba(2,6,23,0.5)]" onClick={() => { setHireOfferId(null); setHireEmployeeId("") }} aria-hidden="true" />
          <div className="relative card p-6 w-full max-w-md">
            <h2 className="font-semibold text-fg mb-1">Hire candidate</h2>
            <p className="text-sm text-text-secondary mb-4">Enter the employee ID for the new hire (e.g. EMP-1005).</p>
            <div className="field mb-4">
              <label htmlFor="hire-employee-id" className="field-label">Employee ID</label>
              <input id="hire-employee-id" className="input" value={hireEmployeeId} onChange={(e) => setHireEmployeeId(e.target.value)} placeholder="EMP-1005" autoFocus />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" type="button" onClick={() => { setHireOfferId(null); setHireEmployeeId("") }}>Cancel</Button>
              <Button variant="primary" type="button" disabled={!hireEmployeeId.trim() || busy === `h${hireOfferId}`}
                onClick={() => {
                  const eid = hireEmployeeId.trim()
                  if (!eid) return
                  const oid = hireOfferId
                  setHireOfferId(null); setHireEmployeeId("")
                  run(`h${oid}`, () => api.post(`/offers/${oid}/hire`, { employee_id: eid }), "Hired — onboarding checklist created")
                }}>
                Hire
              </Button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  )
}