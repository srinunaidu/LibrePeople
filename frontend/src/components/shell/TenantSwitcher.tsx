import { useEffect, useRef, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { useTenant } from "@/context/TenantContext"
import { listClients, type ClientOut } from "@/lib/api"
import { barePath } from "@/lib/tenantPath"
import { queryClient } from "@/lib/queryClient"
import { IconCheck, IconChevronDown, IconGlobe, IconX } from "@/components/icons"
import { cn } from "@/lib/utils"

/**
 * TenantSwitcher — pinned to the bottom of the unified sidebar.
 *
 * Lists the workspaces the signed-in account can reach (listClients()),
 * shows the active tenant slug (useTenant), and offers the default
 * (no-slug) workspace. Selecting a tenant keeps the current sub-route
 * where that route exists inside /t/:scope, otherwise it lands on
 * /t/:slug/dashboard. The shared queryClient is invalidated on switch so
 * no tenant-A data survives into tenant B.
 */

/** Top-level routes registered under /t/:slug/* in App.tsx. A sub-route
 * outside this set (e.g. /admin/*) has no tenant-scoped registration, so
 * preserving it would hit the catch-all; those land on /dashboard. */
const TENANT_ROUTE_ROOTS = [
  "/dashboard",
  "/people",
  "/recruiting",
  "/onboarding",
  "/time",
  "/scheduling",
  "/leave",
  "/onboarding-config",
  "/offboarding",
  "/reports",
  "/client-onboarding",
  "/platform",
  "/ess",
  "/forecasting",
  "/project-status",
  "/theme",
  "/design-gallery",
  "/data-quality",
  "/import",
  "/jobs",
  "/mfa",
]

function tenantSafeSubRoute(bare: string): string {
  if (bare === "/" || bare === "") return "/dashboard"
  if (TENANT_ROUTE_ROOTS.some((root) => bare === root || bare.startsWith(`${root}/`))) {
    return bare
  }
  return "/dashboard"
}

export function TenantSwitcher() {
  const { tenant } = useTenant()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const [clients, setClients] = useState<ClientOut[] | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let alive = true
    listClients()
      .then((rows) => {
        if (alive) setClients(rows ?? [])
      })
      .catch(() => {
        if (alive) setClients([])
      })
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false)
    }
    document.addEventListener("mousedown", onDown)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onDown)
      document.removeEventListener("keydown", onKey)
    }
  }, [open])

  const currentSlug = tenant?.slug ?? null
  const currentName = tenant?.name ?? "Default workspace"

  const select = (slug: string | null) => {
    setOpen(false)
    if (slug === currentSlug) return
    // A different workspace must not read the previous one's cached data.
    queryClient.invalidateQueries()
    const sub = tenantSafeSubRoute(barePath(pathname))
    navigate(slug ? `/t/${slug}${sub}` : sub)
  }

  // Dedup by slug case-insensitive — prevents "duplicate windows" when API returns
  // duplicate rows or includes a client named "Default workspace".
  const uniqueClients = (() => {
    const map = new Map<string, ClientOut>()
    for (const c of clients ?? []) {
      if (!c.slug) continue
      const key = c.slug.toLowerCase()
      if (!map.has(key)) map.set(key, c)
    }
    return Array.from(map.values())
  })()
  const others = uniqueClients.filter((c) => c.slug.toLowerCase() !== (currentSlug ?? "").toLowerCase())

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={`${currentName} ${currentSlug ? `/${currentSlug}` : "default workspace"} — Workspace: Switch workspace`}
        className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-[color:var(--surface-hover)] transition-colors"
      >
        <IconGlobe className="w-4 h-4 shrink-0 text-fg-muted" aria-hidden="true" />
        <span className="flex-1 min-w-0">
          <span className="block text-xs font-semibold text-fg truncate">{currentName}</span>{" "}
          <span className="block text-xs text-fg-muted truncate">
            {currentSlug ? `/${currentSlug}` : "default workspace"}
          </span>
        </span>
        <IconChevronDown className={cn("w-3.5 h-3.5 shrink-0 text-fg-muted transition-transform", open && "rotate-180")} aria-hidden="true" />
      </button>

      {open && (
        <div
          role="menu"
          aria-label="Workspaces"
          className="absolute bottom-full left-0 right-0 mb-2 max-h-72 overflow-y-auto rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-elevated)] p-1 shadow-lg z-50"
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => select(null)}
            className={cn(
              "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs hover:bg-[color:var(--surface-hover)]",
              !currentSlug && "font-semibold"
            )}
          >
            <span className="flex-1 min-w-0">
              <span className="block text-fg truncate">Default workspace</span>
              <span className="block text-fg-muted">no tenant scope</span>
            </span>
            {!currentSlug && <IconCheck className="w-3.5 h-3.5 text-fg-muted" aria-hidden="true" />}
          </button>

          {uniqueClients.map((client) => (
            <button
              key={client.slug}
              type="button"
              role="menuitem"
              onClick={() => select(client.slug)}
              className={cn(
                "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs hover:bg-[color:var(--surface-hover)]",
                client.slug === currentSlug && "font-semibold"
              )}
            >
              <span className="flex-1 min-w-0">
                <span className="block text-fg truncate">{client.name}</span>
                <span className="block text-fg-muted truncate">/{client.slug}</span>
              </span>
              {client.slug === currentSlug && (
                <IconCheck className="w-3.5 h-3.5 text-fg-muted" aria-hidden="true" />
              )}
            </button>
          ))}

          {clients !== null && others.length === 0 && (
            <p className="px-2 py-1.5 text-xs text-fg-muted flex items-center gap-1.5">
              <IconX className="w-3 h-3" aria-hidden="true" /> No other workspaces available
            </p>
          )}
        </div>
      )}
    </div>
  )
}
