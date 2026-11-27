/* HR-12 — Export + retention + erasure (depends AD-07 + AD-09)
 * Real endpoints (backend/app/api/v1/endpoints/admin_jobs.py, *ADMIN_ROLES):
 *   GET  /admin/jobs            → retention job ledger
 *   POST /admin/jobs/{id}/retry → requeue a failed job (audited)
 *   POST /admin/jobs/{id}/discard → discard a job (audited)
 * E-UX-02: the former "Trigger erasure job" button POSTed the nonexistent
 * /admin/jobs/erasure-trigger and was replaced by the real retry/discard actions.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, Table } from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { errorMessage } from "@/lib/api"

interface JobRow { id: string; type: string; state: string }

export default function ExportErasure() {
  const { user } = useAuth()
  const canWrite = ["SuperAdmin", "HR"].includes(user?.role ?? "")
  const [jobs, setJobs] = useState<JobRow[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [discardConfirm, setDiscardConfirm] = useState<string | null>(null)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [error, setError] = useState<unknown | null>(null)

  const load = useCallback(async () => {
    if (!canWrite) { setLoading(false); return }
    setLoading(true); setError(null); setNotice("")
    try {
      const { data } = await api.get("/admin/jobs")
      setJobs((data?.items || []).filter((j: any) => j.job_type?.includes("retention") || j.type?.includes("retention")))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const act = async (id: string, action: "retry" | "discard") => {
    setBusyId(id); setNotice(""); setActionError("")
    try {
      await api.post(`/admin/jobs/${id}/${action}`)
      setDiscardConfirm(null)
      await load()
      setNotice(action === "retry" ? `Job ${id} requeued.` : `Job ${id} discarded.`)
    } catch (e) {
      setActionError(errorMessage(e, `Job ${id} could not be ${action === "retry" ? "retried" : "discarded"}.`))
    } finally { setBusyId(null) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Retention jobs require SuperAdmin or HR; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Export / Erasure"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Export + Retention + Erasure" description="HR-12 · retention job ledger from /admin/jobs (SuperAdmin / HR) · retry/discard are audited (AD-07)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The retention jobs could not be read." fallback="The retention jobs could not be read." onRetry={load} />}
        <SectionCard
          compact
          title="Retention jobs"
          description="From /admin/jobs filtered to retention jobs. Retry requeues a failed job; discard removes it from the queue."
          actions={<Button variant="secondary" size="sm" onClick={() => load()} disabled={loading}>{loading ? "Refreshing…" : "Refresh"}</Button>}
        >
          <Table
            columns={[
              { key: "id", header: "ID", accessor: (j) => <span className="font-mono text-xs">{j.id}</span> },
              { key: "type", header: "Type", accessor: (j) => j.type },
              { key: "state", header: "State", accessor: (j) => j.state },
              {
                key: "actions",
                header: "Actions",
                accessor: (j) => (
                  <span className="inline-flex items-center gap-1">
                    <Button size="sm" variant="secondary" onClick={() => act(j.id, "retry")} loading={busyId === j.id} disabled={!canWrite}>Retry</Button>
                    {discardConfirm === j.id ? (
                      <>
                        <Button size="sm" variant="danger" onClick={() => act(j.id, "discard")} loading={busyId === j.id}>Confirm</Button>
                        <Button size="sm" variant="ghost" onClick={() => setDiscardConfirm(null)}>Cancel</Button>
                      </>
                    ) : (
                      <Button size="sm" variant="ghost" onClick={() => setDiscardConfirm(j.id)} disabled={!canWrite}>Discard</Button>
                    )}
                  </span>
                ),
              },
            ]}
            data={jobs}
            keyAccessor={(j) => j.id}
            caption="Retention jobs"
            emptyMessage="No retention jobs visible."
            sortable={false}
          />
        </SectionCard>
        <div className="text-xs text-fg-muted">HR-12 · R3 · depends AD-07 + AD-09 · feeds HR-09 (manager assignments). Erasure triggering is not exposed by the backend yet.</div>
      </div>
    </Layout>
  )
}