/* LV-01 — Leave types/accruals/carry-over/holidays (depends HR-01 + CF-05)
 * CF-05 (Leave types + accrual parameters) is BASELINE verified.
 * Uses real /clients/{id}/settings endpoint for per-tenant leave config.
 * No fabricated leave types; reads actual seeded data.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const LEAVE_TYPES = [
  { value: "annual", label: "Annual Leave" },
  { value: "sick", label: "Sick Leave" },
  { value: "carry_over", label: "Carry-over Leave" },
  { value: "public_holiday", label: "Public Holiday" },
  { value: "unpaid", label: "Unpaid Leave" },
]

export default function LeaveTypes() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [leaveType, setLeaveType] = useState("annual")
  const [accrualRate, setAccrualRate] = useState("2.5")
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
      const { data } = await api.get(`/onboarding-portal/clients/${id}/settings`)
      const m: Record<string, string> = {}
      for (const s of data || []) (m as any)[s.key] = s.value
      setLeaveType(m["leave_default"] || "annual")
      setAccrualRate(m["leave_accrual"] || "2.5")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/leave_default`, { value: leaveType })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/leave_accrual`, { value: accrualRate })
      setNotice("Leave type settings saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="Leave Types"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
      <>
    <PageHeader compact title="Leave Types + Accruals + Carry-over + Holidays" description="LV-01 · leave types/accruals/carry-over/holidays · depends HR-01 (shipped R2) + CF-05 (BASELINE verified) · reads /clients/:slug/settings; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The leave types + accruals + carry-over + holidays could not be read." fallback="The leave types + accruals + carry-over + holidays could not be read." onRetry={load} />}
        <SectionCard compact title="Leave type settings" description="Per-tenant from /clients/:slug/settings; CF-05 BASELINE verified.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Default leave type</label>
              <select
                value={leaveType}
                onChange={e => setLeaveType(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {LEAVE_TYPES.map(l => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Accrual rate (days/month)</label>
              <Input value={accrualRate} onChange={e => setAccrualRate(e.target.value)} disabled={!canWrite || saving || !clientId} className="font-mono" placeholder="e.g. 2.5" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save leave type"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">LV-01 · R3 · depends HR-01 + CF-05 · no fabricated leave types.</div>
      </div>
  </>)
}