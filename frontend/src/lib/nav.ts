/**
 * Phase C — single role-aware navigation config.
 *
 * One IA drives the rail (WorkspaceRail), the mobile drawer + bottom bar
 * (Layout), the Quick Action palette (CommandPalette), the "g <letter>"
 * shortcuts (lib/keyboard GOTO registry) and the help sheet
 * (ShortcutHelp). Every `to` below is an exact App.tsx route — never an
 * alias (see ADMIN_ALIASES) and never a /t/:slug workspace URL (single
 * tenant install: TenantRedirect strips those).
 *
 * Role model (backend/app/models/user.py — five roles, unchanged):
 *   SuperAdmin / HR      → "admin" lens (everything; SuperAdmin-only admin
 *                           items stay hidden from HR per D2)
 *   Manager              → "manager" lens (D6: no Comp, Payroll, Admin)
 *   Associate            → "employee" lens (D6: self-service subset)
 *   PayrollViewer        → "payroll" lens (D6: books + inputs only)
 * Lenses are automatic by role (D3: no manual switcher). `roles` is the
 * enforcement mirror of `lens`: components filter on `roles`, tests assert
 * the two agree for every role.
 */
import type { ComponentType, SVGProps } from "react"
import {
  Banknote,
  BarChart3,
  Bed,
  Book,
  Briefcase,
  Building,
  Clock,
  FileText,
  Gift,
  GraduationCap,
  HeartHandshake,
  LayoutDashboard,
  LifeBuoy,
  Network,
  Package,
  Plug,
  Receipt,
  Star,
  Target,
  Users,
  Wallet,
  Workflow,
} from "lucide-react"

export type NavIcon = ComponentType<SVGProps<SVGSVGElement>>

export type NavRole = "SuperAdmin" | "HR" | "Manager" | "Associate" | "PayrollViewer"

export type NavLens = "admin" | "manager" | "employee" | "payroll"

export interface NavSubItem {
  label: string
  to: string
}

export interface NavSection {
  /** Stable key — also the palette item id and breadcrumb token. */
  section: string
  label: string
  /** Canonical App.tsx route. Never an alias, never /t/-prefixed. */
  to: string
  icon: NavIcon
  /** Roles that may see (and hence reach via nav) this section. */
  roles: NavRole[]
  /** "g <letter>" shortcut. D4: Org=o, Comp=c, Documents=d, ER=v,
   *  Helpdesk=i, Workflows=w; everything else keeps its historic letter. */
  gKey?: string
  /** Lenses that include this section (pure filter over this config). */
  lens: NavLens[]
  sub?: NavSubItem[]
  /** Bottom-bar rank (lowest first, max 5 shown). Unset = never docked. */
  bottomNavPriority?: number
  /** Extra search phrases for the palette (conversational queries). */
  keywords?: string[]
  /** Short palette description. */
  description?: string
}

const ALL: NavRole[] = ["SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer"]
const ADMIN: NavRole[] = ["SuperAdmin", "HR"]
const ADMIN_MGR: NavRole[] = ["SuperAdmin", "HR", "Manager"]
const SELF: NavRole[] = ["SuperAdmin", "HR", "Manager", "Associate"]

export const NAV_SECTIONS: NavSection[] = [
  {
    section: "overview",
    label: "Overview",
    to: "/dashboard",
    icon: LayoutDashboard,
    roles: ALL,
    gKey: "h",
    lens: ["admin", "manager", "employee", "payroll"],
    sub: [{ label: "Project Status", to: "/project-status" }],
    bottomNavPriority: 1,
    keywords: ["home", "dashboard", "overview", "recent activity"],
    description: "Overview and recent activity",
  },
  {
    section: "people",
    label: "People",
    to: "/people",
    icon: Users,
    roles: SELF,
    gKey: "p",
    lens: ["admin", "manager", "employee"],
    sub: [
      { label: "Departments", to: "/people/departments" },
      { label: "Jobs", to: "/people/jobs" },
      { label: "Locations", to: "/people/locations" },
      { label: "Positions", to: "/people/positions" },
      { label: "Cost Centres", to: "/people/cost-centers" },
      { label: "Self-Service", to: "/ess" },
    ],
    bottomNavPriority: 2,
    keywords: ["people", "employees", "directory", "org"],
    description: "Employees, directory, org chart",
  },
  {
    section: "org",
    label: "Org",
    to: "/admin/org-chart",
    icon: Network,
    roles: SELF,
    gKey: "o",
    lens: ["admin", "manager", "employee"],
    keywords: ["org chart", "organisation", "structure", "hierarchy", "reporting line"],
    description: "Organisation chart and structure",
  },
  {
    section: "recruit",
    label: "Recruit",
    to: "/recruiting",
    icon: Target,
    roles: ADMIN_MGR,
    gKey: "r",
    lens: ["admin", "manager"],
    bottomNavPriority: 8,
    keywords: ["recruiting", "candidates", "offers", "hiring", "requisition"],
    description: "Requisitions, candidates, offers",
  },
  {
    section: "onboard",
    label: "Onboard",
    to: "/onboarding",
    icon: Briefcase,
    roles: SELF,
    gKey: "b",
    lens: ["admin", "manager", "employee"],
    sub: [
      { label: "Onboarding Config", to: "/onboarding-config" },
      { label: "Offboarding", to: "/offboarding" },
    ],
    bottomNavPriority: 9,
    keywords: ["onboarding", "joinee", "induction", "offboarding", "checklist"],
    description: "Onboarding journeys and offboarding",
  },
  {
    section: "time",
    label: "Attendance+Time",
    to: "/time",
    icon: Clock,
    roles: ALL,
    gKey: "t",
    lens: ["admin", "manager", "employee", "payroll"],
    sub: [
      { label: "Scheduling", to: "/scheduling" },
      { label: "Roster Builder", to: "/scheduling/roster" },
    ],
    bottomNavPriority: 3,
    keywords: ["time", "attendance", "clock", "timesheet", "clock in", "roster", "schedule", "solver", "publish", "shift", "my shifts", "upcoming shifts"],
    description: "Clock in/out, timesheets, schedules",
  },
  {
    section: "leave",
    label: "Leave",
    to: "/leave",
    icon: Bed,
    roles: ALL,
    gKey: "l",
    lens: ["admin", "manager", "employee", "payroll"],
    sub: [{ label: "Ledger & Reconciliation", to: "/leave/ledger" }],
    bottomNavPriority: 4,
    keywords: ["leave", "balance", "request", "pto", "pending leaves", "show pending leaves", "my leave requests", "leave requests", "my leave"],
    description: "Requests, balances, types",
  },
  {
    section: "comp",
    label: "Comp",
    to: "/platform/benefits",
    icon: Gift,
    roles: ["SuperAdmin", "HR", "PayrollViewer"],
    gKey: "c",
    lens: ["admin", "payroll"],
    keywords: ["benefits", "compensation", "perks", "salary revisions"],
    description: "Benefits and compensation",
  },
  {
    section: "payroll",
    label: "Payroll",
    to: "/platform/payroll",
    icon: Wallet,
    roles: ["SuperAdmin", "HR", "PayrollViewer"],
    gKey: "y",
    lens: ["admin", "payroll"],
    sub: [
      { label: "Pay runs", to: "/platform/payroll/runs" },
      { label: "Pay setup", to: "/platform/payroll/setup" },
      { label: "Payroll overview", to: "/platform/payroll/overview" },
    ],
    bottomNavPriority: 7,
    keywords: ["payroll", "pay", "salary", "payslip", "show payslip", "my payslip", "pay slip", "salary slip"],
    description: "Pay runs, components, payslips",
  },
  {
    section: "expenses",
    label: "Expenses",
    to: "/expenses",
    icon: Receipt,
    roles: ALL,
    gKey: "x",
    lens: ["admin", "manager", "employee", "payroll"],
    sub: [{ label: "New Expense", to: "/expenses/new" }],
    bottomNavPriority: 5,
    keywords: ["expense", "expenses", "reimburse", "claim"],
    description: "Claims and approvals",
  },
  {
    section: "documents",
    label: "Documents",
    to: "/admin/documents",
    icon: FileText,
    roles: SELF,
    gKey: "d",
    lens: ["admin", "manager", "employee"],
    bottomNavPriority: 13,
    keywords: ["documents", "library", "files", "policy"],
    description: "Company document library",
  },
  {
    section: "assets",
    label: "Assets",
    to: "/assets",
    icon: Package,
    roles: SELF,
    gKey: "k",
    lens: ["admin", "manager", "employee"],
    sub: [{ label: "My Assets", to: "/my-assets" }],
    bottomNavPriority: 12,
    keywords: ["assets", "laptop", "equipment", "inventory", "my assets"],
    description: "Asset inventory and assignment",
  },
  {
    section: "er",
    label: "ER",
    to: "/admin/er-cases",
    icon: HeartHandshake,
    roles: ADMIN_MGR,
    gKey: "v",
    lens: ["admin", "manager"],
    keywords: ["employee relations", "er", "cases", "grievance", "disciplinary"],
    description: "Employee relations cases",
  },
  {
    section: "performance",
    label: "Performance",
    to: "/platform/performance",
    icon: Star,
    roles: SELF,
    gKey: "f",
    lens: ["admin", "manager", "employee"],
    bottomNavPriority: 10,
    keywords: ["performance", "goals", "reviews"],
    description: "Goals, reviews, calibration",
  },
  {
    section: "learning",
    label: "Learning",
    to: "/platform/learning",
    icon: GraduationCap,
    roles: SELF,
    gKey: "n",
    lens: ["admin", "manager", "employee"],
    bottomNavPriority: 11,
    keywords: ["learning", "courses", "certifications", "training"],
    description: "Courses, certifications, talent",
  },
  {
    section: "helpdesk",
    label: "Helpdesk",
    to: "/admin/hrhelp-cases",
    icon: LifeBuoy,
    roles: SELF,
    gKey: "i",
    lens: ["admin", "manager", "employee"],
    bottomNavPriority: 14,
    keywords: ["helpdesk", "help", "support", "ticket", "hr help"],
    description: "HR help requests and tickets",
  },
  {
    section: "reports",
    label: "Reports",
    to: "/reports",
    icon: BarChart3,
    roles: ["SuperAdmin", "HR", "Manager", "PayrollViewer"],
    gKey: "e",
    lens: ["admin", "manager", "payroll"],
    sub: [
      { label: "Forecasting", to: "/forecasting" },
      { label: "Demand & drivers", to: "/forecasting/demand" },
      { label: "Scenarios", to: "/forecasting/scenarios" },
      { label: "Accuracy", to: "/forecasting/accuracy" },
      { label: "Data Quality", to: "/data-quality" },
    ],
    bottomNavPriority: 6,
    keywords: ["reports", "analytics", "headcount", "audit", "forecast"],
    description: "Headcount, leave, labour cost",
  },
  {
    section: "workflows",
    label: "Workflows",
    to: "/admin/workflow",
    icon: Workflow,
    roles: ADMIN_MGR,
    gKey: "w",
    lens: ["admin", "manager"],
    keywords: ["workflow", "approval", "process", "automation"],
    description: "Approval workflows and automation",
  },
  {
    section: "integrations",
    label: "Integrations",
    to: "/platform/integrations",
    icon: Plug,
    roles: ADMIN_MGR,
    gKey: "u",
    lens: ["admin", "manager"],
    keywords: ["integrations", "api", "webhooks", "credentials"],
    description: "Connected systems and credentials",
  },
  {
    section: "admin",
    label: "Admin",
    to: "/client-onboarding",
    icon: Building,
    roles: ADMIN,
    gKey: "a",
    lens: ["admin"],
    sub: [
      { label: "Import / Export", to: "/import" },
      { label: "Background Jobs", to: "/jobs" },
      { label: "Security (MFA)", to: "/mfa" },
      { label: "Compliance", to: "/platform/compliance" },
      { label: "Design System", to: "/design" },
      { label: "Theme Studio", to: "/theme" },
      { label: "Design Gallery", to: "/design-gallery" },
    ],
    keywords: ["admin", "compliance", "client", "onboarding", "import", "export", "jobs", "mfa", "design"],
    description: "Compliance, client onboarding, system",
  },
]

/* ------------------------------------------------------------------ *
 * Alias routes — old paths that render the same screen as a canonical
 * route. App.tsx serves each of these as a guarded `<Navigate replace>`
 * to the canonical target, so bookmarks keep working. Nothing in the nav
 * (rail, palette, drawer, shortcuts, breadcrumbs) may point at an alias.
 * ------------------------------------------------------------------ */
export const ADMIN_ALIASES: Record<string, string> = {
  "/admin/user-admin": "/admin/users",
  "/admin/tenant-branding": "/admin/branding",
  "/admin/module-entitlements": "/admin/entitlements",
  "/admin/workflow-approval": "/admin/workflow",
  "/admin/integration-credentials": "/admin/integrations",
  "/admin/backup-restore": "/admin/backup",
  "/admin/locale-config": "/admin/locale",
  "/admin/ad-03": "/admin/locale",
  "/admin/ad-09": "/admin/retention-export",
  "/admin/rc-03": "/admin/candidate-stages",
  "/admin/hr-01": "/people",
  "/admin/hr-05": "/admin/multi-location-assignments",
  "/admin/lv-01": "/admin/leave-types",
  "/admin/rc-05": "/admin/offer-approvals",
  "/admin/sc-04": "/admin/hard-constraints",
  "/admin/sc-07": "/admin/coverage-gaps",
  "/admin/sc-10": "/admin/planned-vs-actual",
  "/admin/tm-02": "/admin/attendance-policies",
  "/admin/tm-03": "/admin/cross-midnight-overtime",
  "/admin/tm-04": "/admin/shift-based-attendance",
  "/admin/tm-05": "/admin/timesheet-lock",
  "/admin/an-06": "/admin/plan-reconciliation",
  "/admin/bn-02": "/admin/employer-contributions",
  "/admin/ai-02": "/admin/document-classification",
  "/admin/ob-04": "/admin/probation-tracking",
  "/admin/project-status": "/project-status",
  "/admin/design-gallery": "/design-gallery",
  "/admin/theme": "/theme",
  "/admin/data-quality": "/data-quality",
}

export interface AdminConsoleItem {
  label: string
  to: string
  roles: NavRole[]
}

export interface AdminGroup {
  name: string
  icon: NavIcon
  items: AdminConsoleItem[]
}

const SH: NavRole[] = ["SuperAdmin", "HR"]
const S: NavRole[] = ["SuperAdmin"]

function admin(label: string, to: string, roles: NavRole[] = SH): AdminConsoleItem {
  return { label, to, roles }
}

/**
 * Admin console — every canonical (non-alias) /admin/* route, in named
 * groups. Never a flat list. The five admin paths that are also section
 * canonicals (org-chart, documents, er-cases, hrhelp-cases, workflow) are
 * listed here too: the console is the complete admin index, sections are
 * role-aware shortcuts — one screen per function either way.
 */
export const ADMIN_GROUPS: AdminGroup[] = [
  {
    name: "Organization",
    icon: Building,
    items: [
      admin("User Admin", "/admin/users"),
      admin("Company Branding", "/admin/branding", S),
      admin("Module Entitlements", "/admin/entitlements", S),
      admin("Org Chart", "/admin/org-chart", SELF),
      admin("Departments & Cost Centres", "/admin/departments-cost-centres"),
      admin("Employment Status", "/admin/employment-status"),
      admin("Multi-location Assignments", "/admin/multi-location-assignments"),
      admin("Manager Assignments", "/admin/manager-assignments"),
      admin("Contingent Workers", "/admin/contingent-workers"),
      admin("Transfer & Promotion", "/admin/transfer-promotion"),
      admin("Rehire Handling", "/admin/rehire-handling"),
      admin("Custom Fields", "/admin/custom-fields"),
      admin("ESS Profile", "/admin/essprofile"),
      admin("Historical Record", "/admin/historical-record"),
      admin("Announcements Directory", "/admin/announcements-directory"),
      admin("Knowledge Base", "/admin/knowledge-base"),
      admin("ER Cases", "/admin/er-cases", ADMIN_MGR),
      admin("HR Help Cases", "/admin/hrhelp-cases", SELF),
    ],
  },
  {
    name: "Talent",
    icon: Target,
    items: [
      admin("Candidate Stages", "/admin/candidate-stages"),
      admin("Requisition Stages", "/admin/requisition-stages"),
      admin("Hiring Plans", "/admin/hiring-plans"),
      admin("Offer Approvals", "/admin/offer-approvals"),
      admin("Interview Scheduling", "/admin/interview-scheduling"),
      admin("Funnel Analytics", "/admin/funnel-analytics"),
      admin("Probation Tracking", "/admin/probation-tracking"),
      admin("Ten-step Journey", "/admin/ten-step-journey"),
      admin("Resumable Checklists", "/admin/resumable-checklists"),
      admin("Information Collection", "/admin/information-collection"),
      admin("Equipment Access", "/admin/equipment-access"),
      admin("Gap Detection", "/admin/gap-detection"),
      admin("Demand Staffing", "/admin/demand-staffing"),
      admin("Renewal Reminders", "/admin/renewal-reminders"),
    ],
  },
  {
    name: "Time & Scheduling",
    icon: Clock,
    items: [
      admin("Attendance Policies", "/admin/attendance-policies"),
      admin("Cross-midnight Overtime", "/admin/cross-midnight-overtime"),
      admin("Shift-based Attendance", "/admin/shift-based-attendance"),
      admin("Timesheet Lock", "/admin/timesheet-lock"),
      admin("Timesheets", "/admin/timesheets"),
      admin("Schedule Views", "/admin/schedule-views"),
      admin("Hard Constraints", "/admin/hard-constraints"),
      admin("Soft Constraints", "/admin/soft-constraints"),
      admin("Coverage Gaps", "/admin/coverage-gaps"),
      admin("Swaps & Replacements", "/admin/swaps-replacements"),
      admin("Team Availability", "/admin/team-availability"),
      admin("Manager Availability", "/admin/manager-availability"),
      admin("Planned vs Actual", "/admin/planned-vs-actual"),
      admin("Demand Forecasting", "/admin/demand-forecasting"),
      admin("Forecast Exception", "/admin/forecast-exception"),
      admin("Model Versioning", "/admin/model-versioning"),
    ],
  },
  {
    name: "Leave",
    icon: Book,
    items: [
      admin("Leave Types", "/admin/leave-types"),
      admin("Availability Leave", "/admin/availability-leave"),
      admin("Leave to Payroll", "/admin/leave-to-payroll"),
    ],
  },
  {
    name: "Pay & Benefits",
    icon: Banknote,
    items: [
      admin("Pay Schedule", "/admin/pay-schedule"),
      admin("Earnings & Deductions", "/admin/earnings-deductions"),
      admin("Employer Contributions", "/admin/employer-contributions"),
      admin("Bank Export", "/admin/bank-export"),
      admin("Salary Revisions", "/admin/salary-revisions"),
      admin("Headcount Cost", "/admin/headcount-cost"),
    ],
  },
  {
    name: "Performance & Learning",
    icon: GraduationCap,
    items: [
      admin("Goals & OKR", "/admin/goals-okr"),
      admin("Competency Calibration", "/admin/competency-calibration"),
      admin("Improvement Plans", "/admin/improvement-plans"),
      admin("Promotion Readiness", "/admin/promotion-readiness"),
      admin("Succession Planning", "/admin/succession-planning"),
      admin("Skill Gaps", "/admin/skill-gaps"),
      admin("Skill Taxonomy", "/admin/skill-taxonomy"),
      admin("Learning Paths", "/admin/learning-paths"),
      admin("Learning Analytics", "/admin/learning-analytics"),
      admin("Training Assignments", "/admin/training-assignments"),
      admin("Mentoring & Development", "/admin/mentoring-development"),
      admin("Certifications", "/admin/certifications"),
    ],
  },
  {
    name: "Platform",
    icon: Plug,
    items: [
      admin("Workflow Approval", "/admin/workflow", ADMIN_MGR),
      admin("Integration Credentials", "/admin/integrations"),
      admin("Integrations Hub", "/admin/integrations-hub"),
      admin("External Integration", "/admin/external-integration"),
      admin("Process Automation", "/admin/process-automation"),
      admin("Backup / Restore", "/admin/backup"),
      admin("Updates", "/admin/updates", S),
      admin("Feature Flags", "/admin/feature-flags", S),
      admin("Locale Config", "/admin/locale"),
      admin("AI Drafting", "/admin/ai-03"),
      admin("AI Summarisation", "/admin/ai-04"),
      admin("Document Classification", "/admin/document-classification"),
      admin("Policy Search", "/admin/policy-search"),
      admin("Mobile Interaction", "/admin/mobile-interaction"),
      admin("Platform Showcase", "/admin/platform-showcase"),
      admin("Scheduled Reporting", "/admin/scheduled-reporting"),
      admin("Saved Views", "/admin/saved-views"),
      admin("Templates, Drafts & Publish", "/admin/templates-drafts-publish"),
      admin("Plan Reconciliation", "/admin/plan-reconciliation"),
    ],
  },
  {
    name: "Compliance & Audit",
    icon: FileText,
    items: [
      admin("Compliance Center", "/admin/compliance"),
      admin("Export & Erasure", "/admin/export-erasure"),
      admin("Retention Export", "/admin/retention-export"),
      admin("Break-glass", "/admin/break-glass", S),
      admin("Prohibitions", "/admin/prohibitions"),
      admin("States & Discipline", "/admin/states-discipline"),
      admin("Jurisdiction Rules", "/admin/jurisdiction-rules"),
      admin("Validation & Duplicates", "/admin/validation-duplicates"),
      admin("Documents Library", "/admin/documents", SELF),
      admin("Documents Expiry", "/admin/documents-expiry"),
    ],
  },
]

/* ------------------------------------------------------------------ *
 * Derived views — pure filters over the config above.
 * ------------------------------------------------------------------ */

/** Automatic lens for a role (D3: no manual switcher). */
export function lensForRole(role?: string | null): NavLens {
  if (role === "SuperAdmin" || role === "HR") return "admin"
  if (role === "Manager") return "manager"
  if (role === "PayrollViewer") return "payroll"
  return "employee"
}

/** Sections visible to a role. */
export function visibleSections(role?: string | null): NavSection[] {
  return NAV_SECTIONS.filter((s) => s.roles.includes(role as NavRole))
}

/** Sections in a lens (agrees with visibleSections for the mapped role). */
export function sectionsForLens(lens: NavLens): NavSection[] {
  return NAV_SECTIONS.filter((s) => s.lens.includes(lens))
}

/** Admin console groups with items filtered to a role; empty groups dropped. */
export function visibleAdminGroups(role?: string | null): AdminGroup[] {
  const out: AdminGroup[] = []
  for (const g of ADMIN_GROUPS) {
    const items = g.items.filter((i) => i.roles.includes(role as NavRole))
    if (items.length > 0) out.push({ ...g, items })
  }
  return out
}

/** Flat list of every admin console target (for parity tests). */
export function allAdminTargets(): string[] {
  return ADMIN_GROUPS.flatMap((g) => g.items.map((i) => i.to))
}

/** Bottom bar: lowest-priority visible sections, max 5 (AC6). */
export function bottomNavSections(role?: string | null): NavSection[] {
  return visibleSections(role)
    .filter((s) => s.bottomNavPriority !== undefined)
    .sort((a, b) => (a.bottomNavPriority ?? 99) - (b.bottomNavPriority ?? 99))
    .slice(0, 5)
}

export interface GotoEntry {
  label: string
  to: string
  gKey: string
}

/**
 * "g <letter>" registry. Section letters first, then the two historic
 * sub-screen letters (s = scheduling, g = forecasting) so every old
 * sequence keeps working. ShortcutHelp renders from this same list.
 */
export const GOTO_ENTRIES: GotoEntry[] = [
  ...NAV_SECTIONS.filter((s) => s.gKey).map((s) => ({
    label: s.label,
    to: s.to,
    gKey: s.gKey as string,
  })),
  { label: "Scheduling", to: "/scheduling", gKey: "s" },
  { label: "Forecasting", to: "/forecasting", gKey: "g" },
]

/* ------------------------------------------------------------------ *
 * Breadcrumbs — Home / Section / Sub, driven by this config.
 * ------------------------------------------------------------------ */

export interface BreadcrumbItem {
  label: string
  href?: string
}

/** Breadcrumb trail for a bare (scope-stripped) pathname. */
export function breadcrumbFor(pathname: string): BreadcrumbItem[] {
  const items: BreadcrumbItem[] = [{ label: "Home", href: "/dashboard" }]
  if (pathname === "/" || pathname.startsWith("/dashboard")) return items

  // Sub-screen first (exact or parameterised child, e.g. /leave/ledger/7).
  for (const s of NAV_SECTIONS) {
    for (const sub of s.sub ?? []) {
      if (pathname === sub.to || pathname.startsWith(`${sub.to}/`)) {
        items.push({ label: s.label, href: s.to })
        items.push({ label: sub.label })
        return items
      }
    }
  }
  // Section canonical (exact or nested).
  for (const s of NAV_SECTIONS) {
    if (pathname === s.to || pathname.startsWith(`${s.to}/`)) {
      items.push({ label: s.label })
      return items
    }
  }
  // Admin console: Home / <group> / <item>.
  for (const g of ADMIN_GROUPS) {
    const hit = g.items.find((i) => pathname === i.to || pathname.startsWith(`${i.to}/`))
    if (hit) {
      items.push({ label: "Admin", href: "/client-onboarding" })
      items.push({ label: g.name })
      items.push({ label: hit.label })
      return items
    }
  }
  return items
}

/* ------------------------------------------------------------------ *
 * Quick Action palette — visible sections + canonical admin links.
 * ------------------------------------------------------------------ */

export interface PaletteItem {
  id: string
  label: string
  description?: string
  icon: NavIcon
  keywords: string[]
  to: string
  group: string
}

function sectionKeywords(s: NavSection): string[] {
  const base = [s.label.toLowerCase(), s.section, ...(s.keywords ?? [])]
  for (const sub of s.sub ?? []) base.push(sub.label.toLowerCase())
  return [...new Set(base)]
}

/** Palette entries for a role: exactly its visible sections + its canonical
 *  admin links. No aliases, no hidden-role items (AC5). */
export function paletteItemsFor(role?: string | null): PaletteItem[] {
  const out: PaletteItem[] = visibleSections(role).map((s) => ({
    id: s.section,
    label: `Go to ${s.label}`,
    description: s.description,
    icon: s.icon,
    keywords: sectionKeywords(s),
    to: s.to,
    group: "Navigate",
  }))
  for (const g of visibleAdminGroups(role)) {
    for (const item of g.items) {
      // Sections already cover their canonical admin screen; the console
      // entry would be a duplicate palette row.
      if (NAV_SECTIONS.some((s) => s.to === item.to)) continue
      const slug = item.to.replace("/admin/", "")
      out.push({
        id: `admin-${slug}`,
        label: `Go to ${item.label}`,
        description: `${g.name} · Admin console`,
        icon: g.icon,
        keywords: [item.label.toLowerCase(), slug.replace(/-/g, " "), g.name.toLowerCase(), "admin"],
        to: item.to,
        group: "Admin",
      })
    }
  }
  return out
}

/** All palette entries irrespective of role (tests, conversational search). */
export function allPaletteItems(): PaletteItem[] {
  return paletteItemsFor("SuperAdmin")
}
