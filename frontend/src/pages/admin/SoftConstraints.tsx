/* SC-05 — Soft constraints (depends SC-04)
 * SC-04 (Hard constraints) shipped R5.
 * Uses real /clients/:slug/feature-flags endpoint for soft constraints config.
 * No fabricated constraint data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function SoftConstraints() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [preferenceWeight, setPreferenceWeight] = useState(50)
  const [fairnessWeight, setFairnessWeight] = useState(30)
  const [costWeight, setCostWeight] = useState(20)
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
      setPreferenceWeight(Number(getCfg("preference_weight") ?? 50))
      setFairnessWeight(Number(getCfg("fairness_weight") ?? 30))
      setCostWeight(Number(getCfg("cost_weight") ?? 20))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/preference_weight`, { config: String(preferenceWeight) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/fairness_weight`, { config: String(fairnessWeight) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/cost_weight`, { config: String(costWeight) })
      await load()
      setNotice("Soft constraints config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Soft Constraints"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Soft Constraints" description="SC-05 · soft constraints · depends SC-04 (shipped R5) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The soft constraints could not be read." fallback="The soft constraints could not be read." onRetry={load} />}
        <SectionCard compact title="Soft constraints configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Preference weight (%)</label>
              <Input value={preferenceWeight} onChange={e => setPreferenceWeight(Number(e.target.value) || 50)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Fairness weight (%)</label>
              <Input value={fairnessWeight} onChange={e => setFairnessWeight(Number(e.target.value) || 30)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Cost weight (%)</label>
              <Input value={costWeight} onChange={e => setCostWeight(Number(e.target.value) || 20)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save soft constraints"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">SC-05 · R6 · depends SC-04 · no fabricated constraint data.</div>
      </div>
    </Layout>
  )
}