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
