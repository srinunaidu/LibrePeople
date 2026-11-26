/* Employee Relations — confidential case queue (gap #9).
 * HR/SuperAdmin only. Subjects never see their own cases: the API answers
 * 404 to anyone outside HR and the assignee, so this screen is gated on
 * the HR roles before it renders anything.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Alert, Button, EmptyState, Input, LoadingRegion, PageHeader, RetryableAlert, SectionCard, TableSkeleton } from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { errorMessage } from "@/lib/api"

const CASE_TYPES = [
  { value: "grievance", label: "Grievance" },
  { value: "discipline", label: "Discipline" },
  { value: "investigation", label: "Investigation" },
  { value: "whistleblowing", label: "Whistleblowing" },
]

const SEVERITIES = ["Low", "Medium", "High", "Critical"]
const STATUSES = ["Open", "Triaged", "Investigating", "ActionTaken", "Resolved", "Closed"]
const NEXT_STATUS: Record<string, string | null> = {
  Open: "Triaged",
  Triaged: "Investigating",
  Investigating: "ActionTaken",
  ActionTaken: "Resolved",
  Resolved: "Closed",
  Closed: null,
}

type ERCase = {
  id: number
  case_type: string
  subject_employee_id: number | null
  reported_by: string
  severity: string
  status: string
  assigned_to: string | null
  classification: string | null
  outcome: string | null
  created_at: string | null
  resolved_at: string | null
}

type ERComment = { id: number; case_id: number; author: string; comment: string; created_at: string | null }

export default function ERCases() {
  const { user } = useAuth()
  const canView = user?.role === "SuperAdmin" || user?.role === "HR"

  const [cases, setCases] = useState<ERCase[]>([])
  const [summary, setSummary] = useState<{ by_case_type: Record<string, number>; by_status: Record<string, number>; total: number } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown | null>(null)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [typeFilter, setTypeFilter] = useState("")
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [comments, setComments] = useState<ERComment[]>([])

  // create form
  const [newType, setNewType] = useState("grievance")
  const [newSeverity, setNewSeverity] = useState("Medium")
  const [newSubject, setNewSubject] = useState("")
  const [newClassification, setNewClassification] = useState("")
  const [newAssignee, setNewAssignee] = useState("")
  // detail form
  const [outcome, setOutcome] = useState("")
  const [assignee, setAssignee] = useState("")
  const [newComment, setNewComment] = useState("")
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    if (!canView) { setLoading(false); return }
    setLoading(true); setError(null)
    try {
      const params: Record<string, string> = {}
      if (statusFilter) params.status = statusFilter
      if (typeFilter) params.case_type = typeFilter
      const [{ data: list }, { data: summ }] = await Promise.all([
        api.get("/er-cases", { params }),
        api.get("/er-cases/summary"),
      ])
      setCases(Array.isArray(list) ? list : [])
      setSummary(summ)
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canView, statusFilter, typeFilter])

  useEffect(() => { load() }, [load])

  const loadComments = useCallback(async (id: number) => {
    try {
      const { data } = await api.get(`/er-cases/${id}/comments`)
      setComments(Array.isArray(data) ? data : [])
    } catch { setComments([]) }
  }, [])

  const selectCase = (c: ERCase) => {
    setSelectedId(c.id); setOutcome(c.outcome ?? ""); setAssignee(c.assigned_to ?? "")
    setActionError(""); setNotice("")
    loadComments(c.id)
  }

  const selected = cases.find(c => c.id === selectedId) ?? null

  const createCase = async () => {
    setSaving(true); setNotice(""); setActionError("")
    try {
      const payload: Record<string, unknown> = {
        case_type: newType,
        severity: newSeverity,
        classification: newClassification || null,
        assigned_to: newAssignee || null,
      }
      if (newSubject.trim()) payload.subject_employee_id = Number(newSubject.trim())
      const { data } = await api.post("/er-cases", payload)
      setNotice(`Case #${data.id} opened.`)
      setNewClassification(""); setNewAssignee(""); setNewSubject("")
      await load()
    } catch (e) { setActionError(errorMessage(e, "The case could not be opened.")) } finally { setSaving(false) }
  }

  const advance = async () => {
    if (!selected) return
    const next = NEXT_STATUS[selected.status]
    if (!next) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      const payload: Record<string, unknown> = { status: next }
      if (next === "Resolved") {
        if (!outcome.trim()) { setActionError("Resolving a case requires an outcome."); setSaving(false); return }
        payload.outcome = outcome.trim()
      }
      await api.put(`/er-cases/${selected.id}`, payload)
      setNotice(`Case #${selected.id} moved to ${next}.`)
      await load()
      const { data } = await api.get(`/er-cases/${selected.id}`)
      selectCase(data)
    } catch (e) { setActionError(errorMessage(e, "The case could not be updated.")) } finally { setSaving(false) }
  }

  const saveAssignment = async () => {
    if (!selected) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/er-cases/${selected.id}`, { assigned_to: assignee || null })
      setNotice(`Case #${selected.id} assignment saved.`)
      await load()
    } catch (e) { setActionError(errorMessage(e, "The assignment could not be saved.")) } finally { setSaving(false) }
  }

  const addComment = async () => {
    if (!selected || !newComment.trim()) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.post(`/er-cases/${selected.id}/comments`, { comment: newComment.trim() })
      setNewComment("")
      await loadComments(selected.id)
      setNotice("Note recorded.")
    } catch (e) { setActionError(errorMessage(e, "The note could not be recorded.")) } finally { setSaving(false) }
  }

  if (!canView) {
    return <Layout><EmptyState title="Not visible for your role" description={`Employee Relations is confidential and requires HR; your role is ${user?.role || "unknown"}.`} /></Layout>
  }
  if (loading) return <LoadingRegion label="Employee Relations"><TableSkeleton rows={4} cols={4} /></LoadingRegion>

  return (
    <Layout>
      <PageHeader compact title="Employee Relations" description="Confidential grievance, discipline, investigation and whistleblowing cases. HR only — subjects cannot see cases about themselves." />
      <div className="max-w-5xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="Employee Relations cases could not be read." fallback="Employee Relations cases could not be read." onRetry={load} />}

        {summary && (
          <SectionCard compact title="Queue summary" description="Aggregates only — no names or narratives.">
            <div className="flex flex-wrap gap-4 text-sm">
              <span>Total: <strong>{summary.total}</strong></span>
              {Object.entries(summary.by_status).map(([s, n]) => (
                <span key={s}>{s}: <strong>{n}</strong></span>
              ))}
            </div>
          </SectionCard>
        )}

        <SectionCard compact title="Open a case" description="Reporter is your signed-in account. No anonymous intake.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Case type</label>
              <select value={newType} onChange={e => setNewType(e.target.value)} className="w-full rounded border px-3 py-2">
                {CASE_TYPES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div>
              <label>Severity</label>
              <select value={newSeverity} onChange={e => setNewSeverity(e.target.value)} className="w-full rounded border px-3 py-2">
                {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label>Subject employee id (optional)</label>
              <Input value={newSubject} onChange={e => setNewSubject(e.target.value)} placeholder="e.g. 12" />
            </div>
            <div>
              <label>Assign to (username, optional)</label>
              <Input value={newAssignee} onChange={e => setNewAssignee(e.target.value)} placeholder="investigator username" />
            </div>
            <div className="sm:col-span-2">
              <label>Classification</label>
              <Input value={newClassification} onChange={e => setNewClassification(e.target.value)} placeholder="Short classification, no narrative in audit" />
            </div>
          </div>
          <Button onClick={createCase} disabled={saving} className="mt-4">{saving ? "Opening…" : "Open case"}</Button>
        </SectionCard>

        <SectionCard compact title="Queue" description="HR-only. Filter by status or type.">
          <div className="flex gap-4 mb-4">
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded border px-3 py-2">
              <option value="">All statuses</option>
              {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="rounded border px-3 py-2">
              <option value="">All types</option>
              {CASE_TYPES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
          {cases.length === 0 ? (
            <EmptyState title="No cases" description="No Employee Relations cases match the current filters." />
          ) : (
            <table className="w-full text-sm">
              <thead><tr><th>ID</th><th>Type</th><th>Severity</th><th>Status</th><th>Assignee</th><th></th></tr></thead>
              <tbody>
                {cases.map(c => (
                  <tr key={c.id}>
                    <td>#{c.id}</td><td>{c.case_type}</td><td>{c.severity}</td>
                    <td>{c.status}</td><td>{c.assigned_to ?? "—"}</td>
                    <td><Button onClick={() => selectCase(c)}>Open</Button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </SectionCard>

        {selected && (
          <SectionCard compact title={`Case #${selected.id} — ${selected.case_type}`} description={`Status: ${selected.status} · Severity: ${selected.severity} · Reported by ${selected.reported_by}`}>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label>Assign to (username)</label>
                <Input value={assignee} onChange={e => setAssignee(e.target.value)} placeholder="investigator username" />
                <Button onClick={saveAssignment} disabled={saving} className="mt-2">Save assignment</Button>
              </div>
              <div>
                <label>Outcome (required to resolve)</label>
                <Input value={outcome} onChange={e => setOutcome(e.target.value)} placeholder="Recorded action / finding" />
                {NEXT_STATUS[selected.status] && (
                  <Button onClick={advance} disabled={saving} className="mt-2">
                    Move to {NEXT_STATUS[selected.status]}
                  </Button>
                )}
              </div>
            </div>
            <div className="mt-6">
              <h4 className="font-semibold mb-2">Investigation notes (append-only)</h4>
              {comments.length === 0 ? <p className="text-sm text-fg-muted">No notes yet.</p> : (
                <ul className="space-y-2 text-sm">
                  {comments.map(m => <li key={m.id}><strong>{m.author}:</strong> {m.comment}</li>)}
                </ul>
              )}
              <div className="flex gap-2 mt-3">
                <Input value={newComment} onChange={e => setNewComment(e.target.value)} placeholder="Add an investigation note" />
                <Button onClick={addComment} disabled={saving || !newComment.trim()}>Add note</Button>
              </div>
            </div>
          </SectionCard>
        )}
        <div className="text-xs text-fg-muted">ER · confidential · closed cases retain full history · no PIP linkage in v1.</div>
      </div>
    </Layout>
  )
}
