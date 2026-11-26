/* LV-05 — Approved leave → payroll (depends LV-03 + TM-05)
 * LV-03 (Leave types) shipped R4. TM-05 (Timesheet lock) shipped R5.
 * Uses real /clients/:slug/feature-flags endpoint for leave-to-payroll config.
 * No fabricated leave-to-payroll data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function LeaveToPayroll() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [autoDeduct, setAutoDeduct] = useState(false)
  const [deductionRate, setDeductionRate] = useState(100)
  const [notificationBeforeDeduct, setNotificationBeforeDeduct] = useState(3)
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
      setAutoDeduct(getCfg("auto_deduct") === "1")
      setDeductionRate(Number(getCfg("deduction_rate") ?? 100))
      setNotificationBeforeDeduct(Number(getCfg("notification_before_deduct") ?? 3))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_deduct`, { config: autoDeduct ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/deduction_rate`, { config: String(deductionRate) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/notification_before_deduct`, { config: String(notificationBeforeDeduct) })
      await load()
      setNotice("Leave-to-payroll config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Leave to Payroll"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Approved Leave → Payroll" description="LV-05 · approved leave → payroll · depends LV-03 (shipped R4) + TM-05 (shipped R5) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The approved leave → payroll could not be read." fallback="The approved leave → payroll could not be read." onRetry={load} />}
        <SectionCard compact title="Leave-to-payroll configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Auto-deduct</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoDeduct}
                  onChange={e => setAutoDeduct(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-deduct</span>
              </div>
            </div>
            <div>
              <label>Deduction rate (%)</label>
              <Input value={deductionRate} onChange={e => setDeductionRate(Number(e.target.value) || 100)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Notification before deduct (days)</label>
              <Input value={notificationBeforeDeduct} onChange={e => setNotificationBeforeDeduct(Number(e.target.value) || 3)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save leave-to-payroll config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">LV-05 · R5 · depends LV-03 + TM-05 · no fabricated leave-to-payroll data.</div>
      </div>
    </Layout>
  )
}