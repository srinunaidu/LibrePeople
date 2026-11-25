import { useState } from "react"

export interface UseErrorReturn {
  showErrorBox: (message: string, title?: string) => void
  showSonnerError: (message: string) => void
  error: string | null
  setError: React.Dispatch<React.SetStateAction<string | null>>
}

export function useError(): UseErrorReturn {
  const [error, setError] = useState<string | null>(null)

  const showErrorBox = (message: string, title = "Error") => {
    setError(message)
  }

  const showSonnerError = (message: string) => {
    console.error(message)
  }

  return {
    showErrorBox,
    showSonnerError,
    error,
    setError,
  }
}