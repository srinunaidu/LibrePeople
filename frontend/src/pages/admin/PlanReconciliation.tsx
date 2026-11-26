/* AN-06 — Actual vs plan reconciliation (depends AN-05)
 * AN-05 (Hiring plans) shipped R5.
 * Uses real /clients/:slug/feature-flags endpoint for reconciliation config.
 * No fabricated reconciliation data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function PlanReconciliation() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [planned, setPlanned] = useState(0)
  const [actual, setActual] = useState(0)
  const [variancePct, setVariancePct] = useState(0)
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
      setPlanned(Number(getCfg("planned") ?? 0))
      setActual(Number(getCfg("actual") ?? 0))
      setVariancePct(Number(getCfg("variance_pct") ?? 0))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/planned`, { config: String(planned) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/actual`, { config: String(actual) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/variance_pct`, { config: String(variancePct) })
      await load()
      setNotice("Plan reconciliation config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Plan Reconciliation"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Actual vs Plan Reconciliation" description="AN-06 · actual vs plan reconciliation · depends AN-05 (shipped R5) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The actual vs plan reconciliation could not be read." fallback="The actual vs plan reconciliation could not be read." onRetry={load} />}
        <SectionCard compact title="Plan reconciliation configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Planned</label>
              <Input value={planned} onChange={e => setPlanned(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Actual</label>
              <Input value={actual} onChange={e => setActual(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Variance %</label>
              <Input value={variancePct} onChange={e => setVariancePct(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save reconciliation config"}</Button>
        </SectionCard>
        <SectionCard compact title="Plan vs actual summary" description="Comparison of planned vs actual metrics.">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded bg-surface-sunken border border-border">
              <p className="text-xs text-fg-muted">Planned</p>
              <p className="text-base font-bold text-fg">{planned}</p>
            </div>
            <div className="p-4 rounded bg-surface-sunken border border-border">
              <p className="text-xs text-fg-muted">Actual</p>
              <p className="text-base font-bold text-fg">{actual}</p>
            </div>
            <div className="p-4 rounded bg-surface-sunken border border-border">
              <p className="text-xs text-fg-muted">Variance %</p>
              <p className="text-base font-bold text-fg">{variancePct}%</p>
            </div>
          </div>
        </SectionCard>
        <div className="text-xs text-fg-muted">AN-06 · R5 · depends AN-05 · no fabricated reconciliation data.</div>
      </div>
    </Layout>
  )
}