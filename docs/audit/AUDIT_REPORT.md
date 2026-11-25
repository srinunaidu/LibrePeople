# Karmathy HCM — Phase 0 Audit Report

**Date:** 2026-10-21 · **Phase:** 0 (audit and decisions) · **Author:** Super Agent
**Repository:** `/Users/srinivas/LLM/Workforce/Karmathy` · **Origin:** `git@github.com:srinunaidu/Karmathy.git` (private)
**Commit audited:** `origin/main` = `70a8745` ("docs: record the credential recovery and the schema diagnostics")
**Mode:** read-only. No application code, configuration, production system or production data was modified.
**Measurement isolation:** every command was run in a dedicated worktree at `70a8745`. See `commands_run.md`.

Every finding is labelled **Verified**, **Inferred**, **Proposed**, **Not verified** or **Blocked**.

---

## 1. Executive summary

Karmathy is a **broad, working API with a thin business layer**. The repository serves 259
operations across 25 domains, the backend suites are green (17 suites, 520 checks), the frontend
typechecks, builds and passes its route, class and contrast checks, and the contract tooling is
sound. That is real progress, and it is the part of the build that is working.

The gap is between *an endpoint exists* and *the business behaves correctly and safely*. Under the
mandate's target catalog of 142 capabilities, **5 are demonstrated by an automated check, 58 are
partial, 69 are missing and — the part that matters most — 7 are `broken`**: they exist, they are
reachable, and they do the wrong thing. A capability that fails open is not progress; it is a
liability the customer can trip over, and it is the single biggest reason the product cannot be
released to anyone today.

Three things decide the next quarter:

1. **The security foundation is half-built.** The role half of the central policy module is dead
   code — `require_roles` is imported by no endpoint file — and role checks are three ad-hoc
   comparisons. The `Manager` and `PayrollViewer` roles are named in `ALL_ROLES` and enforced
   nowhere. The visibility half *is* applied, in 13 endpoint files.
2. **Payroll does not refuse.** `rule_pack_not_verified` appears nowhere in the backend, the
   payroll endpoint contains zero references to rule packs, and `POST /payroll/runs/{id}/process`
   persists payslips unconditionally. The release condition "payroll is disabled for a jurisdiction
   without a verified rule pack" is **not met**, and the feature matrix claimed it was.
3. **There is no staging.** `main` deploys straight to production on Render. The pilot gate
   ("12 journeys pass on staging") cannot be assessed, and a release candidate cannot cite a
   staging result or a load result.

**Recommendation:** do not attempt a broad feature build yet. Run Phase 1 (security and data
integrity) to completion, create staging, and land the four import, onboarding and payroll
capabilities that the product's value proposition actually rests on. The recommended pilot is in
§9.

---

## 2. Repository inventory

### 2.1 Backend — Verified

| | |
|---|---|
| Framework | FastAPI 0.111.0 (pinned), SQLAlchemy 2.0.29, Alembic, Pydantic 2.7.4, Python 3.11 in the image |
| Entry point | `backend/app/main.py`; the container runs `python -m scripts.migrate upgrade && python -m scripts.reset_admin_password && exec uvicorn app.main:app` |
| Routers | `backend/app/api/v1/api.py` registers 27 endpoint modules under `/api/v1` |
| Models | 26 modules in `backend/app/models/` |
| Migrations | 6 Alembic revisions, each with `upgrade` and `downgrade` |
| Services | `backend/app/services/` — importer, payroll engine, forecasting, metrics, data quality, storage, offer letter |
| Jobs | `backend/app/jobs/` — database queue with leases, heartbeat, exponential backoff, dead-letter, 8 registered job types |
| Audit | `backend/app/core/audit.py` — `record_audit()` called from **all 24** endpoint modules; ordinary rows, no hash chain, no source address |
| Auth | JWT access/refresh with rotation and revocation, MFA (TOTP), password policy, per-IP rate limiting, per-account lockout, forced password change |
| Served surface | **259 operations, 25 tags** (from the live `/api/v1/openapi.json`) |

### 2.2 Frontend — Verified

React 18 + TypeScript + Vite 5 + Tailwind v3 + Radix. 61 registered routes, all internal links
resolve. Bundle 668 kB, single chunk, no code splitting. Three build-time integrity checks:
`check:routes`, `check:api-paths`, `check:classes`. 10 Playwright journeys (contrast, first
sign-in, navigation). **Only `check:routes` is in CI** — the other two are not.

### 2.3 Infrastructure — Verified

| | |
|---|---|
| Database | Oracle Autonomous Database (`karmkathy_adb`, `ADMIN` schema), one schema per customer deployment |
| Hosting | Render free tier: `karmathy-backend` (Docker), `karmathy-frontend` (static) |
| Deploy | **auto-deploy on commit to `main`** — a push to `main` is a production deploy |
| Storage | `STORAGE_BACKEND=local` — ephemeral; offer letters and onboarding documents are lost on redeploy |
| CI | `.github/workflows/ci.yml`: backend suites, secret scan, dependency audit, contract merge, contract drift, schema/event validation, frontend typecheck, route check, build |
| Second deploy path | `.github/workflows/deploy.yml` pushes to an Oracle VM over SSH on every push to `main`. **It has never run in this build.** |
| Secrets | `~/.karmathy/{adb_password,wallet_password,admin-bootstrap.txt}`, mode 0600, outside the repository |

### 2.4 What the audits before this one found, and what happened to it

The 2026-10-19 audit (`docs/audit/archive/2026-10-19/`) found: object-level authorisation missing
on 73 reads and 7 writes; the documented default credential still authenticating in production;
ephemeral production storage; no migrations; no CI gate. **All five were acted on** by Gate 0
(2026-10-19) and iterations 1–6 (2026-10-20): visibility and ownership checks now cover 13
endpoint files, the credential was rotated and the published value is dead, migrations and a CI
gate exist. Its remaining accurate observation — that a security-only pilot is feasible at one
engineer's capacity — is carried into `FEASIBILITY.md`.

---

## 3. Agent roster — Verified

Eight specialist agents exist, each with `PROMPT.md`, `STATE.md` and `LEARNINGS.md` under
`agents/<agent>/`. All eight are **usable**: each has a charter with owned paths, a definition of
done, and a handoff convention. Nothing in the mandate's assignment map lacks an owner.

| Agent | Folder | Worktree | State at the end of this audit |
|---|---|---|---|
| Platform & Security | `platform-security` | `karmathy-platform-security` | **Two branches ready to merge**: `PS-02` (secret scan allowlist, `5bd0950`) and `PS-01` (production reset guard, `53d23f7`). Reported 17 suites / 549 checks in isolation. Delivered the DEC-000 investigation. |
| Data & Import | `data-import` | shared checkout | **Uncommitted.** Rewriting the import engine into `backend/app/imports/`, with `import_headers.py`/`importer.py` deleted, `import_export.py` modified, migration `0007_import_dry_runs.py` and `backend/golden/` added. |
| Payroll & Rules | `payroll-rules` | shared checkout | **Uncommitted.** `backend/app/rules/` (money, loader, engine, reconciliation) with 22 passing tests, a synthetic draft pack, `docs/PAYROLL.md`, `docs/REPORTS.md`. |
| Planning | `planning` | shared checkout | **Uncommitted.** `backend/app/forecasting/test_backtest_harness.py`, `docs/FORECASTING.md`. |
| Workforce Core | `workforce-core` | shared checkout | **Uncommitted.** `backend/app/models/leave.py` (leave ledger), `backend/app/retention/`. |
| Onboarding & Config | `onboarding-config` | `karmathy-onboarding-config` | Branch created, **no commits**. |
| Frontend & Design | `frontend-design` | shared checkout | **Uncommitted.** The monorepo (`packages/tokens`, `packages/ui`, `packages/api-client`, `packages/tenant-theme`, pnpm/Turborepo) and 10 design decisions. |
| QA & Validation | `qa-validation` | shared checkout | **Uncommitted.** The status pass over all 150 matrix rows, `docs/validation/TEST_COUNT.md`, `docs/validation/SEED_DATA.md`, the seed verification, and the test-count reconciliation. |

**Every lane exists and every lane has produced work. The problem is not capability; it is
integration.** Six of eight lanes have work that exists only as uncommitted files in a shared
directory. None of it is behind a gate.

---

## 4. Baseline results — Verified

| Check | Command | Result at `70a8745` |
|---|---|---|
| Backend suites | `bash ci/run_backend_tests.sh` | **17 suites, 520 checks, 0 failed** |
| Secret scan | `ci/secret_scan.py` | **exit 1, 11 findings** — CI is red |
| OpenAPI merge | `scripts/merge_openapi.py --check` | up to date |
| Contract drift | `scripts/check_openapi_drift.py --app <live>` | exit 0, 43 matched, 0 hard failures, **210 undeclared** |
| Frontend | `npm run verify` | typecheck, 61 routes, api-paths, build, classes — all pass |
| Journeys | `npx playwright test` | **10 passed** (12 required) |
| Migrations | `grep -c "def downgrade"` | 6 of 6 have a downgrade |
| Seed | QA's fresh-database run | matches every documented count (20 users, 12 departments, 8 locations, 20 jobs, 600 employees, 12 leave types, 814 balances, 788 requests, 22,321 time entries) |
| Load smoke | — | **no harness exists** |
| Staging | — | **no staging environment exists** |
| CI status of `main` | `gh` / GitHub API | **not readable** — no `gh`, private repo, 404 |

---

## 5. Security and incident status

### 5.1 DEC-000, the default credential — **Verified closed as a vulnerability; open as a release gate**

The Platform & Security agent investigated this read-only on 2026-10-21 and its findings are
corroborated by the evidence in `agents/platform-security/handoffs/2026-10-21.md`:

| Check | Result |
|---|---|
| The published credential against the live backend | **401** for `admin`, `administrator`, `superadmin`, `root` |
| The same against `seed_dev.db`, `backend/smoke_p814.db`, `debug_test2.db`, `debug_test3.db` | no account accepts it |
| The live `admin` account | present, active, role `SuperAdmin`, **not** in `must_change_password`, `password_changed_at` 2026-10-21 07:39:36 |
| `~/.karmathy/admin-bootstrap.txt` | still on disk, mode 0600 — **stale, no longer authenticates** |
| The production audit trail | 389 rows, 105 authentication events, **every one attributable**; no unrecognised actor, no unexplained session |
| Credential lifecycle in the trail | rotate (10-19 15:29) → 18 test accounts deactivated (15:37) → owner changed the password (10-20 08:31) → operator reset (10-21 07:37) → owner changed it again (10-21 07:39) |

**The exposure is closed.** The published credential is dead, no default password exists in the
codebase, the secret scan fails the build if it is reintroduced, and every account that used it is
deactivated or re-keyed.

**Three residual items, all owned by the human or by the owner of the environment:**

1. `~/.karmathy/admin-bootstrap.txt` still exists on the operator machine. It is stale, and it
   should still be deleted — a stale credential file is a credential file.
2. `ADMIN_RESET_PASSWORD` ran as a release step on every deploy until `PS-01` landed; the guard now
   requires an explicit acknowledgement and fails closed. The environment variables should still be
   confirmed unset.
3. The `admin` account's failure counter reads **5 of 10**, three of which are the verification
   attempts themselves. A successful sign-in resets it; the owner should know before seeing a
   lockout message.

**The release gate stays closed until the owner records closure.** DEC-000 is a *decision*, and the
decision has not been taken by the person entitled to take it.

### 5.2 The credential is still in the repository — **Verified**

`ci/secret_scan.py` holds the published credential **in plain text** as a denylist entry. It is a
deliberate control, and the board cites it as evidence that reintroduction fails the build. It is
also the one live credential-shaped value committed to the repository, and it is in the git
history. Storing the SHA-256 of each denylisted value keeps the same detection power with no
credential in the tree. Filed as `PS-07`.

### 5.3 Authorisation — **Verified**

| | |
|---|---|
| `apply_visibility` / `ensure_can_view_employee` | applied in **13** endpoint files |
| `require_roles` / `require_any_role` | defined in `app/api/deps.py`, imported by **no** endpoint file |
| Role checks in endpoints | **3** ad-hoc comparisons: `reports.py:124`, `reports.py:159`, `scheduling.py:182` |
| `User.role` | `String(50)`, default `"Associate"` — a free string, constrained only when written through `PATCH /auth/users` |
| `ALL_ROLES` | `SuperAdmin`, `HR`, `Manager`, `Associate`, `PayrollViewer` — `Manager` and `PayrollViewer` are enforced nowhere |
| Negative tests | 74 security + 29 visibility checks pass |

**Reading:** the *visibility* half of the policy module works and is tested. The *role* half is
dead code. `get_current_admin_user` is used by 26 of 27 endpoint files, so most endpoints are
admin-only rather than role-scoped — safe, but it means the documented role model is not in force.
**The single most valuable security task in the programme** is to apply `require_roles` to every
endpoint and delete the ad-hoc comparisons.

### 5.4 Audit trail — **Verified**

Every one of the 24 endpoint modules calls `record_audit`. Three gaps:

1. **The lockout transition is not audited.** Twelve failed logins on 2026-10-21 drove the counter
   to the threshold of 10 and locked the account. There is **no `login_blocked_locked` row**. A
   reader of the trail cannot distinguish a locked account from a wrong password.
2. **A failed sign-in against an unknown username leaves no row.** The login path returns before
   the audit write so the response does not confirm that a username exists. That is right for the
   *response*; the *audit row* does not have to follow it, and it does not. Credential stuffing
   against guessed usernames is invisible except to the per-IP limiter.
3. **There is no source address in `audit_logs`.** `refresh_tokens` has `ip_hash`; the audit table
   does not. Every incident review to date has been by actor and action rather than by origin.

### 5.5 The production exposure review — **Verified, with one honest note**

The audit trail was read in full. Every authentication event is attributable: the administrator
account (96 events, all consistent with the audit and end-to-end scripts) and 18 ephemeral test
accounts (9 events, all deactivated, one of which held `SuperAdmin`).

**The note.** Verifying the old credential against the live deployment wrote three `login_failed`
rows of its own. They are the last three authentication events in the production trail. The
verification was read-only in intent, but an authentication attempt is a write. It was disclosed
by the agent, and the account's failure counter was reported.

**Governance gap (Proposed):** the mandate's §2.2 says to treat DEC-000 as a release blocker and
to use read-only investigation. An agent's login attempts against production are neither read-only
nor obviously avoidable — the credential has to be tested somehow. The rule should say explicitly
that credential verification against production is permitted **only** with the owner's written
approval, that the attempt count is declared in advance, and that the failure counter is reset
afterwards. This is a decision for the human.

---

## 6. Feature status — Verified, missing and not verified

The full matrix is `docs/product/FEATURE_MATRIX.md` (142 capabilities). Summary:

| Status | Count | Share |
|---|---|---|
| implemented | 5 | 3.5 % |
| partial | 58 | 40.8 % |
| broken | 7 | 4.9 % |
| missing | 69 | 48.6 % |
| in-flight | 3 | 2.1 % |
| **Total** | **142** | |

**How this relates to the legacy 122-row matrix.** QA & Validation re-verified all 150 rows of
`docs/validation/FEATURE_MATRIX.md` against an automated-check rule and moved 12 rows from
`VERIFIED` to `PARTIAL` (their evidence was code-reading, not a test) and `PY-08` to `MISSING`.
Their headline is **16 of 122 in-scope features verified (13.1 %)**. The two numbers are not in
conflict: the legacy matrix verifies *narrower brief-aligned rows*, this catalogue scores *broader
capabilities*, and a broader capability is only `implemented` when the whole of it is
demonstrated. Both are published; neither is rounded up.

**The seven `broken` capabilities** — the ones that must be fixed before anything else:

> **Status update (2026-10-26):** this table is the audit's point-in-time record. Six of the seven
> were closed before it was published (`PY-10`, `PY-08`, `AD-04`, `LV-05`, `IM-06`, `IM-12`), and
> `PY-03` closed on 2026-10-26 when approved time and leave began driving the calculation. The
> current status of record is `docs/product/FEATURE_MATRIX.md`: **0 capabilities are broken.**

| ID | Capability | The defect |
|---|---|---|
| `PY-10` | Payroll refuses without a verified pack | `rule_pack_not_verified` does not exist in the backend; `process` persists payslips unconditionally |
| `PY-03` | Approved time and leave reach payroll | `_calculate_payslips` reads components and profiles only |
| `PY-08` | Explicit currency and pay-period semantics | `base_salary` is per pay period; the offer letter says annual |
| `AD-04` | Role-based permissions, scoped authorisation | `require_roles` is dead code; three ad-hoc role checks |
| `LV-05` | Approved time and leave handoff to payroll | same gap as `PY-03` |
| `IM-06` | Dry run, row errors, token bound to the result hash | the commit path reports `created=N` and writes nothing |
| `IM-12` | Salary units defined explicitly | import schema and offer letter imply annual |

**Not verified (evidence unavailable, not "absent"):** the production schema alignment claim
(`/health/schema` requires authentication), the Oracle behaviour of the migrations, any load
characteristic, and the behaviour of the 259 served operations against a real Oracle schema.

---

## 7. The ten highest-priority risks

| # | Risk | Severity | Evidence | Mitigation |
|---|---|---|---|---|
| **R1** | **Payroll is not gated by rule packs.** A pay run calculates and persists payslips for a jurisdiction with no verified pack, and the matrix claimed the opposite. | Critical | `grep rule_pack_not_verified backend/` → no match; `payroll.py` has 0 rule-pack references; `smoke_test_all_phases` "9. process pay run" → `total_gross == 50000` | `PR-01` — the gate before any payroll work. Until it exists, payroll stays disabled by configuration, not by code. |
| **R2** | **The role model is not enforced.** `Manager` and `PayrollViewer` are documented and enforced nowhere; role checks are three ad-hoc comparisons. | Critical | `require_roles` has no importer outside `deps.py` | `PS-05` — apply `require_roles` everywhere, delete the ad-hoc comparisons, one negative test per role × endpoint |
| **R3** | **Six of eight lanes have work that exists only as uncommitted files in a shared directory.** | Critical | `git status` in the primary checkout; six lanes' paths | `SUP-03` — one worktree and one branch per agent and per issue; every lane's work lands as a branch with a gate |
| **R4** | **There is no staging.** `main` deploys to production. A commit is a release. | Critical | `render.yaml` `autoDeployTrigger: commit`; no staging service exists | `SUP-04` — a staging Render service on the reserved second Oracle database; promotion is a human step |
| **R5** | **The import commit path reports success and writes nothing**, and writes a false row to the audit trail. | Critical | `import_export.py` — `stored_entity, report, _ = _dry_run_store.pop(...)`, then a status rewrite and `created += 1` | `DI-01` — fix and test the two-step flow end to end |
| **R6** | **CI is red.** The secret scan fails the build with 11 findings, so nothing can merge and no green run can be cited. | High | `ci/secret_scan.py` → exit 1, 11 findings | `PS-02` — allowlist the nine distinct local test values with reasons; no rule weakened, no path excluded |
| **R7** | **The audit trail cannot answer the questions an incident asks.** No hash chain, no source address, no lockout transition, no row for an unknown username. | High | `audit_logs` has no address column; no `login_blocked_locked` row exists | `PS-03`, `PS-04` — same-transaction guarantee, hash chain, source address, the two missing events |
| **R8** | **The pilot gate cannot be assessed.** 10 of 12 journeys, no staging, no load harness, axe not in CI, the mobile Playwright project matches a spec that does not exist. | High | `npx playwright test` → "10 passed"; `playwright.config.ts` `testMatch: /responsive\.spec\.ts/` with no such file; no load script in the repo | `QA-01`…`QA-05` — the journeys, the load harness, axe in CI, the responsive spec, the harness concurrency fix |
| **R9** | **The published credential is committed to the repository** as a plain-text denylist entry. | High | `ci/secret_scan.py` | `PS-07` — store SHA-256 digests instead; same detection, no credential in the tree |
| **R10** | **The contract describes a different product.** 210 served endpoints are undeclared; 125 operations are `planned`; the import fragment's shape contradicts the implementation. | Medium | `check_openapi_drift.py` → 210 undeclared; `grep -c "x-lifecycle: planned"` → 125 | `SUP-02` — triage by domain in dependency order; each owner declares its endpoints and promotes them in the same change request |

### Two process risks that are not product risks but will still sink the programme

| # | Risk | Severity | Evidence | Mitigation |
|---|---|---|---|---|
| **R11** | **The coordination record was silently overwritten.** `agents/DECISIONS.md` was replaced by another lane's file before a `git add agents/` staged it; the coordinator's DEC-000…DEC-011 record was never committed. | High | `git show 0ed1376:agents/DECISIONS.md` is a design-decisions file | `SUP-04` — restore the record; agents write only their own folder; stage exact paths, never `agents/` wholesale |
| **R12** | **The CI gate is not trustworthy in a shared checkout.** `ci/run_backend_tests.sh` deletes `backend/*.db` before each suite, so two concurrent runs destroy each other's databases and fail with `attempt to write a readonly database`. | High | Platform & Security hit it three times; the failing suite changes per run; isolated runs are 17/17 twice | `QA-05` — per-suite database paths outside the shared directory, and a lock |

---

## 8. The state of the branches

| Branch | Base | Commits | Merge order | Gate |
|---|---|---|---|---|
| `agent/platform-security/ps-02-secret-scan-allowlist` | `agents/super/board-2026-10-21` | `5bd0950` | **1st** | No rule weakened; the eleven values allowlisted with reasons. Verified by the agent: 17 suites / 549 checks in isolation. |
| `agent/platform-security/ps-01-production-reset-guard` | the PS-02 branch | `53d23f7` | **2nd** — merging it first conflicts on the branch point | Fails closed without an explicit acknowledgement; 44 checks; each new check confirmed to fail with the behaviour reintroduced. |
| `agent/onboarding-config/OC-01-preset-schema-and-graph` | `agents/super/board-2026-10-21` | **none** | — | Nothing to merge. |
| Six uncommitted lanes | the primary checkout | — | — | **Not mergeable.** Each needs a branch, a handoff and a gate. |

---

## 9. Recommended minimum viable pilot — **Proposed**

**The pilot is a security-and-workflow pilot for one customer, not a product launch.**

### In scope

| Capability | Why it is in |
|---|---|
| `AD-04` role enforcement | the product's access model has to be real before anyone uses it |
| `AD-07` audit trail | the customer has to be able to prove what happened |
| `PY-10` + `PY-03` + `PY-08` + `PY-09` payroll gate, inputs and units | pay is the reason a customer buys HCM; the "configurable calculation" label is only honest if the gate exists |
| `IM-06`, `IM-07`, `IM-12` import commit, idempotency and salary units | the customer's data enters through this door; a commit that writes nothing is indefensible |
| `CF-01`, `CF-09`, `CF-11` presets, readiness check, resumable setup | the first hour of the customer's life |
| `HR-01`, `HR-03`, `HR-06` employee master, effective-dated history, org chart | the record everything else hangs off |
| `LV-01`, `LV-02`, `LV-03` leave types, requests, ledger | the first workflow a manager uses |
| `TM-01`, `TM-03` time capture and overtime inputs | feeds the payroll input |
| `UX-01`, `UX-03`, `UX-08`, `UX-09` role homes, self-service, responsive, states | the experience the customer sees |
| `AD-04`, `AD-10`, `AD-01` role enforcement, diagnostics, branding | operability |

### Explicitly excluded

| Excluded | Why |
|---|---|
| **Any statutory payroll claim** | no verified India pack exists; there is no named verifier. Payroll ships in a "requires configuration" state and says so. |
| **Scheduling and forecasting** (`SC-*`, `AN-03`…`AN-06`) | the solver does not exist; a roster that cannot satisfy a hard constraint is worse than no roster |
| **AI of every tier** (`AI-*`) | the controls do not exist. AI lands after the controls, not with them. |
| **Multi-jurisdiction rule packs** | one jurisdiction, one verifier, if that |
| **Recruitment beyond requisitions and offers** (`RC-04`, `RC-06`, `RC-07`) | interview infrastructure is a project of its own |
| **Data subject export, erasure, retention** (`HR-12`, `AD-09`) | **included, not excluded** — they are a legal exposure. They are Phase 1 work, and until they exist the product must not be sold on a promise of compliance. |
| **Marketing site, SSO/SCIM/e-signature integrations, multi-entity** | deferred with reasons already recorded at Gate 0 §3.3 |

### The pilot gate — **Proposed, unchanged in substance from Gate 0**

1. No open Critical or High defect.
2. Every in-scope capability `implemented`, with evidence links.
3. Every one of the journeys J1–J14 passes **on staging**.
4. A load smoke result against the free tier's actual limits.
5. A rehearsed backup and restore, recorded.
6. DEC-000 closed and recorded by the owner.
7. The payroll refusal demonstrated on staging: a pay run for a jurisdiction with no verified pack
   returns `rule_pack_not_verified` and writes nothing.
8. A written go or no-go.

---

## 10. What could not be assessed

| Item | Why | Consequence |
|---|---|---|
| The CI status of `main` | no `gh`, private repository, API 404 | the local reproduction is used; a green CI run is still uncited |
| The open pull requests | same | the merge queue is built from branches, not from GitHub |
| The Oracle behaviour of the migrations | no Oracle connection available to this audit | the migration suite runs on SQLite; `ORA-12838`, `ORA-01408` and `ORA-01400` remain known landmines |
| Load and performance | no harness exists | no budget can be set from a measurement |
| The behaviour of 259 operations against the real schema | `/health/schema` needs authentication; no staging | the schema-alignment claim rests on the agent's live check, not on a measurement I could repeat |
| Backup and restore | no script exists | the pilot gate cannot be met |
| Whether the deployed production commit is `70a8745` | the deployment carries no version identifier | **production may be running something other than `main`** |

---

## 11. Phase 0 exit gate — status

| Required | Status |
|---|---|
| Verified repository and agent inventory | **Done** — §2, §3 |
| Baseline test and build results | **Done** — §4, `commands_run.md` |
| Security and incident status | **Done** — §5; DEC-000 closed as a vulnerability, open as a gate |
| Existing-versus-target feature matrix | **Done** — `docs/product/FEATURE_CATALOG.md` and `docs/product/FEATURE_MATRIX.md` |
| Architecture and dependency map | **Done** — `docs/audit/UPGRADE_PLAN.md` §3 |
| Proposed task breakdown with effort ranges and parallelisation | **Done** — `docs/audit/UPGRADE_PLAN.md` §5, `agents/TASK_BOARD.md` |
| Open decisions requiring human approval | **Done** — `agents/DECISIONS.md`, `agents/ESCALATIONS.md` |
| A recommendation for the smallest safe pilot | **Done** — §9 |

**Phase 0 is complete. No application code was modified. The plan is waiting for the owner's
approval.**

---

*No credential, token, key, personal identifier or customer datum appears in this report. The
production actions described in §5 were performed by the Platform & Security agent and are
disclosed there with their side effects.*
