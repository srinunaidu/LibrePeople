import { cn } from "@/lib/utils"
import * as React from "react"

export interface PageHeaderProps {
  title: string
  description?: string
  icon?: React.ReactNode
  actions?: React.ReactNode
  className?: string
  compact?: boolean
}

export function PageHeader({
  title,
  description,
  icon,
  actions,
  className,
  compact = false,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        `flex flex-col sm:flex-row sm:items-start sm:justify-between ${compact ? "gap-2 mb-3" : "gap-4 mb-6"} mk-reveal`,
        className
      )}
    >
      <div className={`flex items-start ${compact ? "gap-2" : "gap-3"} min-w-0`}>
        {icon && <span className="page-icon">{icon}</span>}
        <div className="min-w-0">
          <h1 className={`page-title text-fg ${compact ? "text-lg" : "mk-h1"}`}>{title}</h1>
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

export function Toolbar({
  children,
  className,
  label,
}: {
  children: React.ReactNode
  className?: string
  label?: string
}) {
  return (
    <div className={cn("toolbar", className)} role="group" aria-label={label}>
      {children}
    </div>
  )
}

export function Breadcrumb({
  items,
  className,
}: {
  items: { label: string; href?: string }[]
  className?: string
}) {
  return (
    <nav aria-label="Breadcrumb" className={className}>
      <ol className="flex items-center gap-1.5 text-sm text-fg-muted flex-wrap">
        {items.map((item, i) => (
          <li key={i} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-fg-subtle" aria-hidden="true">/</span>}
            {item.href ? (
              <a href={item.href} className="hover:text-fg hover:underline">
                {item.label}
              </a>
            ) : (
              <span className="text-fg font-medium" aria-current="page">
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}

export function Field({
  label,
  htmlFor,
  hint,
  required,
  error,
  children,
  className,
}: {
  label: string
  htmlFor?: string
  hint?: string
  required?: boolean
  error?: string | boolean
  children: React.ReactNode
  className?: string
}) {
  const errorId = React.useId()
  const hasError = !!error
  const errorText = typeof error === "string" ? error : undefined
  return (
    <div className={cn("field", className)}>
      <label htmlFor={htmlFor} className="field-label">
        {label}
        {required && (
          <span className="text-error ml-0.5">
            (required)
          </span>
        )}
      </label>
      {React.isValidElement(children)
        ? React.cloneElement(children, {
            ...(hasError ? { "aria-describedby": errorId, "aria-invalid": true } : {}),
            ...(required ? { "aria-required": true } : {}),
          })
        : children}
      {hasError ? (
        <p id={errorId} className="field-hint text-error error-box" role="alert">
          {errorText ?? "Invalid field."}
        </p>
      ) : hint ? (
        <p className="field-hint">{hint}</p>
      ) : null}
    </div>
  )
}

export function FormSection({
  title,
  description,
  children,
  columns = 2,
  className,
}: {
  title?: string
  description?: string
  children: React.ReactNode
  columns?: 1 | 2 | 3 | 4
  className?: string
}) {
  const cols = {
    1: "grid-cols-1",
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  }

  return (
    <div className={className}>
      {(title || description) && (
        <div className="mb-4">
          {title && <h2 className="text-base font-semibold text-fg">{title}</h2>}
          {description && <p className="text-sm text-fg-muted mt-0.5">{description}</p>}
        </div>
      )}
      <div className={cn("gap-4", cols[columns])}>{children}</div>
    </div>
  )
}

export function SubmitBar({
  onCancel,
  submitLabel = "Save",
  cancelLabel = "Cancel",
  loading,
  dirty,
  className,
}: {
  onCancel?: () => void
  submitLabel?: string
  cancelLabel?: string
  loading?: boolean
  dirty?: boolean
  className?: string
}) {
  return (
    <div
      className={cn(
        "sticky bottom-0 z-10 flex items-center justify-end gap-3 -mx-5 -mb-5 px-5 py-4 border-t border-border bg-surface backdrop-blur",
        className
      )}
    >
      {dirty && <span className="text-xs text-fg-muted mr-auto">Unsaved changes</span>}
      {onCancel && (
        <button type="button" onClick={onCancel} className="btn btn-secondary btn-sm" disabled={loading}>
          {cancelLabel}
        </button>
      )}
      <button type="submit" className="btn btn-primary btn-sm" disabled={loading}>
        {loading ? "Saving…" : submitLabel}
      </button>
    </div>
  )
}
