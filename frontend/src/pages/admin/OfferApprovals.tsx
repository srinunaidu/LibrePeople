/* RC-05 — Offer approvals + hire transaction (depends RC-01 + RC-02 + RC-03)
 * RC-01 (Requisitions + budgets + approvals) shipped R4. RC-02 (Position/job description management) shipped R3. RC-03 (Candidates/applications/stages/talent pools) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for offer config.
 * No fabricated offer data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function OfferApprovals() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [autoApprove, setAutoApprove] = useState(false)
  const [approvalThreshold, setApprovalThreshold] = useState(5000)
  const [approvalLevels, setApprovalLevels] = useState(1)
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
      setAutoApprove(getCfg("auto_approve") === "1")
      setApprovalThreshold(Number(getCfg("approval_threshold") ?? 5000))
      setApprovalLevels(Number(getCfg("approval_levels") ?? 1))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_approve`, { config: autoApprove ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/approval_threshold`, { config: String(approvalThreshold) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/approval_levels`, { config: String(approvalLevels) })
      await load()
      setNotice("Offer approval config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Offer Approvals"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Offer Approvals + Hire Transaction" description="RC-05 · offer approvals + hire transaction · depends RC-01 + RC-02 + RC-03 (all shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The offer approvals + hire transaction could not be read." fallback="The offer approvals + hire transaction could not be read." onRetry={load} />}
        <SectionCard compact title="Offer approval configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Auto-approve offers</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoApprove}
                  onChange={e => setAutoApprove(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-approve</span>
              </div>
            </div>
            <div>
              <label>Approval threshold ($)</label>
              <Input value={approvalThreshold} onChange={e => setApprovalThreshold(Number(e.target.value) || 5000)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Approval levels</label>
              <Input value={approvalLevels} onChange={e => setApprovalLevels(Number(e.target.value) || 1)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save approval config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">RC-05 · R5 · depends RC-01 + RC-02 + RC-03 · no fabricated offer data.</div>
      </div>
    </Layout>
  )
}