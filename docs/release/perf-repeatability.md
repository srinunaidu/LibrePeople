# Performance Repeatability + Variance — 2026-11-25

Branch `agent/ops/perf-repeat` from `2b7652f`. Scratch-only, synthetic data, no push. Only this file added; no product code, migration, or other doc touched. Read-only source: `perf-baseline.md` (method replicated, not edited).

## Method replication (deviations noted)

Same stack as baseline: scratch PG 16.16 on `127.0.0.1:55433`, backend `:18000` with `JOB_WORKER_ENABLED=1`, stdlib-urllib harness rewritten-equivalent in `/tmp` (deleted after run): login n=20, emp-list n=20, leave-apply n=10, payroll dry-run n=5 (`POST /payroll/runs/1/process?dry_run=true`), concurrency 50 req / 10 threads. Deviations: (1) schema is now at `0048_mfa_secret_envelope`, so the baseline's scratch `ALTER … TYPE TEXT` workaround is obsolete — nothing needed; (2) privileged writes now require enrolled MFA, so TOTP was enrolled via `POST /auth/mfa/enroll` + `/confirm` (scratch-only); (3) payroll fixture payloads are `{"name","start_date","end_date","pay_date"}` and `{"period_id","jurisdiction":"IN","currency":"INR"}`. One run-4 caveat: the primary pass set ran against the cumulative 100-row table for all nominal levels (reseed was a no-op); run-3 below gives true per-level cross-check values and agrees.

## MEASURED — primary: 3 passes per level (ms; login/list/leave/payroll = p50/p95/p99)

| Level | login | emp_list | leave_apply (201×10) | payroll dry-run (200×5) | light concurrency (50 req/10 thr) |
|---|---|---|---|---|---|
| 10 | P1 247/269/269 P2 245/248/248 P3 245/251/251 | P1 6.4/7.4/7.4 P2 5.3/6.2/6.2 P3 5.4/6.3/6.3 | P1 9.0/11.2 P2 8.1/10.2 P3 7.8/9.1 | P1 34/43 P2 35/40 P3 34/44 | 256/277/269 rps, 0 errs; conc p95 47/42/47 |
| 50 | P1 247/255 P2 245/260 P3 245/259 | P1 6.6/7.5 P2 5.3/6.1 P3 5.2/6.4 | P1 10.3/12.4 P2 7.9/10.7 P3 8.1/9.6 | P1 34/36 P2 33/34 P3 32/34 | 219/270/269 rps, 0 errs; conc p95 60/44/45 |
| 100 | P1 244/261 P2 247/277 P3 249/339 | P1 5.4/7.3 P2 6.9/10.8 P3 6.8/10.2 | P1 8.5/9.7 P2 9.5/10.8 P3 10.2/19.4 | P1 34/35 P2 36/39 P3 41/48 | 271/240/196 rps, 0 errs; conc p95 44/50/62 |

True-level cross-check (fresh DB, progressive seed 10→50→100): login p50 241–246, list p50 4.6–5.9, leave p50 7.0–9.2 across all 9 passes — confirms no level trend to 100, consistent with baseline.

## MEASURED — confirmatory single passes (run-5, cumulative DB)

- L250: login 252/395/395, list 6.1/7.4, leave 8.4/11.2 (201), payroll 38/57 (200), 203 rps / 0 errs / conc p95 59.
- L500: login 251/261/261, list 5.9/6.8, leave 8.6/10.8 (201), payroll 35/38 (200), 216 rps / 0 errs / conc p95 72.
- Dump/import: `pg_dump -Fc` 157 ms / 472 KB; 10-row CSV import commit ~30 ms wall (created=10, rejected=0); DB 16 MB at 510 employees (500 PERF + 10 IMP) — matches baseline footprint.

## Variance verdict (mean±sd of p50 across 3 passes; max pass-to-pass delta)

- STABLE (<20% swing): login p50 245±1 (1–2%); payroll p50 33–37 (≤20%); leave p50 8–9 (±0.5–1.1, ≤30% at L50 — borderline, small-n tails).
- UNSTABLE (>20%): **rps** (L10 cross-check 280→169, −40%; L100 primary 271→196, −28%; L50 219↔270, 23%) — hypothesis: shared-host CPU contention (load avg 4–7 during runs), single localhost client, no isolation; **conc p95** (42→156 ms spike in one pass) — same hypothesis; **login p95 tails** (up to +30%: 261→339; bcrypt ~245 ms p50 is rock-stable, tails are scheduling noise); **leave/payroll p95** (up to +100% on n=10/n=5 samples — tail percentiles of tiny samples, method limit, not a regression signal). Zero errors in all 11 concurrency probes (550 requests).

## Infra spec

Apple M1 Pro, 16 GB RAM, macOS 27.2.1; Homebrew PostgreSQL 16.16 (scratch cluster, port 55433); system Python 3.15 (fastapi 0.162, uvicorn 0.54, alembic 1.20.1, psycopg 3.3.9); backend uvicorn ~279 MB RSS class; shared host (IDE/builds running concurrently — see load averages above).

## Reproducibility (exact commands)

```
initdb -D /tmp/lp-perf-pgdata -U postgres --auth=trust
pg_ctl -D /tmp/lp-perf-pgdata -l /tmp/lp-pg.log -o "-p 55433" start
psql -h 127.0.0.1 -p 55433 -U postgres -c "CREATE DATABASE librepeople_perf;"
ADMIN_INITIAL_PASSWORD='<pw>' DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:55433/librepeople_perf" SECRET_KEY="<32+ chars>" FIELD_ENCRYPTION_KEYS="k1:<key>" FIELD_ENCRYPTION_ACTIVE_KEY_ID="k1" python3 -m scripts.seed_admin
# start backend :18000 with same env + JOB_WORKER_ENABLED=1
# login admin → POST /auth/password → POST /auth/mfa/enroll → TOTP /auth/mfa/confirm
# seed PERF dept/job/leave-type, employees cumulatively; measure per harness pattern above
```

## Proposed acceptance targets — NOT commitments, for owner approval

- login p50 ≤ 300 ms, p95 ≤ 400 ms (bcrypt-bound, single instance).
- emp-list p95 ≤ 50 ms to 500 employees; leave-apply p95 ≤ 100 ms; payroll dry-run p95 ≤ 200 ms (all observed far below except host-noise spikes).
- Repeatability gate: p50 metrics ≤ 15% pass-to-pass delta on a quiet host; p95/tail and rps excluded from gating until measured on isolated hardware (current host too noisy — see UNSTABLE items).
- Light concurrency: 0 errors at 50 req / 10 threads; backup completes; import ≤ 5 s per ≤100 rows.

## What a representative env would change

Isolated (non-shared) CPU for believable p95/rps; real BRS/infra PG with `pg_stat_statements` for per-query attribution; ≥1000-employee levels; multi-client load generation (not one localhost loop); network latency between client and server; soak duration; auth with production bcrypt cost and MFA policy as deployed.

## NOT MEASURED (with reason)

- Frontend timings: no browser stood up — backend-only harness, same as baseline.
- Dashboard endpoint: omitted per task scope (login/list/leave/payroll only).
- Background-job completion latency: only API-triggerable jobs need >2000-row imports or absent solver deps.
- Soak/endurance, failover, cross-tenant load, 1000+ employees: out of time-box; no extrapolation made.
