import * as PopoverPrimitive from "@radix-ui/react-popover"
import { cn } from "@/lib/utils"
import * as React from "react"

const Popover = PopoverPrimitive.Root
const PopoverTrigger = PopoverPrimitive.Trigger

const PopoverContent = React.forwardRef<
  React.ElementRef<typeof PopoverPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof PopoverPrimitive.Content>
>(({ className, sideOffset = 4, align = "center", ...props }, ref) => (
  <PopoverPrimitive.Portal>
    <PopoverPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      align={align}
      className={cn(
        "z-[1000] w-72 rounded-lg border border-border bg-surface-raised p-0 shadow-lg",
        "data-[state=open]:animate-scale-in",
        "focus-visible:outline-2 focus-visible:outline-brand-600",
        className
      )}
      {...props}
    >
      <PopoverPrimitive.Arrow className="h-2 w-2 fill-surface-raised stroke-border" />
    </PopoverPrimitive.Content>
  </PopoverPrimitive.Portal>
))
PopoverContent.displayName = "PopoverContent"

export { Popover, PopoverTrigger, PopoverContent }
