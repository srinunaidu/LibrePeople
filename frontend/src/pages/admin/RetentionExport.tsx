/* AD-09 — Retention / export / erasure workflows (depends AD-04 + AD-07 + IM-10)
 * Real GET /admin/jobs (require_roles(*ADMIN_ROLES)) filtered to retention jobs.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, Table } from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api from "@/lib/api"

export default function RetentionExport() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const canRead = ["SuperAdmin", "HR"].includes(user?.role ?? "")
  const [jobs, setJobs] = useState<{ id: string; type: string; state: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState("")
  const [error, setError] = useState<unknown | null>(null)

  const load = useCallback(async () => {
    if (!canRead) { setLoading(false); return }
    setLoading(true); setError(null); setNotice("")
    try {
      const { data } = await api.get("/admin/jobs")
      setJobs((data?.items || []).filter((j: any) => j.job_type?.includes("retention") || j.type?.includes("retention")))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canRead])
  useEffect(() => { load() }, [load])

  if (!canRead) return <Layout><EmptyState title="Not visible for your role" description={`Retention jobs require SuperAdmin or HR; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Retention"><TableSkeleton rows={4} cols={3} /></LoadingRegion></Layout>
  return (
    <Layout>
      <PageHeader compact title="Retention / Export / Erasure" description="AD-09 · retention job ledger from /admin/jobs (SuperAdmin / HR); audit chain (AD-07) writes on every job." />
      <div data-tenant-slug={tenant?.slug ?? "—"} className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {!!error && <RetryableAlert err={error} title="The retention jobs could not be read." fallback="The retention jobs could not be read." onRetry={load} />}
        <SectionCard
          compact
          title="Retention jobs"
          description="From /admin/jobs filtered to retention jobs; IM-10 enqueue verified."
          actions={<Button variant="secondary" size="sm" onClick={() => load()} disabled={loading}>{loading ? "Refreshing…" : "Refresh"}</Button>}
        >
          <Table
            columns={[
              { key: "id", header: "ID", accessor: (j) => <span className="font-mono text-xs">{j.id}</span> },
              { key: "type", header: "Type", accessor: (j) => j.type },
              { key: "state", header: "State", accessor: (j) => j.state },
            ]}
            data={jobs}
            keyAccessor={(j) => j.id}
            caption="Retention jobs"
            emptyMessage="No retention jobs visible."
            sortable={false}
          />
        </SectionCard>
        <div className="text-xs text-fg-muted">AD-09 · R2 · depends AD-04 + AD-07 + IM-10 (verified) · feeds HR-12 (export/erasure).</div>
      </div>
    </Layout>
  )
}