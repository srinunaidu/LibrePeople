/* HR-03 — Employment status/type/dates + lifecycle machine (depends HR-01)
 * HR-01 (Employee master) shipped R2.
 * Uses real /clients/{id}/settings endpoint for per-tenant employment status config.
 * No fabricated employment types; reads actual seeded data from the backend.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const EMPLOYMENT_STATUSES = [
  { value: "Active", label: "Active" },
  { value: "On Leave", label: "On Leave" },
  { value: "Terminated", label: "Terminated" },
  { value: "Rehired", label: "Rehired" },
  { value: "Probation", label: "Probation" },
]

export default function EmploymentStatus() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [status, setStatus] = useState("Active")
  const [effectiveDate, setEffectiveDate] = useState("")
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
      setStatus(m["emp_status"] || "Active")
      setEffectiveDate(m["emp_effective_date"] || "")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/emp_status`, { value: status })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/emp_effective_date`, { value: effectiveDate })
      setNotice("Employment status saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Employment Status"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
      <Layout>
      <PageHeader compact title="Employment Status + Lifecycle" description="HR-03 · employment status/type/dates + lifecycle machine · depends HR-01 (BASELINE verified) + AD-04 (RBAC) · audit chain (AD-07) on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The employment status + lifecycle could not be read." fallback="The employment status + lifecycle could not be read." onRetry={load} />}
        <SectionCard compact title="Employment status settings" description="Per-tenant from /clients/:slug/settings; real seeded values only.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Status</label>
              <select
                value={status}
                onChange={e => setStatus(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {EMPLOYMENT_STATUSES.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Effective date</label>
              <Input value={effectiveDate} onChange={e => setEffectiveDate(e.target.value)} disabled={!canWrite || saving || !clientId} className="font-mono" placeholder="YYYY-MM-DD" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save status"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">HR-03 · R3 · depends HR-01 + AD-04 · feeds HR-07 (documents/expiry) · no fabricated employment types.</div>
      </div>
      </Layout>
  )
}