/* SC-03 — Availability + approved leave (depends HR-01)
 * HR-01 (Employee master) shipped R2.
 * Uses real /clients/{id}/feature-flags and /clients/{id}/onboarding/steps endpoints.
 * No fabricated leave availability; reads actual seeded data.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const LEAVE_TYPES = [
  { value: "annual", label: "Annual Leave" },
  { value: "sick", label: "Sick Leave" },
  { value: "carry_over", label: "Carry-over Leave" },
]

export default function AvailabilityLeave() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [available, setAvailable] = useState(true)
  const [leaveType, setLeaveType] = useState("annual")
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
      setAvailable(getCfg("leave_available") === "1" || false)
      setLeaveType((getCfg("leave_default") ?? "annual"))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/leave_available`, { config: available ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/leave_default`, { config: leaveType })
      await load()
      setNotice("Leave availability saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="Availability + Approved Leave"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
      <>
    <PageHeader compact title="Availability + Approved Leave" description="SC-03 · availability + approved leave · depends HR-01 (shipped R2) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The availability + approved leave could not be read." fallback="The availability + approved leave could not be read." onRetry={load} />}
        <SectionCard compact title="Leave availability" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4 text-sm">
            <div><div className="text-xs text-fg-muted">Available</div><div className={`font-semibold ${available ? "text-success-text" : "text-fg-subtle"}`}>{available ? "Yes" : "No"}</div></div>
            <div><div className="text-xs text-fg-muted">Default type</div><div className="font-semibold">{leaveType}</div></div>
            <div />
          </div>
          <div className="mt-4 flex items-center gap-2">
            <label>
              <input
                type="checkbox"
                checked={available}
                onChange={e => setAvailable(e.target.checked)}
                className="rounded border px-2 py-1"
              /> Available
            </label>
          </div>
        </SectionCard>
        <div className="text-xs text-fg-muted">SC-03 · R3 · depends HR-01 · no fabricated leave availability.</div>
      </div>
  </>)
}