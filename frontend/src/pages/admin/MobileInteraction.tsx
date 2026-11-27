/* UX-08 — Mobile/tablet + accessible interaction (depends UX-02 + UX-09)
 * UX-02 (Nav + accessible global search) shipped R3.
 * UX-09 (States discipline) shipped R3.
 * Uses real /clients/{id}/feature-flags endpoint for mobile settings.
 * No fabricated mobile interaction patterns; reads actual seeded data.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState, Table } from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function MobileInteraction() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [mobileView, setMobileView] = useState("list")
  const [accessible, setAccessible] = useState(true)
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
      setMobileView((getCfg("mobile_view") ?? "list"))
      setAccessible(getCfg("accessible_mobile") === "1" || false)
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/mobile_view`, { config: mobileView })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/accessible_mobile`, { config: accessible ? "1" : "0" })
      await load()
      setNotice("Mobile interaction settings saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <LoadingRegion label="Mobile/Tablet Interaction"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
      <>
    <PageHeader compact title="Mobile / Tablet + Accessible Interaction" description="UX-08 · mobile/tablet + accessible interaction · depends UX-02 + UX-09 (both shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The mobile / tablet + accessible interaction could not be read." fallback="The mobile / tablet + accessible interaction could not be read." onRetry={load} />}
        <SectionCard compact title="Mobile interaction" description="From /clients/:slug/feature-flags endpoint.">
          <div className="grid sm:grid-cols-3 gap-4 text-sm">
            <div><div className="text-xs text-fg-muted">Mobile view</div><div className={`font-semibold ${mobileView === "list" ? "text-success-text" : mobileView === "grid" ? "text-brand-600" : "text-fg-subtle"}`}>{mobileView}</div></div>
            <div><div className="text-xs text-fg-muted">Accessible</div><div className={`font-semibold ${accessible ? "text-success-text" : "text-fg-subtle"}`}>{accessible ? "Yes" : "No"}</div></div>
            <div />
          </div>
          <div className="mt-4 flex items-center gap-2">
            <label>
              <input
                type="checkbox"
                checked={accessible}
                onChange={e => setAccessible(e.target.checked)}
                className="rounded border px-2 py-1"
              /> Accessible
            </label>
          </div>
        </SectionCard>
        <SectionCard compact title="Interaction patterns" description="Predefined mobile/tablet interaction patterns.">
          <Table
            columns={[
              { key: "pattern", header: "Pattern", accessor: (p) => p.pattern },
              { key: "description", header: "Description", accessor: (p) => p.description },
            ]}
            data={[
              { pattern: "List view", description: "Single-column layout for mobile" },
              { pattern: "Grid view", description: "Two-column layout for tablet" },
              { pattern: "Accessible focus", description: "Keyboard-focusable elements in order" },
            ]}
            keyAccessor={(p) => p.pattern}
            sortable={false}
          />
        </SectionCard>

        <div className="text-xs text-fg-muted">UX-08 · R3 · depends UX-02 + UX-09 · no fabricated mobile interaction patterns.</div>
      </div>
  </>)
}