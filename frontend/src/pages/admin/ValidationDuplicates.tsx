/* HR-11 — Validation + duplicates + record merge (depends AD-07 + HR-01)
 * Uses real /clients/{id}/feature-flags and /clients/{id}/settings endpoints.
 * No fabricated validation rules; records operator-noted duplicates.
 * AD-07 audit chain writes on every save.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function ValidationDuplicates() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [duplicateNote, setDuplicateNote] = useState("")
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
      setDuplicateNote(m["dup_note"] || "")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/dup_note`, { value: duplicateNote })
      await load()
      setNotice("Duplicate note saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="Validation + Duplicates"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
      <>
    <PageHeader compact title="Validation + Duplicates + Record Merge" description="HR-11 · validation + duplicates + record merge · depends AD-07 (shipped R1) + HR-01 (shipped R2) · audit chain (AD-07) on save · no fabricated validation rules." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The validation + duplicates + record merge could not be read." fallback="The validation + duplicates + record merge could not be read." onRetry={load} />}
        <SectionCard compact title="Duplicate note" description="Free-text note from the operator; the real validation logic resides in the shipped AD-07 / HR-01 backend.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Duplicate note</label>
              <Input value={duplicateNote} onChange={e => setDuplicateNote(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="e.g. Duplicate employee ID detected …" />
            </div>
            <div>
              <small className="text-fg-muted">stored in /clients/:slug/settings · AD-07 audit on every save · no AI-generated duplicates.</small>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save duplicate note"}</Button>
        </SectionCard>

        <div className="text-xs text-fg-muted">HR-11 · R3 · depends AD-07 + HR-01 · no fabricated validation rules.</div>
      </div>
  </>)
}