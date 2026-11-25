import { StatusPill } from "@/components/ui"
import { cn } from "@/lib/utils"

export interface ShiftSwapRow {
  id: number
  entry: number | string
  requester: string
  target: string | null | undefined
  proposed_date: string | null | undefined
  status: string
}

export interface ShiftSwapTableProps {
  swaps: ShiftSwapRow[]
  onApprove: (id: number) => void
  onReject: (id: number) => void
  canManage?: boolean
  compact?: boolean
}

/**
 * Shared shift-swap table (AC-06).
 *
 * Renders a `table-base` table of swap requests with Entry, Requester,
 * Target, Date, Status and Actions columns. Approve/Reject actions are
 * shown for pending swaps only when `canManage` is true; otherwise a muted
 * note ("Awaiting manager decision" / "Resolved") is shown. Styling is
 * consistent with ShiftTemplateTable.
 */
export function ShiftSwapTable({
  swaps,
  onApprove,
  onReject,
  canManage = true,
  compact = false,
}: ShiftSwapTableProps) {
  return (
    <table
      className={cn("table-base table-striped", compact ? "table-compact" : "")}
      role="table"
      aria-label="Shift swap requests"
    >
      <caption className="sr-only">Shift swap requests</caption>
      <thead>
        <tr>
          <th scope="col">Entry</th>
          <th scope="col">Requester</th>
          <th scope="col">Target</th>
          <th scope="col">Date</th>
          <th scope="col">Status</th>
          <th scope="col">Actions</th>
        </tr>
      </thead>
      <tbody>
        {swaps.map((s) => {
          const pending = s.status === "Pending"
          const canAct = pending && canManage
          return (
            <tr key={s.id}>
              <td className="font-mono text-xs">#{s.entry}</td>
              <td className="text-sm text-fg">{s.requester}</td>
              <td className="text-sm text-fg">{s.target ?? "—"}</td>
              <td className="text-sm text-fg whitespace-nowrap">
                {s.proposed_date ?? "—"}
              </td>
              <td><StatusPill status={s.status} /></td>
              <td>
                {canAct ? (
                  <div className="flex items-center gap-3">
                    <button className="action-link" onClick={() => onApprove(s.id)}>
                      Approve
                    </button>
                    <button className="action-link-danger" onClick={() => onReject(s.id)}>
                      Reject
                    </button>
                  </div>
                ) : pending ? (
                  <span className="text-xs text-text-secondary">
                    Awaiting manager decision
                  </span>
                ) : (
                  <span className="text-xs text-text-secondary">Resolved</span>
                )}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
