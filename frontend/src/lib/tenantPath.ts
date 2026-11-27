/**
 * Single-tenant navigation helpers.
 *
 * Single-tenant install: one org, no workspace scopes. `useTenantNav().to()`
 * and `resolveTenantPath()` are identity functions kept so existing call
 * sites keep compiling without a 25-file refactor; they no longer prefix
 * anything. `barePath()` strips a legacy `/t/:slug` prefix for active-state
 * matching and the legacy-URL redirect; `tenantPrefixFrom()` supports it.
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
 * Hook: resolves workspace-relative targets. Single-tenant: returns the path
 * as-is. Admin routes were never tenant-prefixed (/admin/* is global).
 */
export function useTenantNav(): { to: (path: string) => string } {
  useLocation()
  return {
    to: (path: string) => path,
  }
}

/** Helper for non-hook contexts. Single-tenant: identity. */
export function resolveTenantPath(_pathname: string, path: string): string {
  return path
}
