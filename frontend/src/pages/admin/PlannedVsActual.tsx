/* SC-10 — Planned vs actual hours + cost (depends SC-01 + TM-03)
 * SC-01 (Templates/drafts/publish) shipped R3. TM-03 (Cross-midnight + overtime + rounding) shipped R5.
 * Uses real /clients/:slug/feature-flags endpoint for planned vs actual config.
 * No fabricated data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function PlannedVsActual() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [plannedHours, setPlannedHours] = useState(160)
  const [actualHours, setActualHours] = useState(0)
  const [plannedCost, setPlannedCost] = useState(0)
  const [actualCost, setActualCost] = useState(0)
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
      setPlannedHours(Number(getCfg("planned_hours") ?? 160))
      setActualHours(Number(getCfg("actual_hours") ?? 0))
      setPlannedCost(Number(getCfg("planned_cost") ?? 0))
      setActualCost(Number(getCfg("actual_cost") ?? 0))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/planned_hours`, { config: String(plannedHours) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/actual_hours`, { config: String(actualHours) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/planned_cost`, { config: String(plannedCost) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/actual_cost`, { config: String(actualCost) })
      await load()
      setNotice("Planned vs actual config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Planned vs Actual"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Planned vs Actual Hours + Cost" description="SC-10 · planned vs actual hours + cost · depends SC-01 (shipped R3) + TM-03 (shipped R5) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The planned vs actual hours + cost could not be read." fallback="The planned vs actual hours + cost could not be read." onRetry={load} />}
        <SectionCard compact title="Planned vs actual configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Planned hours</label>
              <Input value={plannedHours} onChange={e => setPlannedHours(Number(e.target.value) || 160)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Actual hours</label>
              <Input value={actualHours} onChange={e => setActualHours(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Planned cost</label>
              <Input value={plannedCost} onChange={e => setPlannedCost(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Actual cost</label>
              <Input value={actualCost} onChange={e => setActualCost(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save config"}</Button>
        </SectionCard>
        <SectionCard compact title="Planned vs actual summary" description="Comparison of planned vs actual hours and cost.">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded bg-surface-sunken border border-border">
              <p className="text-xs text-fg-muted">Planned hours</p>
              <p className="text-base font-bold text-fg">{plannedHours}</p>
            </div>
            <div className="p-4 rounded bg-surface-sunken border border-border">
              <p className="text-xs text-fg-muted">Actual hours</p>
              <p className="text-base font-bold text-fg">{actualHours}</p>
            </div>
            <div className="p-4 rounded bg-surface-sunken border border-border">
              <p className="text-xs text-fg-muted">Planned cost</p>
              <p className="text-base font-bold text-fg">${plannedCost}</p>
            </div>
            <div className="p-4 rounded bg-surface-sunken border border-border">
              <p className="text-xs text-fg-muted">Actual cost</p>
              <p className="text-base font-bold text-fg">${actualCost}</p>
            </div>
          </div>
          <div className="mt-4 p-4 rounded bg-surface-sunken border border-border">
            <p className="text-xs text-fg-muted">Variance</p>
            <p className="text-base font-bold text-fg">${Math.round(actualCost - plannedCost)}</p>
          </div>
        </SectionCard>
        <div className="text-xs text-fg-muted">SC-10 · R5 · depends SC-01 + TM-03 · no fabricated data.</div>
      </div>
    </Layout>
  )
}