import { cn } from "@/lib/utils"

export interface AvatarProps extends React.HTMLAttributes<HTMLSpanElement> {
  src?: string
  alt?: string
  size?: "xs" | "sm" | "md" | "lg"
  fallback?: string
}

const sizes = {
  xs: "h-5 w-5 text-[10px]",
  sm: "h-7 w-7 text-xs",
  md: "h-9 w-9 text-sm",
  lg: "h-12 w-12 text-base",
}

export function Avatar({ className, src, alt, size = "md", fallback, ...props }: AvatarProps) {
  const initials = fallback || (alt ?? "?").slice(0, 2).toUpperCase()

  if (src) {
    return (
      <span className={cn("relative inline-block rounded-full overflow-hidden", sizes[size], className)} {...props}>
        <img src={src} alt={alt ?? ""} className="h-full w-full object-cover" loading="lazy" />
      </span>
    )
  }

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full bg-gradient-to-br from-brand-600 to-violet-600 text-white font-semibold shrink-0 select-none",
        sizes[size],
        className
      )}
      role="img"
      aria-label={alt}
      {...props}
    >
      {initials}
    </span>
  )
}
