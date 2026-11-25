# Acceptance harness summary (2026-11-22 HEAD 669e200e1430b25c68c997ade1eda0299972e506)

- mode: full run (gated CSV write)
- in-scope rows: 116 (26 at write time)
- PASS (all legs exit 0): 90
- FAIL retained: 26
- promoted to VERIFIED this run: 90 (LP-ADM-001, LP-ADM-002, LP-ADM-003, LP-ADM-004, LP-AUD-001, LP-AUD-002, LP-AUD-003, LP-AUD-004, LP-COMP-001, LP-COMP-002, LP-COMP-003, LP-COMP-004, LP-COMP-005, LP-COMP-006, LP-COMP-007, LP-COMP-008, LP-COMP-009, LP-COMP-010, LP-COMP-011, LP-COMP-012, LP-CORE-001, LP-CORE-002, LP-CORE-003, LP-CORE-004, LP-CORE-005, LP-CORE-006, LP-CORE-007, LP-CORE-008, LP-CORE-009, LP-CORE-010, LP-DATA-003, LP-DATA-004, LP-DATA-005, LP-DATA-006, LP-DATA-007, LP-ESS-001, LP-ESS-002, LP-ESS-003, LP-ESS-004, LP-ESS-005, LP-ESS-006, LP-INT-001, LP-INT-002, LP-LEAVE-001, LP-LEAVE-002, LP-LEAVE-003, LP-LEAVE-004, LP-LEAVE-005, LP-LEAVE-006, LP-LEAVE-007, LP-LEAVE-008, LP-NFR-001, LP-NFR-002, LP-NFR-003, LP-NFR-004, LP-NFR-005, LP-NFR-006, LP-NFR-007, LP-NFR-008, LP-PAY-001, LP-PAY-002, LP-PAY-003, LP-PAY-004, LP-PAY-005, LP-PAY-006, LP-PAY-007, LP-PAY-008, LP-PAY-009, LP-PAY-010, LP-PAY-011, LP-PAY-012, LP-PAY-013, LP-PAY-014, LP-PAY-015, LP-REC-001, LP-REC-002, LP-REC-003, LP-REC-004, LP-REC-005, LP-REP-001, LP-REP-002, LP-REP-003, LP-REP-004, LP-TIME-001, LP-TIME-002, LP-TIME-003, LP-TIME-004, LP-TIME-005, LP-TIME-006, LP-TIME-007)
- retained TESTED/IMPLEMENTED: 0/26
- BLOCKED held (never flipped): 17
- IN PROGRESS held (never flipped): 3

## Failing / retained rows
LP-AUD-005, LP-AUD-006, LP-DATA-001, LP-INT-003, LP-INT-004, LP-INT-005, LP-LIFE-001, LP-LIFE-002, LP-LIFE-003, LP-LIFE-004, LP-LIFE-005, LP-LIFE-006, LP-LIFE-007, LP-LIFE-008, LP-LIFE-009, LP-REC-006, LP-REC-007, LP-TAL-001, LP-TAL-002, LP-TAL-003, LP-TAL-004, LP-TAL-005, LP-TAL-006, LP-TIME-008, LP-TIME-009, LP-TIME-010

## BLOCKED triage (verbatim `Blocker / decision`)

### LP-ADM-005

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-DATA-002

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-DOC-001

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-DOC-002

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-DOC-003

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-EXP-001

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-EXP-002

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-EXP-003

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-NFR-012

```
BLOCKED per PRD 28/29: exact dependency = product-owner approval (data residency; supported deployment matrix; Cloudflare target) — none granted. Recorded 2026-11-22.
```

### LP-NFR-013

```
BLOCKED per PRD 28/29: exact dependency = product-owner approval (data residency; supported deployment matrix; Cloudflare target) — none granted. Recorded 2026-11-22.
```

### LP-NFR-014

```
BLOCKED per PRD 28/29: exact dependency = product-owner approval (data residency; supported deployment matrix; Cloudflare target) — none granted. Recorded 2026-11-22.
```

### LP-NOT-001

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-NOT-002

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-NOT-003

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-SVC-001

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-SVC-002

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

### LP-SVC-003

```
BLOCKED — surplus ID with no phase assignment (docs/product/release-readiness.json defects_surplus: 14 IDs incl. this one; decision: product-owner decisions required before start). Delivery evidence in row proves implementation only, not scope approval. Per PRD 28: exact dependency = product-owner scope decision; recorded 2026-11-22.
```

## IN PROGRESS (held)

- LP-NFR-009: IN PROGRESS: perf/load, backup/restore, or E2E proof not collected on this HEAD (pg_dump/docker-dependent evidence unavailable); continuing with independent work. Recorded 2026-11-22.
- LP-NFR-010: IN PROGRESS: perf/load, backup/restore, or E2E proof not collected on this HEAD (pg_dump/docker-dependent evidence unavailable); continuing with independent work. Recorded 2026-11-22.
- LP-NFR-011: IN PROGRESS: perf/load, backup/restore, or E2E proof not collected on this HEAD (pg_dump/docker-dependent evidence unavailable); continuing with independent work. Recorded 2026-11-22.

## Notes
- Oracle roundtrip out of scope (no wallet/schema here).
- FY26-27 skeleton refusal (409 rule_pack_not_verified for dates >= 2026-04-01) fails payroll rows legitimately; recorded as fail, never force-passed.
- Frontend e2e needs a live server; harness defaults to unit/route checks; e2e-dependent rows stay unpromoted with reason.
- Known FAILs retained (e.g. LP-AUD-005/006 stay IMPLEMENTED): admin_audit route-mount defect, no app-code fix in this slice.
