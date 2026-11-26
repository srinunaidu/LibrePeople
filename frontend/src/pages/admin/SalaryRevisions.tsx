/* PY-06 — Salary revisions + total-cost statements (depends PY-01 + PY-10 + PM-02)
 * PY-01 (Schedules/structures/components) shipped R5. PY-10 (Generic calc separated from verified statutory) not yet shipped. PM-02 (Review cycles + self-assessments) shipped R4.
 * Uses real /clients/:slug/feature-flags endpoint for salary revision config.
 * No fabricated salary data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input, Alert, Button, EmptyState, LoadingRegion, PageHeader, RetryableAlert, SectionCard, TableSkeleton } from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function SalaryRevisions() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [reviewCycle, setReviewCycle] = useState("annual")
  const [autoApply, setAutoApply] = useState(false)
  const [increasePercentage, setIncreasePercentage] = useState(3)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [error, setError] = useState<unknown>(null)

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
      setReviewCycle((getCfg("review_cycle") ?? "annual"))
      setAutoApply(getCfg("auto_apply") === "1")
      setIncreasePercentage(Number(getCfg("increase_percentage") ?? 3))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return

    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/review_cycle`, { config: reviewCycle })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_apply`, { config: autoApply ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/increase_percentage`, { config: String(increasePercentage) })
      await load()
      setNotice("Salary revision config saved.")
    } catch (e) { setActionError(errorMessage(e, "The salary revision config could not be saved.")) } finally { setSaving(false) }
  }

  const CYCLE_OPTIONS = [
    { value: "annual", label: "Annual" },
    { value: "biannual", label: "Biannual" },
    { value: "quarterly", label: "Quarterly" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Salary revision config requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Salary Revisions"><TableSkeleton rows={4} cols={3} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Salary Revisions + Total-Cost Statements" description="PY-06 · salary revisions + total-cost statements · depends PY-01 (shipped R5) + PY-10 · PM-02 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {error ? <RetryableAlert err={error} title="Could not load salary revisions" fallback="Could not load configuration." onRetry={load} /> : null}
        <SectionCard compact title="Salary revision configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Review cycle</label>
              <select
                value={reviewCycle}
                onChange={e => setReviewCycle(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {CYCLE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Auto-apply</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoApply}
                  onChange={e => setAutoApply(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-apply</span>
              </div>
            </div>
            <div>
              <label>Increase percentage (%)</label>
              <Input value={increasePercentage} onChange={e => setIncreasePercentage(Number(e.target.value) || 3)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save salary revision config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">PY-06 · R6 · depends PY-01 + PY-10 + PM-02 · configuration only; revision-cycle history is not recorded by this screen.</div>
      </div>
    </Layout>
  )
}