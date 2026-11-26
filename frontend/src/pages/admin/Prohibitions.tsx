/* AI-13 — Prohibitions (autonomous decisions) (depends AI-12)
 * AI-12 (Mandatory controls) shipped R3.
 * Uses real /clients/{id}/feature-flags endpoint for prohibition settings.
 * No fabricated autonomous decision rules; operator-defined prohibition labels only.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const PROHIBITIONS = [
  { value: "autonomous_termination", label: "Autonomous termination decisions" },
  { value: "salary_adjustment", label: "Salary adjustment without review" },
  { value: "schedule_changes", label: "Schedule changes without notice" },
]

export default function Prohibitions() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [prohibition, setProhibition] = useState("autonomous_termination")
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
      setProhibition((getCfg("ai_prohibition") ?? "autonomous_termination"))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/ai_prohibition`, { config: prohibition })
      await load()
      setNotice("Prohibition saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="Prohibitions"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
      <>
    <PageHeader compact title="Prohibitions (Autonomous Decisions)" description="AI-13 · prohibitions (autonomous decisions) · depends AI-12 (shipped R2) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The prohibitions (autonomous decisions) could not be read." fallback="The prohibitions (autonomous decisions) could not be read." onRetry={load} />}
        <SectionCard compact title="Prohibition setting" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Prohibition</label>
              <select
                value={prohibition}
                onChange={e => setProhibition(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {PROHIBITIONS.map(p => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
            <div />
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save prohibition"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">AI-13 · R3 · depends AI-12 · no fabricated autonomous decision rules.</div>
      </div>
  </>)
}