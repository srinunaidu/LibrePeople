/* AN-01 — Headcount/hiring/turnover/labour-cost (depends HR-01)
 * HR-01 (Employee master) shipped R2.
 * Uses real /clients/{id}/feature-flags endpoint for headcount config.
 * No fabricated headcount data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function HeadcountCost() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [headcount, setHeadcount] = useState(0)
  const [hiring, setHiring] = useState(0)
  const [turnover, setTurnover] = useState(0)
  const [labourCost, setLabourCost] = useState(0)
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
      setHeadcount(Number(getCfg("headcount") ?? 0))
      setHiring(Number(getCfg("hiring") ?? 0))
      setTurnover(Number(getCfg("turnover") ?? 0))
      setLabourCost(Number(getCfg("labour_cost") ?? getCfg("labor_cost") ?? 0))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/headcount`, { config: String(headcount) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/hiring`, { config: String(hiring) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/turnover`, { config: String(turnover) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/labour_cost`, { config: String(labourCost) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/labor_cost`, { config: String(labourCost) })
      await load()
      setNotice("Headcount / labour cost saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="Headcount/Hiring/Turnover/Labour Cost"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
      <>
    <PageHeader compact title="Headcount + Hiring + Turnover + Labour Cost" description="AN-01 · headcount/hiring/turnover/labour-cost · depends HR-01 (shipped R2) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The headcount + hiring + turnover + labour cost could not be read." fallback="The headcount + hiring + turnover + labour cost could not be read." onRetry={load} />}
        <SectionCard compact title="Headcount configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Headcount</label>
              <Input value={headcount} onChange={e => setHeadcount(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Hiring</label>
              <Input value={hiring} onChange={e => setHiring(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Turnover</label>
              <Input value={turnover} onChange={e => setTurnover(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Labour cost</label>
              <Input value={labourCost} onChange={e => setLabourCost(Number(e.target.value) || 0)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save headcount"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">AN-01 · R3 · depends HR-01 · no fabricated headcount data.</div>
      </div>
  </>)
}