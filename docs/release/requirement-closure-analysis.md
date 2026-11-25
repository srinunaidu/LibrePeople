# Requirement Closure Analysis — LP-DOC-003 / LP-NFR-012 / LP-NFR-013

Base: `2b7652f` · Source CSV: `docs/product/requirements-traceability.csv` (lines 49, 92, 93) · Status vocabulary per CSV comment: BLOCKED = external dependency (owner decision). No requirement reinterpreted or weakened.

Contract rule (PRD §28, verbatim): "No requirement may be marked COMPLETE solely because code was written. Completion requires passing tests and demonstrable acceptance evidence." / "If a requirement cannot be completed due to external verification, credentials or product-owner approval, mark it BLOCKED, document the exact dependency and continue with independent work." / "Do not deploy to Cloudflare or any production cloud environment until the product owner explicitly approves the tested local release and deployment plan." Promotion procedure per `docs/release/blocker-register.md`: "approve matrix → record decision → re-map harness → promote."

## LP-DOC-003 (DOC, BLOCKED) — CSV line 49
- Exact row: status BLOCKED. UI: "documents surfaced in frontend/src/pages/People.tsx + ess/ESSHub.tsx (no standalone route verified)". API: "backend/app/api/v1/endpoints/core_hr.py:507 POST document versions (upload_document_version)". DB: "backend/migrations/versions/0040_document_lifecycle.py + backend/app/models/core_hr.py:133 employee_documents; :173 document_versions". Tests: "lp_doc_002_test_suite.py: 11 passed, 0 failed (2026-11-22) — proves implementation, not scope approval". Acceptance: "product scope/matrix NOT approved (surplus); acceptance N/A while BLOCKED". Blocker verbatim: "Matrix/scope approval pending per PRD §29 (supported deployment matrix, data residency/region, S3/licence decisions); acceptance N/A while BLOCKED."
- Flip condition: owner approves storage matrix/scope per PRD §29, decision recorded in `docs/release/decision-register.md`, then harness re-mapped and promoted per procedure above.
- Files verified (all EXIST): `frontend/src/pages/People.tsx` (doc surfacing, no standalone route); `frontend/src/pages/ess/ESSHub.tsx` (ESS surfacing); `backend/app/api/v1/endpoints/core_hr.py:507` (`upload_document_version` endpoint); `backend/migrations/versions/0040_document_lifecycle.py` (lifecycle schema); `backend/app/models/core_hr.py:133,173` (tables); `backend/app/storage/backends.py:115,172,260` (`LocalStorage`/`OCIObjectStorage`/`get_storage()` — proves local-default + OCI opt-in, no S3/GCS).
- Classification: **unresolved owner decision** (Class A per blocker-register.md:8). Evidence: blocker-register.md:8–21; decision-register pending "DOC-003 storage/matrix scope: PENDING"; release-readiness.json `defects_surplus` lists LP-DOC-003 (surplus, 14 IDs).
- Smallest closure: owner decision record only — no code/test. Next: `echo "DECISION $(date +%F): <APPROVE matrix: local-dev + OCI-prod | S3 decision> — owner: <name>" >> docs/release/decision-register.md` then re-map harness.

## LP-NFR-012 (NFR, BLOCKED) — CSV line 92
- Exact row: status BLOCKED. UI/API/DB all "depends on approved deployment target — none approved" / "depends on product-owner-approved target (Cloudflare/architecture) — none approved" / "depends on residency/backup policy approval". Tests: "blocked on external approvals/tooling, not on code; ci/secret_scan.py 2026-11-22: no secrets found". Acceptance: "acceptance N/A while BLOCKED". Blocker verbatim: "BLOCKED per PRD 28/29: exact dependency = product-owner approval (data residency; supported deployment matrix; Cloudflare target) — none granted. Recorded 2026-11-22."
- Flip condition: PRD §29 trio approved (residency + matrix + Cloudflare target), recorded, then deployment evidence collected per blocker-register.md:23–32 procedure.
- Files: no code references to verify (row references none — depends on approval, not code). `ci/secret_scan.py` clean proves posture only, not approval.
- Classification: **unresolved owner decision** (Class A). Evidence: blocker-register.md:23; decision-register "NFR-012 … approvals: PENDING".
- Smallest closure: owner approval record only. Next: record §29 trio decision in `docs/release/decision-register.md`; no code command unblocks this.

## LP-NFR-013 (NFR, BLOCKED) — CSV line 93
- Exact row: identical shape to NFR-012, status BLOCKED, same "none approved / none granted" refs, same "acceptance N/A while BLOCKED" and identical blocker verbatim (see NFR-012 above; CSV line 93).
- Flip condition: same §29 trio approval → record → collect readiness evidence (blocker-register.md:34–42).
- Files: none to verify (approval-gated, not code-gated).
- Classification: **unresolved owner decision** (Class A). Evidence: blocker-register.md:34; decision-register "NFR-013 … approvals: PENDING".
- Smallest closure: owner approval record only. Next: same trio record in `docs/release/decision-register.md`; then readiness evidence pack.
