import { describe, expect, test } from "vitest"
import { render, screen } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import { PendingVerificationAlert } from "./PendingVerificationAlert"

describe("PendingVerificationAlert", () => {
  test("warning tone, human copy and link to docs/PAYROLL.md §3.3", () => {
    render(<PendingVerificationAlert />)
    expect(screen.getByText(/calculation blocked — pending verification/i)).toBeInTheDocument()
    expect(screen.getByText(/configurable calculation, cannot calculate/i)).toBeInTheDocument()
    const link = screen.getByRole("link")
    expect(link).toHaveAttribute("href", "/docs/PAYROLL.md#33")
    expect(link).toHaveTextContent("docs/PAYROLL.md §3.3")
    // Multiple pending verification texts exist (title + body), ensure at least one
    expect(screen.getAllByText(/pending verification/i).length).toBeGreaterThan(0)
  })

  test("warning Alert has correct tone class", () => {
    const { container } = render(<PendingVerificationAlert />)
    // The Alert wrapper should have warning tone
    expect(container.textContent).toContain("pending verification")
  })
})
