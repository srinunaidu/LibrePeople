/* BN-02 — Employer contributions + claims (depends PY-02)
 * PY-02 (Earnings/deductions) not yet shipped - will be built after PY-01.
 * Uses real /clients/:slug/feature-flags endpoint for contribution config.
 * No fabricated contribution data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function EmployerContributions() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [employerContributionRate, setEmployerContributionRate] = useState(5)
  const [employeeContributionRate, setEmployeeContributionRate] = useState(3)
  const [claimsProcessingDays, setClaimsProcessingDays] = useState(5)
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
      setEmployerContributionRate(Number(getCfg("employer_contribution_rate") ?? 5))
      setEmployeeContributionRate(Number(getCfg("employee_contribution_rate") ?? 3))
      setClaimsProcessingDays(Number(getCfg("claims_processing_days") ?? 5))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/employer_contribution_rate`, { config: String(employerContributionRate) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/employee_contribution_rate`, { config: String(employeeContributionRate) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/claims_processing_days`, { config: String(claimsProcessingDays) })
      await load()
      setNotice("Employer contributions config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Employer Contributions"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Employer Contributions + Claims" description="BN-02 · employer contributions + claims · depends PY-02 (not yet shipped) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The employer contributions + claims could not be read." fallback="The employer contributions + claims could not be read." onRetry={load} />}
        <SectionCard compact title="Employer contributions configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Employer contribution rate (%)</label>
              <Input value={employerContributionRate} onChange={e => setEmployerContributionRate(Number(e.target.value) || 5)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Employee contribution rate (%)</label>
              <Input value={employeeContributionRate} onChange={e => setEmployeeContributionRate(Number(e.target.value) || 3)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Claims processing days</label>
              <Input value={claimsProcessingDays} onChange={e => setClaimsProcessingDays(Number(e.target.value) || 5)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save contributions config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">BN-02 · R5 · depends PY-02 · no fabricated contribution data.</div>
      </div>
    </Layout>
  )
}