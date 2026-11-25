import * as DialogPrimitive from "@radix-ui/react-dialog"
import { cn } from "@/lib/utils"
import * as React from "react"
import { X } from "lucide-react"

const Modal = DialogPrimitive.Root
const ModalTrigger = DialogPrimitive.Trigger
const ModalClose = DialogPrimitive.Close

const ModalOverlay = React.forwardRef<
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
ModalOverlay.displayName = "ModalOverlay"

interface ModalContentProps extends React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
  size?: "sm" | "md" | "lg" | "xl" | "full"
}

const sizeClasses = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
  full: "max-w-[90vw]",
}

const ModalContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  ModalContentProps
>(({ className, size = "md", children, ...props }, ref) => (
  <DialogPrimitive.Portal>
    <ModalOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-1/2 top-1/2 z-[1400] w-full -translate-x-1/2 -translate-y-1/2",
        sizeClasses[size],
        "rounded-xl border border-border bg-surface p-6 shadow-xl data-[state=open]:animate-scale-in",
        "max-h-[90vh] overflow-y-auto",
        className
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 rounded-md p-1 text-fg-muted hover:text-fg hover:bg-surface-hover focus-visible:outline-2 focus-visible:outline-brand-600" aria-label="Close">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPrimitive.Portal>
))
ModalContent.displayName = "ModalContent"

const ModalHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col gap-1.5 mb-4", className)} {...props} />
)

const ModalTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold text-fg", className)}
    {...props}
  />
))
ModalTitle.displayName = "ModalTitle"

const ModalDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-fg-muted", className)}
    {...props}
  />
))
ModalDescription.displayName = "ModalDescription"

const ModalFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex items-center justify-end gap-3 mt-6 pt-4 border-t border-border", className)} {...props} />
)

interface DrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
  side?: "left" | "right"
  size?: "sm" | "md" | "lg" | "full"
  title?: string
  description?: string
}

const drawerSizeClasses = {
  sm: "w-64",
  md: "w-96",
  lg: "w-[32rem]",
  full: "w-[90vw] max-w-[40rem]",
}

export function Drawer({
  open,
  onOpenChange,
  children,
  side = "right",
  size = "md",
  title,
  description,
}: DrawerProps) {
  return (
    <Modal open={open} onOpenChange={onOpenChange}>
      <ModalContent
        size={size}
        className={cn(
          drawerSizeClasses[size],
          "max-h-full",
          side === "left" ? "left-0 -translate-x-0" : "right-0 -translate-x-0",
          "top-0 -translate-y-0 h-full rounded-none border-l border-r-0",
          "data-[state=open]:animate-slide-in"
        )}
      >
        {(title || description) && (
          <ModalHeader>
            {title && <ModalTitle>{title}</ModalTitle>}
            {description && <ModalDescription>{description}</ModalDescription>}
          </ModalHeader>
        )}
        {children}
      </ModalContent>
    </Modal>
  )
}

export {
  Modal,
  ModalTrigger,
  ModalClose,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
}
