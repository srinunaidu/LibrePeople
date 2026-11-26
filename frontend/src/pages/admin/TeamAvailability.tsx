/* LV-04 — Team availability + absence calendars (depends LV-03 + HR-09)
 * LV-03 (Leave types) shipped R4. HR-09 (Manager assignments) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for availability config.
 * No fabricated availability data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function TeamAvailability() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [availabilityWindow, setAvailabilityWindow] = useState(30)
  const [absenceNotification, setAbsenceNotification] = useState(true)
  const [calendarSync, setCalendarSync] = useState(true)
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
      setAvailabilityWindow(Number(getCfg("availability_window") ?? 30))
      setAbsenceNotification(getCfg("absence_notification") === "1")
      setCalendarSync(getCfg("calendar_sync") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/availability_window`, { config: String(availabilityWindow) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/absence_notification`, { config: absenceNotification ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/calendar_sync`, { config: calendarSync ? "1" : "0" })
      await load()
      setNotice("Availability config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Team Availability"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Team Availability + Absence Calendars" description="LV-04 · team availability + absence calendars · depends LV-03 (shipped R4) + HR-09 (shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The team availability + absence calendars could not be read." fallback="The team availability + absence calendars could not be read." onRetry={load} />}
        <SectionCard compact title="Availability configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Availability window (days)</label>
              <Input value={availabilityWindow} onChange={e => setAvailabilityWindow(Number(e.target.value) || 30)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Absence notification</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={absenceNotification}
                  onChange={e => setAbsenceNotification(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable absence notification</span>
              </div>
            </div>
            <div>
              <label>Calendar sync</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={calendarSync}
                  onChange={e => setCalendarSync(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable calendar sync</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save availability config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">LV-04 · R5 · depends LV-03 + HR-09 · no fabricated availability data.</div>
      </div>
    </Layout>
  )
}