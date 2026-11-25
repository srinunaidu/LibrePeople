import { describe, expect, test, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import { RetryableAlert } from "./feedback"

describe("RetryableAlert", () => {
  test("retry shown when isRetryable and onRetry provided (requestId displayed)", () => {
    const err = {
      response: { status: 500, data: { error: { message: "Server error" } } },
      apiError: { code: "internal_error", category: "server", message: "Server error", retryable: true, request_id: "req-123" },
    }
    const onRetry = vi.fn()
    render(<RetryableAlert err={err} title="The pay runs could not be read" fallback="The pay runs could not be read." onRetry={onRetry} />)
    expect(screen.getByText("The pay runs could not be read")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument()
    expect(screen.getByTestId("request-id")).toHaveTextContent("req-123")
    expect(screen.getByRole("alert")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /retry/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  test("retry hidden when not retryable", () => {
    const err = {
      response: { status: 400, data: { error: { message: "Bad request" } } },
      apiError: { code: "bad_request", category: "client", message: "Bad request", retryable: false, request_id: "req-456" },
    }
    render(<RetryableAlert err={err} title="The pay runs could not be read" fallback="The pay runs could not be read." onRetry={() => {}} />)
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument()
    expect(screen.getByTestId("request-id")).toBeInTheDocument()
  })

  test("network branch shows check connection and retryable", () => {
    const err = { message: "Network Error" } // no response
    const onRetry = vi.fn()
    render(<RetryableAlert err={err} title="The pay runs could not be read" fallback="The pay runs could not be read." onRetry={onRetry} />)
    expect(screen.getByText(/check your connection/i)).toBeInTheDocument()
    // aria-live is on inner span inside alert
    const live = document.querySelector('[aria-live="polite"]')
    expect(live).toBeInTheDocument()
    expect(screen.getByRole("alert")).toBeInTheDocument()
  })

  test("requestId span has data-testid and mono class", () => {
    const err = {
      response: { status: 429, data: { error: { message: "Too many" } } },
      apiError: { code: "rate_limited", category: "client", message: "Too many", retryable: true, request_id: "req-789" },
    }
    render(<RetryableAlert err={err} title="F" fallback="F" onRetry={() => {}} />)
    const span = screen.getByTestId("request-id")
    expect(span).toHaveClass("font-mono")
    expect(span).toHaveClass("text-xs")
  })
})
