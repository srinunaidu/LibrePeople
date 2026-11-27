/* UX-06 — Announcements/directory/help centre (depends UX-02)
 * E-UX-02: announcements now persist per tenant in the real feature-flags
 * store (key "announcements", config = JSON array) via
 * GET/PUT /onboarding-portal/clients/:id/feature-flags (SuperAdmin only).
 * The former hardcoded seed array and placeholder "New announcement" POST
 * were removed — nothing is shown that the backend does not actually store.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, Table } from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

interface Announcement { id: number; title: string; content: string; date: string }

export default function AnnouncementsDirectory() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [announcements, setAnnouncements] = useState<Announcement[]>([])
  const [title, setTitle] = useState("")
  const [content, setContent] = useState("")
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
      setError("Could not resolve the company. Check the server connection and retry.");
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get(`/onboarding-portal/clients/${id}/feature-flags`)
      const cfg = (data as any[])?.find((x: any) => x.key === "announcements")?.config
      let parsed: Announcement[] = []
      if (cfg) {
        try { parsed = JSON.parse(cfg) } catch { parsed = [] }
      }
      setAnnouncements(Array.isArray(parsed) ? parsed : [])
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const add = async () => {
    if (clientId === null) return
    if (!title.trim()) { setActionError("Announcement title is required."); return }
    setSaving(true); setNotice(""); setActionError("")
    try {
      const next: Announcement[] = [
        ...announcements,
        { id: Date.now(), title: title.trim(), content: content.trim(), date: new Date().toISOString().split("T")[0] },
      ]
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/announcements`, { config: JSON.stringify(next) })
      setTitle(""); setContent("")
      await load()
      setNotice("Announcement added.")
    } catch (e) { setActionError(errorMessage(e, "The announcement could not be saved.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Announcements require SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Announcements"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Announcements + Directory + Help Centre" description="UX-06 · announcements persist per tenant in /clients/:id/feature-flags (key: announcements)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The announcements could not be read." fallback="The announcements could not be read." onRetry={load} />}
        <SectionCard compact title="New announcement" description="Stored as JSON in the tenant's announcements feature flag.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="ann-title" className="block text-xs font-medium mb-1">Title</label>
              <Input id="ann-title" value={title} onChange={e => setTitle(e.target.value)} disabled={saving || !clientId} placeholder="e.g. Policy update" />
            </div>
            <div>
              <label htmlFor="ann-content" className="block text-xs font-medium mb-1">Content (optional)</label>
              <Input id="ann-content" value={content} onChange={e => setContent(e.target.value)} disabled={saving || !clientId} placeholder="Short announcement body" />
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <Button onClick={add} disabled={!canWrite || !title.trim() || saving || !clientId}>{saving ? "Adding…" : "Add announcement"}</Button>
          </div>
        </SectionCard>
        <SectionCard compact title="Announcements" description="From /clients/:id/feature-flags — persisted across refresh and re-login.">
          {announcements.length === 0 ? (
            <EmptyState title="No announcements" description="No announcements have been published for this tenant yet. Add one above." />
          ) : (
            <Table
              columns={[
                { key: "date", header: "Date", accessor: (a) => <span className="whitespace-nowrap">{a.date}</span> },
                { key: "title", header: "Title", accessor: (a) => a.title },
                { key: "content", header: "Content", accessor: (a) => <span className="text-xs text-fg-muted">{a.content || "—"}</span> },
              ]}
              data={announcements}
              keyAccessor={(a) => a.id}
              caption="Tenant announcements"
              sortable={false}
            />
          )}
        </SectionCard>
        <div className="text-xs text-fg-muted">UX-06 · R3 · depends UX-02 · only backend-persisted announcements are shown.</div>
      </div>
    </Layout>
  )
}