import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Switch,Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, Table } from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { listClients, listFeatureFlags, updateFeatureFlag, errorMessage } from "@/lib/api"

export default function FeatureFlags() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const isSuperAdmin = user?.role === "SuperAdmin"
  const [clientId, setClientId] = useState<number | null>(null)
  const [canWrite, setCanWrite] = useState(false)
  const [flags, setFlags] = useState<Record<string, boolean>>({})
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [error, setError] = useState<unknown | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null); setNotice("")
    try {
      if (isSuperAdmin) {
        // List all clients and find the one matching tenant slug
        const clients = await listClients()
        const match = clients.find(c => c.slug === tenant?.slug)
        if (!match) {
          setError("No company record found for this install")
          setClientId(null)
          setCanWrite(false)
          return
        }
        setClientId(match.id)
        setCanWrite(true)
        // Load feature flags for this client
        const data = await listFeatureFlags(match.id)
        const m: Record<string, boolean> = {}
        for (const f of data || []) {
          (m as any)[f.key] = f.enabled
        }
        setFlags(m)
      } else {
        // HR or other non-SuperAdmin roles: read-only
        setClientId(null)
        setCanWrite(false)
        // Could optionally load a client's flags if tenant is known, but not needed
      }
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [isSuperAdmin, tenant])

  useEffect(() => { load() }, [load])

  const toggleFlag = async (key: string, next: boolean) => {
    if (!canWrite || !clientId) return

    const prev = flags[key]
    // Optimistic update
    setFlags({ ...flags, [key]: next })
    setSavingKey(key)
    setNotice(""); setActionError("")

    try {
      await updateFeatureFlag(clientId, key, next)
      setNotice(`Flag "${key}" updated.`)
      setSavingKey(null)
    } catch (e) {
      setActionError(errorMessage(e, `Flag "${key}" could not be updated.`))
      // Rollback on error
      setFlags({ ...flags, [key]: prev })
      setSavingKey(null)
    }
  }

  if (!isSuperAdmin) {
    return (
      <Layout>
        <PageHeader compact title="Feature Flags & Diagnostics" description="AD-10 · install-level release tracking + diagnostics (feeds AD-02 nav gating)" />
        <EmptyState title="Not visible for your role" description={`Feature flags require SuperAdmin; your role is ${user?.role || "unknown"}.`} />
      </Layout>
    )
  }

  if (loading) return <Layout><LoadingRegion label="Feature Flags">Loading flags…</LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Feature Flags & Diagnostics" description="AD-10 · install-level release tracking + diagnostics (feeds AD-02 nav gating)" />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-6">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The feature flags & diagnostics could not be read." fallback="The feature flags & diagnostics could not be read." onRetry={load} />}

        <SectionCard compact title="Install flags" description="From the install company /onboarding-portal/clients/:id/feature-flags endpoint.">
          <Table
            columns={[
              { key: "key", header: "Key", accessor: ([k]) => <span className="px-0 font-mono text-xs">{k}</span> },
              {
                key: "enabled",
                header: "Enabled",
                accessor: ([k, v]) => (
                  <Switch
                    checked={v}
                    onChange={e => toggleFlag(k, e.target.checked)}
                    disabled={!canWrite || savingKey === k}
                    aria-label={`Toggle ${k}`}
                  />
                ),
              },
            ]}
            data={Object.entries(flags)}
            keyAccessor={([k]) => k}
            emptyMessage="No feature flags are configured for this install yet."
            sortable={false}
          />
          {!canWrite && (
            <div className="mt-3 text-xs text-[var(--fg-muted)]">
              SuperAdmin controls changes.
            </div>
          )}
        </SectionCard>

        <div className="text-xs text-[var(--fg-muted)]">AD-10 · depends AD-04 + AD-07 · feeds AD-02 (nav gating), AD-06 (integration health). No fabricated release-gate claims.</div>
      </div>
    </Layout>
  )
}