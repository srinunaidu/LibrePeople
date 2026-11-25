# API Discrepancy Report — contract vs implementation (`216e869`)

Scope: `docs/API_CONTRACT.md` vs `backend/app/api/v1/endpoints/*.py`. No code changed. Secrets: repo-root `API.md` is untracked and was not read (see inventory header).

## Result: 0 documented endpoints missing · 0 frontend mismatches · 6 notes below

## D-01 — Dead test helper inside prod package (Low)
- Impl: `backend/app/api/v1/endpoints/test_assets.py` — 0 `@router` routes; only location that breaks the "one module = one mount" rule in `backend/app/api/v1/api.py:2-36`.
- Contract: n/a (not documented, not mounted).
- Fix: move file to `backend/tests/` (smallest: `git mv backend/app/api/v1/endpoints/test_assets.py backend/tests/`).

## D-02 — Phase-7 reports auth stricter than contract (Medium)
- Contract (`docs/API_CONTRACT.md:129-138`): all six rows marked `U` (any authenticated).
- Impl (`backend/app/api/v1/endpoints/reports.py`): `dashboard:24`, `headcount:33`, `leave:41`, `labor-cost:49` require `REPORTS_ROLES` (SuperAdmin/HR/PayrollViewer); `attendance:58` requires `MANAGER_ROLES`; `audit:67` requires `ADMIN_ROLES`. Associate/Manager callers get 403 where the contract promises 200.
- Fix: either widen impl (not recommended — least privilege looks deliberate) or correct the contract's Access column to `R`/`M`/`A` per row (one-table edit).

## D-03 — Contract Auth section is a Phase-1 snapshot (Medium-Low)
- Contract (`docs/API_CONTRACT.md:7-11`): only `POST /auth/login`, `POST /auth/register`.
- Impl (`backend/app/api/v1/endpoints/auth.py:169-1091`): 16 routes — `refresh` (rotation + reuse-revokes-family, `:318`), `logout`, `me`, `mfa/*` (5), `password`, `users/{id}/password`, `users` CRUD, `impersonate` (SuperAdmin-only, `:1091`).
- Fix: append the 14 rows to the contract's Auth table (docs-only).

## D-04 — Employees PATCH + history undocumented (Low)
- Contract (`docs/API_CONTRACT.md:13-19`): `PUT /employees/{id}` only.
- Impl (`backend/app/api/v1/endpoints/employees.py:565` `PATCH`, `:587` `PUT`, `:609` `GET /{id}/history`): both writes `ADMIN_ROLES`; history `ALL_ROLES` + visibility filter.
- Fix: add two rows to the contract table (docs-only).

## D-05 — Post-Phase-7 growth undocumented by design (Low, informational)
- Contract covers Phases 1–7 only. Implemented but undocumented: time corrections + period-locks (`time_attendance.py:272-413`), scheduling drafts/versions/attendance (`scheduling.py:204-717`), leave ledger/reconciliation/payroll-input (`leave.py:173-270`), reports metrics/joiners/leavers/attrition/payroll (`reports.py:88-629`), onboarding presets/readiness (`onboarding.py:123-255`), plus whole modules (core-hr, payroll, ess, expenses, assets, forecasting, platform, compliance, import-export, data-quality, client-onboarding, admin/*, break-glass, filings).
- Fix: no action unless contract scope is extended; inventory (`docs/api-inventory.md`) is the interim reference.

## D-06 — Spot-checks that passed (no action)
- Server-side enforcement (5): employees `GET /{id}` (`employees.py:381-384`, `ALL_ROLES` + `ensure_can_view_employee`); leave approve (`leave.py:340-351`, `MANAGER_ROLES` + reporting-line check); payroll finalize (`payroll.py:422`, `ADMIN_ROLES` + run-state guards); expenses L1/final (`expenses.py:399/420`, `MANAGER`/`ADMIN` + own-claim rule `:149`); break-glass grant (`break_glass.py:130-`, SuperAdmin + own-tenant refusal + 480-min TTL cap).
- Secrets: `UserOut` (`app/schemas/user.py:82-97`) exposes no hash/token; `LoginResponse` carries access token by design; `grep` for secret logging in endpoints returned 0 hits.
- Frontend: all 78 `api.*("…")` paths in `frontend/src/lib|pages` resolve to a backend route (incl. `POST /public/contact` via `public_router`, `core_hr.py:651`).
