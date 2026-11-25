# Karmathy HCM — Iteration 4 Plan

**Branch:** `iter/4-job-queue` (to be created from main)
**Focus:** Background job queue (J-04/J-05/J-06/J-07) — unblocks import, forecasting, scheduling, payroll, reports

## Gaps to close (from FEATURE_MATRIX.md)

| ID | Feature | Status | Plan |
|---|---|---|---|
| J-04 | Background job queue: queued/running/succeeded/failed/dead states | MISSING | Create `backend/app/jobs/` module with Job model, Job states, JobType enum, database-backed queue |
| J-05 | Job leases with heartbeat + exponential backoff + dead-letter view | MISSING | Lease/heartbeat logic, retry with exponential backoff and jitter, max attempts, dead-letter view for admins with retry/discard |
| J-06 | Job types: csv_import, forecast_run, roster_solve, payroll_process, document_render, webhook_deliver, retention_run, erasure_run | MISSING | Job type registry, job type handlers |
| J-07 | Input hash / result hash; idempotent re-run | MISSING | Input hash computation, result hash storage, idempotent re-run (no-op if same input succeeded) |

## Files expected to change

- `backend/app/models/job.py` — new: Job model with states, lease, heartbeat, input/output hashes
- `backend/app/jobs/__init__.py` — new: job queue module
- `backend/app/jobs/queue.py` — new: database-backed job queue with leases, retry, backoff
- `backend/app/jobs/registry.py` — new: job type registry and handlers
- `backend/migrations/versions/0004_jobs.py` — new migration for jobs table
- `backend/app/api/v1/endpoints/admin.py` — add job queue endpoints (list, retry, discard)
- `backend/app/api/deps.py` — may need admin job queue dependency
- `backend/jobs_test_suite.py` — new test suite
- `ci/run_backend_tests.sh` — add jobs_test_suite
- `docs/validation/FEATURE_MATRIX.md` — mark J-04 through J-07 VERIFIED

## Decision questions (section 5)

None — all Gate 0A decisions are recorded.

## Exit criteria for iteration 4

- Job model with states (queued, running, succeeded, failed, dead) created
- Job queue with leases, heartbeat, retry with exponential backoff + jitter, max attempts
- Dead-letter view for admins with retry and discard actions
- All 7 job types registered with handlers
- Idempotent re-run: same input hash that already succeeded is a no-op
- All 13+ backend test suites pass
