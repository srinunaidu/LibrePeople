import { useEffect, useState } from "react"
import { getClientIdBySlug } from "@/lib/api"
import { getTenantSlug } from "@/lib/tenantSlugStore"

/**
 * Shared hook for admin pages that need the current tenant's integer client ID.
 * Handles case-insensitive slug resolution, loading, and error without hanging.
 * Future admin pages should use this instead of duplicating getClientIdBySlug logic.
 */
export function useClientId() {
  const [clientId, setClientId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const slug = getTenantSlug()

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getClientIdBySlug()
      .then((id) => {
        if (cancelled) return
        if (id === null) {
          setError(`Could not resolve tenant: ${slug ?? "—"}. Try switching to default workspace.`)
        } else {
          setClientId(id)
          setError(null)
        }
      })
      .catch(() => {
        if (!cancelled) setError(`Could not resolve tenant: ${slug ?? "—"}. Try switching to default workspace.`)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [slug])

  return { clientId, loading, error, slug }
}
