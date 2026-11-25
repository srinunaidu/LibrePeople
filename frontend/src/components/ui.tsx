import type { ReactNode } from "react"
import { cn } from "@/lib/utils"
import { IconAlert, IconCheck, IconInfo } from "./icons"
import { KPICard } from "./ui/kpi-card"
import { Sparkline, TrendIndicator } from "./ui/sparkline"
import { Table } from "./ui/table"
import { ShiftTemplateTable } from "./ui/shift-template-table"
import { ShiftSwapTable } from "./ui/shift-swap-table"
import { Modal, Drawer, ModalHeader, ModalTitle, ModalDescription, ModalFooter, ModalTrigger, ModalClose, ModalContent } from "./ui/modal"
import { Toaster, showToast, showSuccess, showError, showWarning, showInfo } from "./ui/toast"
import { Popover, PopoverTrigger, PopoverContent } from "./ui/popover"
import { Breadcrumb } from "./ui/breadcrumb"
import { MobileBottomNav } from "./ui/mobile-bottom-nav"
import { Button } from "./ui/button"
import { Input, Textarea, Select, Checkbox, Switch } from "./ui/inputs"
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuGroup, DropdownMenuSeparator } from "./ui/dropdown-menu"
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "./ui/tooltip"
export { RetryableAlert } from "@/components/ui/feedback"
export { PendingVerificationAlert } from "@/components/ui/PendingVerificationAlert"

export type Tone = "brand" | "teal" | "green" | "violet" | "amber" | "rose" | "slate"

/* ------------------------------------------------------------------ *
 * Card — 360 design: mk-card gradient-border glass card
 * ------------------------------------------------------------------ */

export function Card({
  children,
  className = "",
  padded = true,
  hover = false,
}: {
  children: ReactNode
  className?: string
  padded?: boolean
  hover?: boolean
}) {
  return (
    <div
      className={[
        "mk-card",
        padded ? "p-5" : "",
        hover && "mk-reveal",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </div>
  )
}

/** Card with an icon tile, title and optional supporting text. */
export function SectionCard({
  icon,
  title,
  description,
  actions,
  children,
  className = "",
  compact = false,
}: {
  icon?: ReactNode
  title: string
  description?: string
  actions?: ReactNode
  children?: ReactNode
  className?: string
  compact?: boolean
}) {
  return (
    <section className={`mk-card overflow-hidden ${className}`}>
      <header
        className={`flex items-start ${compact ? "gap-2" : "gap-3"} ${compact ? "px-4 py-2.5" : "px-5 py-4"} border-b border-border-subtle`}
      >
        {icon && <span className="icon-tile">{icon}</span>}
        <div className="min-w-0 flex-1">
          <h2 className={`text-fg leading-tight ${compact ? "text-base" : "mk-h2"}`}>{title}</h2>
          {description && (
            <p className="text-sm text-fg-muted mt-1">{description}</p>
          )}
        </div>
        {actions && <div className="shrink-0 flex items-center gap-2">{actions}</div>}
      </header>
      <div className={compact ? "p-3" : "p-5"}>{children}</div>
    </section>
  )
}

/* ------------------------------------------------------------------ *
 * Stat / metric card — 360 design: mk-card with stat-rail accent
 * ------------------------------------------------------------------ */

export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = "brand",
}: {
  label: string
  value: ReactNode
  hint?: string
  icon?: ReactNode
  tone?: Tone
}) {
  return (
    <div className="mk-card p-5 relative overflow-hidden mk-reveal">
      <span className={`stat-rail stat-rail-${tone}`} aria-hidden="true" />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="mk-kicker text-fg-muted">{label}</p>
          <p className="stat-value">{value}</p>
          {hint && <p className="text-sm text-fg-muted mt-1">{hint}</p>}
        </div>
        {icon && <span className={`icon-tile icon-tile-${tone}`}>{icon}</span>}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ *
 * Alerts — 360 design: mk-card with tone accents
 * ------------------------------------------------------------------ */

const alertToneClasses: Record<string, string> = {
  info: "border-brand-600/30 bg-brand-50/10",
  success: "border-[var(--success-border)]/30 bg-[var(--success-light)]/10",
  error: "border-[var(--error-border)]/30 bg-[var(--error-light)]/10",
  warning: "border-[var(--warning-border)]/30 bg-[var(--warning-light)]/10",
}

export function Alert({
  tone = "info",
  title,
  children,
  action,
  className,
}: {
  tone?: "info" | "success" | "error" | "warning"
  title?: string
  children?: ReactNode
  action?: ReactNode
  className?: string
}) {
  const Icon = tone === "success" ? IconCheck : tone === "error" ? IconAlert : tone === "warning" ? IconAlert : IconInfo
  return (
    <div className={`mk-card p-4 ${alertToneClasses[tone]} mk-reveal ${className ?? ""}`} role={tone === "error" ? "alert" : "status"}>
      <div className="flex items-start gap-3">
        <Icon className="w-5 h-5 mt-0.5 shrink-0 text-fg" />
        <div className="flex-1 min-w-0">
          {title && <p className="font-semibold text-fg">{title}</p>}
          {children && <div className={title ? "mt-1" : ""}><p className="text-sm text-fg-muted">{children}</p></div>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ *
 * Empty state — 360 design: mk-card centered
 * Illustration + primary CTA + learn more pattern for list pages.
 * ------------------------------------------------------------------ */

export function EmptyState({
  title,
  description,
  icon,
  illustration,
  action,
  primaryAction,
  learnMore,
  className,
}: {
  title: string
  description?: string
  icon?: ReactNode
  illustration?: ReactNode
  action?: ReactNode
  /** Primary CTA button, rendered above the secondary action. */
  primaryAction?: ReactNode
  /** "Learn more" link text, rendered below the description. */
  learnMore?: string
  className?: string
}) {
  return (
    <div className={cn("mk-card p-8 text-center mk-reveal", className)}>
      {illustration && <div className="mx-auto mb-4">{illustration}</div>}
      {icon && !illustration && <span className="icon-tile icon-tile-slate mx-auto mb-4">{icon}</span>}
      <p className="mk-h2 text-fg mb-2">{title}</p>
      {description && <p className="max-w-sm mx-auto text-fg-muted">{description}</p>}
      {primaryAction && <div className="mt-4">{primaryAction}</div>}
      {action && <div className="mt-6">{action}</div>}
      {learnMore && (
        <p className="mt-6 text-sm text-fg-muted">
          <a href="#" className="text-brand-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded">
            {learnMore}
          </a>
        </p>
      )}
    </div>
  )
}



/* ------------------------------------------------------------------ *
 * Page header — 360 design: mk-h1 + mk-h2
 * ------------------------------------------------------------------ */

export function PageHeader({
  title,
  description,
  icon,
  actions,
  compact = false,
}: {
  title: string
  description?: string
  icon?: ReactNode
  actions?: ReactNode
  compact?: boolean
}) {
  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-start sm:justify-between ${compact ? "gap-2 mb-0" : "gap-4 mb-0"} mk-reveal`}
    >
      <div className={`flex items-start ${compact ? "gap-2" : "gap-3"} min-w-0`}>
        {icon && <span className="page-icon">{icon}</span>}
        <div className="min-w-0">
          <h1 className={`text-fg ${compact ? "text-lg" : "mk-h1"}`}>{title}</h1>
          {description && (
            <p className={`text-fg-muted max-w-2xl ${compact ? "text-sm mt-1" : "mk-h2 mt-2"}`}>
              {description}
            </p>
          )}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  )
}

/* ------------------------------------------------------------------ *
 * Status pill
 * ------------------------------------------------------------------ */

const STATUS_TONE: Record<string, Tone> = {
  // lifecycle
  Active: "green", Completed: "green", Approved: "green", Accepted: "green",
  Hired: "green", Done: "green", Open: "green", Sent: "green", Draft: "slate",
  Submitted: "brand", Pending: "amber", InProgress: "brand", OnHold: "amber",
  Rejected: "rose", Cancelled: "rose", Terminated: "rose", Failed: "rose",
  Closed: "slate", Suspended: "rose", Completed_: "slate",
  // shift template day/night status
  Night: "violet", Day: "slate",
  // integration health
  healthy: "green", pending: "amber", error: "rose",
}

/**
 * Maps a domain status string onto a colour. Falls back to a neutral tone for
 * values it does not recognise rather than guessing — status is always paired
 * with its text label, so colour is never the only signal.
 */
export function StatusPill({ status, dot }: { status?: string | null; dot?: boolean }) {
  if (!status) return <span className="text-text-secondary">—</span>
  const tone = STATUS_TONE[status] ?? "slate"
  return <span className={`badge badge-${tone} ${dot ? "gap-1.5" : ""}`}>{dot && <span className="h-1.5 w-1.5 rounded-full" aria-hidden="true" />}{status}</span>
}

/* ------------------------------------------------------------------ *
 * Meter
 * ------------------------------------------------------------------ */

export function Meter({
  percent,
  label,
}: {
  percent: number
  label?: string
}) {
  const clamped = Math.max(0, Math.min(100, percent || 0))
  return (
    <div>
      <div
        className="meter"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? "Progress"}
      >
        <span style={{ width: `${clamped}%` }} />
      </div>
      {label && <p className="text-xs text-text-secondary mt-1.5">{label}</p>}
    </div>
  )
}

/* ------------------------------------------------------------------ *
 * Skeletons — 360 design: mk-card containers
 * ------------------------------------------------------------------ */

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />
}

export function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="mk-card p-5" aria-hidden="true">
      <Skeleton className="h-3 w-24 mb-4" />
      <Skeleton className="h-8 w-16 mb-3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className="h-3 w-full mb-2 last:mb-0" />
      ))}
    </div>
  )
}

export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="mk-card p-5" aria-hidden="true">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 mb-3 last:mb-0">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-3 flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

export function LoadingRegion({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div aria-busy="true" aria-live="polite">
      <span className="sr-only">{label}</span>
      {children}
    </div>
  )
}

// Re-export new components
export {
  KPICard,
  Sparkline,
  TrendIndicator,
  Table,
  Modal,
  Drawer,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
  ModalTrigger,
  ModalClose,
  ModalContent,
  Toaster,
  showToast,
  showSuccess,
  showError,
  showWarning,
  showInfo,
  Popover,
  PopoverTrigger,
  PopoverContent,
  ShiftTemplateTable,
  ShiftSwapTable,
  Breadcrumb,
  MobileBottomNav,
  Button,
  Input,
  Textarea,
  Select,
  Checkbox,
  Switch,
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuGroup,
  DropdownMenuSeparator,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
}
