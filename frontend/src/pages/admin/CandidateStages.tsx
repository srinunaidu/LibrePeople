/* RC-03 — Candidate stages + talent pools (depends AD-02 + HR-04)
 * E-UX-02: the former "Advance stage" POSTed /onboarding/steps/advance, which
 * does not exist. Stage + pool now persist as tenant configuration via
 * GET/PUT /clients/:id/feature-flags (candidate_status / candidate_pool,
 * require_roles("SuperAdmin")).
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const STATUSES = ["applied", "screening", "interview", "offer", "hired", "rejected"]
const POOLS = ["engineering", "sales", "operations", "finance", "marketing"]

export default function CandidateStages() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [status, setStatus] = useState("applied")
  const [pool, setPool] = useState("engineering")
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
      setStatus(getCfg("candidate_status") ?? "applied")
      setPool(getCfg("candidate_pool") ?? "engineering")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/candidate_status`, { config: status })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/candidate_pool`, { config: pool })
      await load()
      setNotice("Candidate stage config saved.")
    } catch (e) { setActionError(errorMessage(e, "The candidate stage config could not be saved.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Candidate stage config requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Candidate Stages"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>
  return (
    <Layout>
      <PageHeader compact title="Candidate Stages & Talent Pools" description="RC-03 · default candidate stage + talent pool configuration · persists via /clients/:id/feature-flags (SuperAdmin)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The candidate stage config could not be read." fallback="The candidate stage config could not be read." onRetry={load} />}
        <SectionCard compact title="Stage configuration" description="Default stage + pool stored per tenant; persisted across refresh and re-login.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="cs-status">Status</label>
              <select
                id="cs-status"
                value={status}
                onChange={e => setStatus(e.target.value)}
                className="w-full rounded border px-3 py-2"
                disabled={!canWrite || saving || !clientId}
              >
                {STATUSES.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="cs-pool">Talent pool</label>
              <select
                id="cs-pool"
                value={pool}
                onChange={e => setPool(e.target.value)}
                className="w-full rounded border px-3 py-2"
                disabled={!canWrite || saving || !clientId}
              >
                {POOLS.map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div />
          </div>
          <div className="mt-4 flex gap-3">
            <Button onClick={save} disabled={!canWrite || saving || !clientId}>{saving ? "Saving…" : "Save stage config"}</Button>
          </div>
        </SectionCard>

        <SectionCard compact title="Current configuration" description="The persisted tenant configuration.">
          <div className="text-sm text-fg-muted">Status: {status} | Pool: {pool}</div>
        </SectionCard>

        <div className="text-xs text-fg-muted">RC-03 · R1 · depends AD-02 + HR-04 · feeds RC-01 (candidate-to-offer) · configuration only.</div>
      </div>
    </Layout>
  )
}