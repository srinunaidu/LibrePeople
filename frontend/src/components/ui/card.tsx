import { cn } from "@/lib/utils"
import * as React from "react"

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  padded?: boolean
  hover?: boolean
  raised?: boolean
}

export function Card({ className, padded = true, hover = false, raised = false, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "mk-card card",
        padded && "p-5",
        hover && "mk-reveal",
        raised && "shadow-lg",
        className
      )}
      {...props}
    />
  )
}

export function SectionCard({
  icon,
  title,
  description,
  actions,
  children,
  className,
  compact = false,
}: {
  icon?: React.ReactNode
  title: string
  description?: string
  actions?: React.ReactNode
  children?: React.ReactNode
  className?: string
  compact?: boolean
}) {
  return (
    <section className={cn("mk-card card overflow-hidden", className)}>
      <header
        className={`flex items-start ${compact ? "gap-2" : "gap-3"} ${compact ? "px-4 py-2.5" : "px-5 py-4"} border-b border-border-subtle`}
      >
        {icon && <span className="icon-tile">{icon}</span>}
        <div className="min-w-0 flex-1">
          <h2 className={`text-fg leading-tight ${compact ? "text-base" : "mk-h2"}`}>{title}</h2>
          {description && <p className="text-sm text-fg-muted mt-1">{description}</p>}
        </div>
        {actions && <div className="shrink-0 flex items-center gap-2">{actions}</div>}
      </header>
      <div className={compact ? "p-3" : "p-5"}>{children}</div>
    </section>
  )
}
