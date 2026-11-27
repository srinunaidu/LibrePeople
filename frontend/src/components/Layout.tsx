import { createContext, useContext, useEffect, useRef, useState, type ComponentType, type ReactNode, type SVGProps } from "react"
import { Link, useLocation } from "react-router-dom"
import { useTenant } from "@/context/TenantContext"
import { barePath, useTenantNav } from "@/lib/tenantPath"
import { WorkspaceRail } from "@/components/shell/WorkspaceRail"
import { TopBar } from "@/components/shell/TopBar"
import { CommandPalette } from "@/components/shell/CommandPalette"
import { ShortcutHelp } from "@/components/shell/ShortcutHelp"
import { registerShortcuts } from "@/lib/keyboard"
import { MobileBottomNav } from "@/components/ui/mobile-bottom-nav"
import { ErrorBoundary } from "@/components/ui/ErrorBoundary"

export const LayoutContext = createContext(false)
import {
  Activity,
  BarChart3,
  Bed,
  Book,
  Building,
  Calendar,
  Clock,
  CreditCard,
  FileText,
  Gift,
  LayoutDashboard,
  Palette,
  PieChart,
  Plug,
  Presentation,
  RefreshCcw,
  Settings,
  Sliders,
  Star,
  Target,
  User,
  UserCircle,
  Users,
  X,
} from "lucide-react"

interface BreadcrumbItem {
  label: string
  href?: string
}

/**
 * Application shell.
 *
 * Children are rendered ONCE inside a single <main>. The desktop sidebar and
 * mobile drawer are toggled via CSS (hidden/block) so there is never a
 * duplicate set of inputs, state, or IDs.
 * Nested Layout collapses via LayoutContext to avoid double sidebar/TopBar.
 */
export function Layout({ children }: { children: ReactNode }) {
  const insideLayout = useContext(LayoutContext)
  if (insideLayout) {
    return <ErrorBoundary>{children}</ErrorBoundary>
  }
  const { pathname } = useLocation()
  const { themeError } = useTenant()
  const tenantNav = useTenantNav()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const drawerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    registerShortcuts()
  }, [])

  useEffect(() => {
    setDrawerOpen(false)
  }, [pathname])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawerOpen(false)
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [])

  // Reveal-on-scroll for `.mk-reveal` elements inside the current page.
  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>(".mk-reveal"))
    if (els.length === 0) return
    if (!("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("mk-in"))
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add("mk-in")
            io.unobserve(e.target)
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [pathname])

  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : ""
    return () => {
      document.body.style.overflow = ""
    }
  }, [drawerOpen])

  // Breadcrumb matching runs on the bare path (single-tenant: no scope).
  const breadcrumbItems = getBreadcrumbItems(barePath(pathname), tenantNav)

  // Mobile navigation drawer items. Icons are lucide-react (2px stroke) — no
  // emoji anywhere in the drawer, so the shell stays on-brand at small sizes.
  // Admin routes are global — never tenant-prefixed.
  const adminAwareTo = (p: string) => (p.startsWith("/admin") ? p : tenantNav.to(p))
  const drawerItems = [
    { to: tenantNav.to("/dashboard"), label: "Dashboard", Icon: LayoutDashboard },
    { to: tenantNav.to("/people"), label: "People", Icon: Users },
    { to: tenantNav.to("/time"), label: "Time & Attendance", Icon: Clock },
    { to: tenantNav.to("/scheduling"), label: "Scheduling", Icon: Calendar },
    { to: tenantNav.to("/forecasting"), label: "Forecast", Icon: BarChart3 },
    { to: tenantNav.to("/leave"), label: "Leave", Icon: Bed },
    { to: tenantNav.to("/leave/ledger"), label: "Leave Ledger", Icon: FileText },
    { to: tenantNav.to("/recruiting"), label: "Recruiting", Icon: Target },
    { to: tenantNav.to("/onboarding-config"), label: "Onboarding Config", Icon: Settings },
    { to: tenantNav.to("/platform/payroll"), label: "Payroll", Icon: CreditCard },
    { to: tenantNav.to("/platform/payroll/runs"), label: "Pay runs", Icon: FileText },
    { to: tenantNav.to("/platform/payroll/setup"), label: "Pay setup", Icon: Sliders },
    { to: tenantNav.to("/platform/benefits"), label: "Benefits", Icon: Gift },
    { to: tenantNav.to("/platform/learning"), label: "Learning", Icon: Book },
    { to: tenantNav.to("/platform/performance"), label: "Performance", Icon: Star },
    { to: tenantNav.to("/ess"), label: "Employee Self-Service", Icon: User },
    { to: tenantNav.to("/reports"), label: "Reports", Icon: PieChart },
    { to: tenantNav.to("/project-status"), label: "Project Status", Icon: Presentation },
    { to: tenantNav.to("/platform/integrations"), label: "Integrations", Icon: Plug },
    { to: tenantNav.to("/data-quality"), label: "Data Quality", Icon: Activity },
    { to: adminAwareTo("/admin/users"), label: "User Admin", Icon: UserCircle },
    { to: tenantNav.to("/import"), label: "Import / Export", Icon: RefreshCcw },
    { to: tenantNav.to("/client-onboarding"), label: "Admin", Icon: Building },
    { to: tenantNav.to("/design"), label: "Design System", Icon: Palette },
  ] as const

  const bottomNavItems = [
    { label: "Home", icon: <LayoutDashboard strokeWidth={2} aria-hidden="true" />, href: tenantNav.to("/dashboard") },
    { label: "People", icon: <Users strokeWidth={2} aria-hidden="true" />, href: tenantNav.to("/people") },
    { label: "Time", icon: <Clock strokeWidth={2} aria-hidden="true" />, href: tenantNav.to("/time") },
    { label: "Leave", icon: <Bed strokeWidth={2} aria-hidden="true" />, href: tenantNav.to("/leave") },
    { label: "More", icon: <Settings strokeWidth={2} aria-hidden="true" />, href: tenantNav.to("/platform") },
  ]

  return (
    <LayoutContext.Provider value={true}>
      <div className="min-h-screen bg-[color:var(--bg-canvas)]">
        <a href="#main-content" className="skip-link" aria-label="Skip to main content">
          Skip to main content
        </a>

        {/* Top bar — always visible, 48px */}
        <div className="sticky top-0 z-40">
          <TopBar onOpenDrawer={() => setDrawerOpen(true)} breadcrumbItems={breadcrumbItems} />
        </div>

        {/* Single content row: the unified 220px sidebar (desktop only) + main */}
        <div className="flex">
          <WorkspaceRail />

          <main id="main-content" tabIndex={-1} className="flex-1 min-w-0 bg-[color:var(--bg-canvas)] px-4 py-4 sm:px-6 sm:py-6 lg:px-6 lg:py-6 pb-20 lg:pb-6 overflow-x-hidden">
            <div className="max-w-container mx-auto flex flex-col gap-4">
              {themeError && (
                <div className="alert alert-info mb-4" role="status">
                  {themeError}
                </div>
              )}

              <ErrorBoundary>{children}</ErrorBoundary>
            </div>
          </main>
        </div>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div
            className="absolute inset-0 bg-[rgba(2,6,23,0.5)] backdrop-blur-sm"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
          <nav
            ref={drawerRef}
            aria-label="Mobile navigation"
            className="absolute inset-y-0 left-0 w-72 max-w-[85vw] bg-surface shadow-2xl overflow-y-auto"
          >
            <div className="flex items-center justify-between px-4 py-4 border-b border-border sticky top-0 bg-surface z-10">
              <span className="font-bold text-fg">Navigate</span>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="p-2 rounded-lg text-fg-muted hover:bg-surface-hover"
                aria-label="Close navigation"
              >
                <X className="w-5 h-5" strokeWidth={2} aria-hidden="true" />
              </button>
            </div>
            <div className="p-4 space-y-1">
              {drawerItems.map(({ to, label, Icon: IconComp }) => (
                <MobileDrawerLink key={to} to={to} label={label} IconComp={IconComp} onClick={() => setDrawerOpen(false)} />
              ))}
            </div>
          </nav>
        </div>
      )}

      {/* Mobile bottom nav for primary actions.
          There used to be a second fixed bar here (`MobileBar`), rendered at
          the same `bottom-0` with four of the same links. Two stacked bars
          covered 202px of a 360x900 screen while `main` reserved 80px, so the
          end of every page was unreachable. One bar, one row. */}
      <MobileBottomNav items={bottomNavItems} />

      {/* Overlays */}
      <CommandPalette />
      <ShortcutHelp />
      </div>
    </LayoutContext.Provider>
  )
}

function MobileDrawerLink({
  to,
  label,
  IconComp,
  onClick,
}: {
  to: string
  label: string
  IconComp: ComponentType<SVGProps<SVGSVGElement>>
  onClick: () => void
}) {
  // Client-side navigation: a full-page reload here loses app state.
  return (
    <Link
      to={to}
      onClick={onClick}
      className="flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-lg text-sm font-medium text-fg hover:bg-surface-hover transition-colors"
    >
      <IconComp className="w-5 h-5" strokeWidth={2} aria-hidden="true" />
      {label}
    </Link>
  )
}

/**
 * Breadcrumb items for a bare pathname (single-tenant: no scope).
 */
function getBreadcrumbItems(
  pathname: string,
  tenantNav: { to: (path: string) => string },
): BreadcrumbItem[] {
  return breadcrumbItemsFor(pathname).map((item) => ({
    ...item,
    href: item.href ? tenantNav.to(item.href) : undefined,
  }))
}

/** Builds breadcrumb items for a workspace-relative (bare) pathname. */
function breadcrumbItemsFor(pathname: string): BreadcrumbItem[] {
  const items: BreadcrumbItem[] = [{ label: "Home", href: "/dashboard" }]

  if (pathname.startsWith("/dashboard")) {
    return items
  }

  if (pathname.startsWith("/people")) {
    items.push({ label: "People", href: "/people" })
    if (pathname === "/people/departments") items.push({ label: "Departments" })
    else if (pathname === "/people/jobs") items.push({ label: "Jobs" })
    else if (pathname === "/people/locations") items.push({ label: "Locations" })
    else if (pathname !== "/people") items.push({ label: pathname.split("/").pop() || "Details" })
    return items
  }

  if (pathname.startsWith("/platform/payroll")) {
    items.push({ label: "Payroll", href: "/platform/payroll" })
    return items
  }

  if (pathname.startsWith("/platform/performance")) {
    items.push({ label: "Performance", href: "/platform/performance" })
    return items
  }

  if (pathname.startsWith("/platform/benefits")) {
    items.push({ label: "Benefits", href: "/platform/benefits" })
    return items
  }

  if (pathname.startsWith("/platform/learning")) {
    items.push({ label: "Learning", href: "/platform/learning" })
    return items
  }

  if (pathname.startsWith("/ess")) {
    items.push({ label: "Employee Self-Service", href: "/ess" })
    return items
  }

  if (pathname.startsWith("/platform/compliance")) {
    items.push({ label: "Compliance", href: "/platform/compliance" })
    return items
  }

  if (pathname.startsWith("/platform/integrations")) {
    items.push({ label: "Integrations", href: "/platform/integrations" })
    return items
  }

  if (pathname.startsWith("/platform/users") || pathname.startsWith("/admin/users")) {
    items.push({ label: "User Admin", href: "/admin/users" })
    return items
  }

  if (pathname.startsWith("/platform")) {
    items.push({ label: "Core HR", href: "/platform" })
    return items
  }

  if (pathname.startsWith("/data-quality")) {
    items.push({ label: "Data Quality", href: "/data-quality" })
    return items
  }

  if (pathname.startsWith("/admin")) {
    items.push({ label: "Admin", href: "/admin/users" })
    return items
  }

  if (pathname.startsWith("/time") || pathname.startsWith("/scheduling")) {
    items.push({ label: "Time", href: "/time" })
    if (pathname === "/scheduling/roster") {
      items.push({ label: "Scheduling", href: "/scheduling" })
      items.push({ label: "Roster Builder" })
    } else if (pathname.startsWith("/scheduling")) {
      items.push({ label: "Scheduling", href: "/scheduling" })
    }
    return items
  }

  if (pathname.startsWith("/forecasting")) {
    items.push({ label: "Forecast", href: "/forecasting" })
    if (pathname === "/forecasting/demand") items.push({ label: "Demand & drivers" })
    else if (pathname === "/forecasting/scenarios") items.push({ label: "Scenarios" })
    else if (pathname === "/forecasting/accuracy") items.push({ label: "Accuracy" })
    else if (pathname.startsWith("/forecasting/runs/")) items.push({ label: "Run" })
    return items
  }

  if (pathname.startsWith("/leave")) {
    items.push({ label: "Leave", href: "/leave" })
    if (pathname.startsWith("/leave/ledger")) items.push({ label: "Ledger & Reconciliation" })
    return items
  }

  if (pathname.startsWith("/onboarding-config")) {
    items.push({ label: "Hiring", href: "/recruiting" })
    items.push({ label: "Onboarding Config", href: "/onboarding-config" })
    return items
  }

  if (pathname.startsWith("/recruiting") || pathname.startsWith("/onboarding") || pathname.startsWith("/offboarding")) {
    items.push({ label: "Hiring", href: "/recruiting" })
    if (pathname.startsWith("/onboarding")) items.push({ label: "Onboarding" })
    else if (pathname.startsWith("/offboarding")) items.push({ label: "Offboarding" })
    return items
  }

  if (pathname.startsWith("/reports")) {
    items.push({ label: "Analytics", href: "/reports" })
    return items
  }

  if (pathname.startsWith("/client-onboarding")) {
    items.push({ label: "Admin", href: "/client-onboarding" })
    return items
  }

  if (pathname.startsWith("/import")) {
    items.push({ label: "Import / Export", href: "/import" })
    return items
  }

  if (pathname.startsWith("/jobs")) {
    items.push({ label: "Background Jobs", href: "/jobs" })
    return items
  }

  if (pathname.startsWith("/mfa")) {
    items.push({ label: "Security (MFA)", href: "/mfa" })
    return items
  }

  if (pathname.startsWith("/design")) {
    items.push({ label: "Design System", href: "/design" })
    return items
  }

  return items
}
