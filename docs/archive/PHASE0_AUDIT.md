# Karmathy HCM — Phase 0 Audit & Revamp Plan

Branch: `feature/hcm-slack-revamp` (working locally, no push yet)

## Scope
- **35 routes** in `App.tsx`: 22 top-level + 13 tenant-scoped `/t/:tenantSlug/*`
- **22 page components**, ~4,700 LOC
- Backend: 154 endpoints, 67 tables, 5 roles

---

## 1. Current page inventory

| # | Route | Page | LOC | Data source |
|---|-------|------|-----|-------------|
| 1 | `/` | Homepage | 370 | static |
| 2 | `/login` | Login | 82 | `/auth/login` |
| 3 | `/dashboard` | Dashboard | 247 | `/reports/dashboard` |
| 4 | `/recruiting` | Recruiting | 600 | 6 endpoints |
| 5 | `/onboarding` | Onboarding | 295 | `/onboarding/*` |
| 6 | `/time` | Time & Attendance | 303 | `/time/*` |
| 7 | `/scheduling` | Scheduling | 320 | `/scheduling/*` |
| 8 | `/leave` | Leave | 346 | `/leave/*` |
| 9 | `/offboarding` | Offboarding | 351 | `/offboarding/*` |
| 10 | `/reports` | Reports | 300 | 5 report endpoints |
| 11 | `/client-onboarding` | Client Onboarding | 515 | `/onboarding-portal/*` |
| 12 | `/platform` | Platform Modules | 543 | **21 endpoints, 7 tabs** |
| 13–22 | `/solutions` … `/terms` | Marketing | 34–62 each | static |

---

## 2. Critical gaps (measured, not estimated)

| Gap | Evidence | Impact |
|-----|----------|--------|
| **No role-based home** | `/dashboard` is the same for all 5 roles | Associate sees 4 stat cards irrelevant to them; Manager can't see approvals inbox |
| **No command palette** | zero grep hits for `cmdk`/`⌘K` | Navigation = scroll sidebar, no keyboard-first path |
| **No keyboard shortcuts** | no `g p` / `?` / ⌘K anywhere | Power users cannot move fast |
| **No dark mode** | zero `dark:` variants | WCAG preference ignored; tenant dark theme impossible |
| **TanStack Query unused** | dependency present, **0 imports** | Every page re-implements loading/error/retry by hand; no caching, no polling |
| **TanStack Table unused** | not installed | No sorting, filtering, column visibility, or virtualization |
| **No Sonner / no toast system** | ad-hoc `<div role=alert>` | No undo, no stacking, no auto-dismiss |
| **Friction: `window.prompt`** | `Recruiting.tsx:573` — "Employee ID for the new hire" | Blocks JS, unstyled, no validation |
| **7× duplicated employee picker** | `value={selected}` in Onboarding, Time, Scheduling, Leave, Offboarding, Platform, Recruiting | Each page re-implements the same dropdown |
| **Inline alerts duplicated** | `bg-red-50 border-red-200` appears in 8+ pages | Inconsistent, no icons, no dismiss |
| **No `<main>` landmark on `/login`** | verified | Screen reader cannot jump to content |
| **42 unlabelled form controls** | measured earlier (now fixed in app pages) | WCAG failure |

---

## 3. Click-depth analysis (before → after)

| Task | Current clicks | Target | How |
|------|---------------|--------|-----|
| Associate: clock in | 4 (login → dashboard → Time → select self → Clock in) | **2** | Home shows clock-in card directly |
| Manager: approve leave | 5 (login → sidebar → Leave → find row → Approve) | **2** | Home "Needs your action" → Approve |
| HR: see headcount | 3 (login → Reports → read) | **1** | Home snapshot |
| Any: reach a page | 3–5 (scroll sidebar, find item) | **1** | ⌘K command palette |
| Any: switch module | 2–4 (hover rail, find section) | **1** | `g` + letter shortcut |
| Recruiting: create offer | 4 (tab → form → 5 fields → submit) | **2** | Inline edit + smart defaults |

---

## 4. Proposed IA map (old → new)

### 4.1 Workspace rail (icon-only, left edge, always visible)

```
[Logo]  Home · People · Time · Leave · Recruiting · Payroll · Perf · Learning · Reports · Admin
```

### 4.2 Secondary sidebar (collapsible, ~240px)

Shows contents of the selected area. Starred items at top.

**People** (absorbs Core HR, Benefits, Employee Directory)
- Employees · Directory · Org Chart · Departments · Jobs
- Locations · Cost Centers · Positions · HR Cases
- Benefit Plans · Enrollments

**Time** → Time & Attendance · Scheduling
**Leave** → Leave Requests · Leave Types · Balances
**Recruiting** → Requisitions · Candidates · Applications · Offers
**Payroll** → Pay Runs · Pay Components · Pay Profiles · Payslips
**Performance** → Goals · Reviews · Compensation Bands · Merit Cycles
**Learning** → Courses · Certifications · Talent Pools · Succession
**Reports** → Dashboard · Headcount · Leave · Labour Cost · Audit
**Admin** → Compliance · Headcount Plans · Scenarios · Client Onboarding · Import/Export · Settings

### 4.3 Platform page split (7 tabs → dedicated areas)

| Current Platform tab | Moves to |
|----------------------|----------|
| Core HR | → **People** (Employees, Directory, Org Chart, Departments, Jobs, Locations, Cost Centers, Positions, HR Cases) |
| Payroll | → **Payroll** |
| Performance | → **Performance** |
| Benefits | → **People** → Benefits |
| Learning | → **Learning** |
| Platform | → **Admin** (Webhooks, Background Checks, E-Signatures) |
| Compliance | → **Admin** (Rules, Violations, Headcount Plans, Scenarios) |
| Import/Export | → **Admin** |

**Result:** `/platform` is retired or becomes a redirect. Every tab gets its own route with breadcrumbs, search, and filters. Click depth drops 2–3 for any module.

---

## 5. Role-based home screens

| Role | Home route | "Needs your action" | Primary card |
|------|-----------|---------------------|--------------|
| Associate | `/dashboard` (role=Associate) | Clock in/out, my leave balance, my shifts, my payslips, pending tasks | Clock card |
| Manager | `/dashboard` (role=Manager) | Approvals inbox (leave, timesheets, swaps, goals), team today, team goals | Approvals |
| HR | `/dashboard` (role=HR) | Action inbox (open cases, onboarding due, violations, requisitions), headcount snapshot | Action inbox |
| PayrollViewer | `/dashboard` (role=PayrollViewer) | Pay run status, payslip summary, payroll reports (read-only) | Pay run status |
| SuperAdmin | `/dashboard` (role=SuperAdmin) | Tenant health, feature flags, integrations, audit highlights + all HR views | Tenant health |

All read from existing endpoints. No backend changes.

---

## 6. Component library (build before pages)

**Core primitives:** Button · Input · Select · Textarea · Checkbox · Switch
**Data:** Badge · Avatar · Tabs · DataTable (TanStack Table) · StatusPill
**Overlay:** Dialog · Popover · DropdownMenu · Tooltip · Toast (Sonner)
**Feedback:** Skeleton · EmptyState · Alert · Progress
**Layout:** PageHeader · Card · SectionCard · Toolbar · Breadcrumb
**Navigation:** WorkspaceRail · SecondarySidebar · CommandPalette · KeyboardShortcuts

---

## 7. Decisions needed from you

1. **Platform page split** — do you want `/platform` retired entirely, or kept as a landing that deep-links to the new areas?
2. **Dark mode scope** — light + dark for the whole app, or start with light only and add dark in Phase 6?
3. **Marketing page scale** — keep Display/H1 large scale on marketing, use app-scale (H1 24/32) inside the app?
4. **Mobile bottom bar** — 4 tabs for most-used items per role + "More" sheet, or a single drawer?
5. **Tenant terminology** — implement now or defer to Phase 6?

---

## 8. Files to create (Phase 1+)

```
frontend/src/components/ui/        Button, Input, Select, Textarea, Checkbox, Switch
frontend/src/components/ui/data/   Badge, Avatar, DataTable, StatusPill
frontend/src/components/ui/overlay/ Dialog, Popover, DropdownMenu, Tooltip
frontend/src/components/ui/feedback/ Skeleton, EmptyState, Alert, Progress
frontend/src/components/ui/layout/  PageHeader, Card, SectionCard, Toolbar, Breadcrumb
frontend/src/components/shell/     WorkspaceRail, SecondarySidebar, CommandPalette, TopBar, MobileBar
frontend/src/lib/                   queryClient, hooks (useEmployees, useLeave, etc.)
docs/DESIGN_SYSTEM.md
```

---

## 9. Known backend gaps (for REVAMP_NOTES.md)

- **No `/auth/register` endpoint exists** despite being listed in the feature doc — only `/auth/login` is implemented.
- **No `/ess/*` endpoints exist** despite ESS being described in Phase 8 — self-service is currently frontend-only or missing.
- **No `/time/today` endpoint** exists — attendance summary needs to be derived from `/time/entries`.
- **No `/reports/attendance` endpoint** exists in the verified API surface.

These will be documented in `REVAMP_NOTES.md`, not fixed (backend is out of scope).

---

**Awaiting your approval on the IA map, Platform split, and the 5 decisions above before writing UI code.**