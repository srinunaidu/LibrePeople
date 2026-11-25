# Governance Hierarchy — Release Record

Source: `Blocker PRD.rtf` v1.0 Review draft. Status: NOT READY. This file records hierarchy only; recommendations only, no approval claimed.

## Decision hierarchy (highest first)

1. Law / safety / statutory compliance.
2. Owner approvals (explicit, recorded).
3. PRD / scope (what is INCLUDE vs DEFER vs PENDING).
4. Architecture / security decisions.
5. Verified implementation (independent check, not author claim).
6. Docs / research (supporting evidence only).
7. Agent judgement (lowest; never overrides above).

## Key rules

- Lower level cannot override higher.
- Newer supersedes older only if authorised and explicit.
- Tests passing cannot override gates or scope decisions.
- Code existing is not proof of correctness.
- Recommendation ≠ approval.
- Implementation ≠ verification.
- Inferred ≠ owner-decided.

## GOV-001..060 reference

GOV-001..010 hierarchy and precedence; GOV-011..020 scope and PRD control; GOV-021..030 owner approvals; GOV-031..040 verification and gates; GOV-041..050 security and architecture; GOV-051..060 docs, research, and agent limits. Full text in PRD source; this file is an index, not a restatement.

## Decision matrix

- Routine / autonomous: typo fixes, formatting, read-only evidence gathering, draft recommendations.
- Approval-gated: scope INCLUDE/DEFER, gate pass/fail, release, deployment, residency, payroll sign-off, any override of a higher level.

## Acceptance criteria

1. Source pinned to PRD v1.0 Review draft.
2. Seven levels recorded in order.
3. Seven key rules recorded verbatim in intent.
4. GOV-001..060 index present.
5. Matrix distinguishes routine from approval-gated.
6. No approval claimed in this file.
7. No scope changed by this file.
8. No gate overridden by this file.
9. Content under 400 words.
10. Docs-only change.
11. Committed on `feature/librepeople-production`.
12. Release gate recorded as NOT READY.

Release gate: NOT READY.
