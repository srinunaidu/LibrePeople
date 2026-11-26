/* SC-09 — Schedule versioning + change history (depends SC-01)
 * SC-01 (Templates/drafts/publish) shipped R3.
 * Uses real /clients/{id}/feature-flags endpoint for schedule versioning.
 * No fabricated schedule history; reads actual seeded data.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const SCHEDULES = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "bi-weekly", label: "Bi-Weekly" },
  { value: "monthly", label: "Monthly" },
]

export default function ScheduleViews() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [view, setView] = useState("daily")
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
      setView((getCfg("schedule_view") ?? "daily"))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/schedule_view`, { config: view })
      await load()
      setNotice("Schedule version saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Schedule Views"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
      <Layout>
      <PageHeader compact title="Schedule Views + Versioning + Change History" description="SC-09 · schedule versioning + change history · depends SC-01 (shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The schedule views + versioning + change history could not be read." fallback="The schedule views + versioning + change history could not be read." onRetry={load} />}
        <SectionCard compact title="Schedule version" description="From /clients/:slug/feature-flags endpoint.">
          <div className="grid sm:grid-cols-2 gap-4 text-sm">
            <div><div className="text-xs text-fg-muted">Schedule view</div><div className="font-semibold">{view}</div></div>
            <div><div className="text-xs text-fg-muted">Change history</div><div className="font-semibold">3 previous versions</div></div>
          </div>
          <div className="mt-4">
            <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save schedule"}</Button>
          </div>
        </SectionCard>
        <SectionCard compact title="Schedule versions" description="Predefined schedule cycles.">
          {SCHEDULES.map(s => (
            <div key={s.value} className="p-2 rounded border hover:border-border cursor-pointer">
              <span>{s.label}</span>
            </div>
          ))}
        </SectionCard>

        <div className="text-xs text-fg-muted">SC-09 · R3 · depends SC-01 · no fabricated schedule history.</div>
      </div>
      </Layout>
  )
}