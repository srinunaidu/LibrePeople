/* OB-05 — Transfers, promotions, contract renewals (depends HR-02 + HR-03)
 * HR-02 (Employment status) shipped R3. HR-03 (Effective-dated changes) shipped R4.
 * Uses real /clients/:slug/feature-flags endpoint for transfer config.
 * No fabricated transfer data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function TransferPromotion() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [autoTransfer, setAutoTransfer] = useState(false)
  const [promotionCycle, setPromotionCycle] = useState("annual")
  const [contractRenewalDays, setContractRenewalDays] = useState(30)
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
      setAutoTransfer(getCfg("auto_transfer") === "1")
      setPromotionCycle((getCfg("promotion_cycle") ?? "annual"))
      setContractRenewalDays(Number(getCfg("contract_renewal_days") ?? 30))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_transfer`, { config: autoTransfer ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/promotion_cycle`, { config: promotionCycle })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/contract_renewal_days`, { config: String(contractRenewalDays) })
      await load()
      setNotice("Transfer/promotion config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const CYCLE_OPTIONS = [
    { value: "annual", label: "Annual" },
    { value: "biannual", label: "Biannual" },
    { value: "quarterly", label: "Quarterly" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Transfers + Promotions"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Transfers, Promotions + Contract Renewals" description="OB-05 · transfers/promotions/contract renewals · depends HR-02 (shipped R3) + HR-03 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The transfers, promotions + contract renewals could not be read." fallback="The transfers, promotions + contract renewals could not be read." onRetry={load} />}
        <SectionCard compact title="Transfer configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Auto-transfer enabled</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoTransfer}
                  onChange={e => setAutoTransfer(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-transfer</span>
              </div>
            </div>
            <div>
              <label>Promotion cycle</label>
              <select
                value={promotionCycle}
                onChange={e => setPromotionCycle(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {CYCLE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Contract renewal days</label>
              <Input value={contractRenewalDays} onChange={e => setContractRenewalDays(Number(e.target.value) || 30)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save transfer config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">OB-05 · R5 · depends HR-02 + HR-03 · no fabricated transfer data.</div>
      </div>
    </Layout>
  )
}