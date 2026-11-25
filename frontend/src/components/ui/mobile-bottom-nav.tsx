import { cn } from "@/lib/utils"
import { Link, useLocation } from "react-router-dom"
import * as React from "react"

interface BottomNavItem {
  label: string
  icon: React.ReactNode
  href: string
  badge?: number
}

interface MobileBottomNavProps {
  items: BottomNavItem[]
  className?: string
}

export function MobileBottomNav({ items, className }: MobileBottomNavProps) {
  const location = useLocation()

  return (
    <nav
      className={cn(
        "fixed bottom-0 left-0 right-0 z-[1100] lg:hidden",
        "bg-surface border-t border-border shadow-xl",
        "safe-area-inset-bottom",
        className
      )}
      aria-label="Primary navigation"
    >
      {/* One row per item. The grid was hard-coded to three columns, so the
          five items wrapped onto a second row and the bar grew to 137px —
          taller than the space `main` reserves for it. */}
      <div
        className="grid max-w-[480px] mx-auto"
        style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
      >
        {items.map((item) => {
          const isActive = location.pathname.startsWith(item.href)
          return (
            <Link
              key={item.label}
              to={item.href}
              className={cn(
                "relative flex flex-col items-center justify-center gap-1 p-3",
                "text-fg-muted transition-colors",
                isActive && "text-brand-600"
              )}
              aria-current={isActive ? "page" : undefined}
              aria-label={item.label}
            >
              <span className="flex items-center justify-center" aria-hidden="true">
                {item.icon}
              </span>
              <span className={cn("text-xs font-medium", isActive && "text-brand-600")}>
                {item.label}
              </span>
              {item.badge != null && item.badge > 0 && (
                <span className="absolute -top-1 -right-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-error px-1.5 text-[10px] font-semibold text-white">
                  {item.badge > 99 ? "99+" : item.badge}
                </span>
              )}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
