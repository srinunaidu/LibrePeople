import { readFileSync, readdirSync } from "fs"
import { join } from "path"
import { describe, expect, test } from "vitest"
import { summarizeBulkAdmin } from "@/lib/bulk-admin"

// Honest-feedback slice 2 (E-UX-02): every admin console page renders Alert
// success (role=status) / Alert error with raw backend detail, mutations never
// feed the load-failure channel, no toast/alert() placeholders survive, dead
// endpoints and fabricated activity tables are gone, and API-enforced authz
// (require_roles("SuperAdmin") on settings/feature-flags/integrations) is
// reflected in the UI. Slice-1 frozen files (incl. admin/UserAdmin.tsx) are
// out of scope and untouched.

const ADMIN_DIR = "src/pages/admin"
const FROZEN = new Set(["UserAdmin.tsx"])
const PAGES = readdirSync(join(process.cwd(), ADMIN_DIR))
  .filter((f) => f.endsWith(".tsx") && !f.endsWith(".test.tsx") && !FROZEN.has(f))
  .sort()

const read = (p: string) => readFileSync(join(process.cwd(), p), "utf8")
const readPage = (f: string) => read(join(ADMIN_DIR, f))
// Negative assertions scan code only — header comments document the removed
// fabrications/dead endpoints and legitimately mention their names.
const code = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, "")

describe("slice 2 — admin bulk summary helper", () => {
  test("all succeed renders X of N with no error", () => {
    const out = summarizeBulkAdmin(["hr", "payroll"], [{ status: "fulfilled", value: {} }, { status: "fulfilled", value: {} }], "Saved", "module entitlement")
    expect(out.okCount).toBe(2)
    expect(out.failures).toEqual([])
    expect(out.notice).toBe("Saved 2 of 2 module entitlement(s)")
    expect(out.error).toBe("")
  })

  test("partial failure keeps raw backend detail per string id", () => {
    const out = summarizeBulkAdmin(
      ["hr", "payroll"],
      [
        { status: "fulfilled", value: {} },
        { status: "rejected", reason: { response: { data: { detail: "Dependency requires hr" } } } },
      ],
      "Saved",
      "module entitlement",
    )
    expect(out.notice).toBe("Saved 1 of 2 module entitlement(s) — 1 failed")
    expect(out.error).toContain("payroll: Dependency requires hr")
    expect(out.error).toContain("1 of 2")
  })

  test("numeric ids and total failure render no success notice", () => {
    const out = summarizeBulkAdmin(
      [3],
      [{ status: "rejected", reason: { response: { data: { detail: "Locked" } } } }],
      "Saved",
      "flag",
    )
    expect(out.notice).toBe("")
    expect(out.error).toContain("3: Locked")
  })

  test("single item noun is not pluralised", () => {
    const out = summarizeBulkAdmin(["hr"], [{ status: "fulfilled", value: {} }], "Saved", "module")
    expect(out.notice).toBe("Saved 1 of 1 module")
  })
})

describe("slice 2 — every admin page renders honest Alert feedback", () => {
  for (const page of PAGES) {
    test(`${page}: Alert success + error channel, no toast/alert() placeholders`, () => {
      const src = readPage(page)
      expect(src).toContain('<Alert tone="success"')
      // Error channel: Alert error for actions and/or RetryableAlert for loads.
      expect(src.includes('<Alert tone="error"') || src.includes("RetryableAlert")).toBe(true)
      expect(src).not.toContain("toast" + ".success")
      expect(src).not.toContain("toast" + ".error")
      expect(src).not.toContain("@/components/ui/sonner")
      expect(src).not.toMatch(/[^A-Za-z]alert\(/)
    })

    test(`${page}: mutation failures never feed the load-error channel`, () => {
      const src = readPage(page)
      expect(src).not.toContain("setError(e) } finally { setSaving(false) }")
      expect(src).not.toMatch(/catch\s*\{\s*\}/)
    })

    test(`${page}: no dead endpoints or fabricated success claims`, () => {
      const src = code(readPage(page))
      expect(src).not.toContain("onboarding/steps/advance")
      expect(src).not.toContain("onboarding/steps/reset")
      expect(src).not.toContain("erasure-trigger")
      expect(src).not.toContain("/admin/bank/export")
      expect(src).not.toContain("audit row (AD-07) written")
      expect(src).not.toContain("audit row written")
      expect(src).not.toContain("https://placeholder")
    })

    test(`${page}: wrapped in Layout (nav + responsive shell)`, () => {
      expect(readPage(page)).toContain("<Layout>")
    })
  }
})

describe("slice 2 — API-enforced authz reflected in UI", () => {
  // settings / feature-flags / integrations endpoints are
  // require_roles("SuperAdmin") in client_onboarding.py — pages using them
  // must gate reads and writes to SuperAdmin and show a permission state.
  for (const page of PAGES) {
    const src = readPage(page)
    if (!/api\.get\(`\/onboarding-portal\/clients\/\$\{id\}\/(feature-flags|settings|integrations)`\)/.test(src)) continue
    test(`${page}: SuperAdmin gate + permission-denied state`, () => {
      expect(src).toMatch(/canWrite = user\?\.role === "SuperAdmin"|isSuperAdmin|canAdmin/)
      expect(src).toContain("Not visible for your role")
    })
  }

  test("OrgChart keeps ADMIN_ROLES for rebuild (matches ess_hr.py)", () => {
    const src = readPage("OrgChart.tsx")
    expect(src).toContain('["SuperAdmin", "HR"].includes(user?.role ?? "")')
  })

  test("retention job ledgers keep ADMIN_ROLES (matches admin_jobs.py)", () => {
    for (const page of ["ExportErasure.tsx", "RetentionExport.tsx"]) {
      expect(readPage(page)).toContain('["SuperAdmin", "HR"].includes(user?.role ?? "")')
    }
  })

  test("BankExport payment-file keeps ADMIN_ROLES (matches payroll.py)", () => {
    expect(readPage("BankExport.tsx")).toContain('["SuperAdmin", "HR"].includes(user?.role ?? "")')
  })
})

describe("slice 2 — real data, real actions, persistence", () => {
  test("ModuleEntitlements bulk settles per module and reports per-key failures", () => {
    const src = readPage("ModuleEntitlements.tsx")
    expect(src).toContain("Promise.allSettled")
    expect(src).toContain("summarizeBulkAdmin")
    expect(src).toContain("await load()")
  })

  test("WorkflowApproval uses the real onboarding endpoints and schema", () => {
    const src = readPage("WorkflowApproval.tsx")
    expect(src).toContain("/onboarding`)")
    expect(src).toContain("key, title:")
    expect(src).toContain("/complete`)")
    expect(src).not.toContain("required_approval")
  })

  test("AnnouncementsDirectory persists via feature-flag JSON, no seed array", () => {
    const src = readPage("AnnouncementsDirectory.tsx")
    expect(src).toContain("feature-flags/announcements")
    expect(src).toContain("JSON.stringify")
    expect(src).not.toContain("Company-wide meeting")
    expect(src).not.toContain("Alex Johnson")
  })

  test("ManagerAssignments options come from the employee master", () => {
    const src = code(readPage("ManagerAssignments.tsx"))
    expect(src).toContain("listEmployees()")
    expect(src).not.toContain("John Doe")
    expect(src).not.toContain("manager-john")
    expect(src).toContain("default_manager_department")
  })

  test("HistoricalRecord persists notes, no random record ids", () => {
    const src = readPage("HistoricalRecord.tsx")
    expect(src).toContain("settings/historical_correction_note")
    expect(src).not.toContain("Math.random")
    expect(src).not.toContain("REC-2026")
  })

  test("stage pages persist config via feature flags instead of dead advance", () => {
    expect(readPage("CandidateStages.tsx")).toContain("feature-flags/candidate_status")
    expect(readPage("RequisitionStages.tsx")).toContain("feature-flags/requisition_status")
    expect(readPage("TenStepJourney.tsx")).toContain("feature-flags/journey_step")
  })

  test("ExportErasure uses real retry/discard job actions", () => {
    const src = readPage("ExportErasure.tsx")
    expect(src).toContain("/admin/jobs/${id}/${action}")
  })

  test("InterviewScheduling uses live interviews CRUD, not the flag shim (R2 honesty-sweep, lead-approved)", () => {
    const src = readPage("InterviewScheduling.tsx")
    expect(src).toContain("/api/v1/interviews")
    expect(src).not.toContain("feature-flags/interview_type")
    expect(src).not.toContain("alert(")
  })

  test("PolicySearch stores the query only — no fabricated results", () => {
    const src = readPage("PolicySearch.tsx")
    expect(src).toContain("feature-flags/policy_query")
    expect(src).not.toContain("policy_results")
    expect(src).not.toContain("Citation results")
  })

  test("SavedViews lists the shortcuts the shell actually registers", () => {
    const src = readPage("SavedViews.tsx")
    expect(src).toContain('"g h"')
    expect(src).toContain('"g p"')
    expect(src).not.toContain('"g d"')
    expect(src).not.toContain('"g m"')
    expect(src).toContain("feature-flags/saved_view")
    expect(src).toContain("feature-flags/keyboard_nav")
  })

  test("IntegrationCredentials sends no placeholder endpoint", () => {
    const src = readPage("IntegrationCredentials.tsx")
    expect(src).toContain("endpoint: newEndpoint.trim() || null")
  })
})

describe("slice 2 — fabricated activity/metrics removed", () => {
  const FABRICATED_CARDS: [string, string][] = [
    ["AttendancePolicies.tsx", "Missed punches"],
    ["CompetencyCalibration.tsx", "Competency matrix"],
    ["CoverageGaps.tsx", "Coverage gaps"],
    ["CrossMidnightOvertime.tsx", "Overtime summary"],
    ["DemandForecasting.tsx", "Forecast summary"],
    ["DocumentClassification.tsx", "Document classification results"],
    ["EarningsDeductions.tsx", "Earnings/deductions summary"],
    ["EmployerContributions.tsx", "Claims summary"],
    ["EquipmentAccess.tsx", "Equipment assignments"],
    ["ExternalIntegration.tsx", "Integration status"],
    ["ForecastException.tsx", "Forecast exceptions"],
    ["FunnelAnalytics.tsx", "Funnel metrics"],
    ["HardConstraints.tsx", "Constraint violations"],
    ["HiringPlans.tsx", "Hiring scenarios"],
    ["ImprovementPlans.tsx", "Active improvement plans"],
    ["InformationCollection.tsx", "Collection items"],
    ["LeaveToPayroll.tsx", "Leave-to-payroll mapping"],
    ["MentoringDevelopment.tsx", "Mentorship pairs"],
    ["ModelVersioning.tsx", "Model accuracy"],
    ["OfferApprovals.tsx", "Pending offers"],
    ["PaySchedule.tsx", "Pay components"],
    ["ProbationTracking.tsx", "Probation tracking"],
    ["PromotionReadiness.tsx", "Promotion readiness"],
    ["RehireHandling.tsx", "Rehire dashboard"],
    ["RenewalReminders.tsx", "Upcoming renewals"],
    ["ResumableChecklists.tsx", "Preboarding tasks"],
    ["SalaryRevisions.tsx", "Salary revision history"],
    ["ScheduledReporting.tsx", "Scheduled reports"],
    ["ShiftBasedAttendance.tsx", "Published schedules"],
    ["SkillGaps.tsx", "Skill gaps"],
    ["SuccessionPlanning.tsx", "Succession pool"],
    ["TeamAvailability.tsx", "Team availability"],
    ["TimesheetLock.tsx", "Timesheet lock summary"],
    ["TransferPromotion.tsx", "Recent transfers"],
  ]
  for (const [page, card] of FABRICATED_CARDS) {
    test(`${page}: fabricated "${card}" card removed`, () => {
      expect(readPage(page)).not.toContain(`title="${card}"`)
    })
  }

  test("no fabricated person names remain in admin pages", () => {
    for (const page of PAGES) {
      const src = code(readPage(page))
      expect(src).not.toContain("John Smith")
      expect(src).not.toContain("Sarah Johnson")
    }
  })

  test("JurisdictionRules shows the persisted config, not invented rows", () => {
    const src = readPage("JurisdictionRules.tsx")
    expect(src).toContain("Active jurisdiction config")
    expect(src).not.toContain("2026-01-01")
    expect(src).not.toContain("2026-06-01")
  })

  test("enrollment/publish verbs match what the endpoints actually do", () => {
    for (const page of ["LearningPaths.tsx", "TrainingAssignments.tsx"]) {
      const src = readPage(page)
      expect(src).toContain("Save enrollment flag")
      expect(src).not.toContain('"Enroll"')
    }
    for (const page of ["TemplatesDraftsPublish.tsx", "DemandStaffing.tsx"]) {
      const src = readPage(page)
      expect(src).toContain("Save default template")
      expect(src).not.toContain("Publish template")
    }
  })
})

describe("slice 2 — slice-1 frozen files untouched", () => {
  test("UserAdmin.tsx keeps its slice-1 shape (no sonner, formErrors.impersonate)", () => {
    const src = readPage("UserAdmin.tsx")
    expect(src).not.toContain("sonner")
    expect(src).toContain("formErrors.impersonate")
  })

  test("slice-1 bulk helper and suite still exist", () => {
    expect(read("src/lib/bulk.ts")).toContain("summarizeBulk")
    expect(read("src/lib/feedback-slice1.test.ts")).toContain("slice 1")
  })
})