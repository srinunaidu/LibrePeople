import { IconCheck } from "@/components/icons"
import { StatusPill } from "@/components/ui"
import { cn } from "@/lib/utils"
import type { ShiftTemplate } from "@/types"

/**
 * Shared shift-template table (AC-05).
 *
 * Renders a `table-base` table of shift templates with Code, Name, Hours,
 * Break, Night, Active and Actions columns. Used by Scheduling.tsx (and
 * available to RosterBuilder.tsx) so both pages share identical padding,
 * font sizes, badge alignment and action-button layout.
 *
 * `compact` reduces cell padding for data-dense pages via `.table-compact`.
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
  return (
    <table
      className={cn("table-base table-striped", compact ? "table-compact" : "")}
      role="table"
      aria-label="Configured shift templates"
    >
      <caption className="sr-only">Configured shift templates</caption>
      <thead>
        <tr>
          <th scope="col">Code</th>
          <th scope="col">Name</th>
          <th scope="col">Hours</th>
          <th scope="col" className="num">
            Break
          </th>
          <th scope="col">Night</th>
          <th scope="col">Active</th>
          <th scope="col">Actions</th>
        </tr>
      </thead>
      <tbody>
        {templates.map((t) => (
          <tr key={t.id}>
            <td className="font-mono text-xs">{t.code}</td>
            <td className="text-sm text-fg">{t.name}</td>
            <td className="text-sm text-fg whitespace-nowrap">
              {t.start_time}–{t.end_time}
            </td>
            <td className="text-sm text-fg num">{t.break_minutes}m</td>
            <td><StatusPill status={t.is_night ? "Night" : "Day"} /></td>
            <td>
              {t.is_active ? (
                <IconCheck className="w-4 h-4 text-fg" />
              ) : (
                <span className="text-fg-muted">—</span>
              )}
            </td>
            <td>
              <div className="flex items-center gap-3">
                <button className="action-link" onClick={() => onEdit(t.id)}>
                  Edit
                </button>
                <button className="action-link-danger" onClick={() => onDelete(t.id)}>
                  Delete
                </button>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
