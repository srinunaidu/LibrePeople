# LibrePeople — environment inventory (testing deploy on Render + Neon)

Every variable the backend reads (`backend/app/core/config.py`) plus every
`VITE_*` variable the frontend reads, with purpose, required/optional,
safe default or placeholder, and whether it is a secret. **No real values
appear here — placeholders only.** Owner sets real values as Render
dashboard values (`value`) or secret references (`sync: false` / file);
see `render.yaml` and `docs/deployment-runbook.md`.

Legend: **Secret = YES** means the value must live in Render secrets
(`sync: false`) or `generateValue` — never in git, never in a `value:`.

## Backend (`backend/app/core/config.py`)

| Variable | Purpose | Required in production | Safe default / placeholder | Secret |
|---|---|---|---|---|
| `ENVIRONMENT` | Selects production fail-closed validation | Yes | `production` | No |
| `DATABASE_URL` | SQLAlchemy URL for the app database — **external Neon Postgres** for this deploy (no managed Render DB) | Yes | `postgresql://USER:PASSWORD@HOST/dbname?sslmode=require` (placeholder shape only) | YES (`sync: false`) |
| `SECRET_KEY` | Signs JWTs; min 32 chars enforced in production | Yes | none — Render `generateValue: true` | YES |
| `ALGORITHM` | JWT algorithm; pinned to `HS256`, any other value refuses to start | No | `HS256` | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime; must be ≤ 60 | No | `30` | No |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-token lifetime | No | `14` | No |
| `BACKEND_CORS_ORIGINS` | Exact frontend origin(s), comma-separated; empty or `*` **refuses to start** in production | Yes | `https://librepeople-frontend.onrender.com` (replace with real origin) | No (`sync: false`, not a secret but set per-deploy) |
| `FIELD_ENCRYPTION_KEYS` | `key_id:secret` pairs, comma-separated; decrypts existing PII, enables rotation | Yes | `key1:GENERATED-32-BYTE-SECRET` (placeholder) | YES (`sync: false`) |
| `FIELD_ENCRYPTION_ACTIVE_KEY_ID` | Which key id encrypts new writes | Yes | `key1` | No |
| `ADMIN_INITIAL_PASSWORD` | Seeds the first SuperAdmin (fail-closed: zero users without it); must pass password policy | Bootstrap only | none — set once in environment, then unset | YES (`sync: false`, one-shot) |
| `ADMIN_INITIAL_USERNAME` | First admin username | No | `admin` | No |
| `ADMIN_INITIAL_EMAIL` | First admin email | No | `admin@example.com` (placeholder) | No |
| `MIGRATE_ON_STARTUP` | Run Alembic at app start; this deploy migrates via `preDeployCommand` instead, so set `false` | No | `false` | No |
| `STORAGE_BACKEND` | Object-storage selector; `s3` = S3-compatible (Cloudflare R2) for this deploy | Yes | `s3` | No |
| `R2_ENDPOINT_URL` | R2 S3-compatible endpoint | Yes (with `s3`) | `https://ACCOUNTID.r2.cloudflarestorage.com` (placeholder) | No |
| `R2_BUCKET` | R2 bucket name | Yes (with `s3`) | `librepeople-docs` (placeholder) | No |
| `R2_ACCESS_KEY_ID` | R2 API token key id | Yes (with `s3`) | none — `sync: false` | YES |
| `R2_SECRET_ACCESS_KEY` | R2 API token secret | Yes (with `s3`) | none — `sync: false` | YES |
| `LOCAL_STORAGE_DIR` | Ephemeral local dir; unused when `STORAGE_BACKEND=s3` | No | `/tmp/librepeople-storage` | No |
| `LOG_LEVEL` | `DEBUG/INFO/WARNING/ERROR/CRITICAL` | No | `INFO` | No |
| `TRUSTED_PROXY_CIDRS` | CIDRs whose `X-Forwarded-*` headers are believed; empty = trust none | No | `` (empty) | No |
| `CONTENT_SECURITY_POLICY` | Overrides the conservative default CSP | No | `` (built-in default applies) | No |
| `EMAIL_PROVIDER` | `log` (default, no SMTP) or `smtp` | No | `log` | No |
| `SMTP_HOST` | SMTP relay host (only with `smtp`) | Only with `smtp` | `` | No |
| `SMTP_PORT` | SMTP relay port | Only with `smtp` | `587` | No |
| `SMTP_USERNAME` | SMTP auth username | Only with `smtp` | none — `sync: false` | YES |
| `SMTP_PASSWORD` | SMTP auth password | Only with `smtp` | none — `sync: false` | YES |
| `SMTP_USE_TLS` | STARTTLS on/off | No | `true` | No |
| `SMTP_FROM` | Envelope/from address | Only with `smtp` | `no-reply@example.com` (placeholder) | No |
| `PASSWORD_MIN_LENGTH` | Minimum password length; < 12 refuses to start everywhere | No | `12` | No |
| `PASSWORD_HISTORY_DEPTH` | Rejected password-reuse depth | No | `5` | No |
| `LOGIN_MAX_FAILED_ATTEMPTS` | Failed sign-ins before account lock | No | `5` | No |
| `LOGIN_FAILURE_WINDOW_SECONDS` | Window for counting failures | No | `900` | No |
| `LOGIN_LOCKOUT_SECONDS` | Lockout duration | No | `900` | No |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | Per-IP login attempts | No | `10` | No |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | Per-IP rate-limit window | No | `300` | No |
| `ALLOW_SELF_REGISTRATION` | Public sign-up; keep `false` in production | No | `false` | No |
| `ALLOW_DEV_SEED` | Loads sample departments/jobs/employees; **never** `true` in production | No | `false` | No |
| `PUBLIC_DIAGNOSTIC_ENDPOINTS` | Exposes detailed diagnostics unauthenticated | No | `false` | No |
| `JOB_WORKER_ENABLED` | Runs the in-process background-job worker (imports answer `202` and never apply without it) | No | `false` | No |
| `JOB_WORKER_POLL_SECONDS` | Idle poll interval | No | `2.0` | No |
| `JOB_WORKER_LEASE_SECONDS` | Job claim lease | No | `300` | No |
| `JOB_WORKER_SHUTDOWN_SECONDS` | Graceful-shutdown wait | No | `15.0` | No |
| `RETENTION_SCHEDULE_ENABLED` | Schedules the upload-retention job | No | `false` | No |
| `RETENTION_RUN_INTERVAL_HOURS` | Hours between retention runs; `0` disables | No | `24.0` | No |
| `BACKUP_ENABLED` | Declares an operator-arranged backup exists (reporting only) | No | `false` | No |
| `BACKUP_SCHEDULE` | Backup cadence description for `/admin/status` | No | `manual` | No |
| `BACKUP_LAST_SUCCESS_AT` | Last known-good backup timestamp (operator-maintained) | No | `` | No |
| `BACKUP_MAX_AGE_HOURS` | Staleness threshold for warnings | No | `24` | No |
| `DEFAULT_CURRENCY` | ISO 4217 fallback for legacy pay rows | No | `INR` | No |
| `PROJECT_NAME` / `VERSION` / `API_V1_STR` | Service identity (`LibrePeople`, `1.0.0`, `/api/v1`) | No | built-in | No |
| `RULE_PACK_DIR` | Rule-pack directory inside the image | No | `/app/rule_packs` | No |
| `ORACLE_DSN` / `ORACLE_USER` / `ORACLE_PASSWORD` / `ORACLE_WALLET_DIR` / `ORACLE_WALLET_PASSWORD` | Oracle ADB wallet path — **not used by this testing deploy** (Neon Postgres instead); local-Oracle fallback only | No | unset | YES for password fields if ever used |
| `OCI_NAMESPACE` / `OCI_BUCKET_NAME` / `OCI_CONFIG_FILE` / `OCI_PROFILE` | Oracle Object Storage — **not used by this testing deploy** (R2 instead) | No | unset | No |
| `PORT` | Injected by Render; uvicorn binds `$PORT` | No (platform-set) | `8000` | No |

## Frontend (`VITE_*`)

Read at build time via `import.meta.env`. Only one is used in `frontend/src`:

| Variable | Purpose | Required in production | Safe default / placeholder | Secret |
|---|---|---|---|---|
| `VITE_API_URL` | Backend base URL the SPA calls (e.g. `https://…/api/v1`); falls back to same-origin `/api/v1` when unset | Yes (set to backend URL) | `https://librepeople-backend.onrender.com/api/v1` (replace with real URL) | No (`sync: false`, baked into the static bundle at build time — never a secret) |
| `VITE_PROXY_TARGET` | Dev-server `/api` proxy target; dev/CI only, never production | No | `http://localhost:8000` | No |

Build identity (`RENDER_GIT_COMMIT` / `COMMIT_REF`) is injected by the
platform at build time; no owner action needed.

## CI/CD pipeline secrets (GitHub repository secrets — names only)

Used by `.github/workflows/deploy.yml`; never app runtime values:

| Name | Purpose |
|---|---|
| `RENDER_BACKEND_HOOK` | Render deploy-hook URL for the backend service |
| `RENDER_FRONTEND_HOOK` | Render deploy-hook URL for the frontend service |
| `SMOKE_TEST_USERNAME` | Synthetic login-smoke username (least-privilege test account) |
| `SMOKE_TEST_PASSWORD` | Synthetic login-smoke password |

Owner setup required: create each of the four names above under the
repository's Actions secrets before the first push-to-`main` deploy.
