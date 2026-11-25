import { cn } from "@/lib/utils"

interface SparklineProps {
  data: number[]
  className?: string
  color?: "brand" | "success" | "warning" | "error" | "neutral"
  showTrend?: boolean
  trendValue?: number
  width?: number
  height?: number
}

const colorMap = {
  brand: "var(--brand-600)",
  success: "var(--success)",
  warning: "var(--warning)",
  error: "var(--error)",
  neutral: "var(--fg-muted)",
}

export function Sparkline({
  data,
  className,
  color = "brand",
  showTrend = false,
  trendValue,
  width = 120,
  height = 40,
}: SparklineProps) {
  if (!data.length) return null

  const strokeColor = colorMap[color]
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1

  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * width
    const y = height - ((value - min) / range) * height
    return `${x},${y}`
  }).join(" ")

  const trendColor = trendValue !== undefined
    ? trendValue >= 0
      ? "var(--success)"
      : "var(--error)"
    : "var(--fg-muted)"

  return (
    <div className={cn("flex items-end gap-2", className)}>
      <svg width={width} height={height} aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="sparkline-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path
          d={`M${points}`}
          stroke={strokeColor}
          strokeWidth="2"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d={`M${points} L${width},${height} L0,${height} Z`}
          fill="url(#sparkline-gradient)"
        />
      </svg>
      {showTrend && trendValue !== undefined && (
        <span
          className={cn(
            "text-xs font-semibold whitespace-nowrap",
            trendValue >= 0 ? "text-success-text" : "text-error"
          )}
          aria-label={`Trend: ${trendValue >= 0 ? "up" : "down"} ${Math.abs(trendValue)}%`}
        >
          {trendValue >= 0 ? "↑" : "↓"} {Math.abs(trendValue)}%
        </span>
      )}
    </div>
  )
}

interface TrendIndicatorProps {
  value: number
  label?: string
  className?: string
}

export function TrendIndicator({ value, label, className }: TrendIndicatorProps) {
  const isPositive = value >= 0
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs font-semibold",
        isPositive ? "text-success-text" : "text-error",
        className
      )}
      aria-label={`${label || "Trend"}: ${isPositive ? "up" : "down"} ${Math.abs(value)}%`}
    >
      {isPositive ? (
        <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden="true">
          <path d="M5 12l5 5 10-10" />
        </svg>
      ) : (
        <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden="true">
          <path d="M19 12l-5 5-10-10" />
        </svg>
      )}
      {Math.abs(value)}%
      {label && <span className="text-fg-muted">{label}</span>}
    </span>
  )
}
