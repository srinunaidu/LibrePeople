# Performance Baseline — 2026-11-25

Branch `agent/ops/perf-baseline` from `216e869`. Scratch-only stack, synthetic data only, no push. No product code, migration, rule-pack, or other doc touched; no thresholds invented, no scalability claims.

## Stack (proven scratch recipe)

- PG 16.16 (brew, no sudo): `127.0.0.1:55433`, data `/tmp/lp-perf-pgdata`, db `librepeople_perf`. `alembic upgrade head` → OK (2026-11-25T09:18:22Z).
- Seed: `seed_admin` + password change + TOTP MFA enroll via API; synthetic `PERF` dept/job, `PERF-CL` leave type, one `IN/INR` draft pay period + draft run (writes: draft only, never activated).
- Backend uvicorn `:18000` with `JOB_WORKER_ENABLED=1` (+ scratch-only `FIELD_ENCRYPTION_KEYS`/`SECRET_KEY` env; not committed).
- Measure window 09:24:55Z–09:25:28Z (`/tmp/lp-perf-harness3.py`: stdlib urllib, sequential samples; concurrency via 10-thread pool, 50 requests).

## Seeding (method + counts achieved)

`POST /api/v1/employees/` per employee (`PERF-%05d`, `synth.perf{k}@example.com`, hire 2024-06-03, Active). All levels achieved: **10, 50, 100, 250, 500** (cumulative; `total` from `GET /employees/?page=1&page_size=1`). After L500, a 10-row CSV import added `IMP-*` rows (final count 510, DB 16 MB).

## MEASURED — latency (ms; login n=20, emp_list n=20, dashboard n=20, leave_apply n=10, payroll dry-run n=5)

| Level | login p50/p95/p99 | emp_list p50/p95/p99 | dashboard p50/p95/p99 | leave_apply p50/p95/p99 | payroll dry-run p50/p95/p99 |
|---|---|---|---|---|---|
| 10 | 241/247/247 | 4.3/5.6/5.6 | 6.3/14.3/14.3 | 7.1/13.2/13.2 (201×10) | 32.0/39.1/39.1 (200×5) |
| 50 | 242/262/262 | 4.4/5.6/5.6 | 6.0/8.7/8.7 | 7.1/8.2/8.2 | 33.0/33.1/33.1 |
| 100 | 242/248/248 | 4.8/5.9/5.9 | 5.8/8.8/8.8 | 7.5/8.1/8.1 | 32.8/33.1/33.1 |
| 250 | 241/245/245 | 5.2/6.6/6.6 | 7.2/23.2/23.2 | 8.0/10.7/10.7 | 32.5/34.6/34.6 |
| 500 | 242/245/245 | 5.1/6.4/6.4 | 6.2/8.3/8.3 | 7.0/8.8/8.8 | 32.8/33.5/33.5 |

Payroll dry-run = `POST /payroll/runs/1/process?dry_run=true` → 200, `warning: "dry-run preview: headcount~0, pack in-standard v1.0.0 verified, currency INR; zero writes"`. Headcount 0: no pay profiles seeded. Login latency (~242 ms) is bcrypt-bound, flat across levels; list/dashboard/leave show no level trend to 500.

## MEASURED — throughput, resources, jobs, backup, import

- Light concurrency (emp_list, 50 req / 10 threads): L10 291 rps, L50 284, L100 283, L250 287, L500 256 rps; **0 errors at every level** (all HTTP 200; p95 40–54 ms). Method limit: single localhost client, no think time, not a soak test; locust not used (no new frameworks installed).
- CPU/memory (09:32:10Z, idle): system 16.8% user / 15.3% sys / 67.9% idle (load 4.2, shared host); uvicorn RSS ~279 MB, postgres RSS ~16 MB.
- DB 16 MB at 510 employees. Slow-query note: `pg_stat_statements` extension **absent** (count 0) — no statement stats; nothing flagged by inspection.
- Background job: `roster_solve` row inserted in scratch DB, worker pickup → terminal **~0.6 s and ~2.1 s** (2 samples, created→finished timestamps). Terminal state was FAILED (`RuntimeError: ortools is not available` — solver dep absent in scratch env). Successful-completion latency NOT MEASURED.
- Payroll preparation: second draft-run create **25 ms** (Draft only). Backup: `pg_dump -Fc` **143 ms, 420 KB**. Import: 10-row employee CSV commit **40 ms, created=10, rejected=0**.

## PROPOSED acceptance targets (for owner approval — NOT commitments)

- login p95 ≤ 400 ms (single instance, bcrypt cost as configured); emp_list p95 ≤ 50 ms to 500 employees; dashboard p95 ≤ 100 ms to 500; leave_apply p95 ≤ 100 ms; payroll dry-run p95 ≤ 200 ms to 500.
- Light concurrency: 0 errors at 50 req / 10 threads; ≥ 200 rps localhost.
- Backup completes; job pickup ≤ 10 s when worker enabled; import ≤ 5 s for ≤ 100 rows.

## NOT MEASURED (with reason)

- 1000+ employees: out of time-box; no extrapolation made.
- Successful job completion: only API-triggerable jobs are >2000-row imports (threshold 2000) or solver/notification paths with missing deps/preconditions.
- Frontend timings: backend-only baseline; no browser stood up.
- Soak/endurance, failover, cross-tenant load: out of scope.
- Per-query slow log: `pg_stat_statements` absent.

## Incidental defect (reported, not fixed)

`POST /auth/mfa/enroll` 500s on PG: `users.mfa_secret_hash` / `recovery_codes_hash` are `varchar(64)`, but the ENCv1 envelope (~150 chars) and recovery-code JSON exceed it (`StringDataRightTruncation`). Unblocked measurement with a scratch-DB-only `ALTER … TYPE TEXT`; **no repo change**. Suggest owner files a migration fix.
