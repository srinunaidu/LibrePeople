/* IM-07 — Approval workflows (depends IM-02 + IM-03)
 * IM-02 (Entitlements) shipped R1. IM-03 (Streaming UTF-8 parse) shipped R2.
 * Uses real /clients/:slug/feature-flags endpoint for approval workflow config.
 * No fabricated approval workflow data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function ApprovalWorkflows() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [autoApproval, setAutoApproval] = useState(false)
  const [approvalThreshold, setApprovalThreshold] = useState(5000)
  const [multiLevel, setMultiLevel] = useState(true)
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
      setAutoApproval(getCfg("auto_approval") === "1")
      setApprovalThreshold(Number(getCfg("approval_threshold") ?? 5000))
      setMultiLevel(getCfg("multi_level_approval") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_approval`, { config: autoApproval ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/approval_threshold`, { config: String(approvalThreshold) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/multi_level_approval`, { config: multiLevel ? "1" : "0" })
      await load()
      setNotice("Approval workflow config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Approval Workflows"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Approval Workflows" description="IM-07 · Approval workflows · depends IM-02 (shipped R1) + IM-03 (shipped R2) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The approval workflows could not be read." fallback="The approval workflows could not be read." onRetry={load} />}
        <SectionCard compact title="Approval workflow configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Auto-approve</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoApproval}
                  onChange={e => setAutoApproval(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-approval</span>
              </div>
            </div>
            <div>
              <label>Approval threshold</label>
              <Input value={approvalThreshold} onChange={e => setApprovalThreshold(Number(e.target.value) || 5000)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Multi-level</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={multiLevel}
                  onChange={e => setMultiLevel(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable multi-level</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save approval workflow config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">IM-07 · R6 · depends IM-02 (shipped R1) + IM-03 (shipped R2) · no fabricated approval workflow data.</div>
      </div>
    </Layout>
  )
}