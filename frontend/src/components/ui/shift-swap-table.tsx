import { StatusPill } from "@/components/ui"
import { Button } from "./button"
import { Table } from "./table"

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
 * Domain wrapper ON kit `Table`: Entry, Requester, Target, Date, Status
 * and Actions columns. Approve/Reject actions are shown for pending swaps
 * only when `canManage` is true; otherwise a muted note ("Awaiting manager
 * decision" / "Resolved") is shown.
 *
 * `compact` is accepted for back-compat; density is owned by kit Table now.
 */
export function ShiftSwapTable({
  swaps,
  onApprove,
  onReject,
  canManage = true,
  compact = false,
}: ShiftSwapTableProps) {
  void compact
  return (
    <Table
      columns={[
        { key: "entry", header: "Entry", accessor: (s) => <span className="font-mono text-xs">#{s.entry}</span> },
        { key: "requester", header: "Requester", accessor: (s) => <span className="text-sm text-fg">{s.requester}</span> },
        { key: "target", header: "Target", accessor: (s) => <span className="text-sm text-fg">{s.target ?? "—"}</span> },
        { key: "date", header: "Date", accessor: (s) => (
          <span className="text-sm text-fg whitespace-nowrap">
            {s.proposed_date ?? "—"}
          </span>
        ) },
        { key: "status", header: "Status", accessor: (s) => <StatusPill status={s.status} /> },
        { key: "actions", header: "Actions", accessor: (s) => {
          const pending = s.status === "Pending"
          const canAct = pending && canManage
          return canAct ? (
            <div className="flex items-center gap-3">
              <Button variant="ghost" onClick={() => onApprove(s.id)}>
                Approve
              </Button>
              <Button variant="danger" onClick={() => onReject(s.id)}>
                Reject
              </Button>
            </div>
          ) : pending ? (
            <span className="text-xs text-text-secondary">
              Awaiting manager decision
            </span>
          ) : (
            <span className="text-xs text-text-secondary">Resolved</span>
          )
        } },
      ]}
      data={swaps}
      keyAccessor={(s) => s.id}
      caption="Shift swap requests"
      sortable={false}
    />
  )
}
