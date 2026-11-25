# Decision Register — HEAD 0b8a402 (`feature/librepeople-production`)

## Surplus — 14 IDs, decision-gated (no phase assigned)
Source: `docs/product/phase-gates.md` surplus table + `release-readiness.json`
`defects_surplus` + `docs/product/acceptance-status.md` §7.
IDs: LP-ADM-005, LP-DATA-002, LP-EXP-001..003, LP-NOT-001..003,
LP-DOC-001..003, LP-SVC-001..003. None may start until product-owner
decisions are recorded.

## INCLUDE (granted)
- NFR-014 (owner decision 2026-11-22): INCLUDE as hardening gate —
  0043 safe C2,C4-C9,C11-C13 + `integrity_quarantine` merged ffad35d;
  C1/C3/C10 deferred application-checked. Harness full pass HEAD 65a1af2;
  promoted IMPLEMENTED → VERIFIED in 2ac4050. CLOSED (implemented).

## DEFER (granted, 8 rows DEFERRED BY APPROVAL)
- Owner mandate: surplus DEFER post-initial, preserve backlog (recorded
  2026-11-22 HEAD 5ce1f003): LP-EXP-001..003, LP-NOT-001, LP-NOT-003,
  LP-SVC-001..003. Implementation suites green where run (expenses 78/0,
  notification 37+53, helpdesk 23+1 failure on 0041 head assertion) —
  proves code, not scope approval. Acceptance N/A while deferred. CLOSED (deferred).

## Pending (OPEN, owned by product owner)
- DOC-003 storage/matrix scope: PENDING (see blocker register, Class A).
- NFR-012 deployment/residency/Cloudflare approvals: PENDING.
- NFR-013 deployment/residency/Cloudflare approvals: PENDING.
- Payroll/compliance verifier (§29): OPEN — FY25-26 pack verified,
  FY26-27 skeleton `pending_verification`, independent verified payroll run
  + sign-off NOT done; PAY never VERIFIED per contract.
- Reviewer open: qualified Indian payroll/statutory specialist
  (LP-COMP-010), licence/dependency reviewer (PRD §26), brand/legal
  clearance, data-migration plan, mobile decision — all OPEN per A11.
- Perf targets: PROPOSED only — `docs/performance/synthetic-10emp.md`
  (b46d24b, synthetic 10-employee SQLite smoke) is a baseline, not acceptance;
  NFR-009/010 load profile unmeasured; NFR-011 RPO/RTO per-profile targets
  documented but unapproved/untested. Status: PROPOSED, acceptance N/A.
- All-lost (full-loss restore / disaster rehearsal): OPEN — no all-lost
  restore proof on this HEAD (backup/restore undemonstrated; ADB restore
  rehearsal legacy only). Blocks recoverability claim; owned by builder to
  rehearse + owner to approve RPO/RTO.
