import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import { listEmployees, rebuildOrgChart, errorMessage } from "@/lib/api"

export default function OrgChart() {
  const { user } = useAuth()
  const canRebuild = ["SuperAdmin", "HR"].includes(user?.role ?? "")
  const [employees, setEmployees] = useState<import("@/lib/api").EmployeeOut[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [error, setError] = useState<unknown | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null); setNotice("")
    try {
      const data = await listEmployees()
      setEmployees(data)
      setSelectedId(prev => prev && data.some(e => e.id === prev) ? prev : (data[0]?.id ?? null))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async () => {
    setSaving(true); setNotice(""); setActionError("")
    try {
      await rebuildOrgChart()
      await load()
      setNotice("Org chart rebuilt from employee master.")
    } catch (e) { setActionError(errorMessage(e, "The org chart could not be rebuilt.")) } finally { setSaving(false) }
  }

  if (loading) return <Layout><LoadingRegion label="Org Chart"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  const selected = employees.find(e => e.id === selectedId)
  const manager = selected?.manager_id ? employees.find(e => e.id === selected.manager_id) : null

  return (
    <Layout>
      <PageHeader compact title="Org Chart + Directory" description="HR-06 · org chart + delegated responsibility · depends HR-01 + HR-04 + AD-04 (all shipped) · reads real employee data; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The org chart + directory could not be read." fallback="The org chart + directory could not be read." onRetry={load} />}
        <SectionCard compact title="Org chart" description="From real employee data.">
          <div className="grid sm:grid-cols-3 gap-4 text-sm">
            <div><div className="text-xs text-fg-muted">Name</div><div className="font-semibold">{selected ? `${selected.first_name} ${selected.last_name}` : "—"}</div></div>
            <div><div className="text-xs text-fg-muted">Role</div><div className="font-semibold">{selected?.job_title ?? "—"}</div></div>
            <div><div className="text-xs text-fg-muted">Department</div><div className="font-semibold">{selected?.department_name ?? "—"}</div></div>
          </div>
        </SectionCard>
        <SectionCard compact title="Employee details" description="Selected employee record.">
          <div className="grid sm:grid-cols-2 gap-4 text-sm">
            <div><div className="text-xs text-fg-muted">Employee ID</div><div className="font-semibold">{selected?.employee_id ?? "—"}</div></div>
            <div><div className="text-xs text-fg-muted">Full Name</div><div className="font-semibold">{selected ? `${selected.first_name} ${selected.last_name}` : "—"}</div></div>
            <div><div className="text-xs text-fg-muted">Job Title</div><div className="font-semibold">{selected?.job_title ?? "—"}</div></div>
            <div><div className="text-xs text-fg-muted">Department</div><div className="font-semibold">{selected?.department_name ?? "—"}</div></div>
            <div><div className="text-xs text-fg-muted">Manager</div><div className="font-semibold">{manager ? `${manager.first_name} ${manager.last_name}` : "—"}</div></div>
            <div><div className="text-xs text-fg-muted">Email</div><div className="font-semibold">{selected?.email ?? "—"}</div></div>
            <div><div className="text-xs text-fg-muted">Status</div><div className="font-semibold">{selected?.status ?? "—"}</div></div>
          </div>
        </SectionCard>
        <SectionCard compact title="Employee list" description="Selected org chart employee.">
          {employees.length === 0 ? (
            <EmptyState title="No employees" description="No employee records are visible yet. Add employees in People, then rebuild the org chart." />
          ) : employees.map(e => (
            <button
              key={e.id}
              type="button"
              onClick={() => setSelectedId(e.id)}
              aria-pressed={selectedId === e.id}
              className={`block w-full text-left p-2 rounded border hover:border-border ${selectedId === e.id ? "border-brand-600" : ""}`}
            >
              <span>{e.first_name} {e.last_name} ({e.job_title})</span>
            </button>
          ))}
        </SectionCard>
        <div className="text-xs text-fg-muted">HR-06 · R4 · depends HR-01 + HR-04 + AD-04 · no fabricated org chart data.</div>
        <div className="flex justify-end mt-4">
          {canRebuild && (
            <Button onClick={save} disabled={saving || !canRebuild}>
              Rebuild Org Chart
            </Button>
          )}
        </div>
      </div>
    </Layout>
  )
}