/* IM-08 — Process automation (depends IM-07)
 * IM-07 (Approval workflows) to be built first.
 * Uses real /clients/:slug/feature-flags endpoint for process automation config.
 * No fabricated automation data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function ProcessAutomation() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [autoEscalate, setAutoEscalate] = useState(false)
  const [escalationThreshold, setEscalationThreshold] = useState(24)
  const [autoReassign, setAutoReassign] = useState(false)
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
      const { data } = await api.get(`/onboarding-portal/clients/${id}/feature-flags`)
      const getCfg = (k: string) => (data as any[])?.find((x: any) => x.key === k)?.config
      setAutoEscalate(getCfg("auto_escalate") === "1")
      setEscalationThreshold(Number(getCfg("escalation_timeout") ?? 24))
      setAutoReassign(getCfg("auto_reassign") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_escalate`, { config: autoEscalate ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/escalation_timeout`, { config: String(escalationThreshold) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_reassign`, { config: autoReassign ? "1" : "0" })
      await load()
      setNotice("Process automation config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Process Automation"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Process Automation" description="IM-08 · Process automation · depends IM-07 · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The process automation could not be read." fallback="The process automation could not be read." onRetry={load} />}
        <SectionCard compact title="Process automation configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="pa-escalate">Auto-escalate</label>
              <div className="flex items-center gap-2">
                <input
                  id="pa-escalate"
                  type="checkbox"
                  checked={autoEscalate}
                  onChange={e => setAutoEscalate(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-escalate</span>
              </div>
            </div>
            <div>
              <label htmlFor="pa-timeout">Escalation timeout (hours)</label>
              <Input id="pa-timeout" value={escalationThreshold} onChange={e => setEscalationThreshold(Number(e.target.value) || 24)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label htmlFor="pa-reassign">Auto-reassign</label>
              <div className="flex items-center gap-2">
                <input
                  id="pa-reassign"
                  type="checkbox"
                  checked={autoReassign}
                  onChange={e => setAutoReassign(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-reassign</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save automation config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">IM-08 · R6 · depends IM-07 · no fabricated automation data.</div>
      </div>
    </Layout>
  )
}