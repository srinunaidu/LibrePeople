# Cloud E2E report — deployed env (backend + frontend on Render)

Date: 2026-11-26. Branch: `agent/qa/cloud-e2e-run` (from main `072c86c` + pack merge).
Targets: `https://librepeople-backend.onrender.com` (`/health` 200, 0.2 s),
`https://librepeople-frontend.onrender.com` (`/` 200). Config:
`frontend/e2e/cloud/playwright.cloud.config.ts` (new; `CLOUD_E2E_ACK=1` gate,
workers 1, retries 0, screenshots/traces on failure). Synthetic users only
(`e2e_*`); credentials via `E2E_*` env at runtime, never in files.

> **Round 3 (this section) supersedes round-2 dispositions where they differ;
> round-1/2 history is kept below unchanged.** Round 3 result: **25 passed /
> 0 failed / 0 skipped of 25, browser: cloud-chromium (Desktop Chrome)
> only.**
>
> **Headline reconciliation (round 2):** the canonical counts are the
> runner-verified **15 passed / 10 failed** (10 ✘ items; `grep -c ✓` = 15).
> The first-draft table summed to 14/11 because ESS self-service — which
> PASSED in the canonical run but failed in an earlier run of the same round
> (D-1 race manifestation) — was misfiled under Fail. Corrected in the
> round-2 table below to 4/1 (self-service moved to Pass); headline and
> table now agree at 15/10.

## Round 3 — D-1 confirmation on live 8c12425 (2026-11-26)

Branch `agent/qa/cloud-e2e-round3` from `8c12425` (merge of the D-1
TenantSwitcher role gate). All 6 specs re-run unmodified except one
spec-defect fix (below). **25/25 pass; output contains zero 403 console
errors and zero failed-request entries.**

| Spec | Pass | Fail |
|---|---|---|
| cloud-auth (6) | 6/6 | 0 |
| cloud-employee-lifecycle (4) | 4/4 | 0 |
| cloud-ess-access (5) | 5/5 | 0 |
| cloud-helpdesk (4) | 4/4 | 0 |
| cloud-assets-documents (3) | 3/3 | 0 |
| cloud-reports-exit (3) | 3/3 | 0 |

### D-1 verdict: FIXED on the deployed env

Every non-SuperAdmin journey (HR, Manager, Associate, PayrollViewer) is
free of `GET /onboarding-portal/clients` 403s — the TenantSwitcher no
longer fires the call (`28f75ba`), and every `consoleErrors`/`failed`
assertion in the pack holds on the first attempt. No SuperAdmin synthetic
exists, so the SuperAdmin workspace list itself is **not covered** (no
account to sign in with) — noted, not tested; the gate's SuperAdmin path
(`listClients()` still called for `role === "SuperAdmin"`) is code-read,
not run.

### Defect fixed in round 3 (spec-only, committed)

`cloud-helpdesk` queue-screen test expected HR to see the queue UI, but
`HRHelpCases.tsx:26,65` gates the screen on SuperAdmin (`canWrite`) by
long-standing design — HR works the queue through the API (`GET/POST
/core-hr/cases` 200/201, proven passing). The test now asserts the honest
denial (`Not visible for your role` EmptyState text — a `<p>`, not a
heading, per `feedback.tsx:18`) instead of the subject row, mirroring the
round-1 ProtectedRoute-403 precedent. No weakening: denial + API coverage
together prove the designed split. No other spec changes; no retries
needed — the full suite passed consecutively (24/1 → 4/4 helpdesk →
25/25).

### NOT TESTED remainder (carried over)

SuperAdmin workspace list (no provisioned SuperAdmin synthetic);
exit-interview detail UI (no backend endpoint); document/comment hard
delete (no DELETE routes); file bytes; payslip maths; responsive sweep.
MFA: nothing outstanding — both HR logins satisfy the gate, TOTP helper
unused at runtime (accounts already enrolled), no lockout signals seen.

## Round 2 — full re-run with MFA (2026-11-26)

MFA gate satisfied without touching account security: both HR accounts
(`e2e_hradmin`, `e2e_hrexec`, role HR) report `mfa_enabled: true`
(`GET /auth/mfa/status` 200); password-only login mints a JWT that now
answers privileged reads (`GET /employees/` 200 — round 1's 403
`Multi-factor authentication is required…` envelope is gone). New helper
`frontend/e2e/cloud/totp.ts` (RFC 6238, `node:crypto` only) +
`completeMfaIfRequired` wired into all five API-login specs and the auth
spec: checks status, returns when enabled, otherwise attempts a SINGLE
`POST /auth/mfa/confirm` with the provisioned `E2E_<ROLE>_MFA_SECRET` and
asserts the JWT on a privileged endpoint — never enrolls (a server-minted
secret nobody holds would lock the account after the shred), never retries,
never logs. No login-time MFA challenge exists in the product
(`Login.tsx` is password-only; `POST /auth/login` always mints a pair), so
the UI flow is unchanged. Lockout budget respected: 2 probe logins + spec
logins, all successful (successes reset server counters); zero 429s,
zero lockout signals observed.

### Round-2 per-spec results

| Spec | Pass | Fail |
|---|---|---|
| cloud-auth (6) | hradmin, manager, readonly | hrexec, payroll, employee |
| cloud-employee-lifecycle (4) | admin-create, leave-apply→approve, employee-denied | leave-screen-loads |
| cloud-ess-access (5) | self-service, admin-screen-403-card, admin-writes-refused, 401 | admin-surface-loads |
| cloud-helpdesk (4) | open→comment→history, stranger-404, 401 | queue-screen-loads |
| cloud-assets-documents (3) | boundaries (refused-create, stranger-404) | register→assign, document→versions |
| cloud-reports-exit (3) | termination-denied | reports-answers, exit-termination |

Every API flow now passes end to end (MFA + seed + entitlement fixes hold).
All 10 failures are UI tests tripping on D-1's console error (below) — the
functional assertions in those same tests pass (writes persist, screens
serve, denials render).

### Defects fixed in round 2 (spec/test-setup only, committed)

1. `totp.ts` + login-flow MFA completion (above); zero product-code changes.
2. Empty-tenant seed: deployed tenant ships 0 departments / 0 jobs / 0 leave
   types (`GET` all 200, `count= 0`), so specs now provision-or-reuse
   namespaced rows (`POST /departments|/jobs|/leave/types` 201) in
   lifecycle (×2), assets `makeEmployee`, reports-exit — mirrors the local
   harness seeding its DB.
3. Leave approval needs a balance: grant `POST /leave/entitlements`
   `{2026, type, 20d}` 201 before apply, else 409 `leave_no_entitlement`
   (by design, `leave.py:359-376`).
4. Asset assign answers **200**, not 201 (router sets no 201) — expectation
   corrected; custody persistence holds.

### D-1 confirmation: NOT fixed on the deployed env

`TenantSwitcher` (`WorkspaceRail.tsx:460`) still fires SuperAdmin-only
`GET /onboarding-portal/clients` (`client_onboarding.py:98-103`) for every
non-SuperAdmin page load → exactly one console-error 403 per UI test; all
10 round-2 failures show it and nothing else. The fix exists as
`28f75ba` on `agent/frontend/tenantswitcher-gate` (12-line role gate,
unmerged, undeployed — this branch does not touch it). These cloud specs
are the regression test: once that branch merges and Render redeploys,
`ESS/employee specs show zero console errors and no clients-403` is the
acceptance check. SuperAdmin workspace list: not covered (no SuperAdmin
synthetic provisioned) — noted, not tested.

### Flakes (retried, documented, not masked)

Cross-run flips with no spec changes on those paths: reports-answers
✓→✘, ess-admin-surface ✘→✓→✘, auth manager ✘→✓, readonly ✓→✘→✓, hradmin
✘→✓✓, hrexec ✓→✘. Mechanism: the console-error listener races the
in-flight forbidden request — a 403 landing after the assertion passes
silently. Deterministic cause (D-1), race-dependent manifestation. No
assertion was weakened and nothing was skipped to green.

### NOT TESTED (round 2)

None on MFA grounds — the round-1 NOT TESTED list (all HR-token flows) is
now TESTED and passing at the API level. Still open, carried over: exit-
interview detail UI, hard deletes, file bytes, payslip maths, responsive
sweep (see round-1 section).

---

## Round 1 (history — 9 passed / 16 failed)

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

---

## Round 4 — expenses on live 530a49f (2026-11-26)

Branch `agent/qa/cloud-expenses` from main `530a49f` (expenses UI slice).
Deploy gate passed, no 15-min wait needed: frontend
`dep-dc3qcmlbedkc73cnk00g` live, backend `dep-dc3qcmlbedkc73cnjvfg` live
(verified via Render API), `GET /expenses` 200 before testing.

New spec `frontend/e2e/cloud/cloud-expenses.spec.ts` (3 tests). Result:
**2 passed / 0 failed / 1 skipped; full pack 27 passed / 1 skipped / 0
failed, browser cloud-chromium only.**

| Test | Result | Evidence |
|---|---|---|
| associate files + receipt + submits | SKIP (NOT TESTED) | `GET /employees/` as Associate returns `items: []` — `e2e_employee` has no linked employee record and no API links users to employees, so `_ensure_owner` (`expenses.py:148-153`) would 403 any filing. Owner provisioning needed (set `User.employee_id`); not a product defect, no fix attempted |
| HR approves L1 → final → marks paid | PASS | UI: Submit→L1→final→paid with notices `Claim submitted. / L1 approval recorded. / Final approval recorded. / Claim marked paid.` and header `Approved · payment PAID`; API: claim persists `APPROVED`/`PAID`, receipt row persists with server `download_url` |
| associate cannot approve | PASS | Zero `Approve (L1) / Approve (final) / Mark paid` buttons on the claim detail (`showApproveActions` is Manager+); no console errors, no failed requests |

Setup validated by probe: category create 201, claim create 201 (DRAFT), submit/L1/final/mark-paid all 200, receipt upload 201 (multipart). New tenant rows are namespaced (`CEXP-*`, `CLOUDEXP-*`); receipts are small synthetic text files; nothing real uploaded, no prod data touched. Login budget respected (no 429/lockout signals).

### NOT TESTED remainder (carried over + new)

Associate filing flow (provisioning gap above — the one round-4 gap);
SuperAdmin workspace list (no such synthetic); exit-interview detail UI;
hard deletes; file bytes; payslip maths; responsive sweep. No new product
defects filed this round.

## Verification — expenses associate flow vs live 530a49f (2026-11-26)

Branch `agent/qa/cloud-expenses-verify` from main `530a49f`. Mandate:
confirm the nav fix is deployed before re-running.

**Verdict: fix NOT yet deployed — re-run BLOCKED pending
merge+push+redeploy. No workaround attempted; no specs run, no specs
touched.**

Evidence: both live deploys track main `530a49f` (re-verified this run via
the Render deploys API: latest live frontend and backend deploys both
report commit `530a49f`). The nav fix
(`7d4ab08 fix(expenses): absolute post-create navigate to /expenses/:id`)
exists only on unmerged branch `agent/feat/expenses-ui-navfix` — Render
builds pushed main only, so the deployed `ExpenseNew` still navigates
relative (`../${data.id}`). A minified-asset grep was inconclusive, so the
Render deploy-commit check is the canonical evidence. The associate-filing
spec (`cloud-expenses.spec.ts`, on unmerged `agent/qa/cloud-expenses`)
was therefore NOT executed against live; its post-submit URL assertion
(expect `/expenses/<id>`) remains unverified on the deployed build.
Next step for the owner: merge the navfix branch, push, wait for both
Render services live on the new SHA, then re-run
`e2e/cloud/cloud-expenses.spec.ts -g "associate files"`.
No credentials were staged and none were needed; no lockout signals;
working tree otherwise clean.

---

## Round 5 — expenses nav-fix verified live on abcbf62 (2026-11-26)

Branch `agent/qa/cloud-expenses-proof` from main `abcbf62` (navfix merge).
Deploy gate: frontend build of `abcbf62` polled `build_in_progress` → `live`
via the Render deploys API; `/expenses` 200 before testing.

**Verdict: D-fix VERIFIED live. Associate spec PASSES** (12.1 s, chromium):
file claim → post-submit URL matches `/expenses/<id>` (Playwright
`toHaveURL(/\/expenses\/\d+/)`, no `/6` tenant prefix — the relative
`../${id}` navigate is gone), receipt uploads with server download link,
submit persists `SUBMITTED`, zero console errors, zero failed requests.
Notably the test executed fully rather than skipping: `e2e_employee` now
resolves a linked employee row, so the round-4 provisioning gap is also
closed. No lockout signals (logins: 1 associate UI + API, 1 HR API setup —
all successful). No spec changes, no product changes; report-only commit.

---

## Round 6 — regression + interview scheduling on live f3bc760 (2026-11-26)

Branch `agent/qa/cloud-regression-r4` from main `f3bc760` (honesty-sweep
R2: interviews CRUD wired). Deploy gate: frontend live on `f3bc760` at
run start; backend polled `update_in_progress` → `live` on `f3bc760`
before testing. `/expenses` 200, app boots.

**Full cloud suite: 32 passed / 0 failed / 0 skipped, cloud-chromium
only** (25 carried + 3 expenses + 4 new interview). Zero console-error /
failed-request evidence in the run output.

| Spec | Pass / Fail / Skip | Evidence (one line) |
|---|---|---|
| cloud-auth (6) | 6 / 0 / 0 | all six roles sign in, API token mints, sign-out bounces to `/login`; no console errors |
| cloud-employee-lifecycle (4) | 4 / 0 / 0 | employee create 201 + directory serves; leave apply→approve persists `Approved`; employee create refused |
| cloud-ess-access (5) | 5 / 0 / 0 | self-service reads 200; `/admin/*` 403 cards; admin writes refused; 401s hold |
| cloud-helpdesk (4) | 4 / 0 / 0 | open→comment→history persist; HR queue screen SuperAdmin-only; stranger case 404; 401 |
| cloud-assets-documents (3) | 3 / 0 / 0 | register→assign custody persists; document v1→v2 history; employee create refused, stranger asset 404 |
| cloud-reports-exit (3) | 3 / 0 / 0 | dashboard/headcount/leave 200 + screen loads; termination→notes persist; employee mint refused |
| cloud-expenses (3) | 3 / 0 / 0 | associate file→receipt→submit persists `SUBMITTED`; HR submit→L1→final→paid persists `APPROVED`/`PAID`; associate sees no approve/pay buttons |
| cloud-interview-scheduling (4) | 4 / 0 / 0 | UI schedule 201 + ledger row reads back `Scheduled`; row PUT persists `Completed` + feedback; associate 403 card; unauth 401 |

New spec `frontend/e2e/cloud/cloud-interview-scheduling.spec.ts` (4/4):
HR schedules via UI (`#interview-candidate` + stage select + datetime +
panel → `POST /interviews` 201, `Interview scheduled.`, ledger row
visible, API reads back `Scheduled`); status→`Completed` + verbatim
feedback via row controls (`PUT`, `Interview updated.`, API read-back);
associate meets the ProtectedRoute 403 card at the same URL (spec first
asserted the component EmptyState — wrong layer, fixed to the 403
heading per the ess-access precedent); unauthenticated `GET /interviews`
→ 401. Setup seeds a namespaced candidate (`POST /candidates` 201);
no fabricated ids. Login budget respected (no 429/lockout signals).

### NOT TESTED remainder (carried over)

SuperAdmin workspace list (no such synthetic); exit-interview detail UI;
hard deletes; file bytes; payslip maths; responsive sweep. No new
product defects filed this round.

---

## Round 7 — responsive sweep on live 5945b9e (2026-11-26)

Branch `agent/qa/cloud-responsive` from main `5945b9e`. Deployed frontend
verified live on `5945b9e` before testing (Render deploys API). New spec
`frontend/e2e/cloud/cloud-responsive.spec.ts` (3 tests, 2 logins total —
one associate, one HR — viewport looped in-test, no state files).

**Full cloud suite: 35 passed / 0 failed / 0 skipped, cloud-chromium
only** (32 carried + 3 responsive).

| Width | login | dashboard (assoc+HR) | people | leave | expenses | ess | nav pattern |
|---|---|---|---|---|---|---|---|
| 360 | fit | fit | fit | fit | fit | fit | sidebar hidden, drawer trigger visible, bottom tab bar present |
| 768 | fit | fit | fit | fit | fit | fit | sidebar hidden, drawer trigger visible |
| 1024 | fit | fit | fit | fit | fit | fit | sidebar visible, drawer trigger hidden |
| 1440 | fit | fit | fit | fit | fit | fit | sidebar visible, drawer trigger hidden |

"Fit" = `scrollWidth <= innerWidth + 1px`, zero failures at every
width × page. Primaries hold at 360px: Sign in, drawer trigger, New
claim (both roles), Add employee (HR) — all visible + enabled. No tap-
target overlaps in scrolling content.

### Scanner fix, not a product defect (spec-only, committed)

First run flagged one 360px overlap: directory row button vs the `Time`
bottom-nav item (827px²). Diagnosis (live geometry, no extra
assertions): the bottom nav is `position: fixed` (`MobileBottomNav`,
`mobile-bottom-nav.tsx:23`, `z-[1100] lg:hidden`) and `main` reserves
`pb-20` (`Layout.tsx:170`), so rows scroll clear — flagging scrolled-
under fixed chrome would fail every scrollable page. The scan now
excludes `position: fixed` subtrees (designed chrome); genuine
scrolling-content overlaps still fail. Re-ran once per the flake rule:
green, no transients observed.

### NOT TESTED remainder (carried over)

SuperAdmin workspace list; exit-interview detail UI; hard deletes; file
bytes; payslip maths. No new product defects filed this round.
Login budget respected (2 spec logins + 1 diagnostic login, all
successful; zero 429/lockout signals).
