/* AI-01 — Policy search configuration (depends CF-13 + AD-04 + AD-07)
 * E-UX-02: no policy-search backend endpoint exists, so this screen no longer
 * pretends to run a search or show "citation results". It persists the default
 * policy query per tenant via /clients/:id/feature-flags (SuperAdmin only).
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function PolicySearch() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [query, setQuery] = useState("")
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
      setQuery((getCfg("policy_query") ?? ""))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/policy_query`, { config: query })
      await load()
      setNotice("Policy query saved.")
    } catch (e) { setActionError(errorMessage(e, "The policy query could not be saved.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Policy search config requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Policy Search"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Policy Search + Citations" description="AI-01 · default policy query configuration · persists via /clients/:id/feature-flags (SuperAdmin). No search endpoint is shipped yet; this screen stores the query only." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The policy search config could not be read." fallback="The policy search config could not be read." onRetry={load} />}
        <SectionCard compact title="Default policy query" description="Stored per tenant in the policy_query feature flag.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="ps-query">Search query</label>
              <Input id="ps-query" value={query} onChange={e => setQuery(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="e.g. maternity policy" />
            </div>
            <div />
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save policy query"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">AI-01 · R3 · depends CF-13 + AD-04 + AD-07 · configuration only; no fabricated search results.</div>
      </div>
    </Layout>
  )
}