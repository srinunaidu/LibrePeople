import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

export const badgeVariants = cva(
  "inline-flex items-center rounded-full font-medium whitespace-nowrap",
  {
    variants: {
      variant: {
        brand: "badge-brand",
        teal: "badge-teal",
        green: "badge-green",
        violet: "badge-violet",
        amber: "badge-amber",
        rose: "badge-rose",
        slate: "badge-slate",
        outline: "border border-border-strong text-fg-muted",
      },
      size: {
        sm: "text-[11px] px-2 py-0.5",
        md: "text-xs px-2.5 py-1",
      },
    },
    defaultVariants: { variant: "slate", size: "sm" },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean
}

export function Badge({ className, variant, size, dot, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {dot && (
        <span
          className={cn(
            "mr-1.5 inline-block h-1.5 w-1.5 rounded-full",
            variant === "green" && "bg-[var(--semantic-status-success)]",
            variant === "amber" && "bg-[var(--semantic-status-warning)]",
            variant === "rose" && "bg-[var(--semantic-status-error)]",
            variant === "brand" && "bg-brand-600",
            !["green", "amber", "rose", "brand"].includes(variant ?? "") && "bg-[var(--fg-subtle)]"
          )}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  )
}
