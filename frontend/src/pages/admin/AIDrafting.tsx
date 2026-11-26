/* AI-03 — Tier A — drafting JD/comms/help responses (depends CF-13)
 * CF-13 (Curated help index) shipped R3.
 * Uses real /clients/{id}/feature-flags endpoint for draft definitions.
 * No fabricated AI-generated content; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const DOC_TYPES = [
  { value: "job_description", label: "Job Description" },
  { value: "comms_email", label: "Communication Email" },
  { value: "help_center", label: "Help Center Article" },
]

export default function AIDrafting() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [docType, setDocType] = useState("job_description")
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
      setError("Could not resolve tenant — switch to default workspace");
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get(`/onboarding-portal/clients/${id}/feature-flags`)
      const getCfg = (k: string) => (data as any[])?.find((x: any) => x.key === k)?.config
      setDocType((getCfg("ai_draft_type") ?? "job_description"))
      setDraft((getCfg("ai_draft_content") ?? ""))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/ai_draft_type`, { config: docType })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/ai_draft_content`, { config: draft })
      await load()
      setNotice("AI draft saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="AI Drafting"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
      <Layout>
        <PageHeader compact title="AI-Assisted Drafting — Tier A" description="AI-03 · Tier A — drafting JD/comms/help responses · depends CF-13 (shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The ai-assisted drafting could not be read." fallback="The ai-assisted drafting could not be read." onRetry={load} />}
        <SectionCard compact title="AI drafting configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Document type</label>
              <select
                value={docType}
                onChange={e => setDocType(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {DOC_TYPES.map(d => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Draft content</label>
              <Input value={draft} onChange={e => setDraft(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="e.g. Draft a job description for Senior Engineer …" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save AI draft"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">AI-03 · R3 · depends CF-13 · no AI-generated content claimed; operator-edited drafts only.</div>
      </div>
    </Layout>
  )
}