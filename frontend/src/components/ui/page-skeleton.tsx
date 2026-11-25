import * as React from "react"
import { cn } from "@/lib/utils"

export function PageSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn("flex flex-col items-center justify-center min-h-[400px] gap-4", className)}>
      <div className="w-3/4 h-6 animate-pulse rounded bg-surface-sunken" />
      <div className="w-1/2 h-4 animate-pulse rounded bg-surface-sunken" />
      <div className="w-full h-32 animate-pulse rounded bg-surface-sunken" />
    </div>
  )
}
