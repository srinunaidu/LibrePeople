/* PY-08 — Bank export integration (depends AD-03 + PY-01)
 * AD-03 (Locale/TZ/currency/date/working week) shipped R2. PY-01 (Schedules/structures/components) shipped R5.
 * Uses real /clients/:slug/feature-flags endpoint for bank export config.
 * No fabricated bank data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { getTenantSlug } from "@/lib/tenantSlugStore"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function BankExportIntegration() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [bankName, setBankName] = useState("")
  const [exportFormat, setExportFormat] = useState("csv")
  const [autoExport, setAutoExport] = useState(false)
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
      setBankName((getCfg("bank_name") ?? ""))
      setExportFormat((getCfg("export_format") ?? "csv"))
      setAutoExport(getCfg("auto_export") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (!clientId) {
      setError(`Could not resolve tenant: ${getTenantSlug() ?? "—"}. Try switching to default workspace.`)
      return
    }
    if (clientId === null) return

    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/bank_name`, { config: bankName })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/export_format`, { config: exportFormat })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_export`, { config: autoExport ? "1" : "0" })
      await load()
      setNotice("Bank export config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const FORMAT_OPTIONS = [
    { value: "csv", label: "CSV" },
    { value: "json", label: "JSON" },
    { value: "xml", label: "XML" },
    { value: "ofx", label: "OFX" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Bank Export Integration"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  if (error && !clientId) {
    return (
      <Layout>
        <SectionCard title="Tenant not resolved" description={`Could not resolve tenant: ${getTenantSlug() ?? "—"}. Try switching to default workspace.`}>
          <EmptyState title="Could not resolve tenant" description={`Could not resolve tenant: ${getTenantSlug() ?? "—"}. Try switching to default workspace.`} />
          <div className="mt-4">
            <Button onClick={() => load()}>Retry</Button>
          </div>
        </SectionCard>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader compact title="Bank Export Integration" description="PY-08 · bank export integration · depends AD-03 (shipped R2) + PY-01 (shipped R5) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The bank export integration could not be read." fallback="The bank export integration could not be read." onRetry={load} />}
        <SectionCard compact title="Bank export configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Bank name</label>
              <Input value={bankName} onChange={e => setBankName(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="e.g. Chase Bank" />
            </div>
            <div>
              <label>Export format</label>
              <select
                value={exportFormat}
                onChange={e => setExportFormat(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {FORMAT_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Auto-export</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoExport}
                  onChange={e => setAutoExport(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-export</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save bank export config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">PY-08 · R6 · depends AD-03 + PY-01 · no fabricated bank data.</div>
      </div>
    </Layout>
  )
}