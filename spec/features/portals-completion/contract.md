# Feature: portals-completion
## Behavior
Complete the five role portals so each dashboard is useful (real counts/tasks, zero fake KPIs) and each core journey works end-to-end from the portal: Associate (ESS: clock, leave request, payslips, tasks), Manager (approve leave/timesheets/swaps, team view), HR (cases, requisitions, terminations, payroll prep via existing payroll pages), PayrollViewer (runs, payslips, labor cost), SuperAdmin (users, flags, branding, tenant health). Consistent nav (WorkspaceRail), responsive, a11y (captions, aria, focus, 44px targets).
## Acceptance criteria
1. No mockSparkline/trendValue literals or computed fakes (e.g. gross≈net×1.3, "Since 09:00 AM") remain in components/home/*; every KPI shows a live value with real hint or no trend element; pnpm --filter frontend test passes.
2. Associate: from AssociateHome+ESSHub can clock in/out, submit leave request, view balances/payslips/tasks; empty states + role gates hold. Manager: from ManagerHome can approve/reject a leave, timesheet, swap inline (or one click to the exact row) without full-page reload; team attendance/goals/reviews link to correct routes.
3. HR: from HRHome can reach open cases, requisitions, terminations, headcount, violations, and payroll-prep (PayrollSetup/PayRuns) with working links. Payroll: from PayrollHome can open runs list, run detail (process/approve/finalize per role), setup, labor cost; read-only banner removed or accurate.
4. SuperAdmin: UserAdmin (create/role/reset/impersonate), ModuleEntitlements, TenantBranding all work; HR role sees what App.tsx promises (fix gate mismatch either side); WorkspaceRail admin list de-duplicated (<20 entries, no double aliases); responsive ≤360px + axe/a11y checks pass.
5. All portal data comes from existing backend endpoints; any missing endpoint → mark journey INCOMPLETE, do not invent client-side data.
## Non-goals
No new backend endpoints or schema changes. No new global routes except per rule below. No redesign of Layout/design tokens.
## Interfaces / data
Reuse only: leave/requests + approve, time/timesheets + approve + /today, scheduling/swaps + approve, performance/goals|reviews, payroll/runs|payslips|periods|components|pay-profiles, reports/headcount|labor-cost|audit, core-hr/cases, requisitions, offboarding/terminations, auth/users CRUD, onboarding-portal/clients settings|feature-flags, ess/* (profile/notifications/files/directory/org-chart/announcements). No migrations, no config changes. New page allowed ONLY with justification comment + route registration in both top-level and /t/:slug/* scopes + rail entry; else INCOMPLETE.
## Test plan
- Slice 1 ESS: extend ess_hub_test_suite.py + frontend ESSHub tests.
- Slice 2 Manager: extend leave/time/scheduling suites (approve/reject paths); frontend ManagerHome approve-action tests.
- (Slices 3-5 HR/Payroll/SuperAdmin: separate tasks, same pattern.)
- All: frontend typecheck, vitest run, backend relevant suite green; manual keyboard + 360px pass.
## Risk tier
2 (normal; frontend-only, reversible, role-gated).
## Rollback
Per slice: revert slice's home/page files + rail/route edits; no data migration so DB untouched.
## Open decisions — RESOLVED by lead 2026-11-26
D1 (HR vs SuperAdmin gating for Entitlements/Branding): FAIL CLOSED — verify backend first; default = tighten App.tsx routes to SuperAdmin-only to match the pages, UNLESS backend explicitly allows HR (then widen UI). Never widen UI beyond backend.
D2 (manager team-availability): flag-config + leave/swap inbox is sufficient; NO new team-calendar view (new feature, out of scope).
D3 (fake KPI treatment): DROP entirely (do not compute deltas — needs nonexistent backend aggregations); keep only live values.
