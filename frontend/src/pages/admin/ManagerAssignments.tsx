/* HR-09 — Manager assignments + delegated responsibility (depends HR-01 + AD-05 + AD-04)
 * E-UX-02: assignee options come from the real employee master (listEmployees)
 * instead of the former hardcoded "John Doe / Jane Smith" list. Assignment and
 * department persist via /clients/:id/settings (require_roles("SuperAdmin")).
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage, listEmployees, type EmployeeOut } from "@/lib/api"

export default function ManagerAssignments() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [employees, setEmployees] = useState<EmployeeOut[]>([])
  const [assignee, setAssignee] = useState("")
  const [department, setDepartment] = useState("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [error, setError] = useState<unknown | null>(null)

  const load = useCallback(async () => {
    if (!canWrite) { setLoading(false); return }
    setLoading(true); setError(null); setNotice("")
    const id = await getClientIdBySlug()
    setClientId(id)
    if (id === null) {
      setError("Could not resolve the company. Check the server connection and retry.");
      setLoading(false);
      return;
    }
    try {
      const [{ data }, people] = await Promise.all([
        api.get(`/onboarding-portal/clients/${id}/settings`),
        listEmployees(),
      ])
      const m: Record<string, string> = {}
      for (const s of data || []) (m as any)[s.key] = s.value
      setEmployees(people)
      setAssignee(m["default_manager"] || "")
      setDepartment(m["default_manager_department"] || "")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const departments = Array.from(new Set(employees.map(e => e.department_name).filter((d): d is string => !!d)))

  const save = async () => {
    if (clientId === null) return
    if (!assignee) { setActionError("Select an assignee from the employee master."); return }
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/default_manager`, { value: assignee })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/default_manager_department`, { value: department })
      await load()
      setNotice("Manager assignment saved.")
    } catch (e) { setActionError(errorMessage(e, "The manager assignment could not be saved.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Manager assignments require SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Manager Assignments"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Manager Assignments + Delegated Responsibility" description="HR-09 · default manager from the real employee master · persists via /clients/:id/settings (SuperAdmin)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The manager assignments could not be read." fallback="The manager assignments could not be read." onRetry={load} />}
        <SectionCard compact title="Manager assignment" description="Assignee options are real employee records; department options come from employee departments.">
          {employees.length === 0 ? (
            <EmptyState title="No employees" description="No employee records are visible yet. Add employees in People first — manager options come from the employee master." />
          ) : (
            <>
              <div className="grid sm:grid-cols-3 gap-4">
                <div>
                  <label htmlFor="ma-assignee">Assignee</label>
                  <select
                    id="ma-assignee"
                    value={assignee}
                    onChange={e => setAssignee(e.target.value)}
                    className="w-full rounded border px-3 py-2"
                    disabled={!canWrite || saving || !clientId}
                  >
                    <option value="">Select manager…</option>
                    {employees.map(e => (
                      <option key={e.id} value={String(e.id)}>{e.first_name} {e.last_name}{e.department_name ? ` (${e.department_name})` : ""}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="ma-dept">Department</label>
                  <select
                    id="ma-dept"
                    value={department}
                    onChange={e => setDepartment(e.target.value)}
                    className="w-full rounded border px-3 py-2"
                    disabled={!canWrite || saving || !clientId}
                  >
                    <option value="">Select department…</option>
                    {departments.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>
                <div />
              </div>
              <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save assignment"}</Button>
            </>
          )}
        </SectionCard>
        <div className="text-xs text-fg-muted">HR-09 · R3 · depends HR-01 + AD-05 + AD-04 · feeds HR-12 (export) · options drawn from the employee master.</div>
      </div>
    </Layout>
  )
}