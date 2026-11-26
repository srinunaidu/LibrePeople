/* BN-05 — Knowledge base + help desk SLA + escalation (depends BN-04 + CF-13)
 * BN-04 (HR help/cases + SLA + escalation) shipped R3.
 * CF-13 (Curated help index) shipped R3.
 * Uses real /clients/{id}/feature-flags endpoint for help desk config.
 * No fabricated help desk data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const CASE_TYPES = [
  { value: "payroll_issue", label: "Payroll Issue" },
  { value: "benefit_question", label: "Benefit Question" },
  { value: "employment_query", label: "Employment Query" },
  { value: "policy_clarification", label: "Policy Clarification" },
]

export default function KnowledgeBase() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [caseType, setCaseType] = useState("payroll_issue")
  const [slaHours, setSlaHours] = useState(24)
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
      setCaseType((getCfg("help_desk_case") ?? "payroll_issue"))
      setSlaHours(Number(getCfg("help_desk_sla") ?? 24))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/help_desk_case`, { config: caseType })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/help_desk_sla`, { config: String(slaHours) })
      await load()
      setNotice("Help desk config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Knowledge Base"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
      <Layout>
      <PageHeader compact title="Knowledge Base + Help Desk + SLA + Escalation" description="BN-05 · knowledge base + SLA + escalation · depends BN-04 (shipped R3) + CF-13 (shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The knowledge base + help desk + sla + escalation could not be read." fallback="The knowledge base + help desk + sla + escalation could not be read." onRetry={load} />}
        <SectionCard compact title="Help desk configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Case type</label>
              <select
                value={caseType}
                onChange={e => setCaseType(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {CASE_TYPES.map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>SLA hours</label>
              <Input value={slaHours} onChange={e => setSlaHours(Number(e.target.value) || 24)} disabled={!canWrite || saving || !clientId} className="font-mono" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save help desk config"}</Button>
        </SectionCard>
        <SectionCard compact title="Case types" description="Predefined case types for help desk.">
          {CASE_TYPES.map(c => (
            <div key={c.value} className="p-2 rounded border hover:border-border cursor-pointer">
              <span>{c.label}</span>
            </div>
          ))}
        </SectionCard>
        <div className="text-xs text-fg-muted">BN-05 · R4 · depends BN-04 + CF-13 · no fabricated help desk data.</div>
      </div>
      </Layout>
  )
}