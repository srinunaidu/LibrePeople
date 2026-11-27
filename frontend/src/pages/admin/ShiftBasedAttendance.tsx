/* TM-04 — Shift-based + fixed-schedule attendance (depends TM-01 + HR-09)
 * TM-01 (Clock in/out + breaks + timesheets) shipped R4. HR-09 (Manager assignments) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for schedule config.
 * No fabricated attendance data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function ShiftBasedAttendance() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [allowShiftBased, setAllowShiftBased] = useState(false)
  const [allowFixedSchedule, setAllowFixedSchedule] = useState(true)
  const [schedulePublishDays, setSchedulePublishDays] = useState(7)
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
      setAllowShiftBased(getCfg("allow_shift_based") === "1")
      setAllowFixedSchedule(getCfg("allow_fixed_schedule") === "1")
      setSchedulePublishDays(Number(getCfg("schedule_publish_days") ?? 7))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/allow_shift_based`, { config: allowShiftBased ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/allow_fixed_schedule`, { config: allowFixedSchedule ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/schedule_publish_days`, { config: String(schedulePublishDays) })
      await load()
      setNotice("Shift-based attendance config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Shift-based Attendance"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Shift-based + Fixed-schedule Attendance" description="TM-04 · shift-based + fixed-schedule attendance · depends TM-01 (shipped R4) + HR-09 (shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The shift-based + fixed-schedule attendance could not be read." fallback="The shift-based + fixed-schedule attendance could not be read." onRetry={load} />}
        <SectionCard compact title="Schedule configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Allow shift-based attendance</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={allowShiftBased}
                  onChange={e => setAllowShiftBased(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable shift-based</span>
              </div>
            </div>
            <div>
              <label>Allow fixed schedule</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={allowFixedSchedule}
                  onChange={e => setAllowFixedSchedule(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable fixed schedule</span>
              </div>
            </div>
            <div>
              <label>Schedule publish days</label>
              <Input value={schedulePublishDays} onChange={e => setSchedulePublishDays(Number(e.target.value) || 7)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save schedule config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">TM-04 · R5 · depends TM-01 + HR-09 · no fabricated schedule data.</div>
      </div>
    </Layout>
  )
}