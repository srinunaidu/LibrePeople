# Feature: reporting-personalization
## Behavior
Part E (saved views, separately shippable): REPORTS_ROLES users save named filter sets for existing read-only reports (joiners/leavers/attrition/payroll-summary), list/edit/delete own views, and open shared views published to their role. Part F (scheduled reporting, separately shippable): REPORTS_ROLES users create schedules (report key + stored filters + frequency + timezone) with explicit recipients; execution runs via the existing JobWorker as a new JobType.REPORT_RUN job and delivers an in-app notification with a download link (CSV/XLSX via existing export path). Scheduled execution uses the OWNER's permissions and recipients must individually hold access — a recipient outside the report's role set gets no data (runs-as-owner scoping).
## Acceptance criteria
Part E — saved views:
1. POST /api/v1/report-views (REPORTS_ROLES, tenant-scoped) persists {name, report_key, filters} and GET lists only rows where owner_id=caller OR (visibility=shared AND role-gate passes); cross-tenant id returns 404.
2. PATCH/DELETE /api/v1/report-views/{id} by non-owner non-admin returns 403; shared-view publish requires HR/SuperAdmin, Manager/Associate publish attempt returns 403.
3. Only allowlisted report_key values (joiners, leavers, attrition, payroll-summary) validate; unknown key returns 422 and no row is written.
4. Empty states: new user sees "No saved views yet" with create CTA; deleting last view returns to empty state (frontend test).
Part F — scheduled reporting:
5. POST /api/v1/report-schedules validates {report_key, filters, frequency in {daily,weekly,monthly}, timezone (IANA), recipient_user_ids}; invalid tz/frequency returns 422; schedule creation enqueues nothing synchronously.
6. Due tick enqueues JobType.REPORT_RUN through JobQueueService.enqueue (reuse, dedupe on pending) and JobWorker executes the registered @register(JobType.REPORT_RUN) handler — no new scheduler/cron process.
7. Delivery = in-app Notification row per recipient + CSV/XLSX download link via existing report_exports path; email sent only when EMAIL_PROVIDER=smtp configured (default log provider = no email; documented, not a failure).
8. Runs-as-owner: worker resolves data with owner's resolve_visible_employee_ids + role mask; recipient lacking the report's role gets a notification stating "not available for your role" and no file; payroll-summary schedule with Associate recipient never leaks identifiers (negative test).
9. Failure semantics: transient failure → failed + retry with backoff (max_attempts=5); bad input → JobInputInvalid dead-letter at once; every run writes an audit row (export, schedule id, owner, recipient count).
## Non-goals
No change to existing report calculations, masking, or CSV/XLSX bytes; no new report types or metrics; no email/SMS/push provider build-out; no manager-delegation or public-link sharing; no backfill of shim feature-flag configs.
## Interfaces / data
New tables: report_saved_views(id, tenant_id, owner_id, name, report_key, filters_json, visibility[personal|shared], created_at); report_schedules(id, tenant_id, owner_id, report_key, filters_json, frequency, timezone, recipient_ids_json, next_due_at, active); report_runs(id, schedule_id, job_id, status, created_at). New JobType.REPORT_RUN="report_run". Endpoints: /api/v1/report-views + /api/v1/report-schedules (+/runs, /run-now). RBAC: views/schedules require REPORTS_ROLES; share/publish requires HR/SuperAdmin.
## Test plan
pytest backend/tests/test_report_views.py backend/tests/test_report_schedules.py -q (CRUD, 403-negative for Manager publish + Associate access, cross-tenant 404, invalid tz/key 422, runs-as-owner masking, retry/dead-letter via worker fake); pytest backend/tests/test_cross_tenant.py -q tenant-isolation; npm run typecheck + new frontend component tests for empty states.
## Risk tier
2 (normal)
## Rollback
Disable routes (remove router include), deregister REPORT_RUN handler, set schedules active=false; alembic downgrade new migration(s); export user-created views first — data loss otherwise. Shim pages untouched so UI falls back.
## Open decisions — RESOLVED by lead 2026-11-26
D1 default timezone = tenant timezone. D2 shared views are role-targeted (visible to roles that can view the report), not org-wide broadcast. D3 in-app + optional-SMTP sufficient; guaranteed email out of scope.
## NO-GO (STOP and report, do not invent)
Do not alter existing reports.py semantics/masking; do not invent a cron daemon or new queue; do not add email infra; do not store recipient data outside tenant; do not expose payroll identifiers to unauthorized roles; do not migrate shim feature-flag configs.
