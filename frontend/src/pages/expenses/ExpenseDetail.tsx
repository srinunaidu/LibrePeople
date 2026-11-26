/* LP-EXP-001/002/003 — expense claim detail: submit, L1/L2 approve,
 * reject/rework, mark-paid, receipt upload + view.
 * Every mutation posts its exact endpoint then refetches — the server is the
 * source of truth (no optimistic local-only state). Associate clicks on
 * approve/pay are never sent: the buttons are not rendered for Associates.
 */
import { useCallback, useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { Layout } from "@/components/Layout"
import {
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  RetryableAlert,
  SectionCard,
  TableSkeleton,
} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { errorMessage } from "@/lib/api"
import {
  canFinalApprove,
  canL1Approve,
  canMarkPaid,
  canReject,
  canRework,
  canSubmit,
  canUploadReceipt,
  isAdminRole,
  showApproveActions,
  statusLabel,
  type ExpenseClaim,
  type ExpenseReceipt,
} from "./shared"

function statusOf(err: unknown): number | undefined {
  return (err as { response?: { status?: number } })?.response?.status
}

export default function ExpenseDetail() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const role = user?.role
  const [claim, setClaim] = useState<ExpenseClaim | null>(null)
  const [receipts, setReceipts] = useState<ExpenseReceipt[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown | null>(null)
  const [actionError, setActionError] = useState("")
  const [notice, setNotice] = useState("")
  const [busy, setBusy] = useState("")
  const [rejectReason, setRejectReason] = useState("")
  const [file, setFile] = useState<File | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const [claimRes, receiptRes] = await Promise.all([
        api.get(`/expenses/claims/${id}`),
        api.get(`/expenses/claims/${id}/receipts`),
      ])
      setClaim(claimRes.data)
      setReceipts(Array.isArray(receiptRes.data) ? receiptRes.data : [])
    } catch (e) {
      // A claim whose receipts row is missing still shows the claim.
      if (statusOf(e) === 404) {
        setError(e)
      } else {
        try {
          const { data } = await api.get(`/expenses/claims/${id}`)
          setClaim(data)
          setReceipts([])
        } catch (inner) {
          setError(inner)
        }
      }
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  /** Post one state-machine move, then refetch from the server. */
  const act = async (key: string, run: () => Promise<unknown>, ok: string) => {
    setBusy(key)
    setActionError("")
    setNotice("")
    try {
      await run()
      setNotice(ok)
      await load()
    } catch (e) {
      // 409s (expense_claim_locked, expense_invalid_payment_state) and the
      // archived-category conflict carry the server's message verbatim.
      setActionError(errorMessage(e, "The expense action was refused."))
    } finally {
      setBusy("")
    }
  }

  const uploadReceipt = async () => {
    if (!file || !id) return
    const form = new FormData()
    form.append("file", file)
    await act(
      "receipt",
      () =>
        api.post(`/expenses/claims/${id}/receipts`, form, {
          headers: { "Content-Type": "multipart/form-data" },
        }),
      "Receipt uploaded.",
    )
    setFile(null)
  }

  if (loading) {
    return (
      <Layout>
        <LoadingRegion label="Loading expense claim">
          <TableSkeleton rows={4} cols={2} />
        </LoadingRegion>
      </Layout>
    )
  }

  if (error && statusOf(error) === 403) {
    return (
      <Layout>
        <EmptyState
          title="Not visible for your role"
          description={`This claim needs reporting-line visibility; your role is ${role || "unknown"}.`}
        />
      </Layout>
    )
  }

  if (error && statusOf(error) === 404) {
    return (
      <Layout>
        <EmptyState
          title="Expense claim not found"
          description="This claim was removed or never existed. Reload to get the current list."
          action={
            <button type="button" className="btn btn-secondary btn-sm" onClick={load}>
              Reload
            </button>
          }
        />
      </Layout>
    )
  }

  if (error || !claim) {
    return (
      <Layout>
        <RetryableAlert
          err={error}
          title="The expense claim could not be read."
          fallback="The expense claim could not be read."
          onRetry={load}
        />
      </Layout>
    )
  }

  const showActions = showApproveActions(role)
  const uploadable = canUploadReceipt(claim.status)

  return (
    <Layout>
      <PageHeader
        compact
        title={`Expense claim #${claim.id}`}
        description={`${statusLabel(claim.status)} · payment ${claim.payment_status} · ${claim.amount} ${claim.currency} on ${claim.expense_date}`}
        actions={
          <Link to=".." className="btn btn-secondary btn-sm">
            Back to claims
          </Link>
        }
      />
      {notice && <Alert tone="success">{notice}</Alert>}
      {actionError && <Alert tone="error">{actionError}</Alert>}

      <div className="grid gap-5 lg:grid-cols-2">
        <SectionCard compact title="Claim" description="Server state after the last refetch.">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-fg-muted">Employee</dt>
            <dd className="font-mono">{claim.employee_id}</dd>
            <dt className="text-fg-muted">Category</dt>
            <dd className="font-mono">{claim.category_id}</dd>
            <dt className="text-fg-muted">Date</dt>
            <dd>{claim.expense_date}</dd>
            <dt className="text-fg-muted">Amount</dt>
            <dd>
              {claim.amount} {claim.currency}
            </dd>
            <dt className="text-fg-muted">Status</dt>
            <dd>{statusLabel(claim.status)}</dd>
            <dt className="text-fg-muted">Payment</dt>
            <dd>{claim.payment_status}</dd>
            {claim.description && (
              <>
                <dt className="text-fg-muted">Description</dt>
                <dd>{claim.description}</dd>
              </>
            )}
            {claim.rejection_reason && (
              <>
                <dt className="text-fg-muted">Rejection reason</dt>
                <dd>{claim.rejection_reason}</dd>
              </>
            )}
          </dl>
        </SectionCard>

        <SectionCard compact title="Actions" description="Each move posts, then the claim is re-read.">
          <div className="flex flex-wrap gap-2">
            {canSubmit(claim.status) && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={busy === "submit"}
                onClick={() =>
                  act("submit", () => api.post(`/expenses/claims/${claim.id}/submit`), "Claim submitted.")
                }
              >
                {busy === "submit" ? "Submitting…" : "Submit for approval"}
              </button>
            )}
            {showActions && canL1Approve(role, claim.status) && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={busy === "l1"}
                onClick={() =>
                  act("l1", () => api.post(`/expenses/claims/${claim.id}/l1-approve`), "L1 approval recorded.")
                }
              >
                {busy === "l1" ? "Approving…" : "Approve (L1)"}
              </button>
            )}
            {showActions && canFinalApprove(role, claim.status) && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={busy === "approve"}
                onClick={() =>
                  act("approve", () => api.post(`/expenses/claims/${claim.id}/approve`), "Final approval recorded.")
                }
              >
                {busy === "approve" ? "Approving…" : "Approve (final)"}
              </button>
            )}
            {showActions && isAdminRole(role) && canMarkPaid(role, claim.status, claim.payment_status) && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={busy === "paid"}
                onClick={() =>
                  act("paid", () => api.post(`/expenses/claims/${claim.id}/mark-paid`), "Claim marked paid.")
                }
              >
                {busy === "paid" ? "Marking…" : "Mark paid"}
              </button>
            )}
            {showActions && canReject(role, claim.status) && (
              <span className="inline-flex items-center gap-2">
                <input
                  aria-label="Rejection reason"
                  className="input"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Reason (optional)"
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={busy === "reject"}
                  onClick={() =>
                    act(
                      "reject",
                      () => api.post(`/expenses/claims/${claim.id}/reject`, { reason: rejectReason || undefined }),
                      "Claim rejected.",
                    )
                  }
                >
                  {busy === "reject" ? "Rejecting…" : "Reject"}
                </button>
              </span>
            )}
            {canRework(claim.status) && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={busy === "rework"}
                onClick={() =>
                  act("rework", () => api.post(`/expenses/claims/${claim.id}/rework`), "Claim sent back to draft.")
                }
              >
                {busy === "rework" ? "Sending…" : "Send back to draft"}
              </button>
            )}
            {!canSubmit(claim.status) &&
              !canL1Approve(role, claim.status) &&
              !canFinalApprove(role, claim.status) &&
              !canMarkPaid(role, claim.status, claim.payment_status) &&
              !canReject(role, claim.status) &&
              !canRework(claim.status) && <span className="text-sm text-fg-muted">No actions available.</span>}
          </div>
        </SectionCard>
      </div>

      <div className="mt-5">
        <SectionCard
          compact
          title="Receipts"
          description={
            uploadable
              ? "Attach while the claim is a draft or submitted; bytes stay server-side."
              : "Receipts lock once the claim passes first approval."
          }
        >
          {uploadable && (
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <input
                type="file"
                aria-label="Receipt file"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={!file || busy === "receipt"}
                onClick={uploadReceipt}
              >
                {busy === "receipt" ? "Uploading…" : "Upload receipt"}
              </button>
            </div>
          )}
          {receipts.length === 0 ? (
            <EmptyState title="No receipts" description="Nothing is attached to this claim yet." />
          ) : (
            <ul className="divide-y">
              {receipts.map((r) => (
                <li key={r.id} className="py-2 flex items-center justify-between gap-3">
                  <span className="text-sm">
                    {r.file_name}{" "}
                    <span className="text-fg-muted font-mono">({r.size_bytes} bytes)</span>
                  </span>
                  {/* Server download URL — never an object-URL or local blob. */}
                  <a className="btn btn-secondary btn-sm" href={r.download_url} download={r.file_name}>
                    Download
                  </a>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </div>
    </Layout>
  )
}
