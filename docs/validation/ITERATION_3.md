# Karmathy HCM — Iteration 3 Plan

**Branch:** `iter/3-visibility` (to be created from main)
**Focus:** Object-level authorization — visibility + ownership checks on all endpoints (A-01/A-02)

## Gaps to close (from FEATURE_MATRIX.md)

| ID | Feature | Status | Plan |
|---|---|---|---|
| A-01 | Central policy module applied to all endpoint files | PARTIAL | visibility.py used in only ~4 of 25 endpoint files. Apply `apply_visibility` to all read endpoints and `ensure_can_view_employee` to all single-record read endpoints. |
| A-02 | Employee-scoped reads: self/direct reports/dept/payroll/admin | PARTIAL | Extend visibility filtering to payroll, performance, benefits, time, scheduling, core-hr, ESS, reports endpoints. |
| A-04 | Negative cross-user tests on every module | PARTIAL | Extend security_test_suite.py and visibility_test_suite.py to cover all 25 endpoint files. |

## Files expected to change

- `backend/app/api/v1/endpoints/payroll.py` — visibility on pay-profiles, payslips, runs
- `backend/app/api/v1/endpoints/performance.py` — visibility on reviews, feedback, bands, allocations, goals
- `backend/app/api/v1/endpoints/benefits.py` — visibility on enrollments, life events
- `backend/app/api/v1/endpoints/time_attendance.py` — visibility on entries, timesheets
- `backend/app/api/v1/endpoints/scheduling.py` — visibility on roster, swaps
- `backend/app/api/v1/endpoints/core_hr.py` — visibility on documents, cases
- `backend/app/api/v1/endpoints/ess_hr.py` — visibility on files, directory, checks, alignments
- `backend/app/api/v1/endpoints/reports.py` — visibility on dashboard, headcount, etc.
- `backend/app/api/v1/endpoints/onboarding.py` — visibility on documents, tasks
- `backend/app/api/v1/endpoints/offboarding.py` — already has visibility, verify completeness
- `backend/security_test_suite.py` — add negative tests for newly scoped endpoints
- `backend/visibility_test_suite.py` — expand coverage
- `docs/validation/FEATURE_MATRIX.md` — mark A-01, A-02, A-04 VERIFIED

## Decision questions (section 5)

None — all Gate 0A decisions are recorded. Visibility model already exists in `core/visibility.py`; this is application of the existing policy to all endpoints.

## Exit criteria for iteration 3

- `apply_visibility` called on every read endpoint that returns employee-scoped data
- `ensure_can_view_employee` called on every single-record read endpoint
- Ownership checks on all write endpoints (create/update/delete)
- Negative tests pass for every module: user A cannot read/write user B's rows by ID, list, or search
- All 13 backend suites still pass
