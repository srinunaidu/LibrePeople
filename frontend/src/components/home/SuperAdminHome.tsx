import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTenantNav } from "@/lib/tenantPath"
import { Layout } from "@/components/Layout"
import {
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  KPICard, StatusPill, Table } from "@/components/ui"
import { NeedsAction, type NeedItem } from "@/components/home/NeedsAction"
import {
  IconBuilding,
  IconChart,
  IconGrid,
  IconInbox,
  IconShield,
  IconTarget,
} from "@/components/icons"
import api from "@/lib/api"

interface Client { id: number; name: string; slug: string; status: string; primary_color: string }
interface Integration { id: number; name: string; kind: string; status: string; has_secret: boolean }
interface FeatureFlag { id: number; key: string; enabled: boolean }
interface AuditEntry { id: number; actor_name?: string; action: string; entity_type: string; created_at?: string }

// D3 (portals-completion): no sparkline/trend props on portal KPIs — there is
// no backend aggregation for deltas, so every KPI shows a live value + hint.

export default function SuperAdminHome() {
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [clients, setClients] = useState<Client[]>([])
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [cases, setCases] = useState<any[]>([])
  const [requisitions, setRequisitions] = useState<any[]>([])
  const [violations, setViolations] = useState<any[]>([])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [c, a, cs, r, v] = await Promise.all([
          api.get("/onboarding-portal/clients").catch(() => ({ data: [] })),
          api.get("/reports/audit?limit=10").catch(() => ({ data: [] })),
          api.get("/core-hr/cases").catch(() => ({ data: [] })),
          api.get("/requisitions/").catch(() => ({ data: [] })),
          api.get("/compliance/compliance-violations").catch(() => ({ data: [] })),
        ])
        if (cancelled) return
        setClients(c.data || [])
        setAudit(a.data || [])
        setCases(cs.data || [])
        setRequisitions(r.data || [])
        setViolations(v.data || [])

        // Load integrations + flags for the first client if any
        if (c.data && c.data.length > 0) {
          const cid = c.data[0].id
          const [i, f] = await Promise.all([
            api.get(`/onboarding-portal/clients/${cid}/integrations`).catch(() => ({ data: [] })),
            api.get(`/onboarding-portal/clients/${cid}/feature-flags`).catch(() => ({ data: [] })),
          ])
          if (!cancelled) {
            setIntegrations(i.data || [])
            setFlags(f.data || [])
          }
        }
      } catch {
        if (!cancelled) setError("We couldn't load the admin console.")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const openCases = cases.filter((c) => c.status === "Open" || c.status === "In Progress").length
  const openReqs = requisitions.filter((r) => r.status === "Open").length
  const openViolations = violations.filter((v) => v.status === "Open").length
  const failedIntegrations = integrations.filter((i) => i.status === "failed" || i.status === "error").length
  const disabledFlags = flags.filter((f) => !f.enabled).length

  const needs: NeedItem[] = [
    { id: "cases", label: "Open HR cases", count: openCases, description: "Employee cases needing resolution", actionLabel: "Review", onAction: () => { navigate(tenantNav.to("/admin/er-cases")) }, tone: "rose" },
    { id: "requisitions", label: "Open requisitions", count: openReqs, description: "Roles awaiting candidates", actionLabel: "View", onAction: () => { navigate(tenantNav.to("/recruiting")) }, tone: "brand" },
    { id: "violations", label: "Compliance violations", count: openViolations, description: "Policy or rule violations", actionLabel: "Review", onAction: () => { navigate(tenantNav.to("/platform/compliance")) }, tone: "rose" },
    { id: "integrations", label: "Failed integrations", count: failedIntegrations, description: "Integration connections that need attention", actionLabel: "Fix", onAction: () => { navigate(tenantNav.to("/platform/integrations")) }, tone: "rose" },
  ]

  if (loading) {
    return (
      <Layout>
        <PageHeader compact icon={<IconShield />} title="Admin Console" description="Tenant health and system overview." />
        <LoadingRegion label="Loading admin data">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-0">
            {Array.from({ length: 8 }).map((_, i) => <div key={i} className="skeleton h-28" />)}
          </div>
        </LoadingRegion>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader
        compact
        icon={<IconShield />}
        title="Admin Console"
        description="Tenant health, feature flags, integrations, and system audit highlights."
      />

      {error && <Alert tone="error">{error}</Alert>}

      {needs.length > 0 && <NeedsAction title="Needs your action" items={needs} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-0">
        <KPICard
          label="Tenants"
          value={clients.length}
          hint={`${clients.filter((c) => c.status === "active").length} active`}
          icon={<IconBuilding className="w-5 h-5" />}
          tone="brand"
        />
        <KPICard
          label="Feature Flags"
          value={flags.length}
          hint={`${disabledFlags} disabled`}
          icon={<IconGrid className="w-5 h-5" />}
          tone="green"
        />
        <KPICard
          label="Integrations"
          value={integrations.length}
          hint={`${failedIntegrations} failed`}
          icon={<IconTarget className="w-5 h-5" />}
          tone="teal"
        />
        <KPICard
          label="HR Cases"
          value={cases.length}
          hint={`${openCases} open`}
          icon={<IconInbox className="w-5 h-5" />}
          tone="violet"
        />
      </div>

      <div className="card p-4 text-xs text-fg-muted flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="font-semibold text-fg">Administration</span>
        <button className="action-link" onClick={() => { navigate(tenantNav.to("/admin/users")) }}>Users</button>
        <button className="action-link" onClick={() => { navigate(tenantNav.to("/admin/entitlements")) }}>Module entitlements</button>
        <button className="action-link" onClick={() => { navigate(tenantNav.to("/admin/branding")) }}>Tenant branding</button>
        <button className="action-link" onClick={() => { navigate(tenantNav.to("/admin/feature-flags")) }}>Feature flags</button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-0">
        {/* Tenant health */}
        <SectionCard compact icon={<IconBuilding />} title="Tenant health" description="Registered tenants and their status.">
          {clients.length === 0 ? (
            <EmptyState title="No tenants" description="Create a tenant in Client Onboarding to get started." />
          ) : (
            <Table
              columns={[
                { key: "tenant", header: "Tenant", accessor: (c) => <span className="font-medium">{c.name}</span> },
                { key: "slug", header: "Slug", accessor: (c) => <span className="font-mono text-xs text-fg-muted">{c.slug}</span> },
                { key: "status", header: "Status", accessor: (c) => <StatusPill status={c.status} tone={c.status === "active" ? "green" : "slate"} /> },
              ]}
              data={clients}
              keyAccessor={(c) => c.id}
              caption="Tenant health overview"
              sortable={false}
            />
          )}
          <div className="flex justify-end px-5 py-3">
            <button className="action-link" onClick={() => { navigate(tenantNav.to("/client-onboarding")) }}>Open client onboarding</button>
          </div>
        </SectionCard>

        {/* Feature flags */}
        <SectionCard compact icon={<IconGrid />} title="Feature flags" description="Enabled features for the primary tenant.">
          {flags.length === 0 ? (
            <EmptyState title="No feature flags" description="Feature flags are configured per tenant." />
          ) : (
            <ul className="divide-y divide-border-subtle">
              {flags.slice(0, 10).map((f) => (
                <li key={f.id} className="flex items-center justify-between px-5 py-2.5 hover:bg-surface-hover">
                  <span className="text-sm text-fg">{f.key}</span>
                  <StatusPill status={f.enabled ? "On" : "Off"} tone={f.enabled ? "green" : "slate"} />
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-0">
        <SectionCard compact icon={<IconChart />} title="Audit highlights" description="The 10 most recent recorded actions.">
          {audit.length === 0 ? (
            <EmptyState title="No audit entries" description="Actions will appear here as they happen." />
          ) : (
            <ul className="divide-y divide-border-subtle">
              {audit.slice(0, 10).map((a) => (
                <li key={a.id} className="flex items-center gap-3 px-5 py-2.5 hover:bg-surface-hover">
                  <span className="text-xs text-fg-muted whitespace-nowrap">{a.created_at ? new Date(a.created_at).toLocaleDateString() : "—"}</span>
                  <span className="text-sm text-fg flex-1 truncate">{a.actor_name || "System"} · {a.action}</span>
                  <span className="text-xs text-fg-muted">{a.entity_type}</span>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        <SectionCard compact icon={<IconShield />} title="Integrations" description="Connected services for the primary tenant.">
          {integrations.length === 0 ? (
            <EmptyState title="No integrations" description="Configure integrations in Client Onboarding." />
          ) : (
            <ul className="divide-y divide-border-subtle">
              {integrations.map((i) => (
                <li key={i.id} className="flex items-center gap-3 px-5 py-2.5 hover:bg-surface-hover">
                  <span className="text-sm font-medium text-fg flex-1">{i.name}</span>
                  <span className="text-xs text-fg-muted">{i.kind}</span>
                  <StatusPill status={i.status} tone={i.status === "active" ? "green" : i.status === "failed" ? "rose" : "slate"} />
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </div>

      <div className="card p-4 text-xs text-fg-muted flex items-center gap-2">
        <StatusPill status="SuperAdmin" />
        You have full access to all modules. Use the workspace rail to navigate to any area.
      </div>

      <div className="card p-4 text-xs text-fg-muted flex flex-wrap items-center gap-x-3 gap-y-1">
        <StatusPill status={`v${__BUILD__.version}`} />
        <span>
          build <code className="text-fg">{__BUILD__.commit.slice(0, 7)}</code>
        </span>
        <span aria-label="Release build time">
          last updated {new Date(__BUILD__.time).toLocaleString("en-GB", { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" })} UTC
        </span>
      </div>
    </Layout>
  )
}
