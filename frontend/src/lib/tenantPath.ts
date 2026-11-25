/**
 * Tenant-scope-aware navigation helpers.
 *
 * The app supports tenant workspaces at `/t/:slug/...` (Render free tier
 * has no subdomains, so the path-based fallback is what production uses).
 * Every navigation that hardcodes `/dashboard`, `/people`, ... silently
 * drops a tenant-scoped user OUT of their workspace — the route exists,
 * but the tenant context (branding, and any tenant-scoped behaviour) is
 * lost, and the user reads it as "the menu redirects me somewhere wrong".
 *
 * `useTenantNav()` resolves a workspace-relative target into the correct
 * absolute path for the current URL. Use it for every link built inside
 * the app shell (rail, drawer, bottom bar, breadcrumbs, command palette).
 */
import { useLocation } from "react-router-dom"

/** "/t/acme/people" -> "/t/acme"; global paths -> null. */
export function tenantPrefixFrom(pathname: string): string | null {
  const match = pathname.match(/^\/t\/([^/]+)/)
  return match ? `/t/${match[1]}` : null
}

/** "/t/acme/people" -> "/people"; leaves global paths untouched. */
export function barePath(pathname: string): string {
  const prefix = tenantPrefixFrom(pathname)
  return prefix ? pathname.slice(prefix.length) || "/" : pathname
}

/**
 * Hook: resolves workspace-relative targets ("/people") against the
 * current URL's tenant scope. On global pages it returns the path as-is.
 * Admin routes are never tenant-prefixed (/admin/* is global).
 */
export function useTenantNav(): { to: (path: string) => string } {
  const { pathname } = useLocation()
  const prefix = tenantPrefixFrom(pathname)
  return {
    to: (path: string) => {
      if (path.startsWith("/admin")) return path
      return prefix && path.startsWith("/") ? `${prefix}${path}` : path
    },
  }
}

/** Helper for non-hook contexts */
export function resolveTenantPath(pathname: string, path: string): string {
  if (path.startsWith("/admin")) return path
  const prefix = tenantPrefixFrom(pathname)
  return prefix && path.startsWith("/") ? `${prefix}${path}` : path
}
