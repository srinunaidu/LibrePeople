/* Documents library (LP-DOC-001/002) — frontend-only read-mostly UI.
 * Uses ONLY the six contract endpoints (all relative to /api/v1 baseURL):
 *   GET  /employee-documents
 *   GET  /employee-documents?employee_id=
 *   POST /employee-documents
 *   GET  /employee-documents/{id}/versions
 *   POST /employee-documents/{id}/versions
 *   POST /employee-documents/{id}/ack
 * Download anchors at the document's own storage_url (served by
 * GET /api/v1/files/{path}) via the fileUrl() helper — no URL is guessed.
 * document_type is the category surrogate (no `category` column exists).
 * No access-log viewer, no reminders, no status PATCH, no storage work.
 */
import { useCallback, useEffect, useMemo, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input, Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, EmptyState, StatusPill } from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { errorMessage, fileUrl } from "@/lib/api"

/* ------------------------------------------------------------------ */
/* Contract surface: pure helpers + api-path constants (vitest target) */
/* ------------------------------------------------------------------ */

export const DOCUMENT_TYPES = ["Contract", "ID", "Tax", "Certificate", "Policy", "Other"] as const
export const DOCUMENT_STATUSES = ["Active", "Archived", "Expired"] as const
export type ExpiryBucket = "Expired" | "Expiring" | "Valid"
export type ExpiryFilter = "all" | ExpiryBucket

/** Days before expiry_date at which a document counts as expiring soon. */
export const EXPIRY_SOON_DAYS = 30

export interface EmployeeDocument {
  id: number
  employee_id: number
  document_type: string
  file_name: string
  storage_url: string
  storage_key?: string | null
  current_version: number
  status: string
  expiry_date?: string | null
  retention_until?: string | null
  uploaded_at?: string | null
}

export interface DocumentVersion {
  version_no: number
  file_name: string
  uploaded_by?: string | null
  uploaded_at?: string | null
}

export const API_PATHS = {
  /** R1 list / R3 create */
  collection: "/employee-documents",
  /** R2 employee filter is a query param on the collection path */
  employeeParam: "employee_id",
  /** R4 history / R5 renewal */
  versions: (id: number) => `/employee-documents/${id}/versions`,
  /** R6 acknowledge */
  ack: (id: number) => `/employee-documents/${id}/ack`,
} as const

/** R8 badge rule (client-side, 30-day threshold). Pure — takes `now` for tests.
 * Compares calendar dates in UTC so the result is timezone-independent. */
export function expiryBadge(doc: Pick<EmployeeDocument, "status" | "expiry_date">, now: Date = new Date()): ExpiryBucket {
  if (doc.status === "Expired") return "Expired"
  if (!doc.expiry_date) return "Valid"
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(doc.expiry_date)
  if (!m) return "Valid"
  const expiryUTC = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  const todayUTC = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
  if (expiryUTC < todayUTC) return "Expired"
  return (expiryUTC - todayUTC) / 86400000 <= EXPIRY_SOON_DAYS ? "Expiring" : "Valid"
}

export interface LibraryFilters {
  q: string
  type: string
  status: string
  bucket: ExpiryFilter
}

/** R10 client-side search/filter over the R1 payload. Pure — no network. */
export function filterDocuments(docs: EmployeeDocument[], f: LibraryFilters, now: Date = new Date()): EmployeeDocument[] {
  const q = f.q.trim().toLowerCase()
  return docs.filter((d) => {
    if (f.type !== "all" && d.document_type !== f.type) return false
    if (f.status !== "all" && d.status !== f.status) return false
    if (f.bucket !== "all" && expiryBadge(d, now) !== f.bucket) return false
    if (q) {
      const hay = `${d.file_name} ${d.document_type} ${d.employee_id}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

const ALLOWED_ROLES = ["SuperAdmin", "HR"]

export default function DocumentsLibrary() {
  const { user } = useAuth()
  const canView = !!user?.role && ALLOWED_ROLES.includes(user.role)
  const canUpload = user?.role === "SuperAdmin"

  const [docs, setDocs] = useState<EmployeeDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown | null>(null)

  // R2 server filter
  const [employeeId, setEmployeeId] = useState("")
  // R10 client filters
  const [q, setQ] = useState("")
  const [typeFilter, setTypeFilter] = useState("all")
  const [statusFilter, setStatusFilter] = useState("all")
  const [bucketFilter, setBucketFilter] = useState<ExpiryFilter>("all")

  // R3 upload form
  const [form, setForm] = useState({ employee_id: "", document_type: "Contract", file_name: "", storage_url: "", expiry_date: "", retention_until: "" })
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")

  // R4/R5 versions panel
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [versions, setVersions] = useState<DocumentVersion[]>([])
  const [versionsLoading, setVersionsLoading] = useState(false)
  const [versionsError, setVersionsError] = useState<unknown | null>(null)
  const [renewFile, setRenewFile] = useState({ file_name: "", storage_url: "" })
  const [renewing, setRenewing] = useState(false)

  // R6 ack
  const [ackState, setAckState] = useState<Record<number, string>>({})
  const [acking, setAcking] = useState<number | null>(null)

  const load = useCallback(async () => {
    if (!canView) { setLoading(false); return }
    setLoading(true); setError(null); setNotice("")
    try {
      const params = employeeId.trim() ? { [API_PATHS.employeeParam]: employeeId.trim() } : undefined
      const { data } = await api.get<EmployeeDocument[]>(API_PATHS.collection, { params })
      setDocs(Array.isArray(data) ? data : [])
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canView, employeeId])

  useEffect(() => { load() }, [load])

  const visible = useMemo(
    () => filterDocuments(docs, { q, type: typeFilter, status: statusFilter, bucket: bucketFilter }),
    [docs, q, typeFilter, statusFilter, bucketFilter],
  )

  const upload = async () => {
    setSaving(true); setNotice(""); setActionError("")
    try {
      const payload = {
        employee_id: Number(form.employee_id),
        document_type: form.document_type,
        file_name: form.file_name,
        storage_url: form.storage_url,
        ...(form.expiry_date ? { expiry_date: form.expiry_date } : {}),
        ...(form.retention_until ? { retention_until: form.retention_until } : {}),
      }
      const { data } = await api.post<EmployeeDocument>(API_PATHS.collection, payload)
      setDocs((prev) => [data, ...prev])
      setNotice(`Document uploaded (201): ${data.file_name}.`)
      setForm({ employee_id: "", document_type: "Contract", file_name: "", storage_url: "", expiry_date: "", retention_until: "" })
    } catch (e) { setActionError(errorMessage(e, "Upload failed.")) } finally { setSaving(false) }
  }

  const loadVersions = useCallback(async (id: number) => {
    setSelectedId(id)
    setVersionsLoading(true); setVersionsError(null)
    try {
      const { data } = await api.get<DocumentVersion[]>(API_PATHS.versions(id))
      setVersions(Array.isArray(data) ? data : [])
    } catch (e) { setVersionsError(e) } finally { setVersionsLoading(false) }
  }, [])

  const renew = async () => {
    if (selectedId === null) return
    setRenewing(true); setNotice(""); setActionError("")
    try {
      const { data } = await api.post<DocumentVersion>(API_PATHS.versions(selectedId), {
        file_name: renewFile.file_name,
        storage_url: renewFile.storage_url,
      })
      setVersions((prev) => [...prev, data])
      setDocs((prev) => prev.map((d) => (d.id === selectedId ? { ...d, current_version: d.current_version + 1 } : d)))
      setNotice(`New version uploaded; current_version incremented.`)
      setRenewFile({ file_name: "", storage_url: "" })
      await loadVersions(selectedId)
    } catch (e) { setActionError(errorMessage(e, "Renewal failed.")) } finally { setRenewing(false) }
  }

  const acknowledge = async (id: number) => {
    setAcking(id); setActionError("")
    try {
      await api.post(API_PATHS.ack(id), {})
      setAckState((prev) => ({ ...prev, [id]: "Acknowledged." }))
      setNotice(`Document #${id} acknowledged.`)
    } catch (e) {
      const msg = errorMessage(e, "Acknowledgement failed.")
      setAckState((prev) => ({ ...prev, [id]: msg }))
      if ((e as { response?: { status?: number } })?.response?.status === 403) setActionError(msg)
    } finally { setAcking(null) }
  }

  if (!canView) {
    return <Layout><EmptyState title="Not visible for your role" description={`The documents library requires ${ALLOWED_ROLES.join(" or ")}; your role is ${user?.role || "unknown"}.`} /></Layout>
  }

  if (loading) return <Layout><LoadingRegion label="Documents library"><TableSkeleton rows={5} cols={7} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Documents Library" description="LP-DOC-001/002 · browse employee documents, upload, renew versions, acknowledge — read-mostly UI on live endpoints." />
      <div className="max-w-6xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The documents library could not be read." fallback="The documents library could not be read." onRetry={load} />}

        <SectionCard compact title="Library" description="Employee filter runs server-side (?employee_id=); text/type/status/expiry filters are client-side only.">
          <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
            <div>
              <label>Employee ID (server filter)</label>
              <div className="flex gap-2">
                <Input value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} placeholder="e.g. 12" className="font-mono" />
                <Button onClick={load}>Apply</Button>
              </div>
            </div>
            <div>
              <label>Search (client-side)</label>
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="file, type, employee…" />
            </div>
            <div>
              <label>Type</label>
              <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="w-full rounded border px-3 py-2">
                <option value="all">All types</option>
                {DOCUMENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label>Status</label>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-full rounded border px-3 py-2">
                <option value="all">All statuses</option>
                {DOCUMENT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label>Expiry</label>
              <select value={bucketFilter} onChange={(e) => setBucketFilter(e.target.value as ExpiryFilter)} className="w-full rounded border px-3 py-2">
                <option value="all">All</option>
                <option value="Valid">Valid</option>
                <option value="Expiring">Expiring ≤30d</option>
                <option value="Expired">Expired</option>
              </select>
            </div>
          </div>
          {visible.length === 0 ? (
            <EmptyState title="No documents" description="No documents match — upload one below or clear the filters." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left">
                    <th>Employee</th><th>Type</th><th>File</th><th>Version</th><th>Status</th><th>Expiry</th><th>Uploaded</th><th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((d) => (
                    <tr key={d.id}>
                      <td className="font-mono">{d.employee_id}</td>
                      <td className="font-medium">{d.document_type}</td>
                      <td><a className="action-link" href={fileUrl(d.storage_url)} target="_blank" rel="noreferrer">{d.file_name}</a></td>
                      <td className="font-mono">v{d.current_version}</td>
                      <td><StatusPill status={d.status} /></td>
                      <td>{d.expiry_date || "—"} <span className="text-xs text-fg-muted">({expiryBadge(d)})</span></td>
                      <td className="font-mono">{d.uploaded_at || "—"}</td>
                      <td>
                        <div className="flex gap-2">
                          <Button onClick={() => loadVersions(d.id)}>History</Button>
                          <Button onClick={() => acknowledge(d.id)} disabled={acking === d.id}>{acking === d.id ? "Ack…" : "Acknowledge"}</Button>
                        </div>
                        {ackState[d.id] && <div className="text-xs text-fg-muted mt-1">{ackState[d.id]}</div>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard compact title="Upload / associate document" description="POST /employee-documents only. Status defaults to Active server-side.">
          {!canUpload && <Alert tone="error">Upload requires SuperAdmin — your role is {user?.role}. Attempts return 403.</Alert>}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div><label>Employee ID</label><Input value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: e.target.value })} disabled={!canUpload || saving} className="font-mono" placeholder="e.g. 12" /></div>
            <div><label>Document type</label>
              <select value={form.document_type} onChange={(e) => setForm({ ...form, document_type: e.target.value })} disabled={!canUpload || saving} className="w-full rounded border px-3 py-2">
                {DOCUMENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div><label>File name</label><Input value={form.file_name} onChange={(e) => setForm({ ...form, file_name: e.target.value })} disabled={!canUpload || saving} placeholder="offer-letter.pdf" /></div>
            <div><label>Storage URL</label><Input value={form.storage_url} onChange={(e) => setForm({ ...form, storage_url: e.target.value })} disabled={!canUpload || saving} className="font-mono" placeholder="/api/v1/files/…" /></div>
            <div><label>Expiry date</label><Input value={form.expiry_date} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} disabled={!canUpload || saving} className="font-mono" placeholder="YYYY-MM-DD" /></div>
            <div><label>Retention until</label><Input value={form.retention_until} onChange={(e) => setForm({ ...form, retention_until: e.target.value })} disabled={!canUpload || saving} className="font-mono" placeholder="YYYY-MM-DD" /></div>
          </div>
          <Button onClick={upload} disabled={!canUpload || saving || !form.employee_id || !form.file_name || !form.storage_url} className="mt-4">{saving ? "Uploading…" : "Upload document"}</Button>
        </SectionCard>

        {selectedId !== null && (
          <SectionCard compact title={`Version history — document #${selectedId}`} description="Oldest-first from GET /employee-documents/{id}/versions. Renewal uploads a new version only.">
            {versionsLoading ? <LoadingRegion label="Version history"><TableSkeleton rows={3} cols={4} /></LoadingRegion>
              : versionsError ? <RetryableAlert err={versionsError} title="Version history could not be read." fallback="Version history could not be read." onRetry={() => loadVersions(selectedId)} />
              : versions.length === 0 ? <EmptyState title="No versions" description="No versions recorded for this document yet." />
              : (
                <table className="w-full text-sm mb-4">
                  <thead><tr className="text-left"><th>Version</th><th>File</th><th>Uploaded by</th><th>Uploaded at</th></tr></thead>
                  <tbody>
                    {versions.map((v, i) => (
                      <tr key={`${v.version_no}-${i}`}>
                        <td className="font-mono">v{v.version_no}</td>
                        <td className="font-medium">{v.file_name}</td>
                        <td>{v.uploaded_by || "—"}</td>
                        <td className="font-mono">{v.uploaded_at || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            <div className="grid sm:grid-cols-2 gap-4">
              <div><label>New file name</label><Input value={renewFile.file_name} onChange={(e) => setRenewFile({ ...renewFile, file_name: e.target.value })} disabled={renewing} placeholder="contract-v2.pdf" /></div>
              <div><label>New storage URL</label><Input value={renewFile.storage_url} onChange={(e) => setRenewFile({ ...renewFile, storage_url: e.target.value })} disabled={renewing} className="font-mono" placeholder="/api/v1/files/…" /></div>
            </div>
            <Button onClick={renew} disabled={renewing || !renewFile.file_name || !renewFile.storage_url} className="mt-4">{renewing ? "Uploading…" : "Upload new version"}</Button>
          </SectionCard>
        )}

        <div className="text-xs text-fg-muted">LP-DOC-001/002 · expiry badge is client-side (30-day rule; no job or email) · audit outcomes surface as action notices only.</div>
      </div>
    </Layout>
  )
}
