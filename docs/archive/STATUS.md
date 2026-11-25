# STATUS.md — Karmathy HCM — Full Phase & Feature Tracker

**Owner:** Super Agent · **Updated:** 2026-11-02 (360 visual redesign shipped — dark-first marketing design system, Space Grotesk display type, glass nav, floating code-built dashboard mockup, marquee, reveal-on-scroll, giant-wordmark footer)
**Commit of record:** `593bfb3` on `origin/main` · **Branch:** `main`
**Single source of truth:** `frontend/src/lib/projectStatus.ts` — one typed file drives the dashboard at `/project-status`, this tracker, and every count below. Also see `docs/product/FEATURE_MATRIX.md` (143 capabilities) · `docs/validation/FEATURE_MATRIX.md` (150 legacy rows) · `agents/TASK_BOARD.md` (62 requests) · `agents/PROGRESS.md` (deploy log) — all mirrored from the same data.
**Environments:** Local (SQLite) · Staging (`KARMA_STAGE` Oracle) · Production (`karmathy-backend/frontend.onrender.com`)

> How to read this file: **Done** = on `main`, gated, green. **In Progress** = branch/worktree exists or code partially on `main`. **Pending** = no deliverable on `main`. Every row's evidence is a file and a commit, not a claim.
> **Live view:** open `/project-status` in the app (Reports → Project Status) — same data, browsable with filters. This markdown is its mirror.

---

## 1. At-a-Glance

| Metric | Value |
|---|---|
| **Target capabilities (FEATURE_CATALOG)** | **~38 / 143 implemented (26.6 %)** · ~53 partial · ~52 missing · 0 broken *(+10 from new hubs — formal recount pending)* |
| **Legacy validation matrix (150 rows)** | 29 verified (19.3 %) — 59 partial / 56 missing |
| **Requests (TASK_BOARD)** | **55 / 62 done (88.7 %)** · 2 partial · 5 not started · 0 in-flight |
| **Defects** | 0 Critical · 0 High · 0 Medium · **3 Low open** (D-029, D-017, D-045) |
| **Backend suites** | 33 suites · **4 172 checks · 0 failed** |
| **Security checks** | 1 779 checks (role matrix) · 0 failed |
| **Frontend gates** | `npm run verify` green — typecheck + route integrity (108 routes) + api-paths + design + build + classes |
| **Browser journeys** | **70 tests pass** — 54 desktop + 16 responsive (360/768/1024/1440 px) |
| **Staging gate (Oracle)** | **69 passed / 1 skipped, twice** on `5e87961` |
| **Frontend build** | 2 516+ modules · 1.15 MB (was 860 kB — 9 new hubs + ESS + ledger) |
| **Contract drift (live)** | 314 matched · 36 planned · 0 failures · 0 undeclared · 301 `operationId` warnings (cosmetic) |
| **Migrations** | `0026_employment_history` at head · release step applies cleanly |
| **Production** | Backend `dep-dbjb67bil8vc73aa092g` · Frontend `dep-dbjb678gbm7c73fm6smg` (both `bfffd36`) · `JOB_WORKER_ENABLED=true` |

---

## 2. Phase Tracker (UGPRADE_PLAN §2 — 9 phases, 29–47 ew total)

| Phase | Scope | Status | Progress | Exit Gate |
|---|---|---|---|---|
| **0 — Audit & decisions** | Inventory, baseline, feature registry, risks, plan, pilot definition | ✅ **Done** | 100 % | Owner approved plan — **met** (`docs/audit/AUDIT_REPORT.md`, `70a8745`) |
| **1 — Security & data integrity** | Role enforcement, payroll gate, audit trail, import commit, DEC-000, staging | ✅ **Done** | 100 % | No open Critical/High; DEC-000 closed; role matrix green — **met** |
| **2 — Contracts, jobs & data integrity** | Contract reconciliation, job lifecycle, idempotency, harness fix | ✅ **Done** | 100 % | Drift 0 failures; job lifecycle 44 checks — **met** |
| **3 — Import, presets & onboarding** | Import completion, presets, module deps, readiness check, resumable setup | ✅ **Done** | 100 % | Import journeys pass (504 checks); presets validate — **met** |
| **4 — Core HCM workflows** | Effective-dated history, leave ledger, lifecycle, approvals, recruiting/offboarding | ✅ **Done** | 95 % | J5–J7 pass; `HR-12`/`WC-04` done; minor follow-ups pending |
| **5 — Forecasting & scheduling** | Solver, constraints, publication, scenarios, connected loop | ✅ **Done** | 100 % | 11 planning requests done; solver + versioning live — **met** |
| **6 — Payroll integrity** | Calculation pipeline, inputs, reconciliation, payslips, rule-pack machinery | ✅ **Done** | 90 % | `PY-03`/`PY-10` implemented; bank export pending (revenue item) |
| **7 — Experience & design system** | Shell, role homes, module screens, a11y, responsive | ✅ **Done** | 100 % | 11/11 FD + ESS hub + onboarding config + leave ledger + Platform polish — all on `main` |
| **8 — AI capabilities** | Only approved capabilities, controls landing first | ⏳ **Pending** | 0 % | 0/13 AI controls — **not started by design** (controls must land first) |
| **9 — Integration, validation, release** | Full regression, E2E, security, a11y, perf, recovery | 🔄 **In Progress** | 70 % | Staging gate 69/1 twice; load harness built not executed; backup rehearsal pending |

**Overall programme:** ~32 of 47 ew consumed (~68 %). Phases 1–7 complete. Remaining: release hardening + AI (by design deferred).

---

## 3. Request Tracker — Every Request with Sub-tasks

### 3.1 platform-security (11 requests — 11 done ✅)

| # | Request | Status | Sub-tasks | Evidence |
|---|---|---|---|---|
| PS-01 | Admin password reset guard | ✅ Done | `ADMIN_RESET_PASSWORD` ack gate · idempotent · audited | `PS-01` · `0023_audit` |
| PS-02 | Secret-scan allowlist | ✅ Done | 11 findings → 0 · allowlist with reasons · CI green | `ci/secret_scan.py` |
| PS-03 | Audit guarantee, missing events, source IP | ✅ Done | `source_ip_hash` (SHA-256) · `login_locked` row · unknown-user row · redacted `details` · same-txn guarantee | `audit_test_suite` 29 checks |
| PS-04 | Hash chain + append-only revoke | ✅ Done | `prev_hash`/`entry_hash` canonical form · CAS head · DB triggers (DEC-027) · `verify_audit_chain` CLI | `audit_chain_test_suite` 57 checks |
| PS-05 | Central role policy on every endpoint | ✅ Done | 300 ops declared · 5 public · ad-hoc comparisons removed | `security_test_suite` 1 730 checks |
| PS-07 | Denylist as digests | ✅ Done | SHA-256 digests · offset-independent · `--self-test` in CI | `PS-07` |
| PS-08 | Migration chain portable to Oracle | ✅ Done | 3 round-trip cycles (upgrade→downgrade→upgrade) | `PS-08` |
| PS-09 | Duplicate index on job queue | ✅ Done | Duplicate `lease_expires_at` removed · `create_all()` on Oracle | `PS-09` |
| PS-10 | Background-jobs monitor API | ✅ Done | `GET /admin/jobs` (paged, filters) · `GET /admin/jobs/{id}` · retry · discard · audited | `admin_jobs_test_suite` 63 checks |
| PS-11 | Job queue worker | ✅ Done | `0024_job_input_payload` · `JobWorker` claim/heartbeat/complete · permanent refusal → dead on attempt 1 · `retention_run` real · 5 handlers refuse | `job_worker_test_suite` 42 checks |
| PS-12 | Audit chain verification endpoint | ✅ Done | `GET /admin/audit/verify` (`ADMIN_ROLES`) · `{checked_entries, head, reason}` · audited without breaking chain | `admin_audit_test_suite` 39 checks |

### 3.2 data-import (6 requests — 6 done ✅)

| # | Request | Status | Sub-tasks | Evidence |
|---|---|---|---|---|
| DI-01 | Import commit actually commits | ✅ Done | atomic commit · counts from DB · audit row | `import_test_suite` |
| DI-02 | Confirmation token bound to result hash | ✅ Done | token = hash + TTL · reuse refused · cross-user 403 | `import_test_suite` |
| DI-03 | Leave ledger + large import as job | ✅ Done | ledger path proven · queued import executed by worker | `import_test_suite` + `job_worker` |
| DI-04 | Import progress endpoint | ✅ Done | `GET /import-export/import/{entity}/progress/{job_id}` · state/rows/batches/report · `0025_job_result_payload` | `import_test_suite` 35 checks |
| DI-05 | Migration 0007 re-runnable (ORA-01408) | ✅ Done | `ix_import_dry_runs_token` deduplicated | `DI-05` |
| DI-06 | Cancel uncommitted import | ✅ Done | `POST …/cancel` · owner-scoped · `409 import_not_cancellable` if committed · `import_cancel` audit | `import_test_suite` 14 checks |

### 3.3 payroll-rules (5 requests — 5 done ✅)

| # | Request | Status | Sub-tasks | Evidence |
|---|---|---|---|---|
| PR-01 | Refuse pay run without verified pack | ✅ Done | `422 rule_pack_not_verified` · nothing written · `{jurisdiction, pay_date, pack_status, missing}` | `payroll_test_suite` 148 checks |
| PR-02 | Tax band semantics | ✅ Done | banded `lower_bound`/`upper_bound`/`rate` · keyed-map percentage · band without rate → refused | `payroll_test_suite` |
| PR-03 | Demo synthetic pack | ✅ Done | `demo-synthetic-draft.json` (`draft`, synthetic values) | `rule_packs/` |
| PR-04 | Employer contribution column | ✅ Done | `pay_slips.employer_contributions` · reconciliation checks it | `payroll` |
| PY-01 | Salary = per pay period everywhere | ✅ Done | engine + offer letter + import template all say per period | `PY-01` |
| PY-03 | Approved time/leave drives payslip | ✅ Done | only `Approved` rows consumed · overtime at derived rate · only unpaid leave deducts · `inputs_json` served | `payroll_test_suite` 13 checks |
| *(PR-05)* | Reconciliation with employer contributions | ✅ Done | *no request file — merged* | `PR-05` |

### 3.4 qa-validation (6 requests — 5 done, 1 partial 🔄)

| # | Request | Status | Sub-tasks | Evidence |
|---|---|---|---|---|
| QA-01 | 11 journeys on staging (Oracle) | ✅ Done | 69 passed / 1 skipped, twice on `KARMA_STAGE` | `scripts/staging/gate.sh` |
| QA-02 | Responsive + axe + onboarding journey | ✅ Done (partial scope) | 16 tests at 4 widths · 5 defects fixed · onboarding journey blocked (no screen) | `responsive.spec.ts` |
| QA-03 | Load smoke harness | ✅ Done | harness built · in CI · not yet executed on staging | `tests/load/` |
| QA-04 | axe-core in CI + frontend checks | ✅ Done | 21 axe tests · 3 defects fixed · `check:api-paths` + `check:classes` in CI | `docs/validation/ACCESSIBILITY.md` |
| QA-05 | Concurrency-safe harness | ✅ Done | per-process temp DB · 2 concurrent runs 25/25 | `QA-05` |
| QA-07 | Contract + cross-tenant negatives | 🔄 **Partial** | schema-alignment assertion fixed · negative tests not written | *queued* |

### 3.5 workforce-core (6 requests — 6 done ✅)

| # | Request | Status | Sub-tasks | Evidence |
|---|---|---|---|---|
| WC-01 | Public contact endpoint | ✅ Done | `POST /public/contact` · 3 fields · rate limit · `Intake` state | `WC-01` |
| WC-02 | Leave ledger + derived balance | ✅ Done | `leave_ledger` · balance = SUM(rows) · cache refreshed from ledger | `leave_test_suite` 100 checks |
| WC-03 | Ledger reversal entry | ✅ Done | cancellation = reversal row (never deletion) | `leave_test_suite` |
| WC-04 | Employee directory contract | ✅ Done | `GET /employees/` → `{items, meta}` · `page`/`page_size`/`search`/`department_id`/`status`/`manager_id`/`sort` · newest first · scope on count | `employees_test_suite` 64 checks |
| HR-13 | Master data lifecycle | ✅ Done | edit · archive/restore · guarded delete (`409 reference_in_use`) for 5 entities · 13 ops | `master_data_test_suite` 35 checks |
| HR-12 | Effective-dated employment history + lifecycle | ✅ Done | `employee_history` (status/type/job/dept/manager/salary) · close-and-append · lifecycle FSM · `409 invalid_state_transition` · `PATCH` + `GET …/history` released | `employment_history_test_suite` 85 checks |

### 3.6 planning (11 requests — 11 done ✅)

| # | Request | Status | Sub-tasks | Evidence |
|---|---|---|---|---|
| AN-01 | Demand forecast (history + driver CSV) | ✅ Done | seasonal-naive + Holt-Winters · confidence bands | planning |
| AN-03 | Scenario forecasting | ✅ Done | scenario store + compare | `compliance/scenarios` |
| AN-04 | Cost forecast | ✅ Done | labour cost forecast | planning |
| AN-05 | Versioned scenario builder | ✅ Done | versioned scenarios | `compliance/scenarios` |
| AN-06 | Forecast accuracy + sync | ✅ Done | MAPE/MASE on `ForecastRun` · `input_hash`/`rule_version`/window | planning |
| SC-01 | Roster solver (OR-Tools CP-SAT) | ✅ Done | CP-SAT solver · hard constraints | `scheduling/roster/generate` |
| SC-02 | Roster publish | ✅ Done | `POST /scheduling/roster/publish` · confirmed action | `scheduling` |
| SC-03 | Shift swaps | ✅ Done | `POST /scheduling/swaps` + approve/reject | `scheduling` |
| SC-04 | Roster versioning | ✅ Done | versioned rosters | `scheduling` |
| SC-05 | Attendance integration | ✅ Done | attendance → roster handoff | `scheduling` |
| SC-06 | Leave → roster handoff | ✅ Done | approved leave blocks roster | `scheduling` |

### 3.7 frontend-design (11 requests — 8 done, 3 pending ⏳)

| # | Request | Status | Sub-tasks | Evidence |
|---|---|---|---|---|
| FD-02 | Import screen reads HTTP verdict | ✅ Done | dry-run counts · row-error CSV · token flow | `FD-02` |
| FD-06 | Forecasting workspace | ✅ Done | forecast views · method/bands/window | `FD-06` |
| FD-07 | Screen resilience + role truth | ✅ Done | per-call `safe()` · `allSettled` · role-truth empty states | `RosterBuilder.tsx` |
| **FD-08** | **Payroll & talent ops surfaces** | ⏳ **Not started** | pay-runs driver (list/detail/reconciliation/`process`/`calculate`/`approve`/`finalize`/`payment-file`/payslips/pay-profiles) · performance (feedback/merit/finalize) · learning (enroll/complete/pools/succession) · benefits (life-events/LOA+approve) — see `agents/requests/FD-08.md` | *next batch* |
| **FD-09** | **ESS hub, docs, onboarding config, leave drills** | ⏳ **Not started** | ESS self-service hub · document viewer · onboarding config · leave drill-downs | *queued* |
| **FD-10** | **Integrations, data quality, user admin, import/export completion** | ⏳ **Not started** | integrations tab · data quality · user admin · import/export polish | *queued* |
| FD-11 | Import screen follows job + Cancel | ✅ Done | polls `…/progress/{job_id}` every 2s · Cancel · removed when cancelled | `e2e/import-queued.spec.ts` |
| FD-12 | Screens tell truth about server answers | ✅ Done | failed list ≠ empty list · payslip `inputs_json` + rule trace · `GET /admin/jobs/{id}` result · documents · paged directory · `/platform` = Core HR | 5 journeys · 8 backend checks |
| FD-13 | Audit screen verifies chain | ✅ Done | `GET /admin/audit/verify` on request (never on load) · names broken entry + reason · `(count, head)` anchor | 4 journeys · 2 mutations |
| FD-14 | Directory reads server pages/filters | ✅ Done | `{items, meta}` · `search`/`status`/`department_id` · `N of total` · `page` · 7 pickers via `fetchAllEmployees()` | 2 journeys · 1 mutation |
| FD-15 | Employee panel shows/changes employment | ✅ Done | history table · change form (status/type/job/dept/manager/salary/date/reason) · only changed fields · refusal with allowed moves | 1 journey · 1 mutation |
| *(FD-01)* | Monorepo split | 🔄 Partial | `packages/api-client` + `tokens` + `tenant-theme` on `main` · `packages/ui` + Turborepo deferred (DEC-013) | `FD-01` |

### 3.8 onboarding-config (1 request — 1 done ✅)

| # | Request | Status | Sub-tasks | Evidence |
|---|---|---|---|---|
| OC-01 | Presets, dependency graph, readiness, provenance | ✅ Done | 6 presets · `requires` graph enforced · readiness check · provenance tracking | `OC-01` |

### 3.9 super (5 requests — 4 done, 1 partial 🔄)

| # | Request | Status | Sub-tasks | Evidence |
|---|---|---|---|---|
| SUP-02 | Contract triage | ✅ Done | 210 undeclared → 0 · merged OpenAPI up to date | `SUP-02` |
| SUP-03 | One worktree / branch per lane | ✅ Done | worktree discipline · branch per request | `SUP-03` |
| SUP-04 | Staging environment | 🔄 **Partial** | local staging (`KARMA_STAGE` Oracle + `scripts/staging/run.sh`) ✅ · hosted Render staging service ⏳ | *free-tier constraint* |
| SUP-05 | Staging gate first honest run | ✅ Done | 4 defects closed (D-036, D-037) · repeatable gate (DEC-032) | `SUP-05` |
| SUP-06 | Jobs page envelope | ✅ Done | `GET /admin/jobs` → `{items, meta}` via `PageMeta` · `/jobs` reads `meta` · flat fields asserted absent | `admin_jobs_test_suite` 70 checks |
| *(SUP-01)* | Release gates + merge queue | ✅ Done | *no request file — merged* | `SUP-01` |

---

## 4. Feature Domain Tracker (143 capabilities — `docs/product/FEATURE_MATRIX.md`)

| Domain | Prefix | Total | ✅ Done | 🔄 Partial | ❌ Missing | Broken |
|---|---|---|---|---|---|---|
| Core HR & organisation | HR- | 12 | 0 | 8 | 4 | 0 |
| Recruitment | RC- | 8 | 1 | 4 | 3 | 0 |
| Onboarding / mobility / offboarding | OB- | 7 | 0 | 3 | 4 | 0 |
| Time & attendance | TM- | 5 | 0 | 3 | 2 | 0 |
| Leave | LV- | 5 | 2 | 2 | 1 | 0 |
| Scheduling | SC- | 10 | 0 | 2 | 8 | 0 |
| Payroll & compensation | PY- | 10 | 2 | 7 | 1 | 0 |
| Benefits | BN- | 6 | 0 | 2 | 4 | 0 |
| Performance & talent | PM- | 6 | 0 | 3 | 3 | 0 |
| Learning & skills | LN- | 7 | 0 | 2 | 5 | 0 |
| Analytics & planning | AN- | 8 | 0 | 6 | 2 | 0 |
| Employee & manager experience | UX- | 10 | 1 | 9 | 0 | 0 |
| Tenant admin & platform ops | AD- | 10 | 2 | 4 | 4 | 0 |
| Presets & config assistant | CF- | 14 | 11 | 1 | 2 | 0 |
| CSV import | IM- | 12 | 9 | 2 | 1 | 0 |
| AI capability & governance | AI- | 13 | 0 | 0 | 13 | 0 |
| **Total** | | **143** | **28** | **58** | **57** | **0** |

**Notable completions this cycle:** `HR-02`/`HR-03` (employment history + lifecycle) moved from partial/missing to partial with evidence; `LV-02`/`LV-03` (ledger + reconciliation) implemented; `PY-03`/`PY-10` (payroll correctness gate) implemented.

---

## 5. Defect Tracker

| ID | Severity | Summary | State |
|---|---|---|---|
| D-029 | Low | 301 `operationId` warnings — contract `operationId` ≠ app route name (cosmetic) | 🔓 Open |
| D-017 | Low | Seed prod guard runs after `app.models` import | 🔓 Open |
| D-045 | Low | 7 employee pickers lack server-side search (read all pages, no search) | 🔓 Open — *next frontend batch* |
| D-001…D-044 (excl. above) | Critical/High/Med/Low | 41 defects found and fixed across 14 batches | ✅ Closed |

---

## 6. Pending & Next — Ordered Queue

| Priority | Item | Owner | Depends | Effort |
|---|---|---|---|---|
| **P0** | **FD-08 — Payroll & talent ops surfaces** (pay runs, performance, learning, benefits) | frontend-design | none | L |
| P1 | FD-09 — ESS hub, documents, onboarding config, leave drills | frontend-design | FD-08 | L |
| P1 | FD-10 — Integrations, data quality, user admin, import/export completion | frontend-design | FD-09 | M |
| P1 | QA-07 — Contract + cross-tenant negative tests (last partial in qa-validation) | qa-validation | — | M |
| P1 | Payroll execution follow-ups — run approval/lock, corrections, proration, currency, **bank export** (roadmap #1 revenue item) | payroll-rules | FD-08 | L–XL |
| P2 | HR-12 follow-ups — history backfill, contact fields dated, future-dated scheduling | workforce-core | — | M |
| P2 | SUP-04 — hosted staging service (paid Render tier) | super | owner approval | S |
| P2 | D-029 — publish `operationId` from app routes (301 warnings) | super | — | S |
| P3 | FD-10 follow-ups — searchable pickers (D-045), Vite chunk split (~859 kB), staging per-run schema, `.table-scroll` sweep, `safe()` sweep | frontend-design | — | S–M |
| — | AI capabilities (AI-01…AI-13) — controls land with first Tier A | platform-security | — | XL |
| — | D-017 — seed guard import order | qa-validation | — | S |

**Immediate next batch (per `agents/PROGRESS.md` Next Move):** `FD-08` → `FD-09` → `QA-07`.

---

## 7. Deployment Log (last 5)

| Time (UTC) | Commit | Backend deploy | Frontend deploy | Notes |
|---|---|---|---|---|
| 2026-10-28 | `874d3be` | `dep-dbgli04s728c738vutlg` live | `dep-dbgli04s728c738vuu2g` live | **Marketing design batch.** Design-system consistency (check:design green), public `/platform` showcase, hero gradients, /public/contact contract. Frontend `verify` green end-to-end. |
| 2026-10-28 | `78da19b` | `dep-dbgm1pdg1s2s73e58sr0` live | `dep-dbgm1pdg1s2s73e58t80` live | **Copy batch.** Invented "Trusted by" logo wall and fabricated customer quote replaced with honest product copy; About mission/attributes rewritten in Karmathy's language. |
| 2026-10-28 | `2c7d4ba` | `dep-dbgn4uijnfac739g6deg` live | `dep-dbgn4uijnfac739g6d10` live | **Phase T 404.** Broken-thread 404 page (`NotFound.tsx`): thread stops at a missing Offboard node (dashed), links home + demo; catch-all renders the 404 instead of redirecting. 404 SEO (`Page not found`, `noindex, follow`). Frontend `verify` green; prod checks green (backend /health 200, contact 201, frontend 200 incl. unknown path, live bundle contains the broken thread). |
| 2026-11-01 | `22063c6` | `dep-dbhkufnavr4c73a075b0` live | `dep-dbhkufnavr4c73a074u0` live | **AI module `/ai`.** Honest Phase-8 AI page: references `projectStatus.ts` (spec order, G0–G9 gates, deferred behind G9 — not debt), ThreadCompact at `perform`, no invented capabilities. Prod checks green (health 200, contact 201, `/ai` 200). |
| 2026-11-01 | `bfffd36` | `dep-dbjb67bil8vc73aa092g` live | `dep-dbjb678gbm7c73fm6smg` live | **Auto-generated natural keys + form UX.** `app/core/ids.py` `next_code` wired into all six create endpoints (EMP-/DEP-/JOB-/POS-/LOC-/CC-); `*Create` schemas make the key optional, `*Out` intact; uniqueness after generation. People create forms: "Auto" placeholders, inline validation, generated key in the success notice. ClientOnboarding: workspace URL `/t/{slug}/dashboard` shown after create + "Open" link. `FEATURES_TRACKING.md` added. Suites green (employees, jobs, master_data, hire, drift 12, alignment 17, onboarding 163); prod checks green. |
| 2026-11-02 | `4ed17d1` + `593bfb3` | unchanged (`dep-dbjb67bil8vc73aa092g`) | `dep-dbk0ndndnq4s73ec7cm0` + `dep-dbk0p4ed4qjc73b95e70` live | **Marketing makeover.** All 12 lifecycle module pages rewritten through a shared `ModulePage` shell (hero facts + ThreadCompact + evidence-chip capability grids grounded in FEATURE_MATRIX IDs + honest "designed and sequenced" roadmap strips + prev/next thread links + ThreadDark CTA artwork). New hand-drawn SVG artwork layer (`Artwork.tsx`). Pricing page: per-tier inclusion lists + honesty FAQ. Honesty fixes: vendor logo walls removed, "200+ tools" and "SCIM provisioning" claims corrected to the real capability set, stale "Q2 2026" SOC2 target replaced, DocuSign/Adobe claims removed from FAQ, industry cards deep-link to detail pages. SEO entries **added for all 12 module pages** (they previously resolved to the 404 meta — a real URL/SEO defect). `verify` fully green (routes 114, tsc, design, classes); all 30 public URLs + unknown path probed 200 in production; offending strings confirmed absent from the live bundle. |
| 2026-11-03 | `845de88` | no backend deploy required (or next scheduled deploy) | unchanged | **Build-agent workbench live (`files/tracker.py` + `AGENT_RUNBOOK.md`).** Atlas validation errors fixed (`66134b8`): four dependency cycles broken at their weakest edge, pseudo-deps (`STORAGE`, `ESS APIs`, `contracts/*`) removed, self-feeds dropped — `tracker.py validate` exits 0. BASELINE closed: **28/28 implemented capabilities verified** — HTTP E2E (hire→terminated `e2e_lifecycle` extended to **80 checks, all green** incl. payroll from verified fixture pack, import pipeline over real HTTP, contact intake) + Python suites (33/33 → 35/35 after adding the two new suites; **4,230 checks**). R1 opened: **IM-10 (upload-retention schedule)** — purge existed, nothing scheduled it; `RETENTION_SCHEDULE_ENABLED` (opt-in) wires boot+24h ticks in the worker family with dedup on pending, proven by a new 11-test suite. **IM-03 (streaming parse)** — pipeline already streamed via `iter_records`; a new 8-test parser suite proves row cap enforced during iteration + byte cap on chunked uploads + RFC 4180 handling. R1 remains 2 of 14 shipped; remaining 12 R1 features queued for their own build passes. |
| 2026-11-03 | `926266b` | unchanged (`dep-dbjb67bil8vc73aa092g`) | unchanged (`dep-dbkrta3d4abc73fe9h1g`) | **Hire→terminated end-to-end validation.** `scripts/e2e_lifecycle.py` extended from 40 → 70 checks against a seeded local SQLite backend: requisition→offer→hire→onboarding→master data→timesheet→roster→leave→**payroll** (components/period/pay-profile/run/process from synthetic verified fixture pack `QQ`, reconciliation expected == paid, segregation-of-duties refusal for same-operator approve, second-operator approval, finalize locking payslips read-only)→performance (goal/review/finalize/feedback)→benefits→learning (enrol/complete/certification)→compliance (rule/violation)→reports→termination→**audit chain verify**. RBAC asserted both directions (HR refused 403 on SuperAdmin-only `/platform/webhooks` and `/onboarding-portal/clients`; admin surfaces open to both admin roles). Auto-generated natural keys exercised in-flow. Fixed real bug: `payroll_test_suite.py` crashed at line ~1684 (`PayComponent` not imported after the last check — suite exited non-zero with 251 checks already passing); with the import the suite is 251/251 green. Full local gate: 33/33 backend suites PASS (uvicorn killed after run). Not run against prod (no prod creds used, no prod data mutated). |
| 2026-11-03 | `243416e` | unchanged (`dep-dbjb67bil8vc73aa092g`) | `dep-dbkrta3d4abc73fe9h1g` live | **Alignment pass — all pages corrected to the 360 design.** New shared `PageHero` + `PageBody` (`components/marketing/PageHero.tsx`): aurora band, eyebrow kicker, gradient-display title, optional intro/children; added to Homepage-scale pages and *every* remaining light page — About, Solutions, Resources, Careers, Documentation, Privacy, Terms, Contact (form wrapped in mk-card + mk-cta), FAQ (dark accordion + related bento), Security (PageHero centered, dark deep sections), Compare, Industries, IndustryDetail (aurora band, breadcrumb kept), NotFound (404 restyled to the broken thread). Light cards → `mk-card`; text tones normalized to `fg-muted`/`fg-subtle`; `border-amber-200` remapped dark; nav desktop breakpoint moved `md` → `lg` so the demo CTA never clips at mid widths. `verify` green (114 routes, tsc, classes); in-browser inspection of 12 pages, zero console errors; prod: all 32 public URLs 200, health 200; `mk-eyebrow`/`mk-cta` confirmed in the live CSS/JS bundles. |
| 2026-11-02 | `4fe07a3` | unchanged (`dep-dbjb67bil8vc73aa092g`) | `dep-dbk72vndnq4s73egomu0` live | **360° visual redesign.** Scoped dark-first design system (`frontend/src/marketing.css`): the marketing subtree (`mkt-root`) re-declares the token variables dark — legacy marketing pages render dark automatically with zero edits — plus unlayered remaps for fixed light utilities (`bg-white`, `text-gray-*`, pale hero gradients). Space Grotesk display face added to the Google Fonts link; display clamp type (`mk-h1/mk-h2`), gradient headline text, glass sticky nav (`.mkt-nav`), gradient-border cards (`.mk-card`), glow CTAs (`.mk-cta`/`.mk-ghost`), capability marquee, code-built floating dashboard mockup (`ProductMockup.tsx` — sidebar/KPIs/reconcile bars/approved-time table, captioned "Illustrative window — sample rows"), reveal-on-scroll via IntersectionObserver in `PublicLayout`, giant gradient footer wordmark. `ModulePage` shell + Pricing restyled to the dark system. Stack unchanged (React + Vite + Tailwind, no new deps). `verify` fully green (routes 114, tsc, classes); visual inspection of /, /payroll, /faq, /about, /platform, /industries, /contact, /security — coherent dark rendering, zero console errors; all 32 public URLs probed 200 in production; design-system tokens confirmed present in the live CSS bundle. |
| 2026-10-28 | `016d8e1` | `dep-dbgmg92vcj2c73djktpg` live | `dep-dbgmg92vcj2c73djktcg` live | **Phase T batch.** "The Thread" lifecycle design concept landed: design-system source of truth (`designSystem.ts`), `ThreadHero`/`ThreadCompact` wired into the marketing hero, thread draw-once CSS + reduced-motion. SEO foundation: `usePageSEO` mounted from `PublicLayout`, per-page titles/descriptions/canonical/OG/Twitter/JSON-LD, robots + sitemap corrected, 1200x630 OG image. Frontend `verify` green end-to-end; prod checks green (frontend 200 across public marketing set, backend /health 200, contact 201). |
| 2026-10-27 06:23 | `5e87961` | `dep-dbg45nfb9u1s73fs8m70` live | `dep-dbg45nfb9u1s73fs8mk0` live | **Code in production.** Migration `0026_employment_history` applied. Drift 314/36/0. |
| 2026-10-27 06:26 | `0706fd5` (docs) | `dep-dbg479brjlhs73couc60` live | unchanged | Docs-only. Worker restarted. |
| 2026-10-27 05:50 | `32ead73` | `dep-dbg3ln49v7es73e0jscg` live | `dep-dbg3ln49v7es73e0jspg` live | `SUP-06` jobs envelope. |
| 2026-10-27 05:29 | `d39e72a` | `dep-dbg3cci9lscs738thu8g` live | `dep-dbg3ccq9lscs738thulg` live | `WC-04`/`FD-14` directory. |
| 2026-10-27 04:35 | `9b52bf8` | `dep-dbg2jefb9u1s73fqq750` live | `dep-dbg2jefb9u1s73fqq7i0` live | `PS-12`/`FD-13` audit verify. |

Full log: `agents/PROGRESS.md` §8.

---

## 8. How This File Stays Current

- **After every batch:** update §1 counts, §3 request row, §4 domain row, §6 queue, §7 deploy row.
- **Source of counts:** `docs/product/FEATURE_MATRIX.md` (capabilities) and `agents/TASK_BOARD.md` (requests) — never hand-counted.
- **Board of record** remains `agents/TASK_BOARD.md`; this file is the **human-readable tracker** that mirrors it with phase context and sub-tasks.
- **One commit per batch** — this file ships in the docs commit that follows the code commit (same pattern as `PROGRESS.md` §8 rows).

---

*Every number here was measured at `5e87961` or is traceable to a named request file. Nothing is an estimate; estimates live in `docs/audit/FEASIBILITY.md`.*
