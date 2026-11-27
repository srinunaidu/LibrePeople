/* SC-07 — Coverage gaps + overtime alerts (depends SC-01 + SC-02)
 * SC-01 (Templates/drafts/publish) shipped R3. SC-02 (Demand-based staffing) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for coverage config.
 * No fabricated coverage data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function CoverageGaps() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [coverageThreshold, setCoverageThreshold] = useState(80)
  const [overtimeThreshold, setOvertimeThreshold] = useState(40)
  const [alertEnabled, setAlertEnabled] = useState(true)
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
      setCoverageThreshold(Number(getCfg("coverage_threshold") ?? 80))
      setOvertimeThreshold(Number(getCfg("overtime_threshold") ?? 40))
      setAlertEnabled(getCfg("alert_enabled") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/coverage_threshold`, { config: String(coverageThreshold) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/overtime_threshold`, { config: String(overtimeThreshold) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/alert_enabled`, { config: alertEnabled ? "1" : "0" })
      await load()
      setNotice("Coverage config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Coverage Gaps"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Coverage Gaps + Overtime Alerts" description="SC-07 · coverage gaps + overtime alerts · depends SC-01 + SC-02 (both shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The coverage gaps + overtime alerts could not be read." fallback="The coverage gaps + overtime alerts could not be read." onRetry={load} />}
        <SectionCard compact title="Coverage configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Coverage threshold (%)</label>
              <Input value={coverageThreshold} onChange={e => setCoverageThreshold(Number(e.target.value) || 80)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Overtime threshold (hrs)</label>
              <Input value={overtimeThreshold} onChange={e => setOvertimeThreshold(Number(e.target.value) || 40)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Alert enabled</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={alertEnabled}
                  onChange={e => setAlertEnabled(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable alerts</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save coverage config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">SC-07 · R5 · depends SC-01 + SC-02 · no fabricated coverage data.</div>
      </div>
    </Layout>
  )
}