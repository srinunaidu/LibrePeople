# Oracle Scope Decision — investigation (read-only, no Oracle install, no code changes)

**Classification: [Requires owner decision]**

## 1. Product requirements (PRD + traceability)

- `docs/product/PRD.md:85` — "No mandatory dependency on … Oracle Cloud…". Oracle is explicitly
  **not** a mandatory dependency.
- `docs/product/PRD.md:523,529` — Oracle ADB + Render appear only in §25 "Known baseline from the
  authoritative Karmathy audit": Oracle is described as the *audited configuration*, and
  "Oracle-specific code … spread across multiple files" + "migration history requires re-baselining"
  are listed as findings to remediate.
- `docs/product/PRD.md:548 (§25.1)` — audit finding "Oracle lock-in and migration baseline issues"
  maps to **"PostgreSQL standard; reproducible migrations" (P1)**. The release direction is
  PostgreSQL, not Oracle.
- `docs/product/PRD.md:422,502,618` — reference deployment is Docker Compose + **PostgreSQL**;
  installation acceptance requires a "fresh PostgreSQL migration"; the supported matrix is
  "Linux/Docker/PostgreSQL". No acceptance criterion names Oracle.
- `docs/product/requirements-traceability.csv` — **0 rows mention Oracle** (136 requirements:
  VERIFIED 2 / IMPLEMENTED 105 / IN PROGRESS 3 / BLOCKED 18 / DEFERRED 8). Oracle is **absent**,
  not Required, not VERIFIED/BLOCKED, and **not explicitly DEFERRED** (no DEFERRED row covers it).
- `docs/product/postgresql-migration.md:9-11` — "Existing Oracle installations: Oracle Autonomous DB
  **stays**… the Oracle chain is preserved and continues to work. New installs: PostgreSQL."
  Lines 47-50 leave four open owner questions, including **"(d) Whether to deprecate Oracle on the
  first PG cutover — product owner"**. The deprecation decision is explicitly pending.

Conclusion: Oracle is neither a release requirement nor explicitly deferred — its future is an
unresolved owner question. Hence [Requires owner decision], not [Required], [Explicitly deferred],
or a unilateral [Unsupported — remove claims].

## 2. Code reality (reads + grep only)

- Driver: `backend/requirements.txt:4` pins `oracledb==26.0.1`.
- Engine/wallet wiring: `backend/app/core/database.py:52-89` (oracledb connect args, wallet
  config_dir/wallet_location, `ORACLE_DSN` trio → `oracle+oracledb://:@`); settings
  `ORACLE_WALLET_DIR/_PASSWORD/_DSN/_USER/_PASSWORD` in `backend/app/core/config.py:16-27`;
  same branching mirrored in `backend/migrations/env.py:87`.
- Oracle-aware app code: `backend/app/core/booleans.py:7-18` (`is_true()` per-dialect rendering,
  Oracle `NUMBER(1)`); `backend/app/core/idempotency.py:59,249` (Oracle autoincrement + datetime
  notes); `backend/app/core/migrations.py:21` (Oracle failure modes).
- Migrations: `0030_india_employee_fields.py:38,77,165` (per-dialect `REGEXP_LIKE` vs SQLite `GLOB`
  dict); `0043_integrity_expand.py:155` (portability comment); `env.py:101` (VARCHAR/VARCHAR2,
  no PG-only syntax). No `FROM DUAL` / `SYSDATE` / `VARCHAR2` DDL found in the current
  `backend/migrations` tree (only comments and the per-dialect CHECK map).
- Wallet: `backend/wallet/` contains **only `README.md`** — no wallet files, no credentials
  (git-ignored by design). No live Oracle proof is possible from this tree; `README.md:5` confirms
  "PostgreSQL/Oracle live proof absent", and `docs/product/acceptance-evidence/summary.md:126`
  records "Oracle roundtrip out of scope (no wallet/schema here)".

## 3. Dialect compatibility

The chain is written **Oracle-aware in principle** (per-dialect CHECK map, `is_true()` helper,
portability comments, env.py dialect selection), but Oracle-cleanliness is **unproven in this
release line**: no wallet, no Oracle run evidence, acceptance harness excludes the Oracle
round-trip. Legacy Karmathy-era docs (`docs/validation/JOURNEYS.md`, `scripts/staging/*`,
`frontend/src/lib/projectStatus.ts:31,101-102`) claim staging journeys passed "against real
Oracle", but that predates the LibrePeople PostgreSQL-standard direction and is not release
evidence. Verdict: **partially coded, aspirational in this tree — not proven**.

## 4. Claims inventory (list only — NOT edited)

If the owner rules Oracle unsupported, these file:lines must be edited:
- `frontend/src/lib/seo.ts:122` (Oracle ADB marketing description)
- `frontend/src/lib/projectStatus.ts:31,101-102` (staging/Oracle quality-gate + ps_08/ps_09 claims)
- `frontend/src/pages/Homepage.tsx:319,323,343` ("Oracle ADB (mTLS)" integration pills/copy)
- `frontend/src/pages/marketing/PlatformShowcase.tsx:21,120`
- `frontend/src/pages/marketing/FAQ.tsx:16,27-28,40` (incl. Oracle cold-start answer)
- `frontend/src/pages/marketing/Security.tsx:9,21,114,117` ("Hosted on Oracle Cloud…")
- `frontend/src/pages/Solutions.tsx:8`; `frontend/src/pages/ClientOnboarding.tsx:56,498`
  (`oracle_adb` kind); `frontend/src/pages/Documentation.tsx:10`; `frontend/src/pages/Privacy.tsx:15`
- `backend/requirements.txt:4` (`oracledb` pin); `backend/app/core/database.py:52-89`;
  `backend/app/core/config.py:16-27,146`; `backend/migrations/env.py:87`;
  `backend/wallet/README.md` (whole file); `backend/app/core/booleans.py:7-18`,
  `idempotency.py:59,249`, `migrations.py:21` (Oracle branches)
- `docs/product/postgresql-migration.md` (Oracle-preservation statements, if superseded);
  `docs/product/acceptance-status.md:247` (oracle_migration_roundtrip.py ref);
  legacy `docs/validation/*`, `scripts/staging/*`, `scripts/test_adb_connection.py`,
  `scripts/render_deploy.py`, `.github/workflows/deploy.yml`, `seed/prod/seed_prod.py`,
  `seed/dev/seed_dev.py:10,495,544`, `scripts/import_csv_production.py`, `scripts/migration_sql/TENANT_SCOPING.sql`

## 5. Owner decision required

1. Keep Oracle as an **optional, untested** path (PostgreSQL is the proven standard), or
2. Declare Oracle **unsupported**: remove `oracledb` + wallet plumbing and all claims above, and
   close `postgresql-migration.md` questions (a)–(d).
Either way, no Oracle install/infra work was performed in this investigation.
