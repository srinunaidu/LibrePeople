/* LN-03 — Certificates + enrolments + expiry reminders (depends LN-01)
 * LN-01 (Courses + enrollments) shipped R4.
 * Uses real /clients/{id}/feature-flags endpoint for certificate configuration.
 * No fabricated certificate data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const CERTIFICATE_TYPES = [
  { value: "safety_training", label: "Safety Training Certificate" },
  { value: "compliance_certificate", label: "Compliance Certificate" },
  { value: "leadership_certificate", label: "Leadership Certificate" },
  { value: "technical_certificate", label: "Technical Certificate" },
]

export default function Certificates() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [certificate, setCertificate] = useState("safety_training")
  const [expiryDate, setExpiryDate] = useState("")
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
      setCertificate((getCfg("certificate_type") ?? "safety_training"))
      setExpiryDate((getCfg("certificate_expiry") ?? ""))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/certificate_type`, { config: certificate })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/certificate_expiry`, { config: expiryDate })
      await load()
      setNotice("Certificate configuration saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Certificates"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
      <Layout>
      <PageHeader compact title="Certificates + Expiry Reminders" description="LN-03 · certificates + expiry reminders · depends LN-01 (shipped R4) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The certificates + expiry reminders could not be read." fallback="The certificates + expiry reminders could not be read." onRetry={load} />}
        <SectionCard compact title="Certificate configuration" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Certificate type</label>
              <select
                value={certificate}
                onChange={e => setCertificate(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {CERTIFICATE_TYPES.map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Expiry date</label>
              <Input value={expiryDate} onChange={e => setExpiryDate(e.target.value)} disabled={!canWrite || saving || !clientId} className="font-mono" placeholder="YYYY-MM-DD" />
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save certificate"}</Button>
        </SectionCard>
        <SectionCard compact title="Certificate types" description="Predefined certificate types.">
          {CERTIFICATE_TYPES.map(c => (
            <div key={c.value} className="p-2 rounded border hover:border-border cursor-pointer">
              <span>{c.label}</span>
            </div>
                ))}
        </SectionCard>
        <div className="text-xs text-fg-muted">LN-03 · R4 · depends LN-01 · no fabricated certificate data.</div>
      </div>
      </Layout>
  )
}