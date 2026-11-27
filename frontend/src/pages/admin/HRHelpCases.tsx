/* BN-04 — HR help/cases + SLA + escalation (depends HR-01 + AD-04)
 * HR-01 (Employee master) shipped R2. AD-04 (RBAC) shipped R1.
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

export default function HRHelpCases() {
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
      setError("Could not resolve the company. Check the server connection and retry.");
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

  if (!canWrite) return <Layout><PageHeader compact title="HR Help Desk" description="Help-desk configuration for this install." /><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><PageHeader compact title="HR Help Desk" description="Help-desk configuration for this install." /><LoadingRegion label="HR Help Desk"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="HR Help Desk" description="Default case type and response-time target for employee help requests. Saved per install." />
      <div className="space-y-4">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The help-desk configuration could not be read." fallback="The help-desk configuration could not be read." onRetry={load} />}
        <SectionCard compact title="Help desk configuration" description="Defaults applied to new help requests.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="hd-case-type" className="field-label">Case type</label>
              <select
                id="hd-case-type"
                value={caseType}
                onChange={e => setCaseType(e.target.value)}
                className="input"
              >
                {CASE_TYPES.map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="hd-sla-hours" className="field-label">SLA hours</label>
              <Input id="hd-sla-hours" value={slaHours} onChange={e => setSlaHours(Number(e.target.value) || 24)} disabled={!canWrite || saving || !clientId} className="font-mono" inputMode="numeric" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save help desk config"}</Button>
        </SectionCard>
      </div>
    </Layout>
  )
}