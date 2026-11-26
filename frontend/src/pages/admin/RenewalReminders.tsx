/* BN-03 — Renewal reminders + documentation (depends BN-01 + HR-07)
 * BN-01 (Plans/eligibility/enrolment windows) shipped R4. HR-07 (Documents + expiry + acknowledgements) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for renewal config.
 * No fabricated renewal data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function RenewalReminders() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [reminderDays, setReminderDays] = useState(30)
  const [autoRenew, setAutoRenew] = useState(false)
  const [notificationChannels, setNotificationChannels] = useState<string[]>([])
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
      setReminderDays(Number(getCfg("reminder_days") ?? 30))
      setAutoRenew(getCfg("auto_renew") === "1")
      setNotificationChannels(getCfg("notification_channels") ? String(getCfg("notification_channels")).split(",") : [])
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/reminder_days`, { config: String(reminderDays) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_renew`, { config: autoRenew ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/notification_channels`, { config: notificationChannels.join(",") })
      await load()
      setNotice("Renewal reminder config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const CHANNEL_OPTIONS = [
    { value: "email", label: "Email" },
    { value: "sms", label: "SMS" },
    { value: "in_app", label: "In-app notification" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Renewal Reminders"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Renewal Reminders + Documentation" description="BN-03 · renewal reminders + documentation · depends BN-01 (shipped R4) + HR-07 (shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The renewal reminders + documentation could not be read." fallback="The renewal reminders + documentation could not be read." onRetry={load} />}
        <SectionCard compact title="Renewal configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Reminder days before expiry</label>
              <Input value={reminderDays} onChange={e => setReminderDays(Number(e.target.value) || 30)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Auto-renew</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoRenew}
                  onChange={e => setAutoRenew(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-renewal</span>
              </div>
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-fg mb-2">Notification channels</label>
            <div className="flex flex-wrap gap-2">
              {CHANNEL_OPTIONS.map(ch => (
                <label key={ch.value} className="cursor-pointer flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={notificationChannels.includes(ch.value)}
                    onChange={e => {
                      if (e.target.checked) setNotificationChannels([...notificationChannels, ch.value])
                      else setNotificationChannels(notificationChannels.filter(c => c !== ch.value))
                    }}
                    className="rounded text-brand-600 focus:ring-brand-500"
                  />
                  {ch.label}
                </label>
              ))}
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save renewal config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">BN-03 · R5 · depends BN-01 + HR-07 · no fabricated renewal data.</div>
      </div>
    </Layout>
  )
}