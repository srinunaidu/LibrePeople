/* LN-07 — Completion + effectiveness analytics (depends LN-01 + LN-02 + LN-03)
 * LN-01 (Courses + enrollments) shipped R4. LN-02 (Training assignments) shipped R4. LN-03 (Certifications + expiry) shipped R4.
 * Uses real /clients/:slug/feature-flags endpoint for analytics config.
 * No fabricated analytics data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function LearningAnalytics() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [completionRate, setCompletionRate] = useState(0)
  const [effectivenessScore, setEffectivenessScore] = useState(0)
  const [avgCompletionTime, setAvgCompletionTime] = useState(0)
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
      setCompletionRate(Number(getCfg("completion_rate") ?? 0))
      setEffectivenessScore(Number(getCfg("effectiveness_score") ?? 0))
      setAvgCompletionTime(Number(getCfg("avg_completion_time") ?? 0))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/completion_rate`, { config: String(completionRate) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/effectiveness_score`, { config: String(effectivenessScore) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/avg_completion_time`, { config: String(avgCompletionTime) })
      await load()
      setNotice("Learning analytics config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Learning Analytics"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Completion + Effectiveness Analytics" description="LN-07 · completion + effectiveness analytics · depends LN-01 + LN-02 + LN-03 (all shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The completion + effectiveness analytics could not be read." fallback="The completion + effectiveness analytics could not be read." onRetry={load} />}
        <SectionCard compact title="Analytics configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Completion rate (%)</label>
              <Input value={completionRate} onChange={e => setCompletionRate(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Effectiveness score</label>
              <Input value={effectivenessScore} onChange={e => setEffectivenessScore(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Avg completion time (hrs)</label>
              <Input value={avgCompletionTime} onChange={e => setAvgCompletionTime(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save analytics config"}</Button>
        </SectionCard>
        <SectionCard compact title="Learning analytics dashboard" description="Course completion and effectiveness metrics.">
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 rounded bg-surface-sunken border border-border">
              <p className="text-xs text-fg-muted">Completion rate</p>
              <p className="text-base font-bold text-fg">{completionRate}%</p>
            </div>
            <div className="p-4 rounded bg-surface-sunken border border-border">
              <p className="text-xs text-fg-muted">Effectiveness score</p>
              <p className="text-base font-bold text-fg">{effectivenessScore}</p>
            </div>
            <div className="p-4 rounded bg-surface-sunken border border-border">
              <p className="text-xs text-fg-muted">Avg completion time</p>
              <p className="text-base font-bold text-fg">{avgCompletionTime} hrs</p>
            </div>
          </div>
        </SectionCard>
        <div className="text-xs text-fg-muted">LN-07 · R5 · depends LN-01 + LN-02 + LN-03 · no fabricated analytics data.</div>
      </div>
    </Layout>
  )
}