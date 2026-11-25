# Karmathy HCM — Iteration 5 Plan

**Branch:** `iter/5-csv-import` (to be created from main)
**Focus:** CSV import engine (I-01 through I-08) using the job queue for background processing

## Gaps to close (from FEATURE_MATRIX.md)

| ID | Feature | Status | Plan |
|----|---------|--------|------|
| I-01 | Import templates: departments, locations, jobs, employees, leave_balances, shift_templates | MISSING | Template endpoint returning exact expected columns per entity |
| I-02 | Exact header matching + alias table; unknown headers rejected | MISSING | Header validation with alias table |
| I-03 | Streaming UTF-8 parse; row limit 10,000; size limit 5 MB | MISSING | Streaming CSV parser with limits |
| I-04 | Validation: types, required, ISO 8601, enums, referential, duplicates, salary bounds | MISSING | Row-level validation engine |
| I-05 | Formula-injection neutralisation (=, +, -, @, tab, CR) | MISSING | Value sanitisation |
| I-06 | Dry run with counts + row-error CSV; confirmation token bound to result hash | MISSING | Dry-run → commit flow with token binding |
| I-07 | Idempotent upsert on natural keys; re-import = zero changes | MISSING | Upsert logic keyed on natural keys |
| I-08 | Uploaded file deletion after retention (default 7 days) | MISSING | Retention cleanup job |

## Files expected to change

- `backend/app/api/v1/endpoints/import_export.py` — upload, dry-run, commit, templates endpoints
- `backend/app/imports/` — new module: import engine, validation, templates
- `backend/migrations/versions/0005_imports.py` — import tracking tables
- `backend/jobs/handlers.py` — add `csv_import` handler implementation
- `backend/jobs/registry.py` — register csv_import handler (already registered)
- `backend/imports_test_suite.py` — new test suite (may fold into existing import_test_suite.py)
- `docs/validation/FEATURE_MATRIX.md` — mark I-01 through I-08 VERIFIED

## Decision questions (section 5)

None — all Gate 0A decisions are recorded.

## Exit criteria for iteration 5

- CSV template download returns exact columns per entity
- Upload with unknown headers rejected with full alias list
- Streaming parse respects row (10,000) and size (5 MB) limits
- Row validation catches type/enum/referential/duplicate errors
- Formula-injection values neutralised
- Dry run returns counts + downloadable row-error CSV
- Commit binds confirmation token to dry-run result hash
- Re-import of same file produces zero changes (idempotent)
- File retention cleanup works
- All 14+ backend suites pass
