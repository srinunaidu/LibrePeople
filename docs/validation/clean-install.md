# Clean Install

Python 3.11 + virtualenv `.venv311`; ortools 9.15 (from requirements); PostgreSQL for new installs (SQLite may be used only for local dev if already configured). Single Alembic head: `0047_expense_category_tenant_code`.

Commands (repo root `/Users/srinivas/LLM/Workforce/librepeople-prod`):
1. `python3.11 -m venv .venv311`
2. `.venv311/bin/pip install -r backend/requirements.txt`
3. Set env: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_INITIAL_PASSWORD` (and optional `ADMIN_INITIAL_USERNAME`, `ADMIN_INITIAL_EMAIL`).
4. `cd backend && ../.venv311/bin/python -m alembic upgrade head` (or run `python -m scripts.seed_admin`, which applies migrations first). Confirm head `0047`.
5. Frontend: `cd frontend && npm install && npm run build`
6. Start backend: `cd backend && ../.venv311/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000`
7. Start frontend: `cd frontend && npm run preview` (or `npm run dev`).

## Known gaps (not covered above — see pointers)

- **Seed roles.** Step 4 creates only the first SuperAdmin (fail-closed).
  The demo multi-role seed (SuperAdmin, HR Admin, Manager ×2, PayrollViewer,
  Associate ×5 per tenant) is documented separately in
  `docs/validation/SEED_DATA.md` (`make seed-demo`); demo seed refuses
  production targets and is idempotent.
- **MFA.** No MFA enrolment/verification step is part of clean install; if
  the deployment requires MFA, enrol it after the first SuperAdmin sign-in
  (account starts in `must_change_password` state) before handing over.
- **PayrollViewer note.** PayrollViewer is a read-scoped demo role from the
  seed — it exists only when the demo seed is loaded, never from step 4
  alone. Payroll runs themselves are blocked without a verified India rule
  pack (see `docs/validation/SEED_DATA.md` "What is NOT in the seed").
