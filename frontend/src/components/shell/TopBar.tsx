import { useEffect, useRef, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import { useTenantNav } from "@/lib/tenantPath"
import { ThemeToggle } from "./ThemeToggle"
import { IconLogout, IconMenu, IconSearch } from "@/components/icons"
import { cn } from "@/lib/utils"
import { showSuccess } from "@/components/ui"

export interface TopBarBreadcrumbItem {
  label: string
  href?: string
}

/**
 * Compact top bar (48px — var(--topbar-height)).
 *
 * Breadcrumb/page title on the left, a ⌘K trigger that opens the command
 * palette (the same `karmathy:open-command-palette` CustomEvent the
 * keyboard shortcut and the sidebar CTA dispatch), theme toggle, and a
 * compact user/role badge. On mobile the menu collapses into the drawer
 * handled by Layout.
 */
export function TopBar({
  onOpenDrawer,
  breadcrumbItems,
}: {
  onOpenDrawer: () => void
  breadcrumbItems: TopBarBreadcrumbItem[]
}) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false)
    }
    document.addEventListener("mousedown", onDown)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onDown)
      document.removeEventListener("keydown", onKey)
    }
  }, [])

  const initials = (user?.username || "U").slice(0, 2).toUpperCase()
  const role = user?.role || "—"
  const title = breadcrumbItems[breadcrumbItems.length - 1]?.label ?? "Home"
  const { isImpersonating, originalUser, exitImpersonation } = useAuth()

  return (
    <>
      {isImpersonating && originalUser && (
        <div
          role="status"
          aria-live="polite"
          data-testid="impersonation-banner"
          className="sticky top-0 z-[45] flex items-center justify-center gap-3 border-b border-[var(--warning-border)] bg-[var(--warning-light)] px-4 py-2 text-sm font-medium text-[var(--warning-text)] shadow"
        >
          <span>
            Impersonating <strong>{user?.username}</strong> ({user?.role}) as <strong>{originalUser.username}</strong> — actions are audited
          </span>
          <button
            type="button"
            data-testid="exit-impersonation"
            onClick={() => {
              exitImpersonation()
              showSuccess("Exited impersonation")
              navigate(tenantNav.to("/dashboard"))
            }}
            className="rounded bg-white px-3 py-1 text-xs font-semibold text-warning-text hover:bg-surface-inset"
          >
            Exit impersonation
          </button>
        </div>
      )}
      <header className="app-header shell-obsidian sticky top-0 z-40 border-b border-[color:var(--border)] bg-[color:var(--bg-shell)]">
      <div className="flex h-[var(--topbar-height)] items-center gap-2 px-3 sm:px-4 lg:px-4">
        {/* Mobile drawer trigger */}
        <button
          type="button"
          onClick={onOpenDrawer}
          className="lg:hidden -ml-1 p-2 rounded-lg text-fg-muted hover:bg-surface-hover hover:text-fg w-9 h-9 flex items-center justify-center shrink-0"
          aria-label="Open navigation"
        >
          <IconMenu className="w-5 h-5" />
        </button>

        {/* Breadcrumb / page title */}
        <div className="min-w-0 flex-1">
          <nav aria-label="Breadcrumb" className="hidden sm:block min-w-0">
            <ol className="flex items-center gap-1.5 text-xs min-w-0">
              {breadcrumbItems.map((item, index) => {
                const isLast = index === breadcrumbItems.length - 1
                return (
                  <li key={`${item.label}-${index}`} className="flex items-center gap-1.5 min-w-0">
                    {index > 0 && (
                      <span aria-hidden="true" className="text-fg-subtle">
                        /
                      </span>
                    )}
                    {item.href && !isLast ? (
                      <Link
                        to={item.href}
                        className="text-fg-muted hover:text-fg transition-colors truncate"
                      >
                        {item.label}
                      </Link>
                    ) : (
                      <span
                        aria-current={isLast ? "page" : undefined}
                        className={cn("truncate", isLast ? "text-fg font-medium" : "text-fg-muted")}
                      >
                        {item.label}
                      </span>
                    )}
                  </li>
                )
              })}
            </ol>
          </nav>
          {/* Mobile: page title only */}
          <span className="sm:hidden block truncate text-sm font-semibold text-fg">{title}</span>
        </div>

        {/* ⌘K trigger — same CustomEvent channel as the keyboard shortcut */}
        <button
          type="button"
          onClick={() => window.dispatchEvent(new CustomEvent("karmathy:open-command-palette"))}
          className="shell-obsidian flex items-center gap-2 h-9 rounded-md border border-[color:var(--border)] bg-[color:var(--bg-input)] px-2.5 text-xs text-fg-muted hover:bg-[color:var(--surface-hover)] hover:border-[color:var(--border-strong)] transition-colors shrink-0"
        >
          <IconSearch className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span className="hidden md:inline">Search</span>
          <kbd className="hidden md:inline-flex items-center rounded border border-[color:var(--border)] px-1 py-0.5 text-[10px] font-medium text-fg-muted">
            ⌘K
          </kbd>
        </button>

        {/* Theme toggle (compact) */}
        <ThemeToggle className="w-9 h-9" />

        {/* Compact user / role badge */}
        <div className="relative shrink-0" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            aria-expanded={menuOpen}
            aria-haspopup="menu"
            className="flex items-center gap-2 rounded-full pl-1 pr-2 h-9 hover:bg-surface-hover"
          >
            <span className="avatar !w-7 !h-7" aria-hidden="true">
              {initials}
            </span>
            <span className="hidden md:block text-xs font-medium text-fg max-w-[110px] truncate">
              {user?.username || "User"}
            </span>
            <span className="badge badge-slate !px-1.5 !text-[10px] hidden sm:inline-flex">{role}</span>
          </button>

          {menuOpen && (
            <div
              role="menu"
              className="absolute right-0 mt-2 w-56 origin-top-right rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-1.5 shadow-lg"
            >
              <div className="px-3 py-2 border-b border-[color:var(--border)] mb-1">
                <p className="text-xs font-semibold text-fg truncate">{user?.username || "User"}</p>
                <p className="text-xs text-fg-muted">{role}</p>
              </div>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false)
                  navigate(tenantNav.to("/design"))
                }}
                className="w-full text-left px-3 py-2 text-xs rounded-md text-fg hover:bg-surface-hover flex items-center gap-2"
              >
                <IconSearch className="w-3.5 h-3.5 text-fg-muted" />
                Design System
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false)
                  window.dispatchEvent(new CustomEvent("karmathy:open-shortcut-help"))
                }}
                className="w-full text-left px-3 py-2 text-xs rounded-md text-fg hover:bg-surface-hover flex items-center gap-2"
              >
                <IconSearch className="w-3.5 h-3.5 text-fg-muted" />
                Keyboard Shortcuts
              </button>
              <div className="border-t border-[color:var(--border)] my-1" />
              <button
                type="button"
                role="menuitem"
                onClick={logout}
                className="w-full text-left px-3 py-2 text-xs rounded-md text-error-text hover:bg-error-light flex items-center gap-2"
              >
                <IconLogout className="w-3.5 h-3.5" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
    </>
  )
}
