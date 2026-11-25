import { useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert,
  EmptyState,
  LoadingRegion,
  Meter,
  PageHeader,
  SectionCard,
  StatCard,
  StatusPill, RetryableAlert, TableSkeleton} from "@/components/ui"
import { IconCheck, IconFile, IconPlus, IconRocket, IconUpload } from "@/components/icons"
import api, { fileUrl } from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import { useAuth } from "@/context/AuthContext"
import type {
  Employee,
  OnboardingDocument,
  OnboardingSummary,
  OnboardingTask,
} from "@/types"

export default function Onboarding() {
  const { user } = useAuth()
  // Mirrors backend/app/api/v1/endpoints/onboarding.py: every new-hire can
  // READ a checklist (`/summary`/`/tasks`/`/documents` → ALL_ROLES,
  // `:241/:269/:315`), but creating the checklist (`:257`), moving a task's
  // status (`:297`) and uploading documents (`:331`) are ADMIN_ROLES.
  const isAdmin = user?.role === "SuperAdmin" || user?.role === "HR"
  const [employees, setEmployees] = useState<Employee[]>([])
  const [selected, setSelected] = useState<number | "">("")
  const [summary, setSummary] = useState<OnboardingSummary | null>(null)
  const [tasks, setTasks] = useState<OnboardingTask[]>([])
  const [documents, setDocuments] = useState<OnboardingDocument[]>([])
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  // Per-section failure flags for the selected employee — a summary miss
  // must not blank the task list beside it.
  type LoadKey = "summary" | "tasks" | "documents"
  const [failedEmployeeReport, setFailedEmployeeReport] = useState<LoadKey[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState("")
  const [docType, setDocType] = useState("IDProof")
  const [file, setFile] = useState<File | null>(null)

  useEffect(() => {
    fetchAllEmployees()
      .then(({ items }) => {
        setEmployees(items)
        if (items.length > 0) setSelected(items[0].id)
      })
      .catch(() =>
        setError(
          "The employee list could not be loaded — it may be temporarily unavailable or restricted for your role.",
        ),
      )
      .finally(() => setLoading(false))
  }, [])

  type EmployeeLoad = { key: LoadKey; label: string }
  const EMPLOYEE_LOADS: EmployeeLoad[] = [
    { key: "summary", label: "progress summary" },
    { key: "tasks", label: "checklist tasks" },
    { key: "documents", label: "uploaded documents" },
  ]

  const loadEmployee = async (id: number) => {
    setError("")
    const results = await Promise.allSettled([
      api.get(`/onboarding/${id}/summary`),
      api.get(`/onboarding/${id}/tasks`),
      api.get(`/onboarding/${id}/documents`),
    ])
    const failedKeys: LoadKey[] = []
    results.forEach((r, i) => {
      const key = EMPLOYEE_LOADS[i].key
      if (r.status === "fulfilled") {
        const data = r.value.data
        if (key === "summary") setSummary(data)
        else if (key === "tasks") setTasks(data)
        else if (key === "documents") setDocuments(data)
      } else {
        failedKeys.push(key)
      }
    })
    setFailedEmployeeReport(failedKeys)
    if (failedKeys.length > 0) {
      setError(
        `Some onboarding data for the selected employee could not be loaded: ${failedKeys
          .map((k) => EMPLOYEE_LOADS.find((l) => l.key === k)?.label ?? k)
          .join(", ")}.`,
      )
    }
  }

  useEffect(() => {
    if (selected !== "") loadEmployee(Number(selected))
  }, [selected])

  const act = async (key: string, fn: () => Promise<unknown>, msg: string) => {
    setError("")
    setNotice("")
    setBusy(key)
    try {
      await fn()
      setNotice(msg)
      if (selected !== "") await loadEmployee(Number(selected))
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Action failed")
    } finally {
      setBusy("")
    }
  }

  const empName = (e: Employee) => `${e.first_name} ${e.last_name} (${e.employee_id})`
  const selectedEmployee = employees.find((e) => e.id === selected)
  const completed = summary?.completed_tasks ?? 0
  const remaining = summary ? summary.total_tasks - summary.completed_tasks : 0

  return (
    <Layout>
      <PageHeader compact
        icon={<IconRocket />}
        title="Onboarding"
        description="Track new-hire checklists and collect required documents."
      />

      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      {loading ? (
        <LoadingRegion label="Loading employees">
          <div className="skeleton h-24 mb-5" />
        </LoadingRegion>
      ) : (
        <>
          {/* Employee selector */}
          <section className="card mb-5">
            <div className="toolbar">
              <div className="field min-w-[240px] grow">
                <label htmlFor="on-emp" className="field-label">Employee (required)</label>
                <select
                  id="on-emp"
                  className="input"
                  value={selected}
                  onChange={(e) => setSelected(Number(e.target.value))}
                >
                  {employees.map((e) => (
                    <option key={e.id} value={e.id}>{empName(e)}</option>
                  ))}
                </select>
                {!loading && employees.length === 0 && (
                  <p className="mt-1 text-xs text-warning-text" role="note">
                    No employees are visible to your account yet — ask an HR or SuperAdmin user.
                  </p>
                )}
              </div>
              {isAdmin ? (
                /* POST /onboarding/{id}/checklist is ADMIN_ROLES
                   (onboarding.py:257) */
                <button
                  className="btn btn-primary"
                  disabled={selected === "" || busy === "cl"}
                  onClick={() =>
                    act("cl", () => api.post(`/onboarding/${selected}/checklist`), "Default checklist created")
                  }
                >
                  <IconPlus className="w-4 h-4" />
                  {busy === "cl" ? "Generating…" : "Generate default checklist"}
                </button>
              ) : (
                <p className="text-xs text-text-secondary max-w-[240px]" role="note">
                  Checklists are generated by HR or SuperAdmin — your role reads the
                  progress and marks nothing.
                </p>
              )}
            </div>

            {summary && (
              <div className="px-5 py-4 border-t border-border">
                <Meter
                  percent={summary.progress_percent}
                  label={`${completed} of ${summary.total_tasks} tasks complete · ${summary.documents_uploaded} document${summary.documents_uploaded === 1 ? "" : "s"} uploaded`}
                />
              </div>
            )}
          </section>

          {selectedEmployee && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
              <StatCard tone="brand" label="Tasks" value={`${completed}/${summary?.total_tasks ?? 0}`} hint={`${remaining} remaining`} />
              <StatCard tone="green" label="Progress" value={`${summary?.progress_percent ?? 0}%`} />
              <StatCard tone="violet" label="Documents" value={summary?.documents_uploaded ?? 0} />
              <StatCard tone="slate" label="Employee ID" value={selectedEmployee.employee_id} />
            </div>
          )}

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <SectionCard compact icon={<IconCheck />} title="Checklist"
              description="Onboarding tasks for the selected employee.">
              {tasks.length === 0 ? (
                <EmptyState
                  title={failedEmployeeReport.includes("tasks") ? "Tasks unavailable" : "No tasks yet"}
                  description={
                    failedEmployeeReport.includes("tasks")
                      ? "The task list could not be loaded for this employee — try selecting them again."
                      : isAdmin
                        ? "Generate the default checklist to populate onboarding tasks."
                        : "The default checklist is generated by HR or SuperAdmin; tasks appear here once it exists."
                  }
                />
              ) : (
                <div
                  className="table-scroll max-h-[420px] overflow-y-auto"
                  tabIndex={0}
                  role="region"
                  aria-label="Onboarding checklist tasks"
                >
                  <table className="table-base table-striped">
                    <caption className="sr-only">Onboarding checklist tasks</caption>
                    <thead>
                      <tr>
                        <th scope="col">Task</th>
                        <th scope="col">Category</th>
                        <th scope="col">Due</th>
                        <th scope="col">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tasks.map((t) => (
                        <tr key={t.id}>
                          <td>
                            <span className="font-medium">{t.title}</span>
                            {t.description && (
                              <span className="block text-xs text-text-secondary mt-0.5">
                                {t.description}
                              </span>
                            )}
                          </td>
                          <td className="text-text-secondary">{t.category}</td>
                          <td className="whitespace-nowrap text-text-secondary">{t.due_date || "—"}</td>
                          <td>
                            <label htmlFor={`task-status-${t.id}`} className="text-xs text-fg-muted leading-none mb-1 block">
                              Status for {t.title}
                            </label>
                            {isAdmin ? (
                              /* PUT /onboarding/tasks/{id} is ADMIN_ROLES
                                 (onboarding.py:297) */
                              <select
                                id={`task-status-${t.id}`}
                                className="input py-1.5 text-xs w-32"
                                value={t.status}
                                disabled={busy === `t${t.id}`}
                                onChange={(e) =>
                                  act(`t${t.id}`, () => api.put(`/onboarding/tasks/${t.id}`, {
                                    status: e.target.value,
                                  }), "Task updated")
                                }
                              >
                                {["Pending", "InProgress", "Completed"].map((s) => (
                                  <option key={s}>{s}</option>
                                ))}
                              </select>
                            ) : (
                              <StatusPill status={t.status} />
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>

            <SectionCard compact icon={<IconFile />} title="Documents"
              description="Required identity, tax and contract documents.">
              {isAdmin ? (
                /* POST /onboarding/{id}/documents is ADMIN_ROLES
                   (onboarding.py:331) */
                <div className="toolbar">
                  <div className="field min-w-[150px]">
                    <label htmlFor="doc-type" className="field-label">Document type (required)</label>
                    <select
                      id="doc-type"
                      className="input"
                      value={docType}
                      onChange={(e) => setDocType(e.target.value)}
                    >
                      {["IDProof", "TaxForm", "BankDetails", "Contract", "Certificate"].map((t) => (
                        <option key={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                  <div className="field grow min-w-[180px]">
                    <label htmlFor="doc-file" className="field-label">File (required)</label>
                    <input
                      id="doc-file"
                      type="file"
                      className="input py-1.5"
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    />
                  </div>
                  <button
                    className="btn btn-primary"
                    disabled={!file || selected === "" || busy === "up"}
                    onClick={() => {
                      if (selected === "" || !file) return
                      const fd = new FormData()
                      fd.append("document_type", docType)
                      fd.append("file", file)
                      act("up", () => api.post(`/onboarding/${selected}/documents`, fd), "Document uploaded")
                      setFile(null)
                    }}
                  >
                    <IconUpload className="w-4 h-4" />
                    {busy === "up" ? "Uploading…" : "Upload"}
                  </button>
                </div>
              ) : (
                <p className="px-5 py-3 text-sm text-text-secondary border-b border-border" role="note">
                  Document upload is an HR or SuperAdmin action — employees view the
                  documents collected on their behalf here.
                </p>
              )}

              {documents.length === 0 ? (
                <EmptyState
                  title={failedEmployeeReport.includes("documents") ? "Documents unavailable" : "No documents uploaded"}
                  description={
                    failedEmployeeReport.includes("documents")
                      ? "The document list could not be loaded for this employee — try selecting them again."
                      : isAdmin
                        ? "Upload identity and tax documents above to complete the checklist."
                        : "Documents collected by HR appear here once uploaded."
                  }
                />
              ) : (
                <div className="table-scroll max-h-[320px] overflow-y-auto">
                  <table className="table-base table-striped">
                    <caption className="sr-only">Uploaded onboarding documents</caption>
                    <thead>
                      <tr>
                        <th scope="col">Type</th>
                        <th scope="col">File</th>
                        <th scope="col">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((d) => (
                        <tr key={d.id}>
                          <td className="font-medium">{d.document_type}</td>
                          <td>
                            <a
                              className="action-link"
                              href={fileUrl(d.storage_url)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {d.file_name}
                            </a>
                          </td>
                          <td><StatusPill status={d.status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>
          </div>
        </>
      )}
    </Layout>
  )
}