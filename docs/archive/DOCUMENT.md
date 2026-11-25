# Karmathy HCM — Complete Feature & Design Document

> **Product:** Karmathy — Workforce Management Software  
> **Tagline:** Empowering People. Enabling Possibilities.  
> **Brand signature:** People. Potential. Progress.  
> **Positioning:** The complete HCM platform for a brighter tomorrow.  
> **Live:** https://karmathy-frontend.onrender.com · https://karmathy-backend.onrender.com  
> **Last updated:** 2026-10-19  
> **Total commits:** 30+ · **Database tables:** 76 · **API endpoints:** 154+ · **Frontend pages:** 22

---

## 1. Architecture & Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11), SQLAlchemy 2.0, python-oracledb (thin mode) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Database | Oracle Autonomous Database (Always Free, OLTP, mTLS) |
| Storage | Oracle Object Storage (PAR URLs, 7-day expiry) |
| Auth | JWT (HS256) + RBAC (5 roles) |
| Deploy | Render (backend Docker + frontend static) + GitHub Actions CI/CD |
| Design | Inter font, 4px spacing, 12px card radius, brand color tokens |

---

## 2. Design System (Brand & UI)

### Color Tokens
| Token | Hex | Usage |
|-------|-----|-------|
| Primary blue | #2563EB | Primary actions, links, focus rings |
| Deep navy | #0F172A | Headings, footer background |
| Teal | #06B6D4 | Technology accents |
| Growth green | #10B981 | Success, positive states |
| Intelligence violet | #8B5CF6 | AI-related features |
| Page background | #F8FAFC | Page background |
| Surface | #FFFFFF | Cards, surfaces |
| Border | #E2E8F0 | Borders, dividers |
| Text primary | #111827 | Primary text |
| Text secondary | #64748B | Secondary text |
| Error | #DC2626 | Errors, destructive actions |
| Warning | #D97706 | Warnings |

### Typography (Inter)
| Style | Size/Line | Weight |
|-------|-----------|--------|
| Display | 56px/64px | 700 |
| H1 | 44px/52px | 700 |
| H2 | 32px/40px | 600 |
| H3 | 24px/32px | 600 |
| Body | 16px/24px | 400 |
| Body SM | 14px/20px | 400 |
| Caption | 12px/16px | 500 |

### Spacing & Radius
- 4px base unit: 4, 8, 12, 16, 24, 32, 48, 64, 80, 96 px
- Card radius: 12px
- Button/input height: 44-48px
- Container max-width: 1280px

### CSS Utility Classes
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

## 3. Marketing Homepage

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

## 4. Multi-Tenant Routing

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

## 5. RBAC & Security

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

## 6. All Phases (1-14 + Enhancements)

### Phase 1 — Foundation + Auth + Employee Data
- JWT auth, RBAC, departments, jobs, employees
- Endpoints: `/employees`, `/departments`, `/jobs`
- Pages: Dashboard, Login

### Phase 2 — Hire & Onboarding
- Requisitions, candidates, applications, offers, offer-letter PDF, onboarding checklists & documents
- Endpoints: `/requisitions`, `/candidates`, `/applications`, `/offers`, `/onboarding`
- Pages: Recruiting, Onboarding

### Phase 3 — Time & Attendance
- Clock in/out, time entries, overtime, payroll-period timesheets
- Endpoints: `/time`
- Page: Time & Attendance

### Phase 4 — Scheduling / Rostering
- Shift templates, roster generation, shift swaps
- Endpoints: `/scheduling`
- Page: Scheduling

### Phase 5 — Leave Management
- Leave types, tenure-based entitlements, requests, approvals
- Endpoints: `/leave`
- Page: Leave

### Phase 6 — Offboarding / Termination
- Exit checklists, final pay, employee close-out
- Endpoints: `/offboarding`
- Page: Offboarding

### Phase 7 — Dashboards & Reporting
- Dashboard, headcount, labor cost, attendance, audit trail
- Endpoints: `/reports`
- Page: Reports

### Phase 8 — Core HR Depth
- Locations, cost centers, positions, employee documents, HR cases, ESS profiles, notifications, announcements, employee directory, org chart, goal alignment, continuous feedback, compliance checks
- Endpoints: `/core-hr`, `/ess`
- Page: Platform (Core HR tab)

### Phase 9 — Payroll
- Periods, components, pay profiles, pay runs (auto-calculate payslips), payslips
- Endpoints: `/payroll`
- Page: Platform (Payroll tab)

### Phase 10 — Performance + Compensation
- Goals, reviews, 360 feedback, compensation bands, merit cycles, allocations
- Endpoints: `/performance`
- Page: Platform (Performance tab)

### Phase 11 — Benefits + Leave of Absence
- Benefit plans, enrollments, life events, LOA
- Endpoints: `/benefits`
- Page: Platform (Benefits tab)

### Phase 12 — Learning & Development + Succession
- Courses, enrollments, certifications, talent pools, succession plans
- Endpoints: `/learning`
- Page: Platform (Learning tab)

### Phase 13 — Integrations Platform
- SSO configs, webhooks (real HTTP delivery), background checks, e-signatures
- Endpoints: `/platform`
- Page: Platform (Platform tab)

### Phase 14 — Compliance + Workforce Planning + Analytics
- Compliance rules/violations, headcount plans, scenarios, report definitions, saved reports
- Endpoints: `/compliance`
- Page: Platform (Compliance tab)

### Client Onboarding Portal
- Tenants, feature flags, integrations, migrations, settings, docs
- Endpoints: `/onboarding-portal`
- Page: Client Onboarding

### Data Import/Export
- CSV import/export for 12 entities
- Endpoints: `/import-export`
- Page: Platform (Import/Export tab)

---

## 7. Frontend Pages (22 total)

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
| (tenant-scoped) | /t/:slug/* | Multi-tenant portal routes |

---

## 8. Database Schema Summary

**76 tables** across all phases:

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

## 9. API Endpoint Inventory

**154+ endpoints** across 20 routers:

| Router | Prefix | Key Endpoints |
|--------|--------|---------------|
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
| payroll | /payroll | periods, components, pay-profiles, runs, payslips, process |
| performance | /performance | goals, reviews, feedback, compensation-bands, merit-cycles, merit-allocations |
| benefits | /benefits | benefit-plans, enrollments, life-events, leaves-of-absence |
| learning | /learning | courses, enrollments, certifications, talent-pools, succession-plans |
| platform | /platform | sso-configs, webhooks, deliveries, background-checks, e-signatures |
| compliance | /compliance | rules, violations, checks, headcount-plans, scenarios, report-definitions, saved-reports |
| import-export | /import-export | entities, export, import |
| onboarding-portal | /onboarding-portal | clients, settings, feature-flags, integrations, migrations, onboarding, docs, by-slug |
| ess | /ess | profiles, notifications, employee-files, announcements, directory, org-chart, goal-alignments, continuous-feedback, compliance-checks |

---

## 10. Test Scripts

| Script | Coverage |
|--------|----------|
| `backend/smoke_test.py` | Phase 1 (auth, employees, departments) |
| `backend/smoke_test_phase2.py` | Phase 2 (recruiting, onboarding) |
| `backend/smoke_test_phases_3_7.py` | Phases 3-7 (39 checks) |
| `backend/smoke_test_client_onboarding.py` | Client Onboarding (18 checks) |
| `backend/smoke_test_all_phases.py` | Phases 8-14 + ESS (65 checks) |
| `scripts/live_e2e.py` | Full live end-to-end (37 checks) |

---

## 11. Known Limitations

1. **Spin-down** — Free tier services sleep when idle; first request is slow
2. **Single schema** — App tables live in `ADMIN` schema
3. **Dynamic egress IPs** — No static outbound IP on free tier; ADB access via mTLS only
4. **No wildcard subdomains** — Render free tier doesn't support `*.karmathy.com`; using path-based `/t/:slug/`
5. **No real SSO flows** — SSO configs exist but actual SAML/OIDC authentication not implemented
6. **No real SCIM** — SCIM tokens exist but provisioning endpoints not implemented
7. **No real e-signature** — Status tracking only, no actual document signing
8. **No real background checks** — Status tracking only, no provider integration
9. **Payroll tax** — Simple percentage withholding, no real tax engine
10. **No mobile app** — Responsive web only
11. **No email notifications** — In-app notifications only, no email delivery
12. **No real-time updates** — Polling-based, no WebSocket
13. **No real SSO/SCIM flows** — Configuration only

---

## 12. File Structure

```
Karmathy/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── api.py (router registration)
│   │   │   └── endpoints/ (21 endpoint files)
│   │   ├── core/ (config, database, security, audit)
│   │   ├── crud/ (13 crud files)
│   │   ├── models/ (16 model files)
│   │   ├── schemas/ (15 schema files)
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
│   │   ├── components/ (Layout, ProtectedRoute, PublicLayout, ui, icons)
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
│   ├── CLIENT_ONBOARDING.md
│   └── FEATURE_INVENTORY.md
├── scripts/
│   └── render_deploy.py
├── render.yaml
├── docker-compose.yml
├── README.md
└── .env.example
```

---

## 13. Live URLs

| | |
|---|---|
| **Homepage** | https://karmathy-frontend.onrender.com/ |
| **Login** | https://karmathy-frontend.onrender.com/login |
| **Dashboard** | https://karmathy-frontend.onrender.com/dashboard |
| **API docs** | https://karmathy-backend.onrender.com/docs |
| **Health** | https://karmathy-backend.onrender.com/health |
| **DB health** | https://karmathy-backend.onrender.com/health/db |
| **Storage health** | https://karmathy-backend.onrender.com/health/storage |

---

## 14. Test Results (Last Run)

| Test suite | Checks | Status |
|------------|--------|--------|
| Phase 1 smoke test | 6 | ✅ |
| Phase 2 smoke test | 12 | ✅ |
| Phases 3-7 smoke test | 39 | ✅ |
| Client Onboarding smoke test | 18 | ✅ |
| Phases 8-14 smoke test | 65 | ✅ |
| Live E2E (hire-to-termination) | 37 | ✅ |
| **Total** | **177** | **✅ All pass** |

---

## 15. Brand Identity

### Brand positioning
"The complete HCM platform for a brighter tomorrow."

### Brand attributes
Trustworthy, intelligent, connected, adaptable, inclusive, precise, and globally scalable.

### Brand signature
"People. Potential. Progress."

### Logo concepts
- **Concept A**: The K symbol — geometric K with blue-to-teal transition
- **Concept B**: People and progress — abstract symbol of connected people
- **Concept C**: Premium enterprise monogram — architectural K monogram

### Color palette
- Primary blue: #2563EB
- Deep navy: #0F172A
- Teal: #06B6D4
- Growth green: #10B981
- Intelligence violet: #8B5CF6
- Page background: #F8FAFC
- Border: #E2E8F0
- Secondary text: #64748B
- Error: #DC2626
- Warning: #D97706

### Typography
- Primary: Inter (system fallbacks)
- Display: 56px/64px, weight 700
- H1: 44px/52px, weight 700
- H2: 32px/40px, weight 600
- H3: 24px/32px, weight 600
- Body: 16px/24px, weight 400
- Caption: 12px/16px, weight 500

### Layout
- 4px base spacing unit
- 12px card radius
- 44-48px button/input height
- 1280px max content width
- Subtle borders, restrained shadows
- Consistent icon sizing and stroke weight