# Contract: Karmathy Phase 0 Implementation Plan

**Feature ID:** karmathy-phase-0-implementation-plan
**Contract path:** spec/features/karmathy-phase-0-implementation-plan/contract.md
**Tier:** Tier 1 (data model, money/payroll, auth, public contracts — Zero-Decision Rule violations)

## Acceptance Criteria (numbered)

**AC-01** Data tenancy strategy explicitly decided (shared schema with tenant discriminator recommended). 
**AC-02** Technology stack confirmed (FastAPI retained, Spring Boot rejected with evidence).
**AC-03** All subjective qualifiers replaced with concrete values ("reasonable", "strong default", "sensible", "appropriate", "where applicable").
**AC-04** Every acronym expanded on first use (HCM, OIDC, OAuth2, RBAC, REST, API, UI, SSO, MFA, CSRF, XSS, SSRF, TLS, VPD, RLS, SLA, WCAG, CI, CD).
**AC-05** Definition of Done made concrete and testable per feature with measurable pass/fail criteria (Section 19.3).
**AC-06** Document made self-contained or external dependencies explicitly listed.
**AC-07** "Alternatives Considered" section added with per-module trade-off rationales.
**AC-08** Consolidated "Risks & Mitigations" section added mapping failure modes to mitigations.
**AC-09** Phase 0 discovery documents created: docs/AS_IS_ASSESSMENT.md, docs/GAP_ANALYSIS.md, docs/TARGET_ARCHITECTURE.md, docs/DECISION_LOG.md, docs/IMPLEMENTATION_PLAN.md.
**AC-10** All Phase 0 documents committed to `main` and verified.

## Test Plan

1. `cd /Users/srinivas/LLM/Workforce/Karmathy/frontend && npm run typecheck && npm run build` — must pass
2. Backend test suite — must pass all suites via `ci/run_backend_tests.sh` (canonical test command; `python3 -m pytest` is not the canonical runner)
3. Verify all 5 Phase 0 documents exist in `docs/`
4. Verify no Tier 1 decisions left TBD in the requirements document

## Scope confirmations

**Billing scope (D1):** In scope now — Build payment integrations, billing, and subscription management as part of this phase. (The prior contract draft carried billing as "[PENDING billing scope decision]"; that pending item is closed by this decision.)

## Open Decisions (for lead/human)

**AC-01 Tenancy conflict:** docs/coordination/GATE_0_DECISIONS.md §1.1 already decided "one Oracle schema per customer" (schema-per-tenant), while AC-01 recommends shared schema with tenant discriminator. Must be reconciled; record winner in DECISION_LOG.md.
**AC-02 Spring Boot rejection:** Rationale must cite repository evidence (existing FastAPI codebase, Oracle driver support).
**AC-03 Concrete qualifier replacements:** Specific values replacing "reasonable", "strong default", etc. must be agreed with the lead.
**Test runner mismatch:** Resolved (D2). `ci/run_backend_tests.sh` is the canonical test command; the repo runs standalone `*_test_suite.py` scripts through it. No pytest conftest needed.
