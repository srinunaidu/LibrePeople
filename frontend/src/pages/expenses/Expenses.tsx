/* LP-EXP-001 — expense claims list (employee + approver queue).
 * GET /expenses/claims; visibility is server-enforced (expenses.py:259-266):
 * Associates see only their own claims, so the UI never sends employee_id.
 * HR/Admin get the team/all queue plus a ?status= filter (:264-265).
 */
import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Layout } from "@/components/Layout"
import {
  Alert,
  Button,
  EmptyState,
  LoadingRegion,
  PageHeader,
  RetryableAlert,
  SectionCard,
  TableSkeleton, Table } from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { errorMessage } from "@/lib/api"
import { CLAIM_STATUS_FILTERS, isManagerRole, statusLabel, type ExpenseClaim } from "./shared"

function statusOf(err: unknown): number | undefined {
  return (err as { response?: { status?: number } })?.response?.status
}

export default function Expenses() {
  const { user } = useAuth()
  const role = user?.role
  const queue = isManagerRole(role)
  const [claims, setClaims] = useState<ExpenseClaim[]>([])
  const [statusFilter, setStatusFilter] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Server-enforced visibility: no employee_id is ever sent for
      // Associates (or anyone) — the backend scopes by caller.
      const params = statusFilter ? { status: statusFilter } : {}
      const { data } = await api.get("/expenses/claims", { params })
      setClaims(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e)
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <Layout>
        <LoadingRegion label="Loading expense claims">
          <TableSkeleton rows={5} cols={5} />
        </LoadingRegion>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader
        compact
        title={queue ? "Expense claims queue" : "My expense claims"}
        description={
          queue
            ? "Team/all claims per server visibility. Filter by status; approve from the claim detail."
            : "Your claims. The server scopes this list to you — nothing is fabricated."
        }
        actions={
          <Link to="new" className="btn btn-primary btn-sm">
            New claim
          </Link>
        }
      />
      {!!error && statusOf(error) === 403 ? (
        <EmptyState
          title="Not visible for your role"
          description={`Expense claims require a workforce role; your role is ${role || "unknown"}.`}
        />
      ) : (
        !!error && (
          <RetryableAlert
            err={error}
            title="The expense claims could not be read."
            fallback="The expense claims could not be read."
            onRetry={load}
          />
        )
      )}
      {!error && (
        <SectionCard
          compact
          title={queue ? "All claims" : "My claims"}
          description={
            queue ? "Same endpoint the employee list uses; visibility stays server-side." : undefined
          }
        >
          {queue && (
            <div className="mb-4 flex items-center gap-2">
              <label htmlFor="exp-status-filter" className="field-label">
                Filter by status
              </label>
              <select
                id="exp-status-filter"
                aria-label="Filter by status"
                className="rounded border px-3 py-2"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All statuses</option>
                {CLAIM_STATUS_FILTERS.map((s) => (
                  <option key={s} value={s}>
                    {statusLabel(s)}
                  </option>
                ))}
              </select>
            </div>
          )}
          {claims.length === 0 ? (
            <EmptyState
              title="No expense claims"
              description={
                queue
                  ? "Nothing matches this filter. Clear the status filter to see more."
                  : "You have no expense claims yet. File your first claim above."
              }
            />
          ) : (
            <Table
              columns={[
                { key: "claim", header: "Claim", accessor: (c) => <span className="font-mono">#{c.id}</span> },
                { key: "date", header: "Date", accessor: (c) => c.expense_date },
                { key: "amount", header: "Amount", accessor: (c) => <>{c.amount} {c.currency}</> },
                { key: "status", header: "Status", accessor: (c) => statusLabel(c.status) },
                { key: "payment", header: "Payment", accessor: (c) => c.payment_status },
                {
                  key: "actions",
                  header: "",
                  accessor: (c) => (
                    <Link to={`${c.id}`} className="btn btn-secondary btn-sm">
                      View
                    </Link>
                  ),
                },
              ]}
              data={claims}
              keyAccessor={(c) => c.id}
              caption="Expense claims"
              sortable={false}
            />
          )}
        </SectionCard>
      )}
      <div className="mt-4">
        <Button variant="secondary" onClick={load}>
          Reload
        </Button>
      </div>
      {!!error && statusOf(error) !== 403 && (
        <div className="mt-2">
          <Alert tone="error">{errorMessage(error, "The expense claims could not be read.")}</Alert>
        </div>
      )}
    </Layout>
  )
}
