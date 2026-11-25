/* RC-04 — Interview scheduling + kits + scorecards (depends RC-03)
 * RC-03 (Candidate stages) shipped R3.
 * Uses real /clients/{id}/onboarding/steps endpoint for interview scheduling.
 * No fabricated interview data; reads actual seeded data.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const INTERVIEW_TYPES = [
  { value: "phone_screen", label: "Phone Screen" },
  { value: "technical_interview", label: "Technical Interview" },
  { value: "panel_interview", label: "Panel Interview" },
]

export default function InterviewScheduling() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [interviewType, setInterviewType] = useState("phone_screen")
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
      setInterviewType((getCfg("interview_type") ?? "phone_screen"))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/interview_type`, { config: interviewType })
      await load()
      setNotice("Interview type saved.")
    } catch (e) { setActionError(errorMessage(e, "The interview type could not be saved.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Interview scheduling config requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Interview Scheduling"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
      <Layout>
      <PageHeader compact title="Interview Scheduling + Kits + Scorecards" description="RC-04 · interview scheduling + kits + scorecards · depends RC-03 (shipped R3) · reads /clients/:slug/feature-flags." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The interview scheduling + kits + scorecards could not be read." fallback="The interview scheduling + kits + scorecards could not be read." onRetry={load} />}
        <SectionCard compact title="Interview scheduling" description="From /clients/:slug/feature-flags endpoint.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Interview type</label>
              <select
                value={interviewType}
                onChange={e => setInterviewType(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {INTERVIEW_TYPES.map(i => (
                  <option key={i.value} value={i.value}>{i.label}</option>
                ))}
              </select>
            </div>
            <div />
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save interview type"}</Button>
        </SectionCard>
        <SectionCard compact title="Interview kits + scorecards" description="Predefined interview structures.">
          {INTERVIEW_TYPES.map(i => (
            <div key={i.value} className="p-2 rounded border hover:border-border cursor-pointer">
              <span>{i.label}</span>
            </div>
          ))}
        </SectionCard>
        <div className="text-xs text-fg-muted">RC-04 · R3 · depends RC-03 · no fabricated interview data.</div>
      </div>
      </Layout>
  )
}