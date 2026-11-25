# Karmathy HCM — Complete Feature Inventory

> **Product:** Karmathy — Workforce Management Software  
> **Tagline:** Empowering People. Enabling Possibilities.  
> **Brand signature:** People. Potential. Progress.  
> **Positioning:** The complete HCM platform for a brighter tomorrow.  
> **Live:** https://karmathy-frontend.onrender.com · https://karmathy-backend.onrender.com  
> **Last updated:** 2026-10-19

---

## Table of Contents

1. [Architecture & Tech Stack](#architecture--tech-stack)
2. [Deployment](#deployment)
3. [Phase 1 — Foundation + Auth + Employee Data](#phase-1--foundation--auth--employee-data)
4. [Phase 2 — Hire & Onboarding](#phase-2--hire--onboarding)
5. [Phase 3 — Time & Attendance](#phase-3--time--attendance)
6. [Phase 4 — Scheduling / Rostering](#phase-4--scheduling--rostering)
7. [Phase 5 — Leave Management](#phase-5--leave-management)
8. [Phase 6 — Offboarding / Termination](#phase-6--offboarding--termination)
9. [Phase 7 — Dashboards & Reporting](#phase-7--dashboards--reporting)
10. [Phase 8 — Core HR Depth](#phase-8--core-hr-depth)
11. [Phase 9 — Payroll](#phase-9--payroll)
12. [Phase 10 — Performance + Compensation](#phase-10--performance--compensation)
13. [Phase 11 — Benefits + Leave of Absence](#phase-11--benefits--leave-of-absence)
14. [Phase 12 — Learning & Development + Succession](#phase-12--learning--development--succession)
15. [Phase 13 — Integrations Platform](#phase-13--integrations-platform)
16. [Phase 14 — Compliance + Workforce Planning + Analytics](#phase-14--compliance--workforce-planning--analytics)
17. [Client Onboarding Portal](#client-onboarding-portal)
18. [Data Import / Export](#data-import--export)
19. [OCI Object Storage](#oci-object-storage)
20. [Brand Design System](#brand-design-system)
21. [Marketing Homepage](#marketing-homepage)
22. [Multi-Tenant Routing](#multi-tenant-routing)
23. [ESS / HR Module](#ess--hr-module)
24. [RBAC & Security](#rbac--security)
25. [Database Schema Summary](#database-schema-summary)
26. [API Endpoint Inventory](#api-endpoint-inventory)
27. [Frontend Pages](#frontend-pages)
28. [Test Scripts](#test-scripts)
29. [Known Limitations](#known-limitations)

---

## Architecture & Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11), SQLAlchemy 2.0, python-oracledb (thin mode) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Database | Oracle Autonomous Database (Always Free, OLTP, mTLS) |
| Storage | Oracle Object Storage (PAR URLs, 7-day expiry) |
| Auth | JWT (HS256) + RBAC |
| Deploy | Render (backend Docker + frontend static) |
| CI/CD | GitHub Actions (auto-deploy on push to main) |
| Design | Inter font, 4px spacing, 12px card radius, brand color tokens |

---

## Deployment

| Service | URL | Type |
|---------|-----|------|
| Frontend | https://karmathy-frontend.onrender.com | Render Static Site (free) |
| Backend | https://karmathy-backend.onrender.com | Render Web Service (Docker, free) |
| API Docs | https://karmathy-backend.onrender.com/docs | Swagger/OpenAPI |
| Database | Oracle ADB `karmkathyadb` (ap-hyderabad-1) | Always Free OLTP |
| Storage | Oracle Object Storage `karmathy-documents` | PAR URLs |

**Oracle ADB details:**
- Host: `adb.ap-hyderabad-1.oraclecloud.com:1522`
- TNS alias: `karmkathyadb_high`
- mTLS: required (wallet with encrypted PEM)
- Schema: `ADMIN`

---

## Phase 1 — Foundation + Auth + Employee Data

### Features
- **Authentication**: JWT token-based login/register, password hashing (bcrypt)
- **RBAC**: 5 roles — SuperAdmin, HR, Manager, Associate, PayrollViewer
- **Employees**: CRUD, employee ID, name, email, phone, hire date, job, department, manager, status, salary
- **Departments**: CRUD with code, name, description, active flag
- **Jobs**: CRUD with title, code, department, salary range, active flag
- **User management**: username, email, role, active flag, linked employee

### Endpoints
- `POST /auth/login` — JWT login
- `POST /auth/register` — user registration
- `GET/POST /employees/` — list/create employees
- `GET/PUT /employees/{id}` — get/update employee
- `GET/POST /departments/` — list/create departments
- `GET/POST /jobs/` — list/create jobs

### Frontend
- Login page (tenant-aware branding)
- Dashboard (summary cards, module links)
- Protected routes

---

## Phase 2 — Hire & Onboarding

### Features
- **Job requisitions**: req number, title, department, job, location, employment type, openings, status (Draft/Open/OnHold/Closed), description, posted/closing dates
- **Candidates**: name, email, phone, source, resume URL, status (Applied/Screening/Interview/Offer/Hired/Rejected)
- **Applications**: link candidate to requisition, status, notes, applied date
- **Offers**: offer number, application, job, salary, start date, offer date, expiry, status (Draft/Sent/Accepted/Declined/Expired), letter URL
- **Offer letter PDF**: auto-generated via fpdf2, stored in OCI/local storage
- **Offer workflow**: generate letter → send → accept → hire (creates Employee + 6-item onboarding checklist)
- **Onboarding tasks**: title, category (Documents/IT/Facilities/Training/General), assigned to, due date, status (Pending/InProgress/Completed)
- **Onboarding documents**: type (IDProof/TaxForm/BankDetails/Contract/Certificate), file upload, status (Pending/Verified/Rejected)
- **Default checklist**: 6-item standard checklist applied on hire

### Endpoints
- `GET/POST /requisitions/`, `GET/PUT /requisitions/{id}`
- `GET/POST /candidates/`, `GET/PUT /candidates/{id}`
- `GET/POST /applications/`, `GET/PUT /applications/{id}`
- `GET/POST /offers/`, `GET/PUT /offers/{id}`
- `POST /offers/{id}/letter` — generate PDF
- `POST /offers/{id}/accept` — accept offer
- `POST /offers/{id}/hire` — hire candidate → employee + checklist
- `GET /onboarding/{employee_id}/summary` — progress %
- `POST /onboarding/{employee_id}/checklist` — create default checklist
- `GET/POST /onboarding/{employee_id}/tasks`, `PUT /onboarding/tasks/{id}`
- `GET/POST /onboarding/{employee_id}/documents`, `PUT /onboarding/documents/{id}`

### Frontend
- Recruiting page (tabbed: Requisitions, Candidates, Applications, Offers with actions)
- Onboarding page (employee picker, progress bar, task status, document upload)

---

## Phase 3 — Time & Attendance

### Features
- **Clock in/out**: web-based clock-in with source tracking (Web/Mobile/Biometric/Manual)
- **Time entries**: work date, clock in/out, break minutes, worked hours, overtime hours, status (Draft/Approved), notes
- **Duplicate clock-in prevention**: rejects if already clocked in
- **Timesheets**: payroll-period summary, total/overtime hours, entry count, status (Draft/Submitted/Approved)
- **Timesheet generation**: roll up time entries into a timesheet for a period
- **Approval workflow**: submit → approve
- **Attendance summary**: daily headcount, present, absent
- **Overtime calculation**: hours beyond 8/day

### Endpoints
- `GET /time/entries` — list entries (filter by employee, date range)
- `POST /time/clock-in` — clock in
- `POST /time/clock-out` — clock out
- `GET /time/today` — attendance summary
- `POST /time/entries` — manual entry (admin)
- `PUT /time/entries/{id}` — update entry
- `DELETE /time/entries/{id}` — delete entry
- `GET /time/timesheets` — list timesheets
- `POST /time/timesheets/generate` — generate timesheet
- `POST /time/timesheets/{id}/submit` — submit
- `POST /time/timesheets/{id}/approve` — approve

---

## Phase 4 — Scheduling / Rostering

### Features
- **Shift templates**: name, code, start/end time (HH:MM), break minutes, night flag, active
- **Roster entries**: employee, work date, shift template, start/end time, night flag, status (Scheduled/Confirmed/Absent/Cancelled)
- **Roster generation**: create entries for a date range from a shift template
- **Shift swaps**: request, approve, reject (with proposed date)
- **Duplicate prevention**: won't create duplicate roster entries for same employee/date

### Endpoints
- `GET/POST /scheduling/shift-templates`, `PUT /scheduling/shift-templates/{id}`
- `GET /scheduling/roster`, `POST /scheduling/roster`, `POST /scheduling/roster/generate`, `PUT /scheduling/roster/{id}`
- `GET /scheduling/swaps`, `POST /scheduling/swaps`, `POST /scheduling/swaps/{id}/approve`, `POST /scheduling/swaps/{id}/reject`

---

## Phase 5 — Leave Management

### Features
- **Leave types**: name, code, paid/unpaid, max days per year, active
- **Leave balances**: entitlement, carried-over, used, available (computed)
- **Entitlements**: assign to all active employees for a leave type/year
- **Tenure-based accrual**: base days + 1 day/year of service (capped at +5)
- **Leave requests**: start/end date, working days (weekday count), reason, status (Pending/Approved/Rejected/Cancelled)
- **Approval workflow**: approve (deducts from balance), reject, cancel (restores balance)
- **Working days calculation**: Monday-Friday count inclusive

### Endpoints
- `GET/POST /leave/types`, `PUT /leave/types/{id}`
- `GET /leave/balances`, `POST /leave/entitlements`
- `GET/POST /leave/requests`, `POST /leave/requests/{id}/approve`, `/reject`, `/cancel`

---

## Phase 6 — Offboarding / Termination

### Features
- **Terminations**: employee, last working date, type (Resignation/Termination/Layoff/Retirement/End of Contract), reason, status (Initiated/In Progress/Completed/Cancelled), exit interview notes, final pay amount
- **Default checklist**: 6-item standard offboarding checklist (laptop, access revocation, final pay, exit interview, knowledge transfer, badge return)
- **Checklist items**: name, category, assigned to, due date, status (Pending/Completed), completed timestamp
- **Progress tracking**: completed/total, percentage
- **Complete termination**: marks termination + employee status as "Terminated"
- **Cancel termination**: sets status to Cancelled

### Endpoints
- `GET/POST /offboarding/tasks`, `PUT /offboarding/tasks/{id}`
- `GET/POST /offboarding/terminations`, `GET /offboarding/terminations/{id}`
- `PUT /offboarding/terminations/{id}`, `POST /offboarding/terminations/{id}/complete`, `POST /offboarding/terminations/{id}/cancel`
- `GET /offboarding/terminations/{id}/progress`
- `PUT /offboarding/items/{id}`

---

## Phase 7 — Dashboards & Reporting

### Features
- **Dashboard**: active/terminated employees, open requisitions, candidates, offers, pending leave, pending timesheets, pending swaps, present today, total hours, overtime
- **Headcount report**: by department, by status
- **Leave report**: by status, entitled/used days totals
- **Labor cost report**: monthly payroll, by department
- **Attendance report**: daily present, hours, overtime
- **Audit trail**: filterable, sortable, limitable
- **Recent activity**: last 10 audit entries

### Endpoints
- `GET /reports/dashboard`
- `GET /reports/headcount`
- `GET /reports/leave`
- `GET /reports/labor-cost`
- `GET /reports/attendance?day=`
- `GET /reports/audit?limit=`

---

## Phase 8 — Core HR Depth

### Features
- **Locations**: name, code, address, city, country, timezone, active
- **Cost centers**: code, name, department, active
- **Positions**: code, title, job, department, location, reports-to, FTE, active
- **Employee documents**: type (Contract/ID/Tax/Certificate/Policy/Other), file name, storage URL, status, expiry date
- **HR cases**: subject, category (Payroll/Benefits/IT/Facilities/Policy/General), priority (Low/Medium/High/Urgent), status (Open/In Progress/Resolved/Closed), assigned to, SLA due, resolution
- **Case comments**: author, comment, timestamp
- **ESS profiles**: preferred name, emergency contacts, bank details, tax ID, direct deposit, notification preferences, language, theme
- **Notifications**: title, message, type (info/success/warning/error/approval/reminder), category, entity reference, read/unread
- **Employee files**: document type, file name, storage URL, version, status, expiry date, uploaded by
- **Announcements**: title, content, category, priority, target audience, published, expiry
- **Employee directory**: searchable (name, email, job title), filterable by department, sync from employee master
- **Org chart**: rebuild from manager relationships, materialized paths, depth tracking
- **Goal alignment**: OKR cascading (goal → parent goal)
- **Continuous feedback**: praise, coaching, recognition (private/public)
- **Compliance checks**: scheduled rule evaluation

### Endpoints
- `/core-hr/locations`, `/core-hr/cost-centers`, `/core-hr/positions`
- `/core-hr/employee-documents`
- `/core-hr/cases`, `/core-hr/cases/{id}/comments`
- `/ess/ess/profile/{employee_id}`, `/ess/ess/profile`
- `/ess/notifications`, `/ess/notifications/{id}/read`
- `/ess/employee-files`
- `/ess/announcements`, `/ess/announcements/{id}/publish`
- `/ess/directory`, `/ess/directory/sync`
- `/ess/org-chart`, `/ess/org-chart/rebuild`
- `/ess/goal-alignments`
- `/ess/continuous-feedback`
- `/ess/compliance-checks`, `/ess/compliance-checks/run`

---

## Phase 9 — Payroll

### Features
- **Payroll periods**: name, start/end date, pay date, status (Draft/Processing/Approved/Paid)
- **Pay components**: code, name, type (Earning/Deduction/Tax), taxable, pre-tax, active
- **Employee pay profiles**: base salary, pay frequency (Monthly/Biweekly/Weekly), bank account, tax withholding %
- **Pay runs**: period, status, total gross/deductions/net, headcount, run date, approval
- **Payslips**: per-employee gross/net/deductions, earnings/deductions JSON, status
- **Pay run processing**: auto-calculates payslips from pay profiles (gross = base salary, tax = gross × withholding %, net = gross - deductions)
- **Approval workflow**: draft → processing → approved → paid

### Endpoints
- `/payroll/periods`, `/payroll/components`, `/payroll/pay-profiles`
- `/payroll/runs`, `/payroll/runs/{id}/approve`, `/payroll/runs/{id}/process`
- `/payroll/payslips`

---

## Phase 10 — Performance + Compensation

### Features
- **Goals**: title, description, weight, progress (0-100), status (Not Started/In Progress/Completed/Cancelled), due date
- **Performance reviews**: employee, reviewer, period, status (Draft/In Progress/Submitted/Finalized), overall rating (1-5), manager/employee comments, finalized timestamp
- **Review feedback**: 360-degree (Self/Manager/Peer/Upward), rating, comments
- **Compensation bands**: job, level (Junior/Mid/Senior/Lead/Principal), min/mid/max salary, currency
- **Merit cycles**: name, year, budget %, start/end date, status (Draft/Active/Closed)
- **Merit allocations**: per-employee current/proposed salary, increase %, status (Draft/Approved/Applied)
- **Goal alignment**: OKR cascading (goal → parent goal)

### Endpoints
- `/performance/goals`, `/performance/goals/{id}`
- `/performance/reviews`, `/performance/reviews/{id}`, `/performance/reviews/{id}/finalize`
- `/performance/feedback`
- `/performance/compensation-bands`
- `/performance/merit-cycles`, `/performance/merit-allocations`

---

## Phase 11 — Benefits + Leave of Absence

### Features
- **Benefit plans**: name, code, type (Health/Dental/Vision/Life/Retirement/Other), provider, employer/employee contribution, active
- **Benefit enrollments**: employee, plan, effective date, end date, status (Active/Terminated/Waived)
- **Life events**: type (Marriage/Birth/Adoption/Divorce/Death/JobChange), date, description, status
- **Leave of absence**: type (FMLA/Parental/Medical/Bereavement/Sabbatical), start/end date, status (Pending/Approved/Denied/Completed), approval

### Endpoints
- `/benefits/benefit-plans`
- `/benefits/benefit-enrollments`
- `/benefits/life-events`
- `/benefits/leaves-of-absence`, `/benefits/leaves-of-absence/{id}/approve`

---

## Phase 12 — Learning & Development + Succession

### Features
- **Courses**: title, code, description, category (Compliance/Technical/Leadership/Soft Skills), duration, mandatory, active
- **Course enrollments**: employee, course, status (Enrolled/In Progress/Completed/Failed), score, started/completed timestamps
- **Certifications**: name, issuer, issued/expiry date, certificate URL
- **Talent pools**: name, description
- **Talent pool members**: employee, readiness (Ready Now/1-2 years/2-3 years), notes
- **Succession plans**: position, primary/backup successor, readiness, notes
- **Continuous feedback**: praise, coaching, recognition (private/public)

### Endpoints
- `/learning/courses`, `/learning/course-enrollments`, `/learning/course-enrollments/{id}/complete`
- `/learning/certifications`
- `/learning/talent-pools`, `/learning/talent-pool-members`
- `/learning/succession-plans`

---

## Phase 13 — Integrations Platform

### Features
- **SSO configs**: provider (SAML/OIDC/OAuth2), entity ID, SSO URL, certificate, client ID/secret, active
- **Webhooks**: URL, events (comma-separated), secret (encrypted), active, last triggered
- **Webhook delivery**: real HTTP POST with HMAC-SHA256 signature, response code, attempts, status
- **Background checks**: candidate, provider (manual/Checkr/HireRight), status (Pending/In Progress/Clear/Consider/Failed), result, completed
- **E-signatures**: document type, signer email/name, status (Pending/Sent/Signed/Declined/Expired), provider, signed timestamp
- **SCIM tokens**: token hash, label, expiry
- **Client onboarding portal**: tenant setup, feature flags, integrations, migrations, settings, docs

### Endpoints
- `/platform/sso-configs`
- `/platform/webhooks`, `/platform/webhooks/{id}/deliver`, `/platform/webhooks/{id}/deliveries`
- `/platform/background-checks`, `/platform/background-checks/{id}/complete`
- `/platform/e-signatures`, `/platform/e-signatures/{id}/sign`

---

## Phase 14 — Compliance + Workforce Planning + Analytics

### Features
- **Compliance rules**: code, name, category (Labor Law/Policy/Certification/Safety), description, severity (Low/Medium/High/Critical), active
- **Compliance violations**: employee, rule, detected, status (Open/In Progress/Resolved/Dismissed), resolved, notes
- **Compliance checks**: scheduled rule evaluation, passed/failed, details
- **Headcount plans**: name, year, department, planned/actual headcount, budget, notes
- **Scenarios**: what-if planning, base plan, adjustments (JSON)
- **Report definitions**: name, description, query, filters
- **Saved reports**: definition, name, result (JSON snapshot)

### Endpoints
- `/compliance/compliance-rules`
- `/compliance/compliance-violations`, `/compliance/compliance-violations/{id}/resolve`
- `/compliance/compliance-checks`, `/compliance/compliance-checks/run`
- `/compliance/headcount-plans`
- `/compliance/scenarios`
- `/compliance/report-definitions`
- `/compliance/saved-reports`

---

## Client Onboarding Portal

### Features
- **Clients (tenants)**: name, slug, industry, country, timezone, locale, primary/secondary color, logo URL, status (draft/active/suspended), contact info
- **Client settings**: arbitrary key/value pairs (payroll.cycle_day, leave.year_start_month, etc.)
- **Feature flags**: 12 default flags (6 modules + 6 sub-features), toggle on/off, JSON config
- **Integrations**: name, kind (oracle_adb/rest/sftp/csv/webhook), endpoint, username, secret (encrypted), status, test
- **Migration jobs**: entity, status (queued/running/succeeded/failed/cancelled), total/processed/succeeded/failed, error log, run
- **Onboarding steps**: 6 default steps, completion tracking, progress %
- **Migration docs**: served from `docs/CLIENT_ONBOARDING.md`
- **Branding**: primary/secondary color, logo URL, timezone, locale

### Endpoints
- `/onboarding-portal/clients` (CRUD)
- `/onboarding-portal/clients/{id}/settings/{key}` (upsert)
- `/onboarding-portal/clients/{id}/feature-flags`, `/feature-flags/{key}` (toggle)
- `/onboarding-portal/clients/{id}/integrations`, `/integrations/{id}/test`
- `/onboarding-portal/clients/{id}/migrations`, `/migrations/{id}/run`, `/migrations/{id}/cancel`
- `/onboarding-portal/clients/{id}/onboarding`, `/onboarding/steps`, `/onboarding/steps/{id}/complete`
- `/onboarding-portal/docs/migration-api`
- `/onboarding-portal/clients/by-slug/{slug}` (public, for multi-tenant branding)

---

## Data Import / Export

### Features
- **Export**: CSV download for 12 entities (departments, jobs, locations, cost centers, employees, candidates, leave types, benefit plans, courses, compliance rules, shift templates, pay components)
- **Import**: CSV upload with type coercion (int, float, bool), per-row error reporting, atomic commit
- **Entities list**: `GET /import-export/entities`

### Endpoints
- `GET /import-export/export/{entity}` — CSV download
- `POST /import-export/import/{entity}` — CSV upload
- `GET /import-export/entities` — list supported entities

---

## OCI Object Storage

### Features
- **Storage backend**: local (dev) or OCI (prod)
- **OCI operations**: save, url_for (PAR with 7-day expiry), delete, exists, list_objects
- **Bucket**: `karmathy-documents` (namespace `axkr5pffw199`, region `ap-hyderabad-1`)
- **Secrets**: OCI config + API key uploaded as Render secret files
- **Offer letters**: stored in OCI, served via PAR URLs

---

## Brand Design System

### Colors
| Token | Hex | Usage |
|-------|-----|-------|
| Primary blue | #2563EB | Primary actions, links |
| Deep navy | #0F172A | Headings, footer |
| Teal | #06B6D4 | Technology accents |
| Growth green | #10B981 | Success, positive states |
| Intelligence violet | #8B5CF6 | AI-related features |
| Page background | #F8FAFC | Page background |
| Border | #E2E8F0 | Borders, dividers |
| Secondary text | #64748B | Secondary text |
| Error | #DC2626 | Errors, destructive |
| Warning | #D97706 | Warnings |
| Success | #10B981 | Success states |
| Surface | #FFFFFF | Cards, surfaces |

### Typography
- **Font**: Inter (system fallbacks)
- **Scale**: Display 56px/64px/700, H1 44/52/700, H2 32/40/600, H3 24/32/600, Body 16/24/400, Caption 12/16/500

### Spacing & Radius
- 4px base unit: 4, 8, 12, 16, 24, 32, 48, 64, 80, 96 px
- Card radius: 12px
- Button/input height: 44-48px
- Container max-width: 1280px

### CSS Utilities
- `.card` — white surface, rounded, shadow, border
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-ghost`
- `.input` — bordered input with focus ring
- `.badge`, `.badge-primary`, `.badge-success`, `.badge-warning`, `.badge-error`
- `.skeleton` — loading placeholder
- `.container-karmathy` — max-width container with responsive padding

### Accessibility
- Focus-visible outlines (2px solid primary)
- Reduced-motion support
- Semantic HTML, ARIA labels
- WCAG 2.2 AA target
- Sufficient contrast ratios

---

## Marketing Homepage

### Sections (in order)
1. **Global navigation**: Logo, Platform, Solutions, Industries, Resources, Company, Login, Request a demo
2. **Hero**: "Empowering People. Enabling Possibilities." + value prop + CTAs + product preview
3. **HCM platform overview**: 6 feature cards
4. **Employee lifecycle & module coverage**: 12 module cards
5. **Industry use cases**: 10 industries
6. **Integrations & extensibility**: 8 integration types
7. **Security & compliance**: 6 security cards
8. **Resources**: 3 resource cards (linked)
9. **Final conversion CTA**: "Ready to transform your workforce?"
10. **Footer**: 4 columns (Platform, Solutions, Resources, Company) + copyright

### Brand elements
- Headline: "Empowering People. Enabling Possibilities."
- Supporting copy: "Connect your workforce, simplify HR operations, and bring your people processes together with one configurable HCM platform."
- Brand signature: "People. Potential. Progress."
- Positioning: "The complete HCM platform for a brighter tomorrow."

---

## Multi-Tenant Routing

### Subdomain detection
- `client1.karmathy.com` → tenant slug "client1"
- `client1.localhost:5173` → tenant slug "client1" (dev)

### Path-based fallback (Render free tier)
- `/t/{slug}/dashboard`, `/t/{slug}/recruiting`, etc.
- Tenant context applied via `TenantProvider`

### Tenant branding
- Primary/secondary colors applied as CSS variables
- Logo URL, timezone, locale, status
- Tenant name in page title
- WCAG contrast validation (deriveTheme with readable variants)
- Theme warnings for inaccessible color choices

---

## RBAC & Security

### Roles
| Role | Access |
|------|--------|
| SuperAdmin | Full access to all modules |
| HR | Employee, recruiting, onboarding, leave, offboarding, reports |
| Manager | Team view, approvals, leave approval |
| Associate | Self-service, own data |
| PayrollViewer | Payroll, reports (read-only) |

### Security features
- JWT authentication (HS256, configurable expiry)
- Password hashing (bcrypt, 72-byte truncation)
- Role-based endpoint protection
- Audit trail (all mutations logged)
- Secret encryption (Fernet, key derived from SECRET_KEY)
- mTLS for Oracle ADB
- CORS configuration
- Input validation (Pydantic)

---

## Database Schema Summary

**67 tables** across all phases:

| Phase | Tables |
|-------|--------|
| 1 | users, departments, jobs, employees |
| 2 | job_requisitions, candidates, applications, offers, onboarding_tasks, onboarding_documents |
| 3 | time_entries, timesheets |
| 4 | shift_templates, roster_entries, shift_swaps |
| 5 | leave_types, leave_balances, leave_requests |
| 6 | terminations, offboarding_tasks, offboarding_items |
| 7 | audit_logs |
| 8 | locations, cost_centers, positions, employee_documents, hr_cases, case_comments, employee_self_service, org_chart_nodes, notifications, employee_files, announcements, employee_directory, goal_alignments, continuous_feedback, compliance_checks |
| 9 | payroll_periods, pay_components, employee_pay_profiles, pay_runs, pay_slips |
| 10 | goals, performance_reviews, review_feedback, compensation_bands, merit_cycles, merit_allocations |
| 11 | benefit_plans, benefit_enrollments, life_events, leaves_of_absence |
| 12 | courses, course_enrollments, certifications, talent_pools, talent_pool_members, succession_plans |
| 13 | sso_configs, scim_tokens, webhooks, webhook_deliveries, background_checks, e_signatures |
| 14 | compliance_rules, compliance_violations, headcount_plans, scenarios, report_definitions, saved_reports |
| CO | clients, client_settings, feature_flags, integrations, migration_jobs, onboarding_steps |

All tables use `NUMBER GENERATED BY DEFAULT AS IDENTITY` for primary keys (Oracle-compatible).

---

## API Endpoint Inventory

**154 endpoints** across 20 routers:

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| auth | /auth | login, register |
| employees | /employees | CRUD |
| departments | /departments | CRUD |
| jobs | /jobs | CRUD |
| requisitions | /requisitions | CRUD |
| candidates | /candidates | CRUD |
| applications | /applications | CRUD |
| offers | /offers | CRUD + letter/accept/hire |
| onboarding | /onboarding | summary, checklist, tasks, documents |
| time | /time | entries, clock-in/out, today, timesheets |
| scheduling | /scheduling | shift-templates, roster, swaps |
| leave | /leave | types, balances, entitlements, requests |
| offboarding | /offboarding | tasks, terminations, items, progress |
| reports | /reports | dashboard, headcount, leave, labor-cost, attendance, audit |
| core-hr | /core-hr | locations, cost-centers, positions, employee-documents, cases, comments |
| payroll | /payroll | periods, components, pay-profiles, runs, payslips |
| performance | /performance | goals, reviews, feedback, compensation-bands, merit-cycles, merit-allocations |
| benefits | /benefits | benefit-plans, enrollments, life-events, leaves-of-absence |
| learning | /learning | courses, enrollments, certifications, talent-pools, succession-plans |
| platform | /platform | sso-configs, webhooks, deliveries, background-checks, e-signatures |
| compliance | /compliance | rules, violations, checks, headcount-plans, scenarios, report-definitions, saved-reports |
| import-export | /import-export | entities, export, import |
| onboarding-portal | /onboarding-portal | clients, settings, feature-flags, integrations, migrations, onboarding, docs, by-slug |
| ess | /ess | profiles, notifications, employee-files, announcements, directory, org-chart, goal-alignments, continuous-feedback, compliance-checks |

---

## Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Homepage | / | Marketing landing page with all sections |
| Login | /login | Tenant-aware login |
| Dashboard | /dashboard | Summary cards, module links, recent activity |
| Recruiting | /recruiting | Tabbed: requisitions, candidates, applications, offers |
| Onboarding | /onboarding | Employee picker, checklist, documents |
| Time & Attendance | /time | Clock in/out, entries, timesheets |
| Scheduling | /scheduling | Shift templates, roster, swaps |
| Leave | /leave | Leave types, balances, requests |
| Offboarding | /offboarding | Terminations, exit checklist |
| Reports | /reports | Dashboard, headcount, leave, labor cost, attendance, audit |
| Client Onboarding | /client-onboarding | Tenant setup, feature flags, integrations, migrations |
| Platform | /platform | Core HR, Payroll, Performance, Benefits, Learning, Integrations, Compliance, Import/Export |
| Solutions | /solutions | Solution cards |
| Industries | /industries | Industry cards |
| Resources | /resources | Resource cards |
| About | /about | Company info, brand attributes |
| Careers | /careers | Open positions |
| Contact | /contact | Contact form |
| Privacy | /privacy | Privacy policy |
| Terms | /terms | Terms of service |
| Documentation | /docs | Documentation hub |

---

## Test Scripts

| Script | Coverage |
|--------|----------|
| `backend/smoke_test.py` | Phase 1 (auth, employees, departments) |
| `backend/smoke_test_phase2.py` | Phase 2 (recruiting, onboarding) |
| `backend/smoke_test_phases_3_7.py` | Phases 3-7 (39 checks) |
| `backend/smoke_test_client_onboarding.py` | Client Onboarding (18 checks) |
| `backend/smoke_test_all_phases.py` | Phases 8-14 (65 checks) |
| `scripts/live_e2e.py` | Full live end-to-end (37 checks) |

---

## Known Limitations

1. **Ephemeral disk** — `STORAGE_BACKEND=local` would lose files on redeploy; now using OCI (fixed)
2. **Spin-down** — Free tier services sleep when idle; first request is slow
3. **Single schema** — App tables live in `ADMIN` schema
4. **Dynamic egress IPs** — No static outbound IP on free tier; ADB access via mTLS only
5. **No wildcard subdomains** — Render free tier doesn't support `*.karmathy.com`; using path-based `/t/:slug/`
6. **No real SSO flows** — SSO configs exist but actual SAML/OIDC authentication not implemented
7. **No real SCIM** — SCIM tokens exist but provisioning endpoints not implemented
8. **No real e-signature** — Status tracking only, no actual document signing
9. **No real background checks** — Status tracking only, no provider integration
10. **Payroll tax** — Simple percentage withholding, no real tax engine
11. **No mobile app** — Responsive web only
12. **No email notifications** — In-app notifications only, no email delivery
13. **No real-time updates** — Polling-based, no WebSocket

---

## File Structure

```
Karmathy/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── api.py (router registration)
│   │   │   └── endpoints/ (20 endpoint files)
│   │   ├── core/ (config, database, security, audit)
│   │   ├── crud/ (12 crud files)
│   │   ├── models/ (15 model files)
│   │   ├── schemas/ (14 schema files)
│   │   ├── services/ (storage, offer_letter)
│   │   └── main.py
│   ├── scripts/
│   │   ├── seed_admin.py
│   │   ├── render_deploy.py
│   │   ├── test_adb_connection.py
│   │   └── live_e2e.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── smoke_test*.py
├── frontend/
│   ├── src/
│   │   ├── components/ (Layout, ProtectedRoute, ui, icons)
│   │   ├── context/ (AuthContext, TenantContext)
│   │   ├── lib/ (api)
│   │   ├── pages/ (22 page files)
│   │   └── types/ (index.ts)
│   ├── tailwind.config.js
│   └── package.json
├── docs/
│   ├── API_CONTRACT.md
│   ├── DB_SCHEMA.sql
│   ├── AUTH_ROLES.md
│   ├── DEPLOYMENT.md
│   └── CLIENT_ONBOARDING.md
├── scripts/
│   └── render_deploy.py
├── render.yaml
├── docker-compose.yml
├── README.md
└── .env.example
```