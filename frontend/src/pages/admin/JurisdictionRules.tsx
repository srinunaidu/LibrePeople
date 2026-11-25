/* PY-09 — Jurisdiction rules + versioning + test fixtures (depends PY-08 + AD-07 + PY-01)
 * Uses real /clients/:id/feature-flags endpoint (require_roles("SuperAdmin")).
 * E-UX-02: the former static "Jurisdiction rules" table (hardcoded US/GB/IN
 * rows with invented dates) was replaced by the actual persisted config.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Alert, Button, EmptyState, LoadingRegion, PageHeader, RetryableAlert, SectionCard, TableSkeleton } from "@/components/ui"
import { PendingVerificationAlert } from "@/components/ui/PendingVerificationAlert"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const JURISDICTION_OPTIONS = [
  { value: "US", label: "United States" },
  { value: "GB", label: "United Kingdom" },
  { value: "EU", label: "European Union" },
  { value: "CA", label: "Canada" },
  { value: "AU", label: "Australia" },
  { value: "IN", label: "India" },
]

export default function JurisdictionRules() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [jurisdiction, setJurisdiction] = useState("US")
  const [ruleVersion, setRuleVersion] = useState("v1.0")
  const [testFixtures, setTestFixtures] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [error, setError] = useState<unknown>(null)

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
      setJurisdiction((getCfg("jurisdiction") ?? "US"))
      setRuleVersion((getCfg("rule_version") ?? "v1.0"))
      setTestFixtures(getCfg("test_fixtures") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/jurisdiction`, { config: jurisdiction })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/rule_version`, { config: ruleVersion })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/test_fixtures`, { config: testFixtures ? "1" : "0" })
      await load()
      setNotice("Jurisdiction rules config saved.")
    } catch (e) { setActionError(errorMessage(e, "The jurisdiction config could not be saved.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Jurisdiction rules require SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Jurisdiction Rules"><TableSkeleton rows={4} cols={3} /></LoadingRegion></Layout>

  const jurisdictionLabel = JURISDICTION_OPTIONS.find(o => o.value === jurisdiction)?.label ?? jurisdiction

  return (
    <Layout>
      <PageHeader compact title="Jurisdiction Rules + Versioning + Test Fixtures" description="PY-09 · jurisdiction rules + versioning + test fixtures · depends PY-08 + AD-07 + PY-01 · reads /clients/:id/feature-flags (SuperAdmin)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {error ? <RetryableAlert err={error} title="Could not load jurisdiction config" fallback="Could not resolve configuration." onRetry={load} /> : null}
        <SectionCard compact title="Jurisdiction rules configuration" description="Per-tenant from /clients/:id/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="jr-jurisdiction">Jurisdiction</label>
              <select
                id="jr-jurisdiction"
                value={jurisdiction}
                onChange={e => setJurisdiction(e.target.value)}
                className="w-full rounded border px-3 py-2"
                disabled={!canWrite || saving || !clientId}
              >
                {JURISDICTION_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="jr-version">Rule version</label>
              <Input id="jr-version" value={ruleVersion} onChange={e => setRuleVersion(e.target.value)} disabled={!canWrite || saving || !clientId} className="font-mono" placeholder="v1.0" />
            </div>
            <div>
              <label htmlFor="jr-fixtures">Test fixtures</label>
              <div className="flex items-center gap-2">
                <input
                  id="jr-fixtures"
                  type="checkbox"
                  checked={testFixtures}
                  onChange={e => setTestFixtures(e.target.checked)}
                  disabled={!canWrite || saving || !clientId}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-fg">Enable test fixtures</span>
              </div>
            </div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save jurisdiction config"}</Button>
        </SectionCard>
        <PendingVerificationAlert />
        <SectionCard compact title="Payroll compliance reports (slice 4)" description="GET /reports/payroll?jurisdiction=IN&period=YYYY-MM — 4 India slices (Payroll Register, TDS, PF/ESI, PT by state) — gated on verified pack. Verified shows in-standard v1.0.0; pending returns 409.">
          <p className="text-sm text-text-secondary">Open <a href="/admin/compliance" className="text-brand-700 hover:underline">Compliance Center → Payroll IN tab</a> to load the four reports for a period (YYYY-MM). History: Pay runs list/detail show rule_pack_id/version/jurisdiction/currency; IN history shows INR and PT column where applicable.</p>
          <p className="text-xs text-text-secondary mt-2">Payslip PDF: GET /payroll/payslips/{"{id}"}/pdf renders gross/net/deductions, statutory breakdown (BASIC, TAX_*, REBATE_87A, PF_EE/ER, ESI_EE/ER, PT_{"{STATE}"}) with watermark when pending; lineage (rule_pack_id + version/effective dates + inputs_json). US unchanged.</p>
        </SectionCard>
        <SectionCard compact title="Active jurisdiction config" description="The persisted per-tenant configuration — what the backend actually reads.">
          <div className="table-scroll">
            <table className="w-full text-sm">
              <caption className="sr-only">Active jurisdiction configuration</caption>
              <thead><tr className="border-b"><th scope="col" className="text-left">Jurisdiction</th><th scope="col" className="text-left">Rule version</th><th scope="col" className="text-left">Test fixtures</th></tr></thead>
              <tbody>
                <tr className="border-b">
                  <td>{jurisdictionLabel} ({jurisdiction})</td>
                  <td className="font-mono">{ruleVersion}</td>
                  <td>{testFixtures ? "Enabled" : "Disabled"}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </SectionCard>
        <div className="text-xs text-fg-muted">PY-09 · R5 · depends PY-08 + AD-07 + PY-01 · configuration shown is the persisted tenant config.</div>
      </div>
    </Layout>
  )
}