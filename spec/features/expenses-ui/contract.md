# Expenses UI — build contract (Tier 2)

Base: main @ 610edcd. Branch: `agent/ops/expenses-contract`.
Owner note: LP-EXP-001..003 deferral is **lifted for UI only on 2026-11-26**; backend scope is
unchanged (backend untouched by this slice).

## 1. Goal + scope

Ship employee + approver expenses UI wired to the real, verified backend — no fake data:

- **List** claims · **detail** per claim · **create** (employee) · **L1 approve**
  (Manager line) / **L2 approve + mark-paid** (HR/Admin) · **receipt upload + view**.
- UI states on every screen: `loading / empty / error / success / permission-denied`
  (role gate via `EmptyState`, never a blank page).
- Persistence: server is source of truth; refetch after each mutation (no optimistic
  local-only state).
- API wiring — exact paths (router prefix `/expenses`, `backend/app/api/v1/api.py:82`;
  route lines in `backend/app/api/v1/endpoints/expenses.py`):
  - `GET /expenses/claims` (:252) · `POST /expenses/claims` (:269) ·
    `GET /expenses/claims/{id}` (:314) · `PATCH /expenses/claims/{id}` (:325)
  - `POST /expenses/claims/{id}/submit` (:372) ·
    `POST /expenses/claims/{id}/l1-approve` (:398) ·
    `POST /expenses/claims/{id}/approve` (:419) ·
    `POST /expenses/claims/{id}/reject` (:439) ·
    `POST /expenses/claims/{id}/rework` (:461) ·
    `POST /expenses/claims/{id}/mark-paid` (:483)
  - `GET /expenses/categories` (:172) (create-form dropdown source)
  - `POST /expenses/claims/{id}/receipts` (:541, multipart, ≤10 MB) ·
    `GET /expenses/claims/{id}/receipts` (:594) · bytes via
    `GET /api/v1/files/{key}` (`backend/app/main.py:338`, `download_url` at `expenses.py:164`)
- Conventions: axios `api` client (`frontend/src/lib/api.ts:40-60`, baseURL `/api/v1`,
  Bearer `karmathy_token`, `X-Tenant-Slug`); `errorMessage`/`fieldErrors`/`isRetryable`
  (`api.ts:101-202`); page pattern `Layout` + `Alert`/`RetryableAlert` + `LoadingRegion` +
  `TableSkeleton` + `EmptyState` + `PageHeader`/`SectionCard`
  (exemplar `frontend/src/pages/admin/LeaveTypes.tsx:7-68`); routes lazy +
  `ProtectedRoute` + `TenantLayout /t/:slug/*` (`frontend/src/App.tsx:174-443`);
  checks `typecheck, check:routes, check:api-paths, build` (`frontend/package.json:10-20`).
- Traceability: LP-EXP-001/002/003 = `docs/product/requirements-traceability.csv:56-58`
  (currently DEFERRED; this UI slice does not change backend scope).

## 2. Acceptance criteria (11, each testable)

1. **Associate sees own claims only** — list calls `GET /expenses/claims` (visibility is
   server-enforced, `expenses.py:259-266`); UI passes no `employee_id` for Associates and
   renders empty-state when zero rows (no fabricated rows).
2. **HR/Admin queue sees all** — same endpoint surfaces team/all claims per
   `apply_visibility`; UI offers a status filter (`?status=`) matching `:264-265`.
3. **Create maps to `POST /expenses/claims`** — sends only
   `{employee_id, category_id, expense_date, amount, currency, description}`; never
   `status`/`payment_status` (schemas expose neither, `expenses.py:3-11`); new claim
   appears with `status=DRAFT, payment_status=UNPAID` (`:294-303`).
4. **Submit maps to `POST /expenses/claims/{id}/submit`** — DRAFT→SUBMITTED only;
   locked-claim 409 (`expense_claim_locked`) surfaces verbatim via `errorMessage`.
5. **L1 approve maps to `POST /expenses/claims/{id}/l1-approve`** — visible/enabled only
   for Manager+ roles on SUBMITTED claims (`:398-416`); Associate clicks are never sent.
6. **L2 approve + mark-paid map to `POST …/approve` then `POST …/mark-paid`** —
   HR/Admin only; mark-paid requires APPROVED+UNPAID or the
   `expense_invalid_payment_state` 409 is shown (`:483-520`).
7. **Reject/rework round-trip** — `POST …/reject {reason}` and `POST …/rework`
   (`:439-480`); rejected claim shows `rejection_reason`; rework returns it to DRAFT.
8. **Validation surfacing** — 422 arrays render per-field via `fieldErrors`
   (`api.ts:170-202`); archived-category 422 (`expense_category_inactive`) names the
   category; empty receipt file and >10 MB refusals show server text (`:558-572`).
9. **403/404 honesty** — 403 renders permission-denied `EmptyState` naming the role
   (cf. `LeaveTypes.tsx:66`); 404 renders removed-record message + reload (never a
   silent empty list); retry only when `isRetryable`.
10. **Receipts round-trip** — upload via multipart `POST …/receipts` on DRAFT/SUBMITTED
    claims only; list via `GET …/receipts`; download links use server `download_url`
    (`GET /api/v1/files/{key}`); no object-URLs or local blobs persisted.
11. **Exports out of scope** — no CSV/PDF/payroll-export button ships; non-goal §4 is
    respected (verified absent in backend).

## 3. Test plan

New vitest file: `frontend/src/pages/expenses/__tests__/expenses.test.tsx` (mock `api`).
14–18 tests: (1) list renders rows; (2) empty-state on zero rows; (3) loading skeleton;
(4) load-error RetryableAlert + retry; (5) Associate hides approve/pay buttons;
(6) HR shows queue + filter; (7) create posts exact body, no status fields;
(8) 422 maps to field errors; (9) submit posts exact path; (10) locked-claim 409 text;
(11) l1-approve posts exact path; (12) approve→mark-paid sequence + invalid-state 409;
(13) reject sends reason + shows it; (14) rework→DRAFT; (15) receipt upload multipart +
list + download_url; (16) 403 permission-denied EmptyState; (17) 404 removed-record;
(18) categories dropdown from `GET /expenses/categories`.
Backend untouched. Gates: `npm run typecheck`, `npm run check:routes`,
`npm run check:api-paths`, `npm run build` (all from `frontend/`).

## 4. Non-goals (verified absent in backend `expenses.py`)

Travel requests, advances, per-diem tables, itineraries (only the word "travel" is the
state-machine docstring `:5`); policy-limits engine; PDF/CSV export (reports CSV is a
separate module). Claims cover LP-EXP-001..003 list/create/approve/pay + receipts only.

## 5. Tier + file ownership

Tier 2. ONLY: `frontend/src/pages/expenses/*` (new: list/detail/create/components) +
one test file (§3) + `App.tsx` route additions (lazy imports, top-level
`/expenses`, `/expenses/:id` + mirrored `/t/:slug/expenses*` entries). No other files.
