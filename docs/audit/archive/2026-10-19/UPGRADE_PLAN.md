# Karmathy HCM — Upgrade Plan

**Companion to:** `AUDIT_REPORT.md` (finding IDs such as `A2-10` refer to that document)
**Owner context:** 1 engineer, 20–40 h/week, $0 budget, first pilot target 1–3 months, single-tenant-per-customer
deployment, per-pay-period salary, all five compliance regimes requested (SOC 2, ISO 27001, GDPR, CCPA, India
statutory payroll).

**Estimation convention.** 1 engineer-week (ew) = **30 productive hours**. Ranges are low/high, not optimistic.
Estimates include implementation, tests and review by the same engineer; they exclude incident response and
customer support.

---

## B1. Prioritized fix list

### Tier 1 — Must fix before any real customer uses this

| # | Finding | Fix | Why it blocks a customer | Effort |
|---|---|---|---|---|
| 1 | A2-11 | Add ownership checks to every self-service write: leave create/cancel, ESS profile/files/feedback/notification, e-signature | Any user can modify another employee's records today | M |
| 2 | A2-10 | Apply `visibility.py` to **all** employee-scoped reads (payroll, performance, benefits, time, scheduling, core-hr, ESS, onboarding, reports) | Payslips, reviews, benefits and timesheets are readable by every logged-in user | L |
| 3 | A2-12 / A6 | Enforce the **single-tenant-per-customer** model: separate deployment + database per customer; remove `clients` as an implicit security boundary; stop describing the app as multi-tenant | The current shared deployment leaks between "clients" | M (per-deployment) / XL (shared) |
| 4 | A5-02 | Set `STORAGE_BACKEND=oci` (or a paid persistent disk) and verify save/read/delete | Offer letters and onboarding documents vanish on every redeploy | S |
| 5 | A5-03 | Remove the hardcoded seed password; require an env-supplied password on first run; rotate the live admin password | The documented default currently authenticates to production | S |
| 6 | A2-16 | Make `base_salary` unit explicit (per period) in schema/UI/offer letter; correct the "annual compensation" wording | Wrong wording can create a contractual pay dispute | S |
| 7 | A2-15 | Feed approved leave, overtime and benefit deductions into payroll (or explicitly disable those inputs) | Payroll pays the wrong amount as soon as those modules are used | L |
| 8 | A2-04 | Make offer→hire atomic (single transaction or compensating rollback) | Partial hires create duplicate employees and broken onboarding | M |
| 9 | A2-02 | Introduce Alembic, baseline the current schema, and make every change a migration | `create_all()` cannot evolve a live Oracle schema; the failure mode is a 503 | M |
| 10 | A4-01 | Add a CI gate: pytest (all suites), `tsc --noEmit`, build, `pip-audit`, `npm audit`, secret scan | Nothing prevents regressions from reaching production | S |
| 11 | A4-04/A4-05 | Upgrade Starlette/FastAPI, python-multipart, python-jose, ecdsa, python-dotenv; plan React Router 7 | Known advisories in auth and upload paths | M |
| 12 | A2-07 | Implement real `Manager` and `PayrollViewer` role guards (at minimum Manager leave/timesheet/swap approval) | The documented role model does not exist server-side | M |

### Tier 2 — Should fix in the next 1–2 months

| # | Finding | Fix | Effort |
|---|---|---|---|
| 13 | A3-03/A3-06 | Persist the user (or add `/auth/me`), handle 401/403 globally, add refresh or silent re-auth | M |
| 14 | A3-05 | Role-aware routing and navigation (hide modules a role cannot use) | M |
| 15 | A2-03 | Add indexes on `employee_id`, `status`, `work_date`, `pay_run_id`, `tenant`-equivalent keys | M |
| 16 | A2-05 | Add pagination/filtering to all list endpoints | M |
| 17 | A2-19/A2-20 | Background queue for payroll, PDF and webhooks; retry with backoff and a dead-letter view | L |
| 18 | A2-14 | Error tracking (Sentry free tier) + infrastructure metrics + alerting | M |
| 19 | A2-13 | Tamper-evident audit (hash chain) and single-transaction audit writes | M |
| 20 | A2-17 | Holiday calendar, anniversary tenure, weekly overtime rules (configurable per region) | M |
| 21 | A2-18 | Either build a real compliance rule engine or label the module "simulation" | L |
| 22 | A3-01/A3-02 | Adopt TanStack Query; split 5 largest pages; remove `window.prompt` | L |
| 23 | A3-12 | Fix brand-token contrast (`#06B6D4`, `#10B981`, `#D97706`, `#8B5CF6`) and breadcrumb separators | S |
| 24 | A3-16 | Route-level code splitting; self-host or drop Inter | M |
| 25 | A3-19 | Remove 8 unused dependencies; remove or gate `/design` | S |
| 26 | A5-05 | Restore rehearsal for ADB; documented RPO/RTO | M |
| 27 | A7-01 | Retention schedule, export, erasure workflow, consent records, DPA template | L |
| 28 | A1-01/A1-02 | Regenerate `API_CONTRACT.md` and `DB_SCHEMA.sql` from code/OpenAPI | M |

### Tier 3 — Improve over time

| # | Finding | Fix | Effort |
|---|---|---|---|
| 29 | A2-01 | Move remaining business logic from routers into services | L |
| 30 | A2-06 | Batch directory/org-chart rebuilds | S |
| 31 | A2-08 | Rate-limit/cache the public tenant resolver; minimise returned fields | S |
| 32 | A3-10/A3-11 | Validate tenant logos; keep operator warnings out of end-user banners | S |
| 33 | A3-14 | Skip link on public pages | S |
| 34 | A6-02 | Replace CRUD-shell modules (scenarios, report definitions, saved reports) with real execution or remove them from marketing | L |
| 35 | A3-17 | Deliver Inter (self-hosted) | S |
| 36 | A2-09 | Pin the JWT algorithm to HS256 and reject others explicitly | S |

---

## B2. Frontend revamp plan

### B2.0 Stack changes (applies across phases)

| Change | What it means | Effort | Notes |
|---|---|---|---|
| **Vite SPA (keep) + Astro marketing** | Keep React/Vite for the authenticated app; move the 10 public pages to Astro for static HTML/SEO | 2–4 ew | Astro can be deployed independently on the same static host |
| **pnpm workspaces + Turborepo** | `apps/web`, `apps/marketing`, `packages/ui`, `packages/api-client`, `packages/tokens`; cached `build`/`lint`/`test` | 0.5–1 ew | Needed before parallel packages; low risk |
| **Generated OpenAPI client** | Generate types + client from `/api/v1/openapi.json` (e.g. `openapi-typescript` + `openapi-fetch`) | 1–1.5 ew | Replaces the 323-line hand-written `types/index.ts`; must be regenerated in CI |
| **Storybook** | Component catalogue for `packages/ui` | 0.5–1 ew | Can start with the 16 existing primitives |
| **Style Dictionary + Tailwind v4** | One token source → CSS variables, Tailwind theme, docs | 1–1.5 ew | Tailwind v4 is CSS-first; pair with the existing token layer |

> **Costing note:** Astro is costed inside **phase 5** (public pages), not again in the stack row. The remaining
> tooling subtotal is **3–5 ew**; the complete stack element (tooling + Astro) is **5–9 ew**.

### B2.1 Phases

> Phases 2–3 and 5–6 can overlap; 4 depends on backend aggregation endpoints; 7 depends on 2; 8 is continuous.

| Phase | Scope | Effort (low–high, ew) | Depends on | Key risks / slip causes | Parallel with backend? |
|---|---|---|---|---|---|
| **1. Audit & IA** | Content inventory, route map, role/task matrix, click-depth targets, usability tests with 3–5 users | **0.5–1** | — | No users available to test (solo, no budget) | Yes |
| **2. Design system** | Tokens + Style Dictionary, Tailwind v4, primitives, Storybook, `docs/DESIGN_SYSTEM.md`, contrast-safe tokens | **2–3** | 1 | Token migration churn; Tailwind v4 breaking changes; no designer to arbitrate | Yes |
| **3. App shell** | Workspace rail, secondary sidebar, top bar, command palette (⌘K), keyboard shortcuts, mobile bottom bar/drawer, breadcrumbs, skip link | **2–3** | 2 | Command-palette search needs a route registry; scope creep into "launcher" | Yes |
| **4. Role-based homes** | Associate (clock/leave/payslips), Manager (approvals inbox), HR (action inbox), PayrollViewer (pay-run status), SuperAdmin (tenant health) | **3–5** | 3 + backend aggregation | Requires new aggregate endpoints; Manager role itself is not implemented (A2-07) | **No** — needs backend |
| **5. Public pages** | Astro migration of Homepage, Solutions, Industries, Resources, About, Careers, Contact, Privacy, Terms, Docs; SEO/sitemap/robots | **2–4** | 2 (tokens) | Astro build/deploy pipeline; content is thin for some pages | Yes |
| **6. Module pages** | Split `/platform` into People, Payroll, Performance, Benefits, Learning, Admin; rebuild Recruiting (600 LOC), ClientOnboarding (515), Offboarding (351), Leave (346), Scheduling (320), Time (303), Onboarding (295), Reports (300) | **8–12** | 2, 3, 4 + generated client | Largest phase; each module has unique flows; no designer; backend gaps (ESS has no UI) | Partly — can start reads-only |
| **7. Tenant customization** | Branding (validated), terminology, feature flags per module, logo safety, theme preview | **1.5–2.5** | 2, 3 | Single-tenant-per-customer reduces the need; avoid over-building | Yes |
| **8. Quality pass** | axe-core in CI, keyboard/focus audit, 360/768/1024/1440 regression, Lighthouse budgets, visual regression, E2E (Playwright) | **2–3** | 2–7 | Often under-estimated; needs a stable UI first | Yes |
| **Stack (B2.0)** | pnpm/Turbo, OpenAPI client, Storybook, Style Dictionary | **3–5** | 1 | Tooling rabbit holes | Yes |
| **Total** | | **24–38.5 ew** | | | |

### B2.2 Minimum viable revamp for the pilot (recommended)

Do **not** attempt the full revamp before the pilot. A pilot slice that removes the worst UX debt:

1. Phase 2 tokens + contrast fixes — **1 ew**
2. Phase 3 shell (command palette deferred) — **1.5 ew**
3. Phase 4 Associate + Manager homes only — **2 ew** (needs backend aggregates)
4. Phase 6: split `/platform` and rebuild **Leave, Time, Recruiting** only — **3 ew**
5. Phase 8: axe + responsive pass — **1 ew**

**Pilot slice ≈ 8.5 ew** (~2 months at 30 h/week). The remaining **15.5–30 ew** can follow after the pilot.
The slice fits inside a 1–3 month window **by itself**, but combined with the 7.6-ew security foundation it is
~16.1 ew (**3.7 months at 30 h/week**). For a 1–3 month pilot, ship the foundation on the existing UI and defer
this slice; for a customer-facing relaunch, plan ~4 months at 30 h/week.

### B2.3 Phase risks that would cause a slip

- **No designer** (confirmed): every visual decision is made by the engineer; budget 20–30% contingency.
- **Backend gaps**: role-based homes and module pages surface endpoints that do not exist (ESS, approvals aggregates).
- **Tailwind v4 + Style Dictionary** is a migration, not a greenfield add; plan a branch and a visual diff.
- **Generated client** will expose backend inconsistencies (hand-written types already drift); expect type errors to fix.

---

## B3. Backend upgrade plan

| Workstream | Scope | Effort (ew) | Finding refs |
|---|---|---|---|
| **Alembic + schema baseline** | Add `alembic.ini`, `migrations/`, autogenerate baseline from models, first migration for missing columns/indexes; remove `create_all()` from production startup; document expand/contract | **1.5–2.5** | A2-02 |
| **Tenant model hardening (single-tenant)** | One deployment + database per customer; remove `clients` as a security boundary; make `/by-slug` return branding only; add a per-deployment config; delete or clearly label the multi-tenant onboarding path; update marketing | **1–2** | A2-12, A2-08, A6-01 |
| **Tenant scoping (only if shared)** | Apply `TENANT_SCOPING.sql`, backfill, add `tenant_id` filters and tests | **4–6** | A2-12 |
| **RBAC consistency** | Role helpers (`require_roles`), Manager approvals, PayrollViewer read-only, ownership checks on 7 IDOR writes, visibility on 73 reads | **3–5** | A2-07, A2-10, A2-11 |
| **Payroll correctness** | Connect time/leave/benefits; explicit per-period unit; offer-letter wording; reconciliation report; tests for each input | **2–4** | A2-15, A2-16 |
| **Transactional integrity** | Single transaction for offer→hire; audit in the same transaction; idempotency for hire | **1–2** | A2-04, A2-13 |
| **Background jobs** | Durable queue (start with a DB-backed worker if $0; Redis/BullMQ or RQ when budget allows); payroll, PDF, webhook retries + dead-letter | **2–3** | A2-19, A2-20 |
| **Observability** | Sentry (free tier), request/latency metrics, DB pool metrics, alert thresholds, uptime check | **1–2** | A2-14 |
| **Security hardening** | Pin HS256, enforce secret strength, remove seed password, dependency upgrades, optional shared rate-limit store | **1–2** | A2-09, A4-04, A5-03 |
| **Indexes & pagination** | FK/filter indexes, cursor or limit/offset on every list, query budgets | **1–2** | A2-03, A2-05 |
| **Test gaps** | Restructure suites under `pytest`, CI gate, frontend unit tests, Playwright E2E, axe, load smoke | **2–3** | A4-01, A4-02 |
| **Compliance foundations** | Retention/export/erasure, audit hash chain, DPA templates, data map | **3–5** | A7-01, A2-13 |
| **Total (single-tenant model)** | Excludes the optional shared-mode row | **18.5–32.5 ew** | |
| *With shared-mode tenant scoping (not chosen)* | *Adds 4–6 ew* | *22.5–38.5 ew* | |

**Sequence (risk-first):** ownership checks → visibility → storage → default credential → Alembic →
offer-hire transaction → payroll inputs → CI gate → RBAC → background jobs → observability → compliance.

---

## B4. Migration and rollout strategy

### B4.1 Principles

- **Expand/contract everywhere.** Every schema change is additive first; code reads old and new; a later release
  removes the old shape.
- **One pilot deployment first.** Because the chosen model is single-tenant-per-customer, the pilot gets its own
  Render service + Oracle schema. The existing shared demo remains read-only.
- **Feature flags at two levels.** `feature_flags` rows (already modelled) for tenant-visible modules; build-time
  flags (`VITE_*`) for whole revamp surfaces.
- **No big-bang cutover.** Old routes stay alive until the new route has been exercised by the pilot.

### B4.2 Shipping the revamp without downtime

| Step | Action | Rollback |
|---|---|---|
| 1 | Add `packages/ui` + tokens alongside the existing `components/ui`; keep both compiled | Revert the package import; old components untouched |
| 2 | Add new routes under the existing paths but behind `VITE_NEW_SHELL`; keep current pages as fallback | Flip the env flag; redeploy previous static build |
| 3 | Run old and new shells side-by-side for the pilot account (`/dashboard?shell=v2`) | Remove the query param → old shell |
| 4 | Migrate public pages to Astro at a separate host/path (`/` via Astro, app at `/app` or subdomain) | Point the CDN/route back to the SPA |
| 5 | Switch module by module (Leave → Time → Recruiting → …); each has its own flag | Per-module flag rollback |
| 6 | Remove legacy components only after two clean weeks of pilot use | Git revert of the removal commit |

**Static-site rollback:** Render keeps previous deploys; a rollback is a redeploy of the prior commit. Because the
revamp is frontend-only for long stretches, this is low-risk.

### B4.3 Data migration needs

| Change | Data migration |
|---|---|
| Alembic baseline | None — stamp the existing schema, then generate the first real migration |
| `base_salary` unit clarification | **No numeric change** (owner confirmed per-period); add a unit/comment and fix the offer-letter text. If a future switch to annual is wanted, a separate migration + comms plan is required |
| Indexes | Online `CREATE INDEX` (Oracle) in a low-traffic window; no data rewrite |
| Audit hash chain | Backfill hashes in batches, or start the chain from a cut-over timestamp |
| Storage move (local → OCI) | One-off copy of existing `/tmp/karmathy-storage` objects; dual-read during the transition |
| Tenant separation (single-tenant) | Provision a fresh schema per customer; import via the existing CSV importer or a scripted dump; no shared-DB `tenant_id` backfill needed |
| Tenant scoping (only if shared later) | `TENANT_SCOPING.sql` → backfill per table → verify → enforce NOT NULL + composite uniques |

### B4.4 Rollback per major change

| Change | Rollback |
|---|---|
| Dependency upgrades | Pin back; keep a lockfile diff; deploy previous image |
| RBAC/ownership checks | Feature flag `ENFORCE_OBJECT_SCOPE`; disabling restores old behaviour (but leaves the hole — use only for minutes) |
| Background jobs | Keep synchronous path behind a flag until the queue is proven |
| Astro marketing | DNS/route switch back to the SPA static site |
| Storage backend | Keep `STORAGE_BACKEND` switchable; dual-write during migration |
| Alembic migration | Every migration has a tested `downgrade()`; destructive changes are split into a later release |

### B4.5 Pilot rollout checklist

1. Provision a dedicated backend + Oracle schema for the pilot customer.
2. Rotate the admin password; create named accounts (no shared admin).
3. Apply Alembic baseline; run all 11 suites + tenant/visibility negative tests.
4. Enable only the modules the pilot bought (feature flags).
5. Run a paid parallel payroll in **dry-run** against a known payroll and reconcile by hand.
6. Run the a11y/responsive/perf pass on the pilot's actual devices.
7. Agree an incident contact and a rollback window before go-live.
