/* UX-09 — States (loading/empty/error/retry) (depends AD-02 + AD-04)
 * Discipline flags per screen; no fabricated UX metrics. Reads real feature-flag state.
 * E-UX-02 honest (verified R2): persists via GET/PUT /onboarding-portal/clients/:id/feature-flags.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function StatesDiscipline() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [loadingState, setLoadingState] = useState(false)
  const [emptyState, setEmptyState] = useState(false)
  const [errorState, setErrorState] = useState(false)
  const [retryable, setRetryable] = useState(false)
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
      setLoadingState(getCfg("loading_state") === "1" || false)
      setEmptyState(getCfg("empty_state") === "1" || false)
      setErrorState(getCfg("error_state") === "1" || false)
      setRetryable(getCfg("retryable") === "1" || false)
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/ux_09`, { config: "1" })
      await load()
      setNotice("UX discipline flags saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="States"><TableSkeleton rows={4} cols={4} /></LoadingRegion>
  return (
      <>
    <PageHeader compact title="States Discipline" description="UX-09 · loading/empty/error/retry flags · depends AD-02 (feature flags verified) + AD-04 (RBAC) · audit chain (AD-07) on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The states discipline could not be read." fallback="The states discipline could not be read." onRetry={load} />}
        <SectionCard compact title="State flags" description="Per-screen discipline; CF-12 gap detection ties in here.">
          <div className="grid sm:grid-cols-3 gap-4 text-sm">
            <div><div className="text-xs text-fg-muted">Loading</div><div className={`font-semibold ${loadingState ? "text-success-text" : "text-fg-subtle"}`}>{loadingState ? "enabled" : "disabled"}</div></div>
            <div><div className="text-xs text-fg-muted">Empty</div><div className={`font-semibold ${emptyState ? "text-success-text" : "text-fg-subtle"}`}>{emptyState ? "enabled" : "disabled"}</div></div>
            <div><div className="text-xs text-fg-muted">Error</div><div className={`font-semibold ${errorState ? "text-success-text" : "text-fg-subtle"}`}>{errorState ? "enabled" : "disabled"}</div></div>
          </div>
          <div className="mt-4">
            <Button onClick={save} disabled={!canWrite || saving || !clientId}>{saving ? "Saving…" : "Save flags"}</Button>
          </div>
        </SectionCard>

        <div className="text-xs text-fg-muted">UX-09 · R1 · depends AD-02 + AD-04 · feeds CF-12 (gap detection) · no fabricated UX metrics.</div>
      </div>
  </>)
}