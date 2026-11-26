import { IconCheck } from "@/components/icons"
import { StatusPill } from "@/components/ui"
import type { ShiftTemplate } from "@/types"
import { Button } from "./button"
import { Table } from "./table"

/**
 * Shared shift-template table (AC-05).
 *
 * Domain wrapper ON kit `Table`: Code, Name, Hours, Break, Night, Active
 * and Actions columns. Used by Scheduling.tsx (and available to
 * RosterBuilder.tsx) so both pages share identical padding, font sizes,
 * badge alignment and action-button layout.
 *
 * `compact` is accepted for back-compat; density is owned by kit Table now.
 */
export interface ShiftTemplateTableProps {
  templates: ShiftTemplate[]
  onEdit: (id: number) => void
  onDelete: (id: number) => void
  compact?: boolean
}

export function ShiftTemplateTable({
  templates,
  onEdit,
  onDelete,
  compact = false,
}: ShiftTemplateTableProps) {
  void compact
  return (
    <Table
      columns={[
        { key: "code", header: "Code", accessor: (t) => <span className="font-mono text-xs">{t.code}</span> },
        { key: "name", header: "Name", accessor: (t) => <span className="text-sm text-fg">{t.name}</span> },
        { key: "hours", header: "Hours", accessor: (t) => (
          <span className="text-sm text-fg whitespace-nowrap">
            {t.start_time}–{t.end_time}
          </span>
        ) },
        { key: "break", header: "Break", accessor: (t) => <span className="text-sm text-fg">{t.break_minutes}m</span>, cellClassName: "num" },
        { key: "night", header: "Night", accessor: (t) => <StatusPill status={t.is_night ? "Night" : "Day"} /> },
        { key: "active", header: "Active", accessor: (t) => (
          t.is_active ? (
            <IconCheck className="w-4 h-4 text-fg" />
          ) : (
            <span className="text-fg-muted">—</span>
          )
        ) },
        { key: "actions", header: "Actions", accessor: (t) => (
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => onEdit(t.id)}>
              Edit
            </Button>
            <Button variant="danger" onClick={() => onDelete(t.id)}>
              Delete
            </Button>
          </div>
        ) },
      ]}
      data={templates}
      keyAccessor={(t) => t.id}
      caption="Configured shift templates"
      sortable={false}
    />
  )
}
