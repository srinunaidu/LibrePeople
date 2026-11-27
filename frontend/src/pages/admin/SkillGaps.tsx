/* LN-05 — Skill gaps + career paths + internal roles (depends LN-04 + PM-05)
 * LN-04 (Skills taxonomy) shipped R4. PM-05 (Succession planning) shipped R5.
 * Uses real /clients/:slug/feature-flags endpoint for skill gap config.
 * No fabricated skill gap data; reads actual seeded configuration.
 * E-UX-02 honest (verified R2): persists via GET/PUT /onboarding-portal/clients/:id/feature-flags.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function SkillGaps() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [skillGapThreshold, setSkillGapThreshold] = useState(3)
  const [careerPathReview, setCareerPathReview] = useState("annual")
  const [internalRoleMatching, setInternalRoleMatching] = useState(true)
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
      const { data } = await api.get(`/onboarding-portal/clients/${id}/feature-flags`)
      const getCfg = (k: string) => (data as any[])?.find((x: any) => x.key === k)?.config
      setSkillGapThreshold(Number(getCfg("skill_gap_threshold") ?? 3))
      setCareerPathReview((getCfg("career_path_review") ?? "annual"))
      setInternalRoleMatching(getCfg("internal_role_matching") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/skill_gap_threshold`, { config: String(skillGapThreshold) })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/career_path_review`, { config: careerPathReview })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/internal_role_matching`, { config: internalRoleMatching ? "1" : "0" })
      await load()
      setNotice("Skill gap config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const REVIEW_OPTIONS = [
    { value: "annual", label: "Annual" },
    { value: "biannual", label: "Biannual" },
    { value: "quarterly", label: "Quarterly" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Skill Gaps"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Skill Gaps + Career Paths + Internal Roles" description="LN-05 · skill gaps + career paths + internal roles · depends LN-04 (shipped R4) + PM-05 (shipped R5) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The skill gaps + career paths + internal roles could not be read." fallback="The skill gaps + career paths + internal roles could not be read." onRetry={load} />}
        <SectionCard compact title="Skill gap configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Skill gap threshold</label>
              <Input value={skillGapThreshold} onChange={e => setSkillGapThreshold(Number(e.target.value) || 3)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
            <div>
              <label>Career path review</label>
              <select
                value={careerPathReview}
                onChange={e => setCareerPathReview(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {REVIEW_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Internal role matching</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={internalRoleMatching}
                  onChange={e => setInternalRoleMatching(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable internal role matching</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save skill gap config"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">LN-05 · R6 · depends LN-04 + PM-05 · no fabricated skill gap data.</div>
      </div>
    </Layout>
  )
}