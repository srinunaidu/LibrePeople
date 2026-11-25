# Naive-datetime site inventory

Method: `grep` for `datetime.utcnow()`, `datetime.now()`,
`date.today()` under `backend/app`, plus `tzinfo is None` coercions.
Representative, not exhaustive — implementation slice re-verifies each.

| # | Site | Current | Disposition |
|---|------|---------|-------------|
| 1 | `crud/crud_client_onboarding.py` (`started_at`, `finished_at`, `completed_at`, `last_sync_at`, `hire_date`) | `datetime.utcnow()` naive | **Fix** → `utcnow()` aware |
| 2 | `crud/crud_offboarding.py` (`completed_at`) | `datetime.utcnow()` naive | **Fix** → `utcnow()` aware |
| 3 | `crud/crud_scheduling.py` (`decided_at`) | `datetime.utcnow()` naive | **Fix** → `utcnow()` aware |
| 4 | `crud/crud_leave.py` (`decided_at`) | `datetime.utcnow()` naive | **Fix** → `utcnow()` aware |
| 5 | `crud/crud_time_attendance.py` (`clock_in`) | `datetime.utcnow()` naive | **Fix** → `as_utc()` from wall |
| 6 | `api/v1/endpoints/forecasting.py` (`finished_at`, generated name) | `datetime.utcnow()` naive | **Fix** → `utcnow()` aware |
| 7 | `api/v1/endpoints/time_attendance.py`, `reports.py`, `scheduling.py`, `payroll.py` (`date.today()` defaults) | server-local day | **Fix** → tenant-zone day |
| 8 | `services/data_quality.py`, `services/scheduling.py`, `services/job_admin.py`, `services/ops_status.py`, `jobs/handlers.py`, `models/user.py`, `models/imports.py` (`tzinfo is None → replace UTC`) | SQLite-naive read coercion | **Keep** — sole sanctioned naive entry point |
| 9 | `job_worker_test_suite.py:82`, `ops_model_test_suite.py:319` | tests asserting naive==aware | **Fix** tests with policy |

No `ZoneInfo` usage found in `backend/app` — all zone handling is new.
