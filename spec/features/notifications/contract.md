# Feature: notifications (LP-NOT-001) — event-driven notification centre

## Goal
State changes that affect a specific person (leave decisions, pay-run progress,
onboarding/offboarding milestones) emit one in-app notification to that person
at the moment the change is decided, readable in the ESS notification centre.
No delivery provider yet (LP-NOT-002 owns delivery); this slice is emission +
centre reads only.

## Approved scope (do not relitigate)
`backend/app/services/notifications.py` (emit + duplicate guard + preference
stub gate) + emission call sites in `leave.py`, `payroll.py`, `onboarding.py`,
`offboarding.py` + centre reads in `ess_hr.py` (list, unread-count, mark-read,
preferences read; create stays ADMIN-only) + `backend/notification_centre_test_suite.py`
wired into `ci/run_backend_tests.sh`. No schema change, no migration, no email/SMS/push
sending (`email_sent` stays `False` until LP-NOT-002).

## Read-access decision (explicit — not a bug)
Centre reads are **owner-only**, not owner-or-HR. `recipient_id` is a *user* id,
so the employee-visibility filter does not apply: every endpoint scopes to the
caller's own login. Listing with another user's `recipient_id`, or acknowledging
another user's row, answers 403 — including for HR/SuperAdmin callers. Rationale:
notifications are personal; HR already sees every underlying HR record through
their own endpoints, so HR privilege gains nothing here except cross-reading a
colleague's inbox. If a future support/audit need requires it, it belongs to a
new slice with its own audit trail, not to this one.

## Acceptance criteria
- AC-1 (emissions): leave create notifies the requester (receipt), approve
  notifies success, reject notifies warning, and a refused decision (e.g. no
  entitlement, 409) notifies nobody; payroll process/finalize notify the
  operator and every slip employee on success only (refused process/finalize
  notifies nothing); onboarding notifies the employee only on the crossing
  into Completed; offboarding start notifies warning and completion notifies
  success. Each case writes exactly one row per recipient.
- AC-2 (duplicate guard): re-emitting the same
  `(recipient, category, entity_type, entity_id, notification_type, title)` key
  returns the first row instead of inserting a second; entity-less emissions
  dedupe on `(recipient, category, notification_type, title)` against NULL-entity
  rows only and never collide with keyed rows.
- AC-3 (preference stub gate): a recipient with all three channel flags off
  receives no row while the underlying change still commits (403-free skip);
  a recipient with no ESS profile reads defaults (email+push on, sms off) and
  is notified normally; nothing in this slice sets `email_sent`.
- AC-4 (owner-only centre): unread-count counts only the caller's own unread
  rows; the list shows only the caller's own rows and a foreign `recipient_id`
  answers 403; mark-read succeeds for the owner (idempotent on re-read) and
  answers 403 for anyone else; preferences read returns the caller's own flags.
- AC-5 (suite gate): `backend/notification_centre_test_suite.py` passes with 0
  failures (53 checks); `payroll_test_suite` (251/0) and `ess_hub_test_suite`
  (37/0) pass unchanged; `leave`, `payroll_execution`, and `onboarding` suites
  fail identically with and without this slice (pre-existing environment
  failures: SQLite ALTER, MFA-gated profile create, retail-preset validation —
  verified byte-identical at base `f2578d8`); a base-vs-branch probe shows
  payroll process + onboarding completion emitting 0 rows at base and ≥1 on
  the branch.
