import { useMemo } from "react"
import { fieldErrors } from "@/lib/api"

/**
 * Hook wrapping fieldErrors() for forms.
 * Returns the map, helpers, and a globalError for the _global bucket.
 */
export function useFieldErrors(err: unknown) {
  const map = useMemo(() => fieldErrors(err), [err])
  const get = (field: string) => map.get(field)
  const has = (field: string) => map.has(field)
  const globalError = map.get("_global") ?? null
  // For pages that need to branch global fallback only when no field matched
  const hasFieldErrors = map.size > 0 && !(map.size === 1 && map.has("_global"))
  return {
    fieldErrors: map,
    getFieldError: get,
    get,
    has,
    hasFieldErrors,
    globalError,
    clearField: (_field: string) => {},
  }
}

export default useFieldErrors
