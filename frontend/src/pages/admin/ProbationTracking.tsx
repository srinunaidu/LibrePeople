/* OB-04 — Probation tracking + confirmation (depends OB-02 + HR-02)
 * OB-02 (Information collection) shipped R5. HR-02 (Employment status) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for probation config.
 * No fabricated probation data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function ProbationTracking() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [probationPeriod, setProbationPeriod] = useState(90)
  const [autoConfirm, setAutoConfirm] = useState(false)
  const [reviewFrequency, setReviewFrequency] = useState("monthly")
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
      setProbationPeriod(Number(getCfg("probation_period") ?? 90))
      setAutoConfirm(getCfg("auto_confirm") === "1")
      setReviewFrequency((getCfg("review_frequency") ?? "monthly"))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/probation_period`, { config: String(probationPeriod) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_confirm`, { config: autoConfirm ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/review_frequency`, { config: reviewFrequency })
      await load()
      setNotice("Probation tracking config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const REVIEW_OPTIONS = [
    { value: "monthly", label: "Monthly" },
    { value: "quarterly", label: "Quarterly" },
    { value: "biweekly", label: "Biweekly" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Probation Tracking"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Probation Tracking + Confirmation" description="OB-04 · probation tracking + confirmation · depends OB-02 (shipped R5) + HR-02 (shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The probation tracking + confirmation could not be read." fallback="The probation tracking + confirmation could not be read." onRetry={load} />}
        <SectionCard compact title="Probation configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Probation period (days)</label>
              <Input value={probationPeriod} onChange={e => setProbationPeriod(Number(e.target.value) || 90)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Review frequency</label>
              <select
                value={reviewFrequency}
                onChange={e => setReviewFrequency(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {REVIEW_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Auto-confirm</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoConfirm}
                  onChange={e => setAutoConfirm(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-confirm</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save probation config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">OB-04 · R5 · depends OB-02 + HR-02 · no fabricated probation data.</div>
      </div>
    </Layout>
  )
}