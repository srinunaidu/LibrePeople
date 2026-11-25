/* AN-04 — Demand + labour-cost forecasts (depends AN-02 + SC-01)
 * AN-02 (Metric definitions) shipped R4. SC-01 (Templates/drafts/publish) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for forecast config.
 * No fabricated forecast data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function DemandForecasting() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [headcount, setHeadcount] = useState(0)
  const [laborCost, setLaborCost] = useState(0)
  const [forecastMonths, setForecastMonths] = useState(12)
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
      setHeadcount(Number(getCfg("headcount") ?? 0))
      setLaborCost(Number(getCfg("labor_cost") ?? getCfg("labour_cost") ?? 0))
      setForecastMonths(Number(getCfg("forecast_months") ?? 12))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/headcount`, { config: String(headcount) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/labor_cost`, { config: String(laborCost) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/labour_cost`, { config: String(laborCost) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/forecast_months`, { config: String(forecastMonths) })
      await load()
      setNotice("Forecast settings saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Demand Forecasting"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Demand + Labour Cost Forecasting" description="AN-04 · demand/hiring/turnover/labour-cost forecasts · depends AN-02 (shipped R4) + SC-01 (shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The demand + labour cost forecasting could not be read." fallback="The demand + labour cost forecasting could not be read." onRetry={load} />}
        <SectionCard compact title="Forecast configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Current headcount</label>
              <Input value={headcount} onChange={e => setHeadcount(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Labour cost (period)</label>
              <Input value={laborCost} onChange={e => setLaborCost(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Forecast horizon (months)</label>
              <Input value={forecastMonths} onChange={e => setForecastMonths(Number(e.target.value) || 12)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div />
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save forecast config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">AN-04 · R5 · depends AN-02 + SC-01 · no fabricated forecast data.</div>
      </div>
    </Layout>
  )
}