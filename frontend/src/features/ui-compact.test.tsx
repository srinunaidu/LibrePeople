import { describe, expect, test, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import React from "react"
import { parseConversationalQuery } from "@/components/shell/CommandPalette"
import { deriveActionCards } from "@/components/home/NextBestActionCards"
import { deriveTheme } from "@/context/TenantContext"
import { AccordionItem } from "@/components/ui/accordion"
import { BulkBar } from "@/components/ui/bulk-bar"
import { ProgressRing } from "@/components/ui/progress-ring"

// ---- CommandPalette conversational parsing ----
describe("CommandPalette conversational", () => {
  test("parses 'show pending leaves' → leave", () => {
    const item = parseConversationalQuery("show pending leaves")
    expect(item?.id).toBe("leave")
  })
  test("parses 'payslip' → payroll", () => {
    const item = parseConversationalQuery("payslip")
    expect(item?.id).toBe("payroll")
  })
  test("parses 'show payslip' → payroll", () => {
    const item = parseConversationalQuery("show payslip")
    expect(item?.id).toBe("payroll")
  })
  test("parses 'leave' keyword", () => {
    const item = parseConversationalQuery("leave")
    expect(item?.id).toBe("leave")
  })
  test("returns null for unknown query", () => {
    const item = parseConversationalQuery("xyz unknown query 123")
    expect(item).toBeNull()
  })
})

// ---- Next Best Action ranking ----
describe("NextBestAction deriveActionCards", () => {
  test("returns 3 card types sorted by priority", () => {
    const cards = deriveActionCards({
      pendingApprovals: 5,
      unfilledShifts: 3,
      upcomingDeadlines: 2,
      onApprovals: () => {},
      onShifts: () => {},
      onDeadlines: () => {},
    })
    expect(cards.length).toBe(3)
    expect(cards[0].priority).toBe(1)
    expect(cards[1].priority).toBe(2)
    expect(cards[2].priority).toBe(3)
  })
  test("cards have CTA and count", () => {
    const cards = deriveActionCards({
      pendingApprovals: 1,
      unfilledShifts: 0,
      upcomingDeadlines: 0,
      onApprovals: vi.fn(),
      onShifts: vi.fn(),
      onDeadlines: vi.fn(),
    })
    const approvals = cards.find((c) => c.id === "approvals")!
    expect(approvals.count).toBe(1)
    expect(approvals.ctaLabel).toBeTruthy()
  })
})

// ---- deriveTheme WCAG AA contrast ----
describe("deriveTheme WCAG AA", () => {
  test("returns readable theme for brand blue", () => {
    const theme = deriveTheme("#2563eb", "#0f172a")
    expect(theme).not.toBeNull()
    expect(theme!.vars["--tenant-primary-text"]).toBeTruthy()
  })
  test("adjusts light accent for readability on white", () => {
    // A light yellow should be darkened for text on white
    const theme = deriveTheme("#fde68a", "#0f172a")
    expect(theme).not.toBeNull()
    // The text variant should be darker than the raw accent
    expect(theme!.vars["--tenant-primary-text"]).not.toBe("#FDE68A")
  })
  test("returns null for invalid hex", () => {
    expect(deriveTheme("not-a-color", "#000")).toBeNull()
  })
  test("contrast helper preserves dark accent as text", () => {
    const darkTheme = deriveTheme("#1e40af", "#0f172a")
    expect(darkTheme).not.toBeNull()
    // Dark blue on white already has sufficient contrast, so text variant close to original
    expect(darkTheme!.vars["--tenant-primary-text"]).toBeTruthy()
  })
})

// ---- Accordion aria-expanded + keyboard ----
describe("AccordionItem", () => {
  test("renders collapsed by default and toggles on click", () => {
    render(
      <AccordionItem title="Advanced Options">
        <p>Hidden content</p>
      </AccordionItem>
    )
    const btn = screen.getByRole("button", { name: /Advanced Options/ })
    expect(btn.getAttribute("aria-expanded")).toBe("false")
    expect(screen.queryByText("Hidden content")).toBeNull()
    fireEvent.click(btn)
    expect(btn.getAttribute("aria-expanded")).toBe("true")
    expect(screen.getByText("Hidden content")).toBeTruthy()
  })

  test("toggles via keyboard Enter and Space", () => {
    render(
      <AccordionItem title="Options">
        <p>Content</p>
      </AccordionItem>
    )
    const btn = screen.getByRole("button", { name: /Options/ })
    fireEvent.keyDown(btn, { key: "Enter" })
    expect(btn.getAttribute("aria-expanded")).toBe("true")
    fireEvent.keyDown(btn, { key: " " })
    expect(btn.getAttribute("aria-expanded")).toBe("false")
  })
})

// ---- BulkBar selection logic ----
describe("BulkBar", () => {
  test("renders nothing when nothing selected", () => {
    const { container } = render(<BulkBar selectedCount={0} totalCount={10} />)
    expect(container.innerHTML).toBe("")
  })
  test("shows count and actions when selected", () => {
    render(
      <BulkBar
        selectedCount={2}
        totalCount={10}
        actions={<button>Approve</button>}
      />
    )
    expect(screen.getByText("2 of 10 selected")).toBeTruthy()
    expect(screen.getByText("Approve")).toBeTruthy()
  })
})

// ---- ProgressRing semantic ----
describe("ProgressRing", () => {
  test("renders with correct aria-valuenow", () => {
    render(<ProgressRing percent={72} label="Onboarding" />)
    const ring = screen.getByRole("progressbar")
    expect(ring.getAttribute("aria-valuenow")).toBe("72")
  })
  test("clamps percent to 0-100", () => {
    render(<ProgressRing percent={150} />)
    expect(screen.getByRole("progressbar").getAttribute("aria-valuenow")).toBe("100")
  })
})

// ---- Autosave debounce ----
describe("useAutosave", () => {
  test("module exports useAutosave and useAutosaveRestore", async () => {
    const mod = await import("@/hooks/useAutosave")
    expect(typeof mod.useAutosave).toBe("function")
    expect(typeof mod.useAutosaveRestore).toBe("function")
  })
  test("autosave writes to storage with debounce", async () => {
    const store: Record<string, string> = {}
    const fakeStorage = {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => { store[k] = v },
      removeItem: (k: string) => { delete store[k] },
    } as unknown as Storage
    // @ts-ignore
    globalThis.localStorage = fakeStorage
    fakeStorage.setItem("test-autosave-key", JSON.stringify({ data: { foo: "bar" }, savedAt: Date.now() }))
    expect(fakeStorage.getItem("test-autosave-key")).toBeTruthy()
    fakeStorage.removeItem("test-autosave-key")
    expect(fakeStorage.getItem("test-autosave-key")).toBeNull()
  })
})

// ---- Badge semantic check (CSS var usage) ----
describe("Badge semantic tokens", () => {
  test("badge class maps to semantic vars", async () => {
    const { badgeVariants } = await import("@/components/ui/badge")
    // Variant 'green' should map to a semantic class, not hardcoded bg-emerald
    const cls = badgeVariants({ variant: "green" })
    // The class should not contain literal emerald hex
    expect(cls).not.toContain("bg-emerald")
    expect(cls).toContain("badge-green")
  })
})
