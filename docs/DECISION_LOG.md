# Decision Log — Karmathy HCM

**Purpose:** Consolidated record of every architectural decision for Karmathy HCM, covering Gate 0 (coordinator) decisions and decisions taken during EGM review remediation. Each decision records date, decision, rationale, alternatives considered, owner, and status.

**Statuses:** `Approved` | `Pending` | `Open (reconciliation required)` | `Superseded`

**Date convention:** ISO 8601 (YYYY-MM-DD).

---

## Gate 0 decisions (coordinator-approved, 2026-10-19)

Source: `docs/coordination/GATE_0_DECISIONS.md` (Gate 0A §1.1–1.7). Owner: Karmathy build coordinator.

### D-01 Tenancy model

| Field | Value |
|-------|-------|
| Date | 2026-10-19 |
| Decision | One Oracle Autonomous Database (ADB) instance; one Oracle schema per customer (schema-per-tenant). Each deployment serves exactly one customer; schema selection is configuration (`DB_SCHEMA`), not code. Cross-tenant queries are impossible by construction: there is no tenant dimension in any query because there is only ever one tenant in the database. |
| Rationale | The Oracle free tier allows two databases. A database-per-customer model would cap the product at two customers with no room for a staging copy. A schema per customer gives physical separation without a second database, keeps the second database free for staging or a noisy tenant, and preserves the isolation property that matters (schema owner enforces table-level isolation). |
| Alternatives considered | - Database-per-tenant: rejected — free tier caps at 2 databases, no staging headroom. <br> - Shared schema with tenant discriminator: not adopted under this Gate 0 decision (reconciliation with contract AC-01 is open — see Notes). <br> - Hybrid schema/database mix: rejected — added complexity with no free-tier benefit. |
| Owner | Karmathy build coordinator |
| Status | Approved (Gate 0). **Open reconciliation item:** contract AC-01 recommends shared schema with tenant discriminator; the lead/owner must reconcile Gate 0 with AC-01 before the requirements document is finalized and record the winning option here. |

### D-02 Business presets

| Field | Value |
|-------|-------|
| Date | 2026-10-19 |
| Decision | Launch business presets: `retail`, `construction`, `hospitality`, `healthcare_clinic`, `light_manufacturing`, `generic_office`. |
| Rationale | As specified in the build brief. Presets are jurisdiction-agnostic. Any field that could only be filled from a jurisdiction rule pack carries the sentinel `REQUIRES_RULE_PACK` and blocks payroll enablement until a verified pack is attached. Enforced by `contracts/rules/preset.schema.json`. |
| Alternatives considered | - Fewer presets (MVP subset): rejected — the build brief specifies the six presets. <br> - Jurisdiction-specific presets at launch: rejected — presets are jurisdiction-agnostic; jurisdiction rule packs are introduced later (India first). |
| Owner | Karmathy build coordinator |
| Status | Approved (Gate 0). |

### D-03 Launch jurisdiction for payroll rule packs

| Field | Value |
|-------|-------|
| Date | 2026-10-19 |
| Decision | India is the first launch jurisdiction for payroll rule packs. Payroll ships disabled until a rule pack is verified by a named human. |
| Rationale | Build brief section 8: the payroll rule packs for the pilot jurisdiction are verified and signed off by a named professional, or payroll is disabled for the pilot. No statutory value is written into the codebase or into any pack from memory. |
| Alternatives considered | - Multiple jurisdictions at launch: rejected — each jurisdiction is a project requiring a named verifier; India is first. <br> - Enable payroll with flat-percentage defaults: rejected — no statutory value outside a verified rule pack. |
| Owner | Karmathy build coordinator |
| Status | Approved (Gate 0). |

### D-04 No external LLM in the configuration assistant

| Field | Value |
|-------|-------|
| Date | 2026-10-19 |
| Decision | No external LLM call in the default build. The configuration assistant is a rule engine over tenant configuration; each rule has an ID, condition, plain-language message, severity, fix target, and positive and negative tests. A curated help index provides fixed answers. |
| Rationale | Avoids sending employee data to an external model, removes a dependency and cost, and keeps behavior deterministic and testable. |
| Alternatives considered | - LLM-powered assistant: rejected for the default build. If LLM mode is ever approved it receives configuration metadata only — never employee rows — and is behind a feature flag that is off by default. |
| Owner | Karmathy build coordinator |
| Status | Approved (Gate 0). |

### D-05 Statistical methods for forecasting

| Field | Value |
|-------|-------|
| Date | 2026-10-19 |
| Decision | Statistical methods only. `statsmodels` for Holt-Winters exponential smoothing, `ortools` (CP-SAT) for the roster solver, and `numpy`/`pandas` for data handling. No gradient-boosted or neural models. |
| Rationale | Follows the build brief's default. A trained model must be versioned, retrained, and explained; none of that is affordable here. Statistical methods are auditable and stateless. |
| Alternatives considered | - Gradient-boosted / neural forecasting models: rejected — model versioning, retraining, and explainability overhead is not affordable. |
| Owner | Karmathy build coordinator |
| Status | Approved (Gate 0). |

### D-06 Default admin credential rotation

| Field | Value |
|-------|-------|
| Date | 2026-10-19 |
| Decision | The default admin credential is rotated, and the rotation is enforced by the code, not by convention. |
| Rationale | The credential that shipped in `backend/scripts/seed_admin.py` and was repeated in `README.md` and `docs/DEPLOYMENT.md` was still authenticating as SuperAdmin against the live production backend when Gate 0 opened. Code enforcement makes it impossible to repeat. |
| Alternatives considered | - Convention-only rotation (documented rule): rejected — conventions are not enforced. <br> - Keep the published credential: rejected — it was authenticating against production. |
| Owner | Karmathy build coordinator |
| Status | Approved (Gate 0). |
| Enforcement | (1) Seed script reads `ADMIN_INITIAL_PASSWORD` from the environment and refuses to run without it; it never prints a password. <br> (2) Forced password change: a seeded or administrator-set account carries `must_change_password` and can only read its own profile, change its password, and sign out; the gate is in `get_current_active_user`. <br> (3) CI secret scan (`ci/secret_scan.py`) fails the build on the published credential, private keys, known token formats, and high-entropy values assigned to secret-looking names; the published credential is denylisted. <br> (4) The credential is removed from documentation; seed instructions show how to generate one. |

---

## EGM review remediation decisions

Decisions taken during EGM review remediation (Phase 0 discovery baseline). Date: 2026-11-06. Owner: Engineering lead (Phase 0 owner).

### D-07 Technology stack

| Field | Value |
|-------|-------|
| Date | 2026-11-06 |
| Decision | FastAPI retained as the backend framework. Spring Boot is not adopted. Frontend remains React 18 + TypeScript + Vite 5 + Tailwind v3 + Radix + TanStack Query/Table/Virtual. |
| Rationale | Repository evidence: the codebase is an existing FastAPI application (154 endpoints, SQLAlchemy 2.0, Pydantic 2, Oracle Autonomous Database via `oracledb` thin mode, JWT access/refresh, Alembic migrations, standalone backend test suites). Retaining FastAPI avoids a rewrite with no user-visible benefit. Any rejection of the retained stack is backed by repository evidence, not preference. |
| Alternatives considered | - Spring Boot: not adopted — no repository evidence favors it over the existing FastAPI codebase; team skills and Oracle driver support favor FastAPI. <br> - Replace FastAPI with another Python framework: rejected — no evidence the current stack is broken; migration cost with no user-visible value. |
| Owner | Engineering lead (Phase 0 owner) |
| Status | Approved. |

### D-08 Definition of Done criteria

| Field | Value |
|-------|-------|
| Date | 2026-11-06 |
| Decision | Definition of Done (Section 19.3) is concrete and testable per feature, expressed as measurable pass/fail criteria rather than qualitative checklist items. |
| Rationale | Replaces subjective qualifiers ("reasonable", "strong default", "sensible defaults", "appropriate", "compelling") with verifiable thresholds so done can be gated in CI and assessed objectively. |
| Alternatives considered | - Qualitative checklist DoD: rejected — not measurable or CI-gateable. <br> - Per-feature measurable pass/fail criteria: adopted. |
| Owner | Engineering lead (Phase 0 owner) |
| Status | Approved. |
| Examples | "% of endpoints with server-side validation", "cross-tenant negative test count", "accessibility scan exit code", "all 12 E2E journeys pass on staging", "no open Critical or High defects", "load smoke meets feasibility-assessment targets". |

### D-09 Billing scope

| Field | Value |
|-------|-------|
| Date | 2026-11-06 |
| Decision | [PENDING] — billing scope not yet decided. No billing model or paid-cloud commitment is made in Phase 0. |
| Rationale | Deferred pending lead/owner confirmation. Phase 0 is discovery and decision recording only; no production deployment or paid cloud cost is introduced. |
| Alternatives considered | None yet — decision pending. |
| Owner | Engineering lead (Phase 0 owner) |
| Status | Pending. |

### D-10 Test runner

| Field | Value |
|-------|-------|
| Date | 2026-11-06 |
| Decision | [PENDING] — test runner not yet decided. |
| Rationale | The repo runs backend suites via `ci/run_backend_tests.sh` (standalone `python suite.py` scripts, not pytest), while the contract test plan cites `python3 -m pytest`. Decide whether to keep `python3 -m pytest` (requires adding pytest discovery/conftest) or substitute `ci/run_backend_tests.sh`, preserving the "33 suites, 4,172 checks" target. |
| Alternatives considered | - `python3 -m pytest` with added discovery/conftest. <br> - `ci/run_backend_tests.sh` (existing per-suite runner). <br> Decision pending lead/owner confirmation. |
| Owner | Engineering lead (Phase 0 owner) |
| Status | Pending. |

---

## Notes

- Gate 0 tenancy decision (D-01) records schema-per-tenant per `docs/coordination/GATE_0_DECISIONS.md` §1.1. Contract AC-01 recommends shared schema with tenant discriminator; the lead/owner must reconcile Gate 0 with AC-01 before the requirements document is finalized. The winning option will be recorded here when decided.
- [PENDING] decisions (D-09 billing scope, D-10 test runner) are intentionally left undecided; no values are invented.
- Phase 0 is document-only: no application code, database schema, migration, production deployment, DNS change, credential rotation, or paid cloud cost is introduced by this log.
