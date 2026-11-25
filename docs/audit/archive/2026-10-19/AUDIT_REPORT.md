# Karmathy HCM — Project Audit Report

**Document audited:** `DOCUMENT.md` — *Karmathy HCM — Complete Feature & Design Document* (last updated 2026-10-19)
**Repository:** `/Users/srinivas/LLM/Workforce/Karmathy`
**Branch / commit audited:** `feature/hcm-slack-revamp`. At the start: `75c3cc5` (clean). During the audit the
frontend advanced to `91024a2` ("Phase 2: app shell, command palette, keyboard shortcuts, mobile nav"), and at
close there were **10 uncommitted frontend files**. Backend code is unchanged across `75c3cc5..91024a2`, so every
backend finding applies to both; frontend findings describe the working tree observed on 2026-10-19.
**Live system observed:** `https://karmathy-frontend.onrender.com` · `https://karmathy-backend.onrender.com`
**Audit date:** 2026-10-19
**Mode:** read-only. No application code, configuration, or data was modified by this audit. The frontend changes
above were not made by the audit.

---

## How to read this report

Every finding has an ID, the document's claim, what was actually found, evidence, severity and effort.
Findings are labelled **[Fact]** when verified by code, a command, or a live response, and **[Assumption]**
when inferred and not directly verified.

| Severity | Meaning |
|---|---|
| **Critical** | Blocks any real customer use: security breach, cross-tenant exposure, data loss, or wrong pay/leave |
| **High** | Major risk or a core capability that does not work as documented |
| **Medium** | Reliability, performance, accessibility or maintainability problem |
| **Low** | Polish, stale docs, cosmetic |

| Effort | Meaning |
|---|---|
| **S** | ≤ 1 engineer-day |
| **M** | 2–5 engineer-days |
| **L** | 1–3 engineer-weeks |
| **XL** | > 3 engineer-weeks |

**Test-environment caveat.** The host has only Python 3.15. The pinned backend versions
(`pydantic==2.7.4`, `sqlalchemy==2.0.29`) do **not** build/run on 3.15, so the suites were executed in a
throwaway venv with `fastapi 0.146.0`, `SQLAlchemy 2.1.5`, `pydantic 2.14.1`, against SQLite. Results prove the
application logic passes; they do **not** prove the pinned production set. See `commands_run.md`.
No real secrets, tokens, or connection strings are reproduced in this report.

### Owner decisions received (2026-10-19)

| Question | Answer | How it changes the audit |
|---|---|---|
| Team | **1 engineer** | All estimates assume a solo generalist; no parallel workstreams |
| Capacity | **20–40 h/week** | ~0.5–1 FTE |
| First pilot target | **1–3 months** | Drives the feasibility verdict |
| Budget | **$0 (free tiers only)** | No paid Render/Redis/monitoring; constraints on the plan |
| Compliance | **SOC 2, ISO 27001, GDPR, CCPA, India statutory payroll** | All five are required; none is currently evidenced |
| Design | **Engineers only** | UX work competes with engineering time |
| Regions | **India, US, UK/EU, Middle East, SEA** | Multi-jurisdiction payroll and data residency |
| Deployment model | **Single tenant per customer** | Changes tenant isolation from "schema-wide `tenant_id`" to "one deployment/database per customer"; still requires the marketing claim to change and object-level RBAC to be fixed |
| `base_salary` unit | **Per pay period** | Engine is correct; the **offer letter wording is wrong** and must change |
| Live testing | **Use documented default admin login** | Authenticated checks were run; default credential found still active |
| Data retention | **Per-region rules** | A7-01 must be region-aware; no single retention schedule can be implemented |

> The "single tenant per customer" answer means full schema-wide `tenant_id` isolation (finding A2-12) is **no
> longer the top blocker for a pilot**, provided every customer gets a physically separate deployment/database and
> the shared `clients` table is never used as a security boundary. It remains a blocker for any shared/demo
> environment. Object-level authorisation (A2-10/A2-11) stays **Critical** regardless.

---

## Executive summary (top 10)

Karmathy is a **broad, working single-organisation HCM application**. It is **not** a multi-tenant product,
despite what `DOCUMENT.md` says, and several high-value modules are readable or writable by any authenticated
user. The owner has since chosen a **single-tenant-per-customer** deployment model, which turns full schema-wide
tenancy into a provisioning task — but object-level authorisation is still **Critical** and the current shared
deployment still leaks between brands. The code is better than average for its stage: consistent layering, a real
audit trail, Decimal payroll arithmetic, structured errors, request IDs and a 435-check local test suite. The gaps
are concentrated in **object-level authorisation, migrations, money inputs and operations**.

| # | Issue | Severity | Effort |
|---|---|---|---|
| 1 | **No tenant isolation in the current shared deployment.** 0 of 77 tables carry `tenant_id`; cross-tenant read **and write** demonstrated. `/t/:slug/` changes branding only. Under the chosen *single-tenant-per-customer* model this becomes a deployment/provisioning project (**M per customer**) rather than schema-wide work — but the current shared instance is still unsafe and the multi-tenant claim is false. | Critical (shared) | XL shared / M per deployment |
| 2 | **Object-level authorisation is only partially wired.** 73 `GET` endpoints are open to *any* authenticated user with no visibility filter: all pay profiles, payslips, pay runs, performance reviews, compensation bands, merit allocations, benefit enrollments, colleagues' time entries/timesheets, ESS files and cases. | Critical | L |
| 3 | **IDOR on writes.** Any authenticated user can cancel another employee's leave request, edit any ESS profile, sign any e-signature, create leave for any employee, and create feedback/files against any employee. | Critical | M |
| 4 | **Payroll is not connected to time, leave or benefits**, and `base_salary` has no unit. The engine treats it as **per-period**; the offer letter calls it **"annual compensation"**. Real money is at stake. | High | L |
| 5 | **Storage is ephemeral in production.** `render.yaml` sets `STORAGE_BACKEND=local` on a free Render service: offer-letter PDFs and onboarding documents are lost on every redeploy. | High | S |
| 6 | **No schema migrations.** Alembic is in `requirements.txt` but there is no `alembic.ini`, no `migrations/`; only `create_all()` in a background thread plus one hand-written Oracle script. Schema drift is already documented. | High | M |
| 7 | **No CI gate.** The only workflow SSH-deploys to an Oracle VM; it runs no tests, lint, type-check or security scan. | High | S |
| 8 | **Default credential shipped, printed and still active.** `seed_admin.py` hardcodes `admin` + a default password (redacted; `seed_admin.py:24`), prints it, and `DEPLOYMENT.md` repeats it. On 2026-10-19 the documented credential authenticated to the **live** backend as SuperAdmin. | High | S |
| 9 | **RBAC is binary (admin vs everyone).** 127 operations use `get_current_admin_user`; 101 use "any authenticated". `Manager` and `PayrollViewer` have no distinct server-side permissions — a Manager cannot approve leave. | High | M |
| 10 | **Dependency debt.** 20 advisory IDs in pinned backend deps (starlette, python-multipart, python-jose, ecdsa, python-dotenv) and 2 moderate React Router advisories; **8** unused frontend dependencies. | High | M |

A one-page "what is actually trustworthy" summary is in §A6. The recommended decision is in
`FEASIBILITY.md` §7: **proceed only as a reduced-scope, single-tenant design partner after the security/storage
foundation; do not sell this as multi-tenant or claim compliance.**

---

# Part A — Audit findings

## A1. Inventory verification

### A1.1 Headline counts

| Item | `DOCUMENT.md` says | Actual (verified) | Verdict | Evidence |
|---|---|---|---|---|
| Backend routers | "20 routers" (§9) / "21 endpoint files" (§12) | **25 routers / 25 endpoint files** | **Mismatch** | `backend/app/api/v1/api.py` (25 `include_router`); `ls app/api/v1/endpoints/*.py` = 25 |
| Endpoints | "154+ endpoints" (§9) | **164 unique paths / 236 operations** | **Mismatch (understated)** | route walk + `application.openapi()`; live `/api/v1/openapi.json` agrees (164/236) |
| Database tables | "76 tables" (§8) | **77** (76 model tables + `idempotency_records`) | **Mismatch (+1)** | `grep -c __tablename__ app/models/*.py` = 76; `verify_tenant_isolation.py` prints `tables: 77` |
| Database models | not stated | **76 mapped classes in 20 files** | — | `grep -c "^class .*(Base)"` |
| Frontend pages | "22 pages" (§7) | **22 page files**, but the set differs: an undocumented `/design` showcase exists; the doc counts the tenant-scoped route as a page | **Partial mismatch** | `ls src/pages/*.tsx` = 22; `App.tsx:46` |
| Frontend routes | — | **35 `<Route>` elements**: 22 top-level (incl. `/design`), 12 tenant-scoped, 1 catch-all | — | `frontend/src/App.tsx` |
| Components | "Layout, ProtectedRoute, PublicLayout, ui, icons" | **22 component files** (3 shell + 16 `ui/` + `icons.tsx` + legacy `ui.tsx`) | — | `ls src/components` |
| Test scripts | **6** (§10) | **14 scripts**: 11 local suites + `e2e_lifecycle.py` + `live_e2e.py` + `verify_tenant_isolation.py` | **Mismatch** | `backend/*_test_suite.py`, `scripts/*` |
| Test checks | **177** (§14) | **435 numbered local checks** (all pass) + the phase-2 smoke flow + 5 tenant checks (fail, expected) | **Mismatch** | see A4 |
| `crud/` files | 13 | **15** | Mismatch | `ls app/crud` |
| `schemas/` files | 15 | **20** | Mismatch | `ls app/schemas` |
| `services/` files | 2 | **6** | Mismatch | `ls app/services` |
| `models/` files | 16 | **20** | Mismatch | `ls app/models` |

**A1-01 — Documentation inventory is stale.** Severity **Medium**, Effort **S**.
`DOCUMENT.md` §7–§12 and `docs/FEATURE_INVENTORY.md` (which repeats "67 tables / 154 endpoints / 20 routers")
do not describe the code that is deployed. Anyone onboarding from the document will look for the wrong number
of routers, tables and tests. Evidence: the table above; `docs/FEATURE_INVENTORY.md:546,572`.

### A1.2 Endpoint inventory by router (actual)

| Router | File | Operations |
|---|---|---|
| `/auth` | `auth.py` | 4 |
| `/employees` | `employees.py` | 4 |
| `/departments` | `departments.py` | 3 |
| `/jobs` | `jobs.py` | 3 |
| `/requisitions` | `requisitions.py` | 4 |
| `/candidates` | `candidates.py` | 4 |
| `/applications` | `applications.py` | 4 |
| `/offers` | `offers.py` | 7 |
| `/onboarding` | `onboarding.py` | 8 |
| `/time` | `time_attendance.py` | 11 |
| `/scheduling` | `scheduling.py` | 11 |
| `/leave` | `leave.py` | 10 |
| `/offboarding` | `offboarding.py` | 11 |
| `/reports` | `reports.py` | 9 |
| `/onboarding-portal` | `client_onboarding.py` | 23 |
| `/core-hr` | `core_hr.py` | 13 |
| `/payroll` | `payroll.py` | 13 |
| `/performance` | `performance.py` | 15 |
| `/benefits` | `benefits.py` | 9 |
| `/learning` | `learning.py` | 12 |
| `/platform` | `integrations_platform.py` | 12 |
| `/compliance` | `compliance.py` | 13 |
| `/import-export` | `import_export.py` | 4 |
| `/data-quality` | `data_quality.py` | 3 |
| `/ess` | `ess_hr.py` | 21 |
| app-level (`/`, `/health*`) | `main.py` | 5 |
| **Total** | | **236** |

Not listed in `DOCUMENT.md` §9 at all: `/data-quality`, and the app-level diagnostics. The doc's router table
lists "20" and omits `data-quality` and `ess` routing nuances.

### A1.3 `docs/` drift

| Doc | Claim | Reality | Drift |
|---|---|---|---|
| `docs/API_CONTRACT.md` | 150-line contract; ends at Phase 7 status enums | Only Phases 1–7 + auth/offers; no payroll, performance, benefits, learning, platform, compliance, ESS, data-quality, import/export | **High** — more than half the API is undocumented |
| `docs/DB_SCHEMA.sql` | "DB schema" | **22** `CREATE TABLE` statements, stopping at `audit_logs` (Phase 7). 55 tables missing | **High** |
| `docs/AUTH_ROLES.md` | "`get_current_user` → 403 on invalid"; "Public: `/auth/register`"; role table implies Manager/PayrollViewer permissions | Code returns **401** + `WWW-Authenticate` (`deps.py:37-41`); register is **disabled by default** (`config.py:26`); Manager/PayrollViewer have **no distinct server permissions** (0 role-helper uses) | **High** |
| `docs/DEPLOYMENT.md` | Lists `/health/db`, `/health/storage`, `/health/wallet` as public URLs; says wallet lives in `backend/wallet/` | All three return **401** anonymously (verified live); `render.yaml` mounts `/etc/secrets` | **Medium** |
| `docs/CLIENT_ONBOARDING.md` | 6-step portal, integration kinds, migration runner | Endpoints exist and are admin-gated; but the portal is **not tenant-isolating** (clients are rows, not boundaries) | **High** (security framing) |
| `docs/FEATURE_INVENTORY.md` | 67 tables / 154 endpoints / 20 routers | 77 / 164 paths (236 ops) / 25 | **Medium** |

**A1-02 — API and schema docs cover roughly half the product.** Severity **High**, Effort **M**.
Evidence: `grep -c "CREATE TABLE" docs/DB_SCHEMA.sql` = 22; `docs/API_CONTRACT.md` headings stop at Offboarding/Reports.

---

## A2. Backend health

### A2.1 Architecture

**What the document says:** "FastAPI + SQLAlchemy 2.0", endpoints → crud → models, 13 crud files, 21 endpoint files.

**What was found [Fact]:** The layering exists and is mostly respected.

- Routers register in `app/api/v1/api.py`; dependencies in `app/api/deps.py`; DB session via `get_db()`.
- Domain logic is split between `crud/` (15 files) and `services/` (payroll engine, offer letter, storage, importer,
  data quality, metrics). Most endpoints are thin; a few (`ess_hr.py`, `integrations_platform.py`, `compliance.py`)
  contain business logic directly in the router.
- **Circular imports:** none found at import time — the app imports and 236 routes register in tests. Several
  modules use function-local imports to avoid cycles (e.g. `core/visibility.py` imported inside handlers), which is
  a smell but not a failure.
- **Dependency injection:** consistent use of `Depends(get_db)` and `Depends(get_current_*)`.
- **Duplication:** `_calculate_payslips` lives in the router rather than `services/`; compliance "checks" are simulated
  (`ess_hr.py:327-330`, explicitly `# Simulate a check`).

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A2-01 | Business logic in routers (`payroll._calculate_payslips`, ESS, compliance) rather than services; makes testing and reuse harder | Medium | M |

### A2.2 Database

| Check | Document claim | Actual | Verdict | Evidence |
|---|---|---|---|---|
| Schema matches models | implied | `create_all()` creates all models; **no diff check** | Not verified | no migration tooling |
| Migrations | not mentioned | **Alembic listed but not configured**; no `alembic.ini`, no `migrations/`; `create_all()` in a daemon thread at startup | **Missing** | `requirements.txt:12`; `main.py:91-108`; `find . -iname "*alembic*"` → none |
| Indexes on FKs / filters | not mentioned | **0 `Index()` declarations in 20 model files**. Oracle does **not** auto-index FK columns (unlike MySQL). Common filters (`employee_id`, `status`, `work_date`, `pay_run_id`) are unindexed except where a unique constraint exists | **High** | `grep -c "Index(" app/models/*.py` = 0 |
| Identity columns | "all tables use Identity()" | `Identity()` used throughout; one historical `autoincrement=True` incident is recorded | Pass | `PHASE2_STATUS.md:99-101` |
| N+1 queries | — | Few true N+1s in request paths; `ess_hr.sync_directory` and `rebuild_org_chart` query per employee in a loop | Medium | `ess_hr.py:191-214,237-269` |
| Pagination | — | Only some list endpoints paginate (`skip`/`limit`); payroll, ESS, performance, benefits, learning, core-hr, time, scheduling, compliance lists return **all rows** | Medium | `payroll.py:85-86`; `ess_hr.py:113-117` |
| Transaction boundaries | — | Payroll run: one commit at the end (good) + a **separate** audit commit. Offer hire: `create_employee()` commits, checklist commits, then candidate/application commit, then audit commit — a failure mid-way leaves a **partial hire** | **High** | `payroll.py:277-288`; `offers.py:215-254`; `crud_employee.create_employee` commits |
| Tenant discriminator | `DOCUMENT` implies multi-tenancy (§4) | **0 of 77 tables have `tenant_id`**; `users` has no tenant FK | **Critical** | `verify_tenant_isolation.py`: 0 passed, 5 failed; `grep -rn tenant_id app/models` = 0 |

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A2-02 | No migration tooling; schema changes rely on `create_all()` which never ALTERs existing tables. A stale DB already produced a 503 (documented in `REVAMP_NOTES.md` #10) | High | M |
| A2-03 | Zero model-level indexes; Oracle leaves FK columns unindexed, so list filters and joins will table-scan as data grows | High | M |
| A2-04 | Offer→hire is not atomic: employee and checklist commit before candidate/application status and audit | High | M |
| A2-05 | Unbounded list endpoints (no pagination) on payroll/ESS/performance/benefits/learning/core-hr/time/scheduling/compliance | Medium | M |
| A2-06 | Per-employee queries inside loops in directory sync and org-chart rebuild | Medium | S |

### A2.3 Security

#### JWT, password hashing, secrets

| Check | Document claim | Actual | Verdict | Evidence |
|---|---|---|---|---|
| JWT algorithm | "HS256" | `ALGORITHM` is **configurable via env** and used as the allow-list (`algorithms=[settings.ALGORITHM]`); default HS256. Not hard-pinned to HS256 | Medium | `config.py:21`; `deps.py:29-31`; `security.py:22-23` |
| Secret strength | not stated | `SECRET_KEY` is required but **no minimum length or entropy check**; Render generates one (`render.yaml:14-15`), local `.env.example` is a placeholder | Medium | `config.py:20` |
| Expiry | "configurable expiry" | 30 min default; **no refresh token, no revocation, no logout server-side** | Medium | `config.py:22`; `create_access_token` |
| bcrypt 72-byte truncation | "handled" | **Handled**: `_to_bytes` slices to 72 bytes for both hash and verify | Pass | `security.py:8-34` |
| Fernet key derivation | "key derived from SECRET_KEY" | Key = `SHA256(SECRET_KEY)`; **no rotation/versioning**. On decrypt failure it **returns the ciphertext as-is** (silent plaintext fallback) | High | `security.py:37-65` |
| Secrets in code/logs | — | Default admin password hardcoded and printed (`seed_admin.py:24,42`); observability redacts 25 key names (good) | High | `seed_admin.py`; `core/observability.py` |
| CORS | "configured" | Explicit allow-list, `allow_credentials=False`, warns in production if unset — **good**. Default is empty (deny) | Pass | `main.py:48-62`; `config.py:54-61` |
| Rate limiting | not in doc | In-process sliding window on login/register; **per-replica**, in-memory only | Medium | `core/rate_limit.py:1-13` |
| Input validation | "Pydantic" | Pydantic schemas on bodies; several list filters are unvalidated free strings (`status`, `year`); `employee_id` query params accepted without ownership checks | Medium | e.g. `leave.py:123-144` |
| mTLS / wallet | "required" | Thin-mode wallet config supported; wallet files are local and **not committed**; `STORAGE_BACKEND=local` in `render.yaml` | Pass (mTLS) / High (storage) | `database.py:9-16`; `render.yaml:28-29` |

#### RBAC — measured, per operation

Static analysis of all **231 endpoint functions** (AST: which auth dependency each function uses):

| Auth level | Count | Meaning |
|---|---|---|
| `get_current_admin_user` (SuperAdmin/HR only) | **127** | writes and admin reads |
| `get_current_active_user` (any authenticated role) | **101** | reads and self-service writes |
| Public (no auth) | **3** | `/auth/login`, `/auth/register` (gated), `/onboarding-portal/clients/by-slug/{slug}` |

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A2-07 | **RBAC is effectively binary.** There are **zero** uses of a role helper for `Manager` or `PayrollViewer`. Consequently: a Manager **cannot approve leave** (approval uses `get_current_admin_user`, `leave.py:168`), and `PayrollViewer` gets the same read access as any authenticated user. The role table in `DOCUMENT.md` §5 is not implemented server-side. | High | M |
| A2-08 | **Public tenant resolver** `GET /onboarding-portal/clients/by-slug/{slug}` returns tenant branding/config (name, colours, logo, timezone, locale, status) unauthenticated. Needed for branding, but it also confirms tenant existence and is the only tenant-scoped lookup | Medium | S |
| A2-09 | `ALGORITHM` is env-configurable rather than pinned; a misconfiguration could change accepted algorithms | Medium | S |

#### Object-level data visibility — **the largest authorisation gap**

`app/core/visibility.py` implements a sound policy (self / self+reporting line / all, fail-closed). It is used in
**exactly 3 endpoint files** — `employees.py`, `leave.py`, `offboarding.py` — and **5 call sites**.
The other **73 `GET` endpoints available to any authenticated user have no visibility filter**:

- `/payroll/pay-profiles`, `/payroll/payslips`, `/payroll/runs` — **all compensation and payslips**
- `/performance/reviews`, `/feedback`, `/compensation-bands`, `/merit-allocations`, `/goals`
- `/benefits/benefit-enrollments`, `/life-events`, `/leaves-of-absence`
- `/time/entries`, `/time/timesheets` — colleagues' hours
- `/scheduling/roster`, `/swaps`
- `/ess/employee-files`, `/ess/directory` (directory is arguably intended), `/ess/compliance-checks`, `/ess/goal-alignments`
- `/core-hr/employee-documents`, `/cases`, `/cases/{id}/comments`
- `/onboarding/{employee_id}/documents`, `/tasks`, `/summary`
- `/offboarding/terminations/{id}/progress`
- `/reports/dashboard|headcount|leave|labor-cost|attendance|metrics`

**Writes with no ownership check (IDOR):**

| Endpoint | Impact | Evidence |
|---|---|---|
| `POST /leave/requests/{id}/cancel` (any authenticated) | Cancel **another employee's** leave | `leave.py:214-226` |
| `POST /leave/requests` (any authenticated) | File leave **as another employee** (`employee_id` in body) | `leave.py:147-161` |
| `PUT /ess/profile/{employee_id}` (any authenticated) | Edit **any employee's** self-service profile | `ess_hr.py:63-74` |
| `POST /ess/employee-files` (any authenticated) | Attach files to any employee | `ess_hr.py:120-125` |
| `POST /ess/continuous-feedback` (any authenticated) | Write feedback about any employee | `ess_hr.py:302-307` |
| `PUT /platform/e-signatures/{id}/sign` (any authenticated) | **Sign another person's e-signature** | `integrations_platform.py:175-186` |
| `PUT /ess/notifications/{id}/read` (any authenticated) | Mark another user's notification read | `ess_hr.py:97-107` |

> This directly contradicts `docs/PHASE2_STATUS.md:46`, which records "Object-level data visibility (P1-3) —
> Completed and verified". The 29-check suite only covered employees, leave and terminations.

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A2-10 | 73 any-auth GET endpoints have no object-level visibility filter; compensation, performance, benefits, timesheets and documents are exposed to every logged-in user | **Critical** | L |
| A2-11 | Seven any-auth writes allow cross-employee modification (cancel leave, edit ESS, sign e-signature, etc.) | **Critical** | M |

#### Tenant isolation

| Check | Result | Evidence |
|---|---|---|
| Tenant column on HCM tables | **0 / 77** | `verify_tenant_isolation.py` |
| `users` tenant reference | **absent** (`id, username, email, hashed_password, role, is_active, employee_id, created_at`) | same |
| Cross-tenant read | Acme's user sees Globex's client row | suite output |
| Cross-tenant write | Globex **renames** Acme's client → HTTP 200, `HIJACKED BY GLOBEX` | suite output |
| Remediation | `scripts/migration_sql/TENANT_SCOPING.sql` written, **never executed** | file header; `PHASE2_STATUS.md:64` |
| Frontend `/t/:slug/` | branding only | `TenantContext.tsx:204-253` |

**A2-12 — No tenant isolation in the current shared deployment.** Severity **Critical (shared)**, Effort **XL**;
under the owner's chosen **single-tenant-per-customer** model, Effort drops to **M per deployment**.
`DOCUMENT.md` §4 presents subdomain/path tenant routing as if it separates data. It does not, and the live shared
instance demonstrates cross-brand read **and write**. Applying the migration is a coordinated DDL + backfill + code +
verification operation; it is only required if the shared model is retained. For the chosen model, the fix is to
provision a separate deployment and Oracle schema per customer, remove `clients` as a security boundary, and stop
describing the product as multi-tenant. Object-level authorisation (A2-10/A2-11) is unaffected and remains Critical.

#### Audit trail

| Check | Result | Evidence |
|---|---|---|
| Mutations audited | All endpoint files with mutations call `record_audit` (PHASE2 claim reproduced) | `grep`; `visibility_test_suite` |
| Atomic with operation | Yes where the handler commits once; payroll and offer-hire commit the audit separately | `audit.py:1-32`; `payroll.py:277-288` |
| Immutable/tamper-evident | No — ordinary rows, no hash chain, no delete protection | Medium |
| Read access | Admin-only after the P1-3 fix | `reports.py` (2 admin deps) |
| Login audited | Yes | `auth.py` |

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A2-13 | Audit rows are not tamper-evident and some are written in a second transaction after the action | Medium | M |

### A2.4 Error handling and observability

| Check | Result | Evidence |
|---|---|---|
| Consistent error envelope | Yes: `{error:{code,category,message,retryable,details,request_id}}`; 9 categories | `core/errors.py` (per PHASE2) |
| Request IDs | Inbound `X-Request-ID` echoed; generated otherwise | live test in `PHASE2_STATUS.md:130` |
| Structured logs + redaction | JSON logs, recursive scrub of 25 sensitive keys | `core/observability.py` |
| Health checks | `/health` public; `/health/db`, `/health/storage`, `/health/wallet` require auth (401 verified live) | `main.py:149-228` |
| Metrics | No Prometheus/OpenTelemetry endpoint; `reports/metrics` is a business metric catalogue, not infrastructure metrics | `reports.py` |
| Error tracking | No Sentry/equivalent | — |
| Dependency failure | 503 + `Retry-After`, raw exceptions hidden | `errors.py` (per PHASE2) |

**A2-14 — No infrastructure metrics or error tracking.** Severity **Medium**, Effort **M**.

### A2.5 Business-logic correctness

| Area | Document claim | What the code does | Verdict |
|---|---|---|---|
| Payroll withholding | "Simple percentage withholding" (§11) | Flat percentage of gross, clamped 0–100, Decimal + `ROUND_HALF_UP` | Matches limitation; **not statutory** |
| Payroll inputs | §9 implies pay runs "auto-calculate" | Gross = `base_salary` only. **Approved leave, overtime and benefit deductions are not fed in** | **High gap** |
| `base_salary` unit | not stated | Engine docstring: **per pay period**. Offer letter text: **"annual compensation"**. **Owner confirmed per-period on 2026-10-19** | **Wording defect — High** |
| Payroll state machine | not detailed | `Draft→Processing→Approved→Finalized→Paid`, SoD, no-empty-run, finalize lock, idempotency | Good |
| Terminated employees | — | Excluded (`Active`/`On Leave`), excluded set reported | Good |
| Leave accrual | "tenure-based entitlements" | Base entitlement + `min(tenure_years, 5)` extra days **only for paid types**; `tenure_years = entitlement_year - hire_date.year` (calendar-year, not anniversary) | Partial / minor off-by-one |
| Leave working days | — | Weekdays only; **no public-holiday calendar**, no half-days, no jurisdiction calendar | Partial |
| Leave approval | — | Balance moves once; over-draw capped at entitlement+carryover; missing-entitlement audited | Good |
| Timesheet overtime | "overtime" | `max(hours/day − 8, 0)` only; no weekly overtime, no rate multipliers, no jurisdiction rules | Partial |
| Offer-letter PDF | "offer-letter PDF" | Generated with fpdf2; says **annual compensation**; signed blank line, no e-sign | Works, wording risk |
| Roster generation | "roster generation" | `/scheduling/roster/generate` exists; logic is template repetition for a date range (no demand/coverage optimisation) | Works as a stub-level feature |
| Compliance checks | "compliance rules/violations" | `run_compliance_checks` marks **every** rule passed (`# Simulate a check`) | **Stub** |

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A2-15 | Payroll ignores approved leave, overtime and benefit deductions | High | L |
| A2-16 | `base_salary` is per-period (owner-confirmed), but the offer letter calls it **"annual compensation"** — fix the wording, not the engine | High | S |
| A2-17 | Leave accrual uses calendar-year tenure and no holiday calendar; overtime has no weekly/rate rules | Medium | M |
| A2-18 | Compliance "checks" always pass — it is a simulation, not a rule engine | High (if marketed) | L |

### A2.6 Async and background work

| Long-running task | Where it runs | Timeout / recovery |
|---|---|---|
| Payroll processing | Synchronously in the request (`payroll.process_run`) | No timeout; loop over all profiles; idempotency key; one transaction |
| Offer-letter PDF | Synchronously in the request (`offers.generate_offer_letter`) | No timeout; storage write inline |
| Webhook delivery | Synchronously in the request (`integrations_platform.deliver_webhook`) | `urlopen(timeout=10)`, **single attempt**, no retry/backoff |
| Directory sync / org-chart rebuild | Synchronously, per-employee queries | No batching |
| Data import | Synchronously via `services/importer.py` (savepoints per batch) | Partial recovery via savepoints |

**A2-19 — No background job system.** Severity **High**, Effort **L**. Long operations run in the web request,
blocking a worker and risking platform timeouts; webhook failures are never retried.

### A2.7 Webhooks

| Check | Result | Evidence |
|---|---|---|
| Real HTTP delivery | **Yes** — `urllib.request` POST | `integrations_platform.py:96-115` |
| Signing | HMAC-SHA256 over body in `X-Webhook-Signature` | `:99-104` |
| Retry policy | **None** — one attempt, status set to Failed | `:109-115` |
| Failure recovery | No queue, no dead-letter, no re-drive endpoint | — |
| SSRF protection | **None** — admin-supplied URL fetched from the server | `:97` |
| Secret storage | Fernet-encrypted with SECRET_KEY-derived key | `:60-61` |

**A2-20 — Webhooks have no retry, no dead-letter and no SSRF guard.** Severity **High**, Effort **M**.

---

## A3. Frontend health

### A3.1 Build and types

| Check | Result | Evidence |
|---|---|---|
| `npx tsc --noEmit` | **Pass, exit 0** | command log |
| `npx vite build` | **Pass** — **263 modules**, 1.27 s (current working tree); 152 modules at `75c3cc5` | build output |
| Bundle | `index.js` **604.63 kB** (179.61 kB gzip), `index.css` 37.96 kB (8.18 kB gzip) — grew from 467.02 kB / 133.73 kB at `75c3cc5` after the Phase 2 shell | build output |
| Code splitting | **None** — a single JS chunk | build output |
| Warnings | Vite warns the JS chunk is **>500 kB** after minification (new with the Phase 2 shell) | build output |

### A3.2 Structure

- State: React context only (`AuthContext`, `TenantContext`); **no server-state library in use**.
  `@tanstack/react-query` is installed but **0 imports**. Every page hand-rolls `useState` + `useEffect` + `catch`.
- API calls: a single axios instance in `lib/api.ts`; no domain hooks; no shared cache.
- Duplication: the employee picker is reimplemented on ~7 pages; inline error/success banners are repeated.
- Large files (>300 lines): `Recruiting` 600, `Platform` 543, `ClientOnboarding` 515, `Design` 421,
  `Layout` 397, `Homepage` 370, `Offboarding` 351, `Leave` 346, `Scheduling` 320, `TimeAttendance` 303.
- Prop drilling: limited; most components are page-local.
- `Platform.tsx` was migrated to controlled inputs (good), but the page is still a 543-line tab monolith.

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A3-01 | No server-state layer in use: `QueryProvider` is wired, but there are **0** `useQuery`/`useMutation` call sites; every page hand-rolls fetch/loading/error logic | Medium | M |
| A3-02 | Monolithic pages (600/543/515 lines) mixing tabs, forms and data access | Medium | L |

### A3.3 API layer

| Check | Result | Evidence |
|---|---|---|
| Token attached | Request interceptor reads `karmathy_token` from localStorage | `api.ts:24-30` |
| Error normalisation | Maps `{error:{...}}` onto `detail`; preserves 422 list shape; retryable + request ID helpers | `api.ts:45-95` |
| **401 handling** | **None** — no response interceptor clears the token or redirects to login. An expired token leaves the user on a page that errors | `grep -rn "401"` in `src/` = 0 |
| **403 handling** | Pages show the generic error banner; no role-aware message | — |
| Token refresh | **No refresh endpoint and no refresh logic** | `api.ts` |
| Shared types | Hand-written in `src/types/index.ts` (323 lines); **not generated from OpenAPI** | `types/index.ts` |

**A3-03 — No 401/403 session handling and no token refresh.** Severity **High**, Effort **M**.
**A3-04 — API types are hand-written and already partially drift from the backend.** Severity **Medium**, Effort **M**.

### A3.4 Routing and auth

| Check | Result | Evidence |
|---|---|---|
| `ProtectedRoute` correctness | Checks **only** `!!token`; **no role check** | `ProtectedRoute.tsx:8-13` |
| Role checks in UI | **None** — `grep "user.role"` in `src/` = 0 imports/usages | command log |
| Auth state on reload | `user` is **not persisted** and there is **no `/auth/me`**, so after reload `user` is `null`; account menu shows "User"/"—" and pages cannot branch on role | `AuthContext.tsx:7-35` |
| Login redirect | Always `navigate("/dashboard")`; ignores `/t/:slug/login` and any deep-link destination | `Login.tsx:30` |
| Tenant deep links | Anonymous `/t/acme/leave` → `<Navigate to="/login">` → login → `/dashboard`, **losing the tenant slug** | `ProtectedRoute.tsx:11`; `App.tsx:60-72` |
| Invalid slug | Tenant context sets a warning and falls back to default branding; data is still global | `TenantContext.tsx:249-251` |
| Missing tenant | Same fallback | same |
| Catch-all | `*` → `/` | `App.tsx:74` |

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A3-05 | `ProtectedRoute` has no role check; all authenticated users can open every page (server still enforces on writes, but the UI overstates access) | High | M |
| A3-06 | `user` is lost on reload (no `/auth/me`, not persisted) — role/identity-dependent UI cannot work | High | S |
| A3-07 | Tenant context is lost on login/redirect; deep links and `/t/:slug/*` are not preserved | Medium | M |
| A3-08 | Login always lands on `/dashboard`; no `returnTo` | Low | S |

### A3.5 Tenant theming

`deriveTheme(primary, secondary)` (`TenantContext.tsx:137-196`) is real and does three useful things:
1. picks black/white button text by contrast;
2. darkens the accent until it reaches 4.5:1 **as text on white**;
3. lightens a tint until dark text is readable on it, and emits warnings.

**Strengths:** invalid hex → `null` → default theme; CSS variables are actually consumed under `[data-tenant]`
(`index.css:442-463`). This closes the earlier "inert theme" defect.

**Weaknesses:**

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A3-09 | Only `primary`/`secondary` are validated; the **secondary colour** is applied raw and is never contrast-checked (`deriveTheme` returns `--tenant-secondary` unchanged). A tenant can set an unreadable secondary. | Medium | S |
| A3-10 | A tenant `logo_url` is rendered in `<img>` with no size/format validation; an arbitrary external URL is fetched into the authenticated shell (tracking/SSRF-to-user risk). | Low | S |
| A3-11 | Derived-theme warnings are shown to **every** user as a page banner (`themeError`), which is operator-facing text in an end-user surface. | Low | S |

### A3.6 Accessibility

**Verified live on the homepage** (browser evaluation of the rendered DOM):

| Check | Result |
|---|---|
| `lang` | `en` ✅ |
| `<main>` | 1 ✅ |
| `<nav>` | 1 ✅ |
| `<h1>` | 1 ✅ |
| Heading order | sequential ✅ |
| Images without `alt` | 0 (no `<img>` on homepage) ✅ |
| Form controls without labels | 0 (no form controls on homepage) ✅ |
| Buttons without accessible name | 0 ✅ |
| **Skip link** | **absent on the public homepage** ❌ (present in the authenticated `Layout`, `Layout.tsx:193`) |

**Static audit of the authenticated shell:** skip link, `aria-current`, `aria-expanded`, `aria-controls`, focus
management on Escape, `aria-label` on collapsed rail items, and `sr-only` labels are present
(`Layout.tsx:152-229,324-355`). `index.css` defines `:focus-visible`, `prefers-reduced-motion` and `.skip-link`.

**Authenticated pages — verified live** (logged in as SuperAdmin with the documented default credential, read-only
navigation; DOM-level checks, not the full axe-core rule engine):

| Page | Unlabelled controls | Unnamed buttons | `alt` gaps | `<main>` | Skip link | Heading order | Low-contrast text |
|---|---|---|---|---|---|---|---|
| `/dashboard` | **0** | 0 | 0 | ✅ | ✅ | ✅ | 8 (breadcrumb `/` 1.42:1, `›` 1.48:1) |
| `/recruiting` | **0** (6 controls) | 0 | 0 | ✅ | ✅ | ✅ | 2 (breadcrumb separators) |
| `/leave` | **0** (10 controls) | 0 | 0 | ✅ | ✅ | ✅ | 2 (breadcrumb separators) |
| `/time` | **0** (3 controls) | 0 | 0 | ✅ | ✅ | ✅ | 2 (breadcrumb separators) |
| `/platform` | **0** | 0 | 0 | ✅ | ✅ | ✅ | 2 (breadcrumb separators) |

This **contradicts the stale note** in `ENHANCEMENT_INVENTORY.md:132-136` ("42 unlabelled form controls").
Those defects have since been fixed on these pages. The remaining contrast failures are decorative breadcrumb
separators (`/`, `›`) rather than body copy; they are exposed to screen readers as text and should be
`aria-hidden` or darkened.

**Lighthouse (live, browser tool; accessibility / best-practices / SEO only — the tool does not run a performance
benchmark or emulate a device):**

| Page | Accessibility | Best Practices | SEO | Failures |
|---|---|---|---|---|
| Public homepage | **0.95** | 1.00 | 1.00 | 1: insufficient colour contrast |
| `/platform` (authenticated) | **1.00** | 1.00 | 1.00 | none |

This independently confirms that **contrast is the only automated a11y failure on the homepage**, and that the
audited authenticated page is clean. (Lighthouse uses an axe-derived rule set; it does not test keyboard traversal
or focus traps.)

**Not verified:** keyboard-traversal and focus-trap behaviour. A full axe-core run in CI is still recommended.

**Brand-token contrast (computed, WCAG 2.1):**

| Token | Hex | On white | Result |
|---|---|---|---|
| Primary blue | `#2563EB` | **5.17:1** | ✅ AA |
| Text secondary | `#64748B` | **4.76:1** | ✅ AA |
| Error | `#DC2626` | **4.83:1** | ✅ AA |
| Navy | `#0F172A` | **17.85:1** | ✅ AA |
| Violet | `#8B5CF6` | **4.23:1** | ❌ AA for normal text |
| Warning | `#D97706` | **3.19:1** | ❌ AA for normal text |
| **Teal** | `#06B6D4` | **2.43:1** | ❌ fails even AA-large (3:1) |
| **Growth green** | `#10B981` | **2.54:1** | ❌ fails even AA-large (3:1) |

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A3-12 | Brand tokens `#06B6D4` (2.43:1) and `#10B981` (2.54:1) cannot carry text on white; `#D97706` and `#8B5CF6` fail AA for normal text. The document claims "sufficient contrast ratios" (§2). | High | S |
| A3-13 | No automated axe run in CI. Lighthouse: **0.95** a11y on the homepage (contrast), **1.00** on `/platform`; DOM checks found **0** unlabelled controls on the top 5 authenticated pages. Keyboard traversal/focus traps not tested | Low | S |
| A3-14 | Public pages have no skip link | Low | S |

### A3.7 Responsive behaviour

**Static verification (breakpoints in code):**

- `Layout.tsx`: desktop rail `hidden lg:block` (≥1024 px), mobile drawer `lg:hidden` with hamburger,
  `aria-expanded`/`aria-controls`, Escape-to-close and body-scroll lock. This fixes the earlier "no nav below
  1024 px" defect.
- Container: `px-4 sm:px-6 lg:px-8`, `max-w-container` (1280 px).
- Cards/grids use Tailwind responsive prefixes across pages.

**Live viewport testing at 360 / 768 / 1024 / 1440 px: Not verified** (no viewport-emulation tool exposed in
this session; browser resize was not performed). Marked Not verified rather than guessed.

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A3-15 | Responsive behaviour at 360/768/1024/1440 was not measured; only breakpoint code was reviewed | Medium (verification gap) | S |

### A3.8 Performance

| Metric | Value | Evidence |
|---|---|---|
| JS bundle | **604.6 kB raw / 179.6 kB gzip**, single chunk (467 kB / 133.7 kB at `75c3cc5`) | `vite build` |
| CSS | 37.96 kB / 8.18 kB gzip | `vite build` |
| Code splitting | none | build output |
| Images | homepage has **0 `<img>`** (1 inline SVG) | live DOM |
| Fonts | Inter is declared but **no webfont is loaded**; rendering falls back to the system stack | `ENHANCEMENT_INVENTORY.md:121-125`; no `@font-face` |
| Lighthouse | A11y **0.95** homepage / **1.00** `/platform`; BP & SEO **1.00**; performance score not measured (tool does not benchmark) | browser Lighthouse |
| Cold start | Backend first request **42.4 s** on free tier | live curl |

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A3-16 | Single **604.6 kB** bundle (179.6 kB gzip), no route-level code splitting; Vite now warns >500 kB | Medium | M |
| A3-17 | Declared Inter font is never delivered, so typography does not match the design system | Low | S |
| A3-18 | Lighthouse a11y measured: homepage **0.95** (contrast), `/platform` **1.00**; best-practices/SEO **1.00**. Performance score not measured (tool does not run a benchmark) | Low | S |

### A3.9 Dead code and unused dependencies

| Item | Finding | Evidence |
|---|---|---|
| `@tanstack/react-query` | **Provider wired but no hooks**: 0 `useQuery`/`useMutation` call sites | grep |
| `@tanstack/react-virtual` | declared, **0 imports** | grep |
| `date-fns` | declared, **0 imports** | grep |
| `lucide-react` | declared, **0 imports** (custom `icons.tsx` is used) | grep |
| `@radix-ui/react-progress`, `react-checkbox`, `react-switch`, `react-label`, `react-slot` | declared, **0 imports** | grep |
| `/design` page | 421-line showcase shipped behind auth and linked from the command palette, top bar and drawer; undocumented in §7 | `App.tsx:46`; `CommandPalette.tsx:40`; `TopBar.tsx:109`; `Layout.tsx:149` |
| `window.prompt` | still used for "Employee ID for the new hire" | `Recruiting.tsx:573` |
| Theme toggle | now present (`ThemeToggle.tsx`, rendered in `TopBar.tsx:80`) — the earlier "no toggle" note is stale | code |

**A3-19 — Eight unused dependencies, a shipped `/design` route and a `window.prompt`.** Severity **Low**, Effort **S**.
**A3-20 — `window.prompt` remains in the hire flow.** Severity **Medium**, Effort **S**.

---

## A4. Testing and quality

### A4.1 Test execution results (local, SQLite, fresh DB per suite)

| Suite | Result | Notes |
|---|---|---|
| `backend/smoke_test.py` | **6 steps, complete** | Auth, department, employee, list, 401 |
| `backend/smoke_test_phase2.py` | **complete** | Hire + onboarding summary |
| `backend/smoke_test_phases_3_7.py` | **39 passed, 0 failed** | Time, scheduling, leave, offboarding, reports |
| `backend/smoke_test_client_onboarding.py` | **20 passed, 0 failed** | Doc says 18 — stale |
| `backend/smoke_test_all_phases.py` | **67 passed, 0 failed** | Doc says 65 — stale |
| `backend/security_test_suite.py` | **66 passed, 0 failed** | |
| `backend/visibility_test_suite.py` | **29 passed, 0 failed** | Only employees/leave/terminations |
| `backend/ops_model_test_suite.py` | **40 passed, 0 failed** | Idempotency, concurrency, errors |
| `backend/import_test_suite.py` | **43 passed, 0 failed** | |
| `backend/data_quality_test_suite.py` | **44 passed, 0 failed** | |
| `backend/metrics_test_suite.py` | **41 passed, 0 failed** | |
| `scripts/e2e_lifecycle.py` | **40 passed, 0 failed** | Hire→termination lifecycle |
| `scripts/verify_tenant_isolation.py` | **0 passed, 5 failed** | **Expected** — evidence for A2-12 |
| `scripts/live_e2e.py` | **Not run** | Requires live credentials and writes data; the audit stayed read-only |

**Total numbered local checks: 435 passing** (plus the phase-2 smoke flow, which prints step-by-step results rather
than a count). The five tenant failures are the intended negative evidence. An earlier draft said "492"; that was an
arithmetic error (the 40 e2e checks were counted twice).

**Reproducibility caveat:** the suites are not fully idempotent in place (they use a relative SQLite path);
each was run in a fresh directory. `REVAMP_NOTES.md` #8 and #10 already document the SQLite path and stale-schema
issues.

### A4.2 Coverage gaps (zero or thin)

| Area | Coverage |
|---|---|
| Tenant isolation | Negative suite only (fails) |
| Object-level visibility | 3 modules only (employees, leave, terminations); 73 endpoints untested for scoping |
| Payroll ↔ time/leave/benefits | None (feature absent) |
| Payroll tax correctness for any jurisdiction | None |
| Offer→hire partial-failure rollback | None |
| Webhook retry/failure paths | Delivery happy path only |
| SSO/SCIM/e-sign/background checks | Configuration CRUD only |
| Frontend unit tests | **None** — no test runner installed |
| Frontend E2E | None in CI |
| Accessibility | No automated axe run in CI (Lighthouse run manually: 0.95 homepage, 1.00 `/platform`) |
| Load/performance | None |
| Backup/restore | None |

### A4.3 CI

`.github/workflows/deploy.yml` is the **only** workflow. It triggers on `push: main`, SSHes to an Oracle VM,
pulls, writes `.env` from GitHub secrets, and runs `docker compose up -d --build`. It does **not** run tests,
lint, type-check, dependency audit, or a security scan. Render's auto-deploy on `main` also bypasses any gate.

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A4-01 | No CI quality gate on any PR; 435 checks exist but nothing runs them automatically | High | S |
| A4-02 | No frontend test runner or automated accessibility check | High | M |
| A4-03 | The 5 failing tenant checks are "expected" but there is no test that fails the build on a *new* leak | Medium | S |

### A4.4 Dependency vulnerabilities

`pip-audit -r backend/requirements.txt` (pinned set):

| Package | Version | Advisories | Fix available |
|---|---|---|---|
| `starlette` | 0.37.2 | 7 IDs (PYSEC-2026-161/248/249/1941/1943/2280/2281) | ≥0.40 / 1.x |
| `python-multipart` | 0.0.9 | 7 IDs (PYSEC-2026-1851/1852/3036–3040) | ≥0.0.31 |
| `python-jose` | 3.3.0 | 4 IDs (PYSEC-2024-232/233, 2025-185, 2026-4298) | 3.4.0 |
| `ecdsa` | 0.19.2 (transitive) | 1 ID (PYSEC-2026-1325) | — |
| `python-dotenv` | 1.0.1 | 1 ID (PYSEC-2026-2270) | 1.2.2 |

`npm audit --omit=dev`: **2 moderate** in `react-router` (open redirect via backslash; arbitrary constructor
injection in SSR hydration). Fix requires `react-router-dom@7` (breaking).

| ID | Finding | Severity | Effort |
|---|---|---|---|
| A4-04 | 20 backend advisory IDs in pinned dependencies (Starlette, python-multipart, python-jose, ecdsa, python-dotenv) | High | M |
| A4-05 | 2 moderate React Router advisories; fix is a major upgrade | Medium | M |
| A4-06 | Several declared frontend deps are unused (A3-19), increasing audit surface | Low | S |

---

## A5. Deployment and operations

### A5.1 Configuration review

| File | Finding |
|---|---|
| `render.yaml` | Backend Docker free plan; frontend static free; `STORAGE_BACKEND=local`; `SECRET_KEY` generated; `BACKEND_CORS_ORIGINS` manual; no `ALLOW_SELF_REGISTRATION` (safe default); health check `/health` |
| `backend/Dockerfile` | Not reviewed line-by-line this pass; pinned requirements |
| `.github/workflows/deploy.yml` | Deploy-only; no tests; writes `.env` from secrets; targets an Oracle VM that is **not** the Render deployment |
| `scripts/render_deploy.py` | Idempotent create/reuse; reads secrets from `~/.render` and `~/.karmathy`; not audited for log leakage |
| `docker-compose.yml` | Backend + nginx; mounts `./backend` into the container (dev-style, not immutable) |

**A5-01 — Two divergent deployment paths (Render and Oracle VM) and CI targets only the VM.** Severity **Medium**, Effort **M**.

### A5.2 Environment variables

| Variable | Required | Default | Risk |
|---|---|---|---|
| `SECRET_KEY` | **Yes** (no default) | — | No strength validation; rotation would orphan Fernet-encrypted secrets |
| `DATABASE_URL` **or** `ORACLE_DSN`+`ORACLE_USER`+`ORACLE_PASSWORD`(+`ORACLE_WALLET_DIR`) | **Yes** | — | Fails fast if absent |
| `ORACLE_WALLET_DIR` / `ORACLE_WALLET_PASSWORD` | Wallet mode | `None` | Wallet files must be present |
| `ALGORITHM` | No | `HS256` | Configurable, not pinned |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | — |
| `ALLOW_SELF_REGISTRATION` | No | `False` | Safe |
| `PUBLIC_DIAGNOSTIC_ENDPOINTS` | No | `False` | Safe |
| `BACKEND_CORS_ORIGINS` | No | `""` (deny) | Production warns if unset/`*` |
| `LOGIN_RATE_LIMIT_*` | No | `10 / 300s` | — |
| `STORAGE_BACKEND` | No | `local` | **Production is `local`** → data loss |
| `OCI_NAMESPACE`/`OCI_BUCKET_NAME`/`OCI_CONFIG_FILE` | OCI mode | `None`/`~/.oci/config` | OCI config file is not a Render secret file by default |

**A5-02 — `STORAGE_BACKEND=local` in `render.yaml` on ephemeral disk.** Severity **High**, Effort **S**.
Offer letters (`offers.py:130-132`) and onboarding documents are written to `/tmp/karmathy-storage` (default) and
lost on redeploy/restart. `DEPLOYMENT.md:111-113` acknowledges this but the shipped config still uses it.

### A5.3 Secrets scan

| Check | Result |
|---|---|
| Committed `.env` | **None** (`git ls-files`) |
| Committed wallet files | **None** — `backend/wallet/*` ignored except `README.md`; wallet binaries exist **locally only** |
| `adb_password.rtf` | Exists on disk, **untracked** (`.gitignore` has `adb_password*`, `*.rtf`) |
| High-entropy key patterns in git history | **None found** (grep for private keys, `rnd_`, `sk-`, `AKIA`, `ghp_`) |
| Hardcoded credentials | **`seed_admin.py:24` — a default password is hardcoded (redacted)**, printed at :42; repeated in `DEPLOYMENT.md:16` and `README.md:90` |
| Docs exposure | `DEPLOYMENT.md` includes the ADB OCID, region, TNS alias and schema name — infrastructure identifiers, not credentials, but should be need-to-know |

**A5-03 — Default admin credential is hardcoded, printed, documented and still active in production.** Severity
**High**, Effort **S**. `seed_admin.py:24` hardcodes the password, prints it at `:42`, and `DEPLOYMENT.md:16`
repeats it. On 2026-10-19 the documented credential **authenticated successfully against the live backend as
`SuperAdmin`** (verified, credential not reproduced here). Either the password was never changed after seeding or
it was reset to the documented value. This should be rotated before any customer data exists. No committed secret
leak was found. [Fact]

### A5.4 Backup and recovery

| Component | Protection | Restore tested? |
|---|---|---|
| Oracle ADB | Platform-managed automatic backups | **No** — no restore rehearsal recorded (`PHASE2_STATUS.md:88`) |
| Object storage | **Not used in production** (`STORAGE_BACKEND=local`); local disk is ephemeral | N/A — data is lost |
| Configuration | In git + Render env | Partially |
| Audit log | In ADB | Only as good as the ADB restore |

**A5-05 — No restore rehearsal; ephemeral document storage.** Severity **High**, Effort **M** (storage) / **M** (restore rehearsal).

### A5.5 Free-tier spin-down

| Observation | Value |
|---|---|
| Backend `GET /health` (cold) | **HTTP 200 in 42.44 s** |
| Backend `/docs` (warm) | HTTP 200 in 0.14 s |
| Frontend `/` | HTTP 200 in 0.38 s |
| Impact | First user after idle waits ~40 s; Render may return 502/503 while waking [Assumption: platform behaviour] |
| Scheduled/background jobs | **None exist**, so nothing is missed while asleep — but also nothing can run (no cron/queue) |

### A5.6 Live URL verification (§13 of the document)

| Documented URL | Status | Time | Note |
|---|---|---|---|
| `https://karmathy-frontend.onrender.com/` | **200** | 0.38 s | Revamped homepage renders |
| `https://karmathy-frontend.onrender.com/login` | **200** | 0.38 s | |
| `https://karmathy-frontend.onrender.com/dashboard` | **200 (shell)** | — | Client-side redirect to `/login` for anonymous |
| `https://karmathy-backend.onrender.com/docs` | **200** | 0.14 s | |
| `https://karmathy-backend.onrender.com/health` | **200** | **42.44 s** | Cold start (a second cold request measured 45.58 s) |
| `https://karmathy-backend.onrender.com/health/db` | **401** | 0.13 s | Document says public; now requires auth |
| `https://karmathy-backend.onrender.com/health/storage` | **401** | 0.19 s | Document says public; now requires auth |
| `https://karmathy-backend.onrender.com/openapi.json` | **404** | 0.20 s | Correct location is `/api/v1/openapi.json` (**200**, 45.58 s cold) |

**A5-04 — §13 is stale for the diagnostics and omits the auth requirement.** Severity **Low**, Effort **S**.

---

## A6. Known limitations and claims

### A6.1 Section 11 limitations, verified

| # | Limitation in `DOCUMENT.md` | Accurate? | Evidence |
|---|---|---|---|
| 1 | Free-tier spin-down | **Yes** — 42 s cold start measured | live curl |
| 2 | Single schema (`ADMIN`) | **Yes** | `DEPLOYMENT.md:38` |
| 3 | Dynamic egress IPs; mTLS only | **Yes** (not independently probed) | config/driver setup |
| 4 | No wildcard subdomains; path fallback | **Yes** — and path fallback changes branding only | `TenantContext` |
| 5 | No real SSO | **Yes** — `SSOConfig` CRUD only; no SAML/OIDC flow | `integrations_platform.py:34-47` |
| 6 | No real SCIM | **Yes** — `scim_tokens` table; no provisioning endpoints | models; no `/scim` router |
| 7 | No real e-signature | **Yes** — status flag only; `sign` sets `Signed` with no document | `integrations_platform.py:175-186` |
| 8 | No real background checks | **Yes** — status tracking only | `:127-157` |
| 9 | Payroll tax simple percentage | **Yes** — and it is not statutory | `payroll_engine.py` |
| 10 | No mobile app | **Yes** | — |
| 11 | No email notifications | **Yes** — in-app `Notification` rows only | `ess_hr.py:89-94` |
| 12 | No real-time updates | **Yes** — polling | — |
| 13 | Duplicate of 5/6 | **Yes (redundant)** | — |

**A6-01 — The limitations list is honest, but some UI/marketing copy overstates.** Severity **Medium**, Effort **S**.
The homepage advertises "Security & compliance" and the product is described as multi-tenant by §4; neither is
true. The prior `ENTERPRISE_AUDIT.md:439-446` already flags "multi-tenant" and "SOC 2" language.

### A6.2 Section 6 "complete" features that are stubs

| Feature | Claimed | Actual |
|---|---|---|
| Compliance checks (Phase 14) | "Compliance rules/violations" | `run_compliance_checks` **marks every active rule passed** — simulation (`ess_hr.py:320-334`) |
| Report definitions / saved reports | "report definitions, saved reports" | CRUD rows; no execution engine |
| Headcount plans / scenarios | "headcount plans, scenarios" | CRUD rows; no planning calculations |
| SSO / SCIM / e-sign / background checks | listed under Phase 13 | configuration/status only (doc admits) |
| Migration runner | "Executes real imports" | Real CSV/row-by-row importer; Oracle/REST/SFTP "connectivity test" is a TCP/HTTP probe, not a schema-aware migration |
| Roster generation | "roster generation" | template replication, not coverage optimisation |
| Notifications | "notifications" | in-app rows; no delivery channel |
| ESS portal | "ESS profiles" | endpoints exist, but the **frontend has no ESS pages** (`ls src/pages` has no ESS) |
| Webhook retries | not claimed | none |

**A6-02 — Several "complete" modules are CRUD shells or simulations; ESS has no UI at all.** Severity **High**, Effort **L** (if the claim is to be made true).

---

## A7. Compliance and data protection (flag only — not legal advice)

### A7.1 Personal data stored

| Category | Where | Sensitivity |
|---|---|---|
| Employee identity | `employees` (name, email, phone, hire date, status, salary) | PII |
| Government IDs | **Not found** in models (no SSN/NIN/Aadhaar/PAN fields) | — |
| Bank / payout details | **Not found** in models (pay profile has salary, frequency, tax withholding; no bank account) | — |
| Pay data | `employee_pay_profiles`, `pay_slips` (gross/net/deductions, JSON lines) | High |
| Leave / health-adjacent | `leave_requests` (type, reason, dates) — could reveal health/family data | High |
| Termination records | `terminations` (reason, dates, final pay) | High |
| Documents | `employee_documents`, `onboarding_documents`, `employee_files`, offer-letter PDFs | High (may contain identity documents) |
| Performance / feedback | `performance_reviews`, `review_feedback`, `continuous_feedback` | High |
| Background checks | `background_checks` (candidate, result text) | High |
| Audit trail | `audit_logs` (actor, action, entity, details) | High |
| Auth | `users` (email, bcrypt hash, role) | High |
| Tenant config | `clients`, `client_settings`, `integrations` (encrypted secret) | Medium |

### A7.2 Data-subject controls

| Control | Present? | Evidence |
|---|---|---|
| Retention policy | **No** — rows live indefinitely | no retention field/policy |
| Deletion / erasure | **No** employee delete endpoint; terminations keep records | endpoints |
| Export (subject access) | Partial: `/import-export/export` for admin, 12 entities; no per-subject export | `import_export.py` |
| Consent capture | **No** | no consent model |
| Data processing agreement / records | **No** | not in repo |
| Encryption at rest | ADB platform encryption (assumed); documents on **local disk** | `render.yaml` |
| Encryption in transit | HTTPS + ADB mTLS | config |
| Access logging | Yes (audit) | `audit.py` |
| Breach/incident process | **No runbook** | — |
| Data residency | ADB in `ap-hyderabad-1`; app in Render `singapore` | `DEPLOYMENT.md:25,36` |

### A7.3 What GDPR / CCPA / local payroll would require (flag)

> **Owner input (2026-10-19):** the pilot must satisfy **all five** regimes — SOC 2, ISO 27001, GDPR, CCPA and
> India statutory payroll — across India, the US, UK/EU, the Middle East and Southeast Asia. Nothing below is
> currently evidenced. This is the binding constraint in `FEASIBILITY.md`.

- **Lawful basis, notices and consent** for employee data, and a DPA with each customer.
- **Subject access, correction, export and erasure** workflows (including data held in documents and audit logs).
- **Retention schedules** with defensible periods (payroll/tax records often must be kept — e.g. several years —
  which conflicts with erasure; a qualified professional must set the balance).
- **Processor/sub-processor register** (Render, Oracle Cloud, any future email/background-check provider).
- **International transfer mechanism** for data moving between Singapore/Hyderabad/EU.
- **Security programme** (access reviews, encryption, incident response, vendor risk) before any SOC 2/ISO claim.
- **Payroll**: statutory calculations, filing formats, retention and auditability are **jurisdiction-specific**;
  the current flat-percentage engine cannot satisfy any of them.

**A7-01 — No retention, erasure, consent or per-subject export; no DPA/incident runbook.** Severity **High**, Effort **L**.
**A7-02 — Data residency spans Singapore (app) and Hyderabad (ADB); no transfer assessment.** Severity **Medium**, Effort **M**.
**A7-03 — A qualified privacy lawyer and a payroll/tax professional must confirm the requirements per market.
This report does not provide legal advice.** [Flag only]

---

## Appendix A — Evidence index (key files/lines)

| Ref | Location |
|---|---|
| Router registration (25) | `backend/app/api/v1/api.py` |
| Auth dependencies / 401 semantics | `backend/app/api/deps.py:25-70` |
| JWT + bcrypt + Fernet | `backend/app/core/security.py` |
| Config defaults | `backend/app/core/config.py` |
| Visibility policy | `backend/app/core/visibility.py` |
| Visibility call sites | `employees.py:49,101`; `leave.py:76-80,135-144`; `offboarding.py:79-83` |
| Payroll engine | `backend/app/services/payroll_engine.py` |
| Payroll run / state machine | `backend/app/api/v1/endpoints/payroll.py:107-337` |
| Offer → hire transaction | `backend/app/api/v1/endpoints/offers.py:172-256` |
| ESS IDORs | `backend/app/api/v1/endpoints/ess_hr.py:43-125,302-307` |
| E-signature IDOR | `backend/app/api/v1/endpoints/integrations_platform.py:175-186` |
| Leave cancel IDOR | `backend/app/api/v1/endpoints/leave.py:214-226` |
| Webhook delivery | `backend/app/api/v1/endpoints/integrations_platform.py:73-124` |
| Storage | `backend/app/services/storage.py` |
| Tenant migration (unapplied) | `scripts/migration_sql/TENANT_SCOPING.sql` |
| Tenant negative test | `scripts/verify_tenant_isolation.py` |
| Auth context (no `/auth/me`) | `frontend/src/context/AuthContext.tsx` |
| ProtectedRoute (no role check) | `frontend/src/components/ProtectedRoute.tsx` |
| Tenant theme derivation | `frontend/src/context/TenantContext.tsx:137-196` |
| API client (no 401 handler) | `frontend/src/lib/api.ts` |
| Deploy config | `render.yaml`; `.github/workflows/deploy.yml` |
| Default credential | `backend/scripts/seed_admin.py:24` |
| Stale schema doc | `docs/DB_SCHEMA.sql` (22 tables) |

## Appendix B — Not verified (with reasons)

| Item | Reason |
|---|---|
| Full axe-core / keyboard-traversal / focus-trap audits | Lighthouse (axe-derived) was run, but keyboard traversal and focus traps were not tested |
| Responsive viewports 360/768/1024/1440 | No viewport-emulation tool used in this session |
| `scripts/live_e2e.py` | Requires live credentials and writes data; the audit stayed read-only |
| PostgreSQL/Redis/multi-replica behaviour | Not part of current deployment |
| Oracle-specific DDL execution | Would modify production; not authorised |
| `pydantic==2.7.4` / `sqlalchemy==2.0.29` on Python 3.11 | Host has only Python 3.15; suites ran on newer versions |
| Backup restore | No restore environment |
| Font rendering / real-device performance | Not measured |

## Appendix C — Assumptions (unverified)

| ID | Assumption |
|---|---|
| AS-1 | Render free web services return 502/503 while waking; only the cold-start latency (42 s) was measured |
| AS-2 | Oracle ADB has platform-managed automatic backups enabled; the console was not inspected |
| AS-3 | The live deployment may correspond to a commit at or after `91024a2`; the deployed SHA was not read from Render. Backend findings are unaffected because backend code is unchanged from `75c3cc5`. |
| AS-4 | ~~`base_salary` is intended as per-period because the engine says so.~~ **Confirmed by the owner on 2026-10-19: per pay period.** The offer-letter wording is the defect. |
| AS-5 | ~~The 42 unlabelled controls from `ENHANCEMENT_INVENTORY.md:132-136` still exist.~~ **Disproved on 2026-10-19: the top 5 authenticated pages have 0 unlabelled controls.** The note is stale. |
