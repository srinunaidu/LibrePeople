# Blocker Register — HEAD 0b8a402 (`feature/librepeople-production`)

Classification: A = product-owner approval/decision · B = external tooling/environment
C = in-progress implementation work · D = independent reviewer/verifier
E = documentation/procedure. Every BLOCKED + IN PROGRESS row from the live CSV
(`docs/product/requirements-traceability.csv`) is listed; no other statuses qualify.

## LP-DOC-003 — BLOCKED — Class A
- Dependency: product-owner approval of supported deployment/storage matrix
  (data residency/region, S3/licence decisions) per PRD §29.
- Evidence: storage matrix verified at HEAD 8beddae
  (`docs/product/storage-matrix.md`): local dir default
  (`settings.LOCAL_STORAGE_DIR`, ephemeral), OCI Object Storage prod opt-in
  (`STORAGE_BACKEND=oci` + namespace/bucket); no S3/GCS backend exists.
  Implemented via `backend/app/storage/backends.py get_storage()`;
  `lp_doc_002_test_suite.py` 11 passed (proves implementation, not scope approval).
- Owner: product owner (matrix/scope approval).
- Procedure: approve matrix → record decision → re-map harness → promote.
- Approval needed: §29 deployment matrix + residency/region + S3/licence decision.
- Next action: owner decision on storage matrix; acceptance N/A while BLOCKED.
- Status: BLOCKED (unchanged at 0b8a402).

## LP-NFR-012 — BLOCKED — Class A
- Dependency: product-owner approval — data residency, supported deployment
  matrix, Cloudflare/architecture target (PRD §28/§29). No target approved.
- Evidence: acceptance N/A while BLOCKED; `ci/secret_scan.py` clean;
  cross_tenant 31 + security 2073 passed (proves code posture, not approval).
- Owner: product owner.
- Procedure: approve target/matrix/residency → record → collect deployment evidence.
- Approval needed: PRD §29 trio (residency + matrix + Cloudflare target).
- Next action: owner approval; no code work unblocks this.
- Status: BLOCKED (unchanged at 0b8a402).

## LP-NFR-013 — BLOCKED — Class A
- Dependency: same PRD §28/§29 owner approvals as NFR-012 (none granted).
- Evidence: acceptance N/A while BLOCKED; secret scan clean; suites green as above.
- Owner: product owner.
- Procedure: approve → record → collect evidence.
- Approval needed: PRD §29 trio (residency + matrix + target).
- Next action: owner approval; no code work unblocks this.
- Status: BLOCKED (unchanged at 0b8a402).

## LP-NFR-009 — IN PROGRESS — Class C (with B element)
- Dependency: perf/load + backup/restore + E2E proof collection
  (pg_dump/docker-dependent evidence unavailable on this HEAD).
- Evidence: no perf/load, backup/restore, or E2E harness run on this HEAD;
  secret scan clean. Proof absent, not VERIFIED; TESTED ceiling applies.
- Owner: builder (independent work continuing).
- Procedure: run perf/load + backup/restore + E2E → record evidence → promote.
- Approval needed: none (work item); RPO/RTO targets themselves are PROPOSED (see decision register).
- Next action: collect missing proof with independent tooling.
- Status: IN PROGRESS.

## LP-NFR-010 — IN PROGRESS — Class C (with B element)
- Dependency/evidence/owner/procedure: same as NFR-009 (proof not collected,
  docker/pg_dump-gated, builder-owned).
- Approval needed: none (work item).
- Next action: collect missing proof.
- Status: IN PROGRESS.

## LP-NFR-011 — IN PROGRESS — Class C (with B element)
- Dependency/evidence/owner/procedure: same as NFR-009/010; RPO/RTO targets
  per deployment profile are PROPOSED only (PRD §NFR-011), restore untested.
- Approval needed: owner sign-off on RPO/RTO targets once proposed values are reviewed.
- Next action: collect backup/restore rehearsal + RPO/RTO evidence.
- Status: IN PROGRESS.
