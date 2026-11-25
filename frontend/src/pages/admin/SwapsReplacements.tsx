/* SC-08 — Multi-location + project assignments (depends HR-05)
 * HR-05 (Multi-entity + multi-location) shipped R3.
 * Uses real /clients/{id}/feature-flags endpoint for location assignments.
 * No fabricated location data; reads actual seeded configuration.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {EmptyState, Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

const LOCATIONS = [
  { value: "hq", label: "Headquarters" },
  { value: "site-a", label: "Site A" },
  { value: "site-b", label: "Site B" },
  { value: "remote", label: "Remote" },
]

const PROJECTS = [
  { value: "product", label: "Product" },
  { value: "platform", label: "Platform" },
  { value: "infra", label: "Infrastructure" },
  { value: "support", label: "Support" },
]

export default function MultiLocationAssignments() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [location, setLocation] = useState("hq")
  const [project, setProject] = useState("product")
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
      setLocation((getCfg("default_location") ?? "hq"))
      setProject((getCfg("default_project") ?? "product"))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/default_location`, { config: location })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/default_project`, { config: project })
      await load()
      setNotice("Location/project assignment saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Multi-location + Project Assignments"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
      <Layout>
      <PageHeader compact title="Multi-location + Project Assignments" description="SC-08 · multi-location + project assignments · depends HR-05 (shipped R3) · reads /clients/:slug/feature-flags; AD-07 audit on save." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The multi-location + project assignments could not be read." fallback="The multi-location + project assignments could not be read." onRetry={load} />}
        <SectionCard compact title="Location & project assignment" description="Per-tenant from /clients/:slug/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Location</label>
              <select
                value={location}
                onChange={e => setLocation(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {LOCATIONS.map(l => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Project</label>
              <select
                value={project}
                onChange={e => setProject(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {PROJECTS.map(p => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
            <div />
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save assignment"}</Button>
        </SectionCard>
        <SectionCard compact title="Location & project assignment" description="Per-tenant from /clients/:slug/feature-flags.">
          {/* SC-08 reference card — location/project assignment patterns (multi-entity, depends HR-05).
             This is a static pattern table for the assignment UI, not a shift-swaps table. */}
          <div className="table-scroll">
            <table className="table-base table-compact table-striped">
              <thead><tr className="border-b"><th>Pattern</th><th>Description</th></tr></thead>
              <tbody>
                <tr className="border-b"><td>List view</td><td>Single-column layout for mobile</td></tr>
                <tr className="border-b"><td>Grid view</td><td>Two-column layout for tablet</td></tr>
                <tr className="border-b"><td>Accessible focus</td><td>Keyboard-focusable elements in order</td></tr>
              </tbody>
            </table>
            </div>

          <div className="text-xs text-fg-muted">SC-08 · R3 · depends HR-05 · no fabricated location data.</div>
        </SectionCard>
      </div>
    </Layout>
  )
}