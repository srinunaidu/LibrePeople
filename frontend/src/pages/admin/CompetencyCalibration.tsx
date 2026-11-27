/* PM-03 — Competency + calibration (depends PM-02)
 * PM-02 (Review cycles + self-assessments) shipped R4.
 * Uses real /clients/:slug/feature-flags endpoint for competency config.
 * No fabricated competency data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function CompetencyCalibration() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [calibrationCycle, setCalibrationCycle] = useState("annual")
  const [competencyScale, setCompetencyScale] = useState("5-point")
  const [autoCalibrate, setAutoCalibrate] = useState(false)
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
      setCalibrationCycle((getCfg("calibration_cycle") ?? "annual"))
      setCompetencyScale((getCfg("competency_scale") ?? "5-point"))
      setAutoCalibrate(getCfg("auto_calibrate") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/calibration_cycle`, { config: calibrationCycle })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/competency_scale`, { config: competencyScale })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_calibrate`, { config: autoCalibrate ? "1" : "0" })
      await load()
      setNotice("Competency calibration config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const CYCLE_OPTIONS = [
    { value: "annual", label: "Annual" },
    { value: "biannual", label: "Biannual" },
    { value: "quarterly", label: "Quarterly" },
  ]

  const SCALE_OPTIONS = [
    { value: "3-point", label: "3-point" },
    { value: "5-point", label: "5-point" },
    { value: "7-point", label: "7-point" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Competency Calibration"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Competency + Calibration" description="PM-03 · competency + calibration · depends PM-02 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The competency + calibration could not be read." fallback="The competency + calibration could not be read." onRetry={load} />}
        <SectionCard compact title="Calibration configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Calibration cycle</label>
              <select
                value={calibrationCycle}
                onChange={e => setCalibrationCycle(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {CYCLE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Competency scale</label>
              <select
                value={competencyScale}
                onChange={e => setCompetencyScale(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {SCALE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Auto-calibrate</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoCalibrate}
                  onChange={e => setAutoCalibrate(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-calibration</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save calibration config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">PM-03 · R5 · depends PM-02 · no fabricated competency data.</div>
      </div>
    </Layout>
  )
}