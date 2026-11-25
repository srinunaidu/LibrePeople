import * as React from "react"
import { cn } from "@/lib/utils"
import { ChevronDown } from "lucide-react"

export interface AccordionItemProps {
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
  className?: string
}

export function AccordionItem({ title, defaultOpen = false, children, className }: AccordionItemProps) {
  const [open, setOpen] = React.useState(defaultOpen)
  const id = React.useId()
  const contentId = `accordion-${id}`

  return (
    <div className={cn("border border-border rounded-lg overflow-hidden", className)}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen(!open)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            setOpen(!open)
          }
        }}
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-fg hover:bg-surface-hover transition-colors duration-150 min-h-[44px]"
      >
        <span>{title}</span>
        <ChevronDown
          className={cn("w-4 h-4 shrink-0 text-fg-muted transition-transform duration-150", open && "rotate-180")}
          aria-hidden="true"
        />
      </button>
      <div
        id={contentId}
        role="region"
        hidden={!open}
        className={cn(
          "overflow-hidden transition-all duration-150",
          open ? "opacity-100" : "opacity-0"
        )}
      >
        {open && <div className="px-4 py-3 border-t border-border-subtle bg-surface-sunken">{children}</div>}
      </div>
    </div>
  )
}

export function Accordion({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("space-y-2", className)}>{children}</div>
}

/** Advanced Options — collapsed by default, uses AccordionItem pattern */
export function AdvancedOptions({ children }: { children: React.ReactNode }) {
  return <AccordionItem title="Advanced Options">{children}</AccordionItem>
}
