# Cloud E2E report — deployed env (backend + frontend on Render)

Date: 2026-11-26. Branch: `agent/qa/cloud-e2e-run` (from main `072c86c` + pack merge).
Targets: `https://librepeople-backend.onrender.com` (`/health` 200, 0.2 s),
`https://librepeople-frontend.onrender.com` (`/` 200). Config:
`frontend/e2e/cloud/playwright.cloud.config.ts` (new; `CLOUD_E2E_ACK=1` gate,
workers 1, retries 0, screenshots/traces on failure). Synthetic users only
(`e2e_*`); credentials via `E2E_*` env at runtime, never in files.
Result: **9 passed / 16 failed / 0 skipped of 25, browser: cloud-chromium
(Desktop Chrome) only** — responsive projects not run (single-browser run).

## Per-spec results

| Spec | Pass | Fail | Notes |
|---|---|---|---|
| cloud-auth (6) | manager | hradmin, hrexec, payroll, employee, readonly | sign-in/out works for all; failures are console-error assertions (see D1/MFA) |
| cloud-employee-lifecycle (4) | leave-screen-loads*, employee-denied-403/404 | admin-create, leave-apply→approve | *race-pass (see flakes); setup 403s are the MFA block |
| cloud-ess-access (5) | admin-screen-403-card, admin-writes-refused, 401 | employee-self-service UI | fixed test now passes; UI failure = D1 console error |
| cloud-helpdesk (4) | 401 | open→comment, queue screen, stranger-404 | setups answer 403 (MFA block) |
| cloud-assets-documents (3) | 0 | all 3 | setups answer 403 (MFA block) |
| cloud-reports-exit (3) | termination-denied-403/404 | reports, exit | setups answer 403 (MFA block) |

Negative/401 API tests pass everywhere (5/5): permission boundaries hold.

## Defects found + fixed (specs, this branch)

1. `cloud-auth.spec.ts` `signOut` cleared cookies, but the session token lives
   in `localStorage["karmathy_token"]` (`AuthContext.tsx:8`, `api.ts:48`) —
   sign-out never happened. Fixed to use the real TopBar user-menu →
   "Sign out" (`TopBar.tsx:200-208`); sign-in/out now works for all 6 roles.
2. `cloud-ess-access.spec.ts` asserted an associate is bounced off
   `/admin/*` by URL, but `ProtectedRoute.tsx:32-44` renders an in-place
   "403 — Forbidden" card at the same URL (verified in screenshot). Fixed to
   assert the 403 card — denial proven by content, stronger than before.

## Defects filed (NOT fixed — product code out of scope, no push)

- **D1 — shell fires a SuperAdmin-only endpoint for every role.**
  `TenantSwitcher` (pinned in `WorkspaceRail.tsx:460`) calls `listClients()`
  (`TenantSwitcher.tsx:64-76` → `api.ts:262-264` → `GET
  /onboarding-portal/clients`, guarded `require_roles("SuperAdmin")` at
  `backend/app/api/v1/endpoints/client_onboarding.py:98-103`). Every
  non-SuperAdmin page load logs one console error (`403`). The `.catch`
  swallows it in-UI, but the pack's zero-console-error assertion trips —
  deterministically in principle, race-dependent in practice (payroll passed
  once, failed on re-run). Smallest fix (owner's call): gate the call on
  SuperAdmin role or add a role-scoped workspaces endpoint.
- **MFA block (by design, not a defect).** `e2e_hradmin`/`e2e_hrexec` are role
  HR with `mfa_enabled: false`; `get_current_active_user`
  (`backend/app/api/deps.py:204-243`) refuses unenrolled SuperAdmin/HR with
  403 on everything but `/auth/mfa/*` — verbatim: `"Multi-factor
  authentication is required for your role. Enroll at /auth/mfa/enroll."`
  (observed on `GET /employees`, `/departments/`). HRHome fires 7 such calls
  (`HRHome.tsx:49-54`); dashboard shows "Nothing needs your attention"
  instead of the frontend-truth "could not be read" state — worth a look
  once HR can enroll. No MFA was enrolled/disabled by this run.

## NOT TESTED (mandate §7 — MFA challenge, recorded not bypassed)

All flows needing the HR-admin token: employee create, leave apply→approve,
helpdesk open/comment/queue/stranger-404, asset register/assign, document
record/version, reports reads, termination+interview-notes, HR dashboard
console-quiet. Unblock: enroll MFA for the two HR users (designed
`/auth/mfa/enroll→confirm` flow) or provision an MFA-enrolled HR account,
then re-run — no spec changes needed.

## Responsive notes

Not run: this execution used the `cloud-chromium` project only (Desktop
Chrome, 1280×720). No viewport sweep was attempted; responsive remains open
for a follow-up run (`--project` matrix in the cloud config).

## Evidence retained

Failure screenshots + traces under `frontend/test-results/` (gitignored);
console-error arrays name the 403 URLs per role; probe logs show per-role
`auth/me` (`HR×2`, `PayrollViewer×2`, `Manager`, `Associate`) with
`must_change_password: false` for all six.
