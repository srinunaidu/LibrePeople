import { cn } from "@/lib/utils"
import * as React from "react"
import { errorMessage, isRetryable, requestId } from "@/lib/api"
import { Button } from "@/components/ui/button"

export interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("mk-card p-8 text-center mk-reveal", className)}>
      {icon && <span className="icon-tile icon-tile-slate mx-auto mb-4">{icon}</span>}
      <p className="mk-h2 text-fg mb-2">{title}</p>
      {description && <p className="max-w-sm mx-auto text-fg-muted">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}

export interface AlertProps {
  tone?: "info" | "success" | "error" | "warning"
  title?: string
  children?: React.ReactNode
  action?: React.ReactNode
  className?: string
  role?: "alert" | "status"
}

const alertToneClasses: Record<NonNullable<AlertProps["tone"]>, string> = {
  info: "border-[var(--info-border)] bg-[var(--info-light)]",
  success: "border-[var(--success-border)] bg-[var(--success-light)]",
  error: "border-[var(--error-border)] bg-[var(--error-light)]",
  warning: "border-[var(--warning-border)] bg-[var(--warning-light)]",
}

export function Alert({ tone = "info", title, children, action, className, role }: AlertProps) {
  const icons: Record<NonNullable<AlertProps["tone"]>, React.ReactNode> = {
    info: (
      <svg className="w-4 h-4 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 8h.01M12 11v5" />
      </svg>
    ),
    success: (
      <svg className="w-4 h-4 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M9 12l2 2 4-4" />
        <circle cx="12" cy="12" r="9" />
      </svg>
    ),
    error: (
      <svg className="w-4 h-4 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M12 8v4m0 4h.01" />
        <circle cx="12" cy="12" r="9" />
      </svg>
    ),
    warning: (
      <svg className="w-4 h-4 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <path d="M12 9v4m0 4h.01" />
      </svg>
    ),
  }

  return (
    <div
      role={role ?? (tone === "error" ? "alert" : "status")}
      className={cn("mk-card p-4 mk-reveal", alertToneClasses[tone], className)}
    >
      <div className="flex items-start gap-3">
        {icons[tone]}
        <div className="flex-1 min-w-0">
          {title && <p className="font-semibold text-fg">{title}</p>}
          {children && <div className={title ? "mt-1" : ""}><p className="text-sm text-fg-muted">{children}</p></div>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  )
}

export interface MeterProps {
  percent: number
  label?: string
  tone?: "brand" | "green" | "amber" | "rose"
  className?: string
}

export function Meter({ percent, label, tone = "brand", className }: MeterProps) {
  const clamped = Math.max(0, Math.min(100, percent || 0))
  const tones = {
    brand: "bg-brand-600",
    green: "bg-[var(--semantic-status-success)]",
    amber: "bg-[var(--semantic-status-warning)]",
    rose: "bg-[var(--semantic-status-error)]"
  }

  return (
    <div className={cn("mk-card p-4 mk-reveal", className)}>
      <div
        className="h-2 w-full rounded-full bg-surface-inset overflow-hidden"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? "Progress"}
      >
        <div
          className={cn("h-full rounded-full transition-[width] duration-300", tones[tone])}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {label && <p className="text-sm text-fg-muted mt-2">{label}</p>}
    </div>
  )
}

export interface RetryableAlertProps {
  err: unknown
  title?: string
  fallback?: string
  onRetry?: () => void
  className?: string
}

/**
 * Global error Alert: Alert tone=error with Retry CTA iff isRetryable(err),
 * requestId span, and network branch (!response → check connection).
 */
export function RetryableAlert({ err, title, fallback, onRetry, className }: RetryableAlertProps) {
  const e = err as { response?: unknown }
  const isNetwork = !e?.response
  const message = isNetwork
    ? "We can't reach the server right now. Check your connection and try again."
    : errorMessage(err, fallback ?? "Something went wrong")
  const showRetry = !!onRetry && isRetryable(err)
  const rid = requestId(err)
  return (
    <Alert
      tone="error"
      title={title ?? fallback ?? "Something went wrong"}
      className={className}
      role="alert"
      action={
        showRetry ? (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            Retry
          </Button>
        ) : undefined
      }
    >
      <span aria-live="polite">{message}</span>
      {rid && (
        <span data-testid="request-id" className="block mt-2 text-xs font-mono text-fg-muted">
          Request ID: {rid}
        </span>
      )}
    </Alert>
  )
}
