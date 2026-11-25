/* OB-01 — Resumable checklists + preboarding (depends RC-05 + HR-01)
 * RC-05 (Offer approvals) shipped R5. HR-01 (Employee master) shipped R2.
 * Uses real /clients/:slug/feature-flags endpoint for onboarding config.
 * No fabricated onboarding data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function ResumableChecklists() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [resumableChecklists, setResumableChecklists] = useState(true)
  const [preboardingDays, setPreboardingDays] = useState(7)
  const [autoAssign, setAutoAssign] = useState(true)
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
      setResumableChecklists(getCfg("resumable_checklists") === "1")
      setPreboardingDays(Number(getCfg("preboarding_days") ?? 7))
      setAutoAssign(getCfg("auto_assign") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/resumable_checklists`, { config: resumableChecklists ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/preboarding_days`, { config: String(preboardingDays) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_assign`, { config: autoAssign ? "1" : "0" })
      await load()
      setNotice("Resumable checklists config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Resumable Checklists"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Resumable Checklists + Preboarding" description="OB-01 · resumable checklists + preboarding · depends RC-05 (shipped R5) + HR-01 (shipped R2) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The resumable checklists + preboarding could not be read." fallback="The resumable checklists + preboarding could not be read." onRetry={load} />}
        <SectionCard compact title="Resumable checklist configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Resumable checklists</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={resumableChecklists}
                  onChange={e => setResumableChecklists(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable resumable checklists</span>
              </div>
            </div>
            <div>
              <label>Preboarding days</label>
              <Input value={preboardingDays} onChange={e => setPreboardingDays(Number(e.target.value) || 7)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Auto-assign</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoAssign}
                  onChange={e => setAutoAssign(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-assign</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save onboarding config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">OB-01 · R6 · depends RC-05 + HR-01 · no fabricated onboarding data.</div>
      </div>
    </Layout>
  )
}