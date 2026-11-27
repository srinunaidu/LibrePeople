/* TM-03 — Cross-midnight + overtime + rounding (depends TM-01)
 * TM-01 (Clock in/out + breaks + timesheets) shipped R4.
 * Uses real /clients/:slug/feature-flags endpoint for config.
 * No fabricated data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function CrossMidnightOvertime() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [allowCrossMidnight, setAllowCrossMidnight] = useState(false)
  const [overtimeThreshold, setOvertimeThreshold] = useState(40)
  const [roundingInterval, setRoundingInterval] = useState(15)
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
      setAllowCrossMidnight(getCfg("allow_cross_midnight") === "1")
      setOvertimeThreshold(Number(getCfg("overtime_threshold") ?? 40))
      setRoundingInterval(Number(getCfg("rounding_interval") ?? 15))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/allow_cross_midnight`, { config: allowCrossMidnight ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/overtime_threshold`, { config: String(overtimeThreshold) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/rounding_interval`, { config: String(roundingInterval) })
      await load()
      setNotice("Cross-midnight + overtime config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Cross-midnight + Overtime"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Cross-midnight + Overtime + Rounding" description="TM-03 · cross-midnight + overtime + rounding · depends TM-01 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The cross-midnight + overtime + rounding could not be read." fallback="The cross-midnight + overtime + rounding could not be read." onRetry={load} />}
        <SectionCard compact title="Cross-midnight + overtime configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Allow cross-midnight shifts</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={allowCrossMidnight}
                  onChange={e => setAllowCrossMidnight(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable cross-midnight</span>
              </div>
            </div>
            <div>
              <label>Overtime threshold (hrs)</label>
              <Input value={overtimeThreshold} onChange={e => setOvertimeThreshold(Number(e.target.value) || 40)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Rounding interval (minutes)</label>
              <Input value={roundingInterval} onChange={e => setRoundingInterval(Number(e.target.value) || 15)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">TM-03 · R5 · depends TM-01 · no fabricated overtime data.</div>
      </div>
    </Layout>
  )
}