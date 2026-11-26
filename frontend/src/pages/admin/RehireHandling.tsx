/* OB-07 — Rehire handling + dashboards (depends OB-06 + HR-02)
 * OB-06 (Exit + retention + erasure) shipped R4. HR-02 (Employment status) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for rehire config.
 * No fabricated rehire data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function RehireHandling() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [rehireEligible, setRehireEligible] = useState(true)
  const [rehireWaitDays, setRehireWaitDays] = useState(90)
  const [rehireReview, setRehireReview] = useState(true)
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
      setRehireEligible(getCfg("rehire_eligible") === "1")
      setRehireWaitDays(Number(getCfg("rehire_wait_days") ?? 90))
      setRehireReview(getCfg("rehire_review") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/rehire_eligible`, { config: rehireEligible ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/rehire_wait_days`, { config: String(rehireWaitDays) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/rehire_review`, { config: rehireReview ? "1" : "0" })
      await load()
      setNotice("Rehire handling config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Rehire Handling"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Rehire Handling + Dashboards" description="OB-07 · rehire handling + dashboards · depends OB-06 (shipped R4) + HR-02 (shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The rehire handling + dashboards could not be read." fallback="The rehire handling + dashboards could not be read." onRetry={load} />}
        <SectionCard compact title="Rehire configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Rehire eligible</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={rehireEligible}
                  onChange={e => setRehireEligible(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable rehire</span>
              </div>
            </div>
            <div>
              <label>Wait days before rehire</label>
              <Input value={rehireWaitDays} onChange={e => setRehireWaitDays(Number(e.target.value) || 90)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Review required</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={rehireReview}
                  onChange={e => setRehireReview(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Require review</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save rehire config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">OB-07 · R5 · depends OB-06 + HR-02 · no fabricated rehire data.</div>
      </div>
    </Layout>
  )
}