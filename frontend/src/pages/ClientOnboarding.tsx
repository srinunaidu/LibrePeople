import { useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {
  Alert,
  EmptyState,
  Meter,
} from "@/components/ui/feedback"
import { RetryableAlert, Table } from "@/components/ui"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, SectionCard } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { StatusPill } from "@/components/ui/status-pill"
import { Button } from "@/components/ui/button"
import { Input, Select, Textarea, Checkbox, Switch } from "@/components/ui/inputs"
import { Field, PageHeader } from "@/components/ui/layout"
import { IconBuilding, IconPlus, IconAlert, IconDownload, IconRefresh, IconFile, IconX } from "@/components/icons"
import api from "@/lib/api"
import { useAuth } from "@/context/AuthContext"
import type {
  Client,
  FeatureFlag,
  Integration,
  MigrationJob,
  OnboardingStep,
} from "@/types"

interface ClientSetting { id: number; key: string; value: string | null }

export default function ClientOnboarding() {
  const { user } = useAuth()
  const isSuperAdmin = user?.role === "SuperAdmin"
  const [clients, setClients] = useState<Client[]>([])
  const [selected, setSelected] = useState<number | "">("")
  const [tab, setTab] = useState("profile")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [busy, setBusy] = useState(false)

  type DetailKey = "flags" | "integrations" | "migrations" | "settings" | "onboarding" | "docs"
  const [failedDetail, setFailedDetail] = useState<Record<string, boolean>>({})

  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [migrations, setMigrations] = useState<MigrationJob[]>([])
  const [settings, setSettings] = useState<ClientSetting[]>([])
  const [steps, setSteps] = useState<OnboardingStep[]>([])
  const [progress, setProgress] = useState({ total: 0, completed: 0, percent: 0 })
  const [docs, setDocs] = useState("")

  const [clientForm, setClientForm] = useState({
    name: "", slug: "", industry: "", country: "India", timezone: "Asia/Kolkata",
    locale: "en-IN", currency: "INR", primary_color: "#2563EB", secondary_color: "#1F2937",
    contact_name: "", contact_email: "",
  })
  const [intForm, setIntForm] = useState({
    name: "", kind: "oracle_adb", endpoint: "", username: "", secret: "", notes: "",
  })
  const [settingForm, setSettingForm] = useState({ key: "", value: "" })
  const [migForm, setMigForm] = useState({ integration_id: "", entity: "employees", total: 100 })

  const loadClients = async () => {
    try {
      const r = await api.get("/onboarding-portal/clients")
      setClients(r.data)
      if (r.data.length && selected === "") setSelected(r.data[0].id)
    } catch {
      setError("Failed to load clients")
    }
  }

  const loadClientData = async (id: number) => {
    setBusy(true)
    setError("")
    try {
      const results = await Promise.allSettled([
        api.get(`/onboarding-portal/clients/${id}/feature-flags`),
        api.get(`/onboarding-portal/clients/${id}/integrations`),
        api.get(`/onboarding-portal/clients/${id}/migrations`),
        api.get(`/onboarding-portal/clients/${id}/settings`),
        api.get(`/onboarding-portal/clients/${id}/onboarding`),
        api.get("/onboarding-portal/docs/migration-api"),
      ])
      const detailKeys: DetailKey[] = ["flags", "integrations", "migrations", "settings", "onboarding", "docs"]
      const failures: Record<string, boolean> = {}
      detailKeys.forEach((key, i) => {
        const r = results[i]
        if (r.status !== "fulfilled") {
          failures[key] = true
          return
        }
        const data = r.value.data
        if (key === "flags") setFlags(data)
        else if (key === "integrations") setIntegrations(data)
        else if (key === "migrations") setMigrations(data)
        else if (key === "settings") setSettings(data)
        else if (key === "onboarding") {
          setSteps(data.steps)
          setProgress({ total: data.total, completed: data.completed, percent: data.percent })
        } else if (key === "docs") setDocs(data.content)
      })
      setFailedDetail(failures)
      const failedTabs = (Object.keys(failures) as DetailKey[]).length
      if (failedTabs === detailKeys.length) {
        setError("Failed to load client data")
      }
    } catch {
      setError("Failed to load client data")
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (isSuperAdmin) loadClients()
  }, [isSuperAdmin])

  useEffect(() => {
    if (isSuperAdmin && selected !== "") loadClientData(Number(selected))
  }, [isSuperAdmin, selected])

  const act = async (fn: () => Promise<unknown>, msg: string) => {
    setError("")
    setNotice("")
    try {
      const res = await fn()
      setNotice(msg)
      if (selected !== "") await loadClientData(Number(selected))
      return res
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Action failed")
      return null
    }
  }

  const sel = clients.find((c) => c.id === selected)

  const tabs = [
    { key: "profile", label: "Profile" },
    { key: "flags", label: "Feature Flags" },
    { key: "integrations", label: "Integrations" },
    { key: "migrations", label: "Migrations" },
    { key: "settings", label: "Settings" },
    { key: "onboarding", label: "Onboarding" },
    { key: "docs", label: "Migration Docs" },
  ]

  if (!isSuperAdmin) {
    return (
      <Layout>
        <PageHeader compact
          icon={<IconBuilding />}
          title="Client Onboarding Portal"
          description="Provision tenants, configure branding and feature flags, wire up integrations, and run data migrations."
        />
        <RetryableAlert err={user?.role || "unknown"} title="Not visible for your role" fallback="Not visible for your role." />
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader compact
        icon={<IconBuilding />}
        title="Client Onboarding Portal"
        description="Provision tenants, configure branding and feature flags, wire up integrations, and run data migrations."
      />

      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        {/* Client sidebar */}
        <SectionCard compact title="Clients" icon={<IconPlus className="h-4 w-4" />}>
          {clients.length === 0 ? (
            <EmptyState
              icon={<IconBuilding />}
              title="No clients yet"
              description="Create your first client to begin onboarding."
            />
          ) : (
            <div className="space-y-1 mb-4">
              {clients.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setSelected(c.id)}
                  aria-current={selected === c.id ? "true" : undefined}
                  className={`w-full text-left px-3 py-2.5 rounded-md text-sm transition-colors ${
                    selected === c.id
                      ? "bg-[rgba(37,99,235,0.12)] text-primary"
                      : "hover:bg-surface-inset text-fg"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium truncate">{c.name}</span>
                    <StatusPill status={c.status} dot />
                  </div>
                  <span className="block text-xs text-fg-muted mt-0.5 truncate">{c.slug}</span>
                </button>
              ))}
            </div>
          )}

          <details className="mt-2">
            <summary className="cursor-pointer text-sm font-medium text-brand-600">
              + New client
            </summary>
            <div className="mt-3 space-y-3">
              <Field label="Client name" htmlFor="nc-name" required>
                <Input
                  id="nc-name"
                  placeholder="Name"
                  aria-label="Client name"
                  value={clientForm.name}
                  onChange={(e) => setClientForm({ ...clientForm, name: e.target.value })}
                />
              </Field>
              <Field label="Client slug" htmlFor="nc-slug" required>
                <Input
                  id="nc-slug"
                  placeholder="Slug"
                  aria-label="Client slug"
                  value={clientForm.slug}
                  onChange={(e) => setClientForm({ ...clientForm, slug: e.target.value })}
                />
              </Field>
              <Field label="Industry" htmlFor="nc-industry">
                <Input
                  id="nc-industry"
                  placeholder="Industry"
                  aria-label="Industry"
                  value={clientForm.industry}
                  onChange={(e) => setClientForm({ ...clientForm, industry: e.target.value })}
                />
              </Field>
              <Field label="Contact name" htmlFor="nc-cname">
                <Input
                  id="nc-cname"
                  placeholder="Contact name"
                  aria-label="Contact name"
                  value={clientForm.contact_name}
                  onChange={(e) => setClientForm({ ...clientForm, contact_name: e.target.value })}
                />
              </Field>
              <Field label="Contact email" htmlFor="nc-cemail">
                <Input
                  id="nc-cemail"
                  type="email"
                  placeholder="Contact email"
                  aria-label="Contact email"
                  value={clientForm.contact_email}
                  onChange={(e) => setClientForm({ ...clientForm, contact_email: e.target.value })}
                />
              </Field>
              <Field label="Primary color" htmlFor="nc-color">
                <div className="flex gap-2 items-center">
                  <input
                    id="nc-color"
                    type="color"
                    className="border border-border rounded-md h-8 w-12"
                    aria-label="Primary colour"
                    value={clientForm.primary_color}
                    onChange={(e) => setClientForm({ ...clientForm, primary_color: e.target.value })}
                  />
                  <span className="text-xs text-fg-muted">Primary color</span>
                </div>
              </Field>
              <Button
                className="w-full"
                disabled={!clientForm.name || !clientForm.slug}
                onClick={async () => {
                  setError("")
                  setNotice("")
                  try {
                    const res = await api.post("/onboarding-portal/clients", clientForm)
                    const slug = res.data?.slug || clientForm.slug
                    setNotice(
                      `Client created with default flags & steps. Workspace URL: /t/${slug}/dashboard — sign in as a SuperAdmin or HR user to enter it (path-based workspace; Render free tier has no custom subdomains).`,
                    )
                    await loadClients()
                    setSelected(res.data.id)
                  } catch (e: any) {
                    setError(e?.response?.data?.detail || "Action failed")
                  }
                }}
              >
                Create client
              </Button>
            </div>
          </details>
        </SectionCard>

        {/* Main panel */}
        <div className="lg:col-span-3">
          {!selected ? (
            <Card className="p-10 text-center">
              <EmptyState
                icon={<IconBuilding />}
                title="Select or create a client"
                description="Choose a client from the sidebar or create a new one to begin onboarding."
              />
            </Card>
          ) : busy ? (
            <Card className="p-10 text-center">
              <Skeleton className="h-4 w-32 mx-auto" />
            </Card>
          ) : (
            <>
              {sel && (
                <SectionCard compact
                  title={sel.name}
                  description={`${sel.slug} · ${sel.industry || "—"} · ${sel.timezone}`}
                  actions={
                    <>
                      <a
                        href={`/t/${sel.slug}/dashboard`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-brand-600 hover:text-brand-700 underline text-sm"
                      >
                        Open workspace
                      </a>
                      <StatusPill status={sel.status} dot />
                    </>
                  }
                  className="mb-5"
                >
                  <p className="text-sm mt-2">
                    Workspace: <span className="font-mono text-xs">/t/{sel.slug}/dashboard</span>
                  </p>
                  <Meter
                    percent={progress.percent}
                    label={`Onboarding ${progress.completed} of ${progress.total} steps complete`}
                    className="mt-4"
                  />
                </SectionCard>
              )}

              <nav className="flex gap-1 mb-4 border-b" aria-label="Client onboarding tabs">
                {tabs.map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setTab(t.key)}
                    className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
                      tab === t.key
                        ? "border-brand-600 text-brand-600"
                        : "border-transparent text-fg-muted hover:text-fg"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </nav>

              {tab === "profile" && sel && (
                <SectionCard compact title="Company Profile & Branding">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Field label="Name" htmlFor="pf-name" required>
                      <Input
                        id="pf-name"
                        defaultValue={sel.name}
                        onBlur={(e) => act(() => api.put(`/onboarding-portal/clients/${sel.id}`, { name: e.target.value }), "Updated")}
                      />
                    </Field>
                    <Field label="Industry" htmlFor="pf-industry">
                      <Input
                        id="pf-industry"
                        defaultValue={sel.industry || ""}
                        onBlur={(e) => act(() => api.put(`/onboarding-portal/clients/${sel.id}`, { industry: e.target.value }), "Updated")}
                      />
                    </Field>
                    <Field label="Timezone" htmlFor="pf-timezone" required>
                      <Input
                        id="pf-timezone"
                        defaultValue={sel.timezone}
                        onBlur={(e) => act(() => api.put(`/onboarding-portal/clients/${sel.id}`, { timezone: e.target.value }), "Updated")}
                      />
                    </Field>
                    <Field label="Locale" htmlFor="pf-locale" required>
                      <Input
                        id="pf-locale"
                        defaultValue={sel.locale}
                        onBlur={(e) => act(() => api.put(`/onboarding-portal/clients/${sel.id}`, { locale: e.target.value }), "Updated")}
                      />
                    </Field>
                    <Field label="Currency" htmlFor="pf-currency" required>
                      <Input
                        id="pf-currency"
                        defaultValue={sel.currency || "INR"}
                        onBlur={(e) => act(() => api.put(`/onboarding-portal/clients/${sel.id}`, { currency: e.target.value.toUpperCase() }), "Updated")}
                      />
                    </Field>
                    <Field label="Primary color" htmlFor="pf-color">
                      <Input
                        id="pf-color"
                        type="color"
                        defaultValue={sel.primary_color}
                        onChange={(e) => act(() => api.put(`/onboarding-portal/clients/${sel.id}`, { primary_color: e.target.value }), "Updated")}
                      />
                    </Field>
                    <Field label="Status" htmlFor="pf-status" required>
                      <Select
                        id="pf-status"
                        defaultValue={sel.status}
                        onChange={(e) => act(() => api.put(`/onboarding-portal/clients/${sel.id}`, { status: e.target.value }), "Updated")}
                      >
                        {["draft", "active", "suspended"].map((s) => <option key={s}>{s}</option>)}
                      </Select>
                    </Field>
                  </div>
                </SectionCard>
              )}

              {tab === "flags" && (
                <SectionCard compact title="Feature Flags">
                  {flags.length === 0 && failedDetail.flags && (
                    <Alert tone="error" title="Failed to load">
                      Feature flags could not be loaded for this client — check the server or retry by reselecting the client.
                    </Alert>
                  )}
                  <Card padded={false}>
<Table
                      columns={[
                        { key: "flag", header: "Flag", accessor: (f) => <span className="font-medium">{f.key}</span> },
                        { key: "desc", header: "Description", accessor: (f) => <span className="text-fg-muted">{f.description}</span> },
                        { key: "enabled", header: "Enabled", accessor: (f) => (
                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={() => act(() => api.put(`/onboarding-portal/clients/${selected}/feature-flags/${f.key}`, { enabled: !f.enabled }), "Flag updated")}
                            aria-pressed={f.enabled}
                            aria-label={f.enabled ? `Disable ${f.key}` : `Enable ${f.key}`}
                          >
                            <span className={`relative inline-flex h-5 w-9 items-center rounded-full transition ${
                              f.enabled ? "bg-brand-600" : "bg-surface-inset"
                            }`}>
                              <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-surface transition ${
                                f.enabled ? "translate-x-5" : "translate-x-1"
                              }`} aria-hidden="true" />
                            </span>
                          </Button>
                        ) },
                      ]}
                      data={flags}
                      keyAccessor={(f) => f.id}
                      caption="Client feature flags"
                      sortable={false}
                    />
                    {flags.length === 0 && (
                      <EmptyState
                        className="p-8"
                        icon={<IconFile />}
                        title="No feature flags"
                        description="This client has no feature flags configured yet."
                      />
                    )}
                  </Card>
                </SectionCard>
              )}

              {tab === "integrations" && (
                <SectionCard compact title="Integrations" description="Configure data source connections for this client.">
                  {integrations.length === 0 && failedDetail.integrations && (
                    <Alert tone="error" title="Failed to load">
                      Integrations could not be loaded for this client — check the server or retry by reselecting the client.
                    </Alert>
                  )}

                  <Card className="mb-4">
                    <form
                      onSubmit={(e) => {
                        e.preventDefault()
                        act(() => api.post(`/onboarding-portal/clients/${selected}/integrations`, intForm), "Integration created")
                      }}
                      className="flex flex-wrap items-end gap-3"
                    >
                      <Field label="Name" htmlFor="int-name" required className="flex-1 min-w-[180px]">
                        <Input
                          id="int-name"
                          placeholder="Name"
                          aria-label="Integration name"
                          value={intForm.name}
                          onChange={(e) => setIntForm({ ...intForm, name: e.target.value })}
                        />
                      </Field>
                      <Field label="Kind" htmlFor="int-kind" required className="flex-1 min-w-[150px]">
                        <Select
                          id="int-kind"
                          value={intForm.kind}
                          onChange={(e) => setIntForm({ ...intForm, kind: e.target.value })}
                        >
                          {["oracle_adb", "rest", "sftp", "csv", "webhook"].map((k) => <option key={k}>{k}</option>)}
                        </Select>
                      </Field>
                      <Field label="Endpoint" htmlFor="int-endpoint" className="flex-1 min-w-[180px]">
                        <Input
                          id="int-endpoint"
                          placeholder="Endpoint"
                          aria-label="Endpoint"
                          value={intForm.endpoint}
                          onChange={(e) => setIntForm({ ...intForm, endpoint: e.target.value })}
                        />
                      </Field>
                      <Field label="Username" htmlFor="int-username" className="flex-1 min-w-[150px]">
                        <Input
                          id="int-username"
                          placeholder="Username"
                          aria-label="Username"
                          value={intForm.username}
                          onChange={(e) => setIntForm({ ...intForm, username: e.target.value })}
                        />
                      </Field>
                      <Field label="Secret" htmlFor="int-secret" className="flex-1 min-w-[150px]">
                        <Input
                          id="int-secret"
                          type="password"
                          placeholder="Secret"
                          aria-label="Secret"
                          value={intForm.secret}
                          onChange={(e) => setIntForm({ ...intForm, secret: e.target.value })}
                        />
                      </Field>
                      <Field label="Notes" htmlFor="int-notes" className="flex-1 min-w-[180px]">
                        <Input
                          id="int-notes"
                          placeholder="Notes"
                          aria-label="Notes"
                          value={intForm.notes}
                          onChange={(e) => setIntForm({ ...intForm, notes: e.target.value })}
                        />
                      </Field>
                      <Button type="submit" disabled={!intForm.name} className="h-10">
                        Add
                      </Button>
                    </form>
                  </Card>

                  <Card padded={false}>
                    <Table
                      columns={[
                        { key: "name", header: "Name", accessor: (i) => i.name },
                        { key: "kind", header: "Kind", accessor: (i) => i.kind },
                        { key: "status", header: "Status", accessor: (i) => <StatusPill status={i.status} dot /> },
                        { key: "secret", header: "Has secret", accessor: (i) => i.has_secret ? "Yes" : "No" },
                        { key: "actions", header: "Actions", accessor: (i) => (
                          <span className="space-x-2">
                            <Button variant="ghost" size="xs" onClick={() => act(() => api.post(`/onboarding-portal/clients/${selected}/integrations/${i.id}/test`), "Tested")}>
                              Test
                            </Button>
                            <Button variant="ghost" size="xs" onClick={() => act(() => api.delete(`/onboarding-portal/clients/${selected}/integrations/${i.id}`), "Deleted")}>
                              <IconX className="h-3.5 w-3.5" aria-hidden="true" />
                            </Button>
                          </span>
                        ) },
                      ]}
                      data={integrations}
                      keyAccessor={(i) => i.id}
                      caption="Client integrations"
                      sortable={false}
                    />
                  </Card>
                </SectionCard>
              )}

              {tab === "migrations" && (
                <SectionCard compact title="Data Migration" description="Run and monitor data migration jobs.">
                  {migrations.length === 0 && failedDetail.migrations && (
                    <Alert tone="error" title="Failed to load">
                      Past migrations could not be loaded for this client — check the server or retry by reselecting the client.
                    </Alert>
                  )}

                  <Card className="mb-4">
                    <form
                      onSubmit={(e) => {
                        e.preventDefault()
                        act(async () => {
                          const r = await api.post(`/onboarding-portal/clients/${selected}/migrations`, {
                            integration_id: migForm.integration_id ? Number(migForm.integration_id) : null,
                            entity: migForm.entity,
                            total: migForm.total,
                          })
                          await api.post(`/onboarding-portal/clients/${selected}/migrations/${r.data.id}/run`)
                        }, "Migration completed")
                      }}
                      className="flex flex-wrap items-end gap-3"
                    >
                      <Field label="Integration" htmlFor="mig-integration" className="flex-1 min-w-[180px]">
                        <Select
                          id="mig-integration"
                          value={migForm.integration_id}
                          onChange={(e) => setMigForm({ ...migForm, integration_id: e.target.value })}
                        >
                          <option value="">None (CSV)</option>
                          {integrations.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
                        </Select>
                      </Field>
                      <Field label="Entity" htmlFor="mig-entity" required className="flex-1 min-w-[150px]">
                        <Select
                          id="mig-entity"
                          value={migForm.entity}
                          onChange={(e) => setMigForm({ ...migForm, entity: e.target.value })}
                        >
                          {["employees", "departments", "jobs", "candidates", "leave_balances"].map((e) => <option key={e}>{e}</option>)}
                        </Select>
                      </Field>
                      <Field label="Total rows" htmlFor="mig-total" required className="w-[120px]">
                        <Input
                          id="mig-total"
                          type="number"
                          min="1"
                          value={migForm.total}
                          onChange={(e) => setMigForm({ ...migForm, total: Number(e.target.value) })}
                        />
                      </Field>
                      <Button type="submit" className="h-10">
                        Run migration
                      </Button>
                    </form>
                  </Card>

                  <Card padded={false}>
                    {migrations.length === 0 ? (
                          <EmptyState
                            className="p-4"
                            icon={<IconRefresh />}
                            title="No migrations yet"
                            description="Run a migration to see results here."
                          />
                        ) : (
                          <Table
                            columns={[
                              { key: "entity", header: "Entity", accessor: (m) => m.entity },
                              { key: "status", header: "Status", accessor: (m) => <StatusPill status={m.status} dot /> },
                              { key: "progress", header: "Progress", accessor: (m) => `${m.processed}/${m.total}` },
                              { key: "result", header: "Succeeded/Failed", accessor: (m) => `${m.succeeded}/${m.failed}` },
                            ]}
                            data={migrations}
                            keyAccessor={(m) => m.id}
                            caption="Client data migrations"
                            sortable={false}
                          />
                        )}
                  </Card>
                </SectionCard>
              )}

              {tab === "settings" && (
                <SectionCard compact title="Custom Settings (key/value)" description="Store arbitrary configuration for this client.">
                  {settings.length === 0 && failedDetail.settings && (
                    <Alert tone="error" title="Failed to load">
                      Saved settings could not be loaded for this client — check the server or retry by reselecting the client.
                    </Alert>
                  )}

                  <Card className="mb-4">
                    <form
                      onSubmit={(e) => {
                        e.preventDefault()
                        act(() => api.put(`/onboarding-portal/clients/${selected}/settings/${settingForm.key}`, { key: settingForm.key, value: settingForm.value }), "Setting saved")
                      }}
                      className="flex flex-wrap items-end gap-3"
                    >
                      <Field label="Key" htmlFor="set-key" required className="flex-1 min-w-[200px]">
                        <Input
                          id="set-key"
                          placeholder="key (e.g. payroll.cycle_day)"
                          aria-label="Setting key"
                          value={settingForm.key}
                          onChange={(e) => setSettingForm({ ...settingForm, key: e.target.value })}
                        />
                      </Field>
                      <Field label="Value" htmlFor="set-value" required className="flex-1 min-w-[200px]">
                        <Input
                          id="set-value"
                          placeholder="value"
                          aria-label="Setting value"
                          value={settingForm.value}
                          onChange={(e) => setSettingForm({ ...settingForm, value: e.target.value })}
                        />
                      </Field>
                      <Button type="submit" disabled={!settingForm.key} className="h-10">
                        Save
                      </Button>
                    </form>
                  </Card>

                  <Card padded={false}>
                    {settings.length === 0 ? (
                        <EmptyState
                          className="p-4"
                          icon={<IconFile />}
                          title="No custom settings"
                          description="Add a key/value pair to store custom configuration."
                        />
                      ) : (
                        <Table
                          columns={[
                            { key: "key", header: "Key", accessor: (x) => <span className="font-medium">{x.key}</span> },
                            { key: "value", header: "Value", accessor: (x) => x.value },
                          ]}
                          data={settings}
                          keyAccessor={(x) => x.id}
                          caption="Client custom settings"
                          sortable={false}
                        />
                      )}
                  </Card>
                </SectionCard>
              )}

              {tab === "onboarding" && (
                <SectionCard compact title={`Onboarding Progress — ${progress.percent}%`} description="Track onboarding step completion.">
                  {steps.length === 0 && failedDetail.onboarding && (
                    <Alert tone="error" title="Failed to load">
                      Onboarding steps could not be loaded for this client — check the server or retry by reselecting the client.
                    </Alert>
                  )}

                  <Meter
                    percent={progress.percent}
                    label={`Onboarding ${progress.completed} of ${progress.total} steps complete`}
                    className="mb-4"
                  />

                  <Card padded={false}>
                    <Table
                      columns={[
                        { key: "order", header: "#", accessor: (st) => st.order_index },
                        { key: "step", header: "Step", accessor: (st) => (
                          <span>
                            <div className="font-medium">{st.title}</div>
                            <div className="text-xs text-fg-muted">{st.description}</div>
                          </span>
                        ) },
                        { key: "owner", header: "Owner", accessor: (st) => st.owner },
                        { key: "status", header: "Status", accessor: (st) => (
                          <StatusPill status={st.completed ? "Completed" : "Pending"} dot />
                        ) },
                        { key: "action", header: "Action", accessor: (st) => (
                          !st.completed ? (
                            <Button variant="ghost" size="xs" onClick={() => act(() => api.post(`/onboarding-portal/clients/${selected}/onboarding/steps/${st.id}/complete`), "Step completed")}>
                              Mark complete
                            </Button>
                          ) : <></>
                        ) },
                      ]}
                      data={steps}
                      keyAccessor={(st) => st.id}
                      caption="Client onboarding steps"
                      sortable={false}
                    />
                  </Card>
                </SectionCard>
              )}

              {tab === "docs" && (
                <SectionCard compact title="Migration API Connection Documentation" description="Reference documentation for the migration API.">
                  {!docs && failedDetail.docs && (
                    <Alert tone="error" title="Failed to load">
                      The migration API documentation could not be loaded — check the server or retry by reselecting the client.
                    </Alert>
                  )}
                  <Card className="p-0">
                    <pre className="text-xs bg-page p-4 rounded overflow-auto max-h-[600px] whitespace-pre-wrap font-mono">
                      {docs || "Documentation will appear here once loaded."}
                    </pre>
                  </Card>
                </SectionCard>
              )}
            </>
          )}
        </div>
      </div>
    </Layout>
  )
}