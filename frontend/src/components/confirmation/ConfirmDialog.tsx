import {
  Modal,
  ModalContent,
  ModalTrigger,
} from "@/components/ui"

// Canonical confirm dialog, built on the barrel Modal primitives
// (a single overlay, focus and close affordance). Previously a third
// radix wrapper; kept exports preserve the call-site API.
const ConfirmDialog = Modal
const ConfirmTrigger = ModalTrigger

interface ConfirmDialogProps {
  open: boolean
  onConfirm: () => void
  onCancel: () => void
  title: string
  description: string
  confirmText?: string
  cancelText?: string
}

const ConfirmContent = ModalContent

ConfirmDialog.displayName = "ConfirmDialog"

export { ConfirmDialog, ConfirmTrigger, ConfirmContent }
export type { ConfirmDialogProps }
