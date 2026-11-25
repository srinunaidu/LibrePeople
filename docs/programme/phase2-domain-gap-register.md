# Phase 2 Domain Gap Register
Changelog: 2026-11-24: 22-domain audit + gap register

## Fixed (this cycle)
1. ESS profile IDOR (security critical) — FIXED in 5cf0568 — ess_hr.py ownership via ensure_can_view_employee_or_403; ESSHub.tsx selector constrained; 51/51 tests
2. Requirements traceability (honesty) — FIXED in 5cf0568 — 122 VERIFIED corrected to 2 VERIFIED (105 IMPLEMENTED, 18 BLOCKED, 8 DEFERRED, 3 IN PROGRESS)

## Critical (open)
3. Helpdesk: employees cannot create cases — POST /cases is ADMIN-only (core_hr.py:840); employee self-service missing; SLA/queue/KB absent; suite has 1 failure (migration 0041 head). Owner: backend. Next: allow authenticated employee create + comment + SLA fields.
4. Backup/restore is read-only theatre — admin_status.py:39 reads tenant settings; no restore endpoint or drill. Owner: platform. Next: implement restore + drill evidence or gate page as read-only.
5. Payroll FY26-27 — pending_verification pack; all 15 PAY rows never VERIFIED; statutory sign-off outstanding. Owner: statutory reviewer. Next: independent professional verification; keep gratuity OFF.

## High
6. Workflow engine absent — approvals hardcoded in leave/timesheet/expenses; ApprovalWorkflows.tsx writes 3 flags. Next: design configurable chains, delegation, escalation, SLA timers; migrate existing approvals.
7. Expenses & travel UI missing — backend 16 routes exist, no /expenses route in App.tsx; marked DEFERRED. Next: wire UI or remove backend lane.
8. Statutory filing persistence — generation only (filings.py), no challan payment/acknowledgement upload/filing status; PT 5 states only; no 24Q validation. Next: add filing status model + endpoints + compliance suite.
9. Employee relations — no models/routes for grievance, discipline, investigation, PIP, whistleblowing; StatesDiscipline.tsx is flag shim. Next: design ER case type + confidentiality.
10. Document management UI — no standalone UI; expiry only as data-quality check; storage BLOCKED (local ephemeral or OCI). Next: document UI + expiry job + resolve storage backend.
11. SCIM endpoints absent — SCIMToken model exists (integrations_platform.py:35) with no endpoints. Next: implement SCIM or drop model.
12. Reporting scheduling/saved views — no scheduled/delivered reports; SavedViews.tsx is shim; no PDF/Excel export. Next: implement scheduling + persistence + export formats.
13. Assets depreciation/maintenance — no depreciation, maintenance, procurement or category API (grep depreciat=0). Next: design asset lifecycle + depreciation.

## Medium/Low
14. Contingent workers — config shim, no model (Core HR)
15. Probation/rehire/exit interviews — flag shims; no probation confirmation task from hire (Lifecycle)
16. Interview entity — no endpoint; InterviewScheduling.tsx writes flags (Recruitment)
17. WorkingTimeViolation — no read endpoint; violations only in roster responses (Attendance)
18. Leave accrual automation — only manual POST /entitlements; no accrual/carry-over/encashment job type (Leave)
19. Performance review cycles/360 — no cycles or peer nomination; calibration/PIP shims (Performance)
20. Learning content/SCORM/assessments/certificates — absent; paths/mentoring shims (Learning)
21. Benefits vendor/insurance/flex wallet/CTC breakup — absent (Compensation)
22. WFM demand-plan approval/publish — no lifecycle; no coverage-gap alerting endpoint (Workforce)
23. Platform: data-residency/deployment matrix BLOCKED (NFR-012/013); scheduler unproven without ortools

## Priority task list
1. Helpdesk employee self-create + SLA + fix failing suite — owner: backend — dependency: none — next: allow auth employee create/comment
2. Backup/restore implement + drill — owner: platform — dependency: tooling — next: restore endpoint + evidence
3. Payroll FY26-27 statutory sign-off — owner: statutory reviewer — dependency: independent professional — next: reviewer package
4. Workflow engine design — owner: architect — dependency: PRD scope decision — next: approval chain model + migration plan
5. Expenses UI or honest deferral — owner: frontend — dependency: backend lane decision — next: route + page or mark deferred
6. Statutory filing persistence — owner: backend — dependency: none — next: filing status model + endpoints
7. Employee relations module — owner: backend — dependency: PRD scope — next: ER case type design
8. Documents UI + expiry job — owner: frontend/backend — dependency: storage backend decision (LP-DOC-003)
9. SCIM endpoints or drop model — owner: backend — dependency: integration priority
10. Reporting scheduling + saved views + export — owner: backend/frontend — dependency: none

## Known limitations
- FY2025-26 payroll frozen; FY2026-27 pending independent verification; gratuity OFF
- PostgreSQL/Oracle live proof: toolchain absent (Class C)
- Performance targets: PROPOSED, no live measurement
- Licensing: ownership/dependency review incomplete
- 18 BLOCKED + 8 DEFERRED requirements (see requirements-traceability.csv)
- No production deployment, customer-data changes, or payroll activation without approval
