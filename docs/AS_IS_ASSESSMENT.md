# Karmathy HCM — Current State Assessment (AS_IS_ASSESSMENT.md)

**Feature:** karmathy-phase-0-implementation-plan
**Repo:** `Karmathy/` (worktree `/Users/srinivas/LLM/Workforce/Karmathy`)
**Branch:** `feature/karmathy-phase-0-implementation-plan` · **Base commit:** `3850614`
**Status of record:** Phase 0 baseline (discovery only — no code, schema, or data changes)
**Prepared for:** EGM review remediation — Comprehension Finding 1 (Major: existing system never described)

---

## 1. Purpose and scope

This document describes the Karmathy HCM system **as it exists today**, measured against artefacts in the repository rather than against intentions. It is the `docs/AS_IS_ASSESSMENT.md` deliverable required by `HCM_SaaS_Agent_Requirements.md` §1.2 (Initial discovery deliverables, lines 69-83) and by contract AC-09.

It is written from these sources of record:

| Source | What it contributes | Path |
|--------|---------------------|------|
| Project Review Brief (verdict + honest list) | One-paragraph verdict; what works / what is missing; quality story; reviewer risks | `/Users/srinivas/LLM/Workforce/info.md` |
| Phase & feature tracker | Phase tracker (9 phases), domain tracker (143 capabilities), defect tracker, pending queue, deployment log | `Karmathy/STATUS.md` |
| Phase 0 audit | Page inventory, click-depth analysis, role-based home screens, backend gaps | `Karmathy/PHASE0_AUDIT.md` |
| Feature matrix (status of record) | 143 capabilities with per-row status, evidence, lane, priority, sensitivity, effort | `Karmathy/docs/product/FEATURE_MATRIX.md` |
| Feature linkages | Dependency atlas (foundations, employee thread, payroll tree, import chain, sequencing rules) | `Karmathy/docs/product/FEATURE_LINKAGES.md` |
| Requirements document | Sections 3.2, 4.4, 8.3, 16, 17, 19.3 referenced by line number | `/Users/srinivas/LLM/Workforce/HCM_SaaS_Agent_Requirements.md` |
| Backend source | FastAPI app, models, config, auth, visibility, encryption, migrations | `Karmathy/backend/app/` |

**Scope note (contract Non-goals):** This is Phase 0 discovery and decision recording only. No application code, database schema, migration, deployment, or credential change is made by this document. It describes; it does not remediate.

---

## 2. Executive summary

**Verdict (adapted from `info.md` §1):** Yes — for an HR system built the right way, but only about one-fifth of the way to a sellable product. The foundations are unusually solid: security is enforced everywhere, data changes are auditable, corrupting mistakes (for example deleting a department people belong to) are blocked by the system itself, and everything claimed is proven by automated tests. What is not yet there is the everyday surface an HR team lives in — the money (payroll execution end-to-end), the employee experience, and third-party integrations. Nothing built so far needs to be redone; the remainder is breadth, not repair.

**Plain-words description (`info.md` §2):** Karmathy is a cloud HR system for small-to-mid businesses: one company per database, so one customer's people, pay and records can never be seen by another. Each customer gets their own branded workspace in the browser. It covers the standard HR journey — hire people, put them in an org structure, record their time and leave, run payroll, give employees a self-service view, and keep the paperwork (docs, compliance, reports) tidy.

**Headline numbers (Phase-0 baseline of record):**

| Metric | Value | Source |
|--------|-------|--------|
| Target capabilities | 143 | `FEATURE_MATRIX.md` §Counts; `STATUS.md` §4 |
| Implemented (done) | 28 (19.6 %) | contract AC-09 baseline; `STATUS.md` §4 domain tracker |
| Partial | 58 | `STATUS.md` §4 domain tracker |
| Missing | 57 | `STATUS.md` §4 domain tracker |
| Broken | 0 | `FEATURE_MATRIX.md` §Counts (`STATUS.md` §1: "0 broken") |
| Post-baseline shipped (per STATUS §1) | ~38 / 143 (~26.6 %) after batches since baseline | `STATUS.md` §1 At-a-Glance |
| Defects open | 3 Low (D-029, D-017, D-045); 41 closed | `STATUS.md` §5 |
| Backend test suites | 33 suites · 4,172 checks · 0 failed | `STATUS.md` §1 |
| Security role-matrix checks | 1,779 · 0 failed | `STATUS.md` §1 |
| Browser journeys | 70 pass (54 desktop + 16 responsive) | `STATUS.md` §1 |
| Staging gate (Oracle) | 69 passed / 1 skipped, twice | `STATUS.md` §1 |
| Deployed (Render) | backend `dep-dbjb67bil8vc73aa092g` · frontend `dep-dbjb678gbm7c73fm6smg` (both `bfffd36`) | `STATUS.md` §1 |

*Note on count drift:* `FEATURE_MATRIX.md` §Counts prints implemented 28 / partial 59 / missing 56, while its own rows and `STATUS.md` §4 sum to 28 / 58 / 57; `STATUS.md` §1 reflects batches shipped after the Phase-0 baseline (~38 implemented). This assessment uses the contract-stated Phase-0 baseline of **28 implemented / 58 partial / 57 missing / 0 broken**, citing `STATUS.md` §4 as the domain tracker and `FEATURE_MATRIX.md` as per-row evidence.

---

## 3. Method

Every claim below is traceable to a named file, section, line, or test suite. Where two source documents disagree (for example capability counts), both figures are shown with their source so the reviewer can reconcile rather than inherit a single number. No behaviour is asserted from a live response alone; per the matrix evidence rule (`FEATURE_MATRIX.md` §Status vocabulary, lines 8-20), a capability counts as implemented only when an automated check at a named commit demonstrates it.

---

## 4. Architecture as deployed

### 4.1 Logical layout

The system is a **modular monolith** (one codebase, one deployed backend, one deployed frontend) serving many tenants through configuration and entitlements rather than customer-specific code. This matches the preferred starting architecture in `HCM_SaaS_Agent_Requirements.md` §3.1 (lines 158-178).

| Layer | Component | Technology / version | Evidence (file, line) | Status |
|-------|-----------|----------------------|-----------------------|--------|
| Presentation | Tenant HCM app + marketing site | React 18, TypeScript, Vite 5, Tailwind v3, Radix, TanStack Query/Table/Virtual | `HCM_SaaS_Agent_Requirements.md` §Interfaces/data (line 27); `frontend/src/App.tsx` | Deployed |
| Presentation | Pages | 22 page components (~4,700 LOC) per `PHASE0_AUDIT.md` §1; `frontend/src/pages/` lists ~38 page files including marketing pages | `PHASE0_AUDIT.md` §1; `frontend/src/pages/` | Deployed |
| Presentation | Routes | 35 routes in `App.tsx`: 22 top-level + 13 tenant-scoped `/t/:tenantSlug/*` | `PHASE0_AUDIT.md` §1 | Deployed |
| API / application | FastAPI application | FastAPI 0.111.0, Python 3.11, Pydantic 2.7.4 | `HCM_SaaS_Agent_Requirements.md` §Interfaces/data (line 25); `backend/app/main.py:35` | Deployed |
| API | Route surface | ~154 endpoints under `/api/v1` | `PHASE0_AUDIT.md` §1 | Deployed |
| API | Auth/deps | Bearer JWT, role checks, visibility filters | `backend/app/api/deps.py` (lines 79-313) | Deployed |
| Domain modules | Core HR, payroll, time, leave, recruiting, onboarding, offboarding, benefits, performance, learning, forecasting, scheduling, compliance, ESS | SQLAlchemy 2.0 models | `backend/app/models/` (23 model modules) | Deployed (partial per domain) |
| Tenant context & authorization | Role-based access control + object-level visibility | 5 roles: SuperAdmin, HR, Manager, Associate, PayrollViewer | `backend/app/api/deps.py:79-82`; `backend/app/models/user.py:36-50`; `backend/app/core/visibility.py:44` | Deployed |
| Config & metadata | Settings, presets, readiness check | Pydantic Settings; 6 versioned industry presets | `backend/app/core/config.py`; `backend/app/core/presets/` | Deployed (partial) |
| Workflow & rules | Payroll rule packs, merit cycles | Verified jurisdiction rule packs; demo pack refused | `backend/app/` rules/; `rule_packs/` | Partial (PY-09 partial) |
| Persistence | Oracle Autonomous Database (thin mode) + local SQLite for tests | `oracledb` thin mode, SQLAlchemy, Alembic | `backend/app/core/database.py:1-52`; `backend/alembic.ini` | Deployed |
| Persistence | Migrations | 28 Alembic versions; head `0026_employment_history` | `backend/migrations/versions/` (28 files); `STATUS.md` §1 | Deployed |
| Integration & background | Durable job queue + worker | Job leases, heartbeats, dead-letter, retry/discard | `backend/app/jobs/worker.py`; `backend/app/main.py:104-158` | Deployed (worker off by default) |
| Observability & audit | Structured logging, security headers, hash-chained audit trail | CSP/HSTS/etc.; `record_audit` + triggers; `verify_audit_chain` | `backend/app/main.py:66-70`; `backend/app/core/audit_chain.py`; `scripts/verify_audit_chain` | Deployed |
| File storage | Local disk (ephemeral) or OCI object storage | `STORAGE_BACKEND=local` default; `oci` for production | `backend/app/core/config.py:112-117`; `.env.example:29-34` | Deployed (local default) |
| Hosting / deployment | Render (backend + frontend services) | Docker-compatible; `render.yaml`, `docker-compose.yml` | `STATUS.md` §1 Production; `render.yaml` | Deployed |
| CI | GitHub Actions, secret scan, OpenAPI drift | `.github/workflows/ci.yml`; `ci/secret_scan.py` | `STATUS.md` §Interfaces/data (line 27) | Deployed |

### 4.2 Backend entry and diagnostics (`backend/app/main.py`)

`app = FastAPI(...)` is created at `main.py:35`. Startup (`main.py:104` `on_startup`) runs Alembic migrations in a background thread (`MIGRATE_ON_STARTUP`, `config.py:79`), seeds admin users, and starts the job worker only when `JOB_WORKER_ENABLED` is set (`config.py:95`, default `false`). Diagnostic endpoints:

| Endpoint | Auth | Purpose | Source |
|----------|------|---------|--------|
| `GET /` | public | API identity/version | `main.py:256-258` |
| `GET /health` | public | Liveness probe | `main.py:294-297` |
| `GET /health/db` | operator (bearer) | DB connection + migration state (Oracle `SELECT 1 FROM DUAL` vs SQLite `SELECT 1`) | `main.py:300-342` |
| `GET /health/schema` | operator | Live schema vs SQLAlchemy models drift report | `main.py:345-389` |
| `GET /health/storage` | operator | Storage backend round-trip probe (save/read/checksum/delete) | `main.py:392-429` |
| `GET /health/wallet` | operator | Oracle wallet file names only (never contents/DSN/passwords) | `main.py:432-455` |

### 4.3 Configuration (`backend/app/core/config.py`)

Pydantic `Settings` (lines 5-178). Relevant names (values intentionally omitted, per contract AC-06 / requirements §1.1):

- Database: `DATABASE_URL`, `ORACLE_WALLET_DIR`, `ORACLE_DSN`, `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_WALLET_PASSWORD`
- Security: `SECRET_KEY`, `ALGORITHM` (pinned `HS256`), `ACCESS_TOKEN_EXPIRE_MINUTES` (30), `REFRESH_TOKEN_EXPIRE_DAYS` (14), `PASSWORD_MIN_LENGTH` (12), `PASSWORD_HISTORY_DEPTH` (5), `LOGIN_MAX_FAILED_ATTEMPTS` (10), `LOGIN_LOCKOUT_SECONDS` (900), `LOGIN_RATE_LIMIT_ATTEMPTS` (10), `LOGIN_RATE_LIMIT_WINDOW_SECONDS` (300), `FIELD_ENCRYPTION_KEYS`, `FIELD_ENCRYPTION_ACTIVE_KEY_ID`, `ALLOW_SELF_REGISTRATION` (false), `PUBLIC_DIAGNOSTIC_ENDPOINTS` (false), `BACKEND_CORS_ORIGINS`
- Operations: `MIGRATE_ON_STARTUP` (true), `LOG_LEVEL`, `JOB_WORKER_ENABLED` (false), `JOB_WORKER_POLL_SECONDS` (2.0), `JOB_WORKER_LEASE_SECONDS` (300), `JOB_WORKER_SHUTDOWN_SECONDS` (15.0), `RETENTION_SCHEDULE_ENABLED` (false), `RETENTION_RUN_INTERVAL_HOURS` (24.0)
- Storage: `STORAGE_BACKEND` (`local`), `LOCAL_STORAGE_DIR`, `OCI_NAMESPACE`, `OCI_BUCKET_NAME`, `OCI_CONFIG_FILE`, `OCI_PROFILE`
- `CONTENT_SECURITY_POLICY`, `ENVIRONMENT`

`settings.validate()` (lines 139-178) fails fast: rejects non-HS256 JWT algorithm, enforces `SECRET_KEY >= 32` chars in production, `PASSWORD_MIN_LENGTH >= 12` (citing NIST SP 800-63B), `ACCESS_TOKEN_EXPIRE_MINUTES <= 60`.

### 4.4 Tenancy

The deployment model observed in code is **one Oracle Autonomous Database instance serving one customer per deployed workspace** — consistent with Gate 0 decision D-01 (`docs/DECISION_LOG.md` §Gate 0, D-01): "one Oracle schema per customer (schema-per-tenant). Each deployment serves exactly one customer; schema selection is configuration (`DB_SCHEMA`), not code. Cross-tenant queries are impossible by construction: there is no tenant dimension in any query because there is only ever one tenant in the database."

`HCM_SaaS_Agent_Requirements.md` §4.4 (lines 315-335) requires a tenancy decision comparing shared-schema-with-discriminator, schema-per-tenant, database-per-tenant, and hybrid, evaluating Oracle VPD/RLS and connection management. That comparison is **open**: contract AC-01 recommends shared schema with tenant discriminator, while Gate 0 D-01 already decided schema-per-tenant. The lead/owner must reconcile before the requirements document is finalized and record the winner in `DECISION_LOG.md` (contract Open decisions).

Within a tenant, data isolation is enforced by role-based authorization (`app/api/deps.py`) and object-level visibility (`app/core/visibility.py`), not by a tenant discriminator column on every table. There is no `tenant_id` column visible in the model set reviewed; multi-tenant scale on a single shared schema is therefore **not yet implemented** — see §7 (architectural gaps) and §9 (risks).

---

## 5. What works (evidence-backed)

The list below is what is **real and working right now**, verified by automated checks — not a plan. Adapted from `info.md` §3 with source references.

| Area | What works | Evidence (file, line / suite) | Status |
|------|-----------|-------------------------------|--------|
| Getting started | Create a company workspace from six prepared business templates (retail, hospitality, etc.); readiness check reports missing/inconsistent items and writes nothing | `info.md` §3; `FEATURE_MATRIX.md` CF-01..CF-10 (implemented) | Implemented |
| People & structure | Employee directory with server-side search/filter, `N of total`, `Load more`; documents on person profile; full lifecycle (create/edit/archive/restore/delete guarded by `409 reference_in_use`) for departments, jobs, locations, positions, cost centres | `info.md` §3; `FEATURE_MATRIX.md` HR-04 (partial); `master_data_test_suite` (35 checks) | Partial |
| Employment lifecycle | State machine Active → On Leave → Terminated → Rehired; `409 invalid_state_transition`; effective-dated `employee_history` (status/type/job/dept/manager/salary + actor + reason + effective date); newer change closes old row; nothing edited in place | `info.md` §3; `FEATURE_MATRIX.md` HR-02/HR-03 (partial); `employment_history_test_suite` (85 checks) | Partial |
| Audit trail | Every write chained; `source_ip_hash` (SHA-256); `details` redacted for salary/bank/national-ID/DOB/card; lockout and unknown-username sign-in audited; mutation and row commit together; hash chain verifiable by CLI and by audit-screen button | `info.md` §5; `FEATURE_MATRIX.md` AD-07 (implemented); `audit_test_suite` (29 checks); `audit_chain_test_suite` (57 checks); `scripts/verify_audit_chain` | Implemented |
| Hiring | Requisitions, candidates, applications, offers; offer accept → hire creates employee + onboarding checklist | `info.md` §3; `FEATURE_MATRIX.md` RC-01/RC-03/RC-05 (partial) | Partial |
| Time & attendance | Clock in/out, timesheets (generate/submit/approve), approval flows, shift templates, swaps | `info.md` §3; `FEATURE_MATRIX.md` TM-01 (partial); `SC-06` swaps (partial) | Partial |
| Leave | Ledger-backed balances (balance = sum of signed ledger rows; a balance that moves without a row is refused); requests/approvals/cancellation/overlap/delegation | `info.md` §3; `FEATURE_MATRIX.md` LV-02/LV-03 (implemented); `leave_test_suite` (100 + 560 checks) | Implemented |
| Payroll (partial, correctness gap closed) | Pay calculated only from approved time and leave; unapproved timesheets excluded and reported; overtime at employee's derived rate; only unpaid leave deducts; every payslip records inputs in `inputs_json`; run refuses with `422 rule_pack_not_verified` before calculating and writes nothing | `info.md` §3; `FEATURE_MATRIX.md` PY-03/PY-10 (implemented); `payroll_test_suite` (13 + 148 checks) | Implemented (partial domain) |
| Bulk import | Templates; exact header matching + aliases; type/enum/date validation; formula-injection neutralisation; dry run with counts + row-error CSV + confirmation token bound to result hash; idempotent upsert on natural keys; background worker with progress, cancel, dead-letter; progress endpoint | `info.md` §3; `FEATURE_MATRIX.md` IM-01..IM-09 (mostly implemented); `import_test_suite` (504 checks); `job_worker_test_suite` (42 checks); `e2e/import-queued.spec.ts` | Implemented |
| Self-service (minimal) | Employees sign in and see their own record | `info.md` §3; `FEATURE_MATRIX.md` UX-03 (partial) | Partial |
| Marketing site | Rebuilt 2026-10-28; outcome-led homepage, bento module grid, industry deep-dives, pricing, security, FAQ, comparison; all links resolve to real pages; contact form → intake queue; `/platform` public showcase | `info.md` §3; `STATUS.md` §7 Deployment Log | Deployed |
| AI module (honest) | `/ai` maps planned AI capabilities to real project status and gates; states AI is after the release gate — no invented capabilities | `info.md` §3; `STATUS.md` §7 (2026-11-01) | Deployed (Phase 8 not started) |
| Natural keys | Auto-generated codes (EMP-/DEP-/JOB-/POS-/LOC-/CC-) with uniqueness check; "Auto" hint; inline validation | `info.md` §3; `STATUS.md` §7 (2026-11-01 bfffd36) | Implemented |
| Public contact | `POST /public/contact`: three fields only, per-IP rate limit, daily cap, 16 KB body limit, `Intake` state separate from HR case queue, 90-day retention | `FEATURE_MATRIX.md` UX-10 (implemented); `deps.py` `require_roles` public surface | Implemented |

---

## 6. What does not work

### 6.1 Missing capabilities (by domain)

Per `STATUS.md` §4 Feature Domain Tracker (143 capabilities: 28 done / 58 partial / 57 missing / 0 broken) and `FEATURE_MATRIX.md` per-row evidence:

| Domain | Total | Done | Partial | Missing | Representative missing capabilities |
|--------|-------|------|---------|---------|-----------------------------------|
| Core HR & organisation (HR-) | 12 | 0 | 8 | 4 | HR-08 custom fields, HR-10 contingent workers, HR-12 export/retention/erasure, HR-05 multi-entity |
| Recruitment (RC-) | 8 | 1 | 4 | 3 | RC-04 interview kits/scorecards, RC-06 candidate comms/career site, RC-07 funnel analytics |
| Onboarding/mobility/offboarding (OB-) | 7 | 0 | 3 | 4 | OB-03 equipment/access tasks, OB-04 probation, OB-05 transfers/promotions, OB-07 rehire dashboards |
| Time & attendance (TM-) | 5 | 0 | 3 | 2 | TM-02 attendance policies/missed-punch corrections, TM-04 shift-based/fixed-schedule attendance |
| Leave (LV-) | 5 | 2 | 2 | 1 | LV-04 team availability/absence calendars |
| Scheduling (SC-) | 10 | 0 | 2 | 8 | SC-02 demand staffing, SC-03 availability, SC-04 hard constraints (no solver), SC-05 soft constraints, SC-07 coverage alerts, SC-08 multi-location, SC-09 versioning, SC-10 plan-vs-actual |
| Payroll & compensation (PY-) | 10 | 2 | 7 | 1 | PY-07 bank export; plus PY-04/PY-05/PY-08 partial |
| Benefits (BN-) | 6 | 0 | 2 | 4 | BN-02 employer contributions/claims, BN-03 renewals, BN-05 knowledge base, BN-06 external provider integration |
| Performance & talent (PM-) | 6 | 0 | 3 | 3 | PM-03 competency/calibration, PM-04 improvement plans, PM-06 promotion readiness |
| Learning & skills (LN-) | 7 | 0 | 2 | 5 | LN-02 mandatory training, LN-04 skills taxonomy, LN-05 skill gaps, LN-06 mentoring, LN-07 analytics |
| Analytics & planning (AN-) | 8 | 0 | 6 | 2 | AN-03 headcount/attrition projections, AN-06 actual-vs-plan reconciliation |
| Employee & manager experience (UX-) | 10 | 1 | 9 | 0 | — (all partial; UX-10 contact form done) |
| Tenant admin & platform ops (AD-) | 10 | 2 | 4 | 4 | AD-03 locale/TZ/currency/working week, AD-05 workflow config, AD-08 backup/restore, AD-09 retention/export/erasure |
| Presets & config assistant (CF-) | 14 | 11 | 1 | 2 | CF-11 ten-step onboarding journey, CF-13 curated help index |
| CSV import (IM-) | 12 | 9 | 2 | 1 | IM-10 upload retention schedule (purge exists, nothing schedules it) |
| AI capability & governance (AI-) | 13 | 0 | 0 | 13 | AI-01..AI-13 all missing; AI-12 mandatory controls not yet landed |
| **Total** | **143** | **28** | **58** | **57** | |

Also missing per `PHASE0_AUDIT.md` §9 (backend gaps, out of scope for Phase 0): no `/auth/register` endpoint; no `/ess/*` endpoints; no `/time/today` endpoint; no `/reports/attendance` endpoint.

### 6.2 Architectural gaps (frontend / experience)

Measured in `PHASE0_AUDIT.md` §2 Critical gaps:

| Gap | Evidence | Impact |
|-----|----------|--------|
| No role-based home | `/dashboard` is identical for all 5 roles (`PHASE0_AUDIT.md` §2) | Associate sees irrelevant stat cards; Manager has no approvals inbox |
| No command palette | zero grep hits for `cmdk`/`⌘K` | Navigation = scroll sidebar only |
| No keyboard shortcuts | no `g p` / `?` / ⌘K | Power users cannot move fast |
| No dark mode | zero `dark:` variants | WCAG preference ignored |
| TanStack Query unused | dependency present, **0 imports** | Every page re-implements loading/error/retry; no caching or polling |
| TanStack Table unused | not installed | No sorting/filtering/column visibility/virtualization |
| No toast system | ad-hoc `<div role=alert>` | No undo, stacking, auto-dismiss |
| `window.prompt` friction | `Recruiting.tsx:573` | Blocks JS, unstyled, no validation |
| 7× duplicated employee picker | `value={selected}` in Onboarding, Time, Scheduling, Leave, Offboarding, Platform, Recruiting | Inconsistent, no server search (D-045) |
| Inline alerts duplicated | `bg-red-50 border-red-200` in 8+ pages | Inconsistent, no icons/dismiss |
| No `<main>` landmark on `/login` | verified | Screen reader cannot jump to content |

Click-depth analysis (`PHASE0_AUDIT.md` §3): associate clock-in takes 4 clicks; manager leave approval 5; HR headcount 3; reaching any page 3-5. Role-based home screens are proposed (`PHASE0_AUDIT.md` §5) but not implemented — `FEATURE_MATRIX.md` UX-01 is partial ("needs your action" content not query-driven).

### 6.3 Production and operational concerns

| Concern | Detail | Source |
|---------|--------|--------|
| No hosted staging | Free-tier constraint; staging runs on a laptop against real Oracle (`KARMA_STAGE`) | `STATUS.md` §1 Environments; SUP-04 partial |
| Ephemeral document storage | `STORAGE_BACKEND=local` means documents are lost on redeploy; OCI is the production setting but not default | `FEATURE_MATRIX.md` AD-08; `main.py:392-429` health probe |
| Upload retention not scheduled | `purge_expired_uploads` exists and is tested, but nothing enqueues `retention_run` periodically (`RETENTION_SCHEDULE_ENABLED` off by default) | `FEATURE_MATRIX.md` IM-10 (missing) |
| No DSAR / export / erasure / legal hold | No endpoint in the 259 served operations | `FEATURE_MATRIX.md` HR-12/AD-09 (missing) |
| Payroll not execution-ready | No run approval/lock, off-cycle corrections, proration, explicit currency, or bank-ready payment file | `info.md` §4; `FEATURE_MATRIX.md` PY-04/PY-07/PY-08 |
| Employee self-service hub thin | Payslips to employees, leave self-flow, documents, announcements not built out | `info.md` §4 |
| Integrations not built | No accounting sync, no IdP (e.g. Google sign-in), no API consumption by other tools | `info.md` §4; AD-06 partial (webhooks/SSO configs exist, no provider integrated) |
| No SSO/OIDC provider integrated | `/platform/sso-configs` exists; authentication is local bearer JWT only | `FEATURE_MATRIX.md` AD-06 (partial) |
| 301 `operationId` warnings | Contract `operationId` ≠ app route name (cosmetic) | `STATUS.md` §5 D-029 |
| Seed guard ordering | Seed prod guard runs after `app.models` import | `STATUS.md` §5 D-017 |

---

## 7. Data model summary

SQLAlchemy 2.0 declarative models (`backend/app/models/`), registered in `app/main.py:11-33`. Key tables:

| Domain | Key models / tables | File | Notes |
|--------|---------------------|------|-------|
| Identity & access | `users` (5 roles, MFA, password history, lockout) | `user.py:16-155` | Role CHECK constraint admits only the 5 roles (`user.py:36-50`) |
| Core HR | `employees`, `employee_history` (effective-dated), `departments`, `jobs`, `positions`, `cost_centers`, `locations` | `employee.py`, `core_hr.py`, `department.py`, `job.py` | History: newer change closes previous row |
| Time & attendance | `time_entries`, `timesheets`, clock events | `time_attendance.py:1-` | TM-01 partial; no break model |
| Leave | `leave_requests`, `leave_ledger`, `leave_balances` | `leave.py:1-` | LV-02/LV-03 implemented (ledger-backed) |
| Payroll | `pay_runs`, `pay_components`, `pay_profiles`, `pay_slips` | `payroll.py:1-` | PY-03/PY-10 implemented; bank export missing |
| Recruiting | `requisitions`, `candidates`, `applications`, `offers` | `recruiting.py:1-` | Offer accept → hire transaction |
| Onboarding / offboarding | `onboarding` (+checklist/tasks/documents), `offboarding` (+tasks/items/terminations) | `onboarding.py`, `offboarding.py` | OB-06 partial; final settlement not linked to payroll |
| Benefits / performance / learning | `benefit_plans`/`benefit_enrollments`; `goals`/`reviews`/`merit_cycles`/`feedback`; `courses`/`course_enrollments`/`certifications` | `benefits.py`, `performance.py`, `learning.py` | All partial/missing per matrix |
| Scheduling | `shift_templates`, `roster`, `swaps` | `scheduling.py` | SC-01 partial; no solver (SC-04 missing) |
| Forecasting / compliance / planning | `forecast_runs`, `headcount_plans`, `scenarios`, `compliance_rules` | `forecasting.py`, `compliance.py` | AN-04 partial; projections missing |
| ESS | `ess_profile`, notifications, announcements, directory, org-chart | `ess_hr.py` | UX-03 partial |
| Client onboarding | `client_onboarding` (presets, feature flags, workspaces) | `client_onboarding.py` | AD-01/AD-02 partial |
| Integrations platform | `webhooks`/`deliveries`, `sso_configs`, `integrations` | `integrations_platform.py` | AD-06 partial |
| Audit | `audit_entries` (hash-chained, append-only via triggers) | `audit.py` | AD-07 implemented |
| Job queue | `job_queue` (payload, hash, lease, heartbeat, state, dead-letter) | `job_queue.py` | AD-07 implemented |
| Idempotency | `idempotency_records` | `app/core/idempotency.py` | Import dry-run tokens |

`DB_SCHEMA.sql` (`Karmathy/docs/DB_SCHEMA.sql`) is the deployed-schema artefact (94 `CREATE TABLE` statements). `PHASE0_AUDIT.md` §1 cites 67 tables and 5 roles; the model set above reflects the code-reviewed surface. 28 Alembic migration versions exist, head `0026_employment_history` (`STATUS.md` §1 Migrations).

There is **no `tenant_id` discriminator column** on tenant-owned entities in the reviewed model set; isolation is by deployment (one customer per database/workspace) plus role/visibility controls within a tenant (§4.4).

---

## 8. Security and compliance posture

| Control | Implementation | Evidence (file, line / suite) | Gap |
|---------|---------------|-------------------------------|-----|
| Authorization | Server-enforced RBAC via `require_roles`; 250 protected operations + 4 public; role sets: ADMIN_ROLES, MANAGER_ROLES, WORKFORCE_ROLES, REPORTS_ROLES, ALL_ROLES | `app/api/deps.py:79-105, 263-313`; `security_test_suite` (1,475 checks: 1,250 negative + 129 positive + completeness) | Frontend does not consume entitlement flags for navigation (AD-02 partial) |
| Authentication | Local bearer JWT; algorithm pinned to HS256 (not configurable); access 30 min, refresh 14 days; per-IP rate limit 10/300s; account lockout 10 attempts/900s | `app/core/security.py:42, 132-164`; `config.py:31-41, 59-61`; `deps.py:130-152` | No SSO/OIDC provider integrated; no `/auth/register` |
| Password security | bcrypt over SHA-256 prehash (44 bytes, defeats 72-byte truncation); scheme marker `$krb1$`; history depth 5; transparent upgrade on login | `app/core/security.py:78-124` | None identified |
| Field encryption | Fernet `ENCv1:<key_id>:<token>`; key registry; active key derived from `SECRET_KEY` if no registry (warns, never plaintext); decryption failure raises, never returns ciphertext | `app/core/security.py:172-359`; `config.py:51-52` | Rotation not independently operational without key registry |
| Object-level visibility | Reporting-line scope (Manager: self + transitive reports, loop-protected MAX_DEPTH=12); Associate: self only; Global: SuperAdmin/HR/PayrollViewer; fail-closed when no employee link | `app/core/visibility.py:13-159` | Earlier audit found Associate could read entire directory; now closed |
| Audit trail | Hash-chained append-only; `UPDATE`/`DELETE` refused by DB triggers (DEC-027); `source_ip_hash`; `details` redacted; single head row via CAS; `verify_audit_chain` CLI + screen button | `app/core/audit_chain.py`; `audit_chain_test_suite` (57 checks); `scripts/verify_audit_chain` | None identified |
| HTTP security | SecurityHeadersMiddleware (CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy); CORS empty allow-list default (same-origin only), credentials disabled; production warning if CORS wildcard | `app/main.py:66-70, 50-64` | CSP customisable via env; not locked by default |
| Input validation | Pydantic schemas; import validation (types/enums/dates/duplicates/salary bounds); formula-injection neutralisation; masked sensitive values in error reports/logs | `FEATURE_MATRIX.md` IM-04/IM-05/IM-11 | IM-05 stored-value test not recorded |
| Secrets | Never in source control or logs; env var names only in `.env.example` | `.env.example`; `security.py` docstring | None identified |
| Compliance evidence | No compliance assertion without evidence; privacy/employment/tax/labour per launch jurisdiction to be assessed | `HCM_SaaS_Agent_Requirements.md` §16 (lines 945-947) | SOC2 etc. not claimed |
| Backup / restore | No backup or restore script found | `FEATURE_MATRIX.md` AD-08 (missing) | Gap |
| DSAR / erasure / legal hold | No export, retention scheduler, erasure, or legal-hold endpoint | `FEATURE_MATRIX.md` HR-12/AD-09 (missing) | Gap; legal exposure on first real customer |

---

## 9. Risks

| Risk | Severity | Source | Status / mitigation |
|------|----------|--------|---------------------|
| Breadth gap — 57 missing capabilities (and 58 partial) | High | `STATUS.md` §4; `FEATURE_MATRIX.md` | Not debt; not-yet-built. Sequencing: payroll first (info.md §7) |
| Payroll short of execution | High | `info.md` §4 §7; `FEATURE_MATRIX.md` PY-04/PY-07/PY-08 | Approval/lock, corrections, proration, currency, bank file not built; #1 revenue item |
| No hosted staging | Medium | `STATUS.md` §1 SUP-04 partial | Laptop-based Oracle staging works but is manual; paid tier recommended |
| Ephemeral document storage (`STORAGE_BACKEND=local`) | Medium | `FEATURE_MATRIX.md` AD-08 | Documents lost on redeploy; OCI production setting exists |
| Upload retention not scheduled | Medium | `FEATURE_MATRIX.md` IM-10 | `RETENTION_SCHEDULE_ENABLED` off; nothing enqueues `retention_run` |
| No DSAR / erasure / legal hold | Medium (legal exposure) | `FEATURE_MATRIX.md` HR-12/AD-09 | Not started; exposure on first real customer |
| No SSO/OIDC integration | Medium | `FEATURE_MATRIX.md` AD-06 | Local JWT only; `/platform/sso-configs` unconnected |
| 301 `operationId` warnings | Low (cosmetic) | `STATUS.md` §5 D-029 | Queue P2; publish `operationId` from app routes |
| Seed guard import order | Low | `STATUS.md` §5 D-017 | Queue S; fix import order |
| 7 pickers lack server-side search | Low | `STATUS.md` §5 D-045 | Next frontend batch; D-045 open |
| Demo data absent in production | Low (by design) | `info.md` §7 | Company data policy; revisit with approved operator step |
| Count drift between mirror docs | Low (process) | `FEATURE_MATRIX.md` §Counts vs `STATUS.md` §1/§4 | Reconcile at next baseline; this assessment cites both |

These risks map to the consolidated "Risks & Mitigations" section required by contract AC-08 (to be recorded in `DECISION_LOG.md` / requirements document).

---

## 10. Evidence of health

| Measure | Result | Source |
|---------|--------|--------|
| Backend suites | 33 suites · 4,172 checks · 0 failed | `STATUS.md` §1 |
| Security role-matrix | 1,779 checks · 0 failed | `STATUS.md` §1 |
| Browser journeys | 70 pass (54 desktop + 16 responsive at 360/768/1024/1440 px) | `STATUS.md` §1 |
| Accessibility | axe-core WCAG 2.2 A/AA over 20 pages in CI; 3 defects fixed | `STATUS.md` §5 QA-04; `info.md` §5 |
| Staging gate (Oracle) | 69 passed / 1 skipped, twice on `5e87961` | `STATUS.md` §1 |
| Contract drift | 314 matched · 36 planned · 0 failures · 0 undeclared | `STATUS.md` §1 |
| Frontend gates | `npm run verify` green — typecheck + route integrity (108 routes) + api-paths + design + build + classes | `STATUS.md` §1 |
| Migrations | `0026_employment_history` at head; release step applies cleanly | `STATUS.md` §1 |
| Production health | `/health` 200, contact 201, frontend 200 incl. unknown path | `STATUS.md` §7 Deployment Log |
| Broken capabilities | 0 | `FEATURE_MATRIX.md` §Counts |
| Open defects | 3 Low; 41 Critical/High/Medium closed | `STATUS.md` §5 |

---

## 11. Traceability to `HCM_SaaS_Agent_Requirements.md`

| Requirement | Section (line) | How this assessment addresses it |
|-------------|----------------|----------------------------------|
| Discovery deliverable `docs/AS_IS_ASSESSMENT.md` | §1.2 (lines 69-73) | This document |
| Repository structure, framework, versions, backend architecture | §1.2 (lines 79-80) | §4, §7 |
| Oracle connectivity and schema | §1.2 (line 80); §17 (lines 951-981) | §4.2-4.4; §7 |
| Authentication / authorization | §11 (lines 711-713) | §8 |
| Tenant handling | §4 (lines 255-335) | §4.4 |
| Deployment pipeline | §20 (lines 1079-1099) | §4.1 Hosting; `STATUS.md` §7 |
| Environment variables (names only) | §1.1 (line 60); §20 (line 1095) | §4.3; `.env.example` names cited, no values |
| Test coverage and known risks | §19 (lines 1012-1077); §9 risks | §9, §10 |
| Technology direction (FastAPI vs Spring Boot) | §3.2 (lines 180-235) | §4.1; FastAPI retained |
| Data tenancy strategy decision required | §4.4 (lines 315-335) | §4.4 (decision recorded as open in `DECISION_LOG.md`) |
| Definition of Done | §19.3 (lines 1061-1075) | Referenced; not restated (document-only phase) |
| Guardrails (WCAG 2.2 AA, keyboard, etc.) | §8.3 (lines 577-591) | §6.2 maps gaps to these guardrails |

---

## 12. Conclusion

The existing system is now described: a modular monolith (FastAPI backend + React/Vite frontend) on Oracle Autonomous Database, with 143 target capabilities of which 28 are implemented, 58 partial, 57 missing, and 0 broken. Security (RBAC, hash-chained audit, JWT HS256, field encryption, object-level visibility) is the strongest area and is fully test-covered. The principal gaps are breadth — payroll execution, employee self-service, integrations, DSAR/erasure, backup/restore — and frontend experience (role-based homes, command palette, dark mode, TanStack Query/Table). Nothing built needs to be redone; the remainder is breadth, not repair. This assessment is the baseline for the remaining Phase 0 documents (`GAP_ANALYSIS.md`, `TARGET_ARCHITECTURE.md`, `DECISION_LOG.md`, `IMPLEMENTATION_PLAN.md`) and for the requirements-document remediation in contract AC-01 through AC-08.

---

**Sources of record:** `Karmathy/info.md` (project root), `Karmathy/STATUS.md`, `Karmathy/PHASE0_AUDIT.md`, `Karmathy/docs/product/FEATURE_MATRIX.md`, `Karmathy/docs/product/FEATURE_LINKAGES.md`, `Karmathy/docs/DB_SCHEMA.sql`, `Karmathy/backend/app/`, `/Users/srinivas/LLM/Workforce/HCM_SaaS_Agent_Requirements.md`.
