import { cn } from "@/lib/utils"

export function ProgressRing({
  percent,
  size = 48,
  strokeWidth = 4,
  tone = "brand",
  label,
  className,
}: {
  percent: number
  size?: number
  strokeWidth?: number
  tone?: "brand" | "success" | "warning" | "error"
  label?: string
  className?: string
}) {
  const clamped = Math.max(0, Math.min(100, percent))
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (clamped / 100) * circumference

  const colorMap: Record<string, string> = {
    brand: "var(--brand-600)",
    success: "var(--success)",
    warning: "var(--warning)",
    error: "var(--error)",
  }

  return (
    <div className={cn("inline-flex flex-col items-center gap-1", className)} role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--surface-inset)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colorMap[tone]}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 300ms ease" }}
        />
      </svg>
      {label && <span className="text-xs font-medium text-fg">{label}</span>}
      <span className="text-xs text-fg-muted">{clamped}%</span>
    </div>
  )
}
