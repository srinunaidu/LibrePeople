# Neon PostgreSQL provisioning (synthetic, free tier only)

> Agent D — exclusive path: this file only. No product-code or migration changes.
> Secrets policy: connection strings and API tokens are NEVER written here.
> Placeholders `$NEON_API_KEY` / `$DATABASE_URL` denote redacted values in commands.

## 1. Account / project inventory (GET /projects, names/ids/dates only)

- API auth: `GET /users/me` → 200 (proves account access; plan: **free**).
- Organization: `Srinivas` / `org-fragrant-frost-58922924` / plan free / created `2026-11-25T15:30:51Z`.
- `GET /projects?org_id=…` → 200, **COUNT 1**:
  | name | id | created_at | region_id |
  |---|---|---|---|
  | royal-block-82027681 | royal-block-82027681 | 2026-11-25T15:32:44Z | aws-ap-southeast-1 |
- No project named `librepeople-testing` existed. Per "avoid duplicates / USE existing"
  the pre-existing project above (auto-created minutes after the org, same day) was
  **reused** and a new empty database was created inside it — no second project was
  created (deviation from the literal name, preserves free-tier quota).

## 2. Region choice

- `GET /regions` → 200, 11 regions offered. **AWS ap-south-1 (Mumbai) was NOT
  offered**, so it could not be selected.
- Existing project region `aws-ap-southeast-1` (AWS Asia Pacific, Singapore) is the
  closest offered region to ap-south-1/India by latitude/longitude among the list,
  hence kept. No region change (non-destructive rule).

## 3. Project / branch / role / database (names + timestamps, never secrets)

- Project: `royal-block-82027681` / PG 18 / created `2026-11-25T15:32:44Z`.
- Branch (default, primary): `production` (`br-dawn-wind-bizset2l`), ready, created `2026-11-25T15:32:44Z`.
- Role: `neondb_owner` (password auth), created `2026-11-25T15:32:44Z`.
- Databases: `neondb` (default, id 33051) + **`librepeople_testing` (new, id 33108,
  owner `neondb_owner`, created `2026-11-25T15:49:22Z`)** via
  `POST /projects/{id}/branches/{branch}/databases` → 201.
- Endpoints (hosts ONLY, no credentials):
  - direct: `ep-wispy-dream-bizlemgn.c-5.ap-southeast-1.aws.neon.tech`
  - pooled: `ep-wispy-dream-bizlemgn-pooler.c-5.ap-southeast-1.aws.neon.tech`
  - proxy: `c-5.ap-southeast-1.aws.neon.tech`
  - `sslmode=require` on both connection URIs (client-enforced TLS).

## 4. Connection handoff (no strings stored)

- Connection strings (pooled + direct) obtained via `GET .../connection_uri`
  and used ephemerally from environment only. Stored as:
  **"delivered to Render env step (Agent E handoff: project
  royal-block-82027681 / branch production / role neondb_owner /
  host region aws-ap-southeast-1)"**.

## 5. Validation (migration execution explicitly OUT of scope — Agent E/pipeline runs it)

| # | command (redacted) | exit | time | result |
|---|---|---|---|---|
| 1 | `psql "$DATABASE_URL" -c 'SELECT 1;'` (direct) | 0 | ~0.6s | `1` — endpoint responds |
| 2 | `psql "$DATABASE_URL" -c 'SHOW server_version; SELECT version(); SHOW ssl;'` (direct) | 0 | ~0.4s | PG `18.7 (3190d2f)` aarch64; `SHOW ssl = off` (expected: Neon terminates TLS at proxy; client enforces via `sslmode=require`) |
| 3 | `psql "$DATABASE_URL" -c "SELECT count(*) ... WHERE table_schema='public';"` (direct, `librepeople_testing`) | 0 | ~0.4s | `0` tables — DB empty, no migrations run here |
| 4 | `psql "$DATABASE_URL" -c 'SELECT 1;'` (pooled) | 0 | ~0.4s | `1` — pooler host responds |
| 5 | empty-check (pooled, `librepeople_testing`) | 0 | ~0.4s | `0` tables — empty confirmed on both endpoints |
| 6 | `SELECT ssl, cipher FROM pg_stat_ssl WHERE pid = pg_backend_pid();` | 0 | — | `f` / empty — expected (proxy-terminated TLS, backend sees plaintext) |

- API auth for URI fetch used `export NEON_API_KEY=$(...)` read programmatically
  from repo-root `API.md`; the token value never appears in logs or this doc.
- Disconnected after checks; no sessions left open.

## 6. Free-tier limits observed (read-only)

- Plan `free_v3`; owner `branches_limit: 10`; project quota reset `2026-12-01T00:00:00Z`.
- Compute autoscale `0.25–2 CU`, `suspend_timeout_seconds: 0` (scale-to-zero; endpoint
  seen `idle`/`suspended`, cold start ≈ sub-second here).
- `branch_logical_size_limit: 1024` MB; `history_retention_seconds: 21600` (6 h);
  usage counters all `0` at provision time.
- Pooler: `pooler_enabled: false`, mode `transaction` (pooled host still resolvable
  and validated); no paid-tier selection was made or confirmed.

## 7. What remains (not this agent)

1. Migration execution by the deploy pipeline (Agent E) against `librepeople_testing`.
2. Backups via `pg_dump` + Neon branching (6 h PITR on free tier is not a backup).
3. Optional follow-up: rename project to `librepeople-testing` via console if the
   team wants the literal name (cosmetic, non-blocking).
