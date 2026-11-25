import { useState, useRef } from "react"

export interface UseConfirmReturn {
  ref: React.RefObject<HTMLButtonElement>
  confirm: () => void
  cancel: () => void
  open: () => void
}

export function useConfirm(options: {
  title: string
  description: string
  confirmText?: string
  cancelText?: string
  onConfirm?: () => void
  onCancel?: () => void
}): UseConfirmReturn {
  const [showConfirm, setShowConfirm] = useState(false)
  const ref = useRef<HTMLButtonElement>(null)

  const handleConfirm = () => {
    setShowConfirm(false)
    options.onConfirm?.()
  }

  const handleCancel = () => {
    setShowConfirm(false)
    options.onCancel?.()
  }

  return {
    ref,
    confirm: () => setShowConfirm(true),
    cancel: handleCancel,
    open: () => setShowConfirm(true),
  }
}
