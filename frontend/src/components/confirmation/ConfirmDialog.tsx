import * as DialogPrimitive from "@radix-ui/react-dialog"
import { cn } from "@/lib/utils"
import * as React from "react"
import { X } from "lucide-react"

const ConfirmDialog = DialogPrimitive.Root
const ConfirmTrigger = DialogPrimitive.Trigger
const ConfirmClose = DialogPrimitive.Close

const ConfirmOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-[1400] bg-[rgba(2,6,23,0.5)] backdrop-blur-sm data-[state=open]:animate-fade-in",
      className
    )}
    {...props}
  />
))
ConfirmOverlay.displayName = "ConfirmOverlay"

interface ConfirmDialogProps {
  open: boolean
  onConfirm: () => void
  onCancel: () => void
  title: string
  description: string
  confirmText?: string
  cancelText?: string
}

const ConfirmContent = DialogPrimitive.Content

ConfirmDialog.displayName = "ConfirmDialog"

export { ConfirmDialog, ConfirmTrigger, ConfirmContent }
export type { ConfirmDialogProps }