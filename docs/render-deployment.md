# LibrePeople — Render deployment watch

Dated, append-only record of Render testing-deploy observations.
(Karmathy-era history lives in `docs/DEPLOYMENT.md`; this file starts
with the LibrePeople `librepeople-backend` service.)

## 2026-11-26 — admin recovery via Neon least-privilege role + E2E provisioning complete

- Branch: `agent/ops/admin-recovery` from `072c86c`. No code/migration changes.
- Method: read repo hash scheme (`$krb1$` = bcrypt(12) over
  SHA-256/base64 pre-hash, `security.py:get_password_hash`); generated
  strong temp password in memory, hashed with the repo function
  (verified round-trip). Neon API: created temp role
  `recovery_tmp_20261126` (201) + least-privilege grants only
  (`CONNECT`, `USAGE public`, `SELECT, UPDATE ON users`). Single-row
  `UPDATE users SET hashed_password=<redacted-hash>,
  mfa_secret_hash=NULL, recovery_codes_hash=NULL, mfa_enabled=false,
  must_change_password=false WHERE id=1 AND username='admin'` →
  `UPDATE 1`. Pre-check: exactly 1 `admin` row (3 users total incl. the
  two synthetics). Fresh-session SELECT verified, then role dropped via
  Neon API (DELETE 200; direct DROP refused — owner lacks CREATEROLE,
  documented); `pg_roles` + grants both 0 afterwards. Local DNS could
  not resolve Neon hosts (REFUSED) — connected via DoH-resolved
  `hostaddr` with hostname TLS verification intact.
- Admin login 200 (2 attempts used: 1 cold-start timeout, 1 success —
  within budget). MFA re-enrolled+confirmed (required for privileged
  endpoints). Created 6/6 accounts (201 each): `e2e_hradmin` (HR),
  `e2e_hrexec` (HR), `e2e_payroll` (PayrollViewer), `e2e_manager`
  (Manager), `e2e_employee` (Associate), `e2e_readonly`
  (PayrollViewer). Set 12 Render env vars
  (`E2E_<HRADMIN|HREXEC|PAYROLL|MANAGER|EMPLOYEE|READONLY>_USERNAME|PASSWORD`,
  all PUT 200). Login-verify: 6/6 → 200.
- Custody: `BOOTSTRAP_ADMIN_PASSWORD` set in Render env (PUT 200) to the
  current admin password — documented secret store. Rotation: login →
  `POST /mfa/disable` (password suffices) → `POST /password` →
  re-enroll/confirm → update the env var. Never stored elsewhere; local
  secret files shredded.
- Deviation (test-env only): MFA was cleared then re-enrolled on the
  synthetic admin; enrollment secret/recovery codes from this session
  are gone, but password-alone disable keeps recovery self-service.
  Production MUST enforce MFA with held credentials — re-enroll before
  any prod-like use.

### Smoke table

| Check | Result |
|---|---|
| Admin login (recovered) | 200 + JWT |
| 6 E2E logins | all 200 + JWT |
| 12 Render env vars | all PUT 200 |
| Temp role lifecycle | created → grants → UPDATE 1 → dropped → verified gone |

## 2026-11-26 — cloud backup rehearsal: dump + restore-to-new-DB, all counts match

- Branch: `agent/ops/cloud-backup-rehearsal` from `552e2af`. No code,
  migration, or config changes. Synthetic-only pre-check passed
  (`users` 9, `employees` 50 sampled `CLOUD*`/`E2E*`/`example.com` —
  clearly synthetic, proceeded).
- Restore target: `librepeople_restore_test` (id 37081, owner
  `neondb_owner`, created 06:14:01Z) via Neon API (201) — separate DB,
  no production objects touched.
- Tooling detour: local `pg_dump` 16 vs server 18.7 (abort on version
  mismatch) → installed `postgresql@18` via brew (no sudo; user-level),
  `pg_dump` 18.7 matches server.
- Dump: custom format, rc 0, 10.3 s, 477,588 bytes; `pg_restore --list`
  rc 0, 998 entries / 223 TABLE lines / 111 base tables.
- Restore: rc 0, 87.6 s (`--no-owner --no-acl --clean --if-exists`).
  Quirk: pooler sessions needed schema-qualified names during
  verification (`public.users` 200-ok while bare `users` 404'd on the
  pooler); direct endpoint unqualified worked. Data identical either way.
- Counts source → restored: users 9=9, employees 50=50,
  expense_claims 10=10, audit_logs 798=798, tables 111=111,
  `alembic_version` 0049=0049. **ALL MATCH.** (Bonus: live DB head is
  `0049_interviews` — yesterday's missing-revision error resolved.)
- Recovery procedure (honest): restore-to-new-DB proven; promote-by-
  repointing-`DATABASE_URL` cutover is **untested** (gap — app never
  pointed at the restore).
- Retention: restore DB is 16 MB (<100 MB) → **left in place** as
  evidence; `/tmp` dumps removed, no strays. Free tier throughout ($0).

## 2026-11-26 — credential rotation: new admin + ESS passwords, custody updated

- Branch: `agent/ops/password-rotation` from `76df99b`. No code changes.
- Rotated via API as admin: own password via `POST /password` (200);
  `ess.synthetic` (id 3) via `POST /users/{id}/password` (200, account
  left must-change per endpoint design — login unaffected).
- Verification: fresh admin login 200; fresh `ess.synthetic` login 200
  (1 attempt each; no lockout signals). `BOOTSTRAP_ADMIN_PASSWORD` PUT
  200 to the new admin password; all 14 `E2E_*` vars untouched;
  `ADMIN_INITIAL_PASSWORD` still absent.
- Custody unchanged: Render env remains the documented secret store;
  values live only here and in this report to the owner (never
  committed, never logged elsewhere). In-memory secrets shredded.

## 2026-11-26 — bootstrap secret rotated: ADMIN_INITIAL_PASSWORD deleted, app independent

- Branch: `agent/ops/secret-rotation` from `eb86f87`.
- Rotation: `DELETE /services/srv-dc3g9q4ipgvc738jo7ug/env-vars/ADMIN_INITIAL_PASSWORD`
  → 204; GET env list confirms absent (20 vars remain).
- Triggered redeploy `dep-dc3oh1a9lscs73dcbp10`, `live` 01:18:33Z,
  commit `eb86f87` — matches. **Not stale.**
- Verification (no bootstrap secret in env): `GET /health` → 200
  (0.3 s); admin login with custodied password → 200 (1 attempt);
  `GET /api/v1/employees` (admin token) → 200 (0.6 s). App has no
  dependency on the bootstrap secret.
- Secrets posture: `E2E_*` (12 + 2 MFA secrets) in env = intended E2E
  custody. `BOOTSTRAP_ADMIN_PASSWORD` **kept** — it is the documented
  custody store for the current admin password, never read by the app
  (custom name, zero runtime dependency); removing it would destroy the
  only credential record with no benefit.

## 2026-11-26 — deploy dep-dc3ob78ae00c73cnpf8g LIVE @ 8c12425 (D1 TenantSwitcher fix)

- Branch: `agent/ops/render-watch-2` from `8c12425`.
  Deploy `dep-dc3ob78ae00c73cnpf8g`, `live` 01:06:09Z, commit `8c12425`
  — matches. **Not stale.**
- Live confirmation: `GET /health` → 200 (0.3 s); `GET
  /api/v1/employees` as existing `e2e_employee` → 200 (0.5 s, login 200,
  no new accounts created).
- Full smoke NOT re-run: unchanged since last green smoke (b1f1168);
  noted explicitly per scope.


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
