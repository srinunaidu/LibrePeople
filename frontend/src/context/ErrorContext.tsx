import { createContext, useContext, useState, useEffect, ReactNode } from "react"
import { ErrorBox } from "@/components/ui/error-box"

interface ErrorState {
  open: boolean
  message: string
  title: string
  onClose: () => void
}

const ErrorContext = createContext<{
  state: ErrorState
  openError: (message: string, title?: string) => void
  closeError: () => void
} | undefined>(undefined)

export function ErrorProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ErrorState>({
    open: false,
    message: "",
    title: "Error",
    onClose: () => setState({ open: false, message: "", title: "Error", onClose: () => {} }),
  })

  const openError = (message: string, title = "Error") => {
    setState({
      open: true,
      message,
      title,
      onClose: () => setState({ open: false, message: "", title: "Error", onClose: () => {} }),
    })
  }

  const closeError = () => {
    setState({ open: false, message: "", title: "Error", onClose: () => {} })
  }

  useEffect(() => {
    if (state.open) {
      const timeout = setTimeout(
        () =>
          setState({
            open: false,
            message: "",
            title: "Error",
            onClose: () => {},
          }),
        10000,
      )
      return () => clearTimeout(timeout)
    }
  }, [state.open])

  return (
    <ErrorContext.Provider value={{ state, openError, closeError }}>
      {children}
      {state.open && (
        <ErrorBox description={state.message} title={state.title} onClose={state.onClose} />
      )}
    </ErrorContext.Provider>
  )
}

export function useError() {
  const context = useContext(ErrorContext)
  if (!context) {
    return {
      state: { open: false, message: "", title: "Error", onClose: () => {} },
      openError: () => {},
      closeError: () => {},
    }
  }
  return context
}

export { ErrorBox }