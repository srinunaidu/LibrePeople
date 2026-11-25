import { cn } from "@/lib/utils"
import { Link, useLocation, useResolvedPath } from "react-router-dom"
import { ChevronRight } from "lucide-react"
import * as React from "react"

interface BreadcrumbItem {
  label: string
  href?: string
  onClick?: () => void
}

interface BreadcrumbProps {
  items: BreadcrumbItem[]
  className?: string
  separator?: React.ReactNode
}

export function Breadcrumb({ items, className, separator = <ChevronRight className="w-4 h-4 text-fg-muted" /> }: BreadcrumbProps) {
  const location = useLocation()

  return (
    <nav aria-label="Breadcrumb" className={cn("flex items-center gap-1.5 text-sm", className)}>
      <ol className="flex items-center gap-1.5" role="list">
        {items.map((item, index) => {
          const isLast = index === items.length - 1
          const isActive = isLast || item.href === location.pathname
          const resolvedPath = item.href ? useResolvedPath(item.href) : null
          const isCurrentPath = resolvedPath ? location.pathname.startsWith(resolvedPath.pathname) : false

          return (
            <li key={item.label} className="flex items-center gap-1.5">
              {index > 0 && <span aria-hidden="true">{separator}</span>}
              {item.href && !isLast ? (
                <Link
                  to={item.href}
                  className={cn(
                    "flex items-center gap-1 text-fg-muted hover:text-fg transition-colors",
                    isCurrentPath && "text-fg font-medium"
                  )}
                  aria-current={isCurrentPath ? "page" : undefined}
                >
                  {item.label}
                </Link>
              ) : item.onClick ? (
                <button
                  type="button"
                  onClick={item.onClick}
                  className={cn(
                    "flex items-center gap-1 text-fg-muted hover:text-fg transition-colors bg-none border-0 p-0",
                    isActive && "text-fg font-medium"
                  )}
                  aria-current={isActive ? "page" : undefined}
                >
                  {item.label}
                </button>
              ) : (
                <span
                  className={cn(
                    "flex items-center gap-1 text-fg font-medium",
                    isActive && "text-fg"
                  )}
                  aria-current={isActive ? "page" : undefined}
                >
                  {item.label}
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

interface BreadcrumbItemProps {
  label: string
  href?: string
  onClick?: () => void
  children?: React.ReactNode
}

export function BreadcrumbItem({ label, href, onClick, children }: BreadcrumbItemProps) {
  return (
    <li className="flex items-center gap-1.5">
      {href ? (
        <Link to={href} className="text-fg-muted hover:text-fg transition-colors">
          {label}
        </Link>
      ) : onClick ? (
        <button type="button" onClick={onClick} className="text-fg-muted hover:text-fg transition-colors bg-none border-0 p-0">
          {label}
        </button>
      ) : (
        <span className="text-fg font-medium">{label}</span>
      )}
      {children}
    </li>
  )
}
