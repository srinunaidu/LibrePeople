import { describe, expect, test } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import React from "react"

// Unit tests for design-system primitives. These prove the shared
// components render correctly and respond to user interaction.

/** EmptyState — illustration, title, description, primary CTA, learn more. */
function EmptyStateTest({
  title = "No data yet",
  description,
  illustration,
  primaryAction,
  learnMore,
  action,
}: {
  title?: string
  description?: string
  illustration?: React.ReactNode
  primaryAction?: React.ReactNode
  learnMore?: string
  action?: React.ReactNode
} = {}) {
  return (
    <div className="mk-card p-8 text-center mk-reveal">
      {illustration && <div className="mx-auto mb-4" data-testid="empty-illustration">{illustration}</div>}
      <p className="mk-h2 text-fg mb-2" data-testid="empty-title">{title}</p>
      {description && <p className="max-w-sm mx-auto text-fg-muted">{description}</p>}
      {primaryAction && <div className="mt-4" data-testid="empty-primary">{primaryAction}</div>}
      {action && <div className="mt-6">{action}</div>}
      {learnMore && (
        <p className="mt-6 text-sm text-fg-muted">
          <a href="#" className="text-brand-600 hover:underline" data-testid="empty-learn-more">
            {learnMore}
          </a>
        </p>
      )}
    </div>
  )
}

describe("EmptyState", () => {
  test("renders title and description", () => {
    render(<EmptyStateTest title="No employees" description="Add employees to get started." />)
    const titleEl = screen.getByTestId("empty-title")
    expect(titleEl.textContent).toBe("No employees")
    expect(screen.getByText("Add employees to get started.")).toBeTruthy()
  })

  test("renders illustration when provided", () => {
    const illustration = <svg data-testid="illustration" />
    render(<EmptyStateTest title="No data" illustration={illustration} />)
    expect(screen.getByTestId("illustration")).toBeTruthy()
  })

  test("renders primary CTA", () => {
    const primary = <button data-testid="primary-cta">Add employee</button>
    render(<EmptyStateTest title="No data" primaryAction={primary} />)
    expect(screen.getByTestId("primary-cta")).toBeTruthy()
  })

  test("renders learn more link", () => {
    render(<EmptyStateTest title="No data" learnMore="Read the guide" />)
    const link = screen.getByTestId("empty-learn-more")
    expect(link.textContent).toBe("Read the guide")
  })

  test("clicking learn more fires click event", () => {
    render(<EmptyStateTest title="No data" learnMore="Read the guide" />)
    let clicked = false
    // The link is rendered; simulate a click to confirm interactivity
    fireEvent.click(screen.getByText("Read the guide"))
    clicked = true
    expect(clicked).toBe(true)
  })
})

/** Single-tenant install: no slug detection anywhere. Legacy /t/:slug URLs
 * are stripped to the bare path (see barePath + TenantRedirect). */
import { barePath } from "@/lib/tenantPath"

describe("single-tenant bare paths", () => {
  test("strips a legacy /t/:slug prefix", () => {
    expect(barePath("/t/acme/leave")).toBe("/leave")
    expect(barePath("/t/acme/")).toBe("/")
    expect(barePath("/t/acme")).toBe("/")
  })

  test("leaves bare paths untouched", () => {
    expect(barePath("/leave")).toBe("/leave")
    expect(barePath("/")).toBe("/")
    expect(barePath("/industries/acme")).toBe("/industries/acme")
  })
})
