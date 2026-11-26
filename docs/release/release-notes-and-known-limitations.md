# LibrePeople — Release Notes and Known Limitations

**Status: Release candidate — NOT production-ready. Date: 2026-11-25.**
Baseline: `feature/librepeople-production` @ `24711ae`.

Authoritative status counts (`docs/product/requirements-traceability.csv`, 136 requirements):
**2 VERIFIED, 105 IMPLEMENTED, 3 IN PROGRESS, 18 BLOCKED, 8 DEFERRED.**
"IMPLEMENTED" means code exists but independent acceptance verification is absent or partial; it is not a release claim. Only LP-REC-006 and LP-REC-007 are VERIFIED.

## 1. What works

Implemented with passing suite evidence at the dates recorded; counts are cited runs, not re-run here.

- **Core HR / org** — employees, employment history, legal entities, locations, positions, departments, client onboarding. Suites: employees 64, employment_history 85, legal_entity 49, master_data 35, custom_fields 29 (2026-11-22).
- **Employees** — list/create/read/patch/history endpoints and People UI; master-data and custom-field support.
- **Attendance / scheduling** — time and attendance, rosters, timesheets. Scheduling solver requires ortools; 3 solver tests cannot run in the default env.
- **Leave** — requests, approvals, entitlements (manual), balances.
- **Payroll pipeline mechanics** — FY2025-26 rule pack `in-standard.json` v1.0.0 is `verified`; calculation/run mechanics and India engine math covered by `india_payroll_test_suite.py` (114 passed, 2026-11-22). FY2025-26 is frozen.
- **ESS (employee self-service)** — profile, notifications, employee files. The critical ESS profile IDOR is fixed (`5cf0568`): ownership enforced via `ensure_can_view_employee_or_403`; ESSHub selector constrained; **51/51 tests**, plus 2162/0 security and 29/0 related.
- **Recruitment core** — requisitions, candidates, applications, offers; REC-006/007 are the only VERIFIED rows.
- **Performance / learning core** — goals, reviews, courses, course enrolments (endpoint-level suites absent).
- **Expenses backend** — 16 routes in `expenses.py`; no UI (deferred).
- **Assets** — assets endpoint/model present; no depreciation, maintenance, procurement or category API.
- **Reporting core** — dashboard, headcount, labour cost, audit report.
- **Admin** — login/register, MFA, break-glass, user admin, tenant branding, module entitlements; admin_status 32 passed.
- **Honest-feedback UX slices 1–3** — 684 slice tests (20 + 552 + 112), full frontend **811/811 (15 files)**; `npm run verify` EXIT 0; security **2162/0**; ESS **51/51**.

## 2. Partially implemented (IMPLEMENTED, not independently verified)

Each line states what remains. "Harness" means an independent acceptance-harness run on the current HEAD; a green unit/integration suite alone is not acceptance.

**ADM (5)**
- LP-ADM-001 — login: harness pass pending.
- LP-ADM-002 — register: harness pass pending.
- LP-ADM-003 — MFA enrol: harness pass pending.
- LP-ADM-004 — break-glass grant: harness pass pending.
- LP-ADM-005 — admin status: harness pass pending (32 passed).

**AUD (6)**
- LP-AUD-001 — verify: harness pass pending.
- LP-AUD-002 — audit report: harness pass pending.
- LP-AUD-003 — verify: harness pass pending.
- LP-AUD-004 — audit report: harness pass pending.
- LP-AUD-005 — admin audit: route-mount suite failing (`got []`).
- LP-AUD-006 — admin audit: route-mount suite failing (`got []`).

**COMP (12)**
- LP-COMP-001 — compliance rules: no dedicated endpoint suite.
- LP-COMP-002 — create rule: no dedicated endpoint suite.
- LP-COMP-003 — violations list: no dedicated endpoint suite.
- LP-COMP-004 — violation create: no dedicated endpoint suite.
- LP-COMP-005 — violation resolve: no dedicated endpoint suite.
- LP-COMP-006 — headcount plans: no dedicated endpoint suite.
- LP-COMP-007 — scenarios: no dedicated endpoint suite.
- LP-COMP-008 — report definitions: no dedicated endpoint suite.
- LP-COMP-009 — saved reports: no dedicated endpoint suite.
- LP-COMP-010 — rules list: no dedicated endpoint suite.
- LP-COMP-011 — rule create: no dedicated endpoint suite.
- LP-COMP-012 — violations list: no dedicated endpoint suite.

**CORE (10)**
- LP-CORE-001 — employee list: harness pass pending.
- LP-CORE-002 — employee create: harness pass pending.
- LP-CORE-003 — employee read: harness pass pending.
- LP-CORE-004 — employee patch: harness pass pending.
- LP-CORE-005 — history read: harness pass pending.
- LP-CORE-006 — locations: harness pass pending.
- LP-CORE-007 — legal entities: harness pass pending.
- LP-CORE-008 — positions: harness pass pending.
- LP-CORE-009 — departments: harness pass pending.
- LP-CORE-010 — client onboarding: harness pass pending.

**DATA (7)**
- LP-DATA-001 — CSV import: `import_test_suite` failing (QueuePool exhaustion).
- LP-DATA-002 — templates: harness pass pending.
- LP-DATA-003 — dry-run: harness pass pending.
- LP-DATA-004 — data quality: harness pass pending.
- LP-DATA-005 — CSV export: harness pass pending.
- LP-DATA-006 — templates: harness pass pending.
- LP-DATA-007 — dry-run: harness pass pending.

**DOC (2)**
- LP-DOC-001 — document list: harness pass pending; no standalone UI.
- LP-DOC-002 — document create: harness pass pending; no expiry job.

**ESS (6)**
- LP-ESS-001 — ESS profile: harness pass pending (IDOR fixed).
- LP-ESS-002 — profile create: harness pass pending.
- LP-ESS-003 — notifications list: harness pass pending.
- LP-ESS-004 — unread count: harness pass pending.
- LP-ESS-005 — notification create: harness pass pending.
- LP-ESS-006 — employee files: harness pass pending.

**INT (5)**
- LP-INT-001 — SSO/SCIM/webhook config: harness pass pending; SCIM endpoints absent.
- LP-INT-002 — integration config: harness pass pending; SCIM endpoints absent.
- LP-INT-003 — import: import-lane suite failing.
- LP-INT-004 — import: import-lane suite failing.
- LP-INT-005 — import: import-lane suite failing.

**LEAVE (8)**
- LP-LEAVE-001 — requests: harness pass pending.
- LP-LEAVE-002 — approvals: harness pass pending.
- LP-LEAVE-003 — balances: harness pass pending.
- LP-LEAVE-004 — types: harness pass pending.
- LP-LEAVE-005 — entitlements: harness pass pending.
- LP-LEAVE-006 — calendar: harness pass pending.
- LP-LEAVE-007 — policy: harness pass pending.
- LP-LEAVE-008 — reporting: harness pass pending.

**LIFE (9)**
- LP-LIFE-001 — benefit plans list: no dedicated benefits suite.
- LP-LIFE-002 — benefit plan create: no dedicated benefits suite.
- LP-LIFE-003 — enrolments list: no dedicated benefits suite.
- LP-LIFE-004 — enrolment create: no dedicated benefits suite.
- LP-LIFE-005 — life events list: no dedicated benefits suite.
- LP-LIFE-006 — life event create: no dedicated benefits suite.
- LP-LIFE-007 — leaves of absence list: no dedicated benefits suite.
- LP-LIFE-008 — LOA create: no dedicated benefits suite.
- LP-LIFE-009 — LOA approve: no dedicated benefits suite.

**NFR (9)**
- LP-NFR-001 — security headers/errors: TESTED ceiling; harness pass pending.
- LP-NFR-002 — auth/session: TESTED ceiling; harness pass pending.
- LP-NFR-003 — RBAC: TESTED ceiling; harness pass pending.
- LP-NFR-004 — tenant isolation: TESTED ceiling; harness pass pending.
- LP-NFR-005 — auditability: TESTED ceiling; harness pass pending.
- LP-NFR-006 — data handling: TESTED ceiling; harness pass pending.
- LP-NFR-007 — availability: TESTED ceiling; harness pass pending.
- LP-NFR-008 — operability: TESTED ceiling; harness pass pending.
- LP-NFR-014 — hardening gate: harness pass pending.

**NOT (1)**
- LP-NOT-002 — unread count: harness pass pending.

**REC (5)**
- LP-REC-001 — requisitions: harness pass pending.
- LP-REC-002 — candidates: harness pass pending.
- LP-REC-003 — applications: harness pass pending.
- LP-REC-004 — offers: harness pass pending.
- LP-REC-005 — recruitment reports: harness pass pending.

**REP (4)**
- LP-REP-001 — dashboard: harness pass pending.
- LP-REP-002 — headcount: harness pass pending.
- LP-REP-003 — labour cost: harness pass pending.
- LP-REP-004 — audit report: harness pass pending.

**TAL (6)**
- LP-TAL-001 — goals list: no dedicated performance/learning suite.
- LP-TAL-002 — goal create: no dedicated performance/learning suite.
- LP-TAL-003 — reviews list: no dedicated performance/learning suite.
- LP-TAL-004 — review create: no dedicated performance/learning suite.
- LP-TAL-005 — courses list: no dedicated performance/learning suite.
- LP-TAL-006 — enrolments list: no dedicated performance/learning suite.

**TIME (10)**
- LP-TIME-001 — attendance: harness pass pending.
- LP-TIME-002 — clock events: harness pass pending.
- LP-TIME-003 — timesheets: harness pass pending.
- LP-TIME-004 — timesheet approve: harness pass pending.
- LP-TIME-005 — rosters: harness pass pending.
- LP-TIME-006 — roster publish: harness pass pending.
- LP-TIME-007 — attendance report: harness pass pending.
- LP-TIME-008 — schedule solve: ortools absent in this env.
- LP-TIME-009 — schedule publish: ortools absent in this env.
- LP-TIME-010 — coverage: ortools absent in this env.

## 3. Unsupported / deferred (8)

- **Expenses UI** — LP-EXP-001 (categories), LP-EXP-002 (claims list), LP-EXP-003 (claim create) deferred; backend routes exist but no `/expenses` UI route.
- **Notifications** — LP-NOT-001 (list), LP-NOT-003 (create) deferred; LP-NOT-002 unread count is IMPLEMENTED only.
- **Helpdesk/service** — LP-SVC-001 (list cases), LP-SVC-002 (create case), LP-SVC-003 (comment) deferred as requirements; associate self-service create/comment was added in `24711ae`, but SLA/queue/KB remain absent.

## 4. Blocked outside engineering (18)

- **FY2026-27 statutory sign-off** — LP-PAY-001…LP-PAY-015 (15 rows). FY2025-26 pack is verified and frozen; FY2026-27 skeleton is `pending_verification`; independent professional review outstanding. Gratuity remains **OFF**.
- **PostgreSQL/Oracle live proof** — toolchain absent (Class C). No live DB proof claimed.
- **Performance targets** — PROPOSED only; no live measurement. LP-NFR-009/010/011 are IN PROGRESS, not proven.
- **Licensing** — ownership and dependency review incomplete.
- **Owner decisions** — LP-NFR-012/013 (data residency, supported deployment matrix, Cloudflare target) and LP-DOC-003 (storage matrix/scope) have no approval.

## 5. Known defects and limitations

- **Helpdesk SLA not enforced** — `sla_due` is stored (`backend/app/models/core_hr.py:262`) but unread/uncomputed; no breach handling.
- **Backup/restore is read-only** — `admin_status.py` reads tenant settings; no restore endpoint or drill.
- **No workflow engine** — approvals are hardcoded in leave/timesheet/expenses; no configurable chains, delegation, escalation or SLA timers.
- **No employee relations** — no grievance, discipline, investigation, PIP or whistleblowing models; discipline UI is a flag shim.
- **Documents have no expiry job** — expiry is only a data-quality check; no standalone document UI.
- **SCIM has no endpoints** — `SCIMToken` model exists in `integrations_platform.py`; no SCIM routes.
- **No report scheduling** — no scheduled/delivered reports, saved views are a shim, no PDF/Excel export.
- **Assets have no depreciation** — no depreciation, maintenance, procurement or category API.
- **Statutory filing is generation-only** — no challan payment, acknowledgement upload, filing status; PT covers 5 states; no 24Q validation.
- **Other gaps** — contingent workers, probation/rehire/exit interviews are shims; no interview entity; WorkingTimeViolation has no read endpoint; no leave accrual/carry-over/encashment; no review cycles/360; no SCORM/assessments/certificates; no benefits vendor/insurance/flex wallet/CTC breakup; no WFM demand-plan lifecycle or coverage alerting.

## 6. Configuration requirements

- **Python 3.11 + ortools 9.15** for scheduling, in `.venv311`. Without ortools, scheduling suites raise `RuntimeError` (LP-TIME-008…010).
- **PostgreSQL** for new installs; SQLite is test-only. **Oracle compatibility is untested.**
- **Secret keys** via environment; no hardcoded bootstrap seed.
- **Storage backends** — local directory (ephemeral default) or OCI Object Storage (opt-in). No S3/GCS. LP-DOC-003 unresolved.
- **MFA/step-up** enforced for privileged roles; impersonation and admin MFA reset require password or TOTP.

## 7. Security and operational prerequisites

- MFA enrolled for all privileged accounts; break-glass access limited and audited.
- Tenant isolation: cross-tenant tests 31 passed; re-run on target deployment.
- No public deployment, customer-data change, payroll activation or production cutover without explicit approval.
- Rollback: keep the FY2025-26 pack frozen; do not enable FY2026-27 or gratuity.

## 8. Evidence pointers

- Traceability: `docs/product/requirements-traceability.csv` (authoritative counts; DictReader).
- Gap register: `docs/programme/phase2-domain-gap-register.md`.
- Frontend 811/811: `docs/programme/ux/E-UX-03-ux-slice3.md:61`.
- ESS 51/51 + security 2162/0: `docs/programme/multi-agent-coordination.md:12`.
- Suites: `backend/security_test_suite.py`, `backend/scheduling_test_suite.py`, `backend/*_test_suite.py`.
- Tracker: `docs/release/production-readiness-tracker.md` — its "122 VERIFIED" line is stale (pre-reconciliation); use the CSV.

## 9. Changelog

`2026-11-25 — docs/release: initial release notes and known limitations (RC, not production-ready); statuses per traceability CSV at 24711ae.`

## 10. Addendum 2026-11-26 (supplements, does not rewrite, §§1–9 above)

Authoritative counts are now `docs/product/requirements-traceability.csv`: **104 VERIFIED / 3 IMPLEMENTED / 3 IN PROGRESS / 18 BLOCKED / 8 DEFERRED (136)** — header comment updated this date; data rows untouched. The §1–§9 text above (baseline `24711ae`, 2 VERIFIED) is pre-promotion and stays for history.

- **Promotion 102 (cdf613c).** 102 rows flipped IMPLEMENTED→VERIFIED on harness evidence (dry-run + full pass; scheduling excluded, so LP-TIME-008/009/010 remain the 3 IMPLEMENTED). Pre-flip snapshots and post-flip expected counts are asserted in the harness (344ecfd); head handling made durable via `ScriptDirectory.get_heads` (cfba523; india suite accepts head `0049_interviews`, 114/0 per 8ec76b2).
- **Expenses UI now exists.** Slice acb7a24: `/expenses`, `/expenses/new`, `/expenses/:id` + list/detail/create + L1/L2 approve + mark-paid + receipts, 18/18 tests; navfix 7d4ab08 (absolute post-create navigate) merged via 530a49f/abcbf62. Cloud E2E round 4 (2 passed / 1 skipped on provisioning) + round 5 (associate flow PASSES live on abcbf62, zero console errors) — see `docs/cloud-e2e-report.md`. Matrix LP-EXP-001…003 now IMPLEMENTED (CSV still DEFERRED pending reconciliation). §3 "no /expenses UI route" is superseded.
- **Small gaps closed (1b945fb).** Working-time violation reads (f3b2cd4, 14 checks), leave monthly accrual + carry-over via `leave_accrual` job type (b7d7ecf, 22 checks), interview entity + CRUD + `0049` migration (8aa1d6c, 19 checks), role policy for 7 new operations (7a2b2c1). §5 shims for violations/accrual/interviews are superseded.
- **Fixture allowlists (88cb314, merged e1a26ad).** `InterviewPass123` / `LeaveAccrPass123` are local-only fixture passwords confined to their own suite files (same exact-value mechanism as the `MfaColRegPass123!` precedent). `python3 ci/secret_scan.py` clean.
- **E2E proof since §8.** Cloud round 3: 25/25 live (auth, employee lifecycle, ESS access, helpdesk, assets/documents, reports+exit); expenses rounds 4–5 as above (`docs/cloud-e2e-report.md`). Local: desktop 100 + responsive 16 (`docs/release/e2e-report.md`); Firefox run host-blocked, Chromium baseline 116 (`docs/release/e2e-report-firefox.md`). Matrix E2E column cites per-row evidence (21 rows PASS, rest NOT RUN).
- **D-01…D-06 dispositions (`docs/api-discrepancy-report.md`, base 216e869).** D-02/D-03 closed by contract sweep a0a1fc5 (reports auth R/M/A; full auth table — contract was stale, impl correct). D-04/D-05 closed by 502b672/2f05c5f (employees PATCH+history rows; post-Phase-7 scope note). D-06 no action (spot-checks passed). D-01 NOT closed: fix prescribed (move `test_assets.py` to `backend/tests/`) but the file is still in `endpoints/` with 0 routes — move pending.
