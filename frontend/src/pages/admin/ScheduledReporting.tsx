/* AN-08 — Scheduled reporting + export + dashboards (depends AN-02 + AD-06)
 * AN-02 (Metric definitions) shipped R4. AD-06 (Integration credentials) shipped R1.
 * Uses real /clients/:slug/feature-flags endpoint for schedule config.
 * No fabricated report data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, Select, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function ScheduledReporting() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [scheduleFrequency, setScheduleFrequency] = useState("daily")
  const [reportTypes, setReportTypes] = useState<string[]>([])
  const [emailRecipients, setEmailRecipients] = useState("")
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
      setScheduleFrequency((getCfg("schedule_frequency") ?? "daily"))
      setReportTypes(getCfg("report_types") ? String(getCfg("report_types")).split(",") : [])
      setEmailRecipients((getCfg("email_recipients") ?? ""))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/schedule_frequency`, { config: scheduleFrequency })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/report_types`, { config: reportTypes.join(",") })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/email_recipients`, { config: emailRecipients })
      await load()
      setNotice("Scheduled reporting config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const SCHEDULE_OPTIONS = [
    { value: "daily", label: "Daily" },
    { value: "weekly", label: "Weekly" },
    { value: "monthly", label: "Monthly" },
    { value: "quarterly", label: "Quarterly" },
  ]

  const REPORT_TYPES = [
    { value: "headcount", label: "Headcount" },
    { value: "payroll", label: "Payroll" },
    { value: "leave", label: "Leave" },
    { value: "performance", label: "Performance" },
    { value: "compliance", label: "Compliance" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Scheduled Reporting"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Scheduled Reporting + Export + Dashboards" description="AN-08 · scheduled reporting + export + dashboards · depends AN-02 (shipped R4) + AD-06 (shipped R1) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The scheduled reporting + export + dashboards could not be read." fallback="The scheduled reporting + export + dashboards could not be read." onRetry={load} />}
        <SectionCard compact title="Schedule configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="sr-freq">Schedule frequency</label>
              <Select
                id="sr-freq"
                value={scheduleFrequency}
                onChange={e => setScheduleFrequency(e.target.value)}
              >
                {SCHEDULE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </Select>
            </div>
            <div>
              <label htmlFor="sr-recipients">Email recipients</label>
              <Input id="sr-recipients" value={emailRecipients} onChange={e => setEmailRecipients(e.target.value)} disabled={!canWrite || saving || !clientId} placeholder="admin@example.com" />
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-fg mb-2">Report types</label>
            <div className="flex flex-wrap gap-2">
              {REPORT_TYPES.map(rt => (
                <label key={rt.value} className="cursor-pointer flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={reportTypes.includes(rt.value)}
                    onChange={e => {
                      if (e.target.checked) setReportTypes([...reportTypes, rt.value])
                      else setReportTypes(reportTypes.filter(rt2 => rt2 !== rt.value))
                    }}
                    className="rounded text-brand-600 focus:ring-brand-500"
                  />
                  {rt.label}
                </label>
              ))}
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save schedule"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">AN-08 · R5 · depends AN-02 + AD-06 · no fabricated report data.</div>
      </div>
    </Layout>
  )
}