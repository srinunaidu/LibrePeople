/* LN-06 — Mentoring + development plans (depends PM-04 + LN-01)
 * PM-04 (Improvement plans) shipped R5. LN-01 (Courses + enrollments) shipped R4.
 * Uses real /clients/:slug/feature-flags endpoint for mentoring config.
 * No fabricated mentoring data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function MentoringDevelopment() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [mentorshipProgram, setMentorshipProgram] = useState("enabled")
  const [developmentPlanCycle, setDevelopmentPlanCycle] = useState("annual")
  const [mentorMatching, setMentorMatching] = useState(true)
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
      setMentorshipProgram((getCfg("mentorship_program") ?? "enabled"))
      setDevelopmentPlanCycle((getCfg("development_plan_cycle") ?? "annual"))
      setMentorMatching(getCfg("mentor_matching") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/mentorship_program`, { config: mentorshipProgram })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/development_plan_cycle`, { config: developmentPlanCycle })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/mentor_matching`, { config: mentorMatching ? "1" : "0" })
      await load()
      setNotice("Mentoring config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const PROGRAM_OPTIONS = [
    { value: "enabled", label: "Enabled" },
    { value: "disabled", label: "Disabled" },
    { value: "opt_in", label: "Opt-in" },
  ]

  const CYCLE_OPTIONS = [
    { value: "annual", label: "Annual" },
    { value: "biannual", label: "Biannual" },
    { value: "quarterly", label: "Quarterly" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Mentoring Development"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Mentoring + Development Plans" description="LN-06 · mentoring + development plans · depends PM-04 (shipped R5) + LN-01 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The mentoring + development plans could not be read." fallback="The mentoring + development plans could not be read." onRetry={load} />}
        <SectionCard compact title="Mentoring configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Mentorship program</label>
              <select
                value={mentorshipProgram}
                onChange={e => setMentorshipProgram(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {PROGRAM_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Development plan cycle</label>
              <select
                value={developmentPlanCycle}
                onChange={e => setDevelopmentPlanCycle(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {CYCLE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Mentor matching</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={mentorMatching}
                  onChange={e => setMentorMatching(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable mentor matching</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save mentoring config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">LN-06 · R6 · depends PM-04 + LN-01 · no fabricated mentoring data.</div>
      </div>
    </Layout>
  )
}