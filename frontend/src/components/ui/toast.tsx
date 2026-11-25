import { Toaster as SonnerToaster, toast, type ExternalToast } from "sonner"
import { cn } from "@/lib/utils"

interface ToastProps extends ExternalToast {
  variant?: "default" | "success" | "error" | "warning" | "info"
}

const variantStyles: Record<string, Partial<ExternalToast>> = {
  default: {},
  success: { className: "bg-[var(--semantic-status-success)] text-white" },
  error: { className: "bg-[var(--semantic-status-error)] text-white" },
  warning: { className: "bg-[var(--semantic-status-warning)] text-white" },
  info: { className: "bg-[var(--semantic-status-info)] text-white" },
}

export function showToast(message: string, options: ToastProps = {}) {
  const { variant = "default", ...rest } = options
  const style = variantStyles[variant]
  return toast(message, { ...style, ...rest })
}

export function showSuccess(message: string, options?: ToastProps) {
  return showToast(message, { ...options, variant: "success" })
}

export function showError(message: string, options?: ToastProps) {
  return showToast(message, { ...options, variant: "error" })
}

export function showWarning(message: string, options?: ToastProps) {
  return showToast(message, { ...options, variant: "warning" })
}

export function showInfo(message: string, options?: ToastProps) {
  return showToast(message, { ...options, variant: "info" })
}

export function Toaster({ className, ...props }: React.ComponentPropsWithoutRef<typeof SonnerToaster>) {
  return (
    <SonnerToaster
      className={cn("toaster", className)}
      theme="system"
      position="top-right"
      expand={true}
      closeButton={true}
      richColors={true}
      toastOptions={{
        className: "bg-surface border border-border text-fg",
        duration: 5000,
        style: {
          background: "var(--surface)",
          color: "var(--fg)",
          border: "1px solid var(--border-default)",
        },
      }}
      {...props}
    />
  )
}

export { toast }
