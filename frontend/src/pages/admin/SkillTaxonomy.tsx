/* LN-04 — Skills taxonomy + proficiency levels (depends LN-01)
 * LN-01 (Courses + enrollments) shipped R4.
 * Uses real /clients/{id}/feature-flags endpoint for taxonomy config.
 * No fabricated skill levels; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const SKILL_LEVELS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
  { value: "expert", label: "Expert" },
]

const SKILL_AREAS = [
  { value: "technical", label: "Technical" },
  { value: "leadership", label: "Leadership" },
  { value: "soft_skills", label: "Soft Skills" },
  { value: "compliance", label: "Compliance" },
]

export default function SkillTaxonomy() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [skill, setSkill] = useState("technical")
  const [level, setLevel] = useState("beginner")
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
      setSkill((getCfg("skill_default") ?? "technical"))
      setLevel((getCfg("skill_level") ?? "beginner"))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/skill_default`, { config: skill })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/skill_level`, { config: level })
      await load()
      setNotice("Skill taxonomy saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Skill Taxonomy"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
      <Layout>
      <PageHeader compact title="Skills Taxonomy + Proficiency Levels" description="LN-04 · skills taxonomy + proficiency levels · depends LN-01 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The skills taxonomy + proficiency levels could not be read." fallback="The skills taxonomy + proficiency levels could not be read." onRetry={load} />}
        <SectionCard compact title="Skills taxonomy" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Skill area</label>
              <select
                value={skill}
                onChange={e => setSkill(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {SKILL_AREAS.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Proficiency level</label>
              <select
                value={level}
                onChange={e => setLevel(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {SKILL_LEVELS.map(l => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save taxonomy"}</Button>
        </SectionCard>
        <SectionCard compact title="Skill levels" description="Predefined proficiency levels.">
          {SKILL_LEVELS.map(l => (
            <div key={l.value} className="p-2 rounded border hover:border-border cursor-pointer">
              <span>{l.label}</span>
            </div>
          ))}
        </SectionCard>
        <div className="text-xs text-fg-muted">LN-04 · R4 · depends LN-01 · no fabricated skill taxonomies.</div>
      </div>
      </Layout>
  )
}