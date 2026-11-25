# Render deployment evidence — LibrePeople testing deploy (Agent E)

Branch: `agent/ops/render-deploy` (from `d8e212c`). Status as of
2026-11-25T16:17Z: **frontend LIVE, backend BLOCKED on a migration bug
(outside this agent's fix allowance). No production deploy; testing only.**

Credentials policy: tokens and connection strings were read from repo-root
`API.md` and passed via environment only. No values appear here or in any
commit — names only, marked "set, not shown" where secret.

## 1. Service inventory (existing + created, no duplicates)

Pre-existing (other project, suspended, untouched — NOT reused, different app):

| name | id | region | status |
|---|---|---|---|
| karmathy-backend | srv-dba9ak8m7kps73fvig10 | singapore | suspended |
| karmathy-frontend | srv-dba9alfbtjjs73e9ut60 | (static) | suspended |

Created 2026-11-25 ~15:55Z (owner `My Workspace`, free tier, repo
`https://github.com/srinunaidu/LibrePeople`, branch `main`, repo visibility
unchanged):

| name | id | type | plan | region | URL |
|---|---|---|---|---|---|
| librepeople-backend | srv-dc3g9q4ipgvc738jo7ug | Docker web service (`./backend/Dockerfile`, context `./backend`, `healthCheckPath /health`, `numInstances 1`, `preDeployCommand: python -m scripts.migrate upgrade`) | free | singapore | https://librepeople-backend.onrender.com |
| librepeople-frontend | srv-dc3g9s0u01pc73ej79lg | static site (`rootDir frontend`, `npm ci && npm run build`, publish `./dist`, 1 rewrite rule `/* → /index.html`, id rdr-dc3g9s0u01pc73ej7ab0 — a duplicate created by the API was deleted) | free (static) | CDN | https://librepeople-frontend.onrender.com |

## 2. Environment variables (NAMES only — values never stored)

Backend (`librepeople-backend`), all set via API at creation:
`DATABASE_URL` (secret, set, not shown — Neon pooled URI for
`librepeople_testing`, `sslmode=require`, fetched via
`GET /projects/royal-block-82027681/connection_uri`), `SECRET_KEY`
(generated, set, not shown), `ALGORITHM=HS256`,
`ACCESS_TOKEN_EXPIRE_MINUTES=30`, `ENVIRONMENT=production`,
`BACKEND_CORS_ORIGINS=https://librepeople-frontend.onrender.com` (exact
origin, verified — no placeholder mismatch), `FIELD_ENCRYPTION_KEYS`
(secret, set, not shown), `FIELD_ENCRYPTION_ACTIVE_KEY_ID=key1`,
`STORAGE_BACKEND=local` (deviation from `render.yaml`'s `s3` documented
below), `MIGRATE_ON_STARTUP=false`, `RULE_PACK_DIR=/app/rule_packs`,
`LOG_LEVEL=INFO`, `JOB_WORKER_ENABLED=true` (see §7),
`ADMIN_INITIAL_PASSWORD` (one-shot synthetic, set, not shown — app seeds
the bootstrap admin at startup; **delete/rotate after first successful
boot per runbook**; boot never succeeded, so it is still pending).
R2 vars (`R2_*`) intentionally NOT set yet. `VITE_API_URL` on the frontend
= `https://librepeople-backend.onrender.com/api/v1` (verified correct).

## 3. Deploy history

| deploy | service | commit | result (UTC) |
|---|---|---|---|
| dep-dc3g9qcipgvc738jo9ag | backend | 51affccc | `update_failed` 15:57:15 — `ModuleNotFoundError: No module named 'psycopg2'` (fix round 1, §4) |
| dep-dc3g9s8u01pc73ej7ai0 | frontend | 51affccc | **`live`** 15:56:38 |
| dep-dc3ge9rm8hqs7392ms40 | backend | 51affccc | `update_failed` 16:05:38 — same-commit rebuild, same `psycopg2` error (confirms root cause) |
| dep-dc3gfkjrjlhs73fq12ug | backend | d142ad12 (fix branch; service branch temporarily pointed here, reset to `main` afterwards so the lead's merge auto-deploys) | `update_failed` 16:09:49 — new failure: `0012_leave_ledger` `DuplicateObject` (BLOCKED, §5) |

Note: free tier skips `preDeployCommand`
("Predeploy command not run. Commands can only run on paid instance
types"). Harmless here: the image `CMD` runs
`python -m scripts.migrate upgrade` before uvicorn binds, so migrations
still gate the release. `/health/db` will prove it once boot succeeds.

## 4. Fix round 1 (done, committed d142ad1 — minimal product-code fix)

`DATABASE_URL=postgresql://…` makes SQLAlchemy default to the psycopg2
driver, but `backend/requirements.txt` shipped no Postgres DBAPI driver
(Oracle-only image). Fix: +1 line `psycopg2-binary==2.9.10` (manylinux
wheels exist for the image's Python 3.11; verified absent only on the
local 3.15 interpreter, which has no wheel — see test skip note).
Regression test `backend/tests/test_postgres_driver.py`: pins the
requirement in `requirements.txt` (passes everywhere) + proves
`sqlalchemy.dialects.registry.load("postgresql").dbapi` imports
(`importorskip("psycopg2")` where the local interpreter cannot install
it; runs for real in CI/image). Checks run:
`ci/check_requirements.py` → clean; app startup probe → ok (12 routes);
new tests → 1 passed, 1 skipped (local; live-load runs in CI/image).
Full suite `bash ci/run_backend_tests.sh` → EXIT 1 with failures in
`security_headers`, `import`, `india_payroll`, `payroll_framework_restart`
(1 each), `reset_admin_password` (9, incl. a `BACKEND_CORS_ORIGINS`
production-guard error), `scheduling` (1) — all in suites untouched by
this change (the pin cannot affect the local run: the local interpreter
never installs from `requirements.txt`), `migration_test_suite` 67/67
passed. Treat as pre-existing; lead to confirm against `main`.

## 5. BLOCKED — fix round 2 not taken (migration file, out of allowance)

Verbatim tail (backend `dep-dc3gfkjrjlhs73fq12ug`, 2026-11-25T16:10:09Z):

```text
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateObject) type "leaveledgerentrytype" already exists
[SQL: CREATE TYPE leaveledgerentrytype AS ENUM ('ACCRUAL', 'ENTITLEMENT', 'CARRY_OVER', 'USAGE', 'ADJUSTMENT', 'EXPIRY', 'ENCASHMENT')]
```

Root cause (verified against the SQLAlchemy 2.0.29 sources matching the
pinned version): `0012_leave_ledger.py` guards its PG enum with generic
`sa.Enum(..., create_type=False)` plus `_ensure_entry_type(checkfirst=True)`.
But generic-`Enum.create_type` was only added in **SQLAlchemy 2.1**; in
2.0.29 the kwarg never reaches the PostgreSQL impl
(`adapt_emulated_to_native` only propagates `create_type` when
`_is_native_for_emulated`, false for generic `Enum`), so the adapted
`postgresql.ENUM` keeps `create_type=True` and `op.create_table` emits an
unconditional `CREATE TYPE` after the type already exists (via
`_ensure_entry_type`/0001 baseline) → `DuplicateObject` → whole
`upgrade head` rolls back. Deterministic on every PostgreSQL retry;
SQLite/Oracle never exercise it (VARCHAR path — which is why CI is green).
Neon state confirms clean retry: 1 public table (`alembic_version`, zero
rows), zero stray enum types — no manual cleanup needed.

Recommended lead fix (migration-semantics-preserving, not applied here):
in `0012_leave_ledger.py` COLUMNS, use `postgresql.ENUM(..., create_type=False)`
(2.0.29 honors `create_type` on the PG impl; compiles to VARCHAR on
SQLite/Oracle as today) and keep single creation in `_ensure_entry_type`.
Alternative: bump SQLAlchemy to ≥2.1 (larger blast radius — Oracle path,
solver pins — not recommended). After fix: merge to `main` → autoDeploy
rebuilds (service branch already reset to `main`) → expect head `0048`,
then continue §6.

## 6. Smoke (timestamps UTC 2026-11-25)

| check | result |
|---|---|
| frontend `GET /` | **200** (~0.07 s, 16:17Z) |
| backend `GET /health` | unreachable (connection timeout — never had a live deploy; expected while BLOCKED) |
| backend `GET /health/db` (expect `current=head 0048`) | not reached — BLOCKED |
| seeded-admin login + `GET /api/v1/employees` | not reached — bootstrap env is set but the app never booted; run after unblock, then delete `ADMIN_INITIAL_PASSWORD` |
| frontend console errors | not reached (backend down) |
| migrations | `apex/0048` NOT reached; chain fails at `0012` on PostgreSQL |

## 7. Worker verdict — no separate worker service required

The job worker is in-process (`JOB_WORKER_ENABLED`, default false,
`app/main.py` starts `JobWorker` after migration; single instance, claim
is a conditional update). No Render background-worker/private service
needed. Set `JOB_WORKER_ENABLED=true` on the backend (imports otherwise
answer `202` and never apply). `RETENTION_*`/`BACKUP_*` left at defaults
(reporting-only; no backup arranged on free tier).

## 8. Costs observed / remains

Cost: **$0** — both services on free tier; no paid selection made or
confirmed; Neon free (`free_v3`); no custom domain purchased (Render TLS
is automatic on `*.onrender.com`).
Remains for lead: (a) apply §5 fix, merge to `main`, watch auto-deploy to
live; (b) verify `/health/db` = head `0048`; (c) run §6 smoke incl. admin
bootstrap login, then **delete `ADMIN_INITIAL_PASSWORD`** (rotate per
runbook); (d) NO bulk synthetic seed on cloud (Agent F owns E2E data);
(e) R2 wiring later (`STORAGE_BACKEND=s3` + `R2_*` — currently `local`,
ephemeral on free tier); (f) GitHub deploy-hook secrets + synthetic smoke
creds per `docs/env-inventory.md` §CI/CD if the `deploy.yml` pipeline is
wanted; (g) confirm §4 suite failures are pre-existing on `main`.
