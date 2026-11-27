import { useEffect, useState } from "react"
import { getClientIdBySlug } from "@/lib/api"

/**
 * Shared hook for admin pages that need the install's single company ID.
 * Single-tenant: resolves once via GET /company (no slug state).
 * Future admin pages should use this instead of duplicating resolution logic.
 */
export function useClientId() {
  const [clientId, setClientId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getClientIdBySlug()
      .then((id) => {
        if (cancelled) return
        if (id === null) {
          setError("Could not resolve the company. Check the server connection.")
        } else {
          setClientId(id)
          setError(null)
        }
      })
      .catch(() => {
        if (!cancelled) setError("Could not resolve the company. Check the server connection.")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { clientId, loading, error }
}
