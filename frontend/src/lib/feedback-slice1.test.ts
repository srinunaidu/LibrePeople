import { readFileSync } from "fs"
import { join } from "path"
import { describe, expect, test } from "vitest"
import { summarizeBulk } from "@/lib/bulk"

// Honest-feedback slice 1: every mutation in scope renders an Alert success
// (role=status) or an Alert error with the raw backend detail, and Leave bulk
// actions settle per item instead of swallowing failures.

const PAGES = [
  "src/pages/Leave.tsx",
  "src/pages/Recruiting.tsx",
  "src/pages/TimeAttendance.tsx",
  "src/pages/Platform.tsx",
  "src/pages/RosterBuilder.tsx",
  "src/pages/ess/ESSHub.tsx",
  "src/pages/Onboarding.tsx",
  "src/pages/Offboarding.tsx",
  "src/pages/Scheduling.tsx",
  "src/pages/benefits/BenefitsHub.tsx",
  "src/pages/performance/PerformanceHub.tsx",
  "src/pages/learning/LearningHub.tsx",
  "src/pages/ClientOnboarding.tsx",
  "src/pages/admin/UserAdmin.tsx",
]

const read = (p: string) => readFileSync(join(process.cwd(), p), "utf8")

describe("slice 1 — bulk summary helper", () => {
  test("all succeed renders X of N with no error", () => {
    const out = summarizeBulk([1, 2], [{ status: "fulfilled", value: {} }, { status: "fulfilled", value: {} }], "Approved", "request")
    expect(out.okCount).toBe(2)
    expect(out.failures).toEqual([])
    expect(out.notice).toBe("Approved 2 of 2 request(s)")
    expect(out.error).toBe("")
  })

  test("partial failure keeps raw backend detail per id", () => {
    const out = summarizeBulk(
      [7, 8],
      [
        { status: "fulfilled", value: {} },
        { status: "rejected", reason: { response: { data: { detail: "Already approved" } } } },
      ],
      "Approved",
      "request",
    )
    expect(out.notice).toBe("Approved 1 of 2 request(s) — 1 failed")
    expect(out.error).toContain("#8: Already approved")
    expect(out.error).toContain("1 of 2")
  })

  test("total failure renders no success notice", () => {
    const out = summarizeBulk(
      [3],
      [{ status: "rejected", reason: { response: { data: { detail: "Locked" } } } }],
      "Rejected",
      "request",
    )
    expect(out.notice).toBe("")
    expect(out.error).toContain("#3: Locked")
  })
})

describe("slice 1 — every scoped page renders Alert success, no toast placeholder", () => {
  for (const page of PAGES) {
    test(`${page} renders <Alert tone="success"> and no toast placeholder`, () => {
      const src = read(page)
      expect(src).toContain('<Alert tone="success"')
      expect(src).not.toContain("toast" + ".success")
    })
  }

  test("Leave bulk settles per item and swallows nothing", () => {
    const src = read("src/pages/Leave.tsx")
    expect(src).toContain("Promise.allSettled")
    expect(src).toContain("summarizeBulk")
    expect(src).not.toMatch(/catch\s*\{\s*\/\*\s*ignore\s*\*\//)
  })

  test("UserAdmin no longer depends on sonner toasts", () => {
    const src = read("src/pages/admin/UserAdmin.tsx")
    expect(src).not.toContain("sonner")
    expect(src).toContain("formErrors.impersonate")
  })

  test("Platform action failures render Alert error, not RetryableAlert", () => {
    const src = read("src/pages/Platform.tsx")
    // Separate actionError string state for mutations; error/RetryableAlert
    // stays reserved for load failures.
    expect(src).toMatch(/const \[actionError,\s*setActionError\]\s*=\s*useState/)
    expect(src).toContain("setActionError(\"\")")
    // Mutation catch feeds actionError, never the load-failure error state.
    expect(src).not.toMatch(/catch[^{]*\{[^}]*setError/)
    expect(src).toMatch(/catch[^{]*\{[^}]*setActionError/)
    // Error Alert renders next to the success Alert.
    expect(src).toContain('<Alert tone="error"')
    expect(src).toContain("{actionError")
    expect(src).toContain("RetryableAlert")
  })
})
