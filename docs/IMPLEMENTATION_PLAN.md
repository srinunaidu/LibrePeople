# Karmathy HCM — Phase 0 Implementation Plan

**Status:** proposed (discovery baseline; no code or schema change)  
**Date:** 2026-11-06  
**Branch:** `feature/karmathy-phase-0-implementation-plan`  
**Base commit:** `3850614` (`Add production seed script and load data into Oracle production database`)  
**Repo:** `/Users/srinivas/LLM/Workforce/Karmathy`  
**Contract:** `spec/features/karmathy-phase-0-implementation-plan/contract.md`

This document is the Phase 0 implementation plan for Karmathy HCM. Phase 0 is discovery and decision recording only (contract Non-goals): it records pre-determined architectural decisions, sequences delivery into Blocks 0–9, defines per-phase exit gates, makes the Section 19.3 Definition of Done concrete and measurable, and records rollback procedures. It mutates no application code, no database schema, no production data, and no credentials.

It is one of the five Phase 0 discovery documents (`AS_IS_ASSESSMENT.md`, `GAP_ANALYSIS.md`, `TARGET_ARCHITECTURE.md`, `DECISION_LOG.md`, `IMPLEMENTATION_PLAN.md`) required by contract AC-09.

---

## 1. Purpose and scope

The purpose of this plan is to bring Karmathy HCM into compliance with the EGM review findings and the Zero-Decision Rule: **no architectural or delivery decision is left TBD at the start of build work**. Every structural choice below is either already decided in `docs/coordination/GATE_0_DECISIONS.md` (Gate 0, approved 2026-10-19) or explicitly carried forward from `docs/audit/UPGRADE_PLAN.md` (proposed, awaiting owner approval) and `docs/product/FEATURE_LINKAGES.md` (the dependency atlas).

Scope of this document:
- Phase 0 plan only: Blocks 0–9 (GATE_0_DECISIONS §3.1–3.4).
- No application code, database schema, or migration changes (contract Non-goals).
- No production deployment, DNS change, credential rotation, or paid cloud cost (contract Non-goals).
- No Phase 1–6 delivery implementation.

Scope intentionally deferred or pending:
- **Billing scope** for payroll execution is `[PENDING billing scope decision]` and is not decided in this phase. See Section 7.
- The tenancy conflict between contract AC-01 (shared schema with tenant discriminator recommended) and Gate 0 §1.1 (schema-per-tenant already decided) is reconciled in Section 4 and recorded in `DECISION_LOG.md`; this plan implements the Gate 0 decision (schema-per-tenant).

---

## 2. Zero-Decision Rule compliance

The Zero-Decision Rule requires that every architectural decision be pre-determined before build work begins, so that no lane pauses for a decision mid-block. This plan treats the following as **frozen, pre-determined decisions**. None is TBD. No lane may re-open them without a written change request to the coordinator (GATE_0_DECISIONS §2, change-request rule) and, for Tier 1 items, owner approval.

| # | Decision | Value | Source | Tier | Status |
|---|----------|-------|--------|------|--------|
| D1 | Data tenancy | One Oracle Autonomous Database; one Oracle **schema per customer** (`DB_SCHEMA` config, not code) | GATE_0 §1.1 | 1 | Decided |
| D2 | Backend framework | **FastAPI retained** (0.111.0, Python 3.11, SQLAlchemy 2.0.29, Alembic, Pydantic 2.7.4, oracledb thin mode) | Contract §Interfaces/data; GATE_0 §3.2 tech table implied | 1 | Decided |
| D3 | Spring Boot | **Not adopted.** Rejection backed by repository evidence (existing FastAPI codebase, team skills, Oracle driver support), not preference | Contract AC-02; GATE_0 §3.2 direction table | 1 | Decided |
| D4 | Execution capacity | One engineer, 20–40 h/week, single lane | GATE_0 §1.2 | 1 | Decided |
| D5 | First launch jurisdiction | **India.** Payroll ships disabled until a rule pack is verified by a named human | GATE_0 §1.4 | 1 | Decided |
| D6 | Launch business presets | `retail`, `construction`, `hospitality`, `healthcare_clinic`, `light_manufacturing`, `generic_office` | GATE_0 §1.3 | 2 | Decided |
| D7 | External LLM | **No.** Default build has no LLM call; configuration assistant is a rule engine | GATE_0 §1.5 | 2 | Decided |
| D8 | Forecasting/ML | Statistical methods only (`statsmodels` Holt-Winters, `ortools` CP-SAT, `numpy`/`pandas`); no gradient-boosted or neural models | GATE_0 §1.6 | 2 | Decided |
| D9 | Default admin credential | Rotated; no default password anywhere; forced password change; secret scan in CI | GATE_0 §1.7 | 1 | Decided |
| D10 | Rule-pack lifecycle | `draft` → `pending_verification` → `verified` → `superseded`; `verified` only by named human against cited source with golden case | GATE_0 §1.4, CR-001 | 1 | Decided |
| D11 | Cross-tenant `tenant_id` scoping | **Deferred.** Deployment model is one customer per deployment; schema-wide tenancy unnecessary | GATE_0 §3.3 | 3 | Decided (deferred) |
| D12 | Monorepo migration | **Deferred.** 3–5 ew of tooling churn, no user-visible value | GATE_0 §3.3; UPGRADE_PLAN DEC-013 | 3 | Decided (deferred) |
| D13 | Billing scope for payroll | **[PENDING billing scope decision]** — not decided in Phase 0 | This plan §7 | 2 | Open (pending) |

Compliance evidence:
- Every decision above cites its source (Gate 0, contract, or this plan's pending register).
- No Tier 1 decision (tenancy, stack, payroll gating, auth) is left TBD.
- Decisions D1–D10, D12 are recorded as decided in `DECISION_LOG.md`; D11 and D13 are recorded as deferred/open with rationale.

---

## 3. Data tenancy = schema-per-tenant (decision D1)

**Decision (Gate 0 §1.1):** one Oracle Autonomous Database instance, one Oracle schema per customer. A schema is an Oracle user with its own tables, so a customer's data is physically separated from another customer's without a second database.

**Why schema-per-tenant and not the alternatives:**

| Option | Isolation | Free-tier customers | Migrations | Extra capacity | Verdict |
|--------|-----------|---------------------|------------|----------------|---------|
| Schema-per-tenant (chosen) | Table-level, enforced by schema owner | unlimited | schema-qualified | second free DB = headroom for staging or noisy tenant | **Adopted** |
| Database-per-tenant | Instance-level | capped at **2** | instance-qualified | none | Rejected: caps product at 2 customers with no room for staging |
| Shared schema + tenant discriminator | Row-level via application filter + optional VPD/RLS | unlimited | shared | shared | Rejected for Gate 0: cross-tenant queries possible by mistake; conflicts with one-customer-per-deployment model |
| Hybrid (shared + dedicated enterprise) | Mixed | unlimited | mixed | mixed | Rejected for Gate 0: operational complexity not justified at pilot scale |

**Consequence:** the application points at a different schema per deployment via `DB_SCHEMA` — a configuration concern, not a code concern, because a deployment serves exactly one customer. Cross-tenant queries remain impossible by construction: there is no tenant dimension in any query, because there is only ever one tenant in the database. Schema qualification in the migration runner is **Block 3** work; nothing in Block 1 or 2 depends on it (CR-003).

**Reconciliation with contract AC-01:** AC-01 recommends shared schema with tenant discriminator and asks schema-per-tenant, database-per-tenant, and hybrid to be compared and rejected with rationale. Gate 0 §1.1 already decided schema-per-tenant with the comparison above. The lead/owner must reconcile Gate 0 with AC-01 before the requirements document is finalized; the winning option (schema-per-tenant) and its rationale are recorded in `DECISION_LOG.md` (contract Open decisions). This plan implements schema-per-tenant.

---

## 4. Technology stack = FastAPI retained (decision D2/D3)

**Backend:** FastAPI 0.111.0, Python 3.11, SQLAlchemy 2.0.29, Alembic, Pydantic 2.7.4, Oracle Autonomous Database via `oracledb` thin mode, JWT access/refresh, standalone test suites (`backend/*_test_suite.py` run via `ci/run_backend_tests.sh`) (contract §Interfaces/data).

**Frontend:** React 18 + TypeScript + Vite 5 + Tailwind v3 + Radix + TanStack Query/Table/Virtual, npm scripts (`typecheck`, `build`, `verify`, Playwright) (contract §Interfaces/data).

**CI:** GitHub Actions (`.github/workflows/ci.yml`); secret scan (`ci/secret_scan.py`); OpenAPI merge/drift checks (contract §Interfaces/data).

**Spring Boot rejection rationale (evidence-based, per contract AC-02):** The repository's backend is an existing, maintained FastAPI codebase (154 endpoints, 67 tables, 5 roles per PHASE0_AUDIT.md) with SQLAlchemy/Alembic migrations and `oracledb` thin-mode Oracle support already in place. Rewriting to Spring Boot solely to match a preference would discard working code, migrations, tests, and the Oracle driver integration, and is not justified by any repository evidence of a problem with FastAPI. Spring Boot is therefore **not adopted**. Any future rejection of the retained stack must cite repository evidence (codebase, skills, driver support, license/cost), not preference.

---

## 5. Phased plan — Blocks 0–9 (aligned with GATE_0_DECISIONS §3.1–3.4)

Effort in engineer-weeks at 30 productive hours each. **Cumulative** is the point at which the pilot gate can be assessed. Confirmed capacity is one engineer at 20–40 h/week (Gate 0 decision D4); at that rate the full sequence is roughly 5–11 months (GATE_0 §3.1: 16–52 months solo for the brief's three lanes, compressed to one sustainable lane here). The brief's 7-week, three-lane schedule is **not achievable** and is replaced by this sequence (GATE_0 §1.2, §3.1).

Phases reference `docs/audit/UPGRADE_PLAN.md` (its own 0–9 phase plan, S/M/L/XL effort units) and `docs/product/FEATURE_LINKAGES.md` (the dependency atlas). Where the two plans differ in block boundaries, this plan is authoritative for Phase 0 sequencing; UPGRADE_PLAN remains the source for effort units and the dependency graph.

| Block | Scope | Effort | Cumulative | Exit gate (must be met before next block) |
|-------|-------|--------|------------|-------------------------------------------|
| **0** | Gate 0 decisions, contracts, credential rotation, Alembic baseline, CI gate | done | 0 | Credential rotated; CI green |
| **1** | Security foundation: password policy, MFA, refresh rotation, lockout, field encryption with key versions; central policy module; visibility on every read; ownership checks on every write; real `Manager` and `PayrollViewer` roles; HSTS/CSP; CORS allow-list | 4–6 ew | 4–6 | Negative tests for every module; role enforcement on every endpoint |
| **2** | Data layer: index every foreign key and filter column; paginate every list; transaction boundaries; idempotency keys; Oracle schema qualification (`DB_SCHEMA`) | 1.5–2 ew | 5.5–8 | Schema matches models; migration round-trip verifies |
| **3** | Audit: hash chain, append-only, verification CLI | 1 ew | 6.5–9 | Chain verifies |
| **4** | Background jobs (database queue, leases, retry, dead-letter); storage on OCI; CSV import engine (dry run, confirmation token, idempotent upsert, worker) | 3–4 ew | 9.5–13 | Import round-trips; import commit actually commits |
| **5** | Onboarding state machine, presets, configuration-assistant rules, retention and erasure, data subject export | 2.5–3.5 ew | 12–16.5 | Setup is resumable; DSAR/erasure path exists |
| **6** | Workforce core: effective-dated history, leave ledger, overtime rules, working-time checks, consent records, equal-opportunity data separation | 3–4 ew | 15–20.5 | Every calculation traceable |
| **7** | Scheduling solver, forecasting, payroll engine, rule-pack loader (India; payroll disabled until verified pack) | 4–6 ew | 19–26.5 | Payroll refuses without a verified pack |
| **8** | Reports, compliance outputs, role-based homes, module UI, generated API client, statutory filings | 3–4 ew | 22–30.5 | Role homes read real data; pilot gate assessed at end of Block 8 |
| **9** | E2E journeys, accessibility, load and failure tests, validation reports | 2–3 ew | 24–33.5 | 12 journeys pass on staging; all evidence published |

**Pilot gate** is assessed at the end of Block 8 (GATE_0 §3.2): the pilot needs working payroll *inputs*, a usable interface, and the compliance view — not a complete marketing site or a monorepo migration. Pilot criteria (GATE_0 §6): every coverage-matrix row shows true status; all 12 E2E journeys pass on staging; security negative tests pass for every endpoint; no open Critical/High defects; load smoke meets feasibility targets; backup/restore rehearsal completed and recorded; India rule packs verified and signed off by a named professional **or payroll is disabled for the pilot**; a written go or no-go.

**Deliberately deferred (GATE_0 §3.3):** monorepo migration, Astro marketing site, Storybook, Tailwind v4 + Style Dictionary, full role-aware routing beyond five role homes, multi-jurisdiction rule packs beyond India, cross-tenant `tenant_id` scoping, SSO/SCIM/e-signature/background-check integrations, SOC 2 / ISO 27001. Each is deferred with a reason, not silently dropped, and each has a revisit trigger.

**What "production ready" means here (GATE_0 §3.4):** the brief's definition adopted unchanged, made concrete — (a) no statutory value outside a rule pack; a pack may only be `verified` by a named human against a cited source with a golden case, until then the affected module is disabled and says why; (b) a feature that is not ready is removed from navigation and behind a disabled flag — it never appears as a visible dead option.

---

## 6. Per-phase exit gates

Each exit gate is a concrete, measurable precondition. A block is not complete — and the next block does not start — until its gate is met and recorded.

| Block | Exit gate (measurable) |
|-------|------------------------|
| **0** | CI green (`ci/run_backend_tests.sh` exits 0; `npm run typecheck && npm run build` exit 0); default admin credential rotated and absent from docs/code; `DB_SCHEMA` config mechanism documented; Alembic baseline migration present and applies cleanly to a scratch schema. |
| **1** | `require_roles` applied to every endpoint (zero ad-hoc role comparisons); one negative test per role × endpoint (security_test_suite, 1,475 checks) passes; MFA, password policy, forced change, refresh rotation, lockout enforced; field encryption with key versions for banking/national identifiers; HSTS and CSP headers set; no open Critical/High defects. |
| **2** | Every foreign key and filter column indexed; every list paginated; transaction boundaries defined; idempotency keys on mutating endpoints; migration test suite (`migration_test_suite`, `schema_drift_test_suite`, `schema_alignment_test_suite`) passes; Oracle schema qualification compiles and applies to a scratch schema. |
| **3** | Hash-chained, append-only audit log; audit record in same transaction as mutation; `python -m scripts.verify_audit_chain` (or `scripts/verify_audit_chain`) passes; verification CLI present and runnable. |
| **4** | Database-backed job queue with leases, retry, dead-letter; OCI object storage path configured; CSV import engine streams parse with row/byte caps; IM-06 dry run + confirmation token bound to result hash; IM-07 idempotent upsert on natural keys; `import_test_suite` passes; import commit actually writes (counts match the database; audit row matches). |
| **5** | Onboarding state machine resumable (checkpoint + resume); presets versioned and schema-validated; configuration-assistant rules each have positive + negative test; retention/erasure and data-subject export path exists; setup can be re-run without duplicates (retry provisioning → no duplicates). |
| **6** | Effective-dated history on employee/comp/pay records; leave ledger is sum of signed balance transactions; overtime with multipliers and caps, traceable to a rule; working-time checks with violation records; every calculation has a traceable audit row. |
| **7** | Scheduling solver (ortools CP-SAT) with hard constraints; forecasting (statsmodels Holt-Winters) with reported accuracy; payroll engine separates generic calculation (PY-10) from verified statutory rule (PY-09); rule-pack loader enforces `draft` → `verified` and refuses pay run for jurisdiction without a verified pack (`422 rule_pack_not_verified`, writes nothing); golden cases present for India. |
| **8** | Reports and compliance outputs generated; role-based homes (Associate, Manager, HR, PayrollViewer, SuperAdmin) read real data; generated API client present; statutory filings/returns outputs present; payroll inputs usable end-to-end; coverage matrix shows true status with no row marked passing without verification. |
| **9** | All 12 E2E journeys pass on staging; accessibility scan (axe-core) exit code 0 in CI on target pages; responsive verification (mobile/tablet, 360 px up); load smoke meets feasibility targets; failure/recovery tests pass; validation reports published; written go/no-go recorded. |

Exception rule (UPGRADE_PLAN §9 / GATE_0 §5): a lane that discovers a requirement that would break a contract, a security rule, or the 512 MB free-tier memory budget stops and raises a change request (`REVAMP_NOTES.md` + commit message) before implementing any alternative.

---

## 7. Payroll execution scope

Payroll execution scope (Block 7, gated by Block 1 role enforcement and Block 3 audit) covers the following capabilities. Statutory values are never written into code; all come from a verified jurisdiction rule pack (India first; disabled until verified by a named human).

| Capability | ID | Scope | Gate |
|------------|----|-------|------|
| Run approval / lock | PY-04 | Run lifecycle Draft → Processing → Approved → Finalized → Paid; segregation of duties (processor ≠ approver); finalized → payslips read-only, immutable history | PY-10 gate, AD-07 audit |
| Corrections | PY-05 | Historical record + controlled correction; correction traceable to approver and rule | PY-04, AD-07, DB triggers |
| Proration | PY-03/PY-04 | Approved time/leave inputs feed payslip trace; proration derived from approved inputs and effective-dated pay components | PY-01/PY-02/PY-03 |
| Currency | PY-08 | Explicit currency + pay-period semantics (salary per pay period, never annual by default); IM-12 salary units explicit | AD-03 (locale/TZ/currency), PY-01 |
| Bank export | PY-07 | Bank export integration — runs only after PY-04 closes approval/lock; cannot be built before the lock loop (FEATURE_LINKAGES payroll tree) | PY-04 |

**[PENDING billing scope decision]:** Billing scope (e.g. invoicing, payment collection, billing cycles, tax remittance integration) is not decided in Phase 0 and is explicitly out of scope for this plan. No payroll billing capability is planned, estimated, or gated here. When a billing decision is made, it must be recorded in `DECISION_LOG.md` before any billing code is scheduled.

Payroll dependency order (FEATURE_LINKAGES payroll dependency tree): verified rule pack (PY-09) → generic calc split (PY-10) → run lifecycle (PY-04) → reconciliation → segregation of duties → finalized lock → payslips → bank export (PY-07). Anything that inverts this order (e.g. bank export before finalized lock) is rejected.

---

## 8. Definition of Done — concrete and measurable (Section 19.3)

Section 19.3 currently lists qualitative items (Working UI, Server-side validation, Authorization, Tenant isolation, Persistence, Audit, Error/empty states, Automated tests, Documentation, Accessibility review, Evidence). This plan makes them concrete with measurable pass/fail criteria, per feature domain. A feature is **done** only when every applicable criterion below passes with evidence (commit + suite result).

### 8.1 Platform & security (applies to all features)

| Criterion | Measurable threshold | Evidence |
|-----------|----------------------|----------|
| Server-side validation | 100% of mutating endpoints have server-side validation; zero mutating endpoints rely on client-only validation | Endpoint audit + `security_test_suite` |
| Authorization | `require_roles` enforced on 100% of endpoints; one negative test per role × endpoint passes | `security_test_suite` (1,475 checks), exit code 0 |
| Tenant isolation | ≥ 1 cross-tenant negative test per tenant-scoped resource; zero cross-tenant data leaks in UI/API/search/exports/reports/files/background jobs | `visibility_test_suite`, critical acceptance scenarios §19.2 #1–#7 |
| Audit | 100% of mutations write to hash-chained append-only trail in the same transaction; `verify_audit_chain` passes | `audit_chain_test_suite`, verification CLI |
| Encryption at rest | Banking and national identifier fields encrypted with versioned, rotatable keys; decryption failure raises (never returns ciphertext) | `security_test_suite`, field-encryption audit |
| Transport & headers | TLS in transit; HSTS and CSP set; CORS allow-list with `allow_credentials` off | `security_headers_test_suite` |
| Secret hygiene | No default password, no credential in docs/code; `ci/secret_scan.py` exit code 0 | secret scan, grep for published credential |

### 8.2 Core HR & workforce (HR-01/02/03/04)

| Criterion | Measurable threshold | Evidence |
|-----------|----------------------|----------|
| Employee master | One record per person; effective-dated changes with history | `employees_test_suite`, `employment_history_test_suite` |
| Lifecycle state machine | Active → On Leave → Terminated → Rehired enforced; termination/rehire guards pass | `hire_test_suite`, `offboarding` flows |
| Org structures | Departments, jobs, positions, cost centres present; FK integrity prevents cross-tenant relationships | `master_data_test_suite` |

### 8.3 Time & leave (TM/LV)

| Criterion | Measurable threshold | Evidence |
|-----------|----------------------|----------|
| Time capture | Clock in/out + breaks + timesheets; cross-midnight + overtime + rounding traceable | `time`-related suites |
| Leave ledger | Ledger-backed balance = sum of signed rows; carry-over and accrual parameters configurable | `leave_test_suite`, `LV-03` |
| Cut-off & lock | Timesheet lock after cut-off; adjustments require approval | `TM-05`, `hire_test_suite` handoff |

### 8.4 Payroll (PY)

| Criterion | Measurable threshold | Evidence |
|-----------|----------------------|----------|
| Rule-pack gate | 100% of pay runs for a jurisdiction refuse (`422 rule_pack_not_verified`, writes nothing) until pack is `verified` by named human with golden case | `payroll_test_suite`, rule-pack loader tests |
| Run lifecycle | Draft → Processing → Approved → Finalized → Paid; segregation of duties enforced | `payroll_test_suite` |
| Corrections | Corrections traceable to approver + rule; immutable history after finalization | `PY-05`, audit rows |
| Proration | Proration derived from approved time/leave inputs and effective-dated components; zero hard-coded statutory rates | `payroll_test_suite`, golden cases |
| Currency | Pay-period salary semantics; currency explicit per pay profile; no annual-by-default | `PY-08`, `IM-12` |
| Bank export | Runs only after finalized lock; export file format validated | `PY-07`, export tests |
| Reconciliation | Expected vs paid reconciled row-by-row per payslip | `PY-04` reconciliation tests |

### 8.5 Import (IM)

| Criterion | Measurable threshold | Evidence |
|-----------|----------------------|----------|
| Dry run + token | Confirmation token bound to result hash, TTL and bound enforced | `import_test_suite` |
| Idempotent upsert | Natural-key idempotency; re-import produces no duplicates | `import_test_suite` (1,800+ assertions) |
| Validation | Type/enum/date/duplicate validation; formula-injection neutralisation | `import_test_suite`, `streaming_parse_test_suite` |

### 8.6 UX & accessibility (UX)

| Criterion | Measurable threshold | Evidence |
|-----------|----------------------|----------|
| Accessibility scan | axe-core automated run in CI exit code 0 on target pages; keyboard pass; responsive (mobile/tablet, 360 px up) | `responsive.spec.ts`, axe-core CI |
| Role homes | Five role homes (Associate, Manager, HR, PayrollViewer, SuperAdmin) read real data; no visible dead options behind disabled flags | `UX-01`, Block 8 gate |
| E2E journeys | All 12 E2E journeys pass on staging | Playwright, Block 9 gate |

### 8.7 Operations

| Criterion | Measurable threshold | Evidence |
|-----------|----------------------|----------|
| CI | Backend suites pass (`ci/run_backend_tests.sh` exit 0; target 33 suites, 4,172 checks, 0 failed); frontend `typecheck` + `build` exit 0 | CI run output |
| Migrations | Versioned Alembic migrations; downgrade verified before release candidate; no manual production schema changes | `migration_test_suite` |
| Backup/restore | Backup/restore rehearsal completed and recorded (pilot criterion) | Rehearsal record |
| Rollback | Documented rollback procedure per release (Section 9) tested in non-production | Rollback runbook |

A feature is marked one of: Implemented and tested / Implemented but not fully tested / Partially implemented / Designed but not implemented / Blocked — requires approval (contract §23). No item is marked complete without evidence.

---

## 9. Rollback procedures

Phase 0 is document-only. Rollback is safe and immediate:

- **Primary rollback:** `git revert` of the commit(s) adding the five `docs/` Phase 0 files and any requirements-document edits, or `git checkout -- <files>` / delete the new docs.
- **No database migration, no data deletion, no DNS or credential change, no paid service** is touched by this phase, so there is nothing to reverse in production or infrastructure.

For later delivery phases (Blocks 1–9), rollback follows the pattern in `docs/audit/UPGRADE_PLAN.md` §7:

| Change | Rollback |
|--------|----------|
| Role enforcement | Revert the dependency; ad-hoc check returns — flag defaults to off for 7 days |
| Payroll gate | The gate stays; the engine is disabled by jurisdiction. A gate is never rolled back. |
| Audit chain | Expand-then-contract; downgrade tested in both revisions; chain is additive |
| Import commit | Commit route returns previous 400 rather than false success |
| Schema changes | Expand-then-contract, always; downgrade verified before release candidate |
| Staging | Deleting the staging service changes nothing in production |
| Frontend shell | Feature-flagged; flip flag back (old shell reachable for two clean pilot weeks) |

**Release-candidate blocking conditions** (UPGRADE_PLAN §7): no release candidate is prepared while DEC-000 is open, any Critical or High defect is open, a Tier 1 security item is open, a migration lacks a verified downgrade, a payroll feature is enabled for a jurisdiction without a verified pack, or the journey suite is red on staging.

---

## 10. Dependencies and cross-references

### 10.1 UPGRADE_PLAN.md (`docs/audit/UPGRADE_PLAN.md`)
- Source of effort units (S/M/L/XL) and the dependency graph (its §3).
- Phase plan (its §2) with a different 0–9 block breakdown; used here for effort calibration, rollout/rollback table (§7), release-candidate blocking conditions, and the first-two-weeks concrete actions (§9).
- Records that phases 1–2 are not optional and not parallelisable, and that the plan change (payroll gate + role model into Phase 1; import commit ahead of presets; staging in Phase 1) is explicitly recorded (§6).
- Status: **proposed — awaiting the owner's approval.** This plan does not adopt UPGRADE_PLAN's phase numbering; it aligns Blocks 0–9 to GATE_0_DECISIONS §3.2 and uses UPGRADE_PLAN for effort units, dependency graph, and rollback patterns.

### 10.2 FEATURE_LINKAGES.md (`docs/product/FEATURE_LINKAGES.md`)
- The dependency atlas (its §147). Source of truth order: FEATURE_CATALOG.md → FEATURE_MATRIX.md → this atlas.
- Two foundations (AD-04 RBAC, AD-07 audit chain, HR-01/02/04 identity tier) — unremovable; any capability claiming "done" without them is `missing` (sequencing rule #2).
- Payroll dependency tree (§Payroll dependency tree): PY-09 → PY-10 → PY-04 → reconciliation → segregation of duties → lock → payslips → bank export (PY-07). PY-07 cannot be built before PY-04 closes approval/lock.
- Import pipeline chain (§Import pipeline dependency chain): IM-01 → … → IM-07 idempotent upsert → IM-08 worker → IM-09 watch/cancel/dead-letter.
- Sequencing rules (§Sequencing rules the atlas encodes): foundations before modules before integrations before AI; AD-04/AD-07 unremovable; missing capabilities with inflow edges get a dependency not a promise; UX-08 closes every UI distinction; AI lands only with its controls (AI-12).
- This plan's Blocks 0–9 respect every atlas edge; no block rips a load-bearing wall out.

### 10.3 Other referenced artefacts
- `docs/coordination/GATE_0_DECISIONS.md` — Gate 0 decisions, Blocks 0–9, coverage matrix, stop conditions, pilot criteria (primary source for this plan).
- `docs/product/FEATURE_MATRIX.md` and `docs/product/FEATURE_CATALOG.md` — capability status of record and target specification.
- `docs/validation/FEATURE_MATRIX.md` — row-level evidence annex (named commits + suites).
- `HCM_SaaS_Agent_Requirements.md` — Sections 3.2 (technology direction), 4.4 (tenancy), 8.3 (guardrails), 16 (security/privacy/compliance), 19.3 (Definition of Done), 22 (delivery plan).
- External dependencies (names only, per contract AC-06): Oracle Autonomous Database, Render, OCI object storage, identity provider (OIDC/OIDC-compatible), rule-pack verifier.

---

## 11. Risks & mitigations

Consolidated mapping (supports contract AC-08). Owners are roles, not named individuals.

| Failure mode | Mitigation | Owner |
|--------------|------------|-------|
| Payroll not gated by rule packs | PY-10 refuses unverified jurisdictions (`422 rule_pack_not_verified`, writes nothing); payroll disabled until India pack verified by named human | Payroll rules lead |
| Role model not enforced | `require_roles` on every endpoint; one negative test per role × endpoint; ad-hoc comparisons deleted | Platform security lead |
| No staging | Staging Render service + second Oracle database built in Block 0/1 (SUP-04), not deferred to release | Super Agent + owner |
| Import commit writes nothing | IM-06 dry run + IM-07 idempotent upsert; counts match database; audit row matches; gate = import round-trips | Data import lead |
| CI red | Secret scan, OpenAPI drift, per-suite suites; no lane merges while CI red (PS-02 first) | CI owner |
| No hash-chain audit | Hash-chained append-only log; verification CLI; `verify_audit_chain` in gate | Platform security lead |
| Uncommitted lane work | One worktree + branch per agent and per issue (SUP-03); nothing merges without handoff and gate | Super Agent |
| Contract drift | Merged OpenAPI is the authority for what code promises; promoted `planned`→`released` via change request; drift check green | Coordinator |
| Tenancy conflict (AC-01 vs Gate 0 §1.1) | Reconciled in DECISION_LOG.md; this plan implements schema-per-tenant | Lead/owner |
| Billing scope undecided | Marked `[PENDING billing scope decision]`; no billing code scheduled until recorded | Owner |

---

## 12. Open decisions / TBD register

Tier 1 decisions: none left TBD (D1–D10 decided; D11, D12 decided-deferred). The only open item is D13, billing scope for payroll execution (`[PENDING billing scope decision]`), which is explicitly deferred and not part of this plan's scope.

The tenancy reconciliation (AC-01 vs Gate 0 §1.1) is recorded as decided in favor of schema-per-tenant here and in `DECISION_LOG.md`, pending lead/owner sign-off on the requirements document.

---

## 13. Acceptance evidence (contract AC-10)

- This document (`docs/IMPLEMENTATION_PLAN.md`) exists in `Karmathy/docs/`.
- Together with `AS_IS_ASSESSMENT.md`, `GAP_ANALYSIS.md`, `TARGET_ARCHITECTURE.md`, and `DECISION_LOG.md`, all five Phase 0 documents are committed to `main`.
- No Tier 1 decision left TBD (D1–D10 decided; D11/D12 decided-deferred; D13 open-pending recorded).
