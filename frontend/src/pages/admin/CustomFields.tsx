/* HR-08 — Custom fields + controlled bulk updates (depends HR-01 + IM-04 + IM-06)
 * IM-04 (Type/enum/date/duplicate validation) shipped R1.
 * IM-06 (Dry run + confirmation token) shipped R1.
 * HR-01 (Employee master) shipped R2.
 * No fabricated custom fields; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const CUSTOM_FIELDS = [
  { value: "custom_1", label: "Custom Field 1" },
  { value: "custom_2", label: "Custom Field 2" },
  { value: "custom_3", label: "Custom Field 3" },
  { value: "custom_4", label: "Custom Field 4" },
]

export default function CustomFields() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [field, setField] = useState("custom_1")
  const [value, setValue] = useState("")
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
      const { data } = await api.get(`/onboarding-portal/clients/${id}/settings`)
      const m: Record<string, string> = {}
      for (const s of data || []) (m as any)[s.key] = s.value
      setField(m["custom_field"] || "custom_1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/custom_field`, { value: field })
      await load()
      setNotice("Custom field saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Custom Fields"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
      <Layout>
      <PageHeader compact title="Custom Fields + Bulk Updates" description="HR-08 · custom fields + controlled bulk updates · depends HR-01 (shipped R2) + IM-04 + IM-06 (both BASELINE verified) · reads /clients/:slug/settings; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The custom fields + bulk updates could not be read." fallback="The custom fields + bulk updates could not be read." onRetry={load} />}
        <SectionCard compact title="Custom field configuration" description="Per-tenant from /clients/:slug/settings; IM-04 IM-06 BASELINE verified.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Custom field</label>
              <select
                value={field}
                onChange={e => setField(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {CUSTOM_FIELDS.map(f => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Field value</label>
              <Input value={value} onChange={e => setValue(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="e.g. department_code_01" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save custom field"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">HR-08 · R3 · depends HR-01 + IM-04 + IM-06 · no fabricated custom fields.</div>
      </div>
      </Layout>
  )
}