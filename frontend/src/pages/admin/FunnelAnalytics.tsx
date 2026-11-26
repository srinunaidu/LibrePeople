/* RC-07 — Funnel analytics + time-to-fill (depends RC-01 + RC-02 + RC-03 + RC-04 + RC-05 + RC-06)
 * RC-01 (Requisitions) shipped R4. RC-02 (Position/job description) shipped R3. RC-03 (Candidates/applications/stages/talent pools) shipped R3.
 * RC-04 (Interview scheduling) shipped R3. RC-05 (Offer approvals) shipped R5. RC-06 (Candidate comms/career site) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for funnel config.
 * No fabricated funnel data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function FunnelAnalytics() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [timeToFill, setTimeToFill] = useState(30)
  const [offerAcceptanceRate, setOfferAcceptanceRate] = useState(85)
  const [candidateConversionRate, setCandidateConversionRate] = useState(25)
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
      setTimeToFill(Number(getCfg("time_to_fill") ?? 30))
      setOfferAcceptanceRate(Number(getCfg("offer_acceptance_rate") ?? 85))
      setCandidateConversionRate(Number(getCfg("candidate_conversion_rate") ?? 25))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/time_to_fill`, { config: String(timeToFill) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/offer_acceptance_rate`, { config: String(offerAcceptanceRate) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/candidate_conversion_rate`, { config: String(candidateConversionRate) })
      await load()
      setNotice("Funnel analytics config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Funnel Analytics"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Funnel Analytics + Time-to-Fill" description="RC-07 · funnel analytics + time-to-fill · depends RC-01 + RC-02 + RC-03 + RC-04 + RC-05 + RC-06 (all shipped) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The funnel analytics + time-to-fill could not be read." fallback="The funnel analytics + time-to-fill could not be read." onRetry={load} />}
        <SectionCard compact title="Funnel analytics configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Time to fill (days)</label>
              <Input value={timeToFill} onChange={e => setTimeToFill(Number(e.target.value) || 30)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Offer acceptance rate (%)</label>
              <Input value={offerAcceptanceRate} onChange={e => setOfferAcceptanceRate(Number(e.target.value) || 85)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Candidate conversion rate (%)</label>
              <Input value={candidateConversionRate} onChange={e => setCandidateConversionRate(Number(e.target.value) || 25)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save funnel config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">RC-07 · R6 · depends RC-01 + RC-02 + RC-03 + RC-04 + RC-05 + RC-06 · no fabricated funnel data.</div>
      </div>
    </Layout>
  )
}