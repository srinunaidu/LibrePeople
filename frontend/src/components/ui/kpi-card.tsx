import { cn } from "@/lib/utils"
import { Sparkline, TrendIndicator } from "./sparkline"

interface KPICardProps {
  label: string
  value: string | number
  icon?: React.ReactNode
  tone?: "brand" | "teal" | "green" | "violet" | "amber" | "rose" | "slate"
  sparklineData?: number[]
  trendValue?: number
  trendLabel?: string
  hint?: string
  loading?: boolean
  error?: boolean
  className?: string
  onClick?: () => void
}

const toneClasses = {
  brand: "stat-rail-brand icon-tile-brand",
  teal: "stat-rail-teal icon-tile-teal",
  green: "stat-rail-green icon-tile-green",
  violet: "stat-rail-violet icon-tile-violet",
  amber: "stat-rail-amber icon-tile-amber",
  rose: "stat-rail-rose icon-tile-rose",
  slate: "stat-rail-slate icon-tile-slate",
}

export function KPICard({
  label,
  value,
  icon,
  tone = "brand",
  sparklineData,
  trendValue,
  trendLabel,
  hint,
  loading,
  error,
  className,
  onClick,
}: KPICardProps) {
  const [railClass, iconClass] = toneClasses[tone].split(" ")

  const baseClasses = cn(
    "mk-card p-5 relative overflow-hidden mk-reveal",
    onClick && "cursor-pointer",
    className
  )

  if (loading) {
    return (
      <div className={baseClasses}>
        <span className={`stat-rail ${railClass}`} aria-hidden="true" />
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="mk-kicker text-fg-muted">{label}</p>
            <div className="skeleton h-8 w-20 mb-2" />
            {hint && <div className="skeleton h-3 w-32" />}
          </div>
          {icon && <span className={`icon-tile ${iconClass}`} aria-hidden="true">{icon}</span>}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={baseClasses}>
        <span className={`stat-rail ${railClass}`} aria-hidden="true" />
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="mk-kicker text-fg-muted">{label}</p>
            <p className="text-error font-bold">Failed to load</p>
            {hint && <p className="text-sm text-fg-muted mt-1">{hint}</p>}
          </div>
          {icon && <span className={`icon-tile ${iconClass}`} aria-hidden="true">{icon}</span>}
        </div>
      </div>
    )
  }

  return (
    <div
      className={baseClasses}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(); } } : undefined}
    >
      <span className={`stat-rail ${railClass}`} aria-hidden="true" />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="mk-kicker text-fg-muted">{label}</p>
          <p className="stat-value">{value}</p>
          {(sparklineData || trendValue !== undefined) && (
            <div className="mt-2 flex items-end gap-2">
              {sparklineData && <Sparkline data={sparklineData} color={tone as any} width={80} height={28} />}
              {trendValue !== undefined && <TrendIndicator value={trendValue} label={trendLabel} />}
            </div>
          )}
          {hint && !sparklineData && !trendValue && (
            <p className="text-sm text-fg-muted mt-1">{hint}</p>
          )}
        </div>
        {icon && <span className={`icon-tile ${iconClass}`} aria-hidden="true">{icon}</span>}
      </div>
    </div>
  )
}
