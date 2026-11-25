# Karmathy Enhancement — Route & Page Inventory

Audit baseline: commit `287433e` (working tree clean, `npm run build` passing).

## Route inventory (actual, from `frontend/src/App.tsx`)

| # | Route | Page | Persona | Auth | Status |
|---|-------|------|---------|------|--------|
| 1 | `/login` | Login | Public | No | Working, needs a11y + polish |
| 2 | `/` | Homepage | Public | No | Working, has dead links + invalid CSS class |
| 3 | `/dashboard` | Dashboard | All auth | Yes | Working, no loading state |
| 4 | `/recruiting` | Recruiting | HR | Yes | Working (4 tabs) |
| 5 | `/onboarding` | Onboarding | HR | Yes | Working |
| 6 | `/time` | TimeAttendance | Employee/Manager | Yes | Working |
| 7 | `/scheduling` | Scheduling | Manager/HR | Yes | Working |
| 8 | `/leave` | Leave | Employee/Manager | Yes | Working |
| 9 | `/offboarding` | Offboarding | HR | Yes | Working |
| 10 | `/reports` | Reports | Leadership | Yes | Working |
| 11 | `/client-onboarding` | ClientOnboarding | Tenant admin | Yes | Working, has gradient violating design direction |
| 12 | `/platform` | Platform | HR | Yes | Working, uses `getElementById` + bare `<ul>` lists |
| 13 | `/solutions` | Solutions | Public | No | Working |
| 14 | `/industries` | Industries | Public | No | Working |
| 15 | `/resources` | Resources | Public | No | Working |
| 16 | `/about` | About | Public | No | Working |
| 17 | `/careers` | Careers | Public | No | Working |
| 18 | `/contact` | Contact | Public | No | Working |
| 19 | `/privacy` | Privacy | Public | No | Working |
| 20 | `/terms` | Terms | Public | No | Working |
| 21 | `/docs` | Documentation | Public | No | Working |
| 22 | `*` | → `/` redirect | — | No | Catch-all |

No nested routes, no detail/edit routes, no modal-driven routing exist.

## Confirmed defects (Stage 2 plan, ordered by severity)

### D1 — Tenant theme system is inert (High)
`TenantContext.tsx:79-80` sets `--tenant-primary` / `--tenant-secondary` on
`documentElement`. **No stylesheet rule ever reads those variables.** Tenant
accent colours are fetched and discarded, so white-labelling has no visible
effect. Also no contrast validation on tenant-supplied colours.

### D2 — Homepage marketing links misdirect to `/login` (High)
19 occurrences in `Homepage.tsx`. Real public routes already exist for every one
of these targets. Nav "Solutions"/"Industries"/"Resources"/"Company" and footer
"About"/"Careers"/"Contact"/"Privacy"/"Documentation" all send anonymous
visitors to the sign-in page.

### D3 — Dead route `/payroll` in footer (Medium)
`Homepage.tsx:280` links to `/payroll`, which is not registered in `App.tsx`.
It silently hits the `*` catch-all and redirects to `/`. Payroll lives under
the `/platform` tab instead.

### D4 — Non-existent Tailwind class `shadow-card-lg-lg` (Medium)
Used at `Homepage.tsx:243`, `Dashboard.tsx:74`, `Solutions.tsx:23`,
`Resources.tsx:23`. Config defines `card-lg` only, so these hover effects
silently no-op.

### D5 — Inter font never loads (Medium)
`--font-primary` and `tailwind.config.js` both declare Inter, but there is no
`@font-face` or webfont link. Rendering silently falls back to `system-ui`, so
the specified typography is not actually delivered.

### D6 — No mobile navigation in the app shell (High)
`Layout.tsx:31` is `hidden lg:flex`. Below 1024px every authenticated page has
**zero** navigation — users are trapped on whatever page they landed on.

### D7 — App shell has no breadcrumbs / page context (Medium)
Pages hand-roll their own `h1`. No shared breadcrumb or consistent page-header
component exists, so titles/subtitles/actions vary page to page.

### D8 — Marketing hero CTA "Request a demo" goes to `/login` (Medium)
No demo/contact flow; mislabels the destination.

### D9 — `Layout` renders emoji icons in `NAV` that are never used (Low)
`NAV[].icon` is dead data.

### D10 — No loading/skeleton states anywhere (Medium)
All pages render an empty metric grid until data arrives, so a slow API looks
identical to "no data".

### D11 — No test / lint / typecheck scripts for the frontend (Medium)
`package.json` has only `dev`/`build`/`preview`. No ESLint config, no test
runner. `tsc` runs as part of `build` only.

### D12 — `Platform.tsx` bypasses React state (Medium)
Uses `document.getElementById(...).value` for form input, losing controlled
input, validation and accessibility semantics.

## Explicitly out of scope / backend-dependent
- Real auth token refresh (no refresh endpoint in the API surface).
- Per-role route guarding (RBAC exists in data model; no frontend enforcement).
- Employee self-service portal (no route or data model).
- Export/scheduled reports (Import/Export tab is docs-only text).

---

# Stage 7 — Verification & Outcomes

Baseline was `287433e`; all work landed in five reviewed commits on `main`.

## Resolved

| ID | Defect | Fix | Verified by |
|----|--------|-----|--------------|
| D1 | Tenant theme inert — vars set, no rule read them | `[data-tenant]` layer consuming the vars; `deriveTheme()` with WCAG validation | Computed style = `rgb(16,185,129)` for a `#10B981` tenant; CTA renders tenant colour |
| D2 | 19 marketing links sent visitors to `/login` | Each repointed to its existing public route | `check:routes` passes; all 9 public pages verified link-by-link |
| D3 | Dead `/payroll` route hit the catch-all | Repointed to `/leave`; payroll lives under `/platform` | Negative test: reintroducing `/payroll` fails `check:routes` |
| D4 | Invalid `shadow-card-lg-lg` (config has `card-lg`) | Corrected in 4 files | Absent from source and compiled CSS |
| D6 | Nav `hidden lg:flex` — no navigation below 1024px | Sidebar + accessible drawer | Drawer toggles, 10 links, Escape closes, scroll lock verified |
| D7 | No breadcrumbs or page context | Breadcrumbs, `page-header`, tenant brand/logo, account menu | Present on every authenticated page |
| D8 | "Request a demo" misrouted to `/login` | Routed to `/contact` | — |
| D10 | No loading states anywhere | Skeletons + error/retry on Dashboard and Platform | Loading = 22 skeletons with `aria-busy`; error = retry works, **zero** metric values shown |
| D11 | No test/lint/typecheck scripts | `typecheck`, `check:routes`, `verify` | All pass |
| D12 | `Platform.tsx` read form values via `getElementById` | Controlled, labelled inputs | No `getElementById` remains |

Additionally: public pages no longer render the authenticated sidebar/avatar
(`PublicLayout`), Contact form labels now associate with their inputs, heading
order fixed on 5 pages, `<main>` added to the homepage, and SEO metadata,
robots.txt, sitemap.xml and a real favicon added.

## Deliberately not changed
- **Inter is still not downloaded.** It is declared in tokens but no webfont
  loads, so rendering falls back to the system stack. Adding a webfont is a
  product/performance decision (render-blocking request, self-hosting vs CDN)
  and was not assumed.
- **No fabricated data.** Failed API calls surface an error and a retry; they
  are never replaced with placeholder metrics.

## Still open
- Payroll, Performance, Benefits, Learning and Compliance exist only as
  read-only lists on `/platform`; create flows need backend endpoints.
- **42 form controls across 7 authenticated pages are still unlabelled.**
  Measured in-browser: Recruiting 7, Scheduling 8, Leave 9, Offboarding 6,
  ClientOnboarding 6, Onboarding 3, Time 3. These pages were not individually
  redesigned, so their original `<label>` elements still lack `htmlFor`.
  Dashboard and Platform are at 0.
- No frontend test runner. `check:routes` covers link integrity only; the
  contrast maths and theme derivation still need unit tests.
- The other authenticated pages retain their original per-page markup. They
  have the shell, tokens and primitives, but each needs its own layout,
  loading/empty state and labelling pass.

---

# End-to-End Validation

Run against a real backend (FastAPI + SQLite, 138 API endpoints, seeded
admin). The `scripts/e2e_lifecycle.py` suite added with this work is
repeatable and idempotent.

## Backend suites

| Suite | Result |
|-------|--------|
| `scripts/e2e_lifecycle.py` (added) | **40 passed, 0 failed** (3 consecutive runs) |
| `smoke_test.py` | passes on a clean DB |
| `smoke_test_phase2.py` | pass — hire created employee + 6 onboarding tasks, letter on disk |
| `smoke_test_phases_3_7.py` | **39 passed, 0 failed** |
| `smoke_test_client_onboarding.py` | **18 passed, 0 failed** |

E2E covers: auth (valid, wrong password, unauthenticated), a 43-endpoint
read sweep, requisition → candidate → application → offer → letter → accept →
hire → onboarding → clock in/out → timesheet submit/approve → shift template
→ roster → leave type → entitlement → request → approve → terminate →
complete, then reporting consistency.

## Frontend against live data

- Login through the real UI → token issued, authenticated shell loads.
- Dashboard renders live metrics (4 groups) and 10 audit rows from real data.
- Platform renders 4 captioned tables, 0 unlabelled inputs, empty states.
- **Write path proven through the UI**: submitting the location form produced
  a "Location created" notice and both rows were confirmed present in the
  database via the API.
- **Contact form (public → backend) proven**: submission appeared as an HR
  case in the database.
- All 10 authenticated pages render with sidebar, breadcrumbs and no error
  alerts.

## Regression

| Check | Result |
|-------|--------|
| `npm run typecheck` | pass |
| `npm run check:routes` | pass — 21 routes |
| `npm run build` | pass — 116 modules |
| Lighthouse `/`, `/contact`, `/docs`, `/dashboard`, `/platform` | a11y 100, best-practices 100, SEO 100 |

## Notes for maintainers
- `email-validator` is used by `app/schemas/user.py` via `pydantic` but is
  **not declared** in `backend/requirements.txt`. It happens to arrive
  transitively; pin it explicitly.
- `smoke_test*.py` hardcode `sqlite:///./smoke_test.db` relative to the
  working directory and are **not re-runnable** — a second run fails with
  `UNIQUE constraint failed: departments.code`. Run them from a clean cwd or
  delete the `backend/*.db` files first.
- The documented `pydantic==2.7.4` has no wheel for Python 3.14; validation
  here used newer pydantic. Deployment on 3.11/3.12 is unaffected.