# External Dependency Register — HEAD 0b8a402

Class: C = external tooling/environment · D = external person/approval.
Repro = how to reproduce/verify the dependency.

## PostgreSQL / Oracle tooling — Class C
- Items: PostgreSQL migration baseline + `ci/oracle_migration_roundtrip.py`;
  `pg_dump`/docker-dependent backup/restore/E2E evidence unavailable on this HEAD.
- Repro: `ls ci/oracle_migration_roundtrip.py docs/runbooks/db-backup-restore.md`;
  attempt pg_dump/docker restore rehearsal on a host with Docker + PG —
  evidence absent here, which is why NFR-009/010/011 stay IN PROGRESS.
- Evidence: migration suite 67/0 on harness HEAD 65a1af2 proves migrations run,
  not that PG-prod restore works.
- Owner: builder. Next: run round-trip + restore rehearsal where tooling exists.

## Document storage backends (local/OCI; no S3/GCS) — Class C
- Items: `backend/app/storage/backends.py get_storage()`; matrix at
  `docs/product/storage-matrix.md` (HEAD 8beddae).
- Repro: `STORAGE_BACKEND=oci` + `OCI_NAMESPACE`/`OCI_BUCKET_NAME` → OCI;
  default local dir ephemeral. No S3/GCS backend to test.
- Owner: product owner for matrix decision (Class A blocker DOC-003);
  builder for backend code. Next: owner matrix approval.

## Independent payroll/statutory reviewer — Class D
- Items: qualified Indian payroll/statutory specialist for rule-pack review
  (LP-COMP-010, PRD §29); FY26-27 skeleton `pending_verification`;
  independent verified payroll run + sign-off outstanding.
- Repro: `cat backend/rule_packs/in-standard-VERIFICATION.md`;
  `ls backend/rule_packs/in-standard-fy2627-skeleton.json`; no sign-off record exists.
- Owner: product owner to identify reviewer. Next: reviewer engagement + verified run.

## Licence / dependency reviewer — Class D
- Items: OSI-approved licence approval (Apache-2.0 candidate, PRD §26),
  ownership/authority confirmation, third-party licence review + notices.
- Repro: `ls docs/licensing/sbom/` (backend/frontend transitive JSON + manifest,
  59c3823) and `docs/licensing/*` inventory (969d403); approvals still absent —
  inventory proves stock, not approval.
- Owner: product owner (+ legal). Next: licence decision + review sign-off.
