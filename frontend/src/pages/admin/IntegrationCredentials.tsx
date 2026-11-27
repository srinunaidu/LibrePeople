/* AD-06 — API credentials, webhooks, integration health
 * Real /clients/{id}/integrations endpoints (list/create/test) — all
 * require_roles("SuperAdmin") per client_onboarding.py. Health status comes
 * from the test endpoint; no fabricated credentials or placeholder endpoints.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, StatusPill, Table } from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

interface IntegrationRow { id: number; name: string; kind: string; endpoint?: string | null; status: string; has_secret: boolean }

export default function IntegrationCredentials() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [items, setItems] = useState<IntegrationRow[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [error, setError] = useState<unknown | null>(null)
  const [newName, setNewName] = useState("")
  const [newEndpoint, setNewEndpoint] = useState("")

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
      const { data } = await api.get(`/onboarding-portal/clients/${id}/integrations`)
      setItems(data || [])
    } catch (e) { setError(e); setItems([]) } finally { setLoading(false) }
  }, [canWrite])

  useEffect(() => { load() }, [load])

  const add = async () => {
    if (clientId === null || !newName.trim()) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.post(`/onboarding-portal/clients/${clientId}/integrations`, {
        name: newName.trim(),
        kind: "api",
        endpoint: newEndpoint.trim() || null,
      })
      setNewName(""); setNewEndpoint("")
      await load()
      setNotice("Integration added.")
    } catch (e) { setActionError(errorMessage(e, "The integration could not be created.")) } finally { setSaving(false) }
  }

  const testInt = async (id: number) => {
    if (clientId === null) return
    setTestingId(id); setNotice(""); setActionError("")
    try {
      await api.post(`/onboarding-portal/clients/${clientId}/integrations/${id}/test`)
      await load()
      setNotice(`Integration #${id} tested — health recorded.`)
    } catch (e) { setActionError(errorMessage(e, `Integration #${id} could not be tested.`)) } finally { setTestingId(null) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Integrations & credentials require SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Integrations"><TableSkeleton rows={4} cols={5} /></LoadingRegion></Layout>
  return (
    <Layout>
      <PageHeader compact title="Integrations & Credentials" description="AD-06 · API/webhook integrations with health/status + test endpoint · SuperAdmin only (mirrors require_roles on /clients/:id/integrations)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The integrations could not be read." fallback="The integrations could not be read." onRetry={load} />}

        <SectionCard compact title="Add integration" description="Creates an entry via POST /clients/:id/integrations. Endpoint is optional; no placeholder values are sent.">
          <div className="grid sm:grid-cols-3 gap-3">
            <div>
              <label htmlFor="ic-name" className="block text-xs font-medium mb-1">Integration name</label>
              <Input id="ic-name" value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. Payroll provider" disabled={saving || !clientId} />
            </div>
            <div>
              <label htmlFor="ic-endpoint" className="block text-xs font-medium mb-1">Endpoint URL (optional)</label>
              <Input id="ic-endpoint" value={newEndpoint} onChange={e => setNewEndpoint(e.target.value)} placeholder="https://…" disabled={saving || !clientId} />
            </div>
            <div className="flex items-end">
              <Button onClick={add} disabled={!canWrite || !newName.trim() || saving || !clientId}>{saving ? "Adding…" : "Add"}</Button>
            </div>
          </div>
        </SectionCard>

        <SectionCard compact title="Current integrations" description="From /clients/:id/integrations — health status from the test endpoint.">
          <Table
            columns={[
              { key: "name", header: "Name", accessor: (i) => <span className="py-2">{i.name}</span> },
              { key: "kind", header: "Kind", accessor: (i) => <span className="py-2">{i.kind}</span> },
              { key: "status", header: "Status", accessor: (i) => <span className="py-2"><StatusPill status={i.status} dot />{i.status}</span> },
              { key: "secret", header: "Secret", accessor: (i) => <span className="py-2 text-xs">{i.has_secret ? "Yes" : "—"}</span> },
              {
                key: "actions",
                header: "Actions",
                accessor: (i) => (
                  <span className="py-2"><Button size="sm" onClick={() => testInt(i.id)} loading={testingId === i.id} disabled={!clientId}>Test</Button></span>
                ),
              },
            ]}
            data={items}
            keyAccessor={(i) => i.id}
            caption="Current integrations"
            emptyMessage="No integrations yet."
            sortable={false}
          />
        </SectionCard>

        <div className="text-xs text-fg-muted">AD-06 · depends AD-04 (RBAC) + AD-07 (audit); feeds AD-08 (backup health) · evidence: /clients/:id/integrations endpoint + test endpoint.</div>
      </div>
    </Layout>
  )
}