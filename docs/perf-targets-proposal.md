# Performance Targets Proposal — NOT COMMITMENTS, OWNER APPROVAL REQUIRED

> Status: **proposal only**. No target below is a commitment, SLA, or gate
> until the owner approves it. Do not cite this file as a guarantee.

## Measured baselines (quoted, not invented)

Source: `docs/release/perf-baseline.md` (2026-11-25, `agent/ops/perf-baseline`
from `216e869`, PG 16.16 scratch, synthetic data, backend `:18000`).

Latency p50/p95 (ms) at L500 — login 242/245 · emp_list 5.1/6.4 ·
dashboard 6.2/8.3 · leave_apply 7.0/8.8 · payroll dry-run 32.8/33.5
(`POST /payroll/runs/1/process?dry_run=true`, headcount 0: no pay profiles
seeded; login ~242 ms bcrypt-bound, flat across levels).
Light concurrency (emp_list, 50 req / 10 threads): L500 **256 rps, 0 errors**
(284–291 rps at L10–L250; p95 40–54 ms).
Ops: draft-run create 25 ms · `pg_dump -Fc` 143 ms / 420 KB ·
10-row CSV import 40 ms · DB 16 MB at 510 employees ·
`roster_solve` pickup→terminal ~0.6 s / ~2.1 s terminal FAILED
(`ortools` absent — successful-completion latency NOT MEASURED).

Source: `docs/release/perf-repeatability.md` (2026-11-25,
`agent/ops/perf-repeat` from `2b7652f`; deviations: schema at
`0048_mfa_secret_envelope`, MFA-enrolled writes).

Login p50 245±1 ms rock-stable (1–2%); payroll p50 33–37 (≤20%);
leave p50 8–9. L500 confirmatory: login 251/261, list 5.9/6.8,
leave 8.6/10.8, payroll 35/38, 216 rps / 0 errs / conc p95 72.
Dump 157 ms / 472 KB; import ~30 ms; DB 16 MB at 510 — matches baseline.
UNSTABLE (shared-host noise, excluded from gating): rps (−40% swings),
conc p95 spikes (42→156 ms), login p95 tails (+30%), leave/payroll p95
(up to +100% on n=10/n=5 — method limit, not a regression signal).
Zero errors in all 11 concurrency probes (550 requests).
Repeatability gate (proposed there): p50 ≤ 15% pass-to-pass delta on a
quiet host; p95/tails and rps excluded until isolated hardware.

## Proposed targets (per endpoint, with headroom rationale)

Headroom rule: target ≈ 4–6× observed L500 p95 for cheap queries
(absorbs host noise + real PG latency), ≈ 2× for bcrypt-bound login,
≈ 6× for payroll dry-run (real headcount unmeasured).

- `POST /auth/login`: p50 ≤ 300 ms, p95 ≤ 400 ms (observed 251/261;
  bcrypt floor ~245 ms leaves no room below 300/400).
- `GET /employees/` list: p95 ≤ 50 ms to 500 employees (observed 6.8).
- `GET /reports/dashboard`: p95 ≤ 100 ms to 500 (observed 6–8;
  baseline proposed 100, dashboard omitted from repeat scope).
- `POST /leave/requests` (apply): p95 ≤ 100 ms (observed ~11).
- `POST /payroll/runs/{id}/process?dry_run=true`: p95 ≤ 200 ms to 500
  (observed 38; real headcount > 0 unmeasured — target is provisional).
- Light concurrency: 0 errors at 50 req / 10 threads; ≥ 200 rps
  localhost (observed 203–291 rps, 0 errors at every level).
- Ops: backup completes; job pickup ≤ 10 s when worker enabled
  (successful completion NOT MEASURED — no target proposed);
  CSV import ≤ 5 s per ≤ 100 rows (observed ~30–40 ms per 10 rows).

## What would invalidate these

Prod-like env (managed PG with `pg_stat_statements`, isolated CPU,
real network latency), real volumes (≥ 1000 employees, profiles seeded
so payroll headcount > 0), multi-client load generation (not one
localhost loop), soak duration, production bcrypt cost + deployed MFA
policy, successful job-completion measurement, frontend timings.
Any of these differing materially voids the numbers above — re-baseline
first. NOT MEASURED (carried over): 1000+ employees, soak/endurance,
failover, cross-tenant load, per-query slow log, frontend timings.
