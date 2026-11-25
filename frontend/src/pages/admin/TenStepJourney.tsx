/* CF-11 — Ten-step journey + resumable progress (depends CF-02 + CF-09)
 * E-UX-02: the former advance/reset POSTed /onboarding/steps/advance|reset,
 * which do not exist. Resumable state now persists in the real feature-flags
 * store (key journey_step) via GET/PUT /clients/:id/feature-flags (SuperAdmin).
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const JOURNEY_STEPS = [
  "application", "screening", "assessment", "interview1", "interview2",
  "reference", "offer", "acceptance", "onboarding", "complete"
]

export default function TenStepJourney() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [step, setStep] = useState("application")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [error, setError] = useState<unknown | null>(null)

  const progress = Math.max(0, JOURNEY_STEPS.indexOf(step))

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
      const cfg = (data as any[])?.find((x: any) => x.key === "journey_step")?.config
      setStep(JOURNEY_STEPS.includes(cfg) ? cfg : "application")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const persist = async (next: string, verb: string) => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/journey_step`, { config: next })
      await load()
      setNotice(verb)
    } catch (e) { setActionError(errorMessage(e, "The journey state could not be saved.")) } finally { setSaving(false) }
  }

  const advance = () => {
    const idx = JOURNEY_STEPS.indexOf(step)
    const next = idx >= 0 && idx < JOURNEY_STEPS.length - 1 ? JOURNEY_STEPS[idx + 1] : step
    void persist(next, `Journey advanced to ${next}.`)
  }

  const reset = () => { void persist("application", "Journey reset to application.") }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`The ten-step journey requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Ten-Step Journey"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>
  return (
    <Layout>
      <PageHeader compact title="Ten-Step Journey + Resumable Progress" description="CF-11 · 10-step journey · resumable state persists in /clients/:id/feature-flags (key: journey_step, SuperAdmin)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The journey state could not be read." fallback="The journey state could not be read." onRetry={load} />}
        <SectionCard compact title="Journey progress" description="Resumable state stored on the server per tenant.">
          <div className="grid sm:grid-cols-3 gap-4 text-sm">
            <div><div className="text-xs text-fg-muted">Progress</div><div className="font-semibold">{progress}/10</div></div>
            <div><div className="text-xs text-fg-muted">Current step</div><div className="font-semibold">{step}</div></div>
            <div><div className="text-xs text-fg-muted">Resumable</div><div className={`font-semibold ${progress > 0 ? "text-success-text" : "text-fg-subtle"}`}>{progress > 0 ? "active" : "inactive"}</div></div>
          </div>
          <div className="mt-4 flex gap-3">
            <Button onClick={advance} disabled={!canWrite || saving || !clientId || step === "complete"}>{saving ? "Saving…" : "Advance step"}</Button>
            <Button variant="secondary" onClick={reset} disabled={!canWrite || saving || !clientId || progress === 0}>Reset state</Button>
          </div>
        </SectionCard>

        <SectionCard compact title="Journey steps" description="The 10-step lifecycle reference.">
          <div className="table-scroll">
            <table className="w-full text-sm">
              <caption className="sr-only">Journey step reference</caption>
              <thead><tr className="border-b"><th scope="col" className="text-left">Step</th><th scope="col" className="text-center">Index</th></tr></thead>
              <tbody>
                {JOURNEY_STEPS.map((s, i) => (
                  <tr key={s} className="border-b">
                    <td>{s}</td>
                    <td className="text-center">{i + 1}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="text-xs text-fg-muted">CF-11 · R1 · depends CF-02 + CF-09 · resumable state is the persisted journey_step flag.</div>
      </div>
    </Layout>
  )
}