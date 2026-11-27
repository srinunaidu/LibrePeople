import { Table, type Column } from "@/components/ui/table"
import { Card, SectionCard, Skeleton } from "@/components/ui"
import { Badge } from "@/components/ui/badge"
import { EmptyState, Alert } from "@/components/ui/feedback"
import { cn } from "@/lib/utils"

interface Row {
  id: number
  [k: string]: any
}

interface DataListProps {
  title: string
  description?: string
  caption: string
  columns: string[]
  rows: Row[]
  render: (row: Row) => (string | number | null | undefined)[]
  source?: string
  unreadable?: string[]
}

export function DataList({ title, description, caption, columns, rows, render, source, unreadable = [] }: DataListProps) {
  const failed = !!source && unreadable.includes(source)

  const tableColumns: Column<Row>[] = columns.map((col, index) => ({
    key: col.toLowerCase().replace(/\s+/g, "-"),
    header: col,
    accessor: (row) => {
      const cell = render(row)[index]
      return cell === null || cell === undefined || cell === "" ? "—" : cell
    },
  }))

  if (failed) {
    return (
      <SectionCard title={title} description={description} className="mb-4">
        <Alert tone="error" role="alert" className="mb-0">
          This list could not be read. It may be temporarily unavailable, or not visible for your role — it is not an empty result.
        </Alert>
      </SectionCard>
    )
  }

  if (rows.length === 0) {
    return (
      <SectionCard title={title} description={description} className="mb-4">
        <EmptyState title={`No ${title.toLowerCase()} recorded yet.`} />
      </SectionCard>
    )
  }

  return (
    <SectionCard title={title} description={description} className="mb-4">
      <Table
        columns={tableColumns}
        data={rows}
        keyAccessor={(row) => row.id}
        caption={caption}
        sortable={false}
        filterable={false}
        emptyMessage={`No ${title.toLowerCase()} recorded yet.`}
      />
    </SectionCard>
  )
}