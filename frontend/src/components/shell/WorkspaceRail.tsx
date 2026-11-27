import { useEffect, useState, type ComponentType } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useTenant } from "@/context/TenantContext"
import { useAuth } from "@/context/AuthContext"
import { registerGoto, unregisterGoto } from "@/lib/keyboard"
import { barePath, useTenantNav } from "@/lib/tenantPath"
import {
  GOTO_ENTRIES,
  visibleAdminGroups,
  visibleSections,
  type NavSection,
} from "@/lib/nav"
import { ChevronDown, ChevronRight } from "lucide-react"

/**
 * Unified 220px sidebar (TradeMarkk obsidian shell).
 *
 * One role-aware IA driven by lib/nav.ts: the visible sections for the
 * current role, plus a collapsible Admin console holding every canonical
 * /admin/* route in named groups (never a flat list). Route paths are the
 * exact App.tsx registrations — aliases live only in App.tsx as guarded
 * Navigate redirects, never in this nav.
 */
export function WorkspaceRail() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const { tenant } = useTenant()
  const { user } = useAuth()
  const brandName = tenant?.name || "LibrePeople"
  const role = user?.role

  const sections = visibleSections(role)
  const adminGroups = visibleAdminGroups(role)
  const adminCount = adminGroups.reduce((n, g) => n + g.items.length, 0)
  const bare = barePath(pathname)

  // Auto-open the console on admin screens.
  const [adminOpen, setAdminOpen] = useState(() => bare.startsWith("/admin"))
  useEffect(() => {
    if (bare.startsWith("/admin")) setAdminOpen(true)
  }, [bare])

  // "g + letter" shortcuts — registered for the sections (and historic
  // sub-screens) this role may see. Client-side navigation: a full-page
  // reload here loses app state.
  useEffect(() => {
    const mine = GOTO_ENTRIES.filter(
      (e) =>
        sections.some((s) => s.to === e.to) ||
        e.to === "/scheduling" ||
        e.to === "/forecasting"
    )
    mine.forEach((entry) => {
      registerGoto(entry.gKey, {
        label: `Go to ${entry.label}`,
        keys: `g ${entry.gKey}`,
        description: `Navigate to ${entry.label}`,
        group: "Navigation",
        run: () => navigate(tenantNav.to(entry.to)),
      })
    })
    return () => mine.forEach((entry) => unregisterGoto(entry.gKey))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate, tenantNav, role])

  // Admin routes are global, never tenant-prefixed — use bare path
  const navTo = (p: string) => (p.startsWith("/admin") ? p : tenantNav.to(p))

  return (
    <nav
      aria-label="Workspace"
      className="sidebar-obsidian hidden lg:flex flex-col w-[var(--sidebar-width)] shrink-0 border-r border-[color:var(--border)] bg-[color:var(--bg-shell)] sticky top-[var(--topbar-height)] h-[calc(100vh-var(--topbar-height)] overflow-hidden"
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

      {/* Scrollable region: CTA + sections */}
      <div className="flex-1 min-h-0 overflow-y-auto px-2 pt-2.5 pb-3">
        {/* "+ Quick Action" — opens the command palette */}
        <button
          type="button"
          onClick={() => window.dispatchEvent(new CustomEvent("karmathy:open-command-palette"))}
          className="quick-action-cta mb-3 inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-semibold shadow-sm"
        >
          + Quick Action
        </button>

        {sections.map((section) => (
          <div key={section.section} className="mb-3">
            <ul className="space-y-0.5">
              <SidebarEntry item={section} bare={bare} tenantNav={tenantNav} />
            </ul>
          </div>
        ))}

        {/* Collapsible Admin console — every canonical /admin/* route, in
            named groups, one click away. Hidden when the role sees none. */}
        {adminGroups.length > 0 && (
          <div className="mb-3 border-t border-[color:var(--border)] pt-2">
            <button
              type="button"
              onClick={() => setAdminOpen((v) => !v)}
              aria-expanded={adminOpen}
              className={cn(
                "nav-item w-full text-left text-xs uppercase tracking-widest text-fg-muted hover:text-fg",
                bare.startsWith("/admin") && "text-fg"
              )}
            >
              <span className="nav-icon" aria-hidden="true">
                {adminOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              </span>
              Admin console
              <span className="ml-auto text-[10px] tabular-nums text-fg-subtle">{adminCount}</span>
            </button>
            {adminOpen && (
              <div className="mt-0.5 space-y-2">
                {adminGroups.map((group) => (
                  <div key={group.name}>
                    <p className="px-2 mb-0.5 text-[10px] font-semibold uppercase tracking-widest text-fg-muted">
                      {group.name}
                    </p>
                    <ul className="space-y-0.5">
                      {group.items.map((item) => {
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
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

    </nav>
  )
}

/** Light the item on its workspace-relative path (section or any sub). */
function isActivePath(bare: string, section: NavSection): boolean {
  if (bare === section.to || bare.startsWith(`${section.to}/`)) return true
  return (section.sub ?? []).some(
    (sub) => bare === sub.to || bare.startsWith(`${sub.to}/`)
  )
}

/**
 * One sidebar entry: a section link with optional always-visible sub-links.
 */
function SidebarEntry({
  item,
  bare,
  tenantNav,
}: {
  item: NavSection
  bare: string
  tenantNav: { to: (path: string) => string }
}) {
  const active = isActivePath(bare, item)
  const Icon = item.icon as ComponentType<{ className?: string }>
  const resolve = (p: string) => (p.startsWith("/admin") ? p : tenantNav.to(p))

  return (
    <li>
      <Link
        to={resolve(item.to)}
        aria-current={active ? "page" : undefined}
        className={cn("nav-item", active && "nav-item-active")}
      >
        <span className="nav-icon" aria-hidden="true">
          <Icon className="w-4 h-4" />
        </span>
        <span className="flex-1 min-w-0 truncate">{item.label}</span>
      </Link>
      {item.sub && item.sub.length > 0 && (
        <ul className="mt-0.5 mb-1 space-y-0.5">
          {item.sub.map((sub) => {
            const subActive = bare === sub.to || bare.startsWith(`${sub.to}/`)
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
