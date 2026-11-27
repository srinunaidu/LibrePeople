/* AI-06 — Tier B — forecast exception explanations (depends AN-07)
 * AN-07 (Accuracy + model version + confidence) shipped R6.
 * Uses real /clients/:slug/feature-flags endpoint for forecast config.
 * No fabricated forecast data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function ForecastException() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [forecastType, setForecastType] = useState("payroll_exceptions")
  const [alertThreshold, setAlertThreshold] = useState(10)
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
      setForecastType((getCfg("forecast_type") ?? "payroll_exceptions"))
      setAlertThreshold(Number(getCfg("alert_threshold") ?? 10))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/forecast_type`, { config: forecastType })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/alert_threshold`, { config: String(alertThreshold) })
      await load()
      setNotice("Forecast exception config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const FORECAST_TYPES = [
    { value: "payroll_exceptions", label: "Payroll Exceptions" },
    { value: "headcount_variance", label: "Headcount Variance" },
    { value: "turnover_forecast", label: "Turnover Forecast" },
    { value: "labor_cost_forecast", label: "Labor Cost Forecast" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Forecast Exceptions"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Payroll Exception Explanations" description="AI-06 · payroll exception explanations · depends AN-07 (shipped R6) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The payroll exception explanations could not be read." fallback="The payroll exception explanations could not be read." onRetry={load} />}
        <SectionCard compact title="Forecast exception configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Forecast type</label>
              <select
                value={forecastType}
                onChange={e => setForecastType(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {FORECAST_TYPES.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Alert threshold (%)</label>
              <Input value={alertThreshold} onChange={e => setAlertThreshold(Number(e.target.value) || 10)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div />
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save forecast config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">AI-06 · R7 · depends AN-07 · no fabricated forecast data.</div>
      </div>
    </Layout>
  )
}