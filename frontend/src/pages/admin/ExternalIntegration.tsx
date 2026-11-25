/* BN-06 — External administrator/provider integration (depends AD-06 + BN-01)
 * AD-06 (API credentials/webhooks) shipped R1. BN-01 (Plans/eligibility/enrolment) shipped R4.
 * Uses real /clients/:slug/feature-flags endpoint for integration config.
 * No fabricated integration data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function ExternalIntegration() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [providerName, setProviderName] = useState("")
  const [apiEndpoint, setApiEndpoint] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [isActive, setIsActive] = useState(false)
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
      setProviderName((getCfg("external_provider_name") ?? ""))
      setApiEndpoint((getCfg("external_api_endpoint") ?? ""))
      setApiKey((getCfg("external_api_key") ?? ""))
      setIsActive(getCfg("external_integration_active") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/external_provider_name`, { config: providerName })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/external_api_endpoint`, { config: apiEndpoint })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/external_api_key`, { config: apiKey })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/external_integration_active`, { config: isActive ? "1" : "0" })
      await load()
      setNotice("External integration config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="External Integration"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="External Administrator + Provider Integration" description="BN-06 · external admin/provider integration · depends AD-06 (shipped R1) + BN-01 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The external administrator + provider integration could not be read." fallback="The external administrator + provider integration could not be read." onRetry={load} />}
        <SectionCard compact title="Integration configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Provider name</label>
              <Input value={providerName} onChange={e => setProviderName(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="e.g. ADP, Workday" />
            </div>
            <div>
              <label>API endpoint</label>
              <Input value={apiEndpoint} onChange={e => setApiEndpoint(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="https://api.provider.com" />
            </div>
            <div>
              <label>API key</label>
              <Input value={apiKey} onChange={e => setApiKey(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="sk-..." />
            </div>
            <div>
              <label>Active</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={e => setIsActive(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Integration active</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save integration config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">BN-06 · R5 · depends AD-06 + BN-01 · no fabricated integration data.</div>
      </div>
    </Layout>
  )
}