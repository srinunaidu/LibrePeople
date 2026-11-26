# Local Cutover Drill — Evidence Log (LibrePeople)

Date: 2026-11-26. Branch: `agent/ops/local-cutover-drill` from `main` @ `0ac1a69`.
Scope: scratch PostgreSQL 16.16 in `/tmp` only (port 55436), synthetic data only,
no product code changes, no push. Base commit verified before branching.

## 1. Scratch source DB + migrations

- `initdb -D /tmp/lp_cutover_pg`, `pg_ctl -o "-p 55436 -k /tmp" start`,
  `createdb lp_cutover_src`.
- `alembic heads` → single head `0055_scim_external_id` (no merge needed).
- `alembic upgrade head` on empty DB → `0055_scim_external_id`, ~2.4 s, clean.

## 2. Minimal synthetic seed (direct ORM inserts, tenant `cutover-drill`)

Prereqs (not counted): 1 department (`CUT-D1`), 1 job (`CUT-J1`),
1 leave type (`CUT-ANNUAL`, 20 d/yr), 1 expense category (`CUT-TRV`).
Seeded exactly: **1 tenant, 2 users** (`cutover_admin` SuperAdmin,
`cutover_user` Associate), **5 employees** (`EMP-CUT-01..05`),
**2 leave balances** (EMP-01: 20+0/2 d; EMP-02: 20+5/0 d, 2026),
**1 expense claim** (EMP-01, INR 1250.50, `DRAFT`, "Synthetic drill claim").
All names/emails synthetic (`*.example.test`). Passwords dummy-local.

## 3. Dump → restore → verify

| Step | Evidence |
|---|---|
| `pg_dump -Fc` | **391,942 bytes**, ~0.1 s → `/tmp/lp_cutover_dump.fc` |
| `createdb lp_cutover_tgt` + `pg_restore` | clean, no errors, ~0.3 s |
| `alembic_version` src vs tgt | `0055_scim_external_id` = match |
| Row counts src = tgt | departments 1, jobs 1, employees 5, users 2, leave_types 1, leave_balances 2, expense_categories 1, expense_claims 1 |
| Spot-check md5(full row) src vs tgt | `employees[EMP-CUT-01]` `ebedb749…` match; `expense_claims[drill]` `f8777970…` match |

## 4. App checks against RESTORED db (uvicorn 127.0.0.1:55801)

Env: `DATABASE_URL`→tgt socket + dummy `SECRET_KEY` only at runtime
(+ dummy `FIELD_ENCRYPTION_*`, + tenant token — see notes N1, N2).

| Check | Result |
|---|---|
| `GET /health` | 200 `{"status":"healthy"}` |
| `POST /api/v1/auth/login` as `cutover_admin` | **200** (role SuperAdmin, MFA enrolled, no password reset) |
| `GET /api/v1/employees/?page_size=50` (admin) | 200, total **5** (`EMP-CUT-01..05`) |
| `GET /api/v1/expenses/claims` (admin) | 200, **1** claim (1250.50, DRAFT) |

N1 — MFA: SuperAdmin/HR endpoints 403 until MFA enrolled (by design, no grace
period). Enrolled via `/auth/mfa/enroll`→`confirm` with a locally generated
TOTP; enrollment needs `FIELD_ENCRYPTION_KEYS/_ACTIVE_KEY_ID` (dummy local
values used; production uses real keys — enrollment + `mfa_enabled` flag
survived the dump/restore, verified in step 4).
N2 — tenant attribution: login JWTs carry no `tenant` claim and
`TENANT_HOSTNAME_MAP` is read via `getattr` default (no such `Settings` field),
so requests resolve the legacy `default` tenant and custom-slug rows are
invisible (admin saw 0 rows at first). Served the checks with a token minted
by the app's own `create_access_token(..., {"tenant": "cutover-drill"})` —
the documented authoritative source (`tenancy.py` order: JWT claim first).
N3 — the background uvicorn did not survive between operator steps (twice);
restarted, all checks re-passed. Prefer a process supervisor in production.

## 5. Production cutover procedure (operator)

1. Freeze writes (maintenance page / connection draining at proxy).
2. `pg_dump -Fc` primary → checksum + byte count; copy artifact off-host.
3. Provision target, `pg_restore`, compare `alembic_version`, per-table counts,
   and ≥2 row checksums (as §3).
4. Point app config at target (`DATABASE_URL`), real `SECRET_KEY` +
   `FIELD_ENCRYPTION_*` from the vault (never dummy), verified hostname→tenant
   mapping or JWT-tenant path for every real slug.
5. Smoke: `/health` 200, admin login 200, tenant-scoped list counts vs §3,
   one write-path probe (e.g. submit→approve a test claim) then void it.
6. Cut traffic (DNS / LB repoint), monitor error budget + login rate.
7. Rollback-by-repoint: keep the old primary untouched until the bake window
   passes; rollback = repoint `DATABASE_URL`/LB back, no re-dump.

## 6. Explicitly NOT tested

DNS/TLS certs, connection draining under load, LB repoint, replication lag,
vault-sourced secrets, real IdP/JWT-tenant issuance, write-path cutover,
rollback-by-repoint execution, backup encryption/KMS, PITR.

## 7. Residual gaps

- `TENANT_HOSTNAME_MAP` has no `Settings` field (dead config path); custom
  tenants depend on JWT-claim attribution — verify before any real cutover
  smoke test or 0-row results mislead.
- Prod login mints no tenant claim: confirm how each tenant's callers get
  attribution (hostname map vs IdP claim) and test it, not just `default`.
- Uvicorn background flakiness (§N3): use systemd/supervisor + readiness gate.

## 8. Cleanup (done)

Server stopped, `dropdb` both DBs, `pg_ctl stop`, `rm -rf /tmp/lp_cutover_pg
/tmp/lp_cutover_dump.fc /tmp/lp_*` (tokens, logs, seed script); `git status`
shows only this file. No strays outside `/tmp`; no repo files touched.
