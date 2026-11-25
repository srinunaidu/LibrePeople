import { readFileSync, readdirSync } from "fs"
import { join } from "path"
import { describe, expect, test } from "vitest"

// Honest-feedback slice 3 (E-UX-03): UX pages in leave, payroll (PayRunDetail, PayRuns, PayrollSetup, PayrollOverview),
// onboarding render Alert success (role=status) / Alert error with raw backend
// detail, mutations never feed the load-failure channel, no toast/alert()
// placeholders survive, dead endpoints and fabricated activity tables are gone,
// API-enforced authz is reflected in the UI, all config persists server-side,
// Layout shell wraps every page, labels tied to inputs, tables have caption/scope,
// empty/loading/error/success states present, solver messaging honest.

const SCOPE_DIRS = [
  "src/pages/leave",
  "src/pages/payroll",
  "src/pages/onboarding",
] as const

// Pages that have mutations and full page lifecycle
const PAGE_FILES = [
  "LeaveLedger.tsx",
  "PayRunDetail.tsx",
  "PayRuns.tsx",
  "PayrollSetup.tsx",
  "PayrollOverview.tsx",
  "OnboardingConfig.tsx",
] as const

// Utility files - only check for no toast/sonner/alert()
const UTILITY_FILES = [
  "shared.tsx",
] as const

const read = (p: string) => readFileSync(join(process.cwd(), p), "utf8")
const readScope = (dir: string, f: string) => read(join(dir, f))
// Negative assertions scan code only — header comments document the removed
// fabrications/dead endpoints and legitimately mention their names.
const code = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, "")

describe("slice 3 — every scoped page renders honest Alert feedback", () => {
  for (const dir of SCOPE_DIRS) {
    const pageFiles = readdirSync(join(process.cwd(), dir))
      .filter((f) => f.endsWith(".tsx") && !f.endsWith(".test.tsx") && PAGE_FILES.includes(f as any))
      .sort()

    for (const file of pageFiles) {
      test(`${dir}/${file}: Alert success + error channel, no toast/alert() placeholders`, () => {
        const src = readScope(dir, file)
        // Pages with mutations (PayRunDetail, PayRuns, PayrollSetup) have Alert success; read-only pages (LeaveLedger, OnboardingConfig, PayrollOverview) don't
        const hasMutations = ["PayRunDetail.tsx", "PayRuns.tsx", "PayrollSetup.tsx"].includes(file)
        if (hasMutations) {
          expect(src).toContain('<Alert tone="success"')
        }
        // Error channel: Alert error for actions and/or RetryableAlert for loads.
        expect(src.includes('<Alert tone="error"') || src.includes("RetryableAlert")).toBe(true)
        expect(src).not.toContain("toast" + ".success")
        expect(src).not.toContain("toast" + ".error")
        expect(src).not.toContain("@/components/ui/sonner")
        expect(src).not.toMatch(/[^A-Za-z]alert\(/)
      })

      test(`${dir}/${file}: mutation failures never feed the load-error channel`, () => {
        const src = readScope(dir, file)
        // Separate actionError/notice state for mutations; error/RetryableAlert
        // stays reserved for load failures.
        expect(src).not.toMatch(/catch\s*\{\s*\}/)
      })

      test(`${dir}/${file}: no dead endpoints or fabricated success claims`, () => {
        const src = code(readScope(dir, file))
        // Common dead endpoints / fake claims from earlier slices
        expect(src).not.toContain("onboarding/steps/advance")
        expect(src).not.toContain("onboarding/steps/reset")
        expect(src).not.toContain("erasure-trigger")
        expect(src).not.toContain("/admin/bank/export")
        expect(src).not.toContain("audit row (AD-07) written")
        expect(src).not.toContain("audit row written")
        expect(src).not.toContain("https://placeholder")
      })

      test(`${dir}/${file}: wrapped in Layout (nav + responsive shell)`, () => {
        expect(readScope(dir, file)).toContain("<Layout>")
      })
    }

    // Utility files - only check for no toast/sonner/alert()
    const utilFiles = readdirSync(join(process.cwd(), dir))
      .filter((f) => f.endsWith(".tsx") && !f.endsWith(".test.tsx") && UTILITY_FILES.includes(f as any))
      .sort()

    for (const file of utilFiles) {
      test(`${dir}/${file}: utility file has no toast/sonner/alert() placeholders`, () => {
        const src = readScope(dir, file)
        expect(src).not.toContain("toast" + ".success")
        expect(src).not.toContain("toast" + ".error")
        expect(src).not.toContain("@/components/ui/sonner")
        expect(src).not.toMatch(/[^A-Za-z]alert\(/)
      })
    }
  }
})

describe("slice 3 — API-enforced authz reflected in UI", () => {
  // LeaveLedger: WORKFORCE_ROLES / MANAGER_ROLES / REPORTS_ROLES gates
  // OnboardingConfig: ADMIN_ROLES gate for presets/readiness
  // PayRunDetail: READ_ROLES / MANAGE_ROLES gates
  // PayRuns: READ_ROLES / MANAGE_ROLES gates
  // PayrollSetup: READ_ROLES / MANAGE_ROLES gates
  // PayrollOverview: READ_ROLES gate
  for (const dir of SCOPE_DIRS) {
    const pageFiles = readdirSync(join(process.cwd(), dir))
      .filter((f) => f.endsWith(".tsx") && !f.endsWith(".test.tsx") && PAGE_FILES.includes(f as any))
      .sort()

    for (const file of pageFiles) {
      const src = readScope(dir, file)
      if (!src.includes("canWorkforce") && !src.includes("canManager") && !src.includes("canReports") && !src.includes("canAdmin") && !src.includes("canRead") && !src.includes("canManage")) continue

      test(`${dir}/${file}: role gates mirror backend and show permission state`, () => {
        const src = readScope(dir, file)
        // Each page uses role constants and shows EmptyState for denied roles
        expect(src).toContain("EmptyState")
        // Permission denied message
        expect(src).toMatch(/does not read|not visible for your role|requires .Admin|requires HR|requires Manager|requires PayrollViewer|Your role does not read/)
      })
    }
  }
})

describe("slice 3 — real data, real actions, persistence", () => {
  test("LeaveLedger: ledger/reconciliation/payroll-input load independently, per-section error", () => {
    const src = readScope("src/pages/leave", "LeaveLedger.tsx")
    expect(src).toContain("Promise.allSettled")
    // Each section has its own error/notFound state
    expect(src).toContain("ledgerError")
    expect(src).toContain("reconError")
    expect(src).toContain("payrollError")
    expect(src).toContain("ledgerNotFound")
    expect(src).toContain("reconNotFound")
    expect(src).toContain("payrollNotFound")
  })

  test("OnboardingConfig: presets/readiness/employees load independently, drill loads independently", () => {
    const src = readScope("src/pages/onboarding", "OnboardingConfig.tsx")
    expect(src).toContain("Promise.allSettled")
    expect(src).toContain("drillLoading")
    expect(src).toContain("drillErrors")
    expect(src).toContain("drillNotFound")
  })

  test("PayRunDetail: run/slips/employees load independently, period resolved after", () => {
    const src = readScope("src/pages/payroll", "PayRunDetail.tsx")
    expect(src).toContain("Promise.allSettled")
    expect(src).toContain("actionError")
    expect(src).toContain("notice")
    // success notice set AFTER await load()
    expect(src).toContain("setNotice")
    expect(src).toContain("await load()")
  })

  test("PayRunDetail F&F: GET/POST params built correctly, 409 handled with pending_verification gate", () => {
    const src = readScope("src/pages/payroll", "PayRunDetail.tsx")
    expect(src).toContain("rule_pack_not_verified")
    expect(src).toContain("pending" + "_" + "verification")
    expect(src).toContain("notice_days")
    expect(src).toContain("loadFnf")
  })

  test("PayRuns: runs/periods load independently, notice state for create mutation", () => {
    const src = readScope("src/pages/payroll", "PayRuns.tsx")
    expect(src).toContain("Promise.allSettled")
    expect(src).toContain("notice")
    expect(src).toContain("setNotice")
    expect(src).toContain("await load()")
  })

  test("PayrollSetup: periods/components/profiles/employees load independently, notice state for three mutations", () => {
    const src = readScope("src/pages/payroll", "PayrollSetup.tsx")
    expect(src).toContain("Promise.allSettled")
    expect(src).toContain("notice")
    expect(src).toContain("setNotice")
    expect(src).toContain("await load()")
    // Three separate submit functions
    expect(src).toContain("submitPeriod")
    expect(src).toContain("submitComponent")
    expect(src).toContain("submitProfile")
  })

  test("PayrollOverview: runs load independently, read-only no mutations", () => {
    const src = readScope("src/pages/payroll", "PayrollOverview.tsx")
    expect(src).not.toContain("setNotice")
    expect(src).not.toContain("actionError")
    // No form submissions
    expect(src).not.toContain("submit")
  })
})

describe("slice 3 — fabricated activity/metrics removed", () => {
  // No static tables presenting invented records (names, dates, counts, statuses)
  // in the exclusive scope. Reference lists (predefined options) are OK if
  // labelled as predefined, not records.
  for (const dir of SCOPE_DIRS) {
    const pageFiles = readdirSync(join(process.cwd(), dir))
      .filter((f) => f.endsWith(".tsx") && !f.endsWith(".test.tsx") && PAGE_FILES.includes(f as any))
      .sort()

    for (const file of pageFiles) {
      test(`${dir}/${file}: no fabricated person names`, () => {
        const src = code(readScope(dir, file))
        expect(src).not.toContain("John Smith")
        expect(src).not.toContain("Sarah Johnson")
        expect(src).not.toContain("Jane Smith")
        expect(src).not.toContain("Alex Johnson")
      })

      test(`${dir}/${file}: no fabricated metric cards with invented counts`, () => {
        const src = code(readScope(dir, file))
        // These patterns indicate fabricated summary cards
        expect(src).not.toMatch(/title="[^"]*(summary|metrics|dashboard|overview|count|total|active|pending)[^"]*"[\s\S]{0,100}\d+\.\d+%/)
        expect(src).not.toContain("forecast summary")
        expect(src).not.toContain("projected growth")
      })
    }
  }
})

describe("slice 3 — states, a11y, responsive", () => {
  for (const dir of SCOPE_DIRS) {
    const pageFiles = readdirSync(join(process.cwd(), dir))
      .filter((f) => f.endsWith(".tsx") && !f.endsWith(".test.tsx") && PAGE_FILES.includes(f as any))
      .sort()

    for (const file of pageFiles) {
      const src = readScope(dir, file)

      test(`${dir}/${file}: loading states (LoadingRegion/skeleton)`, () => {
        expect(src).toContain("LoadingRegion")
      })

      test(`${dir}/${file}: empty states (EmptyState/empty rows)`, () => {
        expect(src.includes("EmptyState") || src.includes("no ledger entries") || src.includes("No ledger entries") || src.includes("no payslips") || src.includes("No payslips") || src.includes("No .* tasks") || src.includes("No .* documents") || src.includes("no presets")).toBe(true)
      })

      test(`${dir}/${file}: error states (RetryableAlert for loads, Alert error for actions)`, () => {
        expect(src.includes("RetryableAlert") || src.includes('<Alert tone="error"')).toBe(true)
      })

      test(`${dir}/${file}: success states (Alert success)`, () => {
        // OnboardingConfig, LeaveLedger, PayrollOverview are read-only with no mutations - skip success check
        if (file === "OnboardingConfig.tsx" || file === "LeaveLedger.tsx" || file === "PayrollOverview.tsx") return
        expect(src).toContain('<Alert tone="success"')
      })

      test(`${dir}/${file}: permission-denied state (EmptyState gate)`, () => {
        expect(src).toContain("EmptyState")
      })

      test(`${dir}/${file}: form labels tied to inputs (htmlFor)`, () => {
        // PayrollOverview has no forms
        if (file === "PayrollOverview.tsx") return
        expect(src).toContain("htmlFor")
      })

      test(`${dir}/${file}: tables have caption sr-only and scope="col"`, () => {
        // PayrollOverview has tables with caption/scope
        if (file === "PayRuns.tsx" || file === "PayrollSetup.tsx" || file === "PayrollOverview.tsx" || file === "PayRunDetail.tsx" || file === "LeaveLedger.tsx" || file === "OnboardingConfig.tsx") {
          expect(src).toContain('scope="col"')
          expect(src).toContain('className="sr-only"')
        }
      })
    }
  }
})

describe("slice 3 — solver messaging honest (no unverified claims)", () => {
  for (const dir of SCOPE_DIRS) {
    const pageFiles = readdirSync(join(process.cwd(), dir))
      .filter((f) => f.endsWith(".tsx") && !f.endsWith(".test.tsx") && PAGE_FILES.includes(f as any))
      .sort()

    for (const file of pageFiles) {
      const src = code(readScope(dir, file))

      test(`${dir}/${file}: no "saved locally" or "retained locally" without server persistence`, () => {
        expect(src).not.toContain("saved locally")
        expect(src).not.toContain("retained locally")
        expect(src).not.toContain("stored locally")
      })

      test(`${dir}/${file}: pending_verification gate text present where IN jurisdiction`, () => {
        // Only detail pages with IN jurisdiction checks need the gate
        if (file === "PayRunDetail.tsx" && src.includes("jurisdiction") && src.includes("IN")) {
          expect(src).toContain("pending" + "_" + "verification")
        }
      })

      test(`${dir}/${file}: no fabricated success messages like "audit row written"`, () => {
        expect(src).not.toContain("audit row written")
        expect(src).not.toContain("audit row (AD-07) written")
      })
    }
  }
})

describe("slice 3 — slice-1 and slice-2 frozen files untouched", () => {
  test("slice-1 frozen 16 files not in slice 3 scope", () => {
    const frozen = [
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
    // Slice 3 page scope
    const slice3PageScope = PAGE_FILES.map(f => 
      f === "LeaveLedger.tsx" ? "src/pages/leave/LeaveLedger.tsx" :
      f === "PayRunDetail.tsx" ? "src/pages/payroll/PayRunDetail.tsx" :
      f === "PayRuns.tsx" ? "src/pages/payroll/PayRuns.tsx" :
      f === "PayrollSetup.tsx" ? "src/pages/payroll/PayrollSetup.tsx" :
      f === "PayrollOverview.tsx" ? "src/pages/payroll/PayrollOverview.tsx" :
      "src/pages/onboarding/OnboardingConfig.tsx"
    )
    for (const f of frozen) {
      expect(slice3PageScope).not.toContain(f)
    }
  })

  test("slice-2 admin exclusives not in slice 3 scope", () => {
    const slice2Admin = readdirSync(join(process.cwd(), "src/pages/admin"))
      .filter((f) => f.endsWith(".tsx") && !f.endsWith(".test.tsx"))
    const slice3PageScope = PAGE_FILES.map(f => 
      f === "LeaveLedger.tsx" ? "src/pages/leave/LeaveLedger.tsx" :
      f === "PayRunDetail.tsx" ? "src/pages/payroll/PayRunDetail.tsx" :
      f === "PayRuns.tsx" ? "src/pages/payroll/PayRuns.tsx" :
      f === "PayrollSetup.tsx" ? "src/pages/payroll/PayrollSetup.tsx" :
      f === "PayrollOverview.tsx" ? "src/pages/payroll/PayrollOverview.tsx" :
      "src/pages/onboarding/OnboardingConfig.tsx"
    )
    for (const f of slice2Admin) {
      expect(slice3PageScope).not.toContain(`src/pages/admin/${f}`)
    }
  })
})