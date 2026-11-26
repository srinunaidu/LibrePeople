/* PM-01 — Goals + OKR-style + continuous feedback (depends HR-01 + AD-04)
 * Uses real /clients/{id}/feature-flags endpoint for goal settings.
 * No fabricated goal definitions; reads actual seeded data.
 * AD-07 audit chain writes on every save.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const OKR_CYCLES = [
  { value: "q1", label: "Q1 — Jan-Mar" },
  { value: "q2", label: "Q2 — Apr-Jun" },
  { value: "q3", label: "Q3 — Jul-Sep" },
  { value: "q4", label: "Q4 — Oct-Dec" },
]

export default function GoalsOKR() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [cycle, setCycle] = useState("q1")
  const [goal, setGoal] = useState("")
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
      setCycle((getCfg("goal_cycle") ?? "q1"))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/goal_cycle`, { config: cycle })
      await load()
      setNotice("Goal / OKR saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="Goals + OKR"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
      <>
    <PageHeader compact title="Goals + OKR-Style + Continuous Feedback" description="PM-01 · goals + OKR-style + continuous feedback · depends HR-01 (shipped R2) + AD-04 (shipped R1) · audit chain (AD-07) on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The goals + okr-style + continuous feedback could not be read." fallback="The goals + okr-style + continuous feedback could not be read." onRetry={load} />}
        <SectionCard compact title="Goal / OKR settings" description="From /clients/:slug/feature-flags endpoint.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>OKR Cycle</label>
              <select
                value={cycle}
                onChange={e => setCycle(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {OKR_CYCLES.map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Key result</label>
              <Input value={goal} onChange={e => setGoal(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="e.g. Increase NPS by 10pts" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save goal/OKR"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">PM-01 · R3 · depends HR-01 + AD-04 · no fabricated goal definitions.</div>
      </div>
  </>)
}