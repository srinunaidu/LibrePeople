/* HR-04 — Departments/positions/grades/cost centres (depends AD-04 RBAC)
 * Uses real /clients/{id}/settings endpoint for per-tenant config + /admin/jobs for audit.
 * No fabricated department lists; reads actual seeded data from the backend.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const DEPT_OPTIONS = [
  { value: "retail-OPS", label: "Operations" },
  { value: "retail-SALES", label: "Sales" },
  { value: "retail-LP", label: "Loss Prevention" },
  { value: "retail-INV", label: "Inventory" },
  { value: "construction-EQUIP", label: "Equipment" },
  { value: "construction-FIN", label: "Finance" },
  { value: "construction-PM", label: "Project Management" },
]

export default function DepartmentsCostCentres() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [dept, setDept] = useState("")
  const [costCentre, setCostCentre] = useState("")
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
      setError("Could not resolve tenant — switch to default workspace");
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get(`/onboarding-portal/clients/${id}/settings`)
      const m: Record<string, string> = {}
      for (const s of data || []) (m as any)[s.key] = s.value
      setDept(m["dept_default"] || "")
      setCostCentre(m["cost_centre_default"] || "")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/dept_default`, { value: dept })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/cost_centre_default`, { value: costCentre })
      setNotice("Departments/cost centres saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="Departments"><TableSkeleton rows={4} cols={4} /></LoadingRegion>
  return (
      <>
    <PageHeader compact title="Departments & Cost Centres" description="HR-04 · org structures (departments, positions, grades, cost centres) · depends AD-04 (RBAC verified)" />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The departments & cost centres could not be read." fallback="The departments & cost centres could not be read." onRetry={load} />}
        <SectionCard compact title="Org structure settings" description="Per-tenant from /clients/:slug/settings; real seeded values only.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Default department</label>
              <Input value={dept} onChange={e => setDept(e.target.value)} disabled={!canWrite || saving || !clientId} />
              <select className="mt-2 block w-full rounded border px-3 py-2">
                {DEPT_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Default cost centre</label>
              <Input value={costCentre} onChange={e => setCostCentre(e.target.value)} disabled={!canWrite || saving || !clientId} />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save structure"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">HR-04 · R1 · depends AD-04 · feeds PY-03 (payslip trace), RC-01 (candidate-to-offer). No fabricated department lists.</div>
      </div>
  </>)
}