import { Command } from "cmdk"
import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTenantNav } from "@/lib/tenantPath"
import { cn } from "@/lib/utils"
import {
  IconCalendar,
  IconChart,
  IconClock,
  IconDashboard,
  IconExit,
  IconGrid,
  IconPalm,
  IconSearch,
  IconTarget,
  IconUsers,
  IconWallet,
} from "@/components/icons"

interface PaletteItem {
  id: string
  label: string
  description?: string
  icon: React.ComponentType<{ className?: string }>
  keywords: string[]
  to: string
  group: string
}

const ITEMS: PaletteItem[] = [
  { id: "home", label: "Go to Dashboard", description: "Overview and recent activity", icon: IconDashboard, keywords: ["home", "dashboard", "overview"], to: "/dashboard", group: "Navigate" },
  { id: "people", label: "Go to People", description: "Employees, directory, org chart", icon: IconUsers, keywords: ["people", "employees", "directory", "org"], to: "/people", group: "Navigate" },
  { id: "roster", label: "Go to Roster Builder", description: "Generate, adjust and publish roster versions", icon: IconCalendar, keywords: ["roster", "schedule", "solver", "publish", "shift"], to: "/scheduling/roster", group: "Navigate" },
  { id: "time", label: "Go to Time & Attendance", description: "Clock in/out, timesheets", icon: IconClock, keywords: ["time", "attendance", "clock", "timesheet"], to: "/time", group: "Navigate" },
  { id: "leave", label: "Go to Leave", description: "Requests, balances, types", icon: IconPalm, keywords: ["leave", "balance", "request", "pto", "pending leaves", "show pending leaves", "my leave"], to: "/leave", group: "Navigate" },
  { id: "recruiting", label: "Go to Recruiting", description: "Requisitions, candidates, offers", icon: IconTarget, keywords: ["recruiting", "candidates", "offers", "hiring"], to: "/recruiting", group: "Navigate" },
  { id: "payroll", label: "Go to Payroll", description: "Pay runs, components, payslips", icon: IconWallet, keywords: ["payroll", "pay", "salary", "payslip", "show payslip", "my payslip"], to: "/platform/payroll", group: "Navigate" },
  { id: "performance", label: "Go to Performance", description: "Goals, reviews, compensation", icon: IconChart, keywords: ["performance", "goals", "reviews", "compensation"], to: "/platform/performance", group: "Navigate" },
  { id: "learning", label: "Go to Learning", description: "Courses, certifications, talent", icon: IconGrid, keywords: ["learning", "courses", "certifications", "training"], to: "/platform/learning", group: "Navigate" },
  { id: "reports", label: "Go to Reports", description: "Headcount, leave, labour cost", icon: IconChart, keywords: ["reports", "analytics", "headcount", "audit"], to: "/reports", group: "Navigate" },
  { id: "admin", label: "Go to Admin", description: "Compliance, client onboarding", icon: IconExit, keywords: ["admin", "compliance", "client", "onboarding"], to: "/client-onboarding", group: "Navigate" },
  { id: "import", label: "Go to Import / Export", description: "CSV import, dry run, commit", icon: IconGrid, keywords: ["import", "export", "csv", "migration"], to: "/import", group: "Navigate" },
  { id: "jobs", label: "Go to Background Jobs", description: "Queue monitoring and failures", icon: IconGrid, keywords: ["jobs", "queue", "background", "worker"], to: "/jobs", group: "Navigate" },
  { id: "mfa", label: "Go to Security (MFA)", description: "Two-factor enrolment and recovery", icon: IconGrid, keywords: ["mfa", "2fa", "totp", "security", "password"], to: "/mfa", group: "Navigate" },
  { id: "design", label: "Go to Design System", description: "Component showcase", icon: IconGrid, keywords: ["design", "components", "showcase"], to: "/design", group: "Navigate" },
]

/** Natural-language routing: keyword phrases → palette item. Exported for unit testing. */
export function parseConversationalQuery(query: string): PaletteItem | null {
  const q = query.toLowerCase().trim()
  // Direct keyword matching for conversational phrases
  const mappings: Array<{ phrases: string[]; itemId: string }> = [
    { phrases: ["pending leaves", "show pending leaves", "my leave requests", "leave requests"], itemId: "leave" },
    { phrases: ["payslip", "show payslip", "my payslip", "pay slip", "salary slip"], itemId: "payroll" },
    { phrases: ["time", "clock in", "timesheet", "attendance"], itemId: "time" },
    { phrases: ["roster", "my shifts", "upcoming shifts"], itemId: "roster" },
    { phrases: ["dashboard", "overview", "home"], itemId: "home" },
    { phrases: ["people", "directory", "employees"], itemId: "people" },
    { phrases: ["reports", "analytics"], itemId: "reports" },
  ]
  for (const m of mappings) {
    if (m.phrases.some((p) => q.includes(p))) {
      return ITEMS.find((i) => i.id === m.itemId) ?? null
    }
  }
  // Fallback to regular keyword search
  const hit = ITEMS.find(
    (item) =>
      item.keywords.some((k) => q.includes(k.toLowerCase())) ||
      item.label.toLowerCase().includes(q) ||
      item.description?.toLowerCase().includes(q)
  )
  return hit ?? null
}

/**
 * ⌘K command palette.
 *
 * Opens on the global ⌘K / Ctrl+K shortcut (dispatched by lib/keyboard) or
 * via the top-bar search trigger. Searches navigation destinations and runs
 * the selected action. Fully keyboard-driven: arrows to move, enter to run,
 * escape to close.
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const navigate = useNavigate()
  const tenantNav = useTenantNav()

  useEffect(() => {
    const openHandler = () => setOpen(true)
    window.addEventListener("karmathy:open-command-palette", openHandler)
    return () => window.removeEventListener("karmathy:open-command-palette", openHandler)
  }, [])

  const filtered = useMemo(() => {
    if (!query.trim()) return ITEMS
    const q = query.toLowerCase()
    return ITEMS.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.description?.toLowerCase().includes(q) ||
        item.keywords.some((k) => k.includes(q))
    )
  }, [query])

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
        <IconSearch className="w-4 h-4 text-fg-subtle shrink-0" aria-hidden="true" />
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

      <div className="flex items-center justify-between px-4 py-2 border-t border-border bg-surface-sunken">
        <span className="text-[11px] text-fg-muted">
          <kbd className="rounded border border-border px-1 py-0.5 text-[10px]">↑↓</kbd> navigate ·{" "}
          <kbd className="rounded border border-border px-1 py-0.5 text-[10px]">↵</kbd> select
        </span>
        <span className="text-[11px] text-fg-muted">⌘K to open</span>
      </div>
    </Command.Dialog>
  )
}