import { cn } from "@/lib/utils"

export function BulkBar({
  selectedCount,
  totalCount,
  onSelectAll,
  allSelected,
  actions,
  className,
}: {
  selectedCount: number
  totalCount: number
  onSelectAll?: () => void
  allSelected?: boolean
  actions?: React.ReactNode
  className?: string
}) {
  if (selectedCount === 0) return null
  return (
    <div
      role="toolbar"
      aria-label="Bulk actions"
      className={cn(
        "flex items-center gap-3 px-4 py-2.5 rounded-lg border border-border bg-surface text-sm sticky top-0 z-10 shadow-sm transition-all duration-150",
        className
      )}
    >
      <span className="font-medium text-fg">
        {selectedCount} of {totalCount} selected
      </span>
      {onSelectAll && (
        <button
          type="button"
          onClick={onSelectAll}
          className="text-xs font-medium text-brand-600 hover:underline min-h-[44px] inline-flex items-center"
        >
          {allSelected ? "Deselect all" : "Select all"}
        </button>
      )}
      <div className="ml-auto flex items-center gap-2">{actions}</div>
    </div>
  )
}
