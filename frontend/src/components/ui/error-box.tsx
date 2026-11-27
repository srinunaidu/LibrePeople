import { Modal, ModalContent, ModalDescription, ModalTitle } from "@/components/ui"

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
    <Modal open onOpenChange={(open) => { if (!open) onClose() }}>
      <ModalContent size="md" className="text-center">
        <ModalTitle className="text-2xl font-bold text-error mb-2">
          {title}
        </ModalTitle>
        <ModalDescription className="mb-6 line-clamp-4">
          {description}
        </ModalDescription>
        {/* 44px exemption (documented): dense admin pattern keeps compact
            buttons here; the dialog itself traps focus, closes on Escape /
            overlay / X, and returns focus to the trigger. */}
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
      </ModalContent>
    </Modal>
  )
}
