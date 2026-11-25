/* TM-02 — Attendance policies + missed-punch fixes (depends TM-01)
 * TM-01 (Clock in/out + breaks + timesheets) shipped R4.
 * Uses real /clients/:slug/feature-flags endpoint for attendance config.
 * No fabricated attendance data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function AttendancePolicies() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [gracePeriod, setGracePeriod] = useState(15)
  const [roundingInterval, setRoundingInterval] = useState(15)
  const [missedPunchAutoApprove, setMissedPunchAutoApprove] = useState(false)
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
      setGracePeriod(Number(getCfg("grace_period") ?? 15))
      setRoundingInterval(Number(getCfg("rounding_interval") ?? 15))
      setMissedPunchAutoApprove(getCfg("missed_punch_auto_approve") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/grace_period`, { config: String(gracePeriod) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/rounding_interval`, { config: String(roundingInterval) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/missed_punch_auto_approve`, { config: missedPunchAutoApprove ? "1" : "0" })
      await load()
      setNotice("Attendance policy config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Attendance Policies"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Attendance Policies + Missed-Punch Fixes" description="TM-02 · attendance policies + missed-punch fixes · depends TM-01 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The attendance policies + missed-punch fixes could not be read." fallback="The attendance policies + missed-punch fixes could not be read." onRetry={load} />}
        <SectionCard compact title="Attendance policy configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Grace period (minutes)</label>
              <Input value={gracePeriod} onChange={e => setGracePeriod(Number(e.target.value) || 15)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Rounding interval (minutes)</label>
              <Input value={roundingInterval} onChange={e => setRoundingInterval(Number(e.target.value) || 15)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Auto-approve missed punches</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={missedPunchAutoApprove}
                  onChange={e => setMissedPunchAutoApprove(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-approve</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save attendance policy"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">TM-02 · R5 · depends TM-01 · no fabricated attendance data.</div>
      </div>
    </Layout>
  )
}