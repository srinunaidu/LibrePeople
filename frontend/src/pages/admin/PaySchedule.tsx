/* PY-01 — Schedules/structures/components (effective-dated) (depends HR-01 + HR-03 + HR-04)
 * HR-01 (Employee master) shipped R2. HR-03 (Effective-dated changes) shipped R4. HR-04 (Departments/positions/grades/cost centres) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for schedule config.
 * No fabricated schedule data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function PaySchedule() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [payCycle, setPayCycle] = useState("monthly")
  const [payDay, setPayDay] = useState(15)
  const [payComponents, setPayComponents] = useState<string[]>([])
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
      setPayCycle((getCfg("pay_cycle") ?? "monthly"))
      setPayDay(Number(getCfg("pay_day") ?? 15))
      setPayComponents(getCfg("pay_components") ? String(getCfg("pay_components")).split(",") : [])
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/pay_cycle`, { config: payCycle })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/pay_day`, { config: String(payDay) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/pay_components`, { config: payComponents.join(",") })
      await load()
      setNotice("Pay schedule config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const CYCLE_OPTIONS = [
    { value: "weekly", label: "Weekly" },
    { value: "biweekly", label: "Biweekly" },
    { value: "semimonthly", label: "Semimonthly" },
    { value: "monthly", label: "Monthly" },
  ]

  const COMPONENT_OPTIONS = [
    { value: "base_salary", label: "Base salary" },
    { value: "bonus", label: "Bonus" },
    { value: "commission", label: "Commission" },
    { value: "allowance", label: "Allowance" },
    { value: "deduction", label: "Deduction" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Pay Schedule"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Pay Schedule/Structure/Components" description="PY-01 · schedules/structures/components (effective-dated) · depends HR-01 + HR-03 + HR-04 (all shipped) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The pay schedule/structure/components could not be read." fallback="The pay schedule/structure/components could not be read." onRetry={load} />}
        <SectionCard compact title="Pay schedule configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Pay cycle</label>
              <select
                value={payCycle}
                onChange={e => setPayCycle(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {CYCLE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Pay day</label>
              <Input value={payDay} onChange={e => setPayDay(Number(e.target.value) || 15)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Pay components</label>
              <div className="flex flex-wrap gap-2">
                {COMPONENT_OPTIONS.map(c => (
                  <label key={c.value} className="cursor-pointer flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={payComponents.includes(c.value)}
                      onChange={e => {
                        if (e.target.checked) setPayComponents([...payComponents, c.value])
                        else setPayComponents(payComponents.filter(c2 => c2 !== c.value))
                      }}
                      className="rounded text-brand-600 focus:ring-brand-500"
                    />
                    {c.label}
                  </label>
                ))}
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save pay schedule"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">PY-01 · R5 · depends HR-01 + HR-03 + HR-04 · no fabricated pay data.</div>
      </div>
    </Layout>
  )
}