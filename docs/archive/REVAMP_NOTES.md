# REVAMP_NOTES.md — Backend & API Gaps Found During Frontend Revamp

Log of issues found in the existing backend while working on the frontend revamp.
**None of these are fixed** — frontend only. Flag for approval if any should be addressed.

---

## Confirmed API gaps

### 1. `/auth/register` exists but is gated
- Endpoint: `POST /auth/login` (works), `POST /auth/register` (exists in `auth.py:76`)
- Issue: Register is public **only when** `ALLOW_SELF_REGISTRATION` is enabled. Default config may not allow it.
- Frontend impact: Login page works. Self-registration UI is not built (out of scope).

### 2. `/ess/*` router is registered
- `app/api/v1/api.py:66` includes `ess_hr.router` at prefix `/ess`
- Feature doc (Phase 8) describes ESS profiles, notifications, employee files, announcements, directory, org chart, goal alignments, continuous feedback, compliance checks
- Frontend impact: **No ESS pages exist.** The ESS module (Phase 5) can be built once routes are confirmed. This is a frontend gap, not a backend gap.

### 3. `/time/today` endpoint exists
- `time_attendance.py:76` — `@router.get("/today")` returns attendance summary
- Frontend impact: Dashboard "Present today" card currently derives from `/reports/dashboard`. Could switch to `/time/today` for fresher data.

### 4. `/reports/attendance` endpoint exists
- `reports.py:49` — `@router.get("/attendance")` with `?day=` param
- Frontend impact: Reports page does not surface a dedicated attendance view. Could be added.

---

## Frontend gaps (not backend issues)

### 5. TanStack Query is a dependency but never imported
- `@tanstack/react-query@5.59.0` is in `package.json` — zero imports in `src/`
- Every page hand-rolls `useState` + `useEffect` + `catch` for loading/error
- Fix: wire up `QueryClientProvider` in Phase 2, create typed hooks per domain

### 6. No data-fetching hooks library exists
- No `useEmployees`, `useLeaveRequests`, etc.
- Every page repeats the same fetch pattern
- Fix: Phase 2 — create `src/lib/hooks/` with domain hooks

### 7. `email-validator` is an undeclared dependency
- `app/schemas/user.py` uses it via pydantic's `EmailStr`
- Not listed in `requirements.txt` — works only via transitive resolution
- Risk: a dependency bump could break user creation/validation silently
- Recommendation: pin `email-validator` explicitly in `requirements.txt`

### 8. `smoke_test*.py` scripts are not re-runnable
- Hardcode `sqlite:///./smoke_test.db` relative to cwd
- Fail on second run with `UNIQUE constraint failed: departments.code`
- Workaround: run from a clean directory or delete `backend/*.db` first
- Not fixed (backend out of scope)

### 9. `pydantic==2.7.4` has no Python 3.14 wheel
- Building from source requires Rust/maturin and fails on Python 3.14
- Local validation used newer pydantic (2.14.1) in a throwaway venv
- Deployment on Python 3.11/3.12 is unaffected
- Not fixed (pinned version is intentional for Oracle compatibility)

### 10. Stale-database schema gap (found during Phase 1 validation)
- `/payroll/runs` returned HTTP 503 with `dependency_unavailable` against a
  pre-existing SQLite test database
- Root cause: the DB file predates the `processed_by` column on `pay_runs`
  (added to the model in a concurrent commit). `create_all()` does not alter
  existing tables, so the column was missing.
- On a freshly created database the same endpoint returns HTTP 200 with `[]`.
- **Not a frontend issue.** Frontend impact: none — the UI handles 503s via its
  error state and retry. Deployment against Oracle ADB is unaffected because
  migrations run there.
- Fix (if approved): add an Alembic migration for the column, or drop and
  recreate local test DBs.

---

# Gate 0 — credential rotation and session review

**Date:** 2026-10-19
**Gate:** build brief section 0A item 7.

## The credential that was exposed

The seed script created the first administrator with a hard-coded password,
printed it on every run, and the same value was repeated in `README.md` and
`docs/DEPLOYMENT.md`. It was in the repository's history. The audit found it
and it was **still authenticating against the live production backend as
SuperAdmin** when Gate 0 opened.

## Outcome

| | |
|---|---|
| Rotated | Yes |
| The old credential now authenticates | No — `401 unauthenticated` |
| The replacement authenticates | Yes — `200`, role `SuperAdmin` |
| The replacement is stored | `~/.karmathy/admin-bootstrap.txt`, mode `0600`, outside the repository |
| The password appears in this file | No |
| The password appears in the repository | No — the CI secret scan fails the build if it does |
| Forced change at first sign-in | Yes — the account is in a `must_change_password` state and can reach only `GET /auth/me`, `POST /auth/password` and `POST /auth/logout`. Every other endpoint returns `403 forbidden` with the message *"You must change your password before using this account."* |

**Action for the owner:** sign in with the replacement, set your own
password, and delete `~/.karmathy/admin-bootstrap.txt`.

## Review of the sessions that used it

The audit trail was read in full: 32 login events, every one attributable.

| Actor | Logins | Assessment |
|---|---|---|
| `admin` | 25 | The audit session and the owner's own use. Every recorded action under this account is consistent with the audit and end-to-end scripts (creating leave types, approving leave, generating rosters, running a migration, hiring from an offer). No action outside that pattern. |
| `e2euser*`, `auditprobe*`, `iso_probe*`, `iso2_*`, `phase2probe*`, `probe_unlinked*` (18 accounts) | 7 | Created by `scripts/live_e2e.py` and by throwaway audit probes. Ephemeral test accounts. One of them, `auditprobe…`, was created with the **SuperAdmin** role. |

**No unexplained session, and no sign-in from an unrecognised actor.** The
audit trail has no record of the source address, so the review is by actor
and action rather than by origin. That is a limitation of the current audit
model and is recorded as a gap for the audit hash-chain work.

## Follow-up actions taken

1. **The 18 leftover test accounts were deactivated** (`is_active = false`,
   not deleted, so nothing is lost). `auditprobe…` was a SuperAdmin whose
   password was chosen by a throwaway script and was therefore no better
   protected than the published default. Deactivation was done through
   `PATCH /auth/users/{user_id}`, which revokes the account's live sessions
   and writes an audit row, so the action is itself recorded.
2. **No default password exists anywhere.** `scripts/seed_admin.py` reads
   `ADMIN_INITIAL_PASSWORD` from the environment, refuses to run without it,
   and never prints a password. It creates no sample departments or jobs.
3. **A secret scan runs in CI.** `ci/secret_scan.py` fails the build on the
   published credential, on private keys, on known token formats, and on
   high-entropy values assigned to secret-looking names.
4. **The password policy is enforced on every creation path**: length, a
   local breach blocklist, refusal to reuse the last N passwords, and
   refusal of passwords derived from the account identity.

## Other findings from this work

- **A response model was re-validating an input constraint.** `UserOut`
  inherited `email: EmailStr` from the request schema, so the seeded
  administrator's `admin@karmathy.local` — a reserved domain that
  `email-validator` rejects — made `GET /auth/me` and `GET /auth/users`
  return **500**. It now returns the stored value as a string, and
  `UserCreate` keeps the strict validation. A response model must be able
  to describe what is stored.
- **The startup event imported `run_pending_migrations` from the wrong
  module.** The `ImportError` inside the startup event meant the container
  never started, and the deploy failed with no readable cause. The
  application now has a startup suite that enters the lifespan, which the
  existing suites did not do.
- **The container now runs migrations as a release step**, before the server
  binds, so a failed migration fails the deploy and leaves the previous
  working version serving.

---

## Known limitations (from feature doc, kept honest in UI)

1. Ephemeral disk (fixed by OCI)
2. Backend spin-down on free tier — slow first request
3. Single schema (`ADMIN`)
4. No wildcard subdomains (using `/t/:slug/`)
5. No real SSO flows (SAML/OIDC not implemented)
6. No real SCIM (tokens exist, provisioning not implemented)
7. No real e-signature (status tracking only)
8. No real background checks (status tracking only)
9. Payroll uses simple percentage withholding, no real tax engine
10. No mobile app (responsive web only)
11. No email notifications (in-app only)
12. No real-time updates (polling-based)

---

## Decisions made (no backend impact)

- **Platform page split**: 7 tabs → dedicated workspace areas (People, Payroll, Performance, Learning, Admin). `/platform` becomes an overview hub.
- **Route preservation**: all existing routes kept, including `/t/:tenantSlug/*`.
- **Auth unchanged**: JWT storage, refresh behavior, RBAC enforcement all identical.
- **No hardcoded tenant brand values**: all tenant visuals come from tenant config via CSS variables.

---

*Last updated: Phase 1 (design system). New entries added as discovered.*