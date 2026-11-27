/* PM-05 — Succession + talent reviews + pools (depends PM-02)
 * PM-02 (Review cycles + self-assessments) shipped R4.
 * Uses real /clients/:slug/feature-flags endpoint for succession config.
 * No fabricated succession data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function SuccessionPlanning() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [successionCycle, setSuccessionCycle] = useState("annual")
  const [talentPoolSize, setTalentPoolSize] = useState(10)
  const [autoNominate, setAutoNominate] = useState(false)
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
      setSuccessionCycle((getCfg("succession_cycle") ?? "annual"))
      setTalentPoolSize(Number(getCfg("talent_pool_size") ?? 10))
      setAutoNominate(getCfg("auto_nominate") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/succession_cycle`, { config: successionCycle })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/talent_pool_size`, { config: String(talentPoolSize) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_nominate`, { config: autoNominate ? "1" : "0" })
      await load()
      setNotice("Succession planning config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const CYCLE_OPTIONS = [
    { value: "annual", label: "Annual" },
    { value: "biannual", label: "Biannual" },
    { value: "quarterly", label: "Quarterly" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Succession Planning"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Succession + Talent Reviews + Pools" description="PM-05 · succession + talent reviews + pools · depends PM-02 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The succession + talent reviews + pools could not be read." fallback="The succession + talent reviews + pools could not be read." onRetry={load} />}
        <SectionCard compact title="Succession configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Succession cycle</label>
              <select
                value={successionCycle}
                onChange={e => setSuccessionCycle(e.target.value)}
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
            <div>
              <label>Auto-nominate</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoNominate}
                  onChange={e => setAutoNominate(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-nominate</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save succession config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">PM-05 · R5 · depends PM-02 · no fabricated succession data.</div>
      </div>
    </Layout>
  )
}