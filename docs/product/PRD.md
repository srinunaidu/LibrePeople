> Status: Approved by product owner as the requirements baseline on 21 November 2026. Items in section 29 remain open decisions.

LIBREPEOPLE

COMPLETE PRODUCT REQUIREMENTS DOCUMENT

People. Time. Pay. Connected.

Version 1.0 — Review Draft

21 November 2026

India-first | Open-source | Customer-controlled deployment

Existing codebase: Karmathy

## Contents

Update this table in Word to generate the table of contents.

## Document control

Document: LibrePeople — Complete Product Requirements Document (PRD)

Version: 1.0 — Review draft | Status: Product-owner review required | Date: 21 November 2026

Product name: LibrePeople (working name; trademark, company-name and domain clearance are not represented as complete).

Existing codebase: Karmathy. The existing codebase is the starting point, not the product specification. The product requirements in this document govern the target state.

Audience: Product owner, engineering agents, architects, QA, security reviewers, payroll specialists, implementation partners and contributors.

## How to use this PRD

This is the product-level source of truth for scope, user outcomes, product principles and acceptance criteria. The Technical Requirements Document (TRD) defines implementation choices. Where the TRD conflicts with this PRD, record the conflict and obtain product-owner approval; do not silently reinterpret either document.

Every requirement has a stable ID. Engineering must maintain a traceability register linking each requirement to its domain, UI, API, data model, tests, documentation, release status and evidence.

A requirement is not complete because a screen, endpoint, model, menu item or placeholder exists. It is complete only when the end-to-end user outcome works, permission boundaries are enforced, errors are handled, audit events are recorded where required, tests pass and documentation matches the behaviour.

This PRD defines the target product. It does not assert that all listed capabilities currently exist in Karmathy. The supplied authoritative technical audit describes the known baseline and must be used to plan remediation.

## 1. Executive summary

LibrePeople is intended to be a complete, India-first, open-source Human Capital Management (HCM) platform for organisations typically employing 10–500 people. It should be practical for small and mid-sized organisations while retaining the controls and reliability required for real HR operations and payroll.

The deployment model is customer-controlled and independent: each customer installs and operates its own instance on infrastructure it owns or controls. Git is the authoritative source of code. Customers obtain a versioned release, configure their installation, import their data, create administrators, invite employees and begin operations.

The product is not a vendor-hosted infrastructure service. The customer is responsible for infrastructure operation unless they separately contract an implementation or managed service provider. The product must not require a central LibrePeople service to function.

The product should make ordinary implementation decisions through sensible defaults, templates, guided setup and validated imports. Customers should not need to engage developers for normal configuration. Customer-specific needs should be met through supported configuration and extension points, not permanent code forks.

The target experience is: Git/release → deploy → configure → import and validate data → create administrator → invite employees → employee self-service → operational use. A 2–4 hour onboarding target applies only to a prepared customer with clean data and suitable infrastructure; it is a goal to validate, not a guaranteed service level.

## 2. Product vision, mission and motto

Vision: Make dependable, complete and adaptable workforce management software accessible to organisations without forcing them into vendor lock-in or complex enterprise implementation.

Mission: Deliver an open, portable and maintainable HCM platform that brings people operations, workforce time and payroll together while preserving customer control over software, infrastructure and data.

Product motto: “People. Time. Pay. Connected.”

Operating principle: Open by design. Simple to adopt. Reliable to operate.

The motto is a product decision and should inform navigation, module architecture, onboarding, product messaging and prioritisation. It does not mean that the product is limited to three modules; it describes the central connected workforce lifecycle.

## 3. Product principles and decision rules

Complete production product, not an MVP or a collection of disconnected modules.

One authoritative upstream repository and one supported codebase; no customer-specific source forks as the normal customization model.

Independent customer installations with independent application, database, configuration, secrets, documents and backups.

Modular monolith; avoid microservices and distributed complexity unless evidence demonstrates a need.

Configuration before custom code: company settings, policy templates, fields, salary components, workflows, roles and branding must be configurable within safe boundaries.

Sensible defaults and guided setup; optional capabilities must not block a basic HR/payroll go-live.

Security, privacy, payroll accuracy, auditability and statutory correctness cannot be traded for convenience.

Portable deployment: Docker-based customer installation remains supported regardless of any optional cloud deployment target.

No mandatory dependency on Render, Oracle Cloud, Cloudflare, a central identity service or proprietary vendor service.

No fake functionality, hard-coded success states, demo metrics in production, placeholder actions or unverified compliance claims.

Do not silently assume legal rules, customer policy, data residency, licence ownership or infrastructure capacity. Record decisions and obtain approval where necessary.

## 4. Target market, scope and boundaries

Primary market: India. The product should support Indian employment, payroll and statutory workflows, including jurisdiction- and state-sensitive rules where applicable.

Primary organisation size: approximately 10–500 employees. The product should not impose artificial architectural limits at this size and should be designed so future scale can be assessed through measured performance testing.

Organisation types: office-based businesses, professional services, retail, manufacturing, field workforces and shift-based operations. The data model and workflows must not assume all employees work a fixed Monday–Friday office schedule.

Primary deployment: one independently operated installation per customer. One installation may contain multiple legal entities, locations, departments and employee populations.

Out of scope as mandatory product dependencies: vendor-hosted SaaS control plane, central multi-tenant hosting, paid third-party integration for basic HR operations, microservices, AI features required for core workflows, and customer-specific code branches.

Optional future capabilities may include multi-country localisation, native mobile applications, advanced workforce optimisation and AI-assisted insights. These must not displace core reliability.

### 4.1 Product scope at a glance

| Domain | Required product outcome |
|---|---|
| Core HR & organisation | Trusted employee and organisation records, lifecycle history and controlled access. |
| Recruitment & lifecycle | Requisition-to-hire, onboarding, employee changes and controlled offboarding. |
| Time, attendance & leave | Accurate schedules, punches, timesheets, leave ledgers, approvals and payroll inputs. |
| Payroll & compensation | Reproducible payroll calculations, approvals, payments, payslips and reconciliation. |
| India compliance & tax | Versioned statutory rules, tax declarations, calculations, registers and filing-ready outputs. |
| ESS & manager self-service | Employees and managers complete routine transactions without HR intervention. |
| Talent, benefits & expenses | Recruitment, performance, learning, benefits and expense workflows. |
| Documents, reports & administration | Secure records, actionable reporting, configuration, audit and integrations. |

## 5. Users, roles and access model

The product must support configurable roles and permissions, not rely solely on fixed role names. Default role templates should cover Super Administrator, HR Administrator, Payroll Administrator, Finance, Manager, Employee, Recruiter, Auditor and read-only/reporting users.

A person may hold more than one role where authorised. Privileged role assignment must be tightly controlled and audited. HR users must not be able to grant themselves or others unrestricted platform administrator privileges.

Authorisation must be enforced server-side for every API and data operation. Hiding a UI control is not an access-control mechanism.

Employee-level scope is mandatory: an employee may access only their own records unless a separately authorised role or relationship grants access. Manager access must be restricted to permitted reporting lines or teams. HR access must be scoped according to configured legal entity, location or assigned responsibility where appropriate.

Sensitive fields require field-level permissions and masking. Salary, PAN, Aadhaar or other national identifiers, bank details, tax data, date of birth, medical or other sensitive records must not appear in general list endpoints or reports by default.

Privileged actions require re-authentication or additional verification where appropriate, mandatory MFA for privileged roles, audit events and separation-of-duties controls.

### 5.1 Core personas

| Persona | Primary needs | Typical permissions |
|---|---|---|
| Employee | View own information, apply for leave, attendance corrections, payslips, declarations and requests. | Own records and explicitly permitted self-service changes. |
| Manager | Review team information, approve requests, manage attendance and performance. | Assigned team and approval scope. |
| HR administrator | Maintain people data, lifecycle, policies and HR operations. | Assigned HR scope; no automatic platform-superadmin rights. |
| Payroll administrator | Prepare payroll, resolve exceptions and produce payroll outputs. | Payroll data and processing; maker-checker restrictions apply. |
| Finance administrator | Review payroll liabilities, payment outputs and reconciliation. | Financial outputs and approved payroll information. |
| System administrator | Operate installation, security, backups, integrations and system configuration. | Platform administration; business access only when separately granted. |
| Auditor | Review authorised records, approvals, changes and evidence. | Read-only, explicitly scoped and logged. |

## 6. Functional requirements — Core HR and organisation

LP-CORE-001: Maintain employee profiles with identity, contact, employment, job, organisation, compensation reference and emergency-contact information.

LP-CORE-002: Maintain employee identifiers, employment status, joining date, confirmation date, probation, notice period and separation dates.

LP-CORE-003: Maintain legal entities, business units, departments, teams, locations, cost centres, positions, designations, grades and reporting relationships.

LP-CORE-004: Support employee history for changes to role, manager, department, location, legal entity, grade and employment status.

LP-CORE-005: Support configurable employee fields with data types, validation, visibility, access rules and import/export mapping.

LP-CORE-006: Support employee search, filters, saved views, bulk actions and permission-aware exports.

LP-CORE-007: Support employee document metadata, secure attachments, expiry dates, acknowledgement and retention rules.

LP-CORE-008: Prevent invalid state transitions and preserve historical records needed for payroll, audit and statutory purposes.

LP-CORE-009: Provide controlled employee data correction workflows with before/after audit evidence.

LP-CORE-010: Support multiple legal entities and locations within one customer installation.

## 7. Functional requirements — Recruitment and hiring

LP-REC-001: Create position requisitions with headcount, role, location, budget, hiring manager and approval path.

LP-REC-002: Maintain candidate profiles, source, stage, communications, notes and attachments with appropriate privacy controls.

LP-REC-003: Configure hiring stages and interview rounds, schedule interviews and capture structured feedback.

LP-REC-004: Create offers using approved templates and configurable compensation components.

LP-REC-005: Route offers through approval and record acceptance, rejection, expiry and revisions.

LP-REC-006: Convert an accepted candidate into an employee without duplicate data entry and with an auditable transaction.

LP-REC-007: Restrict candidate personal data to authorised recruiters and hiring participants; apply retention controls.

## 8. Functional requirements — Onboarding and offboarding

LP-LIFE-001: Create onboarding plans by role, location, legal entity or employment type using reusable templates.

LP-LIFE-002: Collect documents, acknowledgements, policy acceptance, personal details and required declarations.

LP-LIFE-003: Assign tasks to HR, manager, IT, finance and employee with owners, due dates and status.

LP-LIFE-004: Track probation, confirmation, mandatory documents and onboarding completion.

LP-LIFE-005: Support resignation, termination, retirement and other separation reasons with approval and effective dates.

LP-LIFE-006: Track notice period, handover, asset recovery, access revocation, outstanding advances, leave and attendance reconciliation.

LP-LIFE-007: Generate full-and-final settlement inputs and link them to payroll.

LP-LIFE-008: Block completion where mandatory exit tasks or approvals remain unresolved, except through an authorised, reasoned override that is audited.

LP-LIFE-009: Preserve employment, payroll and statutory history after separation according to retention policy.

## 9. Functional requirements — Time, attendance and scheduling

LP-TIME-001: Support manual, web and approved integration-based attendance capture.

LP-TIME-002: Support shifts, shift patterns, rotations, split shifts where configured, weekly offs, holidays and location-specific calendars.

LP-TIME-003: Record punches, breaks, missing punches, late arrivals, early departures, overtime and attendance exceptions.

LP-TIME-004: Support employee correction requests and manager/HR approval with before/after values and reasons.

LP-TIME-005: Support attendance locking after approval or payroll cutoff and controlled reopening with audit trail.

LP-TIME-006: Support timesheets, project/task allocation where enabled, submission, approval and payroll/billing export.

LP-TIME-007: Support biometric and third-party attendance integration through documented adapters; core operation must remain usable without them.

LP-TIME-008: Support mobile-responsive attendance. Location capture, geofencing or device restrictions must be optional, transparent and policy-controlled.

LP-TIME-009: Define rules for overtime, breaks, grace periods, rounding, night shifts and cross-midnight shifts through configuration and jurisdiction-aware policy.

LP-TIME-010: Reconcile approved attendance and overtime into payroll using traceable inputs.

## 10. Functional requirements — Leave management

LP-LEAVE-001: Configure multiple leave types, eligibility, accrual, opening balance, carry-forward, expiry, encashment and negative-balance rules.

LP-LEAVE-002: Support applicable leave categories and company-specific policies without assuming one national policy applies to every state or employer.

LP-LEAVE-003: Maintain a transaction ledger for accruals, grants, usage, adjustments, encashment and reversals.

LP-LEAVE-004: Validate eligibility, date ranges, holidays, weekly offs, overlaps, balance and notice requirements.

LP-LEAVE-005: Support configurable multi-level approval, delegation, escalation and cancellation.

LP-LEAVE-006: Preserve policy version and calculation evidence for historical balances.

LP-LEAVE-007: Integrate approved leave and unpaid leave with attendance and payroll.

LP-LEAVE-008: Provide employee and manager views of balances, calendars, team availability and request status.

## 11. Functional requirements — Payroll and compensation

Payroll is a critical financial control system. It must be implemented and tested as a deterministic calculation engine. A payslip must be the result of an approved calculation, not a document populated with caller-supplied amounts.

LP-PAY-001: Configure salary structures with earnings, deductions, employer contributions, reimbursements, benefits and informational components.

LP-PAY-002: Support CTC, gross salary, fixed/variable pay, effective-dated revisions and employee-specific structures.

LP-PAY-003: Calculate joiner/leaver proration, unpaid leave, attendance impact, overtime, arrears, retroactive revisions and one-time payments.

LP-PAY-004: Support bonus, incentives, reimbursements, loans, advances, deductions, recoveries, salary holds and adjustments.

LP-PAY-005: Support payroll periods, cutoffs, pre-payroll validation, exception queues, preview, approval, locking and controlled reopening.

LP-PAY-006: Enforce maker-checker and segregation of duties. A user must not approve their own payroll run where policy requires independent approval.

LP-PAY-007: Preserve every calculation input, formula/rule version, result, adjustment, approver and timestamp.

LP-PAY-008: Use decimal-safe arithmetic and explicit rounding rules. No binary floating-point arithmetic for money.

LP-PAY-009: Generate payslips only from locked/approved payroll results and preserve historical payslip versions.

LP-PAY-010: Generate bank payment files in documented formats with validation, approval and reconciliation; formats must be configurable or adapter-based.

LP-PAY-011: Support payroll reversal/correction through controlled adjustment runs; never silently edit paid payroll history.

LP-PAY-012: Reconcile gross-to-net, employer cost, statutory liabilities, deductions, payment totals and ledger/export totals.

LP-PAY-013: Support multi-entity payroll calendars and employee transfers between entities with effective-date handling.

LP-PAY-014: Provide payroll exception reports and explainable calculation breakdowns for each employee.

LP-PAY-015: Prevent unauthorised access to salary structures, payroll inputs, payslips and bank details.

## 12. Functional requirements — Indian tax and statutory compliance

LibrePeople must provide an India-focused, versioned compliance capability. Statutory rates, thresholds, exemptions, applicability and filing specifications change. The product must not embed unverified assumptions or claim legal compliance merely because a calculation is implemented.

LP-COMP-001: Provide an effective-dated rule-pack mechanism with jurisdiction, legal source, applicability, effective dates, calculation method, version and reviewer status.

LP-COMP-002: Support applicable EPF, EPS and EDLI calculations and outputs, subject to verified applicability and current rules.

LP-COMP-003: Support applicable ESI calculations and outputs, subject to verified applicability and current rules.

LP-COMP-004: Support state-specific Professional Tax and Labour Welfare Fund rules where applicable.

LP-COMP-005: Support gratuity and bonus calculations according to verified applicability and rules.

LP-COMP-006: Support salary TDS, employee tax declarations, proofs, projections, regime selection where applicable, tax adjustments and Form 16-related outputs.

LP-COMP-007: Support statutory registers, challan/payment reconciliation, filing-ready reports and export formats where specifications are available and verified.

LP-COMP-008: Maintain a compliance calendar with due dates, responsibilities, status and evidence.

LP-COMP-009: Store calculation-level traceability to the exact rule-pack version used.

LP-COMP-010: Provide a statutory test suite with boundary, effective-date, rounding, eligibility and regression cases reviewed by a qualified Indian payroll/compliance specialist.

LP-COMP-011: Clearly label unsupported jurisdictions, unverified rules and filing steps requiring external portal submission or professional review.

LP-COMP-012: Do not automatically submit to government portals unless a documented, authorised and supported integration exists.

## 13. Functional requirements — Employee and manager self-service

LP-ESS-001: Provide secure employee access to own profile, permitted profile updates, documents, attendance, leave, payslips and requests.

LP-ESS-002: Allow leave, attendance correction, expense, HR request and tax declaration submissions according to configured policy.

LP-ESS-003: Provide status tracking, notifications and history for employee-submitted requests.

LP-ESS-004: Provide managers with team views and approval queues limited to their authorised scope.

LP-ESS-005: Support responsive browser access on mobile devices; native apps are not a prerequisite for the initial supported product.

LP-ESS-006: Protect sensitive information through field-level access, masking and secure document delivery.

## 14. Functional requirements — Benefits, performance and learning

LP-TAL-001: Configure benefit plans, eligibility, enrolment windows, dependants, contributions, claims and approvals.

LP-TAL-002: Configure performance cycles, goals, competencies, self-assessments, manager assessments, peer feedback and review outcomes.

LP-TAL-003: Support calibration and compensation recommendations with restricted access and audit history.

LP-TAL-004: Maintain learning catalogue, courses, assignments, enrolments, mandatory training, completion and certificates.

LP-TAL-005: Support reminders and expiry tracking for mandatory training and qualifications.

LP-TAL-006: Ensure optional talent features can be disabled or left unused without blocking Core HR, attendance or payroll.

## 15. Functional requirements — Expenses and HR service delivery

LP-EXP-001: Configure expense categories, limits, policies, currencies where needed, receipts and submission rules.

LP-EXP-002: Support travel requests, expense claims, multi-level approvals, rejection reasons and reimbursement status.

LP-EXP-003: Integrate approved reimbursements with payroll or payment exports according to company policy.

LP-SVC-001: Provide HR request/case categories, priorities, assignment, comments, attachments, due dates, status and resolution.

LP-SVC-002: Support SLA measurement and escalation as configurable capabilities.

LP-SVC-003: Restrict cases and attachments to authorised participants and preserve audit history.

## 16. Functional requirements — Documents, notifications and integrations

LP-DOC-001: Store documents privately; public, guessable file URLs are prohibited.

LP-DOC-002: Support categories, metadata, versions, expiry, acknowledgements, access logs, retention and secure download.

LP-DOC-003: Support configurable local/object storage backends without changing business logic.

LP-NOT-001: Provide an in-app notification centre and event-driven notifications for key HR and payroll events.

LP-NOT-002: Provide configurable email delivery through replaceable providers; basic product use must not depend on a single email vendor.

LP-NOT-003: Support notification preferences, retries, delivery status and failure visibility.

LP-INT-001: Provide documented, versioned REST APIs and an OpenAPI contract.

LP-INT-002: Provide webhooks with signatures, retries, event identifiers and replay protection.

LP-INT-003: Provide integration adapters for biometric systems, banks, accounting and other systems as justified by documented use cases.

LP-INT-004: Protect outbound URL fetching against SSRF and restrict credentials and network access.

LP-INT-005: Keep third-party integrations optional and provide import/export alternatives where practical.

## 17. Functional requirements — Reporting and administration

LP-REP-001: Provide headcount, joiner/leaver, attrition, attendance, leave, overtime, payroll, salary cost, expense, recruitment and training reports.

LP-REP-002: Provide filters by legal entity, location, department, cost centre, employee type and date range, subject to permissions.

LP-REP-003: Provide CSV/XLSX exports with formula-injection protection and sensitive-field masking.

LP-REP-004: Distinguish actual data from illustrative/demo data; production dashboards must never display fabricated metrics.

LP-ADM-001: Provide company setup, branding, legal entity, location, master data, roles, permissions, workflow and notification configuration.

LP-ADM-002: Provide feature settings that actually gate relevant navigation and API capability; hiding a menu alone is insufficient.

LP-ADM-003: Provide system health and diagnostics without exposing secrets or unauthorised operational details.

LP-ADM-004: Provide configuration export/import and schema validation to support repeatable customer setup.

LP-ADM-005: Provide administrator-visible upgrade status, backup status and actionable operational warnings.

## 18. Configuration and customer-specific adaptation

The product must support variation between customers without requiring the implementation team to modify core source code for normal HR policies.

Configurable areas include branding, legal entities, locations, departments, designations, employee custom fields, salary components, pay structures, leave policies, attendance rules, shifts, holidays, approval workflows, roles, notifications, document types and enabled modules.

Configuration must have schema validation, versioning, audit history, import/export, safe defaults and documented upgrade compatibility.

Configuration must not be able to disable security boundaries, audit controls, statutory calculation safeguards or required data integrity.

Advanced customers may use documented APIs, webhooks and extension points. Extensions must be isolated from core release upgrades and must not require a permanent fork.

Provide a configuration compatibility report during upgrades. If a setting is deprecated or changed, explain the impact and provide a migration path.

## 19. Import, migration and data portability

LP-DATA-001: Provide downloadable, documented templates for employees, organisation masters, salary structures, opening balances and other supported imports.

LP-DATA-002: Validate file type, size, encoding, columns, data types, mandatory values, duplicates and references before import.

LP-DATA-003: Provide row-level preview and error reporting, with safe retry of failed rows and idempotency controls.

LP-DATA-004: Never partially import a file without clearly reporting committed and rejected records and the transaction model.

LP-DATA-005: Provide exports of customer data in documented, machine-readable formats, subject to permissions.

LP-DATA-006: Provide database and document backup/restore procedures and a documented exit path from the product.

LP-DATA-007: Preserve relationships and audit metadata where possible during migration; identify non-migratable items explicitly.

## 20. Installation, deployment and release experience

The product must be independently deployable on customer-owned infrastructure. The supported reference deployment should use Docker Compose, PostgreSQL, application services, a durable worker, reverse proxy, persistent document storage and health checks.

The installation path should validate prerequisites, create secure secrets, configure the database, apply migrations, create the first administrator, configure domain/TLS and run health checks. No default production password or development server may be used.

Each customer installation is independent. There is no central runtime dependency on LibrePeople or the original Karmathy hosting environment.

Git is the source of truth, but production deployments should consume tagged, versioned and verified releases or immutable images—not an unpinned moving main branch.

A customer may choose manual upgrades or an explicitly enabled automated update process. Automated updates must check release compatibility, create/verify backups, apply migrations, run health checks and provide recovery instructions.

The product must support local development and acceptance testing before any cloud deployment. Cloudflare is a possible deployment target to assess separately; it is not a mandatory runtime dependency or an approved assumption.

Cloudflare compatibility must be demonstrated for the actual backend, database access, background jobs, file storage and runtime constraints before recommending it as the production platform. Docker portability remains mandatory.

## 21. Non-functional requirements

LP-NFR-001 Availability: define deployment-level availability objectives and failure modes; do not promise an SLA without operational evidence.

LP-NFR-002 Performance: common HR pages and transactions must be responsive under representative 100-employee workloads; establish measurable budgets and test them.

LP-NFR-003 Scalability: support the target 10–500 employee range with documented sizing guidance and measured load-test results.

LP-NFR-004 Security: secure-by-default authentication, authorisation, secrets, encryption, storage, logging and container configuration.

LP-NFR-005 Privacy: data minimisation, purpose limitation, access controls, retention, export and applicable data-principal workflows.

LP-NFR-006 Reliability: transactions, idempotency, retries, durable background jobs and visible failure handling.

LP-NFR-007 Maintainability: modular monolith boundaries, typed interfaces, code quality gates and documented architecture decisions.

LP-NFR-008 Portability: supported Docker deployment and no hard dependency on one cloud provider.

LP-NFR-009 Accessibility: keyboard access, labels, focus management, contrast and clear validation; target WCAG 2.2 AA where feasible and verify.

LP-NFR-010 Observability: structured logs, metrics/health, job status, backup status and diagnostics with sensitive-data redaction.

LP-NFR-011 Recoverability: documented RPO/RTO targets per deployment profile, automated backups and tested restoration.

LP-NFR-012 Compatibility: supported browser matrix and documented upgrade compatibility policy.

LP-NFR-013 Internationalisation readiness: externalise user-facing strings, support time zones, locale-aware dates/numbers and currency-safe formatting.

LP-NFR-014 Data integrity: preserve financial, employment, approval and audit history with database constraints and transaction rules.

## 22. Privacy, legal and compliance governance

The product must provide controls that help customers meet applicable privacy and employment obligations, but the software must not represent itself as guaranteeing legal compliance. Applicability depends on the customer's facts, jurisdiction, current law and implementation.

Include configurable privacy notices/acknowledgements where required, access logging, data export, correction workflows, retention schedules, deletion/erasure workflows where lawful, and controls for restricted data.

Avoid collecting Aadhaar or other sensitive identifiers unless there is a defined, lawful and necessary purpose. Provide masking and restricted access for any such fields.

Statutory rule packs must cite their source, effective date and verification status. Changes must be reviewed by an identified qualified specialist before release as verified production rules.

Maintain a legal/compliance release checklist for India and state-specific requirements. Do not silently infer the effect or commencement of labour legislation.

## 23. Audit, approvals and financial control

LP-AUD-001: Record actor, action, target, timestamp, request/correlation ID and relevant before/after values for sensitive and material changes.

LP-AUD-002: Protect audit records against ordinary application-level alteration and document the tamper-evidence model.

LP-AUD-003: Record authentication, privilege changes, sensitive data access, exports, payroll approvals, payroll locks, configuration changes and document access.

LP-AUD-004: Support approval delegation and escalation without losing original approver identity or decision history.

LP-AUD-005: Enforce segregation of duties for payroll and other high-risk financial operations.

LP-AUD-006: Provide read-only audit views and exports with strict permission controls.

## 24. Acceptance criteria and definition of done

A requirement is accepted only when its user outcome can be demonstrated in a clean local installation using documented steps and representative test data.

For each functional requirement, acceptance evidence must include: UI or API path, business rules, role/permission tests, validation and error handling, data persistence, audit events where required, automated tests, user documentation and traceability entry.

Critical workflows must be tested end-to-end, not only with unit tests. Payroll and statutory calculations additionally require independently reviewed golden test cases and reproducible calculation evidence.

Security acceptance requires all known critical and high findings from the authoritative audit to be closed or explicitly risk-accepted by the product owner with documented compensating controls. No unresolved critical issue may be labelled production-ready.

Installation acceptance requires a clean Docker deployment, fresh PostgreSQL migration, secure administrator bootstrap, health checks and documented backup/restore.

Upgrade acceptance requires upgrade testing from each supported prior release, configuration compatibility checks, backup verification and recovery procedure.

Release acceptance requires CI to pass, production frontend build, dependency/security checks, database migration tests, end-to-end tests and documented release notes.

### 24.1 Product-level release gates

| Gate | Required evidence | Release status if absent |
|---|---|---|
| Security | Critical/high audit findings closed; access-control and sensitive-data tests pass. | BLOCKED |
| Payroll | Golden test cases independently reviewed; end-to-end payroll and reconciliation pass. | BLOCKED |
| Statutory | Rule source, effective date, applicability and specialist verification recorded. | Unverified capability; cannot claim verified compliance |
| Database | Fresh install and supported upgrade migrations pass; constraints and backups verified. | BLOCKED |
| Operations | Install, health checks, backup, restore and recovery demonstrated. | BLOCKED |
| Product workflows | Core HR, lifecycle, time, leave, payroll and ESS E2E tests pass. | BLOCKED |
| Open source | Copyright ownership, licence and third-party licence review approved. | Public release blocked |
| Release | Versioned artifacts, release notes, CI evidence and rollback guidance available. | BLOCKED |

## 25. Known baseline from the authoritative Karmathy audit

The supplied audit describes the existing system as a modular monolith with a FastAPI backend, React/TypeScript frontend, 27 routers, 267 API endpoints, 84 model classes and approximately 85 database tables. It reports Oracle Autonomous Database and Render hosting in the audited configuration.

The audit identifies reusable foundations including the authentication core, RBAC patterns, audit call pattern, import pipeline, ledger-based leave design, Decimal rules module, frontend design system and test scaffolding.

The audit identifies critical or high-priority issues including privilege escalation to SuperAdmin, weak diagnostics authentication, employee-scope failures for sensitive data, public file access, missing MFA enforcement, lockout/rate-limit weaknesses, horizontal access-control gaps, insecure token storage, encryption-key coupling, ungated deployment, plaintext sensitive fields, incomplete audit tamper evidence and missing licence.

The audit reports that payroll is broken end-to-end: leave, timesheets and overtime are not integrated; caller-supplied payslip amounts are possible; the Paid state is unreachable; and the available rule pack is draft. TDS is not implemented. Some compliance checks are hard-coded. Multi-tenancy is not implemented. Oracle-specific code is spread across multiple files. Database migration history requires re-baselining.

These findings are the remediation baseline, not a substitute for a fresh inspection of the current canonical repository. Engineering must verify each finding against the checked-out code and record whether it is confirmed, fixed, not reproduced or superseded.

### 25.1 Mandatory audit-to-PRD remediation mapping

| Audit finding | PRD requirement / outcome | Priority |
|---|---|---|
| HR can create/promote SuperAdmins | Role governance, LP-CORE access model, LP-NFR-004, LP-AUD-003 | P0 |
| Diagnostics accept arbitrary auth string | LP-ADM-003; authenticated and safe diagnostics | P0 |
| Associate can overwrite bank/tax fields | LP-ESS-001, LP-NFR-004; field-level and employee-scope controls | P0 |
| Public /files mount | LP-DOC-001 to 003; private object/document access | P0 |
| Horizontal access gaps | Section 5 access model; all LP-ESS and module permissions | P0 |
| MFA not enforced; lockout/XFF flaws | LP-NFR-004; secure authentication and trusted proxy handling | P0 |
| Payroll engine broken | LP-PAY-001 to 015 | P0/P1 |
| TDS absent; compliance hard-coded | LP-COMP-001 to 012 | P1 |
| No real multi-tenancy | Independent customer deployment model; no shared SaaS tenancy required | Architecture decision |
| Plaintext sensitive fields/key coupling | LP-NFR-004; privacy and encryption requirements | P0/P1 |
| Audit not tamper-evident | LP-AUD-001 to 006 | P1 |
| Oracle lock-in and migration baseline issues | PostgreSQL standard; reproducible migrations | P1 |
| No licence / dependency review | Section 26 open-source governance | Release blocker |
| Local storage and deployment hardening gaps | Sections 20, 21 and 24 | P1 |

## 26. Open-source, intellectual property and licensing

The product owner must confirm ownership and authority to license the existing Karmathy code before a public LibrePeople release.

Evaluate an OSI-approved licence, with Apache-2.0 as a candidate rather than an assumed decision. Review every direct and transitive dependency licence, notices, fonts, assets, templates and bundled tools.

The existing audit notes a potential LGPL-3.0 dependency review item for fpdf2. Verify the actual dependency version and usage before deciding how to distribute it.

Prepare LICENSE, NOTICE where required, CONTRIBUTING, SECURITY disclosure instructions, code of conduct if desired, release policy and vulnerability reporting process only after owner approval.

Do not publish secrets, customer data, production identifiers, private keys, environment files or internal operational material.

## 27. Product analytics and success measures

Measure product quality without collecting unnecessary employee personal data. Prefer aggregate, opt-in operational telemetry; self-hosted customers must be able to disable outbound telemetry.

Adoption: time from clean deployment to first administrator login, first employee import, first invitation and first completed HR workflow.

Implementation simplicity: number of mandatory setup steps, number of manual corrections after import, configuration errors and time to resolve them.

Reliability: failed jobs, failed imports, migration failures, backup success, restore success and application error rate.

Payroll integrity: calculation reproducibility, reconciliation variance, correction/reversal frequency and verified test coverage.

Security: unresolved findings by severity, access-control regression results, sensitive-data exposure tests and dependency vulnerabilities.

Usability: task completion rate for common employee, manager and HR tasks; support requests attributable to confusing workflows.

Performance: response time and resource use under documented representative 100- and 500-employee scenarios.

## 28. Required engineering traceability and agent operating contract

The engineering agent must treat this PRD as a binding requirements baseline and the authoritative Karmathy audit as the baseline for existing-code remediation.

Before implementation, create docs/product/PRD.md containing this approved PRD and docs/product/requirements-traceability.csv (or equivalent machine-readable register). Do not paraphrase away requirement IDs or acceptance criteria.

For every PRD requirement ID, record: requirement text, product domain, priority, current baseline status, implementation decision, affected UI routes/components, API endpoints, database entities/migrations, permission model, automated test IDs, documentation references, evidence and final status.

Every pull request or implementation batch must identify the PRD IDs it addresses. Every feature must map back to the product motto: People, Time, Pay, Connected. If it does not support a defined user outcome, it must be justified as a platform/security/operational necessity or excluded.

No requirement may be marked COMPLETE solely because code was written. Completion requires passing tests and demonstrable acceptance evidence.

Use statuses: NOT STARTED, IN PROGRESS, BLOCKED, IMPLEMENTED, TESTED, VERIFIED, DEFERRED BY APPROVAL, NOT APPLICABLE. Distinguish IMPLEMENTED from VERIFIED.

If a requirement is ambiguous, record the ambiguity and propose a decision. Do not silently invent product policy, statutory logic, customer behaviour or legal interpretation.

If a requirement cannot be completed due to external verification, credentials or product-owner approval, mark it BLOCKED, document the exact dependency and continue with independent work.

Do not deploy to Cloudflare or any production cloud environment until the product owner explicitly approves the tested local release and deployment plan.

Do not force-push, overwrite main, delete tags, modify production data or commit secrets.

## 29. Product-owner decisions still requiring explicit approval

Canonical repository and GitHub remote: confirm the exact repository and branch that are authoritative.

Brand/legal clearance: LibrePeople is the working product name; confirm trademark, domain and entity checks before public branding.

Copyright and licence: confirm ownership and approve the open-source licence.

Payroll/compliance verifier: identify the qualified Indian payroll/statutory specialist who approves rule packs and golden test cases.

Data migration: identify whether any live customer data must be migrated and approve the migration/rollback plan.

Data residency: define whether customer data and compute must remain in India by contractual or product policy.

Supported deployment environments: approve the initial tested Linux/Docker/PostgreSQL support matrix.

Cloudflare target: approve a specific architecture only after compatibility, cost, background processing, database and storage tests.

Native mobile applications: responsive web ESS is the baseline; native Android/iOS requires a separate prioritised decision.

Customer-specific extensions: approve the policy for third-party extensions and compatibility support.

## 30. Final product acceptance statement

LibrePeople is ready for a production release only when a real customer can deploy it independently from a documented release, configure the organisation without code changes, import and validate employee data, create administrators, invite employees, run the connected HR/time/pay workflows, process payroll with independently verified calculations, access the required statutory outputs, operate ESS, back up and restore the installation, and upgrade safely.

The product must remain customer-controlled, portable and maintainable from one upstream codebase.

The product motto is the final test of coherence: People. Time. Pay. Connected. A capability is not complete if its data, approvals, controls or downstream effects are disconnected from the relevant end-to-end workflow.
