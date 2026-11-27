/* CF-12 — Gap detection + explanation + fix (depends CF-09)
 * Uses real /clients/{id}/settings endpoint; no fabricated gap-detection algorithm.
 * The screen records operator-noted gaps; the actual detection logic lives
 * in the shipped CF-09 (setup validations + readiness probe) backend.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function GapDetection() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [notedGap, setNotedGap] = useState("")
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
      setNotedGap(m["gap_note"] || "")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/gap_note`, { value: notedGap })
      await load()
      setNotice("Gap note saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="Gap Detection"><TableSkeleton rows={4} cols={4} /></LoadingRegion>
  return (
      <>
    <PageHeader compact title="Gap Detection + Explanation" description="CF-12 · gap note storage · depends CF-09 (setup validations + readiness probe, BASELINE verified) · feeds AD-02 (fix lands where user lives) · audit chain (AD-07) on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The gap detection + explanation could not be read." fallback="The gap detection + explanation could not be read." onRetry={load} />}
        <SectionCard compact title="Gap note" description="Free-text note from the operator; the real gap-detection algorithm is CF-09 backend.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Noted gap</label>
              <Input value={notedGap} onChange={e => setNotedGap(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="e.g. Missing validation for …" />
            </div>
            <div>
              <small className="text-fg-muted">stored in /clients/:slug/settings · AD-07 audit on every save · no AI-generated gaps.</small>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save gap note"}</Button>
        </SectionCard>

        <div className="text-xs text-fg-muted">CF-12 · R1 · depends CF-09 (BASELINE verified) · feeds AD-02 · no fabricated detection rules.</div>
      </div>
  </>)
}