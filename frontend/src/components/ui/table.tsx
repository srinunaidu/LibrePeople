import { cn } from "@/lib/utils"
import { useState, useMemo, useCallback } from "react"
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react"
import { Button } from "./button"
import { Input } from "./inputs"
import { Checkbox } from "./inputs"

export interface Column<T> {
  key: string
  header: string
  accessor: (row: T) => React.ReactNode
  sortable?: boolean
  filterable?: boolean
  className?: string
  headerClassName?: string
  cellClassName?: string
  width?: string
}

export interface TableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyAccessor: (row: T) => string | number
  sortable?: boolean
  filterable?: boolean
  paginated?: boolean
  pageSize?: number
  initialPageSize?: number
  pageSizeOptions?: number[]
  virtualized?: boolean
  rowHeight?: number
  loading?: boolean
  emptyMessage?: string
  onRowClick?: (row: T) => void
  selectionMode?: "none" | "single" | "multiple"
  selectedRows?: Set<string | number>
  onSelectionChange?: (selected: Set<string | number>) => void
  className?: string
  caption?: string
}

function SortIcon({ direction }: { direction: "asc" | "desc" | "none" }) {
  if (direction === "asc") return <ChevronUp className="w-4 h-4" />
  if (direction === "desc") return <ChevronDown className="w-4 h-4" />
  return <ChevronsUpDown className="w-4 h-4 text-fg-muted" />
}

function FilterHeader<T>({ column, filterValue, onFilterChange }: { column: Column<T>; filterValue: string; onFilterChange: (value: string) => void }) {
  if (!column.filterable) return null
  return (
    <div className="mt-1">
      <Input
        type="text"
        placeholder={`Filter ${column.header}...`}
        value={filterValue}
        onChange={(e) => onFilterChange(e.target.value)}
        className="text-xs h-8"
        aria-label={`Filter ${column.header}`}
      />
    </div>
  )
}

export function Table<T extends Record<string, any>>({
  columns,
  data,
  keyAccessor,
  sortable = true,
  filterable = false,
  paginated = false,
  pageSize: initialPageSize = 10,
  pageSizeOptions = [10, 25, 50, 100],
  virtualized = false,
  rowHeight = 48,
  loading = false,
  emptyMessage = "No data available",
  onRowClick,
  selectionMode = "none",
  selectedRows = new Set(),
  onSelectionChange,
  className,
  caption,
}: TableProps<T>) {
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: "asc" | "desc" } | null>(null)
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(initialPageSize)
  const [sortableColumns] = useState(columns.filter(c => c.sortable).map(c => c.key))

  const handleSort = useCallback((key: string) => {
    if (!sortable) return
    setSortConfig((current) => {
      if (current?.key === key) {
        return { key, direction: current.direction === "asc" ? "desc" : "asc" }
      }
      return { key, direction: "asc" }
    })
  }, [sortable])

  const handleFilterChange = useCallback((key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setCurrentPage(1)
  }, [])

  const filteredData = useMemo(() => {
    let result = data
    Object.entries(filters).forEach(([key, value]) => {
      if (value) {
        const column = columns.find(c => c.key === key)
        if (column?.filterable) {
          result = result.filter((row) =>
            String(column.accessor(row)).toLowerCase().includes(value.toLowerCase())
          )
        }
      }
    })
    return result
  }, [data, filters, columns])

  const sortedData = useMemo(() => {
    if (!sortConfig) return filteredData
    return [...filteredData].sort((a, b) => {
      const column = columns.find(c => c.key === sortConfig.key)
      if (!column) return 0
      const aVal = column.accessor(a)
      const bVal = column.accessor(b)
      const aStr = String(aVal).toLowerCase()
      const bStr = String(bVal).toLowerCase()
      if (aStr < bStr) return sortConfig.direction === "asc" ? -1 : 1
      if (aStr > bStr) return sortConfig.direction === "asc" ? 1 : -1
      return 0
    })
  }, [filteredData, sortConfig, columns])

  const paginatedData = useMemo(() => {
    if (!paginated) return sortedData
    const start = (currentPage - 1) * pageSize
    return sortedData.slice(start, start + pageSize)
  }, [sortedData, paginated, currentPage, pageSize])

  const totalPages = Math.ceil(sortedData.length / pageSize)

  const handleSelectionChange = (key: string | number, checked: boolean) => {
    if (!onSelectionChange) return
    const newSelected = new Set(selectedRows)
    if (checked) newSelected.add(key)
    else newSelected.delete(key)
    onSelectionChange(newSelected)
  }

  const handleSelectAll = (checked: boolean) => {
    if (!onSelectionChange) return
    const newSelected = new Set<string | number>()
    if (checked) {
      paginatedData.forEach((row) => newSelected.add(keyAccessor(row)))
    }
    onSelectionChange(newSelected)
  }

  const isAllSelected = paginatedData.length > 0 &&
    paginatedData.every((row) => selectedRows.has(keyAccessor(row)))

  const isIndeterminate = paginatedData.some((row) => selectedRows.has(keyAccessor(row))) && !isAllSelected

  if (loading) {
    return (
      <div className={cn("table-scroll", className)} role="status" aria-busy="true" aria-label="Loading table data">
        <table className="table-base">
          <thead>
            <tr>
              {selectionMode !== "none" && <th scope="col" className="w-12" />}
              {columns.map((col) => (
                <th key={col.key} scope="col" className={cn(col.headerClassName, "px-4 py-3")}>
                  <div className="skeleton h-4 w-20" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 5 }).map((_, i) => (
              <tr key={i}>
                {selectionMode !== "none" && <td className="px-4 py-3"><div className="skeleton h-5 w-5 rounded" /></td>}
                {columns.map((col) => (
                  <td key={col.key} className={cn(col.cellClassName, "px-4 py-3")}>
                    <div className="skeleton h-4 w-full" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  const containerStyle = virtualized ? { height: rowHeight * Math.min(paginatedData.length, 20), overflow: "auto" } : {}

  return (
    // A horizontally scrollable table must be reachable from the keyboard;
    // a named region is the stop a screen reader announces.
    <div
      className={cn("table-scroll", className)}
      role={caption ? "region" : undefined}
      aria-label={caption}
      tabIndex={0}
    >
      {filterable && (
        <div className="p-4 border-b border-border bg-surface-sunken">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {columns.filter(c => c.filterable).map((col) => (
              <FilterHeader
                key={col.key}
                column={col}
                filterValue={filters[col.key] || ""}
                onFilterChange={(v) => handleFilterChange(col.key, v)}
              />
            ))}
          </div>
        </div>
      )}

      <table className="table-base" role="table" aria-label={caption}>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {selectionMode !== "none" && (
              <th scope="col" className="w-12 px-4 py-3">
                <Checkbox
                  checked={isAllSelected}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  aria-label="Select all rows"
                  data-indeterminate={isIndeterminate}
                />
              </th>
            )}
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={cn(
                  "px-4 py-3 text-left font-semibold text-fg text-xs uppercase tracking-wide whitespace-nowrap",
                  "border-b border-border bg-surface-sunken",
                  sortable && col.sortable && "cursor-pointer hover:bg-surface-hover select-none",
                  col.headerClassName
                )}
                onClick={() => col.sortable && handleSort(col.key)}
                aria-sort={sortConfig?.key === col.key ? (sortConfig.direction === "asc" ? "ascending" : "descending") : "none"}
              >
                <div className="flex items-center gap-1">
                  <span>{col.header}</span>
                  {sortable && col.sortable && <SortIcon direction={sortConfig?.key === col.key ? sortConfig.direction : "none"} />}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody style={containerStyle as React.CSSProperties}>
          {paginatedData.length === 0 ? (
            <tr>
              <td colSpan={columns.length + (selectionMode !== "none" ? 1 : 0)} className="px-4 py-8 text-center text-fg-muted">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            paginatedData.map((row) => {
              const rowKey = keyAccessor(row)
              const isSelected = selectedRows.has(rowKey)
              return (
                <tr
                  key={rowKey}
                  className={cn(
                    "transition-colors",
                    onRowClick && "cursor-pointer",
                    isSelected && "bg-brand-50 dark:bg-brand-900/30"
                  )}
                  onClick={() => onRowClick?.(row)}
                  onDoubleClick={() => onRowClick?.(row)}
                  role={onRowClick ? "button" : "row"}
                  tabIndex={onRowClick ? 0 : undefined}
                  onKeyDown={onRowClick ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onRowClick(row); } } : undefined}
                  aria-selected={selectionMode !== "none" ? isSelected : undefined}
                >
                  {selectionMode !== "none" && (
                    <td className="px-4 py-3">
                      <Checkbox
                        checked={isSelected}
                        onChange={(e) => handleSelectionChange(rowKey, e.target.checked)}
                        aria-label={`Select row ${rowKey}`}
                      />
                    </td>
                  )}
                  {columns.map((col) => (
                    <td key={col.key} className={cn("px-4 py-3 text-fg align-top border-b border-border-subtle", col.cellClassName)}>
                      {col.accessor(row)}
                    </td>
                  ))}
                </tr>
              )
            })
          )}
        </tbody>
      </table>

      {paginated && totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-border bg-surface-sunken">
          <div className="text-sm text-fg-muted">
            Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, sortedData.length)} of {sortedData.length} results
          </div>
          <div className="flex items-center gap-2">
            <select
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
              className="input w-auto h-9 text-sm py-1"
              aria-label="Rows per page"
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>{size} per page</option>
              ))}
            </select>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCurrentPage(1)}
              disabled={currentPage === 1}
              aria-label="First page"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 17l-5-5 5-5M18 17l-5-5 5-5" /></svg>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              aria-label="Previous page"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6" /></svg>
            </Button>
            <span className="text-sm text-fg px-2" aria-live="polite">Page {currentPage} of {totalPages}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              aria-label="Next page"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18l6-6-6-6" /></svg>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage === totalPages}
              aria-label="Last page"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M13 17l5-5-5-5M6 17l5-5-5-5" /></svg>
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
