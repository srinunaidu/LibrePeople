import { cva, type VariantProps } from "class-variance-authority"
import * as React from "react"
import { cn } from "@/lib/utils"

const TONE_CLASSES: Record<StatusTone, string> = {
  brand: "mk-chip",
  teal: "mk-chip",
  green: "mk-chip",
  violet: "mk-chip",
  amber: "mk-chip",
  rose: "mk-chip",
  slate: "mk-chip",
}

const TONE_DOT_COLORS: Record<StatusTone, string> = {
  brand: "bg-brand-500",
  teal: "bg-[var(--teal-500)]",
  green: "bg-[var(--semantic-status-success)]",
  violet: "bg-[var(--violet-500)]",
  amber: "bg-[var(--semantic-status-warning)]",
  rose: "bg-[var(--semantic-status-error)]",
  slate: "bg-[var(--fg-subtle)]",
}

export const statusVariants = cva(
  "inline-flex items-center rounded-full font-medium whitespace-nowrap"
)

export type StatusTone = "brand" | "teal" | "green" | "violet" | "amber" | "rose" | "slate"

const STATUS_TONES: Record<string, StatusTone> = {
  // lifecycle
  Active: "green", Completed: "green", Approved: "green", Accepted: "green",
  Hired: "green", Done: "green", Open: "green", Sent: "green",
  Submitted: "brand", Pending: "amber", InProgress: "brand", InProgress_: "brand",
  Processing: "brand", Finalized: "teal", Paid: "green",
  OnHold: "amber", Draft: "slate",
  Rejected: "rose", Cancelled: "rose", Terminated: "rose", Failed: "rose",
  Closed: "slate", Suspended: "rose",
  // integration health
  healthy: "green", pending: "amber", error: "rose",
}

export interface StatusPillProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, "children"> {
  status: string | null | undefined
  tone?: StatusTone
  dot?: boolean
}

export function StatusPill({ status, tone, dot = false, className, ...props }: StatusPillProps) {
  if (!status) return <span className="text-fg-muted">—</span>

  const resolvedTone: StatusTone = tone ?? (STATUS_TONES[status] as StatusTone) ?? "slate"

  return (
    <span className={cn("mk-chip gap-1.5", className)} {...props}>
      {dot && (
        <span
          className={cn(
            "mk-chip-dot",
            TONE_DOT_COLORS[resolvedTone]
          )}
          aria-hidden="true"
        />
      )}
      {status}
    </span>
  )
}
