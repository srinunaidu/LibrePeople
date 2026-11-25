# Commands Run — Audit Evidence Log

**Target:** `feature/hcm-slack-revamp` — started at `75c3cc5`; frontend advanced to `91024a2` during the audit,
with 10 uncommitted frontend files at close. Backend is unchanged across that range. · **Date:** 2026-10-19
**Working copy:** `/Users/srinivas/LLM/Workforce/Karmathy`
**Environment:** macOS (darwin) · Python **3.15** in a throwaway venv at
`/private/var/.../T/opencode/karmathy-venv` · Node/npm (repo toolchain)

> **Test-environment caveat.** The pinned `pydantic==2.7.4` and `sqlalchemy==2.0.29` do not build on Python 3.15
> (`maturin`/PyO3 max 3.12; SQLAlchemy asserts on `__static_attributes__`). The backend suites were therefore run in
> a throwaway venv with `fastapi 0.146.0`, `SQLAlchemy 2.1.5`, `pydantic 2.14.1`, against SQLite. Behaviour
> differences from the pinned versions are possible but none were observed. Nothing in the repository was modified.
> No secrets, tokens or connection strings are reproduced below.

---

## 1. Repo state and scope

| Command | Output summary |
|---|---|
| `git branch --show-current` | `feature/hcm-slack-revamp` (throughout) |
| `git rev-parse --short HEAD` at start | `75c3cc5` |
| `git status --short` at start | empty — clean working tree |
| `git rev-parse --short HEAD` at close | `91024a2` — "Phase 2: app shell, command palette, keyboard shortcuts, mobile nav" |
| `git status --short` at close | 10 modified **frontend** files (see below); `docs/audit/` untracked |
| `git diff --stat 75c3cc5..91024a2` | **frontend only** — 13 files, +1235/−358; no backend change |
| `git diff --name-only` at close | `frontend/package{,-lock}.json`, `Layout.tsx`, `SecondarySidebar.tsx`, `ThemeToggle.tsx`, `TopBar.tsx`, `ui/inputs.tsx`, `index.css`, `Homepage.tsx`, `tailwind.config.js` |
| `ls` | `backend/`, `frontend/`, `docs/`, `scripts/`, `render.yaml`, `DOCUMENT.md`, `PHASE0_AUDIT.md`, `ENHANCEMENT_INVENTORY.md` |
| `find backend/app -maxdepth 2 -type d` | `api/v1/endpoints`, `core`, `crud`, `models`, `schemas`, `services`, `db` |
| `ls backend/app/api/v1/endpoints/*.py \| wc -l` | **26** files (25 registered routers + `__init__`) |
| `grep -c "include_router" backend/app/api/v1/api.py` | **25** |
| `ls backend/app/models/*.py \| grep -v __init__ \| wc -l` | **21** files (20 with mapped classes + `base.py`) |

## 2. Inventory counts

| Command | Output summary |
|---|---|
| Python: `len(Base.metadata.tables)` after importing all models | **77 tables** (76 models + `idempotency_records`) |
| Python: count `APIRoute`s by expanding `_IncludedRouter` | **164 paths / 236 operations** |
| Python: `len(app.openapi()["paths"])` | **164** (matches the route walk) |
| `grep -rn "tenant_id" backend/app/models \| wc -l` | **0** |
| `grep -c "CREATE TABLE" docs/DB_SCHEMA.sql` | **22** (55 tables missing) |
| `wc -l docs/API_CONTRACT.md` | **150** (stops at Phase 7) |
| `grep -c "CREATE TABLE" scripts/migration_sql/TENANT_SCOPING.sql` | migration exists; **not applied** |
| `grep -rn "create_all" backend/app` | `app/main.py:103` only (startup daemon thread) |
| `ls backend/alembic.ini backend/migrations` | **not found** |

**RBAC classification script** (walks every API route, collects dependency names, classifies the operation):

```python
# simplified — run from backend/ with the throwaway venv
# expand application.routes -> _IncludedRouter.original_router -> APIRoute
# collect dep.call.__name__ recursively; "admin" -> admin, "current_user" -> any-auth
```

| Result | Count |
|---|---|
| Operations using `get_current_admin_user` | **127** |
| Operations using `get_current_active_user` (any role) | **101** |
| Public (no auth dependency) | **8** |
| **Total** | **236** |

## 3. Backend test suites (all pass unless stated)

Run from `backend/` with the throwaway venv:

```bash
python smoke_test.py
python smoke_test_phase2.py
python smoke_test_phases_3_7.py
python smoke_test_client_onboarding.py
python smoke_test_all_phases.py
python security_test_suite.py
python visibility_test_suite.py
python ops_model_test_suite.py
python import_test_suite.py
python data_quality_test_suite.py
python metrics_test_suite.py
python ../scripts/e2e_lifecycle.py
python ../scripts/verify_tenant_isolation.py
```

| Suite | Result |
|---|---|
| `smoke_test.py` | **6 steps, complete** (auth, department, employee, list, 401) |
| `smoke_test_phase2.py` | **complete** (hire + onboarding summary) |
| `smoke_test_phases_3_7.py` | **39 passed, 0 failed** |
| `smoke_test_client_onboarding.py` | **20 passed, 0 failed** |
| `smoke_test_all_phases.py` | **67 passed, 0 failed** |
| `security_test_suite.py` | **66 passed, 0 failed** |
| `visibility_test_suite.py` | **29 passed, 0 failed** |
| `ops_model_test_suite.py` | **40 passed, 0 failed** |
| `import_test_suite.py` | **43 passed, 0 failed** |
| `data_quality_test_suite.py` | **44 passed, 0 failed** |
| `metrics_test_suite.py` | **41 passed, 0 failed** |
| `scripts/e2e_lifecycle.py` | **40 passed, 0 failed** |
| `scripts/verify_tenant_isolation.py` | **0 passed, 5 failed** — expected; this is the evidence for A2-12 |

**Total across passing suites:** 6 + 39 + 20 + 67 + 66 + 29 + 40 + 43 + 44 + 41 + 40 = **435 numbered checks**,
plus the phase-2 smoke flow (which prints steps, not a total). The earlier "492" figure was an arithmetic error that
double-counted the 40 e2e checks; it is corrected in `AUDIT_REPORT.md` §A4.1.

> `scripts/live_e2e.py` was **not** run: it requires live credentials beyond the admin login and can create data.

## 4. Frontend build and types

| Command | Output summary |
|---|---|
| `cd frontend && npx tsc --noEmit` | **pass** (no output) |
| `npm run build` | **pass** — current tree: `index.js` **604.63 kB** (**179.61 kB gzip**), CSS **37.96 kB** (8.18 kB gzip), **263 modules**; at `75c3cc5`: 467.02 kB (133.73 kB gzip), 152 modules. Vite warns the chunk is >500 kB |

> The build writes only to the git-ignored `frontend/dist/`; no source or config was changed.
| `wc -l src/pages/*.tsx \| sort -rn` | Recruiting **600**, Platform **543**, ClientOnboarding **515**, Design **421**, Homepage **370**, Offboarding **351**, Leave **346** |
| `grep -rn "useQuery\|useMutation" src \| wc -l` | **0** (provider wired, no hooks) |
| `grep -rn "lazy(" src/App.tsx` | **0** (all pages eagerly imported) |
| `grep -rn "karmathy_token" src` | `AuthContext.tsx:8,14,16`; `lib/api.ts:25` |
| `grep -n "navigate" src/pages/Login.tsx` | `navigate("/dashboard")` at `:30` — no `returnTo` |
| `grep -rn "window.prompt" src` | `Recruiting.tsx:573` |
| `grep -rn "/design" src` | `App.tsx:46`; `CommandPalette.tsx:40`; `TopBar.tsx:109`; `Layout.tsx:149,214` |

### Unused dependency scan

```bash
cd frontend
for d in $(node -e "console.log(Object.keys(require('./package.json').dependencies).join(' '))"); do
  n=$(grep -rl "from ['\"]$d\|from ['\"]$d/" src 2>/dev/null | wc -l | tr -d ' ')
  [ "$n" = "0" ] && echo "UNUSED $d"
done
```

Output: `@radix-ui/react-checkbox`, `@radix-ui/react-label`, `@radix-ui/react-progress`, `@radix-ui/react-slot`,
`@radix-ui/react-switch`, `@tanstack/react-virtual`, `date-fns`, `lucide-react` → **8 unused** (0 imports each).

## 5. Dependency audits

| Command | Output summary |
|---|---|
| `pip-audit -r backend/requirements.txt` | **20 advisory IDs** — `starlette`, `python-multipart`, `python-jose`, `ecdsa`, `python-dotenv` (see A4.4 for the list) |
| `cd frontend && npm audit` | **2 moderate** — `react-router` / `react-router-dom` (see A4.4) |
| `grep -n "email-validator" backend/requirements.txt` | **not found** — `EmailStr` relies on transitive resolution (`schemas/user.py:1`) |

## 6. Live endpoint checks

```bash
curl -s -o /dev/null -w "%{http_code} %{time_total}\n" https://karmathy-frontend.onrender.com/
curl -s -o /dev/null -w "%{http_code} %{time_total}\n" https://karmathy-backend.onrender.com/health
curl -s -o /dev/null -w "%{http_code} %{time_total}\n" https://karmathy-backend.onrender.com/health/db
curl -s -o /dev/null -w "%{http_code} %{time_total}\n" https://karmathy-backend.onrender.com/health/storage
curl -s -o /dev/null -w "%{http_code} %{time_total}\n" https://karmathy-backend.onrender.com/docs
curl -s -o /dev/null -w "%{http_code} %{time_total}\n" https://karmathy-backend.onrender.com/openapi.json
```

| URL | Status | Time | Note |
|---|---|---|---|
| `https://karmathy-frontend.onrender.com/` | **200** | 0.38 s | static SPA |
| `https://karmathy-backend.onrender.com/health` | **200** | **42.44 s** | cold start |
| `.../health/db` | **401** | 0.13 s | operator-only; docs say public |
| `.../health/storage` | **401** | 0.19 s | operator-only; docs say public |
| `.../docs` | **200** | — | Swagger UI |
| `.../openapi.json` | **404** | — | schema is at `/api/v1/openapi.json` (`main.py:36`) |
| `.../api/v1/openapi.json` | **200** | 45.58 s | second cold start |

### Authenticated checks

A read-only login was performed in the browser against the live backend using the **documented default admin
credential** (authorised by the owner). The script stored the token in the page's `localStorage` and returned only
`{status, role, username, hasToken}` — **the token was never printed or persisted outside the browser session**.

| Check | Result |
|---|---|
| Login | **200**, role **SuperAdmin**, token present |
| Default credential active in production | **Yes** — finding A5-03 |
| Authenticated a11y pages | `/dashboard`, `/recruiting`, `/leave`, `/time`, `/platform` |

No write operations were performed. No records were created or modified.

## 7. Accessibility and contrast

**Live DOM audit** (browser `evaluate`, per page): counts `input/select/textarea` without `aria-label`,
`aria-labelledby`, `label[for]`, or ancestor `<label>`; buttons without text/`aria-label`/`svg title`; images without
`alt`; `<main>`/`<nav>`/`<header>`; `h1` count; heading-order jumps; skip link; and low-contrast leaf text.

| Page | Controls | Unlabelled | Unnamed buttons | `alt` gaps | `h1` | Order | Skip link | Low contrast |
|---|---|---|---|---|---|---|---|---|
| Homepage | 0 | 0 | 0 | 0 | 1 | ✅ | ❌ | — |
| `/dashboard` | 0 | 0 | 0 | 0 | 1 | ✅ | ✅ | 8 |
| `/recruiting` | 6 | 0 | 0 | 0 | 1 | ✅ | ✅ | 2 |
| `/leave` | 10 | 0 | 0 | 0 | 1 | ✅ | ✅ | 2 |
| `/time` | 3 | 0 | 0 | 0 | 1 | ✅ | ✅ | 2 |
| `/platform` | 0 | 0 | 0 | 0 | 1 | ✅ | ✅ | 2 |

**Contrast formula** (`luminance` per WCAG 2.x; ratio = `(Lmax+0.05)/(Lmin+0.05)`):

| Token | Hex | Ratio on white | Required | Result |
|---|---|---|---|---|
| Teal | `#06B6D4` | **2.43:1** | 4.5:1 (normal text) | ❌ |
| Green | `#10B981` | **2.54:1** | 4.5:1 | ❌ |
| Warning | `#D97706` | **3.19:1** | 4.5:1 | ❌ |
| Violet | `#8B5CF6` | **4.23:1** | 4.5:1 | ❌ |
| Breadcrumb `/` | computed | **1.42:1** | 4.5:1 | ❌ |
| Breadcrumb `›` | computed | **1.48:1** | 4.5:1 | ❌ |

**Lighthouse** (live, via the browser tool; accessibility / best-practices / SEO only — no performance benchmark or
device emulation):

| Page | Accessibility | Best Practices | SEO | Failures |
|---|---|---|---|---|
| Public homepage | **0.95** | 1.00 | 1.00 | insufficient colour contrast |
| `/platform` (authenticated) | **1.00** | 1.00 | 1.00 | none |

## 8. Documentation drift checks

| Command | Output summary |
|---|---|
| `head -20 docs/API_CONTRACT.md` | ends at Phases 1–7; no payroll/performance/benefits/learning/platform/ESS |
| `grep -c "CREATE TABLE" docs/DB_SCHEMA.sql` | **22** |
| `grep -n "Manager\|PayrollViewer" docs/AUTH_ROLES.md` | documents distinct permissions; code has **0** role helpers |
| `grep -rn "require_role" backend/app` | **0** |
| `grep -n "health/db\|health/storage" docs/DEPLOYMENT.md` | lists them as public; `main.py:155,181` requires operator |
| `grep -n "tenant\|visibility" docs/PHASE2_STATUS.md` | line 24 says 0/76; line 47 claims visibility "confirmed live" |
| `grep -c "tenant_id" scripts/migration_sql/TENANT_SCOPING.sql` | migration prepared, not applied |

## 9. Environment / pin checks

| Command | Output summary |
|---|---|
| `python --version` | **3.15** |
| `pip install -r backend/requirements.txt` (attempt) | fails: `pydantic==2.7.4` needs `maturin`/PyO3 (max 3.12); `sqlalchemy==2.0.29` asserts on 3.15 |
| throwaway venv: `pip install fastapi sqlalchemy pydantic` | `fastapi 0.146.0`, `SQLAlchemy 2.1.5`, `pydantic 2.14.1` |
| `grep -n "STORAGE_BACKEND" render.yaml` | `local` — ephemeral disk on Render |
| `grep -n "plan:" render.yaml` | `free` |
| `sed -n '1,40p' backend/scripts/seed_admin.py` | hardcoded password at `:24`, printed at `:42` |

## 10. What was not run (and why)

| Not run | Reason |
|---|---|
| `scripts/live_e2e.py` | requires live credentials and writes data; not authorised beyond read-only navigation |
| Alembic upgrade/downgrade | no Alembic configuration exists |
| Oracle DDL / `TENANT_SCOPING.sql` | would modify production; not authorised |
| Load/concurrency tests | no staging environment; would affect the live free tier |
| `axe-core` full rule engine / keyboard traversal | Lighthouse's axe-derived audit was run; keyboard/focus traps were not tested |
| Restore drill | no restore environment |
| Responsive viewports (360/768/1024/1440) | no viewport-emulation tool used; static CSS review only |

---

**Reproducibility note.** All counts above are reproducible from the listed commands. Where a count depends on the
project's own counting convention, the raw suite outputs are the source of truth and are listed in §3. The
"492 checks" figure quoted in earlier notes is corrected to **435** (see §3).
