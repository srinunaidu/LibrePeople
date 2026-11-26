/* PY-05 — Historical record + controlled correction (depends PY-04 + AD-07)
 * E-UX-02: the former random "record id" and discard-on-save note were removed.
 * Correction notes now persist per tenant via /clients/:id/settings
 * (keys historical_record_id / historical_correction_note, SuperAdmin only).
 * The PY-05 record endpoint is not shipped; this screen stores operator notes.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function HistoricalRecord() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)
  const canWrite = user?.role === "SuperAdmin"
  const [recordId, setRecordId] = useState("")
  const [correction, setCorrection] = useState("")
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
      setRecordId(m["historical_record_id"] || "")
      setCorrection(m["historical_correction_note"] || "")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    if (!recordId.trim()) { setActionError("Record ID is required (e.g. a payslip or pay-run reference)."); return }
    if (!correction.trim()) { setActionError("Correction note is required."); return }
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/historical_record_id`, { value: recordId.trim() })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/historical_correction_note`, { value: correction.trim() })
      await load()
      setNotice("Correction note saved.")
    } catch (e) { setActionError(errorMessage(e, "The correction note could not be saved.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Historical corrections require SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Historical Record"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Historical Record + Controlled Correction" description="PY-05 · operator correction notes persist via /clients/:id/settings (SuperAdmin). The PY-05 record endpoint is not shipped; notes are stored, not applied to payroll records." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The historical correction note could not be read." fallback="The historical correction note could not be read." onRetry={load} />}
        <SectionCard compact title="Record correction" description="Operator notes stored per tenant; persisted across refresh and re-login.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="hr-record">Record ID</label>
              <Input id="hr-record" value={recordId} onChange={e => setRecordId(e.target.value)} disabled={!canWrite || saving || !clientId} className="font-medium" placeholder="e.g. payslip #123" />
            </div>
            <div>
              <label htmlFor="hr-note">Correction note</label>
              <Input id="hr-note" value={correction} onChange={e => setCorrection(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="e.g. Payroll period adjustment for Q3 …" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save correction"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">PY-05 · R3 · depends PY-04 + AD-07 · operator-noted changes only.</div>
      </div>
    </Layout>
  )
}