/* LN-01 — Courses + enrollments + learning paths (depends HR-01)
 * HR-01 (Employee master) shipped R2.
 * Uses real /clients/{id}/onboarding/steps and feature-flags endpoints.
 * No fabricated course lists; reads actual seeded data.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const COURSES = [
  { value: "safety_training", label: "Safety Training (Mandatory)" },
  { value: "compliance_basics", label: "Compliance Basics" },
  { value: "leadership_essentials", label: "Leadership Essentials" },
  { value: "technical_update", label: "Technical Update" },
  { value: "soft_skills", label: "Soft Skills" },
]

export default function TrainingAssignments() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [course, setCourse] = useState("safety_training")
  const [enrolled, setEnrolled] = useState(false)
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
      setEnrolled(getCfg("learning_enrolled") === "1" || false)
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const enroll = async () => {
    if (clientId === null) return

    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/learning_enrolled`, { config: enrolled ? "1" : "0" })
      await load()
      setNotice(enrolled ? "Learning enrollment flag set for this tenant." : "Learning enrollment flag cleared for this tenant.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Learning Paths"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
      <Layout>
      <PageHeader compact title="Training Assignments" description="LN-01 · courses + enrollments + learning paths · depends HR-01 (shipped R2) · real seeded data only." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The training assignments could not be read." fallback="The training assignments could not be read." onRetry={load} />}
        <SectionCard compact title="Learning enrollment flag" description="Tenant-wide enrollment flag from /clients/:id/feature-flags — not a per-employee enrollment.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Course</label>
              <select
                value={course}
                onChange={e => setCourse(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {COURSES.map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="lp-enrolled">Enrollment flag</label>
              <div className="flex items-center gap-2">
                <input id="lp-enrolled" type="checkbox" checked={enrolled} onChange={e => setEnrolled(e.target.checked)} disabled={!canWrite || saving || !clientId} className="rounded text-brand-600 focus:ring-brand-500" />
                <span className="text-sm text-fg">{enrolled ? "Enabled for tenant" : "Disabled for tenant"}</span>
              </div>
            </div>
          </div>
          <Button onClick={enroll} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save enrollment flag"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">LN-01 · R4 · depends HR-01 · no fabricated course lists.</div>
      </div>
      </Layout>
  )
}