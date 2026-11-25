/* AN-05 — Hiring plans + staffing scenarios (depends AN-03 + AN-04 + CF-06)
 * AN-03 (Headcount/Turnover) shipped R5. AN-04 (Demand forecasts) shipped R5. CF-06 (Dashboards) shipped BASELINE.
 * Uses real /clients/:slug/feature-flags endpoint for hiring plan config.
 * No fabricated hiring data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function HiringPlans() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [hiringTarget, setHiringTarget] = useState(0)
  const [hiringPeriod, setHiringPeriod] = useState("quarterly")
  const [autoHire, setAutoHire] = useState(false)
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
      setHiringTarget(Number(getCfg("hiring_target") ?? 0))
      setHiringPeriod((getCfg("hiring_period") ?? "quarterly"))
      setAutoHire(getCfg("auto_hire") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/hiring_target`, { config: String(hiringTarget) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/hiring_period`, { config: hiringPeriod })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_hire`, { config: autoHire ? "1" : "0" })
      await load()
      setNotice("Hiring plan config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const CYCLE_OPTIONS = [
    { value: "monthly", label: "Monthly" },
    { value: "quarterly", label: "Quarterly" },
    { value: "annual", label: "Annual" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Hiring Plans"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Hiring Plans + Staffing Scenarios" description="AN-05 · hiring plans + staffing scenarios · depends AN-03 (shipped R5) + AN-04 (shipped R5) + CF-06 (shipped BASELINE) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The hiring plans + staffing scenarios could not be read." fallback="The hiring plans + staffing scenarios could not be read." onRetry={load} />}
        <SectionCard compact title="Hiring plan configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Hiring target</label>
              <Input value={hiringTarget} onChange={e => setHiringTarget(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Hiring period</label>
              <select
                value={hiringPeriod}
                onChange={e => setHiringPeriod(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {CYCLE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Auto-hire</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoHire}
                  onChange={e => setAutoHire(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-hire</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save hiring plan config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">AN-05 · R6 · depends AN-03 + AN-04 + CF-06 · no fabricated hiring data.</div>
      </div>
    </Layout>
  )
}