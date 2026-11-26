import { useEffect, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { Layout } from "@/components/Layout"

import { StatusPill } from "@/components/ui/status-pill"
import { PageHeader } from "@/components/ui/layout"
import { Alert, EmptyState } from "@/components/ui/feedback"
import { Button, RetryableAlert } from "@/components/ui"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import api, { errorMessage } from "@/lib/api"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { formatNumber } from "@/lib/format"
import { useTenantNav } from "@/lib/tenantPath"
import type { PayRunReconciliation } from "@/types"
import { CreateForm } from "@/components/platform/CreateForm"
import { DataList } from "@/components/platform/DataList"
import { PayslipPanel } from "@/components/platform/PayslipPanel"
import { ReconciliationPanel } from "@/components/platform/ReconciliationPanel"
import { IconWallet, IconTrend, IconHeart, IconBook, IconShield } from "@/components/icons"

interface Row { id: number; [k: string]: any }

const TABS = [
  { key: "corehr", label: "Core HR" },
  { key: "payroll", label: "Payroll" },
  { key: "performance", label: "Performance" },
  { key: "benefits", label: "Benefits" },
  { key: "learning", label: "Learning" },
  { key: "integrations", label: "Platform" },
  { key: "compliance", label: "Compliance" },
  { key: "importexport", label: "Import / Export" },
]

const TAB_KEYS = TABS.map((t) => t.key)

function tabFromPath(pathname: string): string {
  const segment = pathname.split("/").filter(Boolean).pop() ?? ""
  return TAB_KEYS.includes(segment) ? segment : "corehr"
}

export default function Platform() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const { user } = useAuth()
  const { tenant } = useTenant()
  // Headcount/cost figures group in the tenant locale via format.ts —
  // never the browser default. Money pins 2dp (no Intl defaults); headcount
  // uses the raw value, never this helper.
  const money = (value?: number | string | null) =>
    formatNumber(value, { locale: tenant?.locale, minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const isAdmin = user?.role === "SuperAdmin" || user?.role === "HR"
  const tab = tabFromPath(pathname)
  const setTab = (next: string) => {
    navigate(next === "corehr" ? "/platform" : `/platform/${next}`)
  }
  const [error, setError] = useState<unknown | null>(null)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [loading, setLoading] = useState(true)
  const [unreadable, setUnreadable] = useState<string[]>([])

  const [locations, setLocations] = useState<Row[]>([])
  const [costCenters, setCostCenters] = useState<Row[]>([])
  const [positions, setPositions] = useState<Row[]>([])
  const [cases, setCases] = useState<Row[]>([])
  const [jobs, setJobs] = useState<Row[]>([])
  const [departments, setDepartments] = useState<Row[]>([])
  const [periods, setPeriods] = useState<Row[]>([])
  const [components, setComponents] = useState<Row[]>([])
  const [payRuns, setPayRuns] = useState<Row[]>([])
  const [goals, setGoals] = useState<Row[]>([])
  const [reviews, setReviews] = useState<Row[]>([])
  const [bands, setBands] = useState<Row[]>([])
  const [plans, setPlans] = useState<Row[]>([])
  const [enrollments, setEnrollments] = useState<Row[]>([])
  const [courses, setCourses] = useState<Row[]>([])
  const [certs, setCerts] = useState<Row[]>([])
  const [webhooks, setWebhooks] = useState<Row[]>([])
  const [checks, setChecks] = useState<Row[]>([])
  const [sigs, setSigs] = useState<Row[]>([])
  const [rules, setRules] = useState<Row[]>([])
  const [violations, setViolations] = useState<Row[]>([])
  const [plans2, setPlans2] = useState<Row[]>([])
  const [scenarios, setScenarios] = useState<Row[]>([])
  const [entities, setEntities] = useState<string[]>([])

  const loadAll = async () => {
    const failed: string[] = []
    const safe = async (p: string) => {
      try {
        return (await api.get(p)).data
      } catch {
        failed.push(p)
        return []
      }
    }
    const [
      l, cc, pos, cs, per, comp, runs, g, rev, b,
      bp, en, cr, cert, wh, bc, es, ruleset, viol, hp, sc, jb, dp,
    ] = await Promise.all([
      safe("/core-hr/locations"),
      safe("/core-hr/cost-centers"),
      safe("/core-hr/positions"),
      safe("/core-hr/cases"),
      safe("/payroll/periods"),
      safe("/payroll/components"),
      safe("/payroll/runs"),
      safe("/performance/goals"),
      safe("/performance/reviews"),
      safe("/performance/compensation-bands"),
      safe("/benefits/benefit-plans"),
      safe("/benefits/benefit-enrollments"),
      safe("/learning/courses"),
      safe("/learning/certifications"),
      safe("/platform/webhooks"),
      safe("/platform/background-checks"),
      safe("/platform/e-signatures"),
      safe("/compliance/compliance-rules"),
      safe("/compliance/compliance-violations"),
      safe("/compliance/headcount-plans"),
      safe("/compliance/scenarios"),
      safe("/jobs/"),
      safe("/departments/"),
    ])
    setLocations(l); setCostCenters(cc); setPositions(pos); setCases(cs)
    setJobs(jb); setDepartments(dp)
    setPeriods(per); setComponents(comp); setPayRuns(runs)
    setGoals(g); setReviews(rev); setBands(b)
    setPlans(bp); setEnrollments(en)
    setCourses(cr); setCerts(cert)
    setWebhooks(wh); setChecks(bc); setSigs(es)
    setRules(ruleset); setViolations(viol); setPlans2(hp); setScenarios(sc)
    try {
      setEntities((await api.get("/import-export/entities")).data.entities)
    } catch {
      failed.push("/import-export/entities")
      setEntities([])
    }
    setUnreadable(failed)
    setLoading(false)
  }

  useEffect(() => { loadAll() }, [])

  const act = async (fn: () => Promise<unknown>, msg: string) => {
    setActionError("")
    setNotice("")
    try { await fn(); setNotice(msg); await loadAll() } catch (e: any) { setActionError(e?.response?.data?.detail || "Action failed") }
  }

  if (loading) {
    return (
      <Layout>
        <PageHeader compact title="Platform Modules" description="Core HR, Payroll, Performance, Benefits, Learning, Integrations, Compliance, Import/Export" />
        <div aria-busy="true" aria-live="polite">
          <span className="sr-only">Loading platform modules…</span>
          <div className="flex flex-wrap gap-2 mb-4">
            {TABS.map((t) => <Skeleton key={t.key} className="h-9 w-28" />)}
          </div>
          <div className="mk-card p-4">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-4 w-full mb-3 last:mb-0" />)}
          </div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader compact
        title="Platform Modules"
        description="Core HR, Payroll, Performance, Benefits, Learning, Integrations, Compliance, Import/Export"
      />

      {!!error && <RetryableAlert err={error} title="The platform data could not be read" fallback="The platform data could not be read." onRetry={() => window.location.reload()} />}
      {notice && <Alert tone="success">{notice}</Alert>}
      {actionError && <Alert tone="error">{actionError}</Alert>}

      <Tabs defaultValue={tab} onValueChange={setTab} className="mb-4">
        <TabsList role="tablist" aria-label="Platform modules">
          {TABS.map((t) => (
            <TabsTrigger key={t.key} value={t.key}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {TABS.map((t) => (
          <TabsContent key={t.key} value={t.key}>
            {t.key === "corehr" && (
              <div className="space-y-4">
                <CreateForm
                  legend="Add location"
                  fields={[
                    { name: "name", label: "Name", required: true },
                    { name: "code", label: "Code", required: true },
                  ]}
                  submitLabel="Add location"
                  onSubmit={async (v) => {
                    await act(() => api.post("/core-hr/locations", { name: v.name, code: v.code }), "Location created")
                  }}
                />
                <DataList
                  title="Locations"
                  caption="All configured office and work locations"
                  columns={["Code", "Name"]}
                  rows={locations}
                  source="/core-hr/locations"
                  unreadable={unreadable}
                  render={(l) => [l.code, l.name]}
                />

                <CreateForm
                  legend="Add cost center"
                  fields={[
                    { name: "code", label: "Code", required: true },
                    { name: "name", label: "Name", required: true },
                  ]}
                  submitLabel="Add cost center"
                  onSubmit={async (v) => {
                    await act(() => api.post("/core-hr/cost-centers", { code: v.code, name: v.name }), "Cost center created")
                  }}
                />
                <DataList
                  title="Cost centers"
                  caption="Financial and reporting cost centers"
                  columns={["Code", "Name"]}
                  rows={costCenters}
                  source="/core-hr/cost-centers"
                  unreadable={unreadable}
                  render={(c) => [c.code, c.name]}
                />

                {isAdmin ? (
                  <CreateForm
                    legend="Add position"
                    fields={[
                      { name: "code", label: "Code", required: true },
                      { name: "title", label: "Title", required: true },
                      {
                        name: "job_id",
                        label: "Job title",
                        required: true,
                        options: jobs.map((j) => ({ value: String(j.id), label: `${j.code} — ${j.title}` })),
                      },
                      {
                        name: "department_id",
                        label: "Department",
                        required: true,
                        options: departments.map((d) => ({ value: String(d.id), label: d.name })),
                      },
                      { name: "fte", label: "FTE (e.g. 1.0)", placeholder: "1.0" },
                    ]}
                    submitLabel="Add position"
                    onSubmit={async (v) => {
                      await act(
                        () =>
                          api.post("/core-hr/positions", {
                            code: v.code,
                            title: v.title,
                            job_id: Number(v.job_id),
                            department_id: Number(v.department_id),
                            fte: v.fte ? Number(v.fte) : 1.0,
                          }),
                        "Position created",
                      )
                    }}
                  />
                ) : (
                  <Alert tone="info" className="mb-4">
                    Adding a position requires SuperAdmin or HR. You can read the list below.
                  </Alert>
                )}
                <DataList
                  title="Positions"
                  caption="All job positions"
                  columns={["Code", "Title"]}
                  rows={positions}
                  source="/core-hr/positions"
                  unreadable={unreadable}
                  render={(p) => [p.code, p.title]}
                />

                {isAdmin ? (
                  <CreateForm
                    legend="Add HR case"
                    fields={[
                      { name: "subject", label: "Subject", required: true },
                      {
                        name: "category",
                        label: "Category",
                        options: [
                          { value: "General", label: "General" },
                          { value: "Payroll", label: "Payroll" },
                          { value: "Benefits", label: "Benefits" },
                          { value: "Leave", label: "Leave" },
                          { value: "Performance", label: "Performance" },
                          { value: "Conduct", label: "Conduct" },
                        ],
                      },
                      {
                        name: "priority",
                        label: "Priority",
                        options: [
                          { value: "Low", label: "Low" },
                          { value: "Medium", label: "Medium" },
                          { value: "High", label: "High" },
                          { value: "Urgent", label: "Urgent" },
                        ],
                      },
                    ]}
                    submitLabel="Add case"
                    onSubmit={async (v) => {
                      await act(
                        () =>
                          api.post("/core-hr/cases", {
                            subject: v.subject,
                            category: v.category || "General",
                            priority: v.priority || "Medium",
                          }),
                        "HR case created",
                      )
                    }}
                  />
                ) : (
                  <Alert tone="info" className="mb-4">
                    Opening an HR case requires SuperAdmin or HR. You can read the queue below.
                  </Alert>
                )}
                <DataList
                  title="HR cases"
                  caption="All HR cases and their status"
                  columns={["Subject", "Status"]}
                  rows={cases}
                  source="/core-hr/cases"
                  unreadable={unreadable}
                  render={(c) => [c.subject, c.status]}
                />
              </div>
            )}

            {t.key === "payroll" && (
              <div className="space-y-4">
                {periods.length === 0 && components.length === 0 && payRuns.length === 0 ? (
                  <EmptyState
                    icon={<IconWallet />}
                    title="No payroll data"
                    description="No payroll periods, components or runs have been configured yet."
                    action={
                      <>
                        <Button variant="primary">Add pay period</Button>
                        <a href="/docs" className="text-sm text-fg-muted hover:underline ml-2">Learn more</a>
                      </>
                    }
                  />
                ) : (
                  <>
                    <ReconciliationPanel runs={payRuns} refreshRuns={loadAll} />
                    <PayslipPanel runs={payRuns} />
                    <DataList
                      title="Payroll periods"
                      description="Payroll calculations and payment are owned by the backend; this view is read-only."
                      caption="All payroll periods"
                      columns={["Name", "Status"]}
                      rows={periods}
                      source="/payroll/periods"
                      unreadable={unreadable}
                      render={(p) => [p.name, p.status]}
                    />
                    <DataList
                      title="Pay components"
                      caption="Earnings and deduction components"
                      columns={["Code", "Name", "Type"]}
                      rows={components}
                      source="/payroll/components"
                      unreadable={unreadable}
                      render={(c) => [c.code, c.name, c.component_type]}
                    />
                    <DataList
                      title="Pay runs"
                      caption="Processed payroll runs"
                      columns={["Run", "Status", "Gross"]}
                      rows={payRuns}
                      source="/payroll/runs"
                      unreadable={unreadable}
                      render={(p) => [`#${p.id}`, p.status, money(p.total_gross)]}
                    />
                  </>
                )}
              </div>
            )}

            {t.key === "performance" && (
              <div className="space-y-4">
                {goals.length === 0 && reviews.length === 0 && bands.length === 0 ? (
                  <EmptyState
                    icon={<IconTrend />}
                    title="No performance data"
                    description="No goals, reviews or compensation bands have been configured yet."
                    action={
                      <>
                        <Button variant="primary">Add goal</Button>
                        <a href="/docs" className="text-sm text-fg-muted hover:underline ml-2">Learn more</a>
                      </>
                    }
                  />
                ) : (
                  <>
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <p className="text-sm text-fg-muted">
                        Operational surface →{" "}
                        <Link to={tenantNav.to("/platform/performance")} className="text-[var(--semantic-brand-text)] hover:underline font-medium">
                          Performance Hub
                        </Link>{" "}
                        (feedback, merit cycles, review finalize)
                      </p>
                    </div>
                    <DataList
                      title="Goals"
                      caption="All performance goals"
                      columns={["Goal", "Progress", "Status"]}
                      rows={goals}
                      source="/performance/goals"
                      unreadable={unreadable}
                      render={(g) => [g.title, g.progress != null ? `${g.progress}%` : "—", g.status]}
                    />
                    <DataList
                      title="Performance reviews"
                      caption="All performance review cycles"
                      columns={["Period", "Status", "Rating"]}
                      rows={reviews}
                      source="/performance/reviews"
                      unreadable={unreadable}
                      render={(r) => [r.period, r.status, r.overall_rating ?? "—"]}
                    />
                    <DataList
                      title="Compensation bands"
                      caption="Salary bands by level"
                      columns={["Level", "Minimum", "Maximum"]}
                      rows={bands}
                      source="/performance/compensation-bands"
                      unreadable={unreadable}
                      render={(b) => [b.level, money(b.min_salary), money(b.max_salary)]}
                    />
                  </>
                )}
              </div>
            )}

            {t.key === "benefits" && (
              <div className="space-y-4">
                {plans.length === 0 && enrollments.length === 0 ? (
                  <EmptyState
                    icon={<IconHeart />}
                    title="No benefits data"
                    description="No benefit plans or enrollments have been configured yet."
                    action={
                      <>
                        <Button variant="primary">Add benefit plan</Button>
                        <a href="/docs" className="text-sm text-fg-muted hover:underline ml-2">Learn more</a>
                      </>
                    }
                  />
                ) : (
                  <>
                    <p className="text-sm text-fg-muted">
                      Operational surface →{" "}
                      <Link to={tenantNav.to("/platform/benefits")} className="text-[var(--semantic-brand-text)] hover:underline font-medium">
                        Benefits Hub
                      </Link>{" "}
                      (life events, leaves of absence + approve)
                    </p>
                    <DataList
                      title="Benefit plans"
                      caption="All configured benefit plans"
                      columns={["Code", "Name", "Type"]}
                      rows={plans}
                      source="/benefits/benefit-plans"
                      unreadable={unreadable}
                      render={(p) => [p.code, p.name, p.plan_type]}
                    />
                    <DataList
                      title="Enrollments"
                      caption="Employee benefit enrollments"
                      columns={["Employee", "Plan", "Status"]}
                      rows={enrollments}
                      source="/benefits/benefit-enrollments"
                      unreadable={unreadable}
                      render={(e) => [String(e.employee_id), String(e.plan_id), e.status]}
                    />
                  </>
                )}
              </div>
            )}

            {t.key === "learning" && (
              <div className="space-y-4">
                {courses.length === 0 && certs.length === 0 ? (
                  <EmptyState
                    icon={<IconBook />}
                    title="No learning data"
                    description="No courses or certifications have been configured yet."
                    action={
                      <>
                        <Button variant="primary">Add course</Button>
                        <a href="/docs" className="text-sm text-fg-muted hover:underline ml-2">Learn more</a>
                      </>
                    }
                  />
                ) : (
                  <>
                    <p className="text-sm text-fg-muted">
                      Operational surface →{" "}
                      <Link to={tenantNav.to("/platform/learning")} className="text-[var(--semantic-brand-text)] hover:underline font-medium">
                        Learning Hub
                      </Link>{" "}
                      (enrollments, talent pools, succession)
                    </p>
                    <DataList
                      title="Courses"
                      caption="All learning catalogue courses"
                      columns={["Code", "Title"]}
                      rows={courses}
                      source="/learning/courses"
                      unreadable={unreadable}
                      render={(c) => [c.code, c.title]}
                    />
                    <DataList
                      title="Certifications"
                      caption="All certifications"
                      columns={["Name", "Issuer"]}
                      rows={certs}
                      source="/learning/certifications"
                      unreadable={unreadable}
                      render={(c) => [c.name, c.issuer ?? "—"]}
                    />
                  </>
                )}
              </div>
            )}

            {t.key === "integrations" && (
              <div className="space-y-4">
                <p className="text-sm text-fg-muted">
                  Operational surface →{" "}
                  <Link to={tenantNav.to("/platform/integrations")} className="text-[var(--semantic-brand-text)] hover:underline font-medium">
                    Integrations Hub
                  </Link>{" "}
                  (SSO, webhooks, delivery, checks, signatures)
                </p>
                <DataList
                  title="Webhooks"
                  caption="Registered outbound webhooks"
                  columns={["URL", "Events"]}
                  rows={webhooks}
                  source="/platform/webhooks"
                  unreadable={unreadable}
                  render={(w) => [String(w.url).slice(0, 60), Array.isArray(w.events) ? w.events.join(", ") : String(w.events ?? "—")]}
                />
                <DataList
                  title="Background checks"
                  caption="Candidate background checks"
                  columns={["Candidate", "Status"]}
                  rows={checks}
                  source="/platform/background-checks"
                  unreadable={unreadable}
                  render={(c) => [String(c.candidate_id), c.status]}
                />
                <DataList
                  title="E-signatures"
                  caption="Electronic signature envelopes"
                  columns={["Document", "Status"]}
                  rows={sigs}
                  source="/platform/e-signatures"
                  unreadable={unreadable}
                  render={(s) => [s.document_type, s.status]}
                />
              </div>
            )}

            {t.key === "compliance" && (
              <div className="space-y-4">
                {rules.length === 0 && violations.length === 0 && plans2.length === 0 && scenarios.length === 0 ? (
                  <EmptyState
                    icon={<IconShield />}
                    title="No compliance data"
                    description="No compliance rules, violations, headcount plans or scenarios have been configured yet."
                    action={
                      <>
                        <Button variant="primary">Add rule</Button>
                        <a href="/docs" className="text-sm text-fg-muted hover:underline ml-2">Learn more</a>
                      </>
                    }
                  />
                ) : (
                  <>
                    <DataList
                      title="Compliance rules"
                      caption="Configured compliance rules"
                      columns={["Code", "Name", "Severity"]}
                      rows={rules}
                      source="/compliance/compliance-rules"
                      unreadable={unreadable}
                      render={(r) => [r.code, r.name, r.severity]}
                    />
                    <DataList
                      title="Violations"
                      caption="Recorded compliance violations"
                      columns={["Rule", "Status"]}
                      rows={violations}
                      source="/compliance/compliance-violations"
                      unreadable={unreadable}
                      render={(v) => [v.rule_id, v.status]}
                    />
                    <DataList
                      title="Headcount plans"
                      caption="Planned headcount by year"
                      columns={["Name", "Year", "Planned headcount"]}
                      rows={plans2}
                      source="/compliance/headcount-plans"
                      unreadable={unreadable}
                      render={(p) => [p.name, p.year, p.planned_headcount]}
                    />
                    <DataList
                      title="Scenarios"
                      caption="Workforce planning scenarios"
                      columns={["Scenario"]}
                      rows={scenarios}
                      source="/compliance/scenarios"
                      unreadable={unreadable}
                      render={(s) => [s.name]}
                    />
                  </>
                )}
              </div>
            )}

            {t.key === "importexport" && (
              <div className="mk-card p-5">
                <h2 className="mk-h2 text-fg mb-3">Data Import / Export</h2>
                {entities.length > 0 ? (
                  <>
                    <p className="text-sm text-fg-muted mb-4">
                      Supported entities:
                    </p>
                    <div className="flex flex-wrap gap-2 mb-5">
                      {entities.map((e) => (
                        <span key={e} className="badge badge-brand font-mono">{e}</span>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-fg-muted mb-4">
                    The entity list could not be loaded from the server.
                  </p>
                )}
                <div className="table-scroll">
                  <table className="table-base">
                    <caption className="sr-only">Import and export endpoints by operation</caption>
                    <thead>
                      <tr>
                        <th scope="col">Operation</th>
                        <th scope="col">Endpoint</th>
                        <th scope="col">Format</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Export</td>
                        <td><code className="font-mono text-xs">GET /api/v1/import-export/export/{"{entity}"}</code></td>
                        <td>CSV download</td>
                      </tr>
                      <tr>
                        <td>Import</td>
                        <td><code className="font-mono text-xs">POST /api/v1/import-export/import/{"{entity}"}</code></td>
                        <td>Multipart CSV upload</td>
                      </tr>
                      <tr>
                        <td>List entities</td>
                        <td><code className="font-mono text-xs">GET /api/v1/import-export/entities</code></td>
                        <td>JSON</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </Layout>
  )
}