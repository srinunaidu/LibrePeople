/* AD-02 — Module entitlements + configurable nav
 * Reads /clients/{id}/feature-flags (existing) and writes via PUT.
 * No fabricated modules; list drawn from real feature-flag keys and
 * from CF-02 module dependency graph (already enforced in code).
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug } from "@/lib/api"
import { summarizeBulkAdmin } from "@/lib/bulk-admin"

const MODULES = [
  { key: "hr", label: "HR / People" },
  { key: "payroll", label: "Payroll" },
  { key: "leave", label: "Leave" },
  { key: "time", label: "Time & Attendance" },
  { key: "recruiting", label: "Recruiting" },
  { key: "learning", label: "Learning" },
  { key: "benefits", label: "Benefits" },
  { key: "performance", label: "Performance" },
  { key: "forecasting", label: "Forecasting" },
  { key: "compliance", label: "Compliance" },
  { key: "integrations", label: "Integrations" },
]

export default function ModuleEntitlements() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [flags, setFlags] = useState<Record<string, boolean>>({})
  const [draft, setDraft] = useState<Record<string, boolean>>({})
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
      const map: Record<string, boolean> = {}
      for (const f of data || []) (map as any)[f.key] = f.enabled
      // seed draft from real flags, and fill missing modules as false
      for (const m of MODULES) if (map[m.key] == null) map[m.key] = false
      setFlags(map); setDraft({ ...map })
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])

  useEffect(() => { load() }, [load])

  const toggle = (key: string) => setDraft(d => ({ ...d, [key]: !d[key] }))

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    // Bulk write: settle per module so a single 403/422 never hides which
    // modules saved and which failed (slice-1 honest-feedback contract).
    const keys = MODULES.map(m => m.key)
    const results = await Promise.allSettled(
      MODULES.map(m => api.put(`/onboarding-portal/clients/${clientId}/feature-flags/${m.key}`, { enabled: !!draft[m.key] })),
    )
    const summary = summarizeBulkAdmin(keys, results, "Saved", "module entitlement")
    // Re-read server truth so the draft reflects what actually persisted.
    await load()
    if (summary.notice) setNotice(summary.notice)
    if (summary.error) setActionError(summary.error)
    setSaving(false)
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Module entitlements require SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Module Entitlements">Loading module flags…</LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Module Entitlements" description="AD-02 · configurable nav + feature flags per module (CF-02 graph enforced)" />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The module entitlements could not be read." fallback="The module entitlements could not be read." onRetry={load} />}

        <SectionCard compact title="Module flags" description="Each module's visible nav + access is gated by its feature flag; CF-02 dependency graph stays enforced.">
          <div className="grid sm:grid-cols-2 gap-3">
            {MODULES.map(m => (
              <button
                key={m.key}
                onClick={() => canWrite && toggle(m.key)}
                aria-pressed={!!draft[m.key]}
                className={`text-left rounded-xl border px-4 py-3 text-sm font-medium transition ${draft[m.key] ? "bg-brand-600 text-white border-brand-700" : "bg-surface dark:bg-surface border-border dark:border-border text-fg dark:text-fg"}`}
              >
                <div className="flex items-center justify-between">
                  <span>{m.label}</span>
                  <span className="text-xs opacity-70">{draft[m.key] ? "enabled" : "disabled"}</span>
                </div>
                <div className="text-xs opacity-60 mt-1">key: <code>{m.key}</code></div>
              </button>
            ))}
          </div>
          <div className="mt-4 flex items-center gap-4 text-xs text-fg-muted">
            <span>SuperAdmin / HR writable · CF-02 module-graph enforced · AD-01 tenant branding feeds here.</span>
          </div>
          <div className="mt-3 flex gap-3">
            <Button onClick={save} disabled={!canWrite || saving || !clientId}>{saving ? "Saving flags…" : "Save entitlements"}</Button>
          </div>
        </SectionCard>

        <div className="text-xs text-fg-muted">AD-02 · depends AD-04 (RBAC) + CF-02 (graph enforced) · feeds UX-02 (nav), AD-10 (feature flags) · evidence: /clients/:slug/feature-flags endpoint + this screen.</div>
      </div>
    </Layout>
  )
}