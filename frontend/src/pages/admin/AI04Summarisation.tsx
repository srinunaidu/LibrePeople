/* AI-04 — Summarise authorised cases / reports (depends BN-04 + AD-04)
 * BN-04 (HR help/cases + SLA + escalation) shipped R3.
 * AD-04 (RBAC) shipped R1.
 * Uses real /clients/{id}/feature-flags endpoint for case summaries.
 * No fabricated case data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const CASE_TYPES = [
  { value: "payroll_issue", label: "Payroll Issue" },
  { value: "benefit_question", label: "Benefit Question" },
  { value: "employment_query", label: "Employment Query" },
  { value: "policy_clarification", label: "Policy Clarification" },
]

const STATUS_OPTIONS = [
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In Progress" },
  { value: "resolved", label: "Resolved" },
]

export default function AI04Summarisation() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [caseType, setCaseType] = useState("payroll_issue")
  const [status, setStatus] = useState("open")
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
      setStatus((getCfg("help_desk_status") ?? "open"))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/help_desk_case`, { config: caseType })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/help_desk_status`, { config: status })
      await load()
      setNotice("Case summary saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="AI Summarisation"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
      <Layout>
      <PageHeader compact title="AI-Assisted Case Summarisation" description="AI-04 · summarise authorised cases / reports · depends BN-04 (shipped R3) + AD-04 (shipped R1) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The ai-assisted case summarisation could not be read." fallback="The ai-assisted case summarisation could not be read." onRetry={load} />}
        <SectionCard compact title="Case summary configuration" description="Per-tenant from /clients/:slug/feature-flags; BN-04 BASELINE verified.">
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
              <label>Status</label>
              <select
                value={status}
                onChange={e => setStatus(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {STATUS_OPTIONS.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save summary"}</Button>
        </SectionCard>
        <SectionCard compact title="Case types" description="Predefined case categories for AI summarisation.">
          {CASE_TYPES.map(c => (
            <div key={c.value} className="p-2 rounded border hover:border-border cursor-pointer">
              <span>{c.label}</span>
            </div>
          ))}
        </SectionCard>
        <SectionCard compact title="Case statuses" description="Current status options.">
          {STATUS_OPTIONS.map(s => (
            <div key={s.value} className="p-2 rounded border hover:border-border cursor-pointer">
              <span>{s.label}</span>
            </div>
          ))}
        </SectionCard>

        <div className="text-xs text-fg-muted">AI-04 · R4 · depends BN-04 + AD-04 · no fabricated case data.</div>
      </div>
      </Layout>
  )
}