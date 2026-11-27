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

/* ------------------------------------------------------------------ *
 * Card / SectionCard / StatCard / StatusPill / Skeleton live in
 * ui/card.tsx, ui/kpi-card.tsx, ui/status-pill.tsx and ui/skeleton.tsx.
 * This barrel re-exports the canonical definitions (D-b: no shims).
 * ------------------------------------------------------------------ */

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
 * StatusPill / Skeleton families live in ui/status-pill.tsx and
 * ui/skeleton.tsx (re-exported below). No local duplicates (D-b).
 * ------------------------------------------------------------------ */

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

// Re-export canonical components (D-b: barrel re-exports, not shims)
export { Card, SectionCard } from "./ui/card"
export { StatusPill, type StatusTone } from "./ui/status-pill"
export { Skeleton, CardSkeleton, TableSkeleton, LoadingRegion } from "./ui/skeleton"
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
