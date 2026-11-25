/* OB-06 — Exit + retention + erasure (depends HR-02 + HR-07 + AD-07)
 * Real GET /admin/jobs (require_roles(*ADMIN_ROLES)) filtered to retention jobs.
 * E-UX-02: the former browser-alert-only "Trigger erasure job" button was removed —
 * no erasure-trigger endpoint exists in the backend (see programme doc).
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api from "@/lib/api"

export default function ExitErasure() {
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

  if (loading) return (
    <Layout>
      <div data-tenant-slug={tenant?.slug ?? "—"}>
        <LoadingRegion label="Export / Erasure"><TableSkeleton rows={4} cols={4} /></LoadingRegion>
      </div>
    </Layout>
  )

  return (
    <Layout>
      <PageHeader compact title="Exit / Retention / Erasure" description="OB-06 · retention job ledger from /admin/jobs (SuperAdmin / HR) · audit chain (AD-07) on every job change." />
      <div data-tenant-slug={tenant?.slug ?? "—"} className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {!!error && <RetryableAlert err={error} title="The retention jobs could not be read." fallback="The retention jobs could not be read." onRetry={load} />}
        <SectionCard
          compact
          title="Retention jobs"
          description="From /admin/jobs filtered to retention jobs; IM-10 schedule verified."
          actions={<Button variant="secondary" size="sm" onClick={() => load()} disabled={loading}>{loading ? "Refreshing…" : "Refresh"}</Button>}
        >
          <div className="table-scroll">
            <table className="w-full text-sm">
              <caption className="sr-only">Retention jobs</caption>
              <thead><tr className="border-b"><th scope="col" className="text-left">ID</th><th scope="col" className="text-left">Type</th><th scope="col" className="text-left">State</th></tr></thead>
              <tbody>
                {jobs.length === 0 && <tr><td colSpan={3} className="py-3 text-fg-subtle italic">No retention jobs visible.</td></tr>}
                {jobs.map(j => (
                  <tr key={j.id} className="border-b">
                    <td className="font-mono text-xs">{j.id}</td>
                    <td>{j.type}</td>
                    <td>{j.state}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
        <div className="text-xs text-fg-muted">OB-06 · R4 · depends HR-02 + HR-07 + AD-07 · feeds HR-12 (export/erasure). Erasure triggering is not exposed by the backend yet.</div>
      </div>
    </Layout>
  )
}