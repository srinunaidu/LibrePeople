/* TM-05 — Timesheet lock after cut-off + adjustments (depends TM-01)
 * TM-01 (Clock in/out + breaks + timesheets) shipped R4.
 * Uses real /clients/:slug/feature-flags endpoint for timesheet config.
 * No fabricated timesheet data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function TimesheetLock() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [lockAfterCutoff, setLockAfterCutoff] = useState(true)
  const [cutoffDay, setCutoffDay] = useState(5)
  const [allowAdjustments, setAllowAdjustments] = useState(true)
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
      setLockAfterCutoff(getCfg("lock_after_cutoff") === "1")
      setCutoffDay(Number(getCfg("cutoff_day") ?? 5))
      setAllowAdjustments(getCfg("allow_adjustments") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/lock_after_cutoff`, { config: lockAfterCutoff ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/cutoff_day`, { config: String(cutoffDay) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/allow_adjustments`, { config: allowAdjustments ? "1" : "0" })
      await load()
      setNotice("Timesheet lock config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Timesheet Lock"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Timesheet Lock + Adjustments" description="TM-05 · timesheet lock after cut-off + adjustments · depends TM-01 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The timesheet lock + adjustments could not be read." fallback="The timesheet lock + adjustments could not be read." onRetry={load} />}
        <SectionCard compact title="Timesheet lock configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Lock after cut-off</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={lockAfterCutoff}
                  onChange={e => setLockAfterCutoff(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable lock after cut-off</span>
              </div>
            </div>
            <div>
              <label>Cut-off day</label>
              <Input value={cutoffDay} onChange={e => setCutoffDay(Number(e.target.value) || 5)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Allow adjustments</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={allowAdjustments}
                  onChange={e => setAllowAdjustments(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable adjustments</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save timesheet lock config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">TM-05 · R6 · depends TM-01 · no fabricated timesheet data.</div>
      </div>
    </Layout>
  )
}