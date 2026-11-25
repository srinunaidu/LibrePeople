# LibrePeople — Render deployment watch

Dated, append-only record of Render testing-deploy observations.
(Karmathy-era history lives in `docs/DEPLOYMENT.md`; this file starts
with the LibrePeople `librepeople-backend` service.)

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
