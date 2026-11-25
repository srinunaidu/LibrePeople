import { describe, expect, test, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import React from "react"
import { BrowserRouter } from "react-router-dom"
import { AuthProvider } from "@/context/AuthContext"
import { TenantProvider } from "@/context/TenantContext"
import { ErrorBoundary } from "./ErrorBoundary"
import { Layout } from "@/components/Layout"

// A component that always throws during render
function AlwaysThrows(): never {
  throw new Error("Render error in AlwaysThrows")
}

// A component that throws once, then renders normally after retry
let throwOnce = true

function ThrowOnce() {
  if (throwOnce) {
    throw new Error("First render error")
  }
  return <div data-testid="recovered">Recovered</div>
}

// A simple non-throwing component
function NormalComponent() {
  return <div data-testid="normal">Normal render</div>
}

function renderWithProviders(ui: React.ReactNode) {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <TenantProvider>{ui}</TenantProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

describe("ErrorBoundary", () => {
  beforeEach(() => {
    // happy-dom test environment lacks a global localStorage used by AuthContext
    if (typeof globalThis.localStorage === "undefined") {
      Object.defineProperty(globalThis, "localStorage", {
        value: {
          getItem: vi.fn(() => null),
          setItem: vi.fn(() => {}),
          removeItem: vi.fn(() => {}),
          clear: vi.fn(),
        },
        writable: true,
        configurable: true,
      })
    }
    vi.spyOn(console, "error").mockImplementation(() => {})
  })

  test("throwing child → fallback renders (not blank)", () => {
    renderWithProviders(
      <ErrorBoundary>
        <AlwaysThrows />
      </ErrorBoundary>
    )

    // Fallback should be visible
    expect(screen.getByText("Something went wrong")).toBeInTheDocument()
    expect(screen.getByText("We hit an unexpected error. Try again or reload the page.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /reload page/i })).toBeInTheDocument()
    // The original blank page is prevented
    expect(screen.queryByText("Render error in AlwaysThrows")).not.toBeInTheDocument()
  })

  test("non-throwing child → normal render", () => {
    renderWithProviders(
      <ErrorBoundary>
        <NormalComponent />
      </ErrorBoundary>
    )

    expect(screen.getByTestId("normal")).toBeInTheDocument()
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument()
  })

  test("retry button → re-renders child (resetErrorBoundary)", async () => {
    let throwOnce = true
    const ThrowComp = () => {
      if (throwOnce) {
        throw new Error("First render error")
      }
      return <div data-testid="recovered">Recovered</div>
    }

    renderWithProviders(
      <ErrorBoundary>
        <ThrowComp />
      </ErrorBoundary>
    )

    // First render shows fallback
    expect(screen.getByText("Something went wrong")).toBeInTheDocument()

    throwOnce = false

    // Click retry
    fireEvent.click(screen.getByRole("button", { name: /try again/i }))

    // Wait for the child to recover
    await waitFor(() => expect(screen.getByTestId("recovered")).toBeInTheDocument())
  })

  test("reload button → calls window.location.reload (mocked)", () => {
    const reloadMock = vi.spyOn(window.location, "reload").mockImplementation(() => {})

    renderWithProviders(
      <ErrorBoundary>
        <AlwaysThrows />
      </ErrorBoundary>
    )

    fireEvent.click(screen.getByRole("button", { name: /reload page/i }))

    expect(reloadMock).toHaveBeenCalledTimes(1)
    reloadMock.mockRestore()
  })

  test("accessibility: role=alert, aria-live=polite", () => {
    renderWithProviders(
      <ErrorBoundary>
        <AlwaysThrows />
      </ErrorBoundary>
    )

    const fallback = screen.getByRole("alert")
    expect(fallback).toBeInTheDocument()
    expect(fallback).toHaveAttribute("aria-live", "polite")
  })

  test("componentDidCatch logs error to console", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {})

    renderWithProviders(
      <ErrorBoundary>
        <AlwaysThrows />
      </ErrorBoundary>
    )

    expect(consoleError).toHaveBeenCalledWith(
      "ErrorBoundary caught:",
      expect.any(Error),
      expect.objectContaining({ componentStack: expect.any(String) })
    )
    consoleError.mockRestore()
  })

  test("Layout shell remains visible when route content throws", () => {
    renderWithProviders(
      <Layout>
        <AlwaysThrows />
      </Layout>
    )

    // TopBar should be visible (shell stays intact)
    // TopBar contains "Karmathy" brand or similar
    expect(screen.getByText("Karmathy")).toBeInTheDocument()

    // But the failing route content shows fallback
    expect(screen.getByText("Something went wrong")).toBeInTheDocument()
  })
})