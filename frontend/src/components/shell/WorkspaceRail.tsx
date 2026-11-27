import { useEffect, useState, type ComponentType } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useTenant } from "@/context/TenantContext"
import { registerGoto, unregisterGoto } from "@/lib/keyboard"
import { barePath, useTenantNav } from "@/lib/tenantPath"
import {
  Activity,
  BarChart3,
  Bed,
  Book,
  Briefcase,
  Building,
  Calendar,
  ChevronDown,
  ChevronRight,
  Clock,
  CreditCard,
  Gift,
  LayoutDashboard,
  Palette,
  PieChart,
  Plug,
  Presentation,
  RefreshCcw,
  Settings,
  Shield,
  Star,
  Target,
  User,
  Users,
} from "lucide-react"

/**
 * Unified 220px sidebar (TradeMarkk obsidian shell).
 *
 * Merges the old icon-only workspace rail and the secondary sidebar into
 * ONE navigation: brand header, "+ Quick Action" command-palette CTA,
 * categorized groups (OVERVIEW / CORE HR & ESS / TIME & PAYROLL /
 * PLATFORM & ADMIN), and a collapsible Admin console holding every /admin/*
 * route. Single-tenant install: one org, no workspace switcher.
 *
 * Route paths are the exact App.tsx registrations — never renamed here.
 */

export interface NavItem {
  label: string
  to: string
  icon?: ComponentType<{ className?: string }>
  /** Child links rendered under the item (indented, always visible). */
  sub?: NavItem[]
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

/* Admin console — one entry per screen (portals-completion AC4: <20 entries,
 * no double aliases). Alias routes dropped (same component as the canonical
 * entry): /admin/user-admin → users, /admin/tenant-branding → branding,
 * /admin/module-entitlements → entitlements, /admin/workflow-approval →
 * workflow, /admin/integration-credentials + /admin/integrations-hub stay
 * separate (Credentials vs Hub are different screens; the -credentials alias
 * of Credentials is dropped), /admin/backup-restore → backup,
 * /admin/locale-config + /admin/ad-03 → locale, /admin/ad-09 →
 * retention-export. Screens already reachable in the main groups are not
 * repeated here: /admin/project-status + /project-status, /admin/design-gallery
 * + /admin/theme → Theme & Gallery, /admin/data-quality → /data-quality,
 * /admin/hr-01 → People, /admin/break-glass + /admin/compliance → Platform &
 * Admin. /admin/platform-showcase is a marketing demo, not an admin function.
 */
const ADMIN_ITEMS: NavItem[] = [
  { label: "User Admin", to: "/admin/users" },
  { label: "Company branding", to: "/admin/branding" },
  { label: "Module entitlements", to: "/admin/entitlements" },
  { label: "Workflow Approval", to: "/admin/workflow" },
  { label: "Integration Credentials", to: "/admin/integrations" },
  { label: "Backup / Restore", to: "/admin/backup" },
  { label: "Feature Flags", to: "/admin/feature-flags" },
  { label: "Locale Config", to: "/admin/locale" },
  { label: "Retention Export", to: "/admin/retention-export" },
  { label: "Bank Export", to: "/admin/bank-export" },
  { label: "Documents", to: "/admin/documents" },
  { label: "ER Cases", to: "/admin/er-cases" },
  { label: "Export & Erasure", to: "/admin/export-erasure" },
  { label: "Goals & OKR", to: "/admin/goals-okr" },
  { label: "Headcount", to: "/admin/headcount-cost" },
  { label: "Integrations Hub", to: "/admin/integrations-hub" },
  { label: "Interview Scheduling", to: "/admin/interview-scheduling" },
  { label: "Org Chart", to: "/admin/org-chart" },
]

/* "g <letter>" navigation targets — same keys the old workspace rail
 * registered, so CommandPalette entries and ShortcutHelp keep working. */
const GOTO_AREAS: { label: string; to: string; gotoKey: string }[] = [
  { label: "Home", to: "/dashboard", gotoKey: "h" },
  { label: "People", to: "/people", gotoKey: "p" },
  { label: "Time", to: "/time", gotoKey: "t" },
  { label: "Scheduling", to: "/scheduling", gotoKey: "s" },
  { label: "Forecast", to: "/forecasting", gotoKey: "g" },
  { label: "Leave", to: "/leave", gotoKey: "l" },
  { label: "Recruiting", to: "/recruiting", gotoKey: "r" },
  { label: "Payroll", to: "/platform/payroll", gotoKey: "y" },
  { label: "Performance", to: "/platform/performance", gotoKey: "f" },
  { label: "Learning", to: "/platform/learning", gotoKey: "n" },
  { label: "Reports", to: "/reports", gotoKey: "e" },
  { label: "Admin", to: "/client-onboarding", gotoKey: "a" },
]

const GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
      { label: "Reports", to: "/reports", icon: PieChart },
      {
        label: "Forecasting",
        to: "/forecasting",
        icon: BarChart3,
        sub: [
          { label: "Demand & drivers", to: "/forecasting/demand" },
          { label: "Scenarios", to: "/forecasting/scenarios" },
          { label: "Accuracy", to: "/forecasting/accuracy" },
        ],
      },
      { label: "Project Status", to: "/project-status", icon: Presentation },
    ],
  },
  {
    label: "Core HR & ESS",
    items: [
      {
        label: "People",
        to: "/people",
        icon: Users,
        sub: [
          { label: "Departments", to: "/people/departments" },
          { label: "Jobs", to: "/people/jobs" },
          { label: "Locations", to: "/people/locations" },
          { label: "Positions", to: "/people/positions" },
          { label: "Cost centres", to: "/people/cost-centers" },
        ],
      },
      { label: "Recruiting", to: "/recruiting", icon: Target },
      { label: "Onboarding", to: "/onboarding", icon: Briefcase },
      { label: "Offboarding", to: "/offboarding", icon: User },
      { label: "Assets", to: "/assets", icon: Briefcase },
      { label: "My Assets", to: "/my-assets", icon: Briefcase },
      { label: "ESS", to: "/ess", icon: User },
      { label: "Core HR", to: "/platform", icon: Building },
      { label: "Benefits", to: "/platform/benefits", icon: Gift },
    ],
  },
  {
    label: "Time & Payroll",
    items: [
      { label: "Time", to: "/time", icon: Clock },
      {
        label: "Scheduling",
        to: "/scheduling",
        icon: Calendar,
        sub: [{ label: "Roster Builder", to: "/scheduling/roster" }],
      },
      {
        label: "Leave",
        to: "/leave",
        icon: Bed,
        sub: [{ label: "Ledger & Reconciliation", to: "/leave/ledger" }],
      },
      {
        label: "Payroll",
        to: "/platform/payroll",
        icon: CreditCard,
        sub: [
          { label: "Pay runs", to: "/platform/payroll/runs" },
          { label: "Pay setup", to: "/platform/payroll/setup" },
          { label: "Payroll overview", to: "/platform/payroll/overview" },
        ],
      },
      { label: "Expenses", to: "/expenses", icon: CreditCard },
    ],
  },
  {
    label: "Platform & Admin",
    items: [
      { label: "Performance", to: "/platform/performance", icon: Star },
      { label: "Learning", to: "/platform/learning", icon: Book },
      { label: "Compliance", to: "/platform/compliance", icon: Shield },
      { label: "Integrations", to: "/platform/integrations", icon: Plug },
      { label: "Data Quality", to: "/data-quality", icon: Activity },
      { label: "Import / Export", to: "/import", icon: RefreshCcw },
      { label: "Background Jobs", to: "/jobs", icon: Settings },
      { label: "Security (MFA)", to: "/mfa", icon: Shield },
      { label: "Break-glass", to: "/admin/break-glass", icon: Shield },
      { label: "Compliance Center", to: "/admin/compliance", icon: Shield },
      { label: "Admin", to: "/client-onboarding", icon: Building },
      { label: "Design System", to: "/design", icon: Palette },
      {
        label: "Theme & Gallery",
        to: "/theme",
        icon: Briefcase,
        sub: [
          { label: "Theme Studio", to: "/theme" },
          { label: "Design Gallery", to: "/design-gallery" },
        ],
      },
    ],
  },
]

/** Light the item on its workspace-relative path. */
function isActivePath(bare: string, to: string): boolean {
  if (to === "/dashboard") return bare.startsWith("/dashboard")
  if (to === "/reports") return bare.startsWith("/reports")
  if (to === "/client-onboarding") return bare.startsWith("/client-onboarding")
  if (to === "/people") {
    // Core HR (locations, cost centres, positions) is people structure.
    return bare.startsWith("/people") || bare === "/platform"
  }
  if (to === "/theme") {
    return bare.startsWith("/theme") || bare.startsWith("/design-gallery")
  }
  return bare.startsWith(to)
}

export function WorkspaceRail() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const { tenant } = useTenant()
  const brandName = tenant?.name || "LibrePeople"
  const [adminOpen, setAdminOpen] = useState(false)
  // Admin routes are global, never tenant-prefixed — use bare path
  const navTo = (p: string) => (p.startsWith("/admin") ? p : tenantNav.to(p))

  // "g + letter" shortcuts — the registrations the old workspace rail owned.
  // Client-side navigation: a full-page reload here loses app state.
  useEffect(() => {
    GOTO_AREAS.forEach((area) => {
      registerGoto(area.gotoKey, {
        label: `Go to ${area.label}`,
        keys: `g ${area.gotoKey}`,
        description: `Navigate to ${area.label}`,
        group: "Navigation",
        run: () => navigate(tenantNav.to(area.to)),
      })
    })
    return () => GOTO_AREAS.forEach((area) => unregisterGoto(area.gotoKey))
  }, [navigate, tenantNav])

  const bare = barePath(pathname)

  const openAdmin = isActiveAdmin(bare)

  return (
    <nav
      aria-label="Workspace"
      className="sidebar-obsidian hidden lg:flex flex-col w-[var(--sidebar-width)] shrink-0 border-r border-[color:var(--border)] bg-[color:var(--bg-shell)] sticky top-[var(--topbar-height)] h-[calc(100vh-var(--topbar-height))] overflow-hidden"
    >
      {/* Brand header */}
      <Link
        to={tenantNav.to("/dashboard")}
        className="flex items-center gap-2.5 px-3 py-2.5 border-b border-[color:var(--border)] shrink-0 hover:bg-[color:var(--surface-hover)] transition-colors"
      >
        {tenant?.logo_url ? (
          <img src={tenant.logo_url} alt="" className="h-7 w-7 rounded-md object-contain" />
        ) : (
          <span className="brand-mark" aria-hidden="true">
            K
          </span>
        )}
        <span className="text-sm font-semibold text-fg truncate">{brandName}</span>
      </Link>

      {/* Scrollable region: CTA + groups */}
      <div className="flex-1 min-h-0 overflow-y-auto px-2 pt-2.5 pb-3">
        {/* "+ Quick Action" — opens the command palette */}
        <button
          type="button"
          onClick={() => window.dispatchEvent(new CustomEvent("karmathy:open-command-palette"))}
          className="quick-action-cta mb-3 inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-semibold shadow-sm"
        >
          + Quick Action
        </button>

        {GROUPS.map((group) => (
          <div key={group.label} className="mb-3">
            <p className="px-2 mb-1 text-[10px] font-semibold uppercase tracking-widest text-fg-muted">
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => (
                <SidebarEntry key={item.to + item.label} item={item} bare={bare} tenantNav={tenantNav} />
              ))}
            </ul>
          </div>
        ))}

        {/* Collapsible Admin console — every /admin/* route, one click away. */}
        <div className="mb-3 border-t border-[color:var(--border)] pt-2">
          <button
            type="button"
            onClick={() => setAdminOpen((v) => !v)}
            aria-expanded={adminOpen}
            className={cn(
              "nav-item w-full text-left text-xs uppercase tracking-widest text-fg-muted hover:text-fg",
              openAdmin && "text-fg"
            )}
          >
            <span className="nav-icon" aria-hidden="true">
              {adminOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </span>
            Admin console
            <span className="ml-auto text-[10px] tabular-nums text-fg-subtle">{ADMIN_ITEMS.length}</span>
          </button>
          {adminOpen && (
            <ul className="mt-0.5 space-y-0.5">
              {ADMIN_ITEMS.map((item) => {
                const active = bare === item.to
                return (
                  <li key={item.to}>
                    <Link
                      to={navTo(item.to)}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "nav-item !py-1.5 pl-8 text-xs",
                        active && "nav-item-active"
                      )}
                    >
                      <span className="flex-1 min-w-0 truncate">{item.label}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>

    </nav>
  )
}

function isActiveAdmin(bare: string): boolean {
  return bare.startsWith("/admin")
}

/**
 * One sidebar entry: a link with optional always-visible sub-links.
 */
function SidebarEntry({
  item,
  bare,
  tenantNav,
}: {
  item: NavItem
  bare: string
  tenantNav: { to: (path: string) => string }
}) {
  const active = isActivePath(bare, item.to)
  const Icon = item.icon
  const resolve = (p: string) => (p.startsWith("/admin") ? p : tenantNav.to(p))

  return (
    <li>
      <Link
        to={resolve(item.to)}
        aria-current={active ? "page" : undefined}
        className={cn("nav-item", active && "nav-item-active")}
      >
        {Icon && (
          <span className="nav-icon" aria-hidden="true">
            <Icon className="w-4 h-4" />
          </span>
        )}
        <span className="flex-1 min-w-0 truncate">{item.label}</span>
      </Link>
      {item.sub && item.sub.length > 0 && (
        <ul className="mt-0.5 mb-1 space-y-0.5">
          {item.sub.map((sub) => {
            const subActive = bare === sub.to
            return (
              <li key={sub.to + sub.label}>
                <Link
                  to={resolve(sub.to)}
                  aria-current={subActive ? "page" : undefined}
                  className={cn("nav-item !py-1.5 pl-9 text-xs", subActive && "nav-item-active")}
                >
                  <span className="flex-1 min-w-0 truncate">{sub.label}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </li>
  )
}
