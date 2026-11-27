import { useEffect, useState } from "react"
import { GOTO_ENTRIES } from "@/lib/nav"

/**
 * Keyboard shortcut help sheet.
 *
 * Opens on the `?` key or from the user menu. The Navigation group renders
 * from the same "g <letter>" registry the rail registers (lib/nav.ts
 * GOTO_ENTRIES), so the sheet can never drift from the working shortcuts.
 * Dismiss with Escape.
 */
export function ShortcutHelp() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const openHandler = () => setOpen(true)
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false)
    }
    window.addEventListener("karmathy:open-shortcut-help", openHandler)
    document.addEventListener("keydown", keyHandler)
    return () => {
      window.removeEventListener("karmathy:open-shortcut-help", openHandler)
      document.removeEventListener("keydown", keyHandler)
    }
  }, [])

  if (!open) return null

  const groups: { name: string; items: { keys: string; description: string }[] }[] = [
    {
      name: "General",
      items: [
        { keys: "⌘K", description: "Open command palette" },
        { keys: "t", description: "Toggle light / dark theme" },
        { keys: "?", description: "Show this help" },
        { keys: "Esc", description: "Close dialogs and menus" },
      ],
    },
    {
      name: "Navigation",
      items: GOTO_ENTRIES.map((entry) => ({
        keys: `g ${entry.gKey}`,
        description: `Go to ${entry.label}`,
      })),
    },
  ]

  return (
    <div
      className="fixed inset-0 z-[1500] flex items-center justify-center bg-[rgba(2,6,23,0.5)] backdrop-blur-sm p-4"
      onClick={() => setOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
    >
      <div
        className="w-full max-w-lg rounded-xl border border-border bg-surface-raised shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-fg">Keyboard Shortcuts</h2>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="p-1 rounded-md text-fg-muted hover:text-fg hover:bg-surface-hover"
            aria-label="Close"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto p-5 space-y-5">
          {groups.map((group) => (
            <div key={group.name}>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-fg-muted mb-2">{group.name}</h3>
              <ul className="space-y-1.5">
                {group.items.map((item) => (
                  <li key={item.keys} className="flex items-center justify-between gap-4 text-sm">
                    <span className="text-fg">{item.description}</span>
                    <kbd className="shrink-0 rounded border border-border bg-surface-inset px-1.5 py-0.5 text-xs font-medium text-fg-muted">
                      {item.keys}
                    </kbd>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
