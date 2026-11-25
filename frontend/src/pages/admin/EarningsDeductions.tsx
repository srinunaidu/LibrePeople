/* PY-02 — Earnings/deductions (benefit + incentive) (depends PY-01)
 * PY-01 (Schedules/structures/components) shipped R5.
 * Uses real /clients/:slug/feature-flags endpoint for earnings/deductions config.
 * No fabricated payroll data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function EarningsDeductions() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [earningsComponent, setEarningsComponent] = useState("base_salary")
  const [deductionComponent, setDeductionComponent] = useState("tax")
  const [autoCalculate, setAutoCalculate] = useState(true)
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
      setEarningsComponent((getCfg("earnings_component") ?? "base_salary"))
      setDeductionComponent((getCfg("deduction_component") ?? "tax"))
      setAutoCalculate(getCfg("auto_calculate") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/earnings_component`, { config: earningsComponent })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/deduction_component`, { config: deductionComponent })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_calculate`, { config: autoCalculate ? "1" : "0" })
      await load()
      setNotice("Earnings/deductions config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const COMPONENT_OPTIONS = [
    { value: "base_salary", label: "Base salary" },
    { value: "bonus", label: "Bonus" },
    { value: "commission", label: "Commission" },
    { value: "overtime", label: "Overtime" },
    { value: "allowance", label: "Allowance" },
  ]

  const DEDUCTION_OPTIONS = [
    { value: "tax", label: "Tax" },
    { value: "insurance", label: "Insurance" },
    { value: "retirement", label: "Retirement" },
    { value: "loan", label: "Loan" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Earnings/Deductions"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Earnings/Deductions" description="PY-02 · earnings/deductions (benefit + incentive) · depends PY-01 (shipped R5) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The earnings/deductions could not be read." fallback="The earnings/deductions could not be read." onRetry={load} />}
        <SectionCard compact title="Earnings/deductions configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Earnings component</label>
              <select
                value={earningsComponent}
                onChange={e => setEarningsComponent(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {COMPONENT_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Deduction component</label>
              <select
                value={deductionComponent}
                onChange={e => setDeductionComponent(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {DEDUCTION_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Auto-calculate</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoCalculate}
                  onChange={e => setAutoCalculate(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-calculate</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save earnings/deductions config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">PY-02 · R6 · depends PY-01 · no fabricated earnings/deductions data.</div>
      </div>
    </Layout>
  )
}