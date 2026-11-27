# Feature: Phase C — Shell + navigation rebuild
## Behavior
Replace the current 4-group rail with one role-aware IA driven by a single config (frontend/src/lib/nav.ts, new): Overview, People, Org, Recruit, Onboard, Attendance+Time, Leave, Comp, Payroll, Expenses, Documents, Assets, ER, Performance, Learning, Helpdesk, Reports, Workflows, Integrations, Admin — plus Manager / Employee / Payroll lenses (pure filters over the same config). Every nav item points at an existing App.tsx route. Quick Action palette, drawer, bottom nav, breadcrumbs, and g-shortcuts all render from the config.
## Acceptance criteria
1. No /t/ targets in nav config + shell; /t/acme/leave/ledger?page=2 lands on /leave/ledger?page=2 (extends shell/single-tenant.test.tsx).
2. Each section lands on its canonical path for an authorized role and 403s otherwise: Overview→/dashboard; People→/people; Org→/admin/org-chart; Recruit→/recruiting; Onboard→/onboarding; Attendance+Time→/time (+/scheduling/roster); Leave→/leave (+/leave/ledger); Comp→/platform/benefits; Payroll→/platform/payroll (+/runs,/setup,/overview); Expenses→/expenses; Documents→/admin/documents; Assets→/assets (+/my-assets); ER→/admin/er-cases; Performance→/platform/performance; Learning→/platform/learning; Helpdesk→/admin/hrhelp-cases; Reports→/reports (+/forecasting*, /data-quality); Workflows→/admin/workflow; Integrations→/platform/integrations; Admin→/client-onboarding.
3. Alias routes become Navigate replace to canonical (one screen per function; full list in implementation notes). Zero inbound links outside App.tsx/tests.
4. Admin console lists all ~125 admin routes in named groups (Organization, Talent, Time & Scheduling, Leave, Pay & Benefits, Performance & Learning, Platform, Compliance & Audit), never a flat list; a test asserts rail↔routes parity.
5. Quick Action palette contains exactly the visible sections + canonical admin links for the current role; CmdK/Ctrl+K, ?, t, Esc and all g-letters keep working; help sheet renders from the same registry. g-letters: Org=o, Comp=c, Documents=d, ER=v, Helpdesk=i, Workflows=w (others unchanged).
6. Responsive: rail only lg+; <lg uses config-driven drawer + one bottom bar, max 5 items from config priority.
## Non-goals
No page-content redesigns (Phase D); no backend/role-model changes; no new routes, modules, or path renames; no marketing-page touch.
## Interfaces / data
New lib/nav.ts: { section, label, to, icon, roles[], gKey?, lens[], sub?, bottomNavPriority? }. No schema/migration/config changes. Breadcrumbs extend Layout per new sections.
## Test plan
Extend shell/single-tenant.test.tsx (redirect + no-/t/-links); new shell/nav-config.test.tsx (every to exists in App.tsx, no alias in palette, rail↔routes parity, ShortcutHelp↔GOTO match); role tests render rail per role per mapping table; then frontend typecheck, production build, targeted vitest run. All green.
## Risk tier
2 (normal).
## Rollback
Revert the commit. Alias Navigate entries keep old bookmarks working during and after rollout; no migration to unwind.
## Open decisions — RESOLVED by lead 2026-11-27
D1 Comp maps to /platform/benefits + admin salary-revisions (no new page). D2 nav hides admin-only items per role; direct URLs still 403 (enforcement unchanged). D3 lenses automatic by role (no manual switcher). D4 g-letters assigned: Org=o, Comp=c, Documents=d, ER=v, Helpdesk=i, Workflows=w. D5 Forecasting under Reports. D6 Manager lens sees: Overview, People, Org, Recruit, Onboard, Attendance+Time, Leave, Expenses, Documents, Assets, ER, Performance, Learning, Helpdesk, Reports, Workflows, Integrations (no Comp, Payroll-setup, Admin). Associate lens: Overview, People, Org, Onboard (self), Attendance+Time (self), Leave (self), Expenses (self), Documents (self), My Assets, Performance (self), Learning, Helpdesk. Payroll lens: Overview, Attendance+Time (view), Leave ledger/payroll-input, Comp, Payroll, Expenses (view), Reports.
