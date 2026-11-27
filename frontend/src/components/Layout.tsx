import { createContext, useContext, useEffect, useRef, useState, type ComponentType, type ReactNode, type SVGProps } from "react"
import { Link, useLocation } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { barePath, useTenantNav } from "@/lib/tenantPath"
import {
  bottomNavSections,
  breadcrumbFor,
  visibleAdminGroups,
  visibleSections,
} from "@/lib/nav"
import { WorkspaceRail } from "@/components/shell/WorkspaceRail"
import { TopBar } from "@/components/shell/TopBar"
import { CommandPalette } from "@/components/shell/CommandPalette"
import { ShortcutHelp } from "@/components/shell/ShortcutHelp"
import { registerShortcuts } from "@/lib/keyboard"
import { MobileBottomNav } from "@/components/ui/mobile-bottom-nav"
import { ErrorBoundary } from "@/components/ui/ErrorBoundary"

export const LayoutContext = createContext(false)
import {
  X,
} from "lucide-react"

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
  const { user } = useAuth()
  const tenantNav = useTenantNav()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const drawerRef = useRef<HTMLDivElement>(null)
  const role = user?.role

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
  // Trails come from the nav config so new sections appear automatically.
  const breadcrumbItems = breadcrumbFor(barePath(pathname)).map((item) => ({
    ...item,
    href: item.href ? tenantNav.to(item.href) : undefined,
  }))

  // Mobile navigation drawer + bottom bar, both driven by lib/nav.ts for the
  // current role (<lg only; the rail serves lg+). One bottom bar, max 5
  // items, lowest bottomNavPriority first.
  const adminAwareTo = (p: string) => (p.startsWith("/admin") ? p : tenantNav.to(p))
  const drawerSections = visibleSections(role)
  const drawerAdminGroups = visibleAdminGroups(role)

  const bottomNavItems = bottomNavSections(role).map((s) => {
    const Icon = s.icon
    return {
      label: s.section === "time" ? "Time" : s.label,
      icon: <Icon className="w-5 h-5" aria-hidden="true" />,
      href: adminAwareTo(s.to),
    }
  })

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
              {drawerSections.map((section) => {
                const SectionIcon = section.icon
                return (
                  <div key={section.section}>
                    <MobileDrawerLink
                      to={adminAwareTo(section.to)}
                      label={section.label}
                      IconComp={SectionIcon}
                      onClick={() => setDrawerOpen(false)}
                    />
                    {(section.sub ?? []).map((sub) => (
                      <Link
                        key={sub.to}
                        to={adminAwareTo(sub.to)}
                        onClick={() => setDrawerOpen(false)}
                        className="flex items-center gap-3 w-full text-left pl-11 pr-3 py-2 rounded-lg text-sm text-fg-muted hover:bg-surface-hover hover:text-fg transition-colors"
                      >
                        {sub.label}
                      </Link>
                    ))}
                  </div>
                )
              })}
              {drawerAdminGroups.map((group) => (
                <div key={group.name}>
                  <p className="px-3 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-widest text-fg-muted">
                    {group.name}
                  </p>
                  {group.items.map((item) => (
                    <MobileDrawerLink
                      key={item.to}
                      to={adminAwareTo(item.to)}
                      label={item.label}
                      IconComp={group.icon}
                      onClick={() => setDrawerOpen(false)}
                    />
                  ))}
                </div>
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

