import { Toaster as SonnerToaster, toast } from "sonner"

/**
 * Toast notifications via Sonner.
 *
 * Usage anywhere:
 *   import { toast } from "@/components/ui/sonner"
 *   toast.success("Saved", { description: "..." })
 *   toast.error("Failed", { action: { label: "Undo", onClick: () => {} } })
 */
export { toast }

export function Toaster(props: React.ComponentProps<typeof SonnerToaster>) {
  return (
    <SonnerToaster
      position="top-right"
      toastOptions={{
        classNames: {
          toast: "bg-surface-raised border border-border shadow-lg text-sm",
          title: "text-fg font-medium",
          description: "text-fg-muted",
          actionButton: "bg-brand-600 text-white",
          cancelButton: "bg-surface text-fg",
        },
      }}
      closeButton
      {...props}
    />
  )
}
