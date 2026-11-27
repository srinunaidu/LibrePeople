import { Command } from "cmdk"
import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import { useTenantNav } from "@/lib/tenantPath"
import { cn } from "@/lib/utils"
import {
  allPaletteItems,
  paletteItemsFor,
  type PaletteItem,
} from "@/lib/nav"

/** Natural-language routing: keyword phrases → palette item. Exported for unit testing. */
export function parseConversationalQuery(query: string, role?: string | null): PaletteItem | null {
  const items = role ? paletteItemsFor(role) : allPaletteItems()
  const q = query.toLowerCase().trim()
  // Direct keyword matching for conversational phrases
  const mappings: Array<{ phrases: string[]; itemId: string }> = [
    { phrases: ["pending leaves", "show pending leaves", "my leave requests", "leave requests"], itemId: "leave" },
    { phrases: ["payslip", "show payslip", "my payslip", "pay slip", "salary slip"], itemId: "payroll" },
    { phrases: ["time", "clock in", "timesheet", "attendance"], itemId: "time" },
    { phrases: ["roster", "my shifts", "upcoming shifts"], itemId: "time" },
    { phrases: ["dashboard", "overview", "home"], itemId: "overview" },
    { phrases: ["people", "directory", "employees"], itemId: "people" },
    { phrases: ["reports", "analytics"], itemId: "reports" },
  ]
  for (const m of mappings) {
    if (m.phrases.some((p) => q.includes(p))) {
      return items.find((i) => i.id === m.itemId) ?? null
    }
  }
  // Fallback to regular keyword search (multi-character keywords only, so
  // short section keys like "er" cannot match inside ordinary words).
  const hit = items.find(
    (item) =>
      item.keywords.some((k) => k.length > 2 && q.includes(k.toLowerCase())) ||
      item.label.toLowerCase().includes(q) ||
      item.description?.toLowerCase().includes(q)
  )
  return hit ?? null
}

/**
 * ⌘K command palette.
 *
 * Opens on the global ⌘K / Ctrl+K shortcut (dispatched by lib/keyboard) or
 * via the top-bar search trigger. Entries are exactly the current role's
 * visible sections plus its canonical admin links (lib/nav.ts) — no
 * aliases, no hidden-role items. Fully keyboard-driven: arrows to move,
 * enter to run, escape to close.
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const { user } = useAuth()

  const items = useMemo(() => paletteItemsFor(user?.role), [user?.role])

  useEffect(() => {
    const openHandler = () => setOpen(true)
    window.addEventListener("karmathy:open-command-palette", openHandler)
    return () => window.removeEventListener("karmathy:open-command-palette", openHandler)
  }, [])

  const filtered = useMemo(() => {
    if (!query.trim()) return items
    // Conversational query first ("show pending leaves"), then substring.
    const conversational = parseConversationalQuery(query, user?.role)
    const q = query.toLowerCase()
    const substring = items.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.description?.toLowerCase().includes(q) ||
        item.keywords.some((k) => k.includes(q))
    )
    if (conversational && !substring.some((i) => i.id === conversational.id)) {
      return [conversational, ...substring]
    }
    return substring
  }, [query, items, user?.role])

  const run = (item: PaletteItem) => {
    setOpen(false)
    setQuery("")
    navigate(tenantNav.to(item.to))
  }

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Command palette"
      className="fixed left-1/2 top-[15%] z-[1500] w-full max-w-xl -translate-x-1/2 rounded-xl border border-border bg-surface-raised shadow-2xl overflow-hidden"
    >
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
        <Command.Input
          value={query}
          onValueChange={setQuery}
          placeholder="Search pages and actions…"
          className="flex-1 bg-transparent text-sm text-fg placeholder:text-fg-subtle focus:outline-none"
          autoFocus
        />
        <kbd className="hidden sm:inline-flex items-center rounded border border-border px-1.5 py-0.5 text-[10px] font-medium text-fg-muted">
          ESC
        </kbd>
      </div>

      <Command.List className="max-h-[50vh] overflow-y-auto p-2">
        <Command.Empty className="py-8 text-center text-sm text-fg-muted">
          No results found.
        </Command.Empty>

        {filtered.map((item) => (
          <Command.Item
            key={item.id}
            value={`${item.label} ${item.keywords.join(" ")}`}
            onSelect={() => run(item)}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 cursor-pointer transition-colors",
              "data-[selected=true]:bg-brand-50 data-[selected=true]:text-brand-700"
            )}
          >
            <span className="icon-tile icon-tile-brand w-8 h-8 text-sm">
              <item.icon className="w-4 h-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium text-fg">{item.label}</span>
              {item.description && (
                <span className="block text-xs text-fg-muted truncate">{item.description}</span>
              )}
            </span>
            <span className="text-[10px] font-medium text-fg-subtle uppercase tracking-wider">{item.group}</span>
          </Command.Item>
        ))}
      </Command.List>

      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-sunken">
        <span className="text-[11px] text-fg-muted">
          <kbd className="rounded border border-border px-1 py-0.5 text-[10px]">↑↓</kbd> navigate ·{" "}
          <kbd className="rounded border border-border px-1 py-0.5 text-[10px]">↵</kbd> select
        </span>
        <span className="text-[11px] text-fg-muted">⌘K to open</span>
      </div>
    </Command.Dialog>
  )
}
