# Provenance and exclusions

## Provenance

- Inventory date/method: WS1 dependency inventory on branch
  `feature/librepeople-production`; backend versions from `.venv311`
  `pip freeze`; frontend versions/licences from `frontend/package-lock.json`.
- Backend: `backend/requirements.txt` (19 pins) → 114 freeze rows. No backend
  lock file exists; nothing backend-side is lock-confirmed.
- Frontend: `frontend/package.json` (24 deps + 19 devDeps) →
  `frontend/package-lock.json` (538 `packages` entries, 335 top-level
  `node_modules/<name>` packages). Licence fields are citable to the lock file.
- No licence metadata was fetched from PyPI/npm registries; absent metadata is
  marked **UNVERIFIED**, never inferred.

## Source headers

- No `SPDX-License-Identifier` headers were found in sampled backend
  (`backend/app`) or frontend (`frontend/src`) sources.
- No `Copyright (c)` / `Licensed under` source headers were found in the same
  sample. The only copyright notice observed is the rendered marketing footer
  in `frontend/src/components/PublicLayout.tsx`:
  `© 2026 Karmathy. All rights reserved.` — a UI string, not a source licence
  header.

## Exclusions (per `.gitignore`, contents not inventoried)

The following are excluded from this SBOM by `.gitignore` policy; their
contents were **not** listed or inspected:

- Python: `__pycache__/`, `*.py[cod]`, `env/`, `venv/`, `.venv*/`, `.env`,
  `*.db*` (local sqlite test databases, e.g. `admin_*_test.db`).
- Oracle: `backend/wallet/*` (except `README.md`), `*.key`, `*.pem`,
  `*.wallet*`; local credential files (`adb_password*`, `*.rtf`,
  `admin-bootstrap.txt`, `admin-*.txt`, `.env.*`, `seed/dev/.credentials.out`).
- Node: `node_modules/`, `dist/`, `.turbo/`, npm debug logs.
- Playwright: `frontend/.e2e/`, `test-results/`, `playwright-report/`.
- IDE/OS: `.vscode/`, `.idea/`, `*.swp`, `.DS_Store`.

No LICENSE/NOTICE file is published by this document. Do NOT treat
`.gitignore` exclusion as licence clearance.
