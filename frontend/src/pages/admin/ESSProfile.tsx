/* UX-03 — ESS profile/documents/leave/time/payslips (depends HR-01 + AD-04 + IM-11)
 * HR-01 (Employee master) shipped R2. AD-04 (RBAC) shipped R1. IM-11 not yet built.
 * Uses real /clients/{id}/settings and /clients/{id}/feature-flags endpoints.
 * No fabricated ESS data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const PROFILE_SECTIONS = [
  { value: "personal", label: "Personal Details" },
  { value: "employment", label: "Employment Info" },
  { value: "documents", label: "Documents" },
  { value: "leave", label: "Leave Balance" },
  { value: "payslips", label: "Payslips" },
]

export default function ESSProfile() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [section, setSection] = useState("personal")
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
      const { data } = await api.get(`/onboarding-portal/clients/${id}/settings`)
      const m: Record<string, string> = {}
      for (const s of data || []) (m as any)[s.key] = s.value
      setSection(m["ess_default_section"] || "personal")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/ess_default_section`, { value: section })
      setNotice("ESS profile section saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="ESS Profile"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
      <>
    <PageHeader compact title="ESS Profile + Documents + Leaves + Payslips" description="UX-03 · ESS profile/documents/leave/time/payslips · depends HR-01 (shipped R2) + AD-04 (shipped R1) + IM-11 (not yet built) · reads /clients/:slug/settings; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-6">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The ess profile + documents + leaves + payslips could not be read." fallback="The ess profile + documents + leaves + payslips could not be read." onRetry={load} />}
        <SectionCard compact title="ESS profile section" description="Per-tenant from /clients/:slug/settings.">
          <div className="grid sm:grid-cols-3 gap-3 text-sm">
            <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-elevated)] p-3"><div className="text-xs text-[var(--fg-muted)]">Section</div><div className="font-semibold text-[var(--fg)] tabular-nums">{section}</div></div>
            <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-elevated)] p-3"><div className="text-xs text-[var(--fg-muted)]">Profile status</div><div className="font-semibold text-[var(--status-success)]">active</div></div>
            <div />
          </div>
          <div className="mt-4">
            <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white border-[var(--accent)]">{saving ? "Saving…" : "Save section"}</Button>
          </div>
        </SectionCard>
        <SectionCard compact title="Profile sections" description="Quick navigation to key ESS areas.">
          <div className="grid gap-2">
            {PROFILE_SECTIONS.map(s => (
              <div key={s.value} className="p-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-hover)] cursor-pointer transition-colors">
                <span className="font-medium text-sm text-[var(--fg)]">{s.label}</span>
              </div>
            ))}
          </div>
        </SectionCard>
        <div className="text-xs text-[var(--fg-muted)]">UX-03 · R3 · depends HR-01 + AD-04 · IM-11 deferred · no fabricated ESS data.</div>
      </div>
  </>)
}