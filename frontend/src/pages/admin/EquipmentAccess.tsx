/* OB-03 — Equipment/access/training tasks + owners (depends OB-01 + HR-09)
 * OB-01 (Resumable checklists) shipped R5. HR-09 (Manager assignments) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for equipment config.
 * No fabricated equipment data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function EquipmentAccess() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [autoAssign, setAutoAssign] = useState(true)
  const [equipmentTypes, setEquipmentTypes] = useState<string[]>([])
  const [accessReviewDays, setAccessReviewDays] = useState(30)
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
      setAutoAssign(getCfg("auto_assign") === "1")
      setEquipmentTypes(getCfg("equipment_types") ? String(getCfg("equipment_types")).split(",") : [])
      setAccessReviewDays(Number(getCfg("access_review_days") ?? 30))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_assign`, { config: autoAssign ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/equipment_types`, { config: equipmentTypes.join(",") })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/access_review_days`, { config: String(accessReviewDays) })
      await load()
      setNotice("Equipment/access config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const EQUIPMENT_TYPES = [
    { value: "laptop", label: "Laptop" },
    { value: "monitor", label: "Monitor" },
    { value: "phone", label: "Phone" },
    { value: "badge", label: "Access badge" },
    { value: "keys", label: "Office keys" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Equipment Access"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Equipment/Access/Training Tasks + Owners" description="OB-03 · equipment/access/training tasks + owners · depends OB-01 (shipped R5) + HR-09 (shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The equipment/access/training tasks + owners could not be read." fallback="The equipment/access/training tasks + owners could not be read." onRetry={load} />}
        <SectionCard compact title="Equipment configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Auto-assign</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoAssign}
                  onChange={e => setAutoAssign(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-assign</span>
              </div>
            </div>
            <div>
              <label>Access review days</label>
              <Input value={accessReviewDays} onChange={e => setAccessReviewDays(Number(e.target.value) || 30)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Equipment types</label>
              <div className="flex flex-wrap gap-2">
                {EQUIPMENT_TYPES.map(e => (
                  <label key={e.value} className="cursor-pointer flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={equipmentTypes.includes(e.value)}
                      onChange={e => {
                        const input = e.target as HTMLInputElement
                        if (input.checked) setEquipmentTypes([...equipmentTypes, input.value])
                        else setEquipmentTypes(equipmentTypes.filter(t => t !== input.value))
                      }}
                      className="rounded text-brand-600 focus:ring-brand-500"
                    />
                    {e.label}
                  </label>
                ))}
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save equipment config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">OB-03 · R5 · depends OB-01 + HR-09 · no fabricated equipment data.</div>
      </div>
    </Layout>
  )
}