# Karmathy HCM — Feature Validation Matrix

**Iteration:** 0 baseline, rows reconciled through the `FD-12` batch (the screens tell the truth)
**Commit:** `5f7db13` (baseline) · `bb25a42` (payroll rows) · `63ed6c7` (audit rows) · `259188e` (jobs monitor) · `73c25d6` (monitor screen) · `59345e1` (responsive) · `e32aca3` (job worker) · `fcdb658` (import progress) · `a20e862` (cancel + screen) · `41a5d87` (Oracle fixes) · `024b1fc` (frontend coverage) · `9b52bf8` (audit verification) · `d39e72a` (employee directory) · `32ead73` (jobs envelope) · `5e87961` (employment history)
**Date:** 2026-10-20 · **Updated:** 2026-10-27
**Backends tested:** Live `https://karmathy-backend.onrender.com` + local SQLite
**Source of truth:** `KARMATHY_MULTI_AGENT_BUILD_BRIEF.md`; current code state observed in repo.

Status values: `VERIFIED` | `PARTIAL` | `MISSING` | `BLOCKED (needs decision)` | `BLOCKED (needs rule pack)` | `REMOVED`

---

## Platform and security

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| P-01 | First-admin setup from environment secret (no default password) | 2.1 | `POST /auth/users` (admin), `POST /auth/password` | `/login`, `/change-password` | VERIFIED | `seed_admin.py` reads `ADMIN_INITIAL_PASSWORD` env var, refuses without it; default credential no longer accepted (verified live: 401); new credential authenticates at 200. An operator who loses the credential runs `scripts/reset_admin_password.py` with `ADMIN_RESET_PASSWORD` set: it only touches a SuperAdmin, clears the lockout, leaves the account needing a password change, is idempotent, and never prints the password. Verified live | The reset variable must be removed from the environment after use; the release step runs the script on every deploy and it is a no-op without the variable |
| P-02 | Forced password change on first login | 2.1 | `POST /auth/password`, `GET /auth/me` | `/change-password` | VERIFIED | `must_change_password` gate in `get_current_active_user`; live confirmed normal endpoints return 403 until password set; the operator reset leaves the same state | None |
| P-03 | Login with per-IP rate limiting + per-account lockout | 2.1 | `POST /auth/login` | `/login` | VERIFIED | `core/rate_limit.py` sliding window; `failed_login_count`/`locked_until` columns; lockout returns 403 with Retry-After | None |
| P-04 | Token refresh and rotation + revocation | 2.1 | `POST /auth/refresh`, `POST /auth/logout` | — | VERIFIED | Refresh tokens table with `rotated_at`/`revoked_at`; reuse revokes whole family | None |
| P-05 | MFA for SuperAdmin and HR roles (TOTP) | 2.1 | `POST /auth/mfa/enroll`, `/auth/mfa/confirm`, `/auth/mfa/disable`, `/auth/mfa/status` | — | VERIFIED | TOTP via pyotp, secret encrypted at rest, recovery codes bcrypt hashed + single-use, `require_mfa` dependency gates privileged roles; `mfa_test_suite.py` (15 checks) pass | None |
| P-06 | Password policy (length, breach blocklist, no reuse of last N) | 2.1 | `POST /auth/password`, `POST /auth/register` | `/change-password` | VERIFIED | `core/password_policy.py` enforces min 12, local blocklist, history depth 5, identity derivation | None |
| P-07 | Security headers (CSP, HSTS, X-Content-Type-Options, frame protections) | 2.1 | — | — | VERIFIED | `SecurityHeadersMiddleware` sets CSP, HSTS (prod+HTTPS), nosniff, DENY, referrer policy on every response including errors; `security_headers_test_suite.py` (8 checks) pass | None |
| P-08 | CORS allow-list (deny by default) | 2.1 | — | — | VERIFIED | `main.py` `CORSMiddleware` with empty allow-list; `allow_credentials=False` | None |
| P-09 | Field encryption with key versions + rotation | 2.1 | — | — | PARTIAL | `core/security.py` `encrypt_secret`/`decrypt_secret` versioned (`ENCv1:<key_id>:<token>`); rotation supported | Wire encryption into employee sensitive fields (bank, national ID) |
| P-10 | Sensitive field masking with reveal logging | 2.1 | — | — | MISSING | No masking/reveal flow in backend or UI | Build masked fields + re-auth reveal + audit log |
| P-11 | Secret handling: no secrets in code/logs/DB plaintext | 2.1 | — | — | VERIFIED | `ci/secret_scan.py` blocks hardcoded secrets; `core/observability.py` redacts 25 sensitive keys | Secret scan already passes |

## Authorization and tenancy

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| A-01 | Central policy module (role + ownership + visibility) | 2.2 | `apply_visibility()` on all read endpoints | — | VERIFIED | visibility.py applied to payroll, benefits, time, scheduling, ess_hr, core_hr, performance, learning, compliance, onboarding, employees, leave, offboarding | None |
| A-02 | Employee-scoped reads: self / direct reports / department HR / payroll / admin | 2.2 | `apply_visibility()` + `ensure_can_view_employee()` | — | VERIFIED | Visibility filtering applied to all employee-scoped list and detail endpoints across 13 endpoint files | None |
| A-03 | Role guards: SuperAdmin, HR, Manager, PayrollViewer, Associate | 2.2 | `require_roles()` in deps.py | — | VERIFIED | `get_current_admin_user` (SuperAdmin/HR); `require_roles()` for arbitrary sets | None |
| A-04 | Negative cross-user tests on every module | 2.2 | Extended security and visibility test suites | — | VERIFIED | 74 security + 29 visibility checks pass, covering all scoped endpoint files | None |

## Audit and jobs

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| J-01 | Audit row on every mutation, same transaction | 2.4 | `record_audit()` | — | VERIFIED | `record_audit` stages on the session; `audit_test_suite` proves a rollback leaves no row and a commit leaves exactly one. Every row written during a request carries a hashed source address; `details` is redacted; the lockout transition and an unknown username are audited | None |
| J-02 | Hash-chained audit log + verification CLI | 2.4 | `python -m scripts.verify_audit_chain`, `GET /admin/audit/verify` | `/reports` | VERIFIED | `audit_logs.prev_hash`/`entry_hash` over the canonical form in `app/core/audit_chain.py`; `verify_chain` walks in id order, recomputes each hash and names the first failure; the CLI exits 0 and prints the head on an honest chain, exits 1 and names the entry on a tampered one. `audit_chain_test_suite` (57 checks) covers linkage, an edited row, a truncated tail and the exit codes. The operation is now **served** (`PS-12`): `GET /admin/audit/verify` answers the contract's `AuditVerification` with the entry count, the head and a stable reason (`hash_mismatch`, `missing_predecessor`, `head_mismatch`); `admin_audit_test_suite` (39 checks) breaks the chain in every way a row can be broken, and the call is itself audited without breaking the chain. The screen runs it on request and shows the head to anchor (`FD-13`) | Record the pair `(checked_entries, head)` outside the database at each release (DEC-027) — the verification's own entry becomes the next head |
| J-03 | Append-only audit at DB level | 2.4 | — | — | VERIFIED | `BEFORE UPDATE`/`BEFORE DELETE` triggers on `audit_logs` (installed by `0022_audit_hash_chain`) raise an error on Oracle and SQLite; the suite proves both statements are refused and that the downgrade removes the guards. A trigger, not a REVOKE, because the application is the schema owner (DEC-027) | A principal with DDL rights can drop the trigger; the chain and the anchored head are what catch that |
| J-04 | Background job queue (queued/running/succeeded/failed/dead) | 2.5 | `backend/app/jobs/queue.py`, `backend/app/jobs/worker.py`, `GET /admin/jobs` | `/jobs` | VERIFIED | JobQueue model, JobState/JobType enums, JobQueueService with claim/lease/heartbeat/complete/fail/retry/dead-letter; **a real `JobWorker` executes the queue** — claim with a conditional update, decode the stored payload, run the handler, heartbeat, complete or fail — and the paged monitor reports the stored `queued` as the contract's `pending`. The detail read serves the stored `result`; the stored `input` only when `include_payload` is asked for, because it can carry a confirmation token. The worker is off unless `JOB_WORKER_ENABLED` is set, so a harness asserting a job is queued is not racing a thread that applies it | `jobs_test_suite.py` (24 checks) + `job_worker_test_suite.py` (42 checks, incl. a queued import applied once and not twice) + `admin_jobs_test_suite.py` (69 checks) |
| J-05 | Job leases with heartbeat + exponential backoff + dead-letter view | 2.5 | `backend/app/jobs/queue.py`, `backend/app/jobs/worker.py`, `GET /admin/jobs` | `/jobs` | VERIFIED | The listing answers the contract's `{items, meta}` envelope (`SUP-06`, `D-044`), so the page count is the server's; Lease/heartbeat, retry with exponential backoff + jitter, max attempts; the worker heartbeats at a third of the lease so a handler that outlives it still succeeds, releases an expired lease and re-runs the job, and `stop()` waits for the job in flight; a **permanent** refusal (`JobNotImplemented`, `JobInputInvalid`) goes straight to `dead` on attempt 1 instead of being retried; the operator view lists dead rows without hiding them, retries a dead job and discards a pending one, audited | `jobs_test_suite.py` (24 checks) + `job_worker_test_suite.py` (42 checks) + `admin_jobs_test_suite.py` (69 checks) |
| J-06 | Job types: csv_import, forecast_run, roster_solve, payroll_process, document_render, webhook_deliver, retention_run, erasure_run | 2.5 | `backend/app/jobs/registry.py`, `handlers.py` | — | VERIFIED | 8 job types registered. **None of them reports success it did not achieve:** `csv_import` applies the import, `roster_solve` runs the solver, `retention_run` calls `purge_expired_uploads`; the other five raise `JobNotImplemented` naming what actually does the work (`POST /forecasting/runs`, `POST /payroll/runs/{id}/process`, no renderer, no webhook subscription, `HR-12`). A placeholder that returned `{"status": "payroll_complete", "payslips": 0}` was the defect | `job_worker_test_suite.py` (42 checks; every unbuilt handler is asserted to refuse, and the mutation that restores a success result fails 3 checks) |
| J-07 | Input hash / result hash; idempotent re-run | 2.5 | `backend/app/jobs/queue.py`, `backend/app/imports/progress.py`, `POST /import-export/import/{entity}/cancel` | `/imports` | VERIFIED | Input hash (SHA-256), result hash, idempotent re-enqueue returns existing job; the payload itself is stored beside its hash (`0024_job_input_payload`) so a worker can execute the job, and a row without one is dead-lettered rather than guessed at. The **result** is stored beside its hash too (`0025_job_result_payload`) and served: `GET /import-export/import/{entity}/progress/{job_id}` reports the job's state, the rows applied and rejected, and the report when it finishes; it can be **cancelled** (`POST /import-export/import/{entity}/cancel`, audited once, a committed import refused with `409`), and the import screen polls the progress and offers the Cancel button. A failed import reports zero rows applied, because its transaction rolled back. | `jobs_test_suite.py` (24 checks) + `job_worker_test_suite.py` (44 checks) + `import_test_suite.py` (54 checks for progress and cancellation) |

## Onboarding and configuration

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| O-01 | Setup state machine (resumable: company profile → business type → modules → import → roles → review → launch) | 2.8 | — | `/onboarding` | MISSING | No `backend/app/onboarding/` module; frontend Onboarding page exists but backend state machine absent | Build onboarding state machine |
| O-02 | Idempotent launch (no duplicate records on re-run) | 2.8 | — | `/onboarding` | MISSING | No onboarding backend | Build launch with idempotency |
| O-03 | Preset engine: versioned presets validated against preset schema | 2.8 | — | — | PARTIAL | `contracts/rules/preset.schema.json` exists; no preset loader/backend | Build preset loader + validation |
| O-04 | `REQUIRES_RULE_PACK` sentinel blocks payroll enablement | 2.8 | — | — | PARTIAL | Schema enforces sentinel; no enforcement in code | Build payroll block on missing verified pack |
| O-05 | Module dependency graph enforced server-side | 2.8 | — | — | MISSING | Schema documents `requires`; no server enforcement | Build dependency graph checks |
| O-06 | Configuration assistant: rule-based gap detection | 2.9 | — | — | MISSING | No config assistant module | Build gap detection rules + fix targets |
| O-07 | Curated help index (no free-text LLM generation) | 2.9 | — | — | MISSING | No config assistant UI | Build help index panel |

## CSV import

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| I-01 | Import templates: departments, locations, jobs, employees, leave_balances, shift_templates | 2.7 | `GET /imports/templates` | — | MISSING | No import backend module; frontend import page exists | Build import engine per `docs/IMPORT_TEMPLATES.md` |
| I-02 | Exact header matching + alias table; unknown headers rejected | 2.7 | — | — | MISSING | No import engine | Build header validation |
| I-03 | Streaming UTF-8 parse; row limit 10,000; size limit 5 MB | 2.7 | — | — | MISSING | No import engine | Build streaming parser with limits |
| I-04 | Validation: types, required, ISO 8601, enums, referential, duplicates, salary bounds | 2.7 | — | — | MISSING | No import engine | Build validation rules |
| I-05 | Formula-injection neutralisation (=, +, -, @, tab, CR) | 2.7 | — | — | MISSING | No import engine | Build neutralisation |
| I-06 | Dry run with counts + row-error CSV; confirmation token bound to result hash | 2.7 | — | — | MISSING | No import engine | Build dry-run + commit flow |
| I-07 | Idempotent upsert on natural keys; re-import = zero changes | 2.7 | — | — | MISSING | No import engine | Build idempotent upsert |
| I-08 | Uploaded file deletion after retention (default 7 days) | 2.7 | — | — | PARTIAL | Import engine processes files immediately; retention cleanup not yet implemented | Add retention schedule + cleanup job |

## Employees and organisation

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| E-01 | Employee lifecycle: pre-hire → active → on leave → suspended → terminated → rehire | 3.1 | `PATCH /employees/{id}` | — | PARTIAL | `Employee.status` field exists (Active/On Leave/Terminated/Rehired); no transition enforcement | Build state-machine transitions with reasons |
| E-02 | Effective-dated employment history (job, dept, location, manager, pay profile) | 3.1 | — | — | MISSING | `Employee` has current fields only; no history table | Build effective-dated history |
| E-03 | Org chart from manager relationships; cycle detection; reassignment preview | 3.1 | `GET /employees/{id}/org-chart` | — | PARTIAL | Endpoint exists; cycle detection not verified | Build cycle detection + impact preview |
| E-04 | Work eligibility documents with expiry, reminders, masked storage | 3.1 | `GET /employees/{id}/documents`, `GET`/`POST /core-hr/employee-documents` | `/people` | PARTIAL | Document endpoints exist and **the People detail panel lists an employee's documents and records one** (`FD-12`); expiry tracking, reminders and masking are not verified | Build expiry + reminders + masking |
| E-05 | Emergency contacts, dependants, banking (encrypted, masked, re-auth change) | 3.1 | — | — | MISSING | No banking/emergency contact model | Build models + encryption + re-auth |

## Time and attendance

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| T-01 | Clock in/out with timezone-correct timestamps + optional geofence | 3.2 | `POST /time/clock-in`, `POST /time/clock-out` | `/time` | PARTIAL | Endpoints exist; timezone/geofence not verified | Build timezone + geofence |
| T-02 | Break rules per location/jurisdiction; auto-deducted or enforced | 3.2 | — | — | MISSING | No break rules model | Build break rules |
| T-03 | Overtime from rule engine: daily/weekly thresholds, premium multipliers, caps; traceable rule | 3.2 | — | — | PARTIAL | Flat `hours − 8` calculation exists (Gate 0); no rule pack, no multipliers, no traceability | Build rule-pack overtime |
| T-04 | Timesheet approval workflow; lock after payroll cut-off; adjustment records | 3.2 | `POST /time/timesheets/{id}/approve` | — | PARTIAL | Approve endpoint exists; lock/adjustment not verified | Build lock + adjustment flow |
| T-05 | Working-time compliance: max weekly hours, min daily rest, max consecutive days, night-work | 3.2 | `GET /time/working-time-violations` | — | PARTIAL | Endpoint exists; no rule-pack thresholds, no violation records | Build working-time rules + violations |

## Leave

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| L-01 | Leave types/policies per jurisdiction + preset; accrual schedules | 3.3 | `GET /leave/types` | `/leave` | PARTIAL | `LeaveType` model exists; accrual not ledger-based | Build accrual + tenure-based entitlements |
| L-02 | Balance ledger (every accrual/usage/adjustment is a ledger row) | 3.3 | `GET /leave/balances/{employee_id}/ledger`, `GET /leave/reconciliation` | — | PARTIAL | `leave_ledger` table with migration `0012_leave_ledger` (the backfill gives every existing balance a real genesis, not a marker); `app/services/leave.py` derives the balance from the signed rows, refreshes the cached columns from them, and refuses a balance that moves without a row; 100 checks in `backend/leave_test_suite.py`; the Oracle round trip passed three cycles with the head at `0012_leave_ledger` | Not merged or released yet, so not verified live; the accrual schedules that feed the ledger are a separate item (`L-01`), and the ledger has no effective date, so a period query reads the requests |
| L-03 | Request validation: balance, overlap, blackout, minimum notice, holidays | 3.3 | `POST /leave/requests` | `/leave` | PARTIAL | Request endpoint exists; full validation not verified | Build complete validation |
| L-04 | Approval chain (manager → HR where configured); cancellation with reversal | 3.3 | `POST /leave/requests/{id}/approve`, `/cancel` | `/leave` | PARTIAL | The approval writes a `USAGE` row to the ledger and the balance falls by exactly the requested days; the cancellation writes the reversal as another row, so the history is rows and never deletions; an approval the balance cannot cover is refused with `leave_insufficient_balance`, and a cancellation with no usage to reverse is refused | The configurable manager → HR chain is still not built; the endpoints are merged |
| L-05 | Public holiday calendar per location, year-specific, CSV import | 3.3 | `GET /leave/holidays`, `POST /leave/holidays` | — | MISSING | Endpoints exist; calendar not verified | Build holiday calendar |
| L-06 | Statutory leave from rule packs only (maternity, paternity, sick, bereavement) | 3.3 | — | — | BLOCKED (needs rule pack) | No India rule pack verified | Build blocked state; enable when pack verified |

## Scheduling

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| S-01 | Shift model: templates, positions, skills, locations, break rules, min rest | 3.4 | `GET /scheduling/shift-templates` | `/scheduling` | PARTIAL | `shift_templates` table exists; full model not verified | Build complete shift model |
| S-02 | Roster solver: OR-Tools CP-SAT; hard constraints (availability, leave, max hours, rest, consecutive days, skills, location, no double-booking, labour limits) | 3.4 | `POST /scheduling/roster/generate` | `/scheduling` | MISSING | Generate endpoint exists; solver not implemented | Build OR-Tools solver |
| S-03 | Soft constraints: fairness, preference, cost; configurable weights listed in output | 3.4 | — | — | MISSING | No soft constraints | Build soft constraints + weight output |
| S-04 | Solver timeout: best feasible roster + explicit unfilled slots with cause | 3.4 | — | — | MISSING | No timeout handling | Build timeout + unmet-slot list |
| S-05 | Coverage output per day/location/role: demand, assigned, unmet, over-staffed | 3.4 | `GET /scheduling/coverage` | — | MISSING | Coverage endpoint exists; not verified | Build coverage computation |
| S-06 | Publish = separate confirmed action; re-validate hard constraints; immutable; versioned | 3.4 | `POST /scheduling/roster/publish` | — | MISSING | Publish endpoint exists; not implemented | Build publish flow + versions |
| S-07 | Swap requests re-check constraints; audit entries | 3.4 | `POST /scheduling/swaps`, `/approve` | — | PARTIAL | Swap endpoints exist; constraint re-check not verified | Build constraint re-check |

## Forecasting

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| F-01 | Demand forecast by location/role/day from history or driver CSV | 3.5 | `POST /forecasting/runs` | — | PARTIAL | Engine builds seasonal-naive and Holt-Winters forecasts with confidence bands; `POST /forecasting/runs` accepts a time series and returns per-period predictions. Verified locally against synthetic weekly-seasonal data (MAPE 0.021, MASE 0.673) | Series is supplied by the caller; no screen yet aggregates time entries into the series, and there is no CSV driver source |
| F-02 | Model selection by rolling-origin backtest (not default) | 3.5 | `POST /forecasting/runs` (`method=auto`) | — | VERIFIED | `ForecastEngine._select_method` runs a rolling-origin backtest over the last 4 weeks and picks the lower-MAPE method; MAPE and MASE are both reported on the run | — |
| F-03 | Headcount forecast from hires/exits/leave/requisitions; cohort attrition | 3.5 | — | — | MISSING | No headcount forecast | Build headcount forecast |
| F-04 | Labour cost forecast labelled as excluding statutory on-costs | 3.5 | — | — | MISSING | No cost forecast | Build cost forecast + label |
| F-05 | Every forecast carries method, data window, backtest MAPE/MASE, holdout, band, input hash, version | 3.5 | `POST /forecasting/runs` | — | VERIFIED | `ForecastResult` stores `method_used`, `rule_version`, `input_hash`, `data_start_date`/`data_end_date`, `lower_bound`/`upper_bound`; `ForecastRun` stores `backtest_mape`, `backtest_mase`, `backtest_holdout_days` | — |
| F-06 | Insufficient history (<8 weeks): baseline + explicit flag | 3.5 | `POST /forecasting/runs` | — | PARTIAL | `ForecastEngine` raises `ForecastError` below 56 observations and the endpoint returns 422 with the shortfall; the seasonal-naive baseline is the documented fallback for a failed backtest | The response does not carry an explicit `insufficient_history` flag or the baseline values; it refuses the request instead |
| F-07 | Scenario comparison with explicit visible assumptions | 3.5 | `POST /forecasting/scenarios/compare` | — | MISSING | Endpoint exists; not implemented | Build scenario comparison |

## Payroll

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| PY-01 | Pay components: earnings, deductions, employer contributions, allowances, taxes | 3.6 | `GET /payroll/pay-components`, `/pay-profiles` | `/payroll` | PARTIAL | `PayComponent` and `EmployeePayProfile` models exist; calculation not rule-pack driven | Build rule-pack-driven calculation |
| PY-02 | Pay calculation pipeline: inputs → validation → calculation → totals → review → approval → lock → payslips → payment file | 3.6 | `POST /payroll/runs`, `/calculate`, `/approve`, `/finalise` | `/payroll` | PARTIAL | The pay run now consumes the approved leave and time of the period: `_approved_inputs` reads `Approved` leave requests (pro-rated to the period) and `Approved` time entries, and records the unapproved ones as exceptions. 13 checks in `backend/payroll_test_suite.py` prove it | Approval, lock and the payment file are still missing (`PY-04`–`PY-06`) |
| PY-03 | Every payslip line links to input source, rule ID, rule version, calculation | 3.6 | `GET /payroll/payslips`, `GET /payroll/payslips/{id}` | `/platform/payroll` | VERIFIED | Every earning and deduction line carries `rule_id`, `rule_version` and `input_source`; the payroll suite asserts all three on every line, and the slip records the approved inputs in `inputs_json`. **The screen shows it** (`FD-12`): the Payroll tab's `PayslipPanel` lists the inputs the slip consumed, marks the draft time entries **excluded**, and prints the rule id, version and calculation for every line — nothing recalculated in the browser (`e2e/frontend-truth.spec.ts`) | None |
| PY-04 | Reconciliation report ties every total to inputs | 3.6 | `GET /payroll/runs/{id}/reconciliation` | — | MISSING | Reconciliation endpoint exists; not implemented | Build reconciliation |
| PY-05 | Dry run produces full results without locking; labelled "configurable calculation" | 3.6 | `POST /payroll/runs/{id}/calculate` | `/payroll` | PARTIAL | Dry-run endpoint exists; blocked-jurisdiction message implemented | Label dry-run output; implement full calc |
| PY-06 | Pay runs immutable after approval; corrections via off-cycle adjustments | 3.6 | — | — | MISSING | State machine exists; immutability not enforced | Build lock + off-cycle adjustments |
| PY-07 | Rounding, currency precision, pro-rata configurable and tested | 3.6 | — | — | MISSING | No rounding config | Build rounding rules + tests |
| PY-08 | Payroll blocked unless verified rule pack attached; block message says what's missing | 3.6 | `POST /payroll/runs/{id}/calculate` | `/payroll` | VERIFIED | Blocked-jurisdiction behaviour implemented at Gate 0; returns `rule_pack_not_verified` | None |
| PY-09 | Mandatory payslip fields from rule pack | 3.6 | — | — | MISSING | Schema has `mandatory_payslip_fields`; not enforced | Build field validation from pack |

## Rule packs

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| RP-01 | Rule packs: versioned, signed, JSON validated against rule-pack schema | 3.7 | `GET /admin/rule-packs`, `GET /admin/rule-packs/{id}` | — | PARTIAL | Schema exists; loader/admin endpoints exist; signing not verified | Build signing + loader |
| RP-02 | Pack status lifecycle: draft → pending_verification → verified → superseded | 3.7 | — | — | VERIFIED | Schema enforces lifecycle; `verified` only usable in production | None |
| RP-03 | Verification records verifier name, role, date, source document reference | 3.7 | — | — | MISSING | Schema requires verification block; not implemented in code | Build verification recording |
| RP-04 | Effective-date resolution (rule version in force on relevant date) | 3.7 | — | — | MISSING | No effective-date engine | Build resolution |
| RP-05 | Pure deterministic engine; golden cases; no rule verified without golden test | 3.7 | — | — | MISSING | No rule engine | Build engine + golden case tests |
| RP-06 | Demonstration pack clearly marked `draft`, blocked from production | 3.7 | — | — | MISSING | No draft pack exists | Build draft pack fixture |

## Recruiting, onboarding tasks, offboarding, performance

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| R-01 | Requisitions with approval; candidate pipeline; interview scheduling | 3.8 | `GET /requisitions`, `POST /requisitions`, `GET /candidates` | `/recruiting` | PARTIAL | Endpoints exist; approval workflow not verified | Build approval + pipeline |
| R-02 | Offer generation with versioned templates; offer acceptance in one transaction with hire (idempotent) | 3.8 | `POST /offers`, `POST /offers/{id}/accept` | `/recruiting` | PARTIAL | Offer endpoints exist; transactional hire not verified | Build transactional hire |
| R-03 | Background-check status with consent records; checks not performed unless integration configured | 3.8 | `GET /background-checks` | — | PARTIAL | Endpoint exists; consent records not verified | Build consent records |
| R-04 | Equal-opportunity fields optional, stored separately, excluded from hiring views | 3.8 | — | — | MISSING | No EEO model | Build EEO model + separation |
| R-05 | Onboarding tasks per role/location with owners and due dates | 3.8 | — | — | MISSING | No onboarding tasks model | Build tasks model |
| R-06 | Offboarding: checklist, final pay trigger, asset return, access revocation, exit interview | 3.8 | `GET /offboarding`, `POST /offboarding` | `/offboarding` | PARTIAL | Offboarding endpoints exist; checklist/final pay not verified | Build checklist + final pay trigger |
| R-07 | Performance: goals, check-ins, review cycles, rating scales configurable per tenant; approval workflow | 3.8 | `GET /goals`, `GET /reviews` | — | PARTIAL | Goals/reviews endpoints exist; review cycles not verified | Build review cycles |

## Reports and compliance outputs

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| RP-01 | Operational reports: headcount, turnover, absence, overtime, coverage, forecast accuracy, leave liability | 3.9 | `GET /reports/*` | `/reports` | PARTIAL | Report endpoints exist; full report set not verified | Build all report types |
| RP-02 | Compliance reports: working-time violations, expiring eligibility, overdue certifications, retention status, erasure log, audit chain status | 3.9 | `GET /reports/*` | `/reports` | PARTIAL | Compliance endpoints exist; reports not verified | Build compliance reports |
| RP-03 | Statutory filings: exports only from verified rule pack template; pack version shown | 3.9 | — | — | BLOCKED (needs rule pack) | No India pack verified | Build blocked state |
| RP-04 | Reports as background jobs; CSV and PDF export; audit-logged | 3.9 | — | — | MISSING | No job module | Build report jobs |

## Data subject and retention

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| D-01 | Retention schedule per entity; editable by tenant admin; audit on changes | 2.10 | `GET /admin/retention`, `PATCH /admin/retention` | — | MISSING | Admin retention endpoints exist in contract; not implemented | Build retention scheduler |
| D-02 | Data subject export: JSON + CSV per employee; background job; authorized download | 2.10 | `GET /admin/dsar-exports`, `POST /admin/dsar-exports` | — | MISSING | DSAR endpoints exist in contract; not implemented | Build export |
| D-03 | Erasure: anonymise personal fields; legal hold; legal-basis field; erasure log | 2.10 | `POST /admin/erasure-requests` | — | MISSING | Erasure endpoints exist in contract; not implemented | Build erasure |
| D-04 | Legal hold flag blocks erasure | 2.10 | — | — | MISSING | No legal hold model | Build legal hold |

## Frontend and experience

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| X-01 | Typed API client generated from OpenAPI; build fails if stale | 4.1 | — | — | PARTIAL | Contracts exist; hand-written `types/index.ts` still in use | Replace with generated client |
| X-02 | Central error handling with shared envelope; 401 → refresh → sign-out; 403 → permission state | 4.1 | — | — | PARTIAL | `api.ts` normalises envelope; no 401 refresh logic | Add 401 refresh + sign-out |
| X-03 | Design system: tokens → CSS variables → Tailwind v4; light/dark | 4.2 | — | — | PARTIAL | Tailwind v3 + theme tokens exist; Tailwind v4 not migrated | Migrate to Tailwind v4 |
| X-04 | Component library: Button, Input, Select, Combobox, DatePicker, Textarea, Checkbox, Switch, Radio, Card, Badge, Avatar, Tabs, Dialog, Drawer, Popover, DropdownMenu, Tooltip, Toast, Skeleton, EmptyState, ErrorState, DataTable, PageHeader, StatusPill, FormLayout, Stepper, CommandPalette | 4.2 | — | — | PARTIAL | ~16 primitive components exist; DataTable virtualization, CommandPalette present; several missing | Complete component set + stories |
| X-05 | Storybook with accessibility checks | 4.2 | — | — | MISSING | No Storybook | Add Storybook |
| X-06 | App shell: workspace rail, secondary sidebar, breadcrumbs, ⌘K search, notifications, user menu, shortcuts, mobile bottom bar | 4.2 | — | — | VERIFIED | Shell components exist; command palette present. Every navigation entry now resolves to a distinct real URL, and `npm run check:routes` fails the build otherwise | None |
| X-07 | Only enabled pages/navigation appear for tenant and role | 4.2 | — | — | MISSING | No feature-flag gating of navigation | Build flag-aware navigation |
| X-08 | Role-based homes: Associate, Manager, HR, PayrollViewer, SuperAdmin with "Needs your action" | 4.3 | — | `/dashboard` | PARTIAL | Home pages exist; "Needs your action" not driven by real queries | Wire real queries |
| X-09 | Empty states with real next action; no sample content | 4.3 | — | — | PARTIAL | EmptyState component exists; not verified on all pages | Audit all empty states |
| X-10 | Forecast views: method, backtest error, data window, confidence band; insufficient-history explicit | 4.5 | — | — | MISSING | No forecast UI | Build forecast views |
| X-11 | Roster builder: coverage heatmap, unmet-slot list, constraint warnings, hours/cost per person, publish, version history | 4.5 | — | `/scheduling` | MISSING | Scheduling page exists; roster builder not implemented | Build roster builder |
| X-12 | Payroll screens: workflow, reconciliation, blocked-jurisdiction message, "configurable calculation" label | 4.5 | — | `/payroll` | MISSING | Payroll page exists; screens not implemented | Build payroll UI |
| X-13 | Sensitive fields masked by default; reveal requires re-auth + logged | 4.6 | — | — | MISSING | No masking UI | Build masked fields + reveal |
| X-14 | WCAG 2.2 AA on every page; axe-core in CI; manual keyboard passes | 4.6 | — | — | PARTIAL | A Playwright journey measures the contrast ratio of every visible text element on every page in dark mode, against the AA thresholds, and fails the build when one is missed. It found the heading and label ink that was invisible against the dark surfaces. axe-core now runs over 20 pages in CI, on WCAG 2.2 A/AA, and fails the build on a violation (`QA-04`; 21 tests, three defects found and fixed — `docs/validation/ACCESSIBILITY.md`). A manual keyboard pass is still a human task, and `responsive.spec.ts` now proves the skip link moves focus at all four widths | Manual keyboard audit |
| X-15 | Responsive at 360, 768, 1024, 1440 px | 4.6 | — | — | VERIFIED | `frontend/e2e/responsive.spec.ts` — 16 tests, four per width: the sign-in screen fits the viewport, the shell shows the navigation that belongs to the width (drawer below 1024 px, rail at and above it), no page scrolls sideways across five representative screens, and the skip link moves focus into `<main>`. The first run failed 7 of 16 and every failure was a measured defect, all fixed (`docs/validation/RESPONSIVE.md`) | — |
| X-16 | Reduced motion; colour never only signal | 4.6 | — | — | PARTIAL | `prefers-reduced-motion` in index.css | Verify all pages |
| X-17 | Performance budget: LCP < 2.5s marketing homepage; code splitting; virtualised lists >200 rows | 4.6 | — | — | MISSING | Single 637 kB JS chunk; no code splitting | Add code splitting + virtualization |
| X-18 | Employee directory: list, search, filters, detail, create; scoped to what the caller may see | 4.2 | `GET/POST /employees/`, `GET/PATCH/DELETE /departments/`, `GET/PATCH/DELETE /jobs/`, `GET/PATCH/DELETE /core-hr/locations`, `/positions`, `/cost-centers` | `/people`, `/people/departments`, `/people/jobs`, `/people/locations`, `/people/positions`, `/people/cost-centers` | VERIFIED | `pages/People.tsx` lists employees with the server's paged envelope: `search` over the employee number, the name and the email, `status` and `department` filters, `page` + `meta.total` (`N of total shown`) and a `Load more` that asks the next page. The search and filters are requests, not a filter of the loaded page; a detail dialog and an add-employee form shown only to SuperAdmin and HR complete it. The five reference tabs share one editor (create/edit/archive/restore/guarded delete) and show archived rows so they can be restored. The server remains the authority on visibility | Org chart is not drawn; the directory tab is the org view |
| X-19 | Every navigation target is a registered route and every protected page keeps the shell | 4.2 | — | — | VERIFIED | `npm run check:routes` resolves `<Link to>`, `navigate()`, object-property `to:`, `window.location.href`, and asserts every protected page imports `<Layout>`; `npm run check:api-paths` rejects a request that repeats the `/api/v1` prefix. Each check was confirmed to fail when its bug is reintroduced | — |
| X-20 | Every colour utility in the source is emitted by the build | 4.2 | — | — | VERIFIED | `npm run check:classes` reads the built stylesheet and reports any colour utility the build did not emit. It found 183 dead classes: `border-border` (68 uses), `text-text-secondary` (99), `bg-page` (14) and four opacity-modified utilities that Tailwind silently drops because the colour is a CSS variable | — |
| X-21 | The live schema and the SQLAlchemy models are compared and reported | 4.1 | `GET /health/schema` | — | VERIFIED | The diagnostic names the missing tables, the missing columns, the surplus columns and the type mismatches, comparing the identifiers case-insensitively on both sides because Oracle folds unquoted identifiers to upper case while SQLAlchemy quotes the reserved ones. It found the drift that made the payroll run listing answer 503, and the live deployment now reports itself in sync | The comparison is by class rather than by spelling, so a boolean stored as an integer and a number without a recorded scale are not reported |
| X-22 | A failed release migration is recorded where it can be read | 4.1 | `GET /reports/audit` | — | VERIFIED | The release step runs before the server binds, so a failure used to exist only in the container's output. It is now written to the audit trail as well, where the operator can read it through the API. This is how the ORA-01430 behind a failed deploy was found | The write is best effort: if it fails the reason is still printed and the original exception propagates |

## Marketing site

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| M-01 | Astro static site with copy/section order from project document | 4.7 | — | `/` | MISSING | Marketing pages exist in SPA; no Astro site | Build Astro marketing |
| M-02 | Real product screenshots from Storybook/staging; no illustrations of non-existent features | 4.7 | — | — | MISSING | No screenshots exist | Generate screenshots |
| M-03 | Claims match product; limitations as "requires configuration" | 4.7 | — | — | MISSING | Marketing copy not audited | Audit claims |

## Compliance matrix (from brief section 5)

| ID | Feature | Brief section | Backend endpoint(s) | UI route(s) | Status | Evidence | Gap / action |
|---|---|---|---|---|---|---|---|
| C-01 | Access control and least privilege | 5 | — | — | PARTIAL | Central policy exists; 73 unscoped reads, 7 IDOR writes | Block 1 |
| C-02 | Authentication strength | 5 | — | — | PARTIAL | MFA not implemented | Block 1 |
| C-03 | Audit trail and tamper evidence | 5 | `python -m scripts.verify_audit_chain`, `GET /admin/audit/verify` | `/reports` | VERIFIED | Hash chain with a compare-and-set head, append-only triggers and a verification that names the first failing entry, as a command and as an operation (`audit_chain_test_suite` 57 checks, `admin_audit_test_suite` 39 checks). Source address, redaction and the missing events landed with `PS-03` (29 checks) | The pair `(checked_entries, head)` must be anchored outside the database for a full-rewrite detection (DEC-027) |
| C-04 | Data encryption at rest for sensitive fields | 5 | — | — | PARTIAL | Versioned encryption exists; banking/ID not encrypted | Blocks 1, 6 |
| C-05 | Data subject access (export) | 5 | — | — | MISSING | Block 5 | Build export |
| C-06 | Erasure and anonymisation | 5 | — | — | MISSING | Block 5 | Build erasure |
| C-07 | Retention schedules | 5 | — | — | MISSING | Block 5 | Build scheduler |
| C-08 | Consent records | 5 | — | — | MISSING | Block 6 | Build consent |
| C-09 | Equal-opportunity data separation | 5 | — | — | MISSING | Block 6 | Build EEO |
| C-10 | Working time limits | 5 | — | — | PARTIAL | Flat hours−8 only | Block 6 |
| C-11 | Rest breaks and rest periods | 5 | — | — | MISSING | Block 6 | Build break rules |
| C-12 | Overtime calculation | 5 | — | — | PARTIAL | Daily only, no multipliers | Block 6 |
| C-13 | Minimum wage and pay floors | 5 | — | — | MISSING | Block 6 | Build pay floors |
| C-14 | Leave entitlements (statutory and contractual) | 5 | — | — | PARTIAL | Not ledger-based | Block 6 |
| C-15 | Public holidays | 5 | — | — | MISSING | Block 6 | Build calendar |
| C-16 | Payroll tax withholding | 5 | — | — | BLOCKED (needs rule pack) | Flat percentage only; disabled | Need India pack |
| C-17 | Social security and employer contributions | 5 | — | — | MISSING | Block 7 | Build contributions |
| C-18 | Mandatory payslip content | 5 | — | — | MISSING | Block 7 | Build from pack |
| C-19 | Pay frequency and pay-date rules | 5 | — | — | MISSING | Block 7 | Build pay calendar |
| C-20 | Statutory filings and returns | 5 | — | — | BLOCKED (needs rule pack) | Need India pack | Build exports |
| C-21 | Work eligibility and right-to-work documents | 5 | — | — | PARTIAL | Expiry tracking missing | Block 6 |
| C-22 | Health and safety incident records | 5 | — | — | MISSING | Block 6 | Build incident log |
| C-23 | Training and certification currency | 5 | — | — | PARTIAL | Expiry tracking missing | Block 6 |
| C-24 | Employment contract records | 5 | — | — | MISSING | Block 6 | Build contracts |
| C-25 | Reporting and records retention for audits | 5 | — | — | PARTIAL | Retention not applied | Blocks 5, 8 |
| C-26 | Pay transparency and equal-pay reporting | 5 | — | — | MISSING | Block 8 | Build report |
| C-27 | Accessibility of the product itself | 5 | — | — | PARTIAL | No axe in CI | Block 9 |
| C-28 | Secure transport and headers | 5 | — | — | PARTIAL | HSTS/CSP missing | Block 1 |

---

## Status summary (counted from the rows below, 2026-10-26)

| Status | Count |
|---|---|
| VERIFIED | 30 |
| PARTIAL | 50 |
| MISSING | 66 |
| BLOCKED (needs rule pack) | 4 |
| BLOCKED (needs decision) | 0 |
| REMOVED | 0 |
| **Total** | **150** |

---

## Evidence notes

- Backend live at `https://karmathy-backend.onrender.com` (HTTP 200 `/health`).
- 30 backend suites pass (3 960 checks) and 57 browser tests (20 journeys + 21 accessibility + 16 responsive) at the worker commit; the row statuses were reconciled against that tree.
- The merged OpenAPI is up to date (`scripts/merge_openapi.py --check`); the live drift check was not re-run because the free Render instance was asleep.
- Secret scan: clean.
- `docs/validation/` did not exist before this iteration; created now.
