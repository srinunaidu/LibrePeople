/* PM-04 — Improvement plans + recognition (depends PM-02)
 * PM-02 (Review cycles + self-assessments) shipped R4.
 * Uses real /clients/:slug/feature-flags endpoint for improvement plan config.
 * No fabricated improvement data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function ImprovementPlans() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [improvementPeriod, setImprovementPeriod] = useState("90 days")
  const [recognitionProgram, setRecognitionProgram] = useState("employee of the month")
  const [autoEnroll, setAutoEnroll] = useState(false)
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
      setImprovementPeriod((getCfg("improvement_period") ?? "90 days"))
      setRecognitionProgram((getCfg("recognition_program") ?? "employee of the month"))
      setAutoEnroll(getCfg("auto_enroll") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/improvement_period`, { config: improvementPeriod })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/recognition_program`, { config: recognitionProgram })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/auto_enroll`, { config: autoEnroll ? "1" : "0" })
      await load()
      setNotice("Improvement plan config saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  const PERIOD_OPTIONS = [
    { value: "30 days", label: "30 days" },
    { value: "60 days", label: "60 days" },
    { value: "90 days", label: "90 days" },
    { value: "180 days", label: "180 days" },
  ]

  const PROGRAM_OPTIONS = [
    { value: "employee of the month", label: "Employee of the Month" },
    { value: "quarterly awards", label: "Quarterly Awards" },
    { value: "annual awards", label: "Annual Awards" },
    { value: "spot recognition", label: "Spot Recognition" },
  ]

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Improvement Plans"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Improvement Plans + Recognition" description="PM-04 · improvement plans + recognition · depends PM-02 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The improvement plans + recognition could not be read." fallback="The improvement plans + recognition could not be read." onRetry={load} />}
        <SectionCard compact title="Improvement plan configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Improvement period</label>
              <select
                value={improvementPeriod}
                onChange={e => setImprovementPeriod(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {PERIOD_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Recognition program</label>
              <select
                value={recognitionProgram}
                onChange={e => setRecognitionProgram(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {PROGRAM_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Auto-enroll</label>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoEnroll}
                  onChange={e => setAutoEnroll(e.target.checked)}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable auto-enroll</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save improvement plan"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">PM-04 · R5 · depends PM-02 · no fabricated improvement data.</div>
      </div>
    </Layout>
  )
}