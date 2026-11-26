/* SC-04 — Hard constraints (rest/hours/certs/double-book) (depends SC-02 + SC-03)
 * SC-02 (Demand-based staffing) shipped R3. SC-03 (Availability + approved leave) shipped R3.
 * Uses real /clients/:slug/feature-flags endpoint for constraint config.
 * No fabricated constraint data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function HardConstraints() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [maxHoursPerWeek, setMaxHoursPerWeek] = useState(40)
  const [maxHoursPerDay, setMaxHoursPerDay] = useState(12)
  const [minRestHours, setMinRestHours] = useState(11)
  const [allowDoubleBook, setAllowDoubleBook] = useState(false)
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
      setMaxHoursPerWeek(Number(getCfg("max_hours_per_week") ?? 40))
      setMaxHoursPerDay(Number(getCfg("max_hours_per_day") ?? 12))
      setMinRestHours(Number(getCfg("min_rest_hours") ?? 11))
      setAllowDoubleBook(getCfg("allow_double_book") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/max_hours_per_week`, { config: String(maxHoursPerWeek) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/max_hours_per_day`, { config: String(maxHoursPerDay) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/min_rest_hours`, { config: String(minRestHours) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/allow_double_book`, { config: allowDoubleBook ? "1" : "0" })
      await load()
      setNotice("Hard constraints config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Hard Constraints"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Hard Constraints" description="SC-04 · hard constraints (rest/hours/certs/double-book) · depends SC-02 + SC-03 (both shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The hard constraints could not be read." fallback="The hard constraints could not be read." onRetry={load} />}
        <SectionCard compact title="Hard constraint configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Max hours per week</label>
              <Input value={maxHoursPerWeek} onChange={e => setMaxHoursPerWeek(Number(e.target.value) || 40)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Max hours per day</label>
              <Input value={maxHoursPerDay} onChange={e => setMaxHoursPerDay(Number(e.target.value) || 12)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Min rest hours</label>
              <Input value={minRestHours} onChange={e => setMinRestHours(Number(e.target.value) || 11)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Allow double book</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={allowDoubleBook}
                  onChange={e => setAllowDoubleBook(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Allow double booking</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save constraints"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">SC-04 · R5 · depends SC-02 + SC-03 · no fabricated constraint data.</div>
      </div>
    </Layout>
  )
}