# Karmathy HCM — Feature Catalog (target capability specification)

**Status:** target state. **Not** a statement of what exists — that is `docs/product/FEATURE_MATRIX.md`.

**Date:** 2026-10-21 · **Phase:** 0 (audit and decisions) · **Owner:** Super Agent

Every capability in the mandate has a stable ID. The ID is the single key used by the matrix, the task board, the request files and the validation reports. The status of a capability lives in `docs/product/FEATURE_MATRIX.md`; the row-level evidence lives in `docs/validation/FEATURE_MATRIX.md` (owned by QA & Validation). Nothing here duplicates a status.


## Domains

| Prefix | Domain | Accountable lane | Capabilities |
|---|---|---|---|
| `HR-` | Core HR and organisation | workforce-core | 12 |
| `RC-` | Recruitment and talent acquisition | workforce-core | 8 |
| `OB-` | Onboarding, mobility and offboarding | workforce-core | 7 |
| `TM-` | Time and attendance | workforce-core | 5 |
| `LV-` | Leave | workforce-core | 5 |
| `SC-` | Scheduling and workforce operations | planning | 10 |
| `PY-` | Payroll and compensation | payroll-rules | 10 |
| `BN-` | Benefits and employee services | workforce-core | 6 |
| `PM-` | Performance and talent | workforce-core | 6 |
| `LN-` | Learning and skills | workforce-core | 7 |
| `AN-` | Workforce analytics and planning | planning | 8 |
| `UX-` | Employee and manager experience | frontend-design | 10 |
| `AD-` | Tenant administration and platform operations | platform-security | 10 |
| `CF-` | Industry presets and the configuration assistant | onboarding-config | 14 |
| `IM-` | CSV import | data-import | 12 |
| `AI-` | AI capability and governance | platform-security | 13 |

**Total capabilities: 143.**


## Core HR and organisation (`HR-`)

Accountable lane: **workforce-core**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `HR-01` | Employee master records, employee number, contact, emergency contacts | One employee record; unique employee number; contact details; emergency contacts as a related collection. | High — personal data | M |
| `HR-02` | Employment status, type, dates, contract, probation, notice | Employment status and type as a state machine with reasons; contract start/end; probation and notice periods. | Medium — internal detail | L |
| `HR-03` | Effective-dated changes and complete employment history | Every change to job, department, location, manager or pay profile is a dated row; reads resolve 'as of' a date. | Medium — internal detail | L |
| `HR-04` | Departments, positions, grades, job families, reporting lines, cost centres | Full organisation structure with grades, families and cost centres; reporting lines derived from manager assignment. | Low — non-sensitive | L |
| `HR-05` | Multi-entity and multi-location organisation | Support for more than one legal entity inside one deployment. | Low — non-sensitive | L |
| `HR-06` | Org chart and employee directory | Org chart from manager relationships with cycle detection; a directory scoped to what the caller may see. | Medium — internal detail | M |
| `HR-07` | Employee document storage, expiry reminders, acknowledgements | Documents with type, expiry date, reminder schedule and an acknowledgement record. | High — personal data | M |
| `HR-08` | Custom fields, configurable attributes, controlled bulk updates | Tenant-defined employee attributes and audited bulk updates. | Medium — internal detail | XL |
| `HR-09` | Manager assignments, delegated responsibility, lifecycle events | Manager assignment with effective dates and delegation for absence. | Medium — internal detail | M |
| `HR-10` | Contingent workers and contractors | Separate employment type with contractor-specific fields and limited module access. | Medium — internal detail | L |
| `HR-11` | Validation, duplicate detection, record merge, audit history | Field-level validation, duplicate detection, a merge workflow that preserves history. | High — personal data | L |
| `HR-12` | Employee export, retention and erasure tooling | Export per employee, a retention schedule, and erasure with legal hold. | Critical — personal or financial data, or an access control | XL |

## Recruitment and talent acquisition (`RC-`)

Accountable lane: **workforce-core**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `RC-01` | Requisitions, approvals and hiring budgets | A requisition with approval chain and a budget link. | Medium — internal detail | L |
| `RC-02` | Position and job description management | Positions with a versioned job description. | Low — non-sensitive | M |
| `RC-03` | Candidate profiles, applications, stages, talent pools | Candidate record, application with a stage machine, talent pools. | High — personal data | L |
| `RC-04` | Interview scheduling, interview kits, scorecards, feedback | Scheduled interviews with a kit, a scorecard and structured feedback. | Medium — internal detail | XL |
| `RC-05` | Offer approvals, templates, offer-to-hire transaction integrity | Offer with a template and version; acceptance and hire in one idempotent transaction. | High — personal data | M |
| `RC-06` | Candidate communications and career-site integration | Candidate notifications and a career site. | Medium — internal detail | L |
| `RC-07` | Funnel, source effectiveness, time-to-fill, conversion | Recruiting analytics from requisition to hire. | Low — non-sensitive | M |
| `RC-08` | Background-check and e-signature status | Status tracking only; the check is never performed unless an integration is configured. | High — personal data | S |

## Onboarding, mobility and offboarding (`OB-`)

Accountable lane: **workforce-core**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `OB-01` | Resumable onboarding and preboarding checklists | A checklist that survives a restart and can be resumed. | Medium — internal detail | M |
| `OB-02` | Employee information collection and document acknowledgements | Collect employee-supplied data and record acknowledgements. | High — personal data | M |
| `OB-03` | Equipment, access, training and manager-assignment tasks | Typed onboarding tasks with owners and due dates. | Medium — internal detail | M |
| `OB-04` | Probation tracking, confirmation and reminders | Probation period, confirmation decision, reminder. | Medium — internal detail | M |
| `OB-05` | Transfers, promotions, position changes, contract renewals | Internal mobility as an effective-dated change with approval. | Medium — internal detail | L |
| `OB-06` | Exit interviews, access revocation, asset returns, final settlement | Offboarding workflow with tasks, items, progress and completion. | High — personal data | L |
| `OB-07` | Rehire handling, dashboards, overdue-task escalation | Rehire path, completion dashboard, escalation for overdue tasks. | Medium — internal detail | M |

## Time and attendance (`TM-`)

Accountable lane: **workforce-core**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `TM-01` | Clock in/out, capture, breaks and timesheets | Clock events, manual entries, breaks, and a timesheet. | Medium — internal detail | M |
| `TM-02` | Attendance policies, missed-punch corrections | Configurable policy and a correction workflow with reason. | Medium — internal detail | M |
| `TM-03` | Cross-midnight shifts, overtime inputs, rounding, exceptions | Timezone-correct timestamps, cross-midnight handling, rounding rules, exception handling. | Medium — internal detail | L |
| `TM-04` | Shift-based and fixed-schedule attendance | Attendance driven by a shift template or a fixed schedule. | Medium — internal detail | L |
| `TM-05` | Timesheet lock after cut-off and adjustment records | Locked periods and recorded adjustments after lock. | Medium — internal detail | M |

## Leave (`LV-`)

Accountable lane: **workforce-core**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `LV-01` | Leave types, eligibility, accruals, carry-over, holidays | Types with jurisdiction/preset link, accrual schedules, carry-over, a holiday calendar. | Medium — internal detail | L |
| `LV-02` | Requests, approvals, cancellation, overlap checks, delegation | Request validation (balance, overlap, blackout, notice) and an approval chain. | Medium — internal detail | M |
| `LV-03` | Ledger-backed balance transactions and reconciliation | Every balance change is a signed ledger row; the balance is derived and reconcilable. | High — personal data | L |
| `LV-04` | Team availability and absence calendars | Team view of availability and absence. | Medium — internal detail | M |
| `LV-05` | Approved time and leave handoff to payroll | Approved leave reaches the pay run as an input. | Critical — personal or financial data, or an access control | M |

## Scheduling and workforce operations (`SC-`)

Accountable lane: **planning**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `SC-01` | Shift templates, open shifts, roster drafts and publishing | Shift templates, a draft roster and a separate publish action. | Medium — internal detail | L |
| `SC-02` | Demand-based staffing by location, role, skill and interval | Demand targets that drive the roster. | Medium — internal detail | L |
| `SC-03` | Availability, preferences, approved leave and eligibility | Inputs that make a person eligible for a shift. | Medium — internal detail | L |
| `SC-04` | Hard constraints: hours, rest, certifications, double-booking | Constraints that can never be relaxed. | High — personal data | XL |
| `SC-05` | Soft constraints: fairness, continuity, preferences, cost | Weighted preferences reported in the output. | Medium — internal detail | L |
| `SC-06` | Shift bidding, swaps and replacement workflows | Swap request, constraint re-check and authorised approval. | Medium — internal detail | M |
| `SC-07` | Coverage gaps, overstaffing and overtime alerts | Coverage per day/location/role with the gaps named. | Medium — internal detail | M |
| `SC-08` | Multi-location and project/site assignment | Assignment across sites and projects. | Medium — internal detail | L |
| `SC-09` | Schedule versioning, change history, employee notifications | Published versions with history and notifications. | Medium — internal detail | M |
| `SC-10` | Planned versus actual labour hours and cost | Planned hours against recorded hours, with cost. | Medium — internal detail | M |

## Payroll and compensation (`PY-`)

Accountable lane: **payroll-rules**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `PY-01` | Pay schedules, salary structures, pay components, effective-dated changes | Pay periods, profiles and components with effective dates. | Critical — personal or financial data, or an access control | M |
| `PY-02` | Earnings, deductions, allowances, incentives, benefit deductions | The component set a pay run is computed from. | Critical — personal or financial data, or an access control | L |
| `PY-03` | Approved time and leave inputs, adjustments, validation exceptions | The pay run consumes approved time and leave and reports exceptions. | Critical — personal or financial data, or an access control | M |
| `PY-04` | Dry run, approval, processing, reconciliation, payslips | The pay-run pipeline including a dry run that locks nothing. | Critical — personal or financial data, or an access control | L |
| `PY-05` | Historical pay records, controlled correction, audit history | Approved runs are immutable; corrections are off-cycle adjustments. | Critical — personal or financial data, or an access control | M |
| `PY-06` | Salary revisions, bonuses and total-compensation statements | Effective-dated salary change and a total-compensation statement. | Critical — personal or financial data, or an access control | M |
| `PY-07` | Bank export integration | A payment file for the customer's bank, where implemented and validated. | Critical — personal or financial data, or an access control | M |
| `PY-08` | Explicit currency and pay-period semantics | Every amount states its unit and its period; nothing is silently interpreted. | Critical — personal or financial data, or an access control | S |
| `PY-09` | Configurable jurisdictional rules with versioning and test fixtures | A rule-pack loader, an effective-date resolver, golden cases. | Critical — personal or financial data, or an access control | L |
| `PY-10` | Separation of generic calculation from verified statutory capability | Payroll refuses to run for a jurisdiction without a verified pack. | Critical — personal or financial data, or an access control | M |

## Benefits and employee services (`BN-`)

Accountable lane: **workforce-core**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `BN-01` | Benefit plans, eligibility, enrolment periods, dependants | Plans with eligibility rules, an enrolment window and dependants. | High — personal data | L |
| `BN-02` | Employer contributions, reimbursements and claim status | Contribution amounts, reimbursement claims and their status. | Critical — personal or financial data, or an access control | L |
| `BN-03` | Renewal reminders and benefit documentation | Renewal notices and the documents that back a benefit. | Medium — internal detail | M |
| `BN-04` | HR help requests, case assignment, SLA tracking and escalation | A case queue with assignment, SLA clock and escalation. | Low — non-sensitive | M |
| `BN-05` | Knowledge base, service history and employee self-service | Self-service articles and the employee's service history. | Low — non-sensitive | M |
| `BN-06` | Integration status for external administrators and providers | Status only where an integration exists. | High — personal data | S |

## Performance and talent (`PM-`)

Accountable lane: **workforce-core**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `PM-01` | Goals, OKRs, continuous feedback and one-to-ones | A goal hierarchy with feedback and one-to-one records. | Medium — internal detail | L |
| `PM-02` | Review cycles, self-assessments and manager reviews | A configured cycle with self and manager stages and a finalise action. | Medium — internal detail | L |
| `PM-03` | Competency frameworks, calibration and completion tracking | A competency model, a calibration session and completion metrics. | Medium — internal detail | XL |
| `PM-04` | Improvement plans, recognition and development objectives | Performance support and recognition records. | Medium — internal detail | L |
| `PM-05` | Succession plans, critical-role coverage and talent reviews | Succession and readiness for critical roles. | Medium — internal detail | L |
| `PM-06` | Promotion readiness and talent analytics with access controls | Readiness analytics, visible only to the roles that may see them. | High — personal data | L |

## Learning and skills (`LN-`)

Accountable lane: **workforce-core**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `LN-01` | Course catalogue, enrolments, assessments and learning paths | Courses with enrolment, assessment and a path. | Low — non-sensitive | L |
| `LN-02` | Mandatory training and compliance-related assignments | Rules that assign required learning and report completion. | Medium — internal detail | L |
| `LN-03` | Certifications, expiry tracking and renewal reminders | A certification record with expiry and a reminder. | Medium — internal detail | M |
| `LN-04` | Skills taxonomy, proficiency levels and employee-reviewed profiles | A skill vocabulary, a proficiency scale and a profile the employee can amend. | Medium — internal detail | L |
| `LN-05` | Skill gaps, role requirements, career paths and internal opportunities | Gap analysis against a role and the openings that match. | Medium — internal detail | XL |
| `LN-06` | Mentoring and development plans | Mentor pairing and a development plan. | Low — non-sensitive | L |
| `LN-07` | Learning completion and effectiveness analytics | Completion and effectiveness reporting. | Low — non-sensitive | M |

## Workforce analytics and planning (`AN-`)

Accountable lane: **planning**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `AN-01` | Headcount, hiring, turnover, absence and labour-cost metrics | The metric set, computed from the record. | Medium — internal detail | M |
| `AN-02` | Metric definitions, data lineage and governed drill-downs | A metric catalogue with its definition and a drill-down that respects scope. | Medium — internal detail | M |
| `AN-03` | Headcount and attrition projections | A projection from hires, exits, leave and requisitions. | Medium — internal detail | L |
| `AN-04` | Workforce demand and labour-cost forecasts | A demand forecast from history or drivers, with a cost variant. | Medium — internal detail | L |
| `AN-05` | Hiring plans, workforce budgets and staffing scenarios | Scenario comparison with visible assumptions. | Medium — internal detail | M |
| `AN-06` | Actual versus plan reconciliation | Planned against actual, with the variance explained. | Medium — internal detail | M |
| `AN-07` | Forecast accuracy, data quality, model version and confidence | Every forecast carries its method, window, error metrics, band, input hash and version. | Medium — internal detail | S |
| `AN-08` | Scheduled reporting, exports and permission-controlled dashboards | Reports as jobs, export formats, dashboards scoped by role. | Medium — internal detail | L |

## Employee and manager experience (`UX-`)

Accountable lane: **frontend-design**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `UX-01` | Role-based homepages and action-oriented dashboards | A home per role, driven by real queries. | Low — non-sensitive | M |
| `UX-02` | Personalised navigation and accessible global search | Navigation scoped to role and tenant; a search that is keyboard operable. | Low — non-sensitive | M |
| `UX-03` | Employee self-service for profile, documents, leave, time, payslips and requests | The employee's own records, writable where policy allows. | High — personal data | L |
| `UX-04` | Manager views for team availability, approvals, staffing and performance | The manager's team, its approvals and its staffing position. | Medium — internal detail | M |
| `UX-05` | Notification centre, reminders and configurable preferences | In-app notifications with preferences. | Low — non-sensitive | M |
| `UX-06` | Announcements, directory, org chart and help centre | Communication surfaces for employees. | Low — non-sensitive | M |
| `UX-07` | Saved views, filters, keyboard navigation and command palette | Repeatable views and full keyboard operation. | Low — non-sensitive | M |
| `UX-08` | Mobile and tablet workflows, responsive layouts, accessible interactions | The critical journeys at 360, 768, 1024 and 1440 px, keyboard and screen-reader operable. | Medium — internal detail | L |
| `UX-09` | Clear loading, empty, success, error and retry states | Every data view states what is happening and what to do next. | Low — non-sensitive | M |
| `UX-10` | A public contact form with an endpoint of its own | A visitor can send a message; it is rate limited, closed to every field but its own, and lands in a state visibly separate from the HR case queue. | Medium — a stranger's personal data | M |

## Tenant administration and platform operations (`AD-`)

Accountable lane: **platform-security**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `AD-01` | Tenant setup, branding, logos and accessible theme | Per-tenant brand with a contrast-checked theme. | Medium — internal detail | M |
| `AD-02` | Module entitlements, configurable navigation and terminology | Feature flags that decide what a tenant and a role may see. | Medium — internal detail | M |
| `AD-03` | Locale, timezone, currency, date formats and working week | Per-tenant localisation and time semantics. | High — personal data | L |
| `AD-04` | Role-based permissions, scoped authorisation and access reviews | Roles enforced on the server by the central policy module, with periodic review. | Critical — personal or financial data, or an access control | L |
| `AD-05` | Workflow and approval configuration with validation | Configurable approval chains and workflows. | Medium — internal detail | XL |
| `AD-06` | API credentials, webhooks and integration health | Credential issuance, webhook delivery and health. | Critical — personal or financial data, or an access control | L |
| `AD-07` | Audit trails, monitoring, background jobs and retry handling | An evidence-grade audit trail and reliable background work. | Critical — personal or financial data, or an access control | L |
| `AD-08` | Backup and restoration verification | A rehearsed restore, recorded. | Critical — personal or financial data, or an access control | L |
| `AD-09` | Data retention, export and erasure workflows | Retention schedules, subject export, erasure with legal hold. | Critical — personal or financial data, or an access control | XL |
| `AD-10` | Feature flags, release tracking and operational diagnostics | Flags that gate a module, plus diagnostics that say what is wrong. | Medium — internal detail | M |

## Industry presets and the configuration assistant (`CF-`)

Accountable lane: **onboarding-config**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `CF-01` | Versioned industry presets validated against the preset schema | Six presets as schema-validated configuration packages. | Medium — internal detail | L |
| `CF-02` | Recommended modules and dependencies | A dependency graph enforced server-side. | Medium — internal detail | M |
| `CF-03` | Workforce and organisation templates, departments, job families and roles | Suggested structures a customer can accept or change. | Low — non-sensitive | M |
| `CF-04` | Shift templates and working patterns | Working patterns per industry. | Low — non-sensitive | M |
| `CF-05` | Leave types and configurable accrual parameters | Leave configuration per industry. | Medium — internal detail | M |
| `CF-06` | Dashboards, KPIs and action queues per preset | The views a tenant starts with. | Low — non-sensitive | M |
| `CF-07` | Forecast drivers and the data needed to use them | What the forecast needs, per industry. | Low — non-sensitive | S |
| `CF-08` | Employee-import templates per preset | Which import templates apply. | Low — non-sensitive | S |
| `CF-09` | Setup validations, warnings and incomplete-configuration checks | A readiness check that names what is missing. | Medium — internal detail | M |
| `CF-10` | Explicit exclusions and jurisdiction-specific items for review | What a preset does not decide, and why. | High — personal data | S |
| `CF-11` | Ten-step onboarding journey with resumable progress | Company profile → preset → modules → org → import → roles → review → commit, resumable. | Medium — internal detail | XL |
| `CF-12` | Configuration assistant: gap detection, explanation, prefilled form | A rule engine that explains a gap and opens a prefilled form. | Medium — internal detail | L |
| `CF-13` | Curated help index with no free-text generation | Fixed answers from a curated index. | Low — non-sensitive | S |
| `CF-14` | Track which values came from defaults and which the customer changed | Default-versus-override provenance on every setting. | Low — non-sensitive | M |

## CSV import (`IM-`)

Accountable lane: **data-import**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `IM-01` | Downloadable templates for departments, locations, jobs, employees, leave balances and shift templates | A template per entity that the importer accepts unchanged. | High — personal data | S |
| `IM-02` | Exact header matching with documented aliases; unknown headers rejected | Aliases are documented; an unknown header is refused and named. | High — personal data | S |
| `IM-03` | Streaming UTF-8 parse with row and size limits | 10,000 rows and 5 MB per file, enforced. | Medium — internal detail | M |
| `IM-04` | Validation of types, required fields, ISO 8601 dates, enums, references, duplicates and salary bounds | Every malformed row is refused with a reason. | High — personal data | S |
| `IM-05` | Formula-injection neutralisation for =, +, -, @, tab and CR | Injected formulas are neutralised in the stored value. | Critical — personal or financial data, or an access control | S |
| `IM-06` | Dry run with counts, row-error CSV, and a confirmation token bound to the result hash | The preview is exactly what the commit does, and the token cannot be forged. | High — personal data | L |
| `IM-07` | Idempotent upsert on natural keys; a re-import changes nothing | The same file twice creates nothing the second time. | High — personal data | M |
| `IM-08` | Background execution for large files | Long imports run as a job with a status. | Medium — internal detail | M |
| `IM-09` | Progress, cancellation where safe, and failure recovery | The operator sees progress and can recover. | Medium — internal detail | M |
| `IM-10` | Retention and deletion of uploaded files | Uploaded files are deleted on a schedule. | High — personal data | M |
| `IM-11` | Masked personal values in error reports and logs | An error names the row and the column, never the value. | Critical — personal or financial data, or an access control | S |
| `IM-12` | Salary units defined explicitly — never silently annual | Every amount states its unit and period. | Critical — personal or financial data, or an access control | S |

## AI capability and governance (`AI-`)

Accountable lane: **platform-security**.

| ID | Capability | Target behaviour | Sensitivity | Effort |
|---|---|---|---|---|
| `AI-01` | Tier A — HR policy search with citations | Answers from documents the caller may read, each with its source. | High — personal data | L |
| `AI-02` | Tier A — Document classification and field extraction with human verification | A draft extraction a human accepts or corrects. | High — personal data | XL |
| `AI-03` | Tier A — Drafting job descriptions, communications and help responses | A draft the user edits. | Medium — internal detail | M |
| `AI-04` | Tier A — Summarising authorised HR cases and approved reports | A summary of a record the caller may read. | High — personal data | M |
| `AI-05` | Tier A — Configuration-gap explanations and curated product help | The assistant explains a gap in plain language. | Medium — internal detail | M |
| `AI-06` | Tier B — Forecast explanation and scenario comparison | Why the forecast looks as it does. | Medium — internal detail | L |
| `AI-07` | Tier B — Schedule recommendations and coverage explanations | Why a shift is unfilled. | Medium — internal detail | L |
| `AI-08` | Tier B — Skills-gap and learning recommendations | A recommendation with its basis. | Medium — internal detail | L |
| `AI-09` | Tier B — Workforce cost and attrition analysis | An analysis the reader can follow. | Medium — internal detail | L |
| `AI-10` | Tier B — Payroll exception explanations from verified calculation inputs | An explanation built only from inputs the calculation used. | Critical — personal or financial data, or an access control | M |
| `AI-11` | Tier C — Prepare a draft change, check permissions, show impact, request approval, execute through authorised services, record the action | A controlled workflow assistant that never acts on its own authority. | Critical — personal or financial data, or an access control | XL |
| `AI-12` | Mandatory AI controls: permission-aware retrieval, no PII in prompts, no training on customer data, input/output validation, injection defence, tool allowlists, human approval for consequential actions, traceability, evaluation datasets, hallucination/leakage/bypass tests, graceful degradation, generated-content labelling, kill switch | Every control in mandate §7 implemented and tested. | Critical — personal or financial data, or an access control | XL |
| `AI-13` | Prohibitions: no autonomous candidate rejection, eligibility determination, termination decision or compensation change | A policy and a test that proves the prohibition. | Critical — personal or financial data, or an access control | M |
