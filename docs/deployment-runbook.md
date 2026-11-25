# Deployment runbook — LibrePeople testing deploy (Render + Neon + R2)

Cloud counterpart to `docs/runbooks/local-deploy.md`. Local compose is
unchanged for development; **where the two differ, this file wins for the
testing deploy**. No live deploys are performed from here — this is config
and pipeline code only; execution is a later agent/owner step.

## 1. Architecture

| Piece | Where | Notes |
|---|---|---|
| Backend | Render web service `librepeople-backend` (Docker, `backend/Dockerfile`) | Single instance (`numInstances: 1`); health probe `GET /health` |
| Frontend | Render static site `librepeople-frontend` (`frontend/`, `npm ci && npm run build`) | SPA; `/*` rewrites to `/index.html` |
| Database | External **Neon Postgres** via `DATABASE_URL` | No managed Render DB exists for this deploy |
| Storage | Cloudflare **R2** via S3-compatible env (`R2_*`, `STORAGE_BACKEND=s3`) | Keys in Render secrets, never in git |
| Migrations | `preDeployCommand: python -m scripts.migrate upgrade` | Runs to completion **before** the release goes live; single instance, never concurrent |

Blueprint: `render.yaml`. Variable reference: `docs/env-inventory.md`.
Endpoint paths served under `/api/v1` (e.g. `/health`, `/health/db`,
`/api/v1/auth/login`).

## 2. First-time setup (owner, Render dashboard)

1. Create the blueprint: Render dashboard → New → Blueprint → point at this
   repo (`render.yaml` creates both services).
2. Create a Neon project + database; copy its pooled connection string
   (`?sslmode=require`) into the backend service as `DATABASE_URL`
   (`sync: false` — secret).
3. Create an R2 bucket + API token; set `R2_ENDPOINT_URL`, `R2_BUCKET`,
   and the token pair (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
   both `sync: false`).
4. Let Render generate `SECRET_KEY` (`generateValue: true`).
5. Set `BACKEND_CORS_ORIGINS` to the exact frontend origin
   (e.g. `https://librepeople-frontend.onrender.com`) — empty or `*`
   refuses to start in production.
6. Set `FIELD_ENCRYPTION_KEYS` (`key1:` + generated secret, `sync: false`)
   and `FIELD_ENCRYPTION_ACTIVE_KEY_ID` (`key1`).
7. Set `VITE_API_URL` on the frontend service to the backend URL +
   `/api/v1` (`sync: false`; baked in at build time).
8. Note the two deploy-hook URLs (service → Settings → Deploy Hook) and
   store them as GitHub Actions secrets `RENDER_BACKEND_HOOK` /
   `RENDER_FRONTEND_HOOK`; add synthetic-credential secrets
   `SMOKE_TEST_USERNAME` / `SMOKE_TEST_PASSWORD` (least-privilege account).
9. Seed the first SuperAdmin once (fail-closed: zero users otherwise):
   Render shell on the backend service, password via environment only —
   `ADMIN_INITIAL_PASSWORD='<strong password>' python -m scripts.seed_admin`.

No Oracle wallet files are uploaded and no `ORACLE_*` vars are set for this
deploy (Neon owns the data). The backend's local-Oracle fallback stays in
code for local use only.

## 3. Normal deploy (automatic)

Push to `main` → CI gate (`ci.yml`) → `deploy.yml`: validate commit → test
pipeline → build artefact → trigger both deploy hooks → wait for health →
verify `GET /health/db` (proves the `preDeployCommand` migration landed) →
`GET /health` + `POST /api/v1/auth/login` smoke with synthetic creds →
deploy SHA recorded as a run artifact + step summary.

## 4. Verify a release

- Backend: `curl https://<backend>/health` → 200; `/health/db` → 200.
- Frontend: open the URL, sign in with the synthetic account; API calls hit
  `/api/v1` on the backend origin from step 2.7.
- Migrate state (read-only): Render shell → `python -m scripts.migrate status`.

## 5. Rollback

No auto-downgrade, ever. On a failed health/smoke check the pipeline stops
and the failed check is the alert — nothing reverts by itself.

1. Read the last green SHA from a previous run's deploy record artifact.
2. Render dashboard → each service → Deploys → **Rollback to this deploy**.
3. Migrations are forward-only: the rolled-back release re-runs `upgrade`,
   a no-op at a current revision. `downgrade` is a deliberate manual act.

## 6. Where this differs from local-deploy.md

| Concern | Local (`local-deploy.md`) | This testing deploy |
|---|---|---|
| Database | Compose `postgres:16-alpine`, `DATABASE_URL` host `db` | External Neon; `DATABASE_URL` is a Render secret |
| Storage | `STORAGE_BACKEND=local` | `STORAGE_BACKEND=s3` + `R2_*` |
| Migrations | Container CMD runs `upgrade` at start | `preDeployCommand` (release step, single instance) |
| Env source | `.env` file from `.env.example` | Render dashboard values/secrets per `render.yaml` |
| Admin seed | `docker compose exec -e ADMIN_INITIAL_PASSWORD=…` | Render shell, same command, same env-only password |
| Frontend URL | nginx on `:80` | Render static site URL + `VITE_API_URL` baked at build |
