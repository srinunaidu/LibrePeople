# Browser E2E Report — 2026-11-25

Branch `agent/qa/browser-e2e` from `216e869`. Scratch-only stack, synthetic data only, no push.

## Phase 1 — stack (non-default ports, /tmp)

- PG 16.16 (brew, no sudo): `127.0.0.1:55433`, data `/tmp/lp-e2e-pgdata`, db `librepeople_e2e`.
- `alembic upgrade head` → head OK. Seed: synthetic `pgadmin` SuperAdmin + OPS dept/job (mirrors `e2e_server.py`, no DB reset so migration state kept).
- Backend uvicorn `:18000`, frontend `vite preview :14173` (rebuilt dist with `VITE_API_URL` → `:18000`; dist is git-ignored).
- Verify: `GET /health` → 200; `POST /api/v1/auth/login` (pgadmin) → 200 + bearer token; frontend `/` → 200.
- Env note: system python3 runs the suites (`fastapi 0.162.0`, `sqlalchemy 2.1.5`); repo pins `oracledb`, no PG driver, so env-only `psycopg[binary]==3.3.9` installed `--user` (scratch host only, not committed). Node v26.8.2, Playwright 1.64.1, chromium headless (no `--with-deps`, download OK).

## Phase 2 — browsers

`KARMA_PYTHON=$(which python3) npx playwright test` (suite self-manages SQLite backend `:8010` + preview `:4173` per `playwright.config.ts`; guard blocks production hosts).

| Project | Result |
|---|---|
| desktop (21 spec files) | **100 passed** |
| responsive (`responsive.spec.ts`, 360/768/1024/1440) | **16 passed** |

Console errors / failed network: specs assert zero page errors and 200s on every route; all passed, so no failure traces/screenshots retained (only artifact dir, empty of failures).

Coverage: login+forced-password-change (`first-login`), MFA enroll/confirm (`p4-helpers`, exercised by P4 specs), legal-entity CRUD + 403 (`p4-legal-entity`), employee create + 403 (`p4-lifecycle`), leave apply/approve (`p4-time-leave`), ESS/Core route sweep (`redesign-e2e`), permission-denied 403s (`p4-expenses`, `p4-legal-entity`, `p4-lifecycle`).

Defects: 1 — `frontend/e2e/redesign-e2e.spec.ts:70`, spec asserted sidebar brand `/karmathy/i`, rebrand (66b751d) renders tenant name/"LibrePeople". Spec-only, severity low. Fixed (smallest: assertion → `/librepeople/i` + comment); `redesign-e2e` re-run 18/18, then full desktop 100/100.

NOT TESTED: helpdesk ticket create — no helpdesk feature exists in `frontend/src` and no spec covers it; nothing to script.

## Cleanup

Stopped uvicorn `:18000`, `vite preview :14173`, PG cluster; removed `/tmp/lp-e2e-pgdata`, `/tmp/lp-e2e-pgsock`, `/tmp/lp-seed-pg.py`, logs. Verified: `pg_isready -p 55433` refused, no `vite`/`uvicorn`/`postgres -D /tmp` processes remain.
