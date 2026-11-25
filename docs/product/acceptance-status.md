# LibrePeople — Acceptance Status

2026-11-24: statuses reconciled to evidence; prior VERIFIED counts were overstated.

Rolling status for the LibrePeople phase plan (docs/product/phase-gates.md) and the
requirement traceability register (docs/product/requirements-traceability.csv).

- Branch: feature/librepeople-production — base commit 7ab0865255f777ba83a6121df61d0c02a95ccf5d (this reconciliation at 50074e0)
- PRD: docs/product/PRD.md (v1.0, 136 LP IDs — verified by grep)
- Traceability: docs/product/requirements-traceability.csv (136 requirement rows; CSV IDs == PRD IDs)

## Status vocabulary (applied to every row)

| Status | Definition |
|---|---|
| **VERIFIED** | Code exists, passing test evidence exists, and no blocker text withholds verification. |
| **IMPLEMENTED** | Code exists, but independent/adequate verification is absent, or the implementation is partial. |
| **IN PROGRESS** | Actively being built. |
| **BLOCKED** | External dependency: statutory sign-off, infrastructure/tooling, or owner decision. |
| **DEFERRED** | Out of v1 scope, acknowledged and preserved in the backlog. |

`DEFERRED BY APPROVAL` (previous label) is retired; those rows are now `DEFERRED`.
No row is marked VERIFIED by assertion alone; the blocker/decision column must be empty of withholding text.

## Executive summary — corrected counts

| Status | Before (2026-11-22) | After (2026-11-24) |
|---|---:|---:|
| VERIFIED | 122 | **2** |
| IMPLEMENTED | 0 | **105** |
| IN PROGRESS | 3 | **3** |
| BLOCKED | 3 | **18** |
| DEFERRED | 0 | **8** |
| DEFERRED BY APPROVAL (retired label) | 8 | — |
| **Total** | **136** | **136** |

Rows downgraded from VERIFIED: **120** (105 → IMPLEMENTED, 15 → BLOCKED).
8 rows relabelled `DEFERRED BY APPROVAL` → `DEFERRED` (no scope change).

The prior document claimed every row was `NOT STARTED` and 0 `IMPLEMENTED`; that was stale.
The prior CSV claimed 122 `VERIFIED` while ~105 of those rows carried withholding text
("VERIFIED withheld", "do NOT mark VERIFIED", "IMPLEMENTED only", failing suites).
Both are corrected here.

Only two rows meet the VERIFIED bar today: **LP-REC-006**, **LP-REC-007**
(harness HEAD c5f5d89 full green, no withholding).

- Phase plan A0–A11 (docs/product/phase-gates.md): A1 DONE; A0, A2–A11 PLANNED. A5 is PAY-BLOCKED — see §3.
- Level-B battery: docs/product/acceptance-suite.md — 20 areas, Status PLANNED; gate not executed yet.
- Global gate (all 136 PRD IDs appear in phase-gates.md): **136 — PASS** (122 assigned to phases, 14 surplus).
- CSV coverage: **0** IDs missing from phase-gates.md and 0 phase-gates IDs outside the CSV.
- Blockers: A5 (PAY-BLOCKED: 15 rows), 8 DEFERRED surplus rows, DOC-003 + NFR-012/013 BLOCKED on owner approvals, A11 owner decisions (PRD §26/§29).

## Per-requirement status (regenerated from the CSV)

| Requirement ID | Domain | Status | Basis (blocker / decision, abridged) |
|---|---|---|---|
| LP-ADM-001 | ADM | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-ADM-002 | ADM | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-ADM-003 | ADM | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-ADM-004 | ADM | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-ADM-005 | ADM | **IMPLEMENTED** | Owner decision 2026-11-22: INCLUDE in initial release per surplus resolution (was surplus with no phase assignment; see docs/product/phase-gates.md surplus table + PRD §16/§28). Implementation comp… |
| LP-AUD-001 | AUD | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-AUD-002 | AUD | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-AUD-003 | AUD | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-AUD-004 | AUD | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-AUD-005 | AUD | **IMPLEMENTED** | IMPLEMENTED only: admin_audit_test_suite FAILS (route-mount defect, got []); code exists at admin_audit.py:84. Recorded 2026-11-22. |
| LP-AUD-006 | AUD | **IMPLEMENTED** | IMPLEMENTED only: admin_audit_test_suite FAILS (route-mount defect, got []); code exists at admin_audit.py:84. Recorded 2026-11-22. |
| LP-COMP-001 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-COMP-002 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-COMP-003 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-COMP-004 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-COMP-005 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-COMP-006 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-COMP-007 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-COMP-008 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-COMP-009 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-COMP-010 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-COMP-011 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-COMP-012 | COMP | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated compliance-endpoint suite among the 52 backend suites; engine math covered by india_payroll_test_suite 114 passed 2026-11-22. Recorded 2026-11-22. |
| LP-CORE-001 | CORE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-CORE-002 | CORE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-CORE-003 | CORE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-CORE-004 | CORE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-CORE-005 | CORE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-CORE-006 | CORE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-CORE-007 | CORE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-CORE-008 | CORE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-CORE-009 | CORE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-CORE-010 | CORE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-DATA-001 | DATA | **IMPLEMENTED** | IMPLEMENTED only: import_test_suite FAILS twice incl. retry (sqlalchemy QueuePool limit size 5 overflow 10, connection timed out). Recorded 2026-11-22. |
| LP-DATA-002 | DATA | **IMPLEMENTED** | Owner decision 2026-11-22: INCLUDE in initial release per surplus resolution (was surplus with no phase assignment; see docs/product/phase-gates.md surplus table + PRD §16/§28). Implementation comp… |
| LP-DATA-003 | DATA | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-DATA-004 | DATA | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-DATA-005 | DATA | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-DATA-006 | DATA | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-DATA-007 | DATA | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-DOC-001 | DOC | **IMPLEMENTED** | Owner decision 2026-11-22: INCLUDE in initial release per surplus resolution (was surplus with no phase assignment; see docs/product/phase-gates.md surplus table + PRD §16/§28). Implementation comp… |
| LP-DOC-002 | DOC | **IMPLEMENTED** | Owner decision 2026-11-22: INCLUDE in initial release per surplus resolution (was surplus with no phase assignment; see docs/product/phase-gates.md surplus table + PRD §16/§28). Implementation comp… |
| LP-DOC-003 | DOC | **BLOCKED** | BLOCKED — storage matrix recorded 2026-11-22 at HEAD 8beddae1ce5cd5e98427fee08f2d6c8ea70b7d86 (see docs/product/storage-matrix.md): local dir backend is the default (settings.LOCAL_STORAGE_DIR, eph… |
| LP-ESS-001 | ESS | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-ESS-002 | ESS | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-ESS-003 | ESS | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-ESS-004 | ESS | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-ESS-005 | ESS | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-ESS-006 | ESS | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-EXP-001 | EXP | **DEFERRED** | DEFERRED — owner mandate surplus DEFER post-initial preserve backlog |
| LP-EXP-002 | EXP | **DEFERRED** | DEFERRED — owner mandate surplus DEFER post-initial preserve backlog |
| LP-EXP-003 | EXP | **DEFERRED** | DEFERRED — owner mandate surplus DEFER post-initial preserve backlog |
| LP-INT-001 | INT | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-INT-002 | INT | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-INT-003 | INT | **IMPLEMENTED** | IMPLEMENTED only: import lane suite FAILS (QueuePool exhaustion, see DATA rows). Recorded 2026-11-22. |
| LP-INT-004 | INT | **IMPLEMENTED** | IMPLEMENTED only: import lane suite FAILS (QueuePool exhaustion, see DATA rows). Recorded 2026-11-22. |
| LP-INT-005 | INT | **IMPLEMENTED** | IMPLEMENTED only: import lane suite FAILS (QueuePool exhaustion, see DATA rows). Recorded 2026-11-22. |
| LP-LEAVE-001 | LEAVE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-LEAVE-002 | LEAVE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-LEAVE-003 | LEAVE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-LEAVE-004 | LEAVE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-LEAVE-005 | LEAVE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-LEAVE-006 | LEAVE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-LEAVE-007 | LEAVE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-LEAVE-008 | LEAVE | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-LIFE-001 | LIFE | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated benefits-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-LIFE-002 | LIFE | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated benefits-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-LIFE-003 | LIFE | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated benefits-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-LIFE-004 | LIFE | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated benefits-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-LIFE-005 | LIFE | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated benefits-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-LIFE-006 | LIFE | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated benefits-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-LIFE-007 | LIFE | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated benefits-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-LIFE-008 | LIFE | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated benefits-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-LIFE-009 | LIFE | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated benefits-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-NFR-001 | NFR | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — TESTED is the ceiling for NFR per contract; no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-NFR-002 | NFR | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — TESTED is the ceiling for NFR per contract; no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-NFR-003 | NFR | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — TESTED is the ceiling for NFR per contract; no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-NFR-004 | NFR | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — TESTED is the ceiling for NFR per contract; no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-NFR-005 | NFR | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — TESTED is the ceiling for NFR per contract; no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-NFR-006 | NFR | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — TESTED is the ceiling for NFR per contract; no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-NFR-007 | NFR | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — TESTED is the ceiling for NFR per contract; no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-NFR-008 | NFR | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — TESTED is the ceiling for NFR per contract; no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-NFR-009 | NFR | **IN PROGRESS** | IN PROGRESS: perf/load, backup/restore, or E2E proof not collected on this HEAD (pg_dump/docker-dependent evidence unavailable); continuing with independent work. Recorded 2026-11-22. |
| LP-NFR-010 | NFR | **IN PROGRESS** | IN PROGRESS: perf/load, backup/restore, or E2E proof not collected on this HEAD (pg_dump/docker-dependent evidence unavailable); continuing with independent work. Recorded 2026-11-22. |
| LP-NFR-011 | NFR | **IN PROGRESS** | IN PROGRESS: perf/load, backup/restore, or E2E proof not collected on this HEAD (pg_dump/docker-dependent evidence unavailable); continuing with independent work. Recorded 2026-11-22. |
| LP-NFR-012 | NFR | **BLOCKED** | BLOCKED per PRD 28/29: exact dependency = product-owner approval (data residency; supported deployment matrix; Cloudflare target) — none granted. Recorded 2026-11-22. |
| LP-NFR-013 | NFR | **BLOCKED** | BLOCKED per PRD 28/29: exact dependency = product-owner approval (data residency; supported deployment matrix; Cloudflare target) — none granted. Recorded 2026-11-22. |
| LP-NFR-014 | NFR | **IMPLEMENTED** | Owner decision 2026-11-22: INCLUDE as hardening gate (was BLOCKED on deployment-target/residency approvals; 0043 enforces the safe subset at the DB layer). C1/C3/C10 deferred application-checked (C… |
| LP-NOT-001 | NOT | **DEFERRED** | DEFERRED — owner mandate surplus DEFER post-initial preserve backlog |
| LP-NOT-002 | NOT | **IMPLEMENTED** | Owner decision 2026-11-22: INCLUDE in initial release per surplus resolution (was surplus with no phase assignment; see docs/product/phase-gates.md surplus table + PRD §16/§28). Provider-agnostic d… |
| LP-NOT-003 | NOT | **DEFERRED** | DEFERRED — owner mandate surplus DEFER post-initial preserve backlog |
| LP-PAY-001 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-002 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-003 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-004 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-005 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-006 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-007 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-008 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-009 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-010 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-011 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-012 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-013 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-014 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-PAY-015 | PAY | **BLOCKED** | BLOCKED — No VERIFIED per contract (PAY never VERIFIED): FY25-26 pack verified (backend/rule_packs/in-standard.json v1.0.0 status=verified) but FY26-27 skeleton is pending_verification (backend/rul… |
| LP-REC-001 | REC | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-REC-002 | REC | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-REC-003 | REC | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-REC-004 | REC | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-REC-005 | REC | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-REC-006 | REC | **VERIFIED** | none — VERIFIED 2026-11-22 harness HEAD c5f5d89 full green. |
| LP-REC-007 | REC | **VERIFIED** | none — VERIFIED 2026-11-22 harness HEAD c5f5d89 full green. |
| LP-REP-001 | REP | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-REP-002 | REP | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-REP-003 | REP | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-REP-004 | REP | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-SVC-001 | SVC | **DEFERRED** | DEFERRED — owner mandate surplus DEFER post-initial preserve backlog |
| LP-SVC-002 | SVC | **DEFERRED** | DEFERRED — owner mandate surplus DEFER post-initial preserve backlog |
| LP-SVC-003 | SVC | **DEFERRED** | DEFERRED — owner mandate surplus DEFER post-initial preserve backlog |
| LP-TAL-001 | TAL | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated performance/learning-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-TAL-002 | TAL | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated performance/learning-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-TAL-003 | TAL | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated performance/learning-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-TAL-004 | TAL | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated performance/learning-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-TAL-005 | TAL | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated performance/learning-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-TAL-006 | TAL | **IMPLEMENTED** | IMPLEMENTED only: code+model present; no dedicated performance/learning-endpoint suite among the 52 backend suites. Recorded 2026-11-22. |
| LP-TIME-001 | TIME | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-TIME-002 | TIME | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-TIME-003 | TIME | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-TIME-004 | TIME | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-TIME-005 | TIME | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-TIME-006 | TIME | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-TIME-007 | TIME | **IMPLEMENTED** | IMPLEMENTED, not VERIFIED — no independent acceptance harness run on HEAD b3d72e2 2026-11-22; VERIFIED withheld per PRD §28 |
| LP-TIME-008 | TIME | **IMPLEMENTED** | IMPLEMENTED only: scheduling_test_suite cannot pass in this env — solver raises RuntimeError: ortools is not available (backend/app/services/solver.py:73); roster-generate path unproven here. Recor… |
| LP-TIME-009 | TIME | **IMPLEMENTED** | IMPLEMENTED only: scheduling_test_suite cannot pass in this env — solver raises RuntimeError: ortools is not available (backend/app/services/solver.py:73); roster-generate path unproven here. Recor… |
| LP-TIME-010 | TIME | **IMPLEMENTED** | IMPLEMENTED only: scheduling_test_suite cannot pass in this env — solver raises RuntimeError: ortools is not available (backend/app/services/solver.py:73); roster-generate path unproven here. Recor… |

## Executed gates

Phase gates from docs/product/phase-gates.md (per-phase extraction, same as acceptance-suite.md area commands). All commands run on this branch, all PASS.

| Phase | Gate command | Result |
|---|---|---|
| A0 | `awk -v h='## Phase A0 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **4 — PASS** |
| A1 | `awk -v h='## Phase A1 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **5 — PASS** |
| A2 | `awk -v h='## Phase A2 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **5 — PASS** |
| A3 | `awk -v h='## Phase A3 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **18 — PASS** |
| A4 | `awk -v h='## Phase A4 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **18 — PASS** |
| A5 | `awk -v h='## Phase A5 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **27 — PASS** (PAY-BLOCKED state recorded in phase-gates.md) |
| A6 | `awk -v h='## Phase A6 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **9 — PASS** |
| A7 | `awk -v h='## Phase A7 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **13 — PASS** |
| A8 | `awk -v h='## Phase A8 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **9 — PASS** |
| A9 | `awk -v h='## Phase A9 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **2 — PASS** |
| A10 | `awk -v h='## Phase A10 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **10 — PASS** |
| A11 | `awk -v h='## Phase A11 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` | **2 — PASS** |

Global: `grep -oE 'LP-[A-Z]+-[0-9]+' docs/product/phase-gates.md | sort -u | wc -l` → **136 — PASS** (122 assigned to phases; 14 in the surplus table, no phase assigned).

Coverage: `comm -13 <(grep -v '^#' docs/product/requirements-traceability.csv | tail -n +2 | cut -d, -f1 | sort -u) <(grep -oE 'LP-[A-Z]+-[0-9]+' docs/product/phase-gates.md | sort -u) | wc -l` → **0 — PASS** (all 136 CSV IDs appear in phase-gates.md).

CSV parsing note: the file now begins with `#` comment lines (changelog, vocabulary, summary). Data parsing must skip them, e.g. `grep -v '^#' docs/product/requirements-traceability.csv`.

Supporting executed checks (all on this branch):

- `grep -v '^#' docs/product/requirements-traceability.csv | tail -n +2 | awk -F, '{c[$4]++} END{for(s in c) print s, c[s]}' | sort` → `BLOCKED 18, DEFERRED 8, IMPLEMENTED 105, IN PROGRESS 3, VERIFIED 2` (136 rows total)
- `awk -F, 'NR>1{c[$3]++} END{for(s in c) print s, c[s]}'` on the data rows → 19 domains, 136 rows
- No row carries the retired label `DEFERRED BY APPROVAL`; every non-VERIFIED row carries a blocker/decision reason.

## Blocked gates

- **A5 — PAY-BLOCKED** (LP-PAY-001..015, 15 rows now BLOCKED): FY26-27 rule pack is `pending_verification` and 29 payroll/compliance verifier sign-offs for production payroll are outstanding; independent payroll acceptance not done (PRD §11, §25, §28).
- **Surplus/decision-gated work (14 IDs)** — owner resolution recorded 2026-11-22: 8 DEFERRED (LP-EXP-001..003, LP-NOT-001, LP-NOT-003, LP-SVC-001..003); 5 INCLUDED in the initial release and therefore IMPLEMENTED pending harness verification (LP-ADM-005, LP-DATA-002, LP-DOC-001, LP-DOC-002, LP-NOT-002); 1 BLOCKED (LP-DOC-003, storage matrix/scope approval).
- **Owner-approval BLOCKED**: LP-NFR-012, LP-NFR-013 (data residency, supported deployment matrix, Cloudflare target).
- **A11 — owner decisions outstanding** (PRD §26/§29): brand/legal clearance, OSI-approved licence approval + dependency review, payroll/statutory verifier identification, data-migration plan, data-residency definition, supported deployment matrix, native mobile decision.

## Level-B gate

docs/product/acceptance-suite.md — 20 Level-B areas (01–20): titles, exact commands, 1–3 acceptance criteria each, Status **PLANNED**, Depends on phases (numbers) or decision gate. Overall Level-B gate status: **NOT RUN — PLANNED**. Per PRD §28, nothing is marked COMPLETE because code was written; the battery runs per phase owner after A10. See §7 for per-area dependency mapping.

## Remaining decisions

See **§7 Team decision register** below — the standing decisions and their owners/where they live. Outstanding: LP-DOC-003 storage matrix/scope approval, LP-NFR-012/013 deployment approvals, the PAY verifier sign-offs, plus the PRD §29 items listed above.

## Team decision register

1. **D-01 Integration branch approved** — Decision: the LibrePeople integration branch is `feature/librepeople-production` (base commit 7ab0865255f777ba83a6121df61d0c02a95ccf5d). Owner: recorded by the team for this phase plan. Where it lives: docs/product/phase-gates.md (header) and this register.
2. **D-02 Commercial model** — Decision: LibrePeople is an independent, customer-controlled, single-tenant-per-customer product (no shared SaaS tenancy). Owner: product owner (PRD §29). Where it lives: PRD.md §25 (tenancy model), PRD.md §29 ("independent customer deployment model: no shared SaaS tenancy required"), phase-gates.md A2/A9/A11 notes, this register.
3. **D-03 Customer architecture** — Decision: reference deployment = Docker Compose + PostgreSQL + application services + durable worker + reverse proxy + persistent document storage + health checks (PRD §20; PostgreSQL standard per PRD §28). Owner: product owner (PRD §25). Where it lives: PRD.md §20, phase-gates.md A2 (PostgreSQL migration), A9 (installation, backup, restore, upgrade), docs/product/workflow.md §9.
4. **D-04 Names/identity** — Decision: the working product name is LibrePeople; no other identity name is claimed or reused. Owner: product owner (PRD §29 brand/legal clearance). Where it lives: PRD.md §29, this register.
5. **D-05 CI triage** — Decision: CI scripts live in ci/ (run_backend_tests.sh, check_requirements.py, secret_scan.py, oracle_migration_roundtrip.py); for this docs-only phase plan, CI triage is assigned to the builder role per phase-gates.md owners. Owner: builder. Where it lives: ci/, this register.
6. **D-06 Definition of done level A+B** — Decision: Phase DoD = all phase gates (A0–A11) DONE + the Level-B battery (acceptance-suite.md) all 20 areas green/PASS. Owner: product owner (PRD §28). Where it lives: docs/product/phase-gates.md, docs/product/acceptance-suite.md, this register.
7. **D-07 Final completion criteria** — Decision: LibrePeople is ready for production release only when a real customer can deploy independently, configure without code changes, import/validate employee data, create administrators, invite employees, run connected HR/time/pay workflows, process payroll with independently verified calculations, access statutory outputs, operate ESS, back up and restore, and upgrade safely (PRD §30); the product must remain customer-controlled, portable and maintainable; motto: People. Time. Pay. Connected. Owner: product owner (PRD §30). Where it lives: PRD.md §30, phase-gates.md A11, this register.
