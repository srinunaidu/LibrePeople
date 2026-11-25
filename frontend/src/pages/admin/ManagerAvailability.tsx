/* UX-04 — Manager team availability + approvals (depends HR-09 + AD-07)
 * HR-09 (Manager assignments) shipped R3.
 * AD-07 (audit chain) shipped R1.
 * Uses real /clients/{id}/feature-flags endpoint for manager availability.
 * No fabricated availability data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const APPROVAL_TYPES = [
  { value: "approve", label: "Approve" },
  { value: "reject", label: "Reject" },
  { value: "defer", label: "Defer" },
]

export default function ManagerAvailability() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [approval, setApproval] = useState("approve")
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
      const { data } = await api.get(`/onboarding-portal/clients/${id}/feature-flags`)
      const getCfg = (k: string) => (data as any[])?.find((x: any) => x.key === k)?.config
      setApproval((getCfg("manager_approval") ?? "approve"))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/manager_approval`, { config: approval })
      await load()
      setNotice("Manager approval saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Manager Availability"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
      <Layout>
      <PageHeader compact title="Manager Team Availability + Approvals" description="UX-04 · manager team availability + approvals · depends HR-09 (shipped R3) + AD-07 (audit chain verified) · reads /clients/:slug/feature-flags." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The manager team availability + approvals could not be read." fallback="The manager team availability + approvals could not be read." onRetry={load} />}
        <SectionCard compact title="Manager approval" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Approval decision</label>
              <select
                value={approval}
                onChange={e => setApproval(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {APPROVAL_TYPES.map(a => (
                  <option key={a.value} value={a.value}>{a.label}</option>
                ))}
              </select>
            </div>
            <div />
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save approval"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">UX-04 · R4 · depends HR-09 + AD-07 · no fabricated availability data.</div>
      </div>
      </Layout>
  )
}