import * as TabsPrimitive from "@radix-ui/react-tabs"
import * as React from "react"
import { cn } from "@/lib/utils"

const Tabs = TabsPrimitive.Root

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      // `flex-wrap` and `max-w-full`: six tabs are 562px wide, which made
      // the whole page scroll sideways on a 360px screen. Wrapping keeps
      // every tab reachable without a sideways scroll.
      "inline-flex max-w-full flex-wrap items-center gap-1 rounded-lg bg-surface-inset p-1 border border-border-subtle",
      className
    )}
    {...props}
  />
))
TabsList.displayName = "TabsList"

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-all min-h-[44px]",
      // The label was `text-fm-muted` — a typo for `text-fg-muted`, so no
      // class applied and the tabs inherited the page colour. The muted token
      // is only 4.34:1 on this inset strip, so the honest choice is the
      // readable foreground: the raised pill carries the active state, not
      // the text colour.
      "text-fg",
      "data-[state=active]:bg-surface data-[state=active]:text-fg data-[state=active]:shadow-sm",
      "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600",
      "disabled:opacity-50",
      className
    )}
    {...props}
  />
))
TabsTrigger.displayName = "TabsTrigger"

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn("mt-2 focus-visible:outline-none", className)}
    // Keep every panel in the DOM (inactive ones are `hidden`) so that each
    // trigger's `aria-controls` resolves to a real panel id. Radix unmounts
    // inactive panels by default, which left `aria-controls` pointing at IDs
    // that no longer exist — an `aria-valid-attr-value` axe violation.
    forceMount
    {...props}
  />
))
TabsContent.displayName = "TabsContent"

export { Tabs, TabsList, TabsTrigger, TabsContent }