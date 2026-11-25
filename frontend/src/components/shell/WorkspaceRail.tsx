import { useEffect, useState, type ComponentType } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useTenant } from "@/context/TenantContext"
import { registerGoto, unregisterGoto } from "@/lib/keyboard"
import { barePath, useTenantNav } from "@/lib/tenantPath"
import { TenantSwitcher } from "@/components/shell/TenantSwitcher"
import {
  Activity,
  BarChart3,
  Bed,
  Book,
  Briefcase,
  Building,
  Calendar,
  ChevronDown,
  ChevronRight,
  Clock,
  CreditCard,
  Gift,
  LayoutDashboard,
  Palette,
  PieChart,
  Plug,
  Presentation,
  RefreshCcw,
  Settings,
  Shield,
  Star,
  Target,
  User,
  Users,
} from "lucide-react"

/**
 * Unified 220px sidebar (TradeMarkk obsidian shell).
 *
 * Merges the old icon-only workspace rail and the secondary sidebar into
 * ONE navigation: brand header, "+ Quick Action" command-palette CTA,
 * categorized groups (OVERVIEW / CORE HR & ESS / TIME & PAYROLL /
 * PLATFORM & ADMIN), a collapsible Admin console holding every /admin/*
 * route, and a bottom-pinned TenantSwitcher.
 *
 * Route paths are the exact App.tsx registrations — never renamed here.
 */

export interface NavItem {
  label: string
  to: string
  icon?: ComponentType<{ className?: string }>
  /** Child links rendered under the item (indented, always visible). */
  sub?: NavItem[]
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

/* Every /admin/* route registered in App.tsx (L243-387), one click away
 * inside the collapsible Admin console. Labels distinguish the legacy
 * aliases of the same screen (e.g. /admin/users vs /admin/user-admin). */
const ADMIN_ITEMS: NavItem[] = [
  { label: "User Admin (/admin/users)", to: "/admin/users" },
  { label: "Tenant Branding (branding)", to: "/admin/branding" },
  { label: "Entitlements", to: "/admin/entitlements" },
  { label: "Workflow Approval (workflow)", to: "/admin/workflow" },
  { label: "Integration Credentials (integrations)", to: "/admin/integrations" },
  { label: "Backup / Restore (backup)", to: "/admin/backup" },
  { label: "Feature Flags", to: "/admin/feature-flags" },
  { label: "Locale Config (locale)", to: "/admin/locale" },
  { label: "Retention Export", to: "/admin/retention-export" },
  { label: "Candidate Stages", to: "/admin/candidate-stages" },
  { label: "Candidate Stages (RC-03)", to: "/admin/rc-03" },
  { label: "Project Status", to: "/admin/project-status" },
  { label: "Design Gallery", to: "/admin/design-gallery" },
  { label: "Theme Studio", to: "/admin/theme" },
  { label: "Site Page: Solutions", to: "/admin/solutions" },
  { label: "Site Page: Resources", to: "/admin/resources" },
  { label: "Site Page: About", to: "/admin/about" },
  { label: "Site Page: Careers", to: "/admin/careers" },
  { label: "Site Page: Contact", to: "/admin/contact" },
  { label: "Site Page: Privacy", to: "/admin/privacy" },
  { label: "Site Page: Terms", to: "/admin/terms" },
  { label: "Site Page: Documentation", to: "/admin/docs" },
  { label: "Site Page: Pricing", to: "/admin/pricing" },
  { label: "Site Page: Security", to: "/admin/security" },
  { label: "Site Page: FAQ", to: "/admin/faq" },
  { label: "Site Page: Industry Detail", to: "/admin/industry-detail" },
  { label: "Site Page: Compare", to: "/admin/compare" },
  { label: "Site Page: Platform Showcase", to: "/admin/platform-showcase" },
  { label: "Site Page: Design Showcase", to: "/admin/design-showcase" },
  { label: "Locale Config (AD-03)", to: "/admin/ad-03" },
  { label: "Retention Export (AD-09)", to: "/admin/ad-09" },
  { label: "Employee Directory (HR-01)", to: "/admin/hr-01" },
  { label: "Multi-Location Assignments (HR-05)", to: "/admin/hr-05" },
  { label: "Leave Types (LV-01)", to: "/admin/lv-01" },
  { label: "Offer Approvals (RC-05)", to: "/admin/rc-05" },
  { label: "Hard Constraints (SC-04)", to: "/admin/sc-04" },
  { label: "Coverage Gaps (SC-07)", to: "/admin/sc-07" },
  { label: "Planned vs Actual (SC-10)", to: "/admin/sc-10" },
  { label: "Attendance Policies (TM-02)", to: "/admin/tm-02" },
  { label: "Cross-Midnight Overtime (TM-03)", to: "/admin/tm-03" },
  { label: "Shift-Based Attendance (TM-04)", to: "/admin/tm-04" },
  { label: "Timesheet Lock (TM-05)", to: "/admin/tm-05" },
  { label: "Plan Reconciliation (AN-06)", to: "/admin/an-06" },
  { label: "Employer Contributions (BN-02)", to: "/admin/bn-02" },
  { label: "Document Classification (AI-02)", to: "/admin/ai-02" },
  { label: "Probation Tracking (OB-04)", to: "/admin/ob-04" },
  { label: "AI Summarisation (AI-04)", to: "/admin/ai-04" },
  { label: "AI Drafting (AI-03)", to: "/admin/ai-03" },
  { label: "Announcements Directory", to: "/admin/announcements-directory" },
  { label: "Approval Workflows", to: "/admin/approval-workflows" },
  { label: "Attendance Policies", to: "/admin/attendance-policies" },
  { label: "Availability & Leave", to: "/admin/availability-leave" },
  { label: "Backup / Restore", to: "/admin/backup-restore" },
  { label: "Bank Export", to: "/admin/bank-export" },
  { label: "Bank Export Integration", to: "/admin/bank-export-integration" },
  { label: "Certifications", to: "/admin/certifications" },
  { label: "Competency Calibration", to: "/admin/competency-calibration" },
  { label: "Contingent Workers", to: "/admin/contingent-workers" },
  { label: "Coverage Gaps", to: "/admin/coverage-gaps" },
  { label: "Cross-Midnight Overtime", to: "/admin/cross-midnight-overtime" },
  { label: "Custom Fields", to: "/admin/custom-fields" },
  { label: "Data Quality", to: "/admin/data-quality" },
  { label: "Demand Forecasting", to: "/admin/demand-forecasting" },
  { label: "Demand Staffing", to: "/admin/demand-staffing" },
  { label: "Departments & Cost Centres", to: "/admin/departments-cost-centres" },
  { label: "Document Classification", to: "/admin/document-classification" },
  { label: "Document Expiry", to: "/admin/documents-expiry" },
  { label: "ESS Profile", to: "/admin/essprofile" },
  { label: "Earnings & Deductions", to: "/admin/earnings-deductions" },
  { label: "Employer Contributions", to: "/admin/employer-contributions" },
  { label: "Employment Status", to: "/admin/employment-status" },
  { label: "Equipment Access", to: "/admin/equipment-access" },
  { label: "Exit Interviews", to: "/admin/exit-interviews" },
  { label: "Export & Erasure", to: "/admin/export-erasure" },
  { label: "External Integration", to: "/admin/external-integration" },
  { label: "Forecast Exceptions", to: "/admin/forecast-exception" },
  { label: "Funnel Analytics", to: "/admin/funnel-analytics" },
  { label: "Gap Detection", to: "/admin/gap-detection" },
  { label: "Goals & OKR", to: "/admin/goals-okr" },
  { label: "HR Help Cases", to: "/admin/hrhelp-cases" },
  { label: "Hard Constraints", to: "/admin/hard-constraints" },
  { label: "Headcount Cost", to: "/admin/headcount-cost" },
  { label: "Headcount Entity", to: "/admin/headcount-entity" },
  { label: "Headcount Hiring", to: "/admin/headcount-hiring" },
  { label: "Headcount Turnover", to: "/admin/headcount-turnover" },
  { label: "Hiring Plans", to: "/admin/hiring-plans" },
  { label: "Historical Record", to: "/admin/historical-record" },
  { label: "Improvement Plans", to: "/admin/improvement-plans" },
  { label: "Information Collection", to: "/admin/information-collection" },
  { label: "Integration Credentials", to: "/admin/integration-credentials" },
  { label: "Integrations Hub", to: "/admin/integrations-hub" },
  { label: "Interview Scheduling", to: "/admin/interview-scheduling" },
  { label: "Jurisdiction Rules", to: "/admin/jurisdiction-rules" },
  { label: "Knowledge Base", to: "/admin/knowledge-base" },
  { label: "Learning Analytics", to: "/admin/learning-analytics" },
  { label: "Learning Paths", to: "/admin/learning-paths" },
  { label: "Leave to Payroll", to: "/admin/leave-to-payroll" },
  { label: "Leave Types", to: "/admin/leave-types" },
  { label: "Locale Config", to: "/admin/locale-config" },
  { label: "Manager Assignments", to: "/admin/manager-assignments" },
  { label: "Manager Availability", to: "/admin/manager-availability" },
  { label: "Mentoring & Development", to: "/admin/mentoring-development" },
  { label: "Mobile Interaction", to: "/admin/mobile-interaction" },
  { label: "Model Versioning", to: "/admin/model-versioning" },
  { label: "Module Entitlements", to: "/admin/module-entitlements" },
  { label: "Multi-Location Assignments", to: "/admin/multi-location-assignments" },
  { label: "Offer Approvals", to: "/admin/offer-approvals" },
  { label: "Org Chart", to: "/admin/org-chart" },
  { label: "PM02 Goals", to: "/admin/pm02goals" },
  { label: "Pay Schedule", to: "/admin/pay-schedule" },
  { label: "Plan Reconciliation", to: "/admin/plan-reconciliation" },
  { label: "Planned vs Actual", to: "/admin/planned-vs-actual" },
  { label: "Policy Search", to: "/admin/policy-search" },
  { label: "Probation Tracking", to: "/admin/probation-tracking" },
  { label: "Process Automation", to: "/admin/process-automation" },
  { label: "Prohibitions", to: "/admin/prohibitions" },
  { label: "Promotion Readiness", to: "/admin/promotion-readiness" },
  { label: "Rehire Handling", to: "/admin/rehire-handling" },
  { label: "Renewal Reminders", to: "/admin/renewal-reminders" },
  { label: "Requisition Stages", to: "/admin/requisition-stages" },
  { label: "Resumable Checklists", to: "/admin/resumable-checklists" },
  { label: "Salary Revisions", to: "/admin/salary-revisions" },
  { label: "Saved Views", to: "/admin/saved-views" },
  { label: "Schedule Views", to: "/admin/schedule-views" },
  { label: "Scheduled Reporting", to: "/admin/scheduled-reporting" },
  { label: "Shift-Based Attendance", to: "/admin/shift-based-attendance" },
  { label: "Skill Gaps", to: "/admin/skill-gaps" },
  { label: "Skill Taxonomy", to: "/admin/skill-taxonomy" },
  { label: "Soft Constraints", to: "/admin/soft-constraints" },
  { label: "States Discipline", to: "/admin/states-discipline" },
  { label: "Succession Planning", to: "/admin/succession-planning" },
  { label: "Swaps & Replacements", to: "/admin/swaps-replacements" },
  { label: "Team Availability", to: "/admin/team-availability" },
  { label: "Templates & Drafts", to: "/admin/templates-drafts-publish" },
  { label: "Ten-Step Journey", to: "/admin/ten-step-journey" },
  { label: "Tenant Branding", to: "/admin/tenant-branding" },
  { label: "Timesheet Lock", to: "/admin/timesheet-lock" },
  { label: "Timesheets", to: "/admin/timesheets" },
  { label: "Training Assignments", to: "/admin/training-assignments" },
  { label: "Transfer & Promotion", to: "/admin/transfer-promotion" },
  { label: "User Admin", to: "/admin/user-admin" },
  { label: "Validation & Duplicates", to: "/admin/validation-duplicates" },
  { label: "Workflow Approval", to: "/admin/workflow-approval" },
  { label: "Break-glass", to: "/admin/break-glass" },
  { label: "Compliance Center", to: "/admin/compliance" },
]

/* "g <letter>" navigation targets — same keys the old workspace rail
 * registered, so CommandPalette entries and ShortcutHelp keep working. */
const GOTO_AREAS: { label: string; to: string; gotoKey: string }[] = [
  { label: "Home", to: "/dashboard", gotoKey: "h" },
  { label: "People", to: "/people", gotoKey: "p" },
  { label: "Time", to: "/time", gotoKey: "t" },
  { label: "Scheduling", to: "/scheduling", gotoKey: "s" },
  { label: "Forecast", to: "/forecasting", gotoKey: "g" },
  { label: "Leave", to: "/leave", gotoKey: "l" },
  { label: "Recruiting", to: "/recruiting", gotoKey: "r" },
  { label: "Payroll", to: "/platform/payroll", gotoKey: "y" },
  { label: "Performance", to: "/platform/performance", gotoKey: "f" },
  { label: "Learning", to: "/platform/learning", gotoKey: "n" },
  { label: "Reports", to: "/reports", gotoKey: "e" },
  { label: "Admin", to: "/client-onboarding", gotoKey: "a" },
]

const GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
      { label: "Reports", to: "/reports", icon: PieChart },
      {
        label: "Forecasting",
        to: "/forecasting",
        icon: BarChart3,
        sub: [
          { label: "Demand & drivers", to: "/forecasting/demand" },
          { label: "Scenarios", to: "/forecasting/scenarios" },
          { label: "Accuracy", to: "/forecasting/accuracy" },
        ],
      },
      { label: "Project Status", to: "/project-status", icon: Presentation },
    ],
  },
  {
    label: "Core HR & ESS",
    items: [
      {
        label: "People",
        to: "/people",
        icon: Users,
        sub: [
          { label: "Departments", to: "/people/departments" },
          { label: "Jobs", to: "/people/jobs" },
          { label: "Locations", to: "/people/locations" },
          { label: "Positions", to: "/people/positions" },
          { label: "Cost centres", to: "/people/cost-centers" },
        ],
      },
      { label: "Recruiting", to: "/recruiting", icon: Target },
      { label: "Onboarding", to: "/onboarding", icon: Briefcase },
      { label: "Offboarding", to: "/offboarding", icon: User },
      { label: "Assets", to: "/assets", icon: Briefcase },
      { label: "My Assets", to: "/my-assets", icon: Briefcase },
      { label: "ESS", to: "/ess", icon: User },
      { label: "Core HR", to: "/platform", icon: Building },
      { label: "Benefits", to: "/platform/benefits", icon: Gift },
    ],
  },
  {
    label: "Time & Payroll",
    items: [
      { label: "Time", to: "/time", icon: Clock },
      {
        label: "Scheduling",
        to: "/scheduling",
        icon: Calendar,
        sub: [{ label: "Roster Builder", to: "/scheduling/roster" }],
      },
      {
        label: "Leave",
        to: "/leave",
        icon: Bed,
        sub: [{ label: "Ledger & Reconciliation", to: "/leave/ledger" }],
      },
      {
        label: "Payroll",
        to: "/platform/payroll",
        icon: CreditCard,
        sub: [
          { label: "Pay runs", to: "/platform/payroll/runs" },
          { label: "Pay setup", to: "/platform/payroll/setup" },
          { label: "Payroll overview", to: "/platform/payroll/overview" },
        ],
      },
    ],
  },
  {
    label: "Platform & Admin",
    items: [
      { label: "Performance", to: "/platform/performance", icon: Star },
      { label: "Learning", to: "/platform/learning", icon: Book },
      { label: "Compliance", to: "/platform/compliance", icon: Shield },
      { label: "Integrations", to: "/platform/integrations", icon: Plug },
      { label: "Data Quality", to: "/data-quality", icon: Activity },
      { label: "Import / Export", to: "/import", icon: RefreshCcw },
      { label: "Background Jobs", to: "/jobs", icon: Settings },
      { label: "Security (MFA)", to: "/mfa", icon: Shield },
      { label: "Break-glass", to: "/admin/break-glass", icon: Shield },
      { label: "Compliance Center", to: "/admin/compliance", icon: Shield },
      { label: "Admin", to: "/client-onboarding", icon: Building },
      { label: "Design System", to: "/design", icon: Palette },
      {
        label: "Theme & Gallery",
        to: "/theme",
        icon: Briefcase,
        sub: [
          { label: "Theme Studio", to: "/theme" },
          { label: "Design Gallery", to: "/design-gallery" },
        ],
      },
    ],
  },
]

/** Light the item on its workspace-relative path. */
function isActivePath(bare: string, to: string): boolean {
  if (to === "/dashboard") return bare.startsWith("/dashboard")
  if (to === "/reports") return bare.startsWith("/reports")
  if (to === "/client-onboarding") return bare.startsWith("/client-onboarding")
  if (to === "/people") {
    // Core HR (locations, cost centres, positions) is people structure.
    return bare.startsWith("/people") || bare === "/platform"
  }
  if (to === "/theme") {
    return bare.startsWith("/theme") || bare.startsWith("/design-gallery")
  }
  return bare.startsWith(to)
}

export function WorkspaceRail() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const { tenant } = useTenant()
  const brandName = tenant?.name || "LibrePeople"
  const [adminOpen, setAdminOpen] = useState(false)
  // Admin routes are global, never tenant-prefixed — use bare path
  const navTo = (p: string) => (p.startsWith("/admin") ? p : tenantNav.to(p))

  // "g + letter" shortcuts — the registrations the old workspace rail owned.
  // Client-side navigation: a full-page reload here loses app state and,
  // in a tenant workspace, the /t/:slug scope itself.
  useEffect(() => {
    GOTO_AREAS.forEach((area) => {
      registerGoto(area.gotoKey, {
        label: `Go to ${area.label}`,
        keys: `g ${area.gotoKey}`,
        description: `Navigate to ${area.label}`,
        group: "Navigation",
        run: () => navigate(tenantNav.to(area.to)),
      })
    })
    return () => GOTO_AREAS.forEach((area) => unregisterGoto(area.gotoKey))
  }, [navigate, tenantNav])

  const bare = barePath(pathname)

  const openAdmin = isActiveAdmin(bare)

  return (
    <nav
      aria-label="Workspace"
      className="sidebar-obsidian hidden lg:flex flex-col w-[var(--sidebar-width)] shrink-0 border-r border-[color:var(--border)] bg-[color:var(--bg-shell)] sticky top-[var(--topbar-height)] h-[calc(100vh-var(--topbar-height))] overflow-hidden"
    >
      {/* Brand header */}
      <Link
        to={tenantNav.to("/dashboard")}
        className="flex items-center gap-2.5 px-3 py-2.5 border-b border-[color:var(--border)] shrink-0 hover:bg-[color:var(--surface-hover)] transition-colors"
      >
        {tenant?.logo_url ? (
          <img src={tenant.logo_url} alt="" className="h-7 w-7 rounded-md object-contain" />
        ) : (
          <span className="brand-mark" aria-hidden="true">
            K
          </span>
        )}
        <span className="text-sm font-semibold text-fg truncate">{brandName}</span>
      </Link>

      {/* Scrollable region: CTA + groups */}
      <div className="flex-1 min-h-0 overflow-y-auto px-2 pt-2.5 pb-3">
        {/* "+ Quick Action" — opens the command palette */}
        <button
          type="button"
          onClick={() => window.dispatchEvent(new CustomEvent("karmathy:open-command-palette"))}
          className="quick-action-cta mb-3 inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-semibold shadow-sm"
        >
          + Quick Action
        </button>

        {GROUPS.map((group) => (
          <div key={group.label} className="mb-3">
            <p className="px-2 mb-1 text-[10px] font-semibold uppercase tracking-widest text-fg-muted">
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => (
                <SidebarEntry key={item.to + item.label} item={item} bare={bare} tenantNav={tenantNav} />
              ))}
            </ul>
          </div>
        ))}

        {/* Collapsible Admin console — every /admin/* route, one click away. */}
        <div className="mb-3 border-t border-[color:var(--border)] pt-2">
          <button
            type="button"
            onClick={() => setAdminOpen((v) => !v)}
            aria-expanded={adminOpen}
            className={cn(
              "nav-item w-full text-left text-xs uppercase tracking-widest text-fg-muted hover:text-fg",
              openAdmin && "text-fg"
            )}
          >
            <span className="nav-icon" aria-hidden="true">
              {adminOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </span>
            Admin console
            <span className="ml-auto text-[10px] tabular-nums text-fg-subtle">{ADMIN_ITEMS.length}</span>
          </button>
          {adminOpen && (
            <ul className="mt-0.5 space-y-0.5">
              {ADMIN_ITEMS.map((item) => {
                const active = bare === item.to
                return (
                  <li key={item.to}>
                    <Link
                      to={navTo(item.to)}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "nav-item !py-1.5 pl-8 text-xs",
                        active && "nav-item-active"
                      )}
                    >
                      <span className="flex-1 min-w-0 truncate">{item.label}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>

      {/* Bottom-pinned tenant switcher */}
      <div className="shrink-0 border-t border-[color:var(--border)] p-2 bg-[color:var(--bg-shell)]">
        <TenantSwitcher />
      </div>
    </nav>
  )
}

function isActiveAdmin(bare: string): boolean {
  return bare.startsWith("/admin")
}

/**
 * One sidebar entry: a link with optional always-visible sub-links.
 */
function SidebarEntry({
  item,
  bare,
  tenantNav,
}: {
  item: NavItem
  bare: string
  tenantNav: { to: (path: string) => string }
}) {
  const active = isActivePath(bare, item.to)
  const Icon = item.icon
  const resolve = (p: string) => (p.startsWith("/admin") ? p : tenantNav.to(p))

  return (
    <li>
      <Link
        to={resolve(item.to)}
        aria-current={active ? "page" : undefined}
        className={cn("nav-item", active && "nav-item-active")}
      >
        {Icon && (
          <span className="nav-icon" aria-hidden="true">
            <Icon className="w-4 h-4" />
          </span>
        )}
        <span className="flex-1 min-w-0 truncate">{item.label}</span>
      </Link>
      {item.sub && item.sub.length > 0 && (
        <ul className="mt-0.5 mb-1 space-y-0.5">
          {item.sub.map((sub) => {
            const subActive = bare === sub.to
            return (
              <li key={sub.to + sub.label}>
                <Link
                  to={resolve(sub.to)}
                  aria-current={subActive ? "page" : undefined}
                  className={cn("nav-item !py-1.5 pl-9 text-xs", subActive && "nav-item-active")}
                >
                  <span className="flex-1 min-w-0 truncate">{sub.label}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </li>
  )
}
