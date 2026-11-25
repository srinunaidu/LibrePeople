# Revamp Notes — Defects and Drift Found During the Audit

**Status:** observations only. **Nothing in this file was fixed.** This audit was read-only by design.
**Audit target:** `feature/hcm-slack-revamp` — started at `75c3cc5`; frontend advanced to `91024a2` during the
audit, with 10 uncommitted frontend files at close (backend unchanged). · **Date:** 2026-10-19
**Companion to:** `AUDIT_REPORT.md` (finding IDs), `UPGRADE_PLAN.md`, `FEASIBILITY.md`

This is the working log of things that surfaced while verifying `DOCUMENT.md` and are too small or too
cross-cutting for the main findings. It is separate from the repository-root `REVAMP_NOTES.md`, which covers the
earlier frontend revamp; several items there are now stale (see §5).

---

## 1. Documentation drift

| Doc | What it says | What is true | Evidence |
|---|---|---|---|
| `docs/API_CONTRACT.md` | Contract with Phases 1–7 | Stops at offboarding/reports; **no** payroll, performance, benefits, learning, platform, compliance, ESS, import/export, data-quality | `wc -l` = 150; headings end at Phase 7 |
| `docs/DB_SCHEMA.sql` | "DB schema" | **22** `CREATE TABLE`, stopping at `audit_logs`; **55 tables missing** | `grep -c "CREATE TABLE"` = 22 |
| `docs/AUTH_ROLES.md` | `get_current_user` → 403; register public; Manager/PayrollViewer have permissions | Returns **401**; register disabled by default; 0 role-helper uses, Manager/PayrollViewer have no distinct server permissions | `deps.py:37-41`; `config.py:26`; `grep -rn "require_role"` = 0 |
| `docs/DEPLOYMENT.md` | `/health/db`, `/health/storage`, `/health/wallet` are public URLs | All require an operator token and return **401** anonymously — intentional (`main.py:155,181,205`), so the **doc** is wrong | live `curl`; `main.py:119` |
| `docs/CLIENT_ONBOARDING.md` | 6-step tenant portal with isolation | Portal is real but clients are **rows, not security boundaries**; `/by-slug` exposes branding to anyone | `client_onboarding.py`; `TENANT_SCOPING.sql` unapplied |
| `docs/FEATURE_INVENTORY.md` | 67 tables / 154 endpoints / 20 routers | **77 / 164 paths (236 operations) / 25** | OpenAPI + router registration |
| `docs/PHASE2_STATUS.md:47` | Visibility "**confirmed live** (Associate 0 rows vs Admin 12/12/13)" | True only for employees/leave/offboarding; **73 GETs remain unfiltered** | `visibility.py` call sites: `employees.py:49,101`, `leave.py:76-80,135-144`, `offboarding.py:79-83` |
| `DOCUMENT.md` §9 | Router table lists 20 | 25 registered; `/data-quality` and ESS nuances omitted | `api/v1/api.py` |
| Root `REVAMP_NOTES.md` §5 | TanStack Query "never imported" | Provider is wired (`QueryProvider.tsx`), but pages still have **0** `useQuery`/`useMutation` calls | `grep -rn "useQuery\|useMutation"` = 0 |
| Root `REVAMP_NOTES.md` §9 | pydantic 2.7.4 "no Python 3.14 wheel" | Also fails on **3.15** (`maturin`/PyO3 max 3.12); SQLAlchemy 2.0.29 asserts on 3.15 | test run |

**Recommendation:** generate `API_CONTRACT.md` from `/api/v1/openapi.json` in CI, and `DB_SCHEMA.sql` from the
Alembic head. Hand-maintained copies will drift again.

---

## 2. Frontend defects found (not fixed)

| # | Defect | Detail | Severity | Effort | Evidence |
|---|---|---|---|---|---|
| F-1 | **Internal `/design` showcase is shipped to every authenticated user** | 421-line page linked from the command palette, the top-bar menu and the mobile drawer. It is not in `DOCUMENT.md` §7. It exposes every primitive, including destructive variants, and is dead weight in the bundle | Low | S | `App.tsx:46`; `CommandPalette.tsx:40`; `TopBar.tsx:109`; `Layout.tsx:149,214` |
| F-2 | **`window.prompt` in the hire flow** | "Employee ID for the new hire" uses a blocking browser prompt. No validation, no cancel handling, not keyboard/screen-reader friendly, untestable | Medium | S | `Recruiting.tsx:573` |
| F-3 | **Login always lands on `/dashboard`** | No `returnTo`; a user who follows `/leave` while logged out loses their destination | Low | S | `Login.tsx:30` |
| F-4 | **User identity is not persisted** | Only the token is stored; `user` starts `null` on every reload and there is **no `/auth/me`**, so role-aware UI cannot survive a refresh. It also means `ProtectedRoute` cannot check a role | High | M | `AuthContext.tsx:7-18`; `ProtectedRoute.tsx:9-15` |
| F-5 | **No global 401/403 handling** | The response interceptor only normalises error shapes. An expired/invalid token leaves the user on a broken page instead of redirecting to login. Revoked access is invisible | High | M | `lib/api.ts:45-70` |
| F-6 | **Tenant branding is lost on navigation** | `detectTenantSlug()` reads `/t/:slug`, but every shell link is absolute (`/dashboard`, `/leave`, …) and login redirects to `/dashboard`. Branding works only until the first click | Medium | M | `TenantContext.tsx:31-53`; `CommandPalette.tsx:30-40`; `MobileBar.tsx:6-17`; `SecondarySidebar.tsx:153+`; `Layout.tsx:141-146` |
| F-7 | **`/platform` is a 543-line monolith** | People, payroll, performance, benefits, learning and admin are tabs in one page. Deep links cannot target a module; browser back is coarse; the file is hard to review | Medium | L | `wc -l src/pages/Platform.tsx` = 543 |
| F-8 | **Large pages remain un-split** | `Recruiting.tsx` 600, `ClientOnboarding.tsx` 515, `Design.tsx` 421, `Offboarding.tsx` 351, `Leave.tsx` 346; all eagerly imported in `App.tsx` (no `lazy`) | Medium | L | `wc -l`; `App.tsx:4-25` |
| F-9 | **8 unused dependencies** | `@tanstack/react-virtual`, `date-fns`, `lucide-react`, `@radix-ui/react-{progress,checkbox,switch,label,slot}` — 0 imports each. They inflate install time and audit surface | Low | S | `grep` |
| F-10 | **Breadcrumb separators fail contrast** | `/` at **1.42:1** and `›` at **1.48:1** on `/dashboard`; 2 per page elsewhere. Mostly decorative, but exposed to AT as text | Low | S | live DOM computation |
| F-11 | **Brand tokens fail contrast** | Teal `#06B6D4` 2.43:1, Green `#10B981` 2.54:1, Warning `#D97706` 3.19:1, Violet `#8B5CF6` 4.23:1 on white | Medium | S | computed ratios |
| F-12 | **Public homepage has no skip link** | The authenticated shell has one; the marketing homepage does not | Low | S | live DOM |
| F-13 | **Inter is declared but never delivered** | Design system says Inter; no `@font-face` and no self-hosted file, so the browser falls back | Low | S | `index.html`; `index.css` |
| F-14 | **No route-level code splitting** | One **604.6 kB** JS chunk (179.6 kB gzip) for the whole app and all 22 pages; Vite warns >500 kB. Was 467 kB at `75c3cc5` | Medium | M | `vite build` output |
| F-15 | **Theme toggle exists but dark coverage is thin** | `ThemeToggle` is rendered, but only 3 `dark:` utilities exist; most surfaces rely on CSS variables | Low | M | `grep -c "dark:"` = 3 |

> **F-4/F-5** are the two that most affect the revamp: role-based homes and hide-what-you-cannot-use both depend
> on knowing the user after a refresh and reacting to 401/403.

---

## 3. Backend/API gaps surfaced while mapping the UI

| # | Gap | Detail | Evidence |
|---|---|---|---|
| B-1 | **ESS has ~30 endpoints and no UI** | Profiles, notifications, files, announcements, directory, org chart, goal alignments, feedback, compliance | `ess_hr.py`; 0 `/ess` calls under `frontend/src` |
| B-2 | **`/time/today` unused** | Dashboard "Present today" derives from `/reports/dashboard`; `/time/today` is fresher | `time_attendance.py:76`; `Dashboard.tsx` |
| B-3 | **`/reports/attendance` unused** | No attendance report view in the UI | `reports.py:49` |
| B-4 | **Register is disabled by default** | `POST /auth/register` exists but `ALLOW_SELF_REGISTRATION` defaults false; the UI has no registration path | `config.py:26` |
| B-5 | **`email-validator` is undeclared** | `EmailStr` needs it; it resolves transitively today. A clean install can break user create/validate | `schemas/user.py:1`; not in `requirements.txt` |
| B-6 | **Smoke scripts are not re-runnable** | `smoke_test.py` hardcodes `sqlite:///./smoke_test.db`; second run fails on unique department codes | `smoke_test.py:4` |
| B-7 | **OpenAPI is not at the root** | `/openapi.json` → 404; the schema is at `/api/v1/openapi.json`. Tooling and docs assume the root | `main.py:36`; live curl |
| B-8 | **`/health/db` etc. are operator-only** | Correct security, but the docs and any external monitor expect them public. A monitor will see 401 and may declare an outage | `main.py:155-206` |
| B-9 | **Compliance "checks" are simulated** | `# Simulate a check` in the router; results are generated, not evaluated | `ess_hr.py:327-330` |
| B-10 | **No pagination on list endpoints** | A 2,000-employee tenant returns full tables to the SPA | `employees.py`, `payroll.py`, etc. |

---

## 4. Live deployment observations (2026-10-19)

| Observation | Detail |
|---|---|
| Frontend | `200`, ~0.38 s |
| `/health` | `200`, but **42.44 s** on a cold start |
| `/health/db`, `/health/storage` | `401` anonymously (by design; docs wrong) |
| `/docs` | `200` |
| `/openapi.json` (root) | `404` (correct path is `/api/v1/openapi.json`) |
| Default admin credential | **Still authenticates as SuperAdmin** — rotate before any customer data exists |
| Authenticated a11y | 5 pages: 0 unlabelled controls, 0 unnamed buttons, skip link, 1 `h1`, sequential headings |
| Tenant path | `/t/:slug/*` routes exist; nav immediately leaves them (F-6) |

---

## 5. Stale prior notes — do **not** redo this work

These were true in earlier notes but are now fixed or disproved. Re-checking them wastes time.

| Prior claim | Current verified state |
|---|---|
| "42 unlabelled form controls" (`ENHANCEMENT_INVENTORY.md:132-136`) | **0** on `/dashboard`, `/recruiting`, `/leave`, `/time`, `/platform` (DOM check) |
| "No skip link" in the app | Present in `Layout.tsx:193`; still absent on the public homepage |
| "Tenant theme is inert" | `deriveTheme` works and CSS variables are consumed under `[data-tenant]` |
| "TanStack Query never imported" | `QueryProvider` is wired; **no hooks use it yet** (different problem) |
| "No theme toggle" | `ThemeToggle.tsx` is rendered in `TopBar.tsx:80` |
| "No role in `ProtectedRoute`" | Still true — **not** stale; listed as F-4/F-5 and A3-04 |
| "`window.prompt` removed" | Still present (`Recruiting.tsx:573`) |

---

## 6. Safe quick wins (recommended order, all read-only observations)

1. **Remove the `/design` route and its three links** from production builds (F-1) — one commit, no backend.
2. **Replace `window.prompt`** with the existing dialog primitive (F-2).
3. **Delete 8 unused dependencies** (F-9) and re-run `npm audit`.
4. **Darken or `aria-hidden` breadcrumb separators** (F-10) and fix the four brand tokens (F-11).
5. **Add a skip link to the public layout** (F-12).
6. **Persist the user or add `/auth/me`**, then add a 401 interceptor (F-4/F-5). This is the enabler for role-aware UI.
7. **Prefix shell links with the current tenant slug** or drop path-based branding (F-6). Pick one; do not leave both.
8. **Add `email-validator` to `requirements.txt`** (B-5).
9. **Point the docs at `/api/v1/openapi.json`** and mark `/health/db|storage|wallet` as operator-only (B-7/B-8).

None of these require the revamp to start; they reduce noise before it does.
