/** Phase T — design-system shimmer skeleton (premium loading). */
import { cn } from "@/lib/utils"

export function ShimmerSkeleton({
  className,
  lines = 3,
}: {
  className?: string
  lines?: number
}) {
  return (
    <div className={cn("space-y-2", className)} aria-busy="true" aria-label="Loading content">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "h-4 rounded-lg shimmer-gradient",
            i === lines - 1 ? "w-3/4" : "w-full",
          )}
        />
      ))}
    </div>
  )
}
