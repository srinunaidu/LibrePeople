# Karmathy HCM — Gap Analysis (Phase 0 discovery baseline)

**Date:** 2026-11-06 · **Owner:** Super Agent · **Branch:** `feature/karmathy-phase-0-gap-analysis` (base commit `3850614`) · **Status:** Draft for EGM review

**Purpose.** Compare the `HCM_SaaS_Agent_Requirements.md` requirements (the baseline for repository assessment, implementation planning, delivery and validation — requirements doc §1, line 5-6) against the deployed Karmathy codebase. This document answers EGM review Comprehension Finding 1 (Major): "the existing system is never described." It is one of the five Phase 0 discovery documents required by contract AC-09 and requirements doc §1.2 (lines 69-83), and it supports contract AC-01 through AC-08.

**Sources of record used**
- `HCM_SaaS_Agent_Requirements.md` (repo root) — the requirements baseline; line numbers cited below refer to this document.
- `docs/product/FEATURE_MATRIX.md` — capability status of record: **28 of 143 capabilities implemented (19.6%)**, 59 partial, 56 missing, 0 broken (counts table, lines 25-32). Headline at line 34.
- `docs/product/FEATURE_LINKAGES.md` — dependency atlas; "two foundations" (AD-04 RBAC, AD-07 audit chain) at lines 21-46; payroll dependency tree at lines 74-102; sequencing rules at lines 376-384.
- `STATUS.md` — phase tracker; 9-phase tracker at lines 35-47; domain tracker at lines 169-187; defect tracker at lines 195-199.
- `INFO.md` (verdict) — **does not exist in this repository.** No consolidated verdict document was found, so no verdict line can be cited; the FEATURE_MATRIX headline (line 34) and STATUS.md §1 counts are used as the de facto status verdicts.

> Data-quality observation: the two status-of-record documents disagree by one capability. `FEATURE_MATRIX.md` counts table (lines 25-32) records 28 implemented / 59 partial / 56 missing. `STATUS.md` §4 domain tracker (lines 169-187) records 28 done / 58 partial / 57 missing. The discrepancy (one capability shifted between partial and missing) is unresolved and should be reconciled before either document is cited as the single source of truth.

---

## 1. Executive summary / headline verdict

| Measure | Value | Source |
|---|---|---|
| Capabilities implemented | 28 / 143 (19.6%) | `FEATURE_MATRIX.md` lines 27, 34 |
| Capabilities partial | 59 | `FEATURE_MATRIX.md` line 28 |
| Capabilities missing | 56 | `FEATURE_MATRIX.md` line 30 |
| Broken capabilities | 0 | `FEATURE_MATRIX.md` line 29 |
| Backend suites / checks | 33 suites, 4,172 checks, 0 failed | `STATUS.md` line 21 |
| Security (role matrix) checks | 1,779, 0 failed | `STATUS.md` line 22 |
| Served API operations | 259 | `FEATURE_MATRIX.md` HR-12 evidence (line 60) |
| Migration head | `0026_employment_history`, 28 migration versions | `STATUS.md` line 28; `backend/migrations/versions/` (28 files) |
| Production | Render, free plan, `STORAGE_BACKEND=local`, `JOB_WORKER_ENABLED=false` | `render.yaml` lines 8, 29; `backend/app/core/config.py` lines 95, 112 |
| Data tenancy strategy | **Not decided / not implemented** | No `tenant_id` on tenant-owned models; `TENANT_ID="default"` hardcoded |

**Top-line gap:** The requirements envision one deployed multi-tenant product serving many isolated tenants (§2 Product Vision, lines 92-111; §4 Tenant Model and Isolation, lines 255-335). The codebase is a **single-tenant deployment** with no tenant discriminator on tenant-owned entities, no tenant-context resolution in authentication/authorization, and a hardcoded default tenant. Every requirement that presupposes multi-tenancy (tenant isolation, provisioning, entitlements, per-tenant configuration, cross-tenant negative tests) is therefore unimplemented at the data layer, even where the feature surface exists.

**Second top-line gap:** The requirements demand concrete, testable, evidence-backed decisions (data tenancy, technology stack, Definition of Done, acronym expansion, subjective-qualifier removal). None of these is currently recorded as a concrete decision; they are the open decisions tracked in contract §46-48 (Open decisions) and contract AC-01 to AC-08.

---

## 2. Method

Each requirements section was read end-to-end (1,286 lines). For each section I recorded:
1. What the requirement says (with line numbers).
2. What the codebase actually does (with file:line references).
3. The gap status: `Implemented`, `Partial`, `Missing`, or `Architectural (Zero-Decision Rule violation)`.

The per-domain analysis in §3 maps requirements domains to the `FEATURE_MATRIX.md` capability IDs (HR-, RC-, OB-, TM-, LV-, SC-, PY-, BN-, PM-, LN-, AN-, UX-, AD-, CF-, IM-, AI-). The architectural-gap analysis in §4 addresses the contract's Tier 1 "Zero-Decision Rule" concerns (tenancy, stack, DoD). §5 covers production concerns. §6 audits acronym expansion (AC-04) and subjective qualifiers (AC-03) so the requirements-document edits can be traced.

---

## 3. Per-domain gap analysis

Each row cites the requirements section, the FEATURE_MATRIX capability IDs and status, and the codebase evidence. Statuses use the FEATURE_MATRIX vocabulary (`implemented` / `partial` / `missing`) plus `architectural` where the gap is a missing decision rather than missing code.

### 3.1 Product vision & multi-tenancy (§2, lines 90-154)

| Requirement (line) | Codebase reality | Gap |
|---|---|---|
| One product serves many independent tenants; tenant differences via configuration/entitlements, not customer-specific code (lines 92-111) | Single-tenant deployment. `backend/app/models/user.py` `User` has no `tenant_id` (lines 16-152). `backend/app/api/deps.py` resolves identity from JWT but never resolves a tenant (lines 130-152). `backend/app/imports/config.py` hardcodes `TENANT_ID: str = "default"` (line 73); `imports/runner.py:249` and `imports/progress.py:80` write everything under that one tenant. | **Architectural — Zero-Decision Rule violation.** No tenancy strategy decided; no tenant discriminator on tenant-owned entities (AC-01). |
| Tenant data/configuration/files/jobs isolated; never expose one tenant's data to another (requirements §1.1 line 58-59; §4.3 lines 293-304) | Visibility is employee-scoped, not tenant-scoped: `backend/app/core/visibility.py` scopes by reporting line / global roles (lines 54-108). No cross-tenant negative tests exist (requirements §4.3 line 306; §19.2 scenario 4-7 lines 1037-1041). | **Missing.** Cross-tenant isolation unenforced at the data layer; no automated cross-tenant negative tests. |
| Super Admin access to tenant employee data denied by default, granted only via explicit time-bound purpose-recorded support access with audit (line 309-311) | `AD-04` RBAC makes SuperAdmin/HR global readers (`visibility.py:44` `GLOBAL_ROLES`). No support-access / time-bound / purpose-recorded model found. | **Missing.** |

### 3.2 Tenant lifecycle & provisioning (§4.1-4.2, lines 257-291)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Tenant states Draft / Provisioning / Active / Suspended / Read-only / Deprovisioning / Archived; transitions permissioned, audited, validated (lines 259-269) | No tenant model or lifecycle state machine found. `CF-11` (ten-step onboarding journey) is `missing` (FEATURE_MATRIX line 163); `AD-01` tenant setup/branding is `partial` (line 143) — settings endpoint + `logo_url` exist but no tenant-facing branding screen. | **Missing.** |
| Idempotent provisioning; retry without duplicates (lines 290-291) | Import idempotency exists (`IM-07`, implemented, FEATURE_MATRIX line 173) but that is data import, not tenant provisioning. No tenant provisioning retry/idempotency path found. | **Missing.** |

### 3.3 Data tenancy strategy (§4.4, lines 315-335) — AC-01 (contract)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Explicitly decide one of: shared schema + tenant discriminator; schema-per-tenant; database-per-tenant; hybrid (lines 317-324) | **No decision recorded in code or docs.** `GATE_0_DECISIONS.md` §1.1 (docs/coordination) decided "one Oracle schema per customer" (schema-per-tenant) — but that is a coordinator decision, not a requirements-document decision, and it conflicts with AC-01's recommendation of shared schema + tenant discriminator. The application code assumes exactly one tenant per deployment (`TENANT_ID="default"`), so neither option is actually implemented. | **Architectural — Zero-Decision Rule violation (AC-01 open).** Contract open decision (contract §46): reconcile GATE_0 with AC-01 and record the winner in `DECISION_LOG.md`. |
| Every tenant-owned entity must have a tenant key + composite constraints/indexes; evaluate Oracle VPD/RLS (lines 331-335) | Only `backend/app/models/imports.py:96` has a `tenant_id` column. No other tenant-owned model carries a tenant key. No VPD/RLS or equivalent row-level enforcement found. | **Missing.** |

### 3.4 Technology direction (§3.2, lines 180-235) — AC-02 (contract)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Backend: "Existing backend if maintainable; otherwise Java Spring Boot is a strong default" (lines 195-198) — subjective "strong default" must be replaced with a concrete decision backed by repository evidence | Backend is FastAPI 0.111.0 / Python 3.11 / SQLAlchemy 2.0.29 / Pydantic 2.7.4 / oracledb thin (contract §24/Interfaces). No Spring Boot code exists in the repository. Rejection of Spring Boot is not yet documented with repository evidence (existing FastAPI codebase, team skills, Oracle driver support). | **Decision outstanding (AC-02).** Must record FastAPI-retained decision with repository evidence, not preference. |
| Frontend: React / Next.js; retain existing React framework if sound (lines 186-188) | Frontend is React 18 + Vite + Tailwind (contract §24). Retained; consistent with requirement. | Implemented (retained). |
| Hosting: existing Render initially; production suitability assessed; free tier not assumed production-grade (lines 228-230, 249-251) | `render.yaml` deploys backend on Render **free** plan (line 8), `STORAGE_BACKEND=local` (line 29 — ephemeral `/tmp`), single region Singapore, `healthCheckPath: /health`. `config.py:112` defaults `STORAGE_BACKEND=local`. | **Partial / production concern.** Free tier + ephemeral storage contradict §3.3 lines 241, 249-251. See §5. |

### 3.5 Product catalogue, modules & feature entitlements (§5, lines 339-446)

| Requirement | Codebase reality | Gap |
|---|---|---|
| 30-domain module catalogue (lines 362-391); module/feature/tenant-config as three separate concepts (lines 341-354) | `CF-01`..`CF-14` presets/config are largely implemented (FEATURE_MATRIX lines 153-166); `AD-02` module entitlements exists as data but frontend does not consume it for navigation (line 144); `AD-05` workflow/approval configuration `missing` (line 159). | **Partial.** Catalogue metadata per capability (line 400-414) not fully present; entitlement enforcement at backend exists for 250 operations (`AD-04`, FEATURE_MATRIX line 146) but frontend navigation not gated by flags (`AD-02`, line 144). |
| Feature dependency engine explicit, machine-readable, validated by backend (lines 416-431) | `FEATURE_LINKAGES.md` is the dependency atlas (manually maintained), not machine-readable backend validation. `CF-02` module dependency graph enforced in code (FEATURE_MATRIX line 154) covers presets only. | **Partial.** |

### 3.6 Configuration inheritance & versioning (§6, lines 449-493)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Hierarchy Platform Defaults → Industry Template → Country/Localization Pack → Tenant Configuration → Tenant Override (line 455) | `CF-14` default-vs-tenant-vs-override tracking implemented (FEATURE_MATRIX line 166). Full 5-layer inheritance not confirmed implemented. | **Partial.** |
| Versioned templates, diff/impact preview, draft/validate/preview/publish/rollback, atomic publish (lines 462-477) | `CF-09` setup validations/readiness implemented (line 161); draft/publish/rollback lifecycle not confirmed end-to-end. | **Partial.** |
| Configuration schema governance; typed schemas; reject unknown fields (lines 481-490) | Presets validate against schema (`CF-01`, line 153); broader typed-schema governance not confirmed. | **Partial.** |

### 3.7 Configuration Studio UI (§7, lines 496-552)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Super Admin Configuration Studio with 17 navigation areas (lines 503-523) | Admin pages exist (App.tsx lines 35-60+: IntegrationsHub, DataQuality, UserAdmin, TenantBranding, ModuleEntitlements, WorkflowApproval, IntegrationCredentials, BackupRestore, FeatureFlags, LocaleConfig, RetentionExport, etc.), but no evidence all 17 areas are wired or that preview/publish/rollback works. | **Partial.** |
| Every configuration area: view/draft/validate/preview/publish/rollback/export-import (lines 526-539) | Readiness check writes nothing (`CF-09`, line 161); full pattern not confirmed per area. | **Partial.** |

### 3.8 Metadata-driven UI (§8, lines 555-606)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Tenant config controls UI variations without separate frontend build (lines 557-560) | Not implemented; frontend is a compiled SPA. | **Missing.** |
| Target WCAG 2.2 AA accessibility; keyboard navigation, focus, labels, contrast, screen-reader (lines 587-589) | `axe-core` runs over 20 pages in CI (`QA-04`, FEATURE_MATRIX UX-08 line 140); `UX-08` notes "no manual keyboard or screen-reader pass has been made." | **Partial.** |
| "sensible defaults and progressive disclosure" (line 590-591) — subjective qualifier (AC-03) | Not a concrete value. | **Needs concrete value (AC-03).** |

### 3.9 Workflow engine (§9, lines 610-652)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Configurable workflow engine; 14 initial workflows (lines 615-648) | `AD-05` workflow/approval configuration `missing` (FEATURE_LINKAGES line 159; FEATURE_MATRIX line 147). Admin `WorkflowApproval` and `ApprovalWorkflows` pages exist (App.tsx lines 40, 50) but no backend workflow runtime confirmed. | **Missing.** |
| Workflow configuration must not allow unauthorized approval paths or bypass segregation of duties (lines 650-651) | Segregation of duties exists for payroll approval (`PY-05`, FEATURE_MATRIX line 100) but no general workflow SoD enforcement. | **Missing.** |

### 3.10 Business rules engine (§10, lines 655-676)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Typed, testable rules; no arbitrary code execution; payroll/statutory require deterministic reviewed logic (lines 673-676) | `PY-09` jurisdiction rules partial (FEATURE_MATRIX line 104); demo pack refused (rates in prose). `PY-10` generic calc separated from verified statutory (implemented, line 105). | **Partial.** Rule engine exists only in payroll; not a general configurable rules capability. |

### 3.11 Roles, permissions & data access (§11, lines 680-711)

| Requirement | Codebase reality | Gap |
|---|---|---|
| 11 named roles + tenant-defined roles (lines 684-695) | 5 roles: SuperAdmin, HR, Manager, Associate, PayrollViewer (`deps.py:79-82`). No tenant-defined roles. | **Partial.** |
| Server-side enforcement on every API and background operation; deny by default; never UI visibility as security boundary (lines 708-710) | `require_roles` on every endpoint (`deps.py:263-274`); 250 protected + 4 public operations; security_test_suite 1,475 checks (FEATURE_MATRIX AD-04 line 146). Background jobs: worker exists (`PS-11`, STATUS line 67) but tenant context on jobs not confirmed. | **Implemented for API role gating; Partial for background jobs / tenant-defined roles.** |

### 3.12 HCM functional coverage (§12, lines 714-852)

Mapped to FEATURE_MATRIX domain tracker (STATUS.md lines 169-187):

| Domain (req §12) | Cap IDs | Total | Implemented | Partial | Missing | Gap summary |
|---|---|---|---|---|---|---|
| Organization & workforce foundation (§12.1) | HR- | 12 | 0 | 8 | 4 | Employee master partial (no emergency-contact model, no employee-number uniqueness — HR-01 line 49); grades/job-families absent (HR-04 line 52); custom fields missing (HR-08 line 56); contingent workers missing (HR-10 line 58); DSAR/retention/erasure missing (HR-12 line 60) |
| Recruitment & hiring (§12.2) | RC- | 8 | 1 | 4 | 3 | Requisitions partial (no approval/budget — RC-01 line 61); interview/scorecards missing (RC-04 line 64); candidate comms missing (RC-06 line 66); funnel analytics missing (RC-07 line 67) |
| Pre-boarding & onboarding (§12.3) | OB- | 7 | 0 | 3 | 4 | Resumable checklist partial (OB-01 line 69); equipment/access/training tasks missing (OB-03 line 71); probation missing (OB-04 line 72); transfers/promotions missing (OB-05 line 73); rehire missing (OB-07 line 75) |
| Core HR / employee lifecycle (§12.4) | HR- | (see above) | | | | Effective-dated history partial (HR-03 line 51 — begins at HR-12, no backfill); documents expiry/acknowledgement missing (HR-07 line 55) |
| ESS & MSS (§12.5) | UX-03, UX-04 | | | | | ESS partial (profile/leave/time/payslips exist; sensitive-field masking absent — UX-03 line 135); manager views partial (UX-04 line 136) |
| Time, leave, shifts, workforce (§12.6) | TM-, LV-, SC- | TM 5 / LV 5 / SC 10 | LV 2 implemented | TM 3 partial, LV 2 partial, SC 2 partial | TM 2, LV 1, SC 8 | No attendance-policy model (TM-02 line 77); no break model (TM-01 line 76); flat overtime with no rule/multiplier/cap (TM-03 line 78); hard/soft scheduling constraints missing (SC-04/SC-05 lines 89-90); coverage computation missing (SC-07 line 92) |
| Payroll, comp & benefits (§12.7) | PY-, BN- | PY 10 / BN 6 | PY 2, PY 10 implemented | PY 7 partial, BN 2 partial | BN 4, PY 07 missing | Payroll calculation not rule-pack-driven (PY-02 line 97); no currency model (PY-08 line 103); bank export missing (PY-07 line 102); no contribution/claim endpoint (BN-02 line 107) |
| Talent & engagement (§12.8) | PM-, LN- | PM 6 / LN 7 | 0 implemented | PM 3 partial, LN 2 partial | PM 3, LN 5 | No competency endpoint (PM-03 line 113); no improvement-plan endpoint (PM-04 line 114); no skills endpoint (LN-04 line 121) |
| Employee relations & HR services (§12.9) | BN-04 | | | | BN-04 partial | Cases exist; no SLA/assignment/escalation field (BN-04 line 109) |
| Separation, offboarding & alumni (§12.10) | OB-06, OB-07 | | | | OB-06 partial, OB-07 missing | Final settlement not linked to payroll (OB-06 line 74); no rehire endpoint (OB-07 line 75) |

### 3.13 Notifications (§13, lines 855-874)

| Requirement | Codebase reality | Gap |
|---|---|---|
| In-app / email / SMS; templates; event-based; delivery status/retry; tenant sender identity; preferences/opt-out; audit | `UX-05` notification centre partial — `/ess/notifications` (+read) exists; no preference model (FEATURE_MATRIX line 137). `AD-06` webhooks/deliveries partial (line 148). No email/SMS provider integration confirmed. | **Partial.** Notification preference model and provider integrations missing. |

### 3.14 Integrations & API platform (§14, lines 877-891)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Versioned REST APIs with OpenAPI; webhooks with signing/retries/replay; integration credentials stored securely; idempotency keys; rate limits; integration health/status; audit of data exchanged; no secrets in frontend bundles/logs/repo | `/platform/webhooks` (+deliver, deliveries), `/platform/sso-configs`, `/platform/integrations` exist but no API-credential issuance (AD-06 partial, FEATURE_MATRIX line 148). Idempotency keys exist (`IdempotencyRecord`, main.py line 85). Rate limit on `/public/contact` (UX-10 line 141). `ci/secret_scan.py` runs (PS-02, STATUS line 59). `.env.example` contains placeholder secrets (names only, consistent with AC-06 spirit). | **Partial.** API-credential issuance, webhook signing/replay protection, and integration health status not confirmed implemented. |

### 3.15 Reporting & analytics (§15, lines 894-921)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Tenant-scoped reporting; configurable dashboards; saved reports/filters; export permissions/audit; scheduled reports; clear metric definitions & freshness; no cross-tenant aggregation unless authorized | `AN-01`..`AN-08` mostly partial (FEATURE_MATRIX lines 125-132). `/reports/*` return synchronously; no report job, export format, dashboard-per-role (AN-08 line 132). Metric lineage not modelled (AN-02 line 126). | **Partial.** Scheduled reporting, exports, role-based dashboards missing. |

### 3.16 Security, privacy & compliance (§16, lines 924-947)

| Requirement | Codebase reality | Gap |
|---|---|---|
| TLS in transit, encryption at rest (line 928) | TLS referenced but no evidence of enforced min version / HSTS config detail beyond `SecurityHeadersMiddleware` (main.py line 68). | **Partial.** |
| MFA and SSO support (line 930) | MFA mandatory for SuperAdmin/HR (`deps.py:199-218`, `mfa_test_suite.py` exists). SSO: `/platform/sso-configs` exists but no IdP integration confirmed (OIDC/OAuth2 not implemented — auth is local JWT). | **Partial (MFA yes; SSO no).** |
| CSRF, XSS, injection, SSRF protections (line 932) | `security_headers_test_suite.py` exists; input validation in import; formula-injection neutralisation (`IM-05` partial, FEATURE_MATRIX line 171). | **Partial.** |
| Audit logs protected from unauthorized alteration (line 937) | Hash-chained audit chain implemented (AD-07, FEATURE_MATRIX line 149); DB triggers refuse UPDATE/DELETE (DEC-027); `verify_audit_chain` exits 0. | **Implemented.** |
| Data retention, legal hold, deletion workflows (line 938) | `AD-09` retention/export/erasure missing (FEATURE_MATRIX line 151); `IM-10` upload retention missing because nothing schedules `purge_expired_uploads` (FEATURE_MATRIX line 176, FEATURE_LINKAGES line 124). | **Missing.** |
| Backup & restore procedures (line 939) | `AD-08` backup/restore verification missing — no backup or restore script; `STORAGE_BACKEND=local` means documents lost on redeploy (FEATURE_MATRIX line 150). | **Missing.** |

### 3.17 Database & data architecture (§17, lines 951-982)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Tenant key on tenant-owned records; FKs preventing cross-tenant relationships; composite indexes (lines 959-962) | No tenant key on tenant-owned models (only imports.py:96). Alembic migrations versioned (28 versions, head 0026). | **Missing (tenant key); Implemented (migration tooling).** |
| Oracle Free/Always Free limitations assessed; paid-upgrade path recorded (lines 979-981) | render.yaml free plan; no documented capacity limits or paid-upgrade path found. | **Missing.** |

### 3.18 Performance & scalability (§18, lines 985-1008)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Stateless instances; background processing; queue-based bulk imports/payroll/notifications/reports; idempotent jobs; rate limits; load tests; capacity thresholds | Job queue with leases/backoff/dead-letter (AD-07, FEATURE_MATRIX line 149); worker off by default (`JOB_WORKER_ENABLED=False`, config.py:95). Load smoke harness built but not executed on staging (QA-03, STATUS line 99). No published capacity thresholds. | **Partial.** Load tests not executed; worker opt-in means queued work may not run in production. |

### 3.19 Quality engineering & testing (§19, lines 1012-1075)

| Requirement | Codebase reality | Gap |
|---|---|---|
| 13 test layers (lines 1016-1031) | 33 backend suites, 4,172 checks (STATUS line 21); security 1,779 checks; frontend verify green; 70 browser tests. Tenant isolation / cross-tenant negative tests NOT written (QA-07 partial, STATUS line 102). | **Partial.** |
| Critical acceptance scenarios 1-18 (lines 1032-1059) | Not executed as a suite; scenarios 4-7 (cross-tenant retrieval) and 15 (provisioning retry) cannot run without tenancy. | **Missing (blocked by tenancy decision).** |
| Definition of Done §19.3 (lines 1061-1075) | Qualitative checklist: "Working UI, Server-side validation, Authorization, Tenant isolation, Persistence, Audit where appropriate, Error and empty states, Automated tests, Documentation, Accessibility review, Evidence of successful execution." No measurable pass/fail criteria (e.g. "% of endpoints with server-side validation", "cross-tenant negative test count", "accessibility scan exit code"). | **Architectural — AC-05 gap.** DoD is not concrete or testable per feature. |

### 3.20 Deployment & environment strategy (§20, lines 1079-1111)

| Requirement | Codebase reality | Gap |
|---|---|---|
| Separate environments local/shared-dev/test/staging/prod (lines 1083-1088) | Local (SQLite), Staging (KARMA_STAGE Oracle), Production (Render) (STATUS line 6). No shared-dev/test/QA distinct environments documented. | **Partial.** |
| CI pipeline lint/typecheck/tests/security/build; CD to non-prod; prod requires authorization (lines 1091-1094) | GitHub Actions CI (contract §27); secret scan; OpenAPI drift checks. Deployments to Render occur (STATUS §7 deploy log) but authorization gating not documented. | **Partial.** |
| Render free-plan suitability verified (persistent storage, background workers, outbound Oracle access, connection limits, sleep behaviour) (lines 1106-1110) | `STORAGE_BACKEND=local` (ephemeral) on free plan; `JOB_WORKER_ENABLED=False` default; no documented verification of sleep/connection limits. | **Missing — production risk (see §5).** |

### 3.21 AI capabilities (§8 AI rows in FEATURE_MATRIX, lines 179-192)

| Requirement | Codebase reality | Gap |
|---|---|---|
| 13 AI capabilities (AI-01..AI-13) + mandatory controls landing with first Tier A | All 13 `missing` (FEATURE_MATRIX lines 179-192). No AI code, no controls. `AI-12` controls must land with first Tier A, not after (FEATURE_LINKAGES sequencing rule 6, line 383). | **Missing (by design — Phase 8 pending, STATUS line 45).** |

---

## 4. Architectural gaps — Zero-Decision Rule violations

The contract classifies Tier 1 risk as "data model, money/payroll, auth, public contracts — Zero-Decision Rule violations" (contract §39). Four gaps are decisions that have **not** been explicitly made and recorded:

### 4.1 Data tenancy strategy (AC-01) — most significant

**Violation:** Requirements §4.4 (lines 315-335) require an explicit tenancy decision, but none exists in the requirements document or as an implemented architecture. `GATE_0_DECISIONS.md` §1.1 decided schema-per-tenant (one Oracle schema per customer), which conflicts with AC-01's recommended shared-schema-with-tenant-discriminator. The codebase assumes exactly one tenant (`TENANT_ID="default"`, `backend/app/imports/config.py:73`), so neither option is implemented.

**Evidence in code:**
- `backend/app/models/user.py` — `User` has no `tenant_id` (lines 16-152).
- `backend/app/api/deps.py` — identity from JWT; no tenant resolution (lines 130-152).
- `backend/app/core/visibility.py` — employee-scoped visibility, not tenant-scoped (lines 54-108).
- `backend/app/models/imports.py:96` — the only `tenant_id` column in the codebase.

**Required decision (contract AC-01):** shared schema with tenant discriminator (recommended), with schema-per-tenant / database-per-tenant / hybrid compared and rejected with rationale. Record in `DECISION_LOG.md`, reconcile with GATE_0 (contract open decision §46).

### 4.2 Technology stack (AC-02)

**Violation:** §3.2 line 198 leaves Spring Boot as a "strong default" — a subjective qualifier requiring a concrete evidence-backed decision. FastAPI is retained in the codebase but the retention decision is not recorded with repository evidence.

**Required decision:** Confirm FastAPI retained; document rejection of Spring Boot citing repository evidence (existing FastAPI codebase, 28 migrations, SQLAlchemy/oracledb thin, team tooling), not preference. Record in `DECISION_LOG.md`.

### 4.3 Definition of Done (AC-05)

**Violation:** §19.3 (lines 1061-1075) is a qualitative checklist with no measurable pass/fail criteria per feature.

**Required decision:** Replace with concrete, testable criteria (e.g. "% of endpoints with server-side validation", "cross-tenant negative test count", "accessibility scan exit code", "migration up/down round-trip exit code"). Record per-feature DoD.

### 4.4 Subjective qualifiers (AC-03)

**Violation:** Subjective qualifiers remain: "reasonable" (§1 line 49), "strong default" Spring Boot (§3.2 line 198), "sensible defaults" (§8 line 590). Each must be replaced with a concrete, verifiable value agreed with the lead.

---

## 5. Production concerns

These are operational risks observable in the deployed codebase, independent of the Phase 0 decision work:

| # | Concern | Evidence | Severity |
|---|---|---|---|
| P1 | **Ephemeral storage on production.** `STORAGE_BACKEND=local` writes documents/offer letters to `/tmp/karmathy-storage` (`config.py:112-113`, `render.yaml:29`). Render free tier has an ephemeral filesystem; redeploy loses uploads. Contradicts §3.3 line 241 ("Avoid depending on ephemeral local filesystem storage"). | `render.yaml` line 29; `config.py` lines 112-113; `main.py` lines 90-96 | High |
| P2 | **Background worker off by default.** `JOB_WORKER_ENABLED=False` (`config.py:95`). Large imports answered 202 "queued" may never be applied; retention (`IM-10`) not scheduled. | `config.py:95`; `main.py` lines 104-158; FEATURE_MATRIX IM-10 line 176 | High |
| P3 | **Render free tier for production.** Single region (Singapore), free plan, no documented verification of sleep behaviour, persistence, backups, connection limits, support guarantees (§20 lines 1106-1110). | `render.yaml` lines 8-9 | High |
| P4 | **Hardcoded seeded admin passwords in source.** `main.py` lines 199-205 seed `retail_superadmin` / `retail_hradmin` with plaintext passwords on startup. | `main.py` lines 178-229 | High |
| P5 | **No tenant isolation at data layer.** Any future multi-tenant deployment would expose all data to all tenants until a tenant key + row-level enforcement is added. | `models/user.py`; `deps.py`; `visibility.py` | Critical (blocked by 4.1) |
| P6 | **No backup/restore script.** `AD-08` missing; documents lost on redeploy. | FEATURE_MATRIX AD-08 line 150 | High |
| P7 | **No scheduled retention.** `purge_expired_uploads` exists but nothing enqueues `retention_run` periodically. | FEATURE_MATRIX IM-10 line 176; FEATURE_LINKAGES line 124 | Medium |
| P8 | **Cross-tenant negative tests not written.** QA-07 partial (STATUS line 102); §19.2 scenarios 4-7 cannot run without tenancy. | STATUS line 102 | Medium (blocked by 4.1) |

---

## 6. Acronym & subjective-qualifier audit (supports contract AC-03 / AC-04)

This audit is provided so the requirements-document edits (contract AC-03, AC-04) can be traced to specific lines.

### Acronyms NOT expanded on first use (AC-04 gaps)

| Acronym | First use (line) | Context | Expanded? |
|---|---|---|---|
| HCM | 1 | Title "HCM SaaS Platform" | No |
| OIDC / OAuth2 | 207-208 | §3.2 "OIDC/OAuth2-compatible identity provider" | No |
| RBAC | 211 | §3.2 "Server-enforced RBAC plus tenant/data scope" | No |
| REST | 879 | §14 "Versioned REST APIs documented with OpenAPI" | No |
| TLS | 928 | §16 "TLS in transit and encryption at rest" | No |
| VPD / RLS | 333 | §4.4 "Evaluate Oracle VPD/RLS or equivalent controls" | No |
| SLA | 830 (§12.9) | "Service catalogue, SLA and escalation" | No |
| WCAG | 587 | §8.3 "Target WCAG 2.2 AA accessibility" | No |
| CI / CD | — | Not found as expanded acronym; "CI pipeline" §20 line 1092 | Not expanded |

### Subjective qualifiers requiring concrete values (AC-03 gaps)

| Qualifier | Line | Context | Needed |
|---|---|---|---|
| "reasonable" | 49 | "Make reasonable engineering decisions autonomously when the evidence is sufficient." | Specific decision thresholds |
| "strong default" | 198 | "Java Spring Boot is a strong default" | Concrete stack decision + evidence |
| "sensible defaults" | 590 | §8.3 "provide sensible defaults and progressive disclosure" | Named defaults / values |
| "appropriate" | 935 | §16 "malware scanning integration where available" | Defined availability criteria |
| "compelling" | 160 | §3.1 "unless repository evidence demonstrates a compelling reason otherwise" | Evidence bar defined |

---

## 7. Traceability: requirement → code → gap

| Requirements section | Lines | Key code files | Status |
|---|---|---|---|
| Product vision / multi-tenancy | 90-154 | `backend/app/models/user.py`, `deps.py`, `imports/config.py` | Missing (architectural) |
| Tenant lifecycle/provisioning | 257-291 | None (no tenant model) | Missing |
| Data tenancy strategy | 315-335 | `models/imports.py:96` only tenant column | Missing decision (AC-01) |
| Technology direction | 180-235 | `backend/app/main.py` (FastAPI), no Spring Boot | Decision outstanding (AC-02) |
| Module/feature entitlements | 339-446 | `backend/app/api/deps.py` (require_roles), `CF-*` presets | Partial |
| Configuration inheritance | 449-493 | `CF-01`..`CF-14` presets | Partial |
| Configuration Studio | 496-552 | `frontend/src/pages/admin/*` | Partial |
| Metadata-driven UI | 555-606 | Not implemented | Missing |
| Workflow engine | 610-652 | `AD-05` missing | Missing |
| Business rules engine | 655-676 | `PY-09`/`PY-10` payroll only | Partial |
| Roles/permissions/data access | 680-711 | `deps.py`, `visibility.py`, `security_test_suite.py` | Implemented (API), Partial (jobs/tenant roles) |
| HCM functional coverage | 714-852 | `FEATURE_MATRIX.md` domain rows | Partial overall (28/143) |
| Notifications | 855-874 | `UX-05`, `AD-06` | Partial |
| Integrations/API platform | 877-891 | `/platform/webhooks`, `IdempotencyRecord` | Partial |
| Reporting/analytics | 894-921 | `AN-*`, `/reports/*` | Partial |
| Security/privacy/compliance | 924-947 | `audit` chain, `security_test_suite.py`, `mfa_test_suite.py` | Implemented (audit/MFA), Partial (SSO/backup/retention) |
| Database/data architecture | 951-982 | 28 Alembic migrations | Implemented (migrations), Missing (tenant key) |
| Performance/scalability | 985-1008 | Job queue, worker off by default | Partial |
| Quality engineering/testing | 1012-1075 | 33 suites, 4,172 checks | Partial (DoD not measurable — AC-05) |
| Deployment/environments | 1079-1111 | `render.yaml`, `docker-compose.yml` | Partial (free tier, ephemeral storage) |

---

## 8. Conclusion

The deployed Karmathy codebase is a well-engineered, well-tested **single-tenant** HCM application (FastAPI backend, React frontend, Oracle ADB target, Alembic migrations, hash-chained audit, RBAC on 250 operations, job queue, import pipeline). Its gaps relative to `HCM_SaaS_Agent_Requirements.md` are not primarily missing screens — they are **missing decisions and missing data-layer foundations**:

1. **No data tenancy strategy is decided or implemented** (AC-01) — this is the blocking Zero-Decision Rule violation. Every multi-tenant requirement (§2, §4, §19.2 scenarios 4-7) depends on it.
2. **The technology stack retention vs Spring Boot is not recorded with repository evidence** (AC-02).
3. **The Definition of Done is a qualitative checklist, not measurable per feature** (AC-05).
4. **Subjective qualifiers remain** ("reasonable", "strong default", "sensible defaults") (AC-03) and **acronyms are not expanded on first use** (AC-04).

Until the tenancy decision is recorded and the shared-schema (or alternative) discriminator is implemented, no cross-tenant negative test, tenant provisioning, per-tenant entitlement, or per-tenant configuration can be meaningfully validated. This gap analysis is intended to feed `DECISION_LOG.md`, `TARGET_ARCHITECTURE.md`, `AS_IS_ASSESSMENT.md`, and `IMPLEMENTATION_PLAN.md`, and to inform the requirements-document edits required by contract AC-01 through AC-08.
