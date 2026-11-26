# Feature: filing-persistence
## Behavior
Adds filing records: saving a generated filing (type/period/content-hash), submission history, status transitions (Draft→Submitted→Accepted/Rejected→Resubmitted), evidence/attachment refs, resubmission creating a new version (never mutating a Submitted row), duplicate guard on (type, period, state?, content-hash), audit on every transition.
## Acceptance criteria
1. POST /reports/filings/{type}/records?period=YYYY-MM persists generated content-hash + metadata and returns 201 with version=1; repeat identical POST returns 409 duplicate.
2. GET /reports/filings/records?type=&period=&status= lists records with submission history ordered newest-first.
3. POST /reports/filings/records/{id}/submit|accept|reject enforces only legal transitions; illegal transition returns 422 and writes no audit row.
4. Resubmission creates version N+1 linked to prior id; original row immutable.
5. Unauthenticated request returns 401; PayrollViewer-or-above only.
## Non-goals
No challan payment, no upload to tax/PF/ESI authorities, no statutory filing, no new tax calculations (reuse stored deductions_json only).
## Interfaces / data
New table ONLY (no filing store exists): filing_records(id, filing_type, period, state, status, content_hash, content_ref, version, supersedes_id, submitted_by, submitted_at, timestamps). File ownership: new backend/app/models/filing_record.py, extend backend/app/api/v1/endpoints/filings.py, ONE new migration (next number — verify head first). Uses existing record_audit + resolve_rule_pack 409 gate.
## Test plan
pytest backend/tests/test_filings_persistence.py -q (new: create, duplicate-409, transition matrix, resubmit-version, audit rows). Regression: existing filings generation tests.
## Risk tier
2 (normal)
## Rollback
Drop migration + remove router additions; generated txt output unchanged.
## Open decisions — RESOLVED by lead 2026-11-26
Retention: keep-all until owner-defined retention policy lands (retention_until nullable). Attachments: content_ref references only, ≤10MB convention, no binary storage. DOC-003 storage decision untouched.
## NO-GO (STOP and report)
Challan/authority upload, new calculations, touching generation logic beyond calling it, changing existing tables.
