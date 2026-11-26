# Feature: Employee Relations (confidential ER module) — FULL BUILD

Owner decision (2026-11-26): build the FULL confidential ER module now (not deferred).
Branch: `agent/feat/er-module` from `main` @ `71ce36d` (verified via `.git/refs/heads/main`;
working HEAD at branch time was `a931601` on `agent/qa/cloud-assets-interview` — NOT used as base).
Lead decisions: **D1** reporter identity REQUIRED, authenticated only — NO anonymous intake in v1.
**D2** no PIP linkage in v1. **D3** closed cases retain full history — no auto-seal.

## Gap and references (all verified before writing)

- Gap #9 (`docs/programme/phase2-domain-gap-register.md:17`): "Employee relations — no
  models/routes for grievance, discipline, investigation, PIP, whistleblowing;
  `StatesDiscipline.tsx` is flag shim. Next: design ER case type + confidentiality."
- Helpdesk reference (`backend/app/api/v1/endpoints/core_hr.py:736-965`): forward-only status
  machine (`CASE_NEXT_STATUS`), `_is_helpdesk_admin`, `_ensure_can_access_case` (404-never-403),
  both-or-neither attachment validation under `AUTHORISED_FILES_PREFIX`, append-only comments.
- `HRCase` model (`backend/app/models/core_hr.py:237-276`) + `CaseComment` (`:279-304`).
- Visibility helpers (`backend/app/core/visibility.py`): `apply_visibility` (:138),
  `ensure_can_view_employee` (:175, 404-not-403).
- Frontend pattern (`frontend/src/pages/admin/HRHelpCases.tsx`): `Layout`/`PageHeader`/
  `SectionCard`/`api` lib, role-gated route (`App.tsx:335`).
- `requirements-traceability.csv`: grep for `LP-ER|grievance|discipline|whistleblow|\bpip\b`
  returns **0 hits** — CONFIRMED no scope conflict; this contract governs.
- RBAC: `ADMIN_ROLES = ("SuperAdmin", "HR")` (`backend/app/api/deps.py:85`).
- Audit: `record_audit(db, actor, action, entity, id, details=)` (`backend/app/core/audit.py:63`).
- Files: `AUTHORISED_FILES_PREFIX = "/api/v1/files/"` (`backend/app/storage/backends.py:46`).
- Migration head: `0050_workflow_steps` (down_revision `0049_interviews`). NOTE: two stale side-branch
  heads (`0017_forecast_costs`, `0018_scenario_versions`) pre-exist; this slice chains off `0050`
  and does not touch them.

## WHY new tables (not `hr_cases`)

Confidentiality scoping differs fundamentally: `hr_cases` grants the requester (subject)
visibility of their own case (`_ensure_can_access_case`, `core_hr.py:773-790`). ER must DENY
the subject any visibility — a grievance/discipline subject must not see or infer the case.
Inheriting `hr_cases` semantics would leak ER subjects/complainants. Separate tables give
deny-by-default visibility. `hr_cases` semantics, routes and visibility are UNCHANGED.

## Data model (new tables only)

- `er_cases`: `id`, `tenant_id` (nullable, legacy-default pattern), `case_type`
  {grievance, discipline, investigation, whistleblowing} — NO `pip` (D2),
  `subject_employee_id` FK nullable (validated via `ensure_can_view_employee` when present),
  `reported_by` username NOT NULL (D1: authenticated reporter, no anonymous intake),
  `severity` {Low, Medium, High, Critical}, `status` (machine below, default `Open`),
  `assigned_to` username nullable, `classification` text nullable,
  `outcome` text nullable (REQUIRED at Resolved), timestamps, `resolved_at` nullable.
- `er_case_comments`: `case_id` FK → `er_cases.id`, `author`, `comment`, `created_at`.
  Append-only: NO update/delete routes.
- `er_case_attachments`: `case_id` FK, `filename`, `file_key` (must be under
  `AUTHORISED_FILES_PREFIX`), `uploaded_by`, `created_at`. Both-or-neither filename/key.
- No DB enums (PG-clean): plain `String` + service-enforced FSM + `CheckConstraint`s.

## Flows

create (HR-only) → classify → assign investigator → investigate (append-only comments,
attachments via existing `/files` infra) → record action → resolve (outcome required) →
close. Closed cases retain full history (D3). Summary endpoint returns aggregates only.

## Acceptance criteria

1. `POST /er-cases` (`ADMIN_ROLES` only; non-admin → 403 from `require_roles`) creates a case
   with `case_type` in {grievance, discipline, investigation, whistleblowing}; `pip` or any
   other value → 422; `reported_by` is set from the authenticated user (never from payload);
   `subject_employee_id` when present validated via `ensure_can_view_employee`; audited.
2. Status machine `Open > Triaged > Investigating > ActionTaken > Resolved > Closed`, one step
   at a time; illegal jump/backward move → 422 `invalid_status_transition`; `Resolved` requires
   non-blank `outcome` → else 422; resolving stamps `resolved_at`.
3. Confidentiality: non-HR, non-assignee `GET /er-cases`, `GET /er-cases/{id}`,
   `GET /er-cases/{id}/comments` ALL return 404 (never 403) — proven as requester, subject
   employee, manager, and cross-tenant HR. Subject employees CANNOT see cases about themselves.
4. Assignee (`assigned_to` == username, non-HR) can read and append comments on assigned case
   only; cannot list queue (`GET /er-cases` → 404 or empty — fixed: 404) nor read unassigned
   cases (404). Assignee cannot change status/classification/assignment (HR-only `PUT` → 403).
5. Comments and attachments are append-only (no PUT/DELETE routes); attachment filename/key
   both-or-neither with key under `AUTHORISED_FILES_PREFIX`, else 422.
6. `GET /er-cases/summary` (HR-only) returns counts by `case_type`/`status` ONLY — no ids,
   names, narratives, or subject identifiers anywhere in the output.
7. Every mutation calls `record_audit` (`create_er_case`, `triage_er_case`, `assign_er_case`,
   `add_er_comment`, `add_er_attachment`, `resolve_er_case`, `close_er_case`); audit `details`
   carry ids/statuses only, NEVER narrative text.
8. Tenant isolation: `tenant_id` column + `tenant_column_criterion` scoping on list/detail;
   cross-tenant read returns 404 (even for HR of another tenant).
9. `hr_cases`/`case_comments` semantics, routes and visibility UNCHANGED (regression proven by
   existing `hr_helpdesk_test_suite.py` still green).
10. Migration `0051` upgrades a fresh DB to head and downgrade→upgrade round-trips clean on
    sqlite AND scratch PostgreSQL (if toolchain present; else sqlite + PG-safe pattern review).

## File ownership (exact — no other files may be touched)

- NEW `backend/app/models/er_case.py` (ERCase, ERCaseComment, ERCaseAttachment)
- EDIT `backend/app/models/__init__.py` (export only, one line)
- NEW `backend/app/schemas/er_cases.py`
- NEW `backend/app/api/v1/endpoints/er_cases.py` (NOT extending `core_hr.py`: its
  `_ensure_can_access_case` grants requester visibility — the exact semantic ER must not inherit)
- EDIT `backend/app/api/v1/api.py` (router registration, two lines)
- NEW `backend/migrations/versions/0051_er_cases.py` (ONE migration; checkfirst/catalog pattern
  copied from `0050_workflow_steps.py`; no model imports; no enums)
- NEW `frontend/src/pages/er/ERCases.tsx` (HR-only queue + detail + comments + summary counts)
- EDIT `frontend/src/App.tsx` (lazy import + `/admin/er-cases` route, `SuperAdmin`+`HR` gate)
- NEW `backend/er_cases_test_suite.py`

## Test plan

New `backend/er_cases_test_suite.py` (run: `python er_cases_test_suite.py` from `backend/`):
lifecycle + FSM-machine + append-only + attachment-validation + 404-negative matrix (requester /
subject / manager / non-assignee / cross-tenant HR) + assignee-scoped access + aggregate-leak
(narrative/ids absent from summary) + tenant-isolation + audit-rows-present. Related suites must
stay green: `hr_helpdesk_test_suite.py`, `cross_tenant_test_suite.py`, `security_test_suite.py`.
Frontend: `npm run build` + `npm run typecheck` green. Migration: `alembic upgrade head` +
`downgrade -1` + `upgrade head` on scratch PG (cleanup after), sqlite round-trip in suite.

## Risk tier

2 (normal) — new tables/routes, confidential data, no irreversible change to existing data.
Confidentiality regression is the top risk; the 404-negative matrix is the backstop.

## NO-GO list (STOP and report BLOCKED with file:line instead of working around)

- Any required change to existing tables' semantics, columns or constraints.
- Any required change to `hr_cases` routes/visibility to accommodate ER.
- Any confidentiality question not answerable deny-by-default (subject visibility, anonymous
  intake pressure, aggregate leakage).
- `alembic upgrade head` failing on scratch PG, or multiple-head ambiguity involving `0051`.
- Anonymous/public intake being required by another stakeholder (D1 forbids; escalate).

## Rollback

Unregister `er_cases` router + `alembic downgrade -1` (drops `er_case_attachments`,
`er_case_comments`, `er_cases`); `hr_cases` data and routes unaffected. Frontend route removal
is a two-line revert in `App.tsx` + deleting `pages/er/`.
