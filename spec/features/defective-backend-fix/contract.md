# Feature: defective-backend-fix

## Behavior
Repair the 3 DEFECTIVE requirements (LP-AUD-005, LP-AUD-006, LP-DATA-001) with backend/test-only changes. Audit verify stays served at `GET /api/v1/admin/audit/verify`; import stays at `POST /api/v1/import-export/import/{entity}`. Screens affected: audit report (`frontend/src/pages/Reports.tsx:229`, calls correct path) and import screens (`frontend/src/pages/Import.tsx`, `src/lib/imports.ts` — all call correct paths, so no frontend change).

## Acceptance criteria
1. `GET /api/v1/admin/audit/verify` responds 200 for SuperAdmin/HR with the `AuditVerification` shape (verified, checked_entries, head, head_id, first_broken, verified_at).
2. `cd backend && python admin_audit_test_suite.py` exits 0, including the PS12-8 route-mounted check.
3. `cd backend && python import_test_suite.py` exits 0 with no `QueuePool`/timeout signature.
4. No other suite regressed: `security_test_suite.py` and `audit_chain_test_suite.py` results unchanged or better; diff of failures attached.
5. `backend/app/api/v1/endpoints/test_assets.py` (0 routes, D-01) is moved to `backend/tests/`; nothing imports the old path.

## Non-goals
No frontend changes. No new endpoints, schema, migration, or pool re-architecture.

## Interfaces / data
No contract change. Paths served today (`api.py:87` mount + `admin_audit.py:84`; `import_export.py:290`) are the contract paths. If a fix needs a migration or config change, stop (see NO-GO).

## Test plan
Validator runs, from `backend/`: `python admin_audit_test_suite.py`; `python import_test_suite.py`; regression spot: `python security_test_suite.py` (served-operations walk) and `python audit_chain_test_suite.py`. Suites only; no manual steps.

## Risk tier
2 (normal)

## Rollback
`git revert` the fix commit(s); suites return to current HEAD state. No data migration to unwind.

## Open decisions
- HEAD claimed `f3ee5cf` not verified (read-only, no shell): lead to confirm base commit before build.
- Traceability notes harness PASS on 7cba30f / fd568cd for both suites — lead to rule whether re-run green alone closes the DEFECTIVE labels.
- D-01 move (`test_assets.py` -> `backend/tests/`): confirm approved (prescribed in `docs/api-discrepancy-report.md`, still open per release notes).
- Current `fail_import` log shows 2 non-pool fails (schema-doc staleness, DI-04 `not_found` message wording): lead to rule in/out of scope.
- NO-GO: if a green re-run is impossible without pool re-architecture, connection-lifecycle redesign, or contract change, stop and report instead of patching.
