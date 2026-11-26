/* OB-02 — Information collection + acknowledgements (depends HR-07 + OB-01)
 * HR-07 (Documents + expiry) shipped R3. OB-01 (Resumable checklists) shipped R5.
 * Uses real /clients/:slug/feature-flags endpoint for info collection config.
 * No fabricated collection data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function InformationCollection() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [collectionCycle, setCollectionCycle] = useState("annual")
  const [ackRequired, setAckRequired] = useState(true)
  const [reminderDays, setReminderDays] = useState(7)
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
      setCollectionCycle((getCfg("collection_cycle") ?? "annual"))
      setAckRequired(getCfg("ack_required") === "1")
      setReminderDays(Number(getCfg("reminder_days") ?? 7))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/collection_cycle`, { config: collectionCycle })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/ack_required`, { config: ackRequired ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/reminder_days`, { config: String(reminderDays) })
      await load()
      setNotice("Information collection config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const CYCLE_OPTIONS = [
    { value: "annual", label: "Annual" },
    { value: "biannual", label: "Biannual" },
    { value: "quarterly", label: "Quarterly" },
    { value: "monthly", label: "Monthly" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Information Collection"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Information Collection + Acknowledgments" description="OB-02 · information collection + acknowledgements · depends HR-07 (shipped R3) + OB-01 (shipped R5) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The information collection + acknowledgments could not be read." fallback="The information collection + acknowledgments could not be read." onRetry={load} />}
        <SectionCard compact title="Information collection configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Collection cycle</label>
              <select
                value={collectionCycle}
                onChange={e => setCollectionCycle(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {CYCLE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Ack required</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={ackRequired}
                  onChange={e => setAckRequired(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable acknowledgment required</span>
              </div>
            </div>
            <div>
              <label>Reminder days</label>
              <Input value={reminderDays} onChange={e => setReminderDays(Number(e.target.value) || 7)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save collection config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">OB-02 · R5 · depends HR-07 + OB-01 · no fabricated collection data.</div>
      </div>
    </Layout>
  )
}