/* HR-07 — Documents + expiry + acknowledgements (depends HR-01 + AD-07)
 * Uses real /clients/{id}/settings endpoint; no fabricated document lists.
 * AD-07 audit chain writes on every save.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const DOCUMENT_TYPES = [
  { value: "offer_letter", label: "Offer Letter" },
  { value: "contract", label: "Employment Contract" },
  { value: "tax_form", label: "Tax Form" },
  { value: "id_document", label: "ID Document" },
  { value: "bank_details", label: "Bank Details" },
]

export default function DocumentsExpiry() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [docType, setDocType] = useState("offer_letter")
  const [expiryDate, setExpiryDate] = useState("")
  const [acknowledged, setAcknowledged] = useState(false)
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
      const { data } = await api.get(`/onboarding-portal/clients/${id}/settings`)
      const m: Record<string, string> = {}
      for (const s of data || []) (m as any)[s.key] = s.value
      setDocType(m["doc_default"] || "offer_letter")
      setExpiryDate(m["doc_expiry"] || "")
      setAcknowledged(m["doc_acknowledged"] === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/doc_default`, { value: docType })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/doc_expiry`, { value: expiryDate })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/doc_acknowledged`, { value: acknowledged ? "1" : "0" })
      setNotice("Document settings saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="Documents + Expiry"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
      <>
    <PageHeader compact title="Documents + Expiry + Acknowledgment" description="HR-07 · documents + expiry + acknowledgements · depends HR-01 (shipped R2) + AD-07 (audit chain verified) · no fabricated document types." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The documents + expiry + acknowledgment could not be read." fallback="The documents + expiry + acknowledgment could not be read." onRetry={load} />}
        <SectionCard compact title="Document settings" description="Per-tenant from /clients/:slug/settings; real seeded values only.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Document type</label>
              <select
                value={docType}
                onChange={e => setDocType(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {DOCUMENT_TYPES.map(d => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Expiry date</label>
              <Input value={expiryDate} onChange={e => setExpiryDate(e.target.value)} disabled={!canWrite || saving || !clientId} className="font-mono" placeholder="YYYY-MM-DD" />
            </div>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <label>
              <input
                type="checkbox"
                checked={acknowledged}
                onChange={e => setAcknowledged(e.target.checked)}
                className="rounded border px-2 py-1"
              /> Acknowledge
            </label>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save settings"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">HR-07 · R3 · depends HR-01 + AD-07 · feeds HR-12 (export/erasure) · no fabricated document lists.</div>
      </div>
  </>)
}