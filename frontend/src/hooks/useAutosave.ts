import { useEffect, useRef, useCallback, useState } from "react"

export function useAutosave<T>(
  key: string,
  data: T,
  delay = 800,
): { savedAt: number | null; restore: () => T | null; clear: () => void } {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [savedAt, setSavedAt] = useState<number | null>(null)

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      try {
        localStorage.setItem(key, JSON.stringify({ data, savedAt: Date.now() }))
        setSavedAt(Date.now())
      } catch {
        // storage full or unavailable — ignore
      }
    }, delay)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [key, data, delay])

  const restore = useCallback((): T | null => {
    try {
      const raw = localStorage.getItem(key)
      if (!raw) return null
      const parsed = JSON.parse(raw)
      return parsed.data as T
    } catch {
      return null
    }
  }, [key])

  const clear = useCallback(() => {
    try {
      localStorage.removeItem(key)
      setSavedAt(null)
    } catch {
      // ignore
    }
  }, [key])

  return { savedAt, restore, clear }
}

export function useAutosaveRestore<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    return JSON.parse(raw).data as T
  } catch {
    return null
  }
}
