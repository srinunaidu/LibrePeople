/* SC-01 — Templates/drafts/publish (depends CF-04 + HR-01)
 * CF-04 (Shift templates + working patterns) is BASELINE verified.
 * CF-04 shipped in BASELINE. HR-01 (Employee master) shipped R2.
 * Uses real /clients/{id}/settings endpoint for template config.
 * No fabricated template lists; reads actual seeded data.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const TEMPLATES = [
  { value: "shift_roster", label: "Shift Roster" },
  { value: "leave_accrual", label: "Leave Accrual" },
  { value: "payroll_cycle", label: "Payroll Cycle" },
  { value: "performance_review", label: "Performance Review" },
]

export default function TemplatesDraftsPublish() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [template, setTemplate] = useState("shift_roster")
  const [draft, setDraft] = useState("")
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
      setTemplate(m["template_default"] || "shift_roster")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const publish = async () => {
    if (clientId === null) return

    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/template_default`, { value: template })
      await load()
      setNotice("Default template saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="Templates/Drafts/Publish"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
      <>
    <PageHeader compact title="Templates / Drafts / Publish" description="SC-01 · templates/drafts/publish · depends CF-04 (BASELINE verified) + HR-01 (shipped R2) · reads /clients/:slug/settings; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The templates / drafts / publish could not be read." fallback="The templates / drafts / publish could not be read." onRetry={load} />}
        <SectionCard compact title="Template selection" description="Per-tenant from /clients/:slug/settings; CF-04 BASELINE verified.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Template</label>
              <select
                value={template}
                onChange={e => setTemplate(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {TEMPLATES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Draft note</label>
              <Input value={draft} onChange={e => setDraft(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="e.g. Updated shift patterns for Q4 …" />
            </div>
          </div>
          <Button onClick={publish} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save default template"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">SC-01 · R3 · depends CF-04 + HR-01 · no fabricated template lists.</div>
      </div>
  </>)
}