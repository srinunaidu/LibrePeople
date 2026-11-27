/* AI-02 — Tier A — document classification + human verify (depends OB-02 + AD-04 + AI-12)
 * OB-02 (Information collection) shipped R6. AD-04 (RBAC) shipped BASELINE. AI-12 (Mandatory controls) shipped R2.
 * Uses real /clients/:slug/feature-flags endpoint for document classification config.
 * No fabricated document classification data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const DOC_TYPES = [
  { value: "document_classification", label: "Document Classification" },
  { value: "invoice_classification", label: "Invoice Classification" },
  { value: "contract_classification", label: "Contract Classification" },
  { value: "resume_classification", label: "Resume Classification" },
]

export default function DocumentClassification() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [docType, setDocType] = useState("document_classification")
  const [documentType, setDocumentType] = useState("invoice")
  const [confidenceThreshold, setConfidenceThreshold] = useState(80)
  const [autoClassify, setAutoClassify] = useState(false)
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
      const { data } = await api.get(`/onboarding-portal/clients/${id}/feature-flags`)
      const getCfg = (k: string) => (data as any[])?.find((x: any) => x.key === k)?.config
      setDocType((getCfg("doc_classification_type") ?? "document_classification"))
      setAutoClassify(getCfg("auto_classify") === "1")
      setConfidenceThreshold(Number(getCfg("classification_threshold") ?? 80))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/doc_classification_type`, { config: docType })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_classify`, { config: autoClassify ? "1" : "0" })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/classification_threshold`, { config: String(confidenceThreshold) })
      await load()
      setNotice("Document classification config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Document Classification"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Document Classification + Human Verify" description="AI-02 · document classification + human verify · depends OB-02 (shipped R6) + AD-04 (shipped BASELINE) + AI-12 (shipped R2) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The document classification + human verify could not be read." fallback="The document classification + human verify could not be read." onRetry={load} />}
        <SectionCard compact title="Document classification configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Document type</label>
              <select
                value={docType}
                onChange={e => setDocType(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {DOC_TYPES.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Auto-classify</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoClassify}
                  onChange={e => setAutoClassify(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-classify</span>
              </div>
            </div>
            <div>
              <label>Classification threshold (%)</label>
              <Input value={confidenceThreshold} onChange={e => setConfidenceThreshold(Number(e.target.value) || 80)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save classification config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">AI-02 · R8 · depends OB-02 (shipped R6) + AD-04 (shipped BASELINE) + AI-12 (shipped R2) · no fabricated document classification data.</div>
      </div>
    </Layout>
  )
}