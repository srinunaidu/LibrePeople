/**
 * Global keyboard shortcuts.
 *
 *   ⌘K / Ctrl+K  — command palette
 *   g + letter   — go to a workspace area (g h = home, g p = people, …)
 *   ?            — shortcut help
 *   t            — toggle theme
 *
 * Shortcuts are registered once at the app root. They are suppressed while
 * the user is typing in a form field, so "g p" in a search box types the
 * letters rather than navigating away.
 */

export interface Shortcut {
  /** Human-readable label shown in the palette and help sheet. */
  label: string
  /** The key combination. Single lowercase letters are treated as "g + key". */
  keys: string
  /** What the shortcut does. */
  description: string
  /** Group shown in the help sheet. */
  group: "Navigation" | "Actions" | "General"
  /** Whether this appears in the ⌘K palette. */
  palette?: boolean
  run: () => void
}

let registered = false
let pendingG = false
let gTimer: number | undefined
const listeners = new Set<(shortcut: Shortcut) => void>()

export function onShortcut(cb: (shortcut: Shortcut) => void): () => void {
  listeners.add(cb)
  return () => listeners.delete(cb)
}

function emit(shortcut: Shortcut) {
  listeners.forEach((cb) => cb(shortcut))
}

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return (
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.tagName === "SELECT" ||
    target.isContentEditable
  )
}

const passthrough = new Set(["h", "t", "?"])

/**
 * Register global keyboard shortcuts. Safe to call more than once — it is a
 * no-op after the first registration.
 */
export function registerShortcuts() {
  if (registered) return
  registered = true

  document.addEventListener("keydown", (e) => {
    // Command palette: ⌘K or Ctrl+K.
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault()
      emit({ label: "Command palette", keys: "⌘K", description: "Search and navigate anywhere", group: "General", palette: true, run: () => {} })
      window.dispatchEvent(new CustomEvent("karmathy:open-command-palette"))
      return
    }

    // Everything below is suppressed while typing.
    if (isTyping(e.target)) return

    // "g" starts a two-key sequence.
    if (!pendingG && e.key.toLowerCase() === "g" && !e.metaKey && !e.ctrlKey && !e.altKey) {
      pendingG = true
      window.clearTimeout(gTimer)
      gTimer = window.setTimeout(() => (pendingG = false), 900)
      e.preventDefault()
      return
    }

    if (pendingG) {
      pendingG = false
      window.clearTimeout(gTimer)
      const key = e.key.toLowerCase()
      const shortcut = GOTO_SHORTCUTS[key]
      if (shortcut) {
        e.preventDefault()
        shortcut.run()
        emit(shortcut)
      }
      return
    }

    // Single-key shortcuts.
    if (e.key === "?") {
      e.preventDefault()
      window.dispatchEvent(new CustomEvent("karmathy:open-shortcut-help"))
      return
    }

    if (e.key.toLowerCase() === "t" && !e.metaKey && !e.ctrlKey && !e.altKey) {
      e.preventDefault()
      window.dispatchEvent(new CustomEvent("karmathy:toggle-theme"))
    }
  })
}

/** "g + letter" navigation targets. Filled in by the shell once mounted. */
const GOTO_SHORTCUTS: Record<string, Shortcut> = {}

export function registerGoto(key: string, shortcut: Shortcut) {
  GOTO_SHORTCUTS[key.toLowerCase()] = shortcut
}

export function unregisterGoto(key: string) {
  delete GOTO_SHORTCUTS[key.toLowerCase()]
}