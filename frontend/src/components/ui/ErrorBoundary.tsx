import { Button } from "@/components/ui/button"
import { requestId } from "@/lib/api"
import * as React from "react"

interface ErrorBoundaryState {
  error: Error | null
}

export interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ReactNode
  onError?: (error: Error, info: React.ErrorInfo) => void
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private retryButtonRef = React.createRef<HTMLButtonElement>()

  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo)
    this.props.onError?.(error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ error: null })
  }

  handleReload = () => {
    window.location.reload()
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps, prevState: ErrorBoundaryState) {
    // Move focus to the retry control when the fallback first appears.
    if (prevState.error === null && this.state.error !== null && this.retryButtonRef.current) {
      this.retryButtonRef.current.focus()
    }
  }

  render() {
    const { children, fallback, onError, ...rest } = this.props

    if (this.state.error !== null) {
      if (fallback !== undefined) {
        return fallback
      }

      const rid = requestId(this.state.error) ?? (this.state.error as unknown as { apiError?: { request_id?: string } })?.apiError?.request_id
      return (
        <div
          role="alert"
          aria-live="polite"
          className="mk-card p-8 text-center border border-error-border bg-error-light"
        >
          <span className="icon-tile icon-tile-rose mx-auto mb-4" aria-hidden="true">
            <svg
              className="w-6 h-6"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
              <path d="M12 9v4" />
              <path d="M12 17h.01" />
            </svg>
          </span>
          <h2 className="mk-h2 text-fg mb-2">Something went wrong</h2>
          <p className="max-w-sm mx-auto text-fg-muted mb-6">
            We hit an unexpected error. Try again or reload the page.
          </p>
          {rid && (
            <p className="text-xs font-mono text-fg-muted mb-4" data-testid="request-id">
              Request ID: {rid}
            </p>
          )}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button
              onClick={this.handleRetry}
              ref={this.retryButtonRef}
              className="mk-cta"
            >
              Try again
            </Button>
            <Button
              onClick={this.handleReload}
              variant="outline"
              className="mk-ghost"
            >
              Reload page
            </Button>
          </div>
        </div>
      )
    }

    return <>{children}</>
  }
}
