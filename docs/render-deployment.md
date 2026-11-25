# LibrePeople — Render deployment watch

Dated, append-only record of Render testing-deploy observations.
(Karmathy-era history lives in `docs/DEPLOYMENT.md`; this file starts
with the LibrePeople `librepeople-backend` service.)

## 2026-11-25 — deploy dep-dc3ihvs9v7es7388mhe0 LIVE @ 072c86c BUT seed still off (dashboard env overrides render.yaml)

- Branch: `agent/ops/render-bootstrap` from `072c86c` (origin/main).
  Deploy `dep-dc3ihvs9v7es7388mhe0`, created `18:29:19Z`, `live`
  `18:30:56Z`. Commit built: `072c86c` — matches. **Not stale.**
- Startup logs (verbatim): `[startup] MIGRATE_ON_STARTUP is disabled;
  skipping migrations.` (18:30:51Z) then worker start, startup complete.
  No seed line; no `Seeded initial SuperAdmin` / `already-exists`.
  Migration no-op confirmed instead via CMD:
  `[migrate] Database is now at 0048_mfa_secret_envelope` (18:30:02Z).
- Root cause: Render dashboard env still holds `MIGRATE_ON_STARTUP=false`
  (verified via API); dashboard-set values override `render.yaml`, so the
  `71c11e9` blueprint change did not take effect. **Lead action: flip the
  variable in the dashboard (or Blueprint-sync) — that edit redeploys by
  itself.** Untouched here (no dashboard writes, no redeploy from this agent).
- Authenticated smoke blocked again: no users exist (nothing has ever
  seeded this DB). HR-admin account creation therefore pending bootstrap.

### Smoke table

| Check | Result |
|---|---|
| `GET /health` → 200 | pass, 0.2 s |
| Migration `current == head` incl. `0048` | pass via logs (CMD no-op at 0048); `GET /health/db` 401-gated |
| `POST /api/v1/auth/login` | 401 (zero users; generic no-enumeration response) |
| `GET /api/v1/employees` (no token) | 401 (auth-gated) |
| Frontend `/` | 200, 0.5 s |
| Synthetic HR-admin account | pending bootstrap (needs SuperAdmin token) |

### Gaps / costs

- Cost: $0 (free tier).
- `ADMIN_INITIAL_PASSWORD`: **left set** — portals need provisioning next;
  rotation happens only after Admin/ESS accounts are verified working.
- Still open: R2 vars absent; `JOB_WORKER_ENABLED` value uninspected; no
  custom domains (default `*.onrender.com` TLS).

## 2026-11-25 — free-tier fix: MIGRATE_ON_STARTUP true (no release step on free tier)

- `render.yaml`: `MIGRATE_ON_STARTUP` `false` → `true` (+ comment).
  Deploy `dep-dc3ieoss728c739783ng` proved preDeployCommand never runs on
  free tier, so the release step the runbook relies on does not exist
  there; startup migrate+seed is the only in-platform bootstrap path.
  Safe: `numInstances: 1` (no concurrent migration), alembic upgrades
  idempotent, `seed_initial_admin` fail-closed (seeds only at zero users).
- `ADMIN_INITIAL_PASSWORD` left as-is for the first boot; rotation after.
- No redeploy triggered (lead's push decides).

## 2026-11-25 — deploy dep-dc3ieoss728c739783ng LIVE @ 4d21662 (driver fix verified; bootstrap blocked on free tier)

- Branch: `agent/ops/render-smoke` from `4d21662` (origin/main, includes
  fix `41a1a27`). Deploy `dep-dc3ieoss728c739783ng`, trigger
  `new_commit`, created `18:22:27Z`, `live` at `18:25:38Z`.
  Commit built: `4d21662` — matches. **Not stale.**
- preDeployCommand: **skipped by the platform** —
  `Predeploy command not run. Commands can only run on paid instance types`
  (18:23:50Z). Migrations still ran via the Dockerfile CMD
  (`python -m scripts.migrate upgrade && exec uvicorn ...`): full chain
  `0001_baseline → … → 0048_mfa_secret_envelope` on the fresh Neon DB,
  ending `[migrate] Database is now at 0048_mfa_secret_envelope`
  (18:24:43Z). Repo chain is linear (50 files, one head: `0048`).
  Caveat: on free tier the runbook's "preDeploy proves migration" step
  does not execute; the CMD fallback is the actual migration path.
- Bootstrap: **zero users exist** (no prior live deploy; startup skips
  `_seed_admin_users()` when `MIGRATE_ON_STARTUP=false`, confirmed in
  code + logs). One-off job `python -m scripts.seed_admin` refused:
  `400 new paid services not allowed` — paid-tier STOP applies. Owner
  must run the seed from the Render dashboard Shell, then sign in and
  rotate. `ADMIN_INITIAL_PASSWORD` **kept** (deletion deferred until
  post-bootstrap smoke — deleting now would destroy the only bootstrap
  credential).

### Smoke table

| Check | Result |
|---|---|
| `GET /health` → 200 `{"status":"healthy"}` | pass, 0.2 s |
| Migration `current == head` incl. `0048` | pass via deploy logs (above); `GET /health/db` 401-gated, needs SuperAdmin |
| `POST /api/v1/auth/login` seeded admin | 401 (zero users — expected, not a failure) |
| `GET /api/v1/employees` | 307 unauthenticated (auth-gated; token smoke pending bootstrap) |
| Frontend `/` | 200, 0.4 s (already live) |
| Post-smoke: delete `ADMIN_INITIAL_PASSWORD`, redeploy if required, re-verify `/health` | deferred (see Bootstrap) |

### Gaps / costs

- Cost: $0 (free tier; one-off jobs unavailable = paid feature).
- R2 vars still absent while `STORAGE_BACKEND` set — verify before file smoke.
- `JOB_WORKER_ENABLED` key exists (value uninspected).
- No custom domains (default `*.onrender.com` TLS).
- Follow-ups for lead: (1) owner Shell bootstrap + login/token smoke +
  secret deletion; (2) decide whether free-tier deploys should rely on
  CMD migrations or move seeding into an always-run startup path.

## 2026-11-25 — deploy dep-dc3hph49v7es73875p8g FAILED in preDeployCommand (STALE? no — SHA matches)

- Service: `librepeople-backend` (`srv-dc3g9q4ipgvc738jo7ug`,
  `https://librepeople-backend.onrender.com`)
- Deploy: `dep-dc3hph49v7es73875p8g`, trigger `new_commit`,
  created `2026-11-25T17:37:08Z`, finished `2026-11-25T17:39:03Z`,
  status `update_failed`. Prior deploys `dep-dc3gfkjrjlhs73fq12ug`
  (`d142ad12`) and `dep-dc3ge9rm8hqs7392ms40` / `dep-dc3g9qcipgvc738jo9ag`
  (`51affcc`) also `update_failed` earlier the same day.
- Commit built: `8688183e610b042c735ba21508c8029a3a3bbd1e` — equals the
  in-scope SHA `8688183`. **Not a stale build.**
- Failing step (verbatim tail, redacted — no secrets present):
  `preDeployCommand: python -m scripts.migrate upgrade` exited 1 with
  `ModuleNotFoundError: No module named 'psycopg2'` raised from
  `app/core/database.py:118 create_engine(...)` via SQLAlchemy's
  default `postgresql` dialect (`psycopg2.py:690 import_dbapi`).
- Cause: `backend/requirements.txt` carried `oracledb` but no Postgres
  driver, while `DATABASE_URL` points at Neon Postgres; the Docker image
  therefore cannot even import the engine, before any migration runs.
  Small + safe → fixed on branch `agent/ops/render-watch` as commit
  `41a1a27`: pins `psycopg2-binary==2.9.13` + regression tests
  (`backend/tests/test_postgres_driver_pinned.py`).
  Regression evidence: new tests fail on the pre-fix tree
  (`ModuleNotFoundError`, same as Render) and pass 3/3 with the driver
  installed; engine creation with a `postgresql://` URL proceeds past
  the DBAPI import (fails only at TCP connect, as expected locally).
  **Lead: merge + push to trigger a redeploy; this agent did NOT push.**

### Smoke table (not run — blocked on rebuild)

| Check | Result |
|---|---|
| `GET /health` → 200 | pending redeploy |
| `GET /health/db` (migration `current_revision == head`, incl. `0048`) | pending redeploy |
| Seeded-admin login → 200 + token | pending redeploy (`ADMIN_INITIAL_PASSWORD` key present; use one-shot only if zero users exist) |
| `GET /api/v1/employees` → 200 | pending redeploy |
| Post-smoke: delete `ADMIN_INITIAL_PASSWORD`, redeploy if required, re-verify `/health` | pending smoke |

### Gaps / costs

- Cost: $0 expected (free tier; failed build consumed build minutes only).
- R2 vars (`R2_ENDPOINT_URL`, `R2_BUCKET`, `R2_ACCESS_KEY_ID`,
  `R2_SECRET_ACCESS_KEY`) are **absent** from the service env while
  `STORAGE_BACKEND` is set — verify before file-path smoke.
- Worker: `JOB_WORKER_ENABLED` key exists (value not inspected here).
- Custom domains: none configured; TLS is the default `*.onrender.com` cert.
