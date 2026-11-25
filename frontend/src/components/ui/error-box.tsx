import * as DialogPrimitive from "@radix-ui/react-dialog"
import { cn } from "@/lib/utils"
import * as React from "react"
import { X } from "lucide-react"

export function ErrorBox({
  title = "Error",
  description,
  action,
  onClose,
}: {
  title?: string
  description: string
  action?: string
  onClose: () => void
}) {
  return (
    <DialogPrimitive.Root>
      <DialogPrimitive.Overlay className="fixed inset-0 z-[1000] bg-black/40 backdrop-blur-sm" />
      <DialogPrimitive.Content
        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg rounded-2xl bg-surface p-8 shadow-xl text-center border border-border"
      >
        <DialogPrimitive.Title className="text-2xl font-bold text-error mb-2">
          {title}
        </DialogPrimitive.Title>
        <DialogPrimitive.Description className="text-text-secondary mb-6 line-clamp-4">
          {description}
        </DialogPrimitive.Description>
        <div className="flex justify-between items-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md bg-surface-inset text-sm font-medium hover:bg-surface-hover"
          >
            Cancel
          </button>
          {action && (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-md bg-brand-600 text-white font-medium hover:bg-brand-700"
            >
              {action}
            </button>
          )}
        </div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Root>
  )
}