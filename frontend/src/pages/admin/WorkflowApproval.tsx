/* AD-05 — Workflow/approval configuration
 * Real endpoints (backend/app/api/v1/endpoints/client_onboarding.py):
 *   GET  /clients/{id}/onboarding            → { steps: OnboardingStepOut[] } (SuperAdmin)
 *   POST /clients/{id}/onboarding/steps      → create { key, title, description?, order_index, owner? } (SuperAdmin)
 *   POST /clients/{id}/onboarding/steps/{id}/complete (SuperAdmin)
 * Audit chain (AD-07) writes on create/complete; RBAC (AD-04) gates writes.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, Table } from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

interface StepRow { id: number; key: string; title: string; description?: string | null; order_index: number; completed: boolean; owner?: string | null }

export default function WorkflowApproval() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [steps, setSteps] = useState<StepRow[]>([])
  const [title, setTitle] = useState("")
  const [owner, setOwner] = useState("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [completingId, setCompletingId] = useState<number | null>(null)
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
      const { data } = await api.get(`/onboarding-portal/clients/${id}/onboarding`)
      setSteps(((data as any)?.steps ?? []) as StepRow[])
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const createStep = async () => {
    if (clientId === null || !title.trim()) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      const key = title.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || `step_${Date.now()}`
      await api.post(`/onboarding-portal/clients/${clientId}/onboarding/steps`, {
        key, title: title.trim(), owner: owner.trim() || null, order_index: steps.length,
      })
      setTitle(""); setOwner("")
      await load()
      setNotice("Workflow step created.")
    } catch (e) { setActionError(errorMessage(e, "The workflow step could not be created.")) } finally { setSaving(false) }
  }

  const completeStep = async (id: number) => {
    if (clientId === null) return
    setCompletingId(id); setNotice(""); setActionError("")
    try {
      await api.post(`/onboarding-portal/clients/${clientId}/onboarding/steps/${id}/complete`)
      await load()
      setNotice(`Step #${id} marked complete.`)
    } catch (e) { setActionError(errorMessage(e, `Step #${id} could not be completed.`)) } finally { setCompletingId(null) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Workflow configuration requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Workflow & Approval"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>
  return (
    <Layout>
      <PageHeader compact title="Workflow / Approval" description="AD-05 · step-based workflow · audit chain (AD-07) records every create/complete · SuperAdmin only (mirrors require_roles on /clients/:id/onboarding*)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The workflow steps could not be read." fallback="The workflow steps could not be read." onRetry={load} />}

        <SectionCard compact title="New workflow step" description="POST /clients/:id/onboarding/steps — SuperAdmin only. Each create writes an audit row via AD-07.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="wname" className="block text-xs font-medium mb-1">Step title</label>
              <Input id="wname" value={title} onChange={e => setTitle(e.target.value)} disabled={saving || !clientId} placeholder="e.g. Manager sign-off" />
            </div>
            <div>
              <label htmlFor="wowner" className="block text-xs font-medium mb-1">Owner (optional)</label>
              <Input id="wowner" value={owner} onChange={e => setOwner(e.target.value)} disabled={saving || !clientId} placeholder="e.g. HR" />
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <Button onClick={createStep} disabled={!canWrite || !title.trim() || saving || !clientId}>{saving ? "Creating…" : "Create step"}</Button>
          </div>
        </SectionCard>

        <SectionCard compact title="Configured steps" description="Steps from GET /clients/:id/onboarding — complete marks a step done (audited).">
          <Table
            columns={[
              { key: "title", header: "Title", accessor: (s) => <span className="py-2">{s.title}</span> },
              { key: "key", header: "Key", accessor: (s) => <span className="py-2 font-mono text-xs">{s.key}</span> },
              { key: "owner", header: "Owner", accessor: (s) => <span className="py-2">{s.owner || "—"}</span> },
              { key: "status", header: "Status", accessor: (s) => <span className="py-2">{s.completed ? "Complete" : "Pending"}</span> },
              {
                key: "action",
                header: "Action",
                accessor: (s) => (
                  <span className="py-2">
                    {!s.completed ? (
                      <Button size="sm" variant="secondary" onClick={() => completeStep(s.id)} loading={completingId === s.id} disabled={!clientId}>Complete</Button>
                    ) : <span className="text-xs text-fg-muted">—</span>}
                  </span>
                ),
              },
            ]}
            data={steps}
            keyAccessor={(s) => s.id}
            caption="Configured workflow steps"
            emptyMessage="No steps configured yet — create one above."
            sortable={false}
          />
        </SectionCard>

        <div className="text-xs text-fg-muted">AD-05 · depends AD-04 + AD-07 · feeds AD-06 (credentials), RC-01 · evidence: /clients/:id/onboarding endpoints + this screen.</div>
      </div>
    </Layout>
  )
}