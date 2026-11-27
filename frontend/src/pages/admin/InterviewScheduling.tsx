/* RC-04 — Interview scheduling (depends RC-03; candidate stages shipped R3).
 * R2 honesty-sweep: list/create/update go to the live recruiting CRUD —
 * real GET/POST/PUT /api/v1/interviews (backend/app/api/v1/endpoints/interviews.py,
 * mounted at api.py:53; require_roles SuperAdmin/HR). The former
 * feature-flags shim is gone — nothing here is read from or written to
 * client config. No fabricated interview data; an empty ledger renders
 * an EmptyState, never invented rows.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Alert, Button, EmptyState, Input, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton, Table } from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import { listInterviews, createInterview, updateInterview, errorMessage, type InterviewOut } from "@/lib/api"

const STAGES = ["Screening", "Phone Screen", "Technical Interview", "Panel Interview", "Final Round"]
const STATUSES = ["Scheduled", "Completed", "Cancelled", "NoShow"]

export default function InterviewScheduling() {
  const { user } = useAuth()
  const canAdmin = ["SuperAdmin", "HR"].includes(user?.role ?? "")

  const [interviews, setInterviews] = useState<InterviewOut[]>([])
  const [candidateId, setCandidateId] = useState("")
  const [stage, setStage] = useState("Screening")
  const [scheduledAt, setScheduledAt] = useState("")
  const [interviewers, setInterviewers] = useState("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [error, setError] = useState<unknown | null>(null)
  const [edits, setEdits] = useState<Record<number, { status: string; feedback: string }>>({})

  const load = useCallback(async () => {
    if (!canAdmin) { setLoading(false); return }
    setLoading(true); setError(null); setNotice("")
    try {
      const rows = await listInterviews({ limit: 100 })
      setInterviews(rows)
      setEdits(Object.fromEntries(rows.map(r => [r.id, { status: r.status, feedback: r.feedback ?? "" }])))
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canAdmin])
  useEffect(() => { load() }, [load])

  const save = async () => {
    const cid = Number(candidateId)
    if (!Number.isInteger(cid) || cid <= 0) { setActionError("Candidate ID is required — enter the numeric candidate id."); return }
    setSaving(true); setNotice(""); setActionError("")
    try {
      await createInterview({
        candidate_id: cid,
        stage,
        scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : null,
        interviewers: interviewers.split(",").map(s => s.trim()).filter(Boolean),
      })
      setCandidateId(""); setScheduledAt(""); setInterviewers("")
      await load()
      setNotice("Interview scheduled.")
    } catch (e) { setActionError(errorMessage(e, "The interview could not be scheduled.")) } finally { setSaving(false) }
  }

  const saveRow = async (id: number) => {
    const edit = edits[id]
    if (!edit) return
    setUpdatingId(id); setNotice(""); setActionError("")
    try {
      await updateInterview(id, { status: edit.status, feedback: edit.feedback || null })
      await load()
      setNotice("Interview updated.")
    } catch (e) { setActionError(errorMessage(e, "The interview could not be updated.")) } finally { setUpdatingId(null) }
  }

  if (!canAdmin) return <Layout><EmptyState title="Not visible for your role" description={`Interview scheduling requires SuperAdmin or HR; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Interview Scheduling"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Interview Scheduling" description="RC-04 · live interview ledger from GET /api/v1/interviews (SuperAdmin / HR)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="Interviews could not be read." fallback="Interviews could not be read." onRetry={load} />}
        <SectionCard compact title="Schedule an interview" description="Writes to POST /api/v1/interviews.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="interview-candidate">Candidate ID</label>
              <Input id="interview-candidate" inputMode="numeric" value={candidateId} onChange={e => setCandidateId(e.target.value)} placeholder="e.g. 42" />
            </div>
            <div>
              <label htmlFor="interview-stage">Stage</label>
              <select id="interview-stage" value={stage} onChange={e => setStage(e.target.value)} className="w-full rounded border px-3 py-2">
                {STAGES.map(s => (<option key={s} value={s}>{s}</option>))}
              </select>
            </div>
            <div>
              <label htmlFor="interview-when">Scheduled at</label>
              <Input id="interview-when" type="datetime-local" value={scheduledAt} onChange={e => setScheduledAt(e.target.value)} />
            </div>
            <div>
              <label htmlFor="interview-panel">Interviewers (comma-separated)</label>
              <Input id="interview-panel" value={interviewers} onChange={e => setInterviewers(e.target.value)} placeholder="e.g. priya, omar" />
            </div>
          </div>
          <Button
            onClick={save}
            disabled={saving || !candidateId.trim()}
            title={!candidateId.trim() ? "Enter a candidate ID first — the backend requires one." : "Schedule via POST /api/v1/interviews"}
            className="mt-4"
          >
            {saving ? "Scheduling…" : "Schedule interview"}
          </Button>
          {!candidateId.trim() && <p className="text-xs text-fg-muted mt-2">Enter a candidate ID to enable scheduling — the backend rejects rows without one.</p>}
        </SectionCard>
        <SectionCard
          compact
          title="Scheduled interviews"
          description="From GET /api/v1/interviews; status and feedback persist via PUT /api/v1/interviews/:id."
          actions={<Button variant="secondary" size="sm" onClick={() => load()} disabled={loading}>{loading ? "Refreshing…" : "Refresh"}</Button>}
        >
          {interviews.length === 0 ? (
            <EmptyState title="No interviews scheduled" description="The live ledger is empty — schedule the first interview above. Nothing is shown that the backend does not store." />
          ) : (
            <Table
              columns={[
                { key: "id", header: "ID", accessor: (iv) => <span className="py-2 pr-3 tabular-nums">{iv.id}</span> },
                { key: "candidate", header: "Candidate", accessor: (iv) => <span className="py-2 pr-3 tabular-nums">{iv.candidate_id}</span> },
                { key: "stage", header: "Stage", accessor: (iv) => <span className="py-2 pr-3">{iv.stage}</span> },
                {
                  key: "status",
                  header: "Status",
                  accessor: (iv) => (
                    <span className="py-2 pr-3">
                      <select
                        aria-label={`Status for interview ${iv.id}`}
                        value={edits[iv.id]?.status ?? iv.status}
                        onChange={e => setEdits(prev => ({ ...prev, [iv.id]: { status: e.target.value, feedback: prev[iv.id]?.feedback ?? "" } }))}
                        className="rounded border px-2 py-1"
                      >
                        {STATUSES.map(s => (<option key={s} value={s}>{s}</option>))}
                      </select>
                    </span>
                  ),
                },
                {
                  key: "feedback",
                  header: "Feedback",
                  accessor: (iv) => (
                    <span className="py-2 pr-3">
                      <Input
                        aria-label={`Feedback for interview ${iv.id}`}
                        value={edits[iv.id]?.feedback ?? ""}
                        onChange={e => setEdits(prev => ({ ...prev, [iv.id]: { status: prev[iv.id]?.status ?? iv.status, feedback: e.target.value } }))}
                        placeholder="Outcome notes"
                      />
                    </span>
                  ),
                },
                {
                  key: "actions",
                  header: "",
                  accessor: (iv) => (
                    <span className="py-2">
                      <Button variant="secondary" size="sm" onClick={() => saveRow(iv.id)} disabled={updatingId === iv.id}>
                        {updatingId === iv.id ? "Saving…" : "Save"}
                      </Button>
                    </span>
                  ),
                },
              ]}
              data={interviews}
              keyAccessor={(iv) => iv.id}
              caption="Scheduled interviews"
              sortable={false}
            />
          )}
        </SectionCard>
        <div className="text-xs text-fg-muted">RC-04 · reads and writes /api/v1/interviews · no fabricated interview data.</div>
      </div>
    </Layout>
  )
}
