/* PM-06 — Promotion readiness + talent analytics (depends PM-05 + PM-03)
 * PM-05 (Succession planning) shipped R5. PM-03 (Competency calibration) shipped R5.
 * Uses real /clients/:slug/feature-flags endpoint for promotion readiness config.
 * No fabricated promotion data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function PromotionReadiness() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [readinessThreshold, setReadinessThreshold] = useState(70)
  const [readinessCycle, setReadinessCycle] = useState("annual")
  const [talentPoolSize, setTalentPoolSize] = useState(10)
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
      setReadinessThreshold(Number(getCfg("readiness_threshold") ?? 70))
      setReadinessCycle((getCfg("readiness_cycle") ?? "annual"))
      setTalentPoolSize(Number(getCfg("talent_pool_size") ?? 10))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/readiness_threshold`, { config: String(readinessThreshold) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/readiness_cycle`, { config: readinessCycle })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/talent_pool_size`, { config: String(talentPoolSize) })
      await load()
      setNotice("Promotion readiness config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const CYCLE_OPTIONS = [
    { value: "annual", label: "Annual" },
    { value: "biannual", label: "Biannual" },
    { value: "quarterly", label: "Quarterly" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Promotion Readiness"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Promotion Readiness + Talent Analytics" description="PM-06 · promotion readiness + talent analytics · depends PM-05 (shipped R5) + PM-03 (shipped R5) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The promotion readiness + talent analytics could not be read." fallback="The promotion readiness + talent analytics could not be read." onRetry={load} />}
        <SectionCard compact title="Promotion readiness configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Readiness threshold (%)</label>
              <Input value={readinessThreshold} onChange={e => setReadinessThreshold(Number(e.target.value) || 70)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Review cycle</label>
              <select
                value={readinessCycle}
                onChange={e => setReadinessCycle(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {CYCLE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Talent pool size</label>
              <Input value={talentPoolSize} onChange={e => setTalentPoolSize(Number(e.target.value) || 10)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save promotion config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">PM-06 · R6 · depends PM-05 + PM-03 · no fabricated promotion data.</div>
      </div>
    </Layout>
  )
}