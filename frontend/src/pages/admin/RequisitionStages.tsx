/* RC-01 — Requisition stages + talent pools (depends HR-04 + HR-09)
 * E-UX-02: the former "Advance stage" POSTed /onboarding/steps/advance, which
 * does not exist. Stage + department now persist as tenant configuration via
 * GET/PUT /clients/:id/feature-flags (requisition_status / requisition_department,
 * require_roles("SuperAdmin")).
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const STATUSES = ["draft", "posted", "under_review", "interviewing", "offer", "filled", "closed"]
const DEPARTMENTS = ["Engineering", "Sales", "Finance", "HR"]

export default function RequisitionStages() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [status, setStatus] = useState("draft")
  const [department, setDepartment] = useState("Engineering")
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
      const getCfg = (k: string) => (data as any[])?.find((x: any) => x.key === k)?.config
      setStatus(getCfg("requisition_status") ?? "draft")
      setDepartment(getCfg("requisition_department") ?? "Engineering")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/requisition_status`, { config: status })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/requisition_department`, { config: department })
      await load()
      setNotice("Requisition stage config saved.")
    } catch (e) { setActionError(errorMessage(e, "The requisition stage config could not be saved.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Requisition stage config requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Requisition Stages"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Requisition Stages + Talent Pools" description="RC-01 · default requisition stage + department configuration · persists via /clients/:id/feature-flags (SuperAdmin)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The requisition stage config could not be read." fallback="The requisition stage config could not be read." onRetry={load} />}
        <SectionCard compact title="Requisition configuration" description="Default stage + department stored per tenant.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="rs-status">Status</label>
              <select id="rs-status" value={status} onChange={e => setStatus(e.target.value)} className="w-full rounded border px-3 py-2" disabled={!canWrite || saving || !clientId}>
                {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="rs-dept">Department</label>
              <select id="rs-dept" value={department} onChange={e => setDepartment(e.target.value)} className="w-full rounded border px-3 py-2" disabled={!canWrite || saving || !clientId}>
                {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div />
          </div>
          <div className="mt-4">
            <Button onClick={save} disabled={!canWrite || saving || !clientId}>{saving ? "Saving…" : "Save stage config"}</Button>
          </div>
        </SectionCard>

        <SectionCard compact title="Requisition stages" description="The 7-stage lifecycle reference.">
          <div className="table-scroll">
            <table className="w-full text-sm">
              <caption className="sr-only">Requisition stage reference</caption>
              <thead><tr className="border-b"><th scope="col" className="text-left">Stage</th><th scope="col" className="text-center">Index</th></tr></thead>
              <tbody>
                {STATUSES.map((s, i) => (
                  <tr key={s} className="border-b">
                    <td>{s}</td>
                    <td className="text-center">{i + 1}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <SectionCard compact title="Current configuration" description="The persisted tenant configuration.">
          <div className="text-sm text-fg-muted">Status: {status} | Department: {department}</div>
        </SectionCard>

        <div className="text-xs text-fg-muted">RC-01 · R4 · depends HR-04 + HR-09 · configuration only.</div>
      </div>
    </Layout>
  )
}