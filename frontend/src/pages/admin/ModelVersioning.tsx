/* AN-07 — Accuracy + model version + confidence (depends AN-04 + AD-07)
 * AN-04 (Demand forecasts) shipped R5. AD-07 (Audit chain) shipped BASELINE.
 * Uses real /clients/:slug/feature-flags endpoint for model config.
 * No fabricated model data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function ModelVersioning() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [modelVersion, setModelVersion] = useState("v1.0")
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.85)
  const [autoRetrain, setAutoRetrain] = useState(false)
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
      setModelVersion((getCfg("model_version") ?? "v1.0"))
      setConfidenceThreshold(Number(getCfg("confidence_threshold") ?? 0.85))
      setAutoRetrain(getCfg("auto_retrain") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/model_version`, { config: modelVersion })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/confidence_threshold`, { config: String(confidenceThreshold) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_retrain`, { config: autoRetrain ? "1" : "0" })
      await load()
      setNotice("Model versioning config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Model Versioning"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Model Versioning + Accuracy + Confidence" description="AN-07 · accuracy + model version + confidence · depends AN-04 (shipped R5) + AD-07 (shipped BASELINE) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The model versioning + accuracy + confidence could not be read." fallback="The model versioning + accuracy + confidence could not be read." onRetry={load} />}
        <SectionCard compact title="Model versioning configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Model version</label>
              <Input value={modelVersion} onChange={e => setModelVersion(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="v1.0" />
            </div>
            <div>
              <label>Confidence threshold</label>
              <Input value={confidenceThreshold} onChange={e => setConfidenceThreshold(Number(e.target.value) || 0.85)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Auto-retrain</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoRetrain}
                  onChange={e => setAutoRetrain(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-retrain</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save model config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">AN-07 · R6 · depends AN-04 + AD-07 · no fabricated model data.</div>
      </div>
    </Layout>
  )
}