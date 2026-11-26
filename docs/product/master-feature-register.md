# LibrePeople — Master Feature Register (UX rebuild baseline)

Base: main HEAD `f3ee5cf` · branch `agent/ux/master-register` · date 2026-11-26.
Scope: full product-surface inventory for the UX rebuild. No code changed.

Sources (read-only): `frontend/src/App.tsx` (routes + role gates),
`frontend/src/pages/**` (183 files), `frontend/src/components/**` (+ `features/`, 70 files),
`frontend/src/lib/api.ts` (380 lines), `backend/app/api/v1/api.py` + `endpoints/*.py`
(36 routers), `rule_packs/` (in-standard, in-standard-fy2627-skeleton, demo-synthetic-draft),
`docs/product/PRD.md` (§§1–30), `docs/product/requirements-traceability.csv` (136 rows,
statuses VERIFIED 104 / IMPLEMENTED 3 / IN PROGRESS 3 / BLOCKED 18 / DEFERRED 8 —
system of record; see staleness note), `docs/feature-completion-matrix.md`,
`docs/product/acceptance-status.md` (2026-11-24: 2 VERIFIED / 105 IMPLEMENTED —
STALE, superseded by 2026-11-26 CSV promotion of 102 rows), gap register
`docs/programme/phase2-domain-gap-register.md` (gaps #3–#23), `docs/release/e2e-report.md`
(desktop 100 + responsive 16), `docs/cloud-e2e-report.md` (Round 3: 25/25 live),
`docs/release/release-notes-and-known-limitations.md`.

UX classification used below: **IN SCOPE** (in PRD scope, rendered + wired, tests pass) ·
**INCOMPLETE** (in scope, code partial / proof missing) · **DEFECTIVE** (in scope, failing
suite or broken path) · **REDUNDANT** (duplicate surface, requirement-level) ·
**OUT OF SCOPE** (owner-deferred, preserved in backlog) · **OWNER DECISION REQUIRED**
(external dependency: statutory sign-off, infra/tooling, owner approval).
Requirement-level REDUNDANT = 0; route-level redundancy is listed in §5 (alias routes).

## 1. Summary counts

| UX class | Count | IDs |
|---|---:|---|
| IN SCOPE | 101 | all VERIFIED except the 3 DEFECTIVE rows |
| INCOMPLETE | 6 | TIME-008/009/010 (IMPLEMENTED, ortools unproven) + NFR-009/010/011 (IN PROGRESS) |
| DEFECTIVE | 3 | AUD-005, AUD-006 (admin-audit route-mount FAIL `got []`); DATA-001 (import QueuePool FAIL) |
| REDUNDANT (requirement-level) | 0 | route-level dupes in §5, not requirement dupes |
| OUT OF SCOPE | 8 | EXP-001/002/003, SVC-001/002/003, NOT-001/003 (DEFERRED) |
| OWNER DECISION REQUIRED | 18 | PAY-001…015 (FY26-27 sign-off), DOC-003 (storage), NFR-012/013 (residency/deploy) |
| **Total** | **136** | reconciles to traceability CSV |

Staleness flags: (a) `acceptance-status.md` (2/105/3/18/8) predates the 2026-11-26
promotion to 104 VERIFIED — CSV governs. (b) Matrix marks EXP-001/002/003 IMPLEMENTED
with live cloud-E2E (R4 2pass/1skip + R5 associate PASS, `acb7a24` UI slice 18/18 tests,
navfix `7d4ab08`) ahead of the CSV, which still records them DEFERRED — kept OUT OF
SCOPE here with reclassification pending owner scope approval. (c) Matrix per-row
Acceptance cells for the 102 promoted rows still carry pre-promotion PARTIAL text.

Audit roll-ups: pages audited 183 files (~180 screens: ~102 admin incl. tests,
~30 core/ESS/payroll/leave/expenses, 19 marketing, rest shared/tabs/tests);
dead-control hits 332 (`disabled`/TODO/noop/`not wired`) across 99 admin files;
raw `<button>/<table>/<dialog>` bypassing the UI kit in 19 files;
fake/placeholder-data hits (`Math.random`/dummy/sample/lorem) in 7 files
(`Import.tsx`, `ProjectStatus.tsx`, `ManagerAssignments.tsx`, `JurisdictionRules.tsx`,
`AnnouncementsDirectory.tsx`, `DesignGallery.tsx`, `ProductMockup.tsx`).
Backend suites: 76 `*_test_suite.py` files. Frontend: 811/811 (15 files) per release notes.

## 2. Register — auth, admin, audit (ADM/AUD)

| ID | Feature | UX class | Roles | Routes + screens | Backend API | DB | Actual behavior / defects | Tests |
|---|---|---|---|---|---|---|---|---|
| LP-ADM-001 | Login (password + JWT) | IN SCOPE | public | `/login` → `Login.tsx`; App.tsx:186 | `auth.py:169 POST /login` | `user.py` + 0002/0003/0009 cred+MFA | Rendered + wired; cloud E2E 6/6 sign-in/out R3 | lp_phase2_access 86 ✓, mfa 17 ✓, security 2073 ✓, e2e PASS |
| LP-ADM-002 | Self-registration | IN SCOPE | public | `/login` (register tab) `Login.tsx` | `auth.py:260 POST /register` | `user.py` | Rendered + wired; break-glass dep noted | access 86 ✓, security 2073 ✓ |
| LP-ADM-003 | MFA enrol/verify | IN SCOPE | auth | `/mfa` `Mfa.tsx`; App.tsx:249 | `auth.py:446 POST /mfa/enroll` | `user.py` + 0003 | Rendered + wired; local E2E MFA enroll/confirm PASS | mfa 17 ✓, e2e PASS |
| LP-ADM-004 | Break-glass grant | IN SCOPE | SuperAdmin only | `/admin/break-glass` `BreakGlass.tsx`; App.tsx:397 | `break_glass.py:130 POST grant` | `user.py` | Rendered + wired; SuperAdmin gate enforced | access 86 ✓ |
| LP-ADM-005 | Admin status/health | IN SCOPE | SuperAdmin, HR | `/admin/project-status` `ProjectStatus.tsx` | `admin_status.py` | tenant settings read | Rendered + wired; restore side is read-only theatre (gap#4) — defect carried, not reclassed | admin_status 32 ✓ |
| LP-AUD-001…004 | Audit verify + audit report | IN SCOPE (×4) | SuperAdmin, HR | `Reports.tsx` (audit report) + `HistoricalRecord.tsx` | `admin_audit.py:84 GET /verify`; `reports.py:63 GET /audit` | `audit.py:18 logs`, `:66 chain_head` + 0021/0022 | Rendered + wired | audit 29 ✓ + chain 58 ✓ |
| LP-AUD-005/006 | Admin audit API surface | DEFECTIVE (×2) | SuperAdmin, HR | same as above | `admin_audit.py:84` | `audit.py` + 0022 | Suite FAIL: route mounted at contract path `got []` (D-01 test_assets dead helper) | admin_audit FAIL |

## 3. Register — people, org, lifecycle (CORE/LIFE/DOC/ESS/NOT/SVC)

| ID | Feature | UX class | Roles | Routes + screens | Backend API | DB | Actual behavior / defects | Tests |
|---|---|---|---|---|---|---|---|---|
| LP-CORE-001…005 | Employee list/create/read/patch/history | IN SCOPE (×5) | auth (mgmt ops HR) | `/people*` (6 routes) `People.tsx`; App.tsx:207-212,285 | `employees.py:181/270/381/565/609` | `employee.py:66` + 0026 history | Rendered + wired; cloud E2E employee-create + directory PASS | employees 64 ✓, history 85 ✓, e2e PASS |
| LP-CORE-006/007/008/009 | Locations / legal entities / positions / departments | IN SCOPE (×4) | auth | `People.tsx` tabs + `/admin/departments-cost-centres` | `core_hr.py:89/267/341`, `departments.py` | master-data tables | Rendered + wired | legal_entity 49 ✓, master_data 35 ✓ |
| LP-CORE-010 | Client onboarding (tenant setup) | IN SCOPE | SuperAdmin, HR | `/client-onboarding` `ClientOnboarding.tsx` | `client_onboarding.py` router | clients | Rendered + wired | onboarding suite ✓ |
| LP-LIFE-001…009 | Benefits plans/enrol/life-events/LOA+approve | IN SCOPE (×9) | auth | `/platform/benefits` `BenefitsHub.tsx` | `benefits.py:27–103` | benefits models | Rendered + wired; vendor/insurance/flex-wallet absent (gap#21, missing piece not blocker) | endpoint suite absent; engine math covered |
| LP-DOC-001/002 | Employee documents list/create | IN SCOPE (×2) | auth | via `People.tsx` / ESS | `core_hr.py:452/462` | doc tables | Rendered + wired | suite ✓ |
| LP-DOC-003 | Document version upload | OWNER DECISION | auth | no standalone UI (gap#10) | `core_hr.py:507` | — | BLOCKED: storage backend undecided (local ephemeral vs OCI) | N/A |
| LP-ESS-001/002/006 | ESS profile + employee files | IN SCOPE (×3) | self (ownership-enforced) | `/ess` `ESSHub.tsx`; `/admin/essprofile` | `ess_hr.py:56/67/192` | ess/hr tables | IDOR fixed `5cf0568`; selector constrained | ESS 51/51 ✓, security 2162/0 |
| LP-ESS-003/004/005 | Notifications list/unread/create | IN SCOPE (×3) | auth | `ESSHub.tsx` | `ess_hr.py:100/110/163` | notifications | Rendered + wired | notification suites ✓ |
| LP-NOT-002 | Unread-count badge | IN SCOPE | auth | `ESSHub.tsx` / TopBar | `ess_hr.py:110` | notifications | Rendered + wired | suite ✓ |
| LP-NOT-001/003 | Notification publish surface | OUT OF SCOPE (×2) | — | surplus surface only | `ess_hr.py:100/163` | notifications | DEFERRED by owner mandate; code preserved | N/A |
| LP-SVC-001/002/003 | Helpdesk cases list/create/comment | OUT OF SCOPE (×3) | ADMIN-only today | `/admin/hrhelp-cases` `HRHelpCases.tsx` | `core_hr.py:812/840/888` | `core_hr.py:253` hr_cases + 0041 attachments | DEFERRED; known defect: POST /cases ADMIN-only, employee self-create missing (gap#3); suite 30/30 | hr_helpdesk 30 ✓ (code proof, not scope) |

## 4. Register — hiring, time, leave, pay (REC/TIME/LEAVE/PAY/TAL/REP/COMP/INT/DATA/NFR/EXP)

| ID | Feature | UX class | Roles | Routes + screens | Backend API | DB | Actual behavior / defects | Tests |
|---|---|---|---|---|---|---|---|---|
| LP-REC-001…005 | Candidates/requisitions/jobs/offers/hire-from-offer | IN SCOPE (×5) | auth | `/recruiting` `Recruiting.tsx`; `/jobs` `Jobs.tsx`; `/admin/candidate-stages`, `requisition-stages`, `offer-approvals`, `funnel-analytics` | `candidates.py:19`, `requisitions.py:23`, `jobs.py:73`, `offers.py:44/175` | recruiting + job_queue + 0004/0024/0025 | Rendered + wired; only VERIFIED pair per old doc (REC-006/007) but all 7 VERIFIED in CSV | hire 26 ✓, jobs 24 ✓, cross-tenant 31 ✓, e2e PASS (hire path) |
| LP-REC-006/007 | Onboarding summary + presets | IN SCOPE (×2) | auth | `/onboarding` + `/onboarding-config` `OnboardingConfig.tsx` | `onboarding.py:123/255` | onboarding | Rendered + wired; only rows VERIFIED under both old+new counts | harness full-green `c5f5d89` |
| LP-TIME-001…007 | Clock in/out, entries CRUD, timesheets generate | IN SCOPE (×7) | auth | `/time` `TimeAttendance.tsx`; `/admin/timesheets`, `timesheet-lock`, `attendance-policies`, `shift-based-attendance`, `cross-midnight-overtime` | `time_attendance.py:44–216` | time_attendance + 0016/0035 | Rendered + wired | time_corrections 63 ✓, e2e PASS |
| LP-TIME-008/009/010 | Roster generate / availability | INCOMPLETE (×3) | auth | `/scheduling` `Scheduling.tsx`; `/scheduling/roster` `RosterBuilder.tsx` | `scheduling.py:161/203/259` | scheduling + 0016 | Code present; solver raises `RuntimeError: ortools is not available` (`solver.py:73`) — unproven in default env | scheduling suite PASS only where ortools present (`2d27af4`) |
| LP-LEAVE-001…008 | Types/balances/ledger/recon/payroll-input/requests/approve | IN SCOPE (×8) | auth | `/leave`, `/leave/ledger`, `/leave/ledger/:employeeId`; `/admin/leave-types`, `leave-to-payroll` | `leave.py:81–340` | leave tables | Rendered + wired; accrual/carry-over/encashment automation absent (gap#18, manual entitlements only) | leave suites ✓ |
| LP-PAY-001…015 | Periods/components/profiles/runs/create/approve/gates/filings/register/TDS/PF/PT/24Q/ECR | OWNER DECISION (×15) | SuperAdmin, HR | `/platform/payroll*` `PayrollOverview/PayRuns/PayRunDetail/PayrollSetup.tsx`; `/admin/pay-schedule`, `bank-export*`, `earnings-deductions`, `employer-contributions`, `salary-revisions` | `payroll.py:76–544`, `filings.py:55/108/187/267`, `reports.py:476/487/638` | rule_packs | Mechanics render; FY25-26 pack `verified`, FY26-27 `pending_verification`; 409 `rule_pack_not_verified` gate enforced (`payroll.py:536/544`); gratuity OFF; NO pay run VERIFIED without statutory sign-off | india_payroll 114 ✓ (math), acceptance withheld |
| LP-TAL-001…004 | Goals + reviews CRUD | IN SCOPE (×4) | auth | `/platform/performance` `PerformanceHub.tsx`; `/admin/goals-okr`, `pm02goals`, `competency-calibration`, `improvement-plans`, `promotion-readiness`, `succession-planning` | `performance.py:44–87` | performance + learning DDL | Rendered + wired; no dedicated endpoint suite; cycles/360/calibration are shims (gap#19) | talent 45 ✓ |
| LP-TAL-005/006 | Courses + enrolments | IN SCOPE (×2) | auth | `/platform/learning` `LearningHub.tsx`; `/admin/learning-paths`, `learning-analytics`, `training-assignments`, `skill-taxonomy`, `skill-gaps`, `certifications`, `mentoring-development` | `learning.py:38/53` | learning DDL | Rendered + wired; SCORM/assessments/certificates absent (gap#20); several admin screens flag-shims | talent 45 ✓ |
| LP-REP-001…004 | Dashboard/headcount/labor-cost/audit reports | IN SCOPE (×4) | auth | `/reports` `Reports.tsx` | `reports.py:21/30/46/63` | read-only aggregates | Rendered + wired; scheduling/saved-views/PDF-Excel absent (gap#12, `SavedViews.tsx` shim) | reports_slice 37 ✓, metrics 41 ✓ |
| LP-COMP-001…012 | Compliance rules/violations/plans/scenarios/report-defs | IN SCOPE (×12) | SuperAdmin, HR | `/platform/compliance` `Compliance.tsx`; `/admin/compliance` `ComplianceCenter.tsx` | `compliance.py:38–132` | compliance models | Rendered + wired; no dedicated endpoint suite; vendor/insurance/wallet absent (gap#21) | engine-math covered |
| LP-INT-001/002 | SSO/SCIM/webhooks platform | IN SCOPE (×2) | SuperAdmin, HR | `/platform/integrations` + `/admin/integrations-hub`, `integration-credentials`, `external-integration` | `integrations_platform.py` | sso/scim_token model | Rendered; SCIMToken model has no endpoints (gap#11) | suite ✓ (model-level) |
| LP-INT-003/004/005 | Import-backed integrations | IN SCOPE (×3) | SuperAdmin, HR | `/import` `Import.tsx`; `/data-quality` `DataQuality.tsx` | `import_export.py:290` | imports + 0007/0029 | Rendered + wired | data_quality 44 ✓, migration 67 ✓, retention ✓ |
| LP-DATA-001 | CSV import | DEFECTIVE | SuperAdmin, HR | `/import` `Import.tsx` | `import_export.py:290 POST /import/{entity}` | `imports.py:56` + 0007 | FAIL: `import_test_suite` QueuePool exhaustion | suite FAIL |
| LP-DATA-002…007 | Templates/dry-run/data-quality/export | IN SCOPE (×6) | SuperAdmin, HR | `/import` + `/admin/data-quality` `DataQuality.tsx` | `import_export.py:183/240/379`, `data_quality.py` | imports + 0007/0029 | Rendered + wired | data_quality 44 ✓, migration 67 ✓ |
| LP-NFR-001…008/014 | Security headers, error envelope, RBAC, audit chain | IN SCOPE (×9) | cross-cutting | all screens (`ProtectedRoute.tsx` 403 gate; `api.ts` interceptors) | cross-cutting `auth.py`, `errors.py` | — | Enforced; NFR-014 text mentions unapproved target but CSV=VERIFIED | security 2073/2162 ✓ |
| LP-NFR-009/010/011 | Perf/load/backup-restore/E2E proof | INCOMPLETE (×3) | — | `/admin/backup-restore` read-only (gap#4) | `admin_status.py:39` read | tenant settings | No restore endpoint/drill; pg/pg_dump evidence unavailable | N/A (proof missing) |
| LP-NFR-012/013 | Data residency / deploy matrix / Cloudflare target | OWNER DECISION (×2) | — | — | — | — | PRD §29 approvals outstanding; `docs/product/postgresql-migration.md` pending | N/A |
| LP-EXP-001/002/003 | Expense categories/claims/create (+approve/pay UI slice) | OUT OF SCOPE (×3) | auth (slice) | `/expenses`, `/expenses/new`, `/expenses/:id` (`Expenses/ExpenseNew/ExpenseDetail/shared`, `acb7a24`); App.tsx:401-403 | `expenses.py:126/206/223` (+16 routes) | 0037 expenses | CSV=DEFERRED but UI slice exists 18/18 tests + cloud E2E R4/R5 PASS — reclassification pending owner scope sign-off; approvals hardcoded (gap#6) | expenses 78 ✓ + slice 18/18 ✓, e2e PASS |

## 5. Navigation map (what each role sees)

- **Public (unauthenticated):** `/` Homepage + marketing cluster (`/platform`, `/platform/compliance`,
  `/solutions`, `/industries`, `/industries/:slug`, `/resources`, `/pricing`, `/security`,
  `/faq`, `/compare/:competitor`, `/about`, `/careers`, `/contact`, `/privacy`, `/terms`,
  `/docs`, `/ai`) + `/login`. Marketing pages share `marketing/ModulePage/PageHero` kit.
- **Any authenticated role** (`ProtectedRoute`, no `roles`): `/dashboard` (role-specific home:
  `SuperAdminHome/HRHome/ManagerHome/AssociateHome/PayrollHome`), `/people*` (6 routes),
  `/recruiting`, `/onboarding`, `/time`, `/scheduling`, `/scheduling/roster`, `/leave*`,
  `/onboarding-config`, `/offboarding`, `/assets`, `/my-assets`, `/reports`,
  `/client-onboarding`, `/platform/payroll*`, `/platform/performance|benefits|learning`,
  `/ess`, `/forecasting*` (incl. `/runs/:runId`), `/project-status`, `/theme`,
  `/design-gallery`, `/data-quality`, `/import`, `/jobs`, `/mfa`, `/expenses*`,
  plus tenant-mirrored `/t/:slug/*` (same 30 screens via `TenantLayout` + `useTenantNav`).
- **SuperAdmin + HR only** (`roles=["SuperAdmin","HR"]`, 403 otherwise per
  `ProtectedRoute.tsx:22-38`): all `/admin/*` (~130 routes): user/branding/entitlements/
  workflow/integrations/backup/flags/locale/retention + ~95 domain screens + 14 marketing
  site-page editors (`/admin/solutions…/compare`) + 18 short-code aliases
  (`/admin/rc-03→CandidateStages`, `ad-03→LocaleConfig`, `ad-09→RetentionExport`,
  `hr-01→People`, `hr-05`, `lv-01`, `rc-05`, `sc-04/07/10`, `tm-02/03/04/05`, `an-06`,
  `bn-02`, `ai-02/03/04`, `ob-04`) — REDUNDANT at route level (same component, two paths).
- **SuperAdmin only:** `/admin/break-glass` (App.tsx:397).
- **Feature flags:** per-client flags `GET/PUT /onboarding-portal/clients/{id}/feature-flags`
  (`api.ts:listFeatureFlags/updateFeatureFlag`); admin UI `/admin/feature-flags`
  (`FeatureFlags.tsx`); consumed in `SuperAdminHome.tsx`, `WorkspaceRail.tsx`,
  `FunnelAnalytics.tsx`, `StatesDiscipline.tsx`, `TenStepJourney.tsx`,
  `DocumentClassification.tsx`, `types/index.ts`. No global `useFlag` hook — per-page reads.

## 6. Design-system inventory, patterns, inconsistencies

Primitives (`components/ui/`): `button`, `inputs`, `card`, `table`, `data-table`,
`dialog`, `modal`, `tabs`, `badge`, `status-pill`, `kpi-card`, `sparkline`,
`progress-ring`, `avatar`, `breadcrumb`, `accordion`, `popover`, `dropdown-menu`,
`tooltip`, `sonner`/`toast`, `skeleton`, `page-skeleton`, `layout`, `error-box`,
`bulk-bar`, `feedback`, `RetryableAlert`, `PendingVerificationAlert`, `ErrorBoundary`,
`mobile-bottom-nav`, `shift-swap-table`, `shift-template-table`. Page kit imported by
~88 admin screens (`WorkflowApproval.tsx:10` et al.): `Alert, Button, EmptyState,
LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton`.
Shell: `WorkspaceRail` (single nav, collapsible Admin console), `TopBar`,
`CommandPalette`, `TenantSwitcher`, `SecondarySidebar`, `ThemeToggle`, `ShortcutHelp`.
Role homes: `home/SuperAdminHome/HRHome/ManagerHome/AssociateHome/PayrollHome/
NeedsAction/NextBestActionCards/DashboardFallback`. Marketing kit:
`marketing/ModulePage/PageHero/ProductMockup/Artwork/Thread/ShimmerSkeleton`.

Conflicting patterns (file refs):
1. Buttons: kit `ui/button.tsx` vs barrel `components/ui.tsx` vs raw `<button>` in
   19 admin files — triple pattern; standardise on kit Button.
2. Modals: `ui/modal.tsx` AND `ui/dialog.tsx` coexist — pick one.
3. Tables: `ui/table.tsx` vs `ui/data-table.tsx` vs `shift-swap-table.tsx` vs
   `shift-template-table.tsx` — four patterns for grids.
4. Admin screens: ~88 use the PageHeader/SectionCard kit; the remainder hand-roll
   headers/cards — audit and migrate.
5. Fake-data pockets (7 files, §1) must be replaced with empty-states/skeletons
   before visual QA: notably `ProjectStatus.tsx`, `Import.tsx`, marketing
   `ProductMockup.tsx` (acceptable as illustration, must never ship as product UI).
6. `disabled` attributes in 99 admin files (332 dead-control hits) — many are
   flag-shim screens (gap#14–20: ContingentWorkers, ProbationTracking, RehireHandling,
   ExitInterviews, InterviewScheduling, SkillGaps, SavedViews, StatesDiscipline);
   each needs either wiring or honest empty-state gating.

## 7. Backlog cross-references

- Traceability CSV (system of record) → matrix `docs/feature-completion-matrix.md`
  (reconciliation note: 104+3 EXP vs 8 DEFERRED) → `acceptance-status.md` (STALE).
- Gaps #3 (helpdesk self-create), #4 (backup/restore theatre), #5 (PAY sign-off),
  #6 (workflow engine), #7 (expenses UI decision), #8 (filing persistence), #9 (ER
  module), #10 (documents UI + storage DOC-003), #11 (SCIM), #12 (scheduled
  reports), #13 (assets lifecycle), #14–#20 (shims), #21 (benefits vendors),
  #22 (demand-plan lifecycle), #23 (residency/scheduler) — all in
  `docs/programme/phase2-domain-gap-register.md`.
- PRD §29 owner decisions (§4 PAY/NFR rows + repo/brand/licence/migration/native-mobile).
- E2E: `docs/release/e2e-report.md`, `docs/cloud-e2e-report.md`,
  `docs/validation/e2e-scenarios.md`, `known-limitations.md`.
- Rule packs: `backend/rule_packs/in-standard.json` (v1.0.0 verified, FY25-26 frozen),
  `in-standard-fy2627-skeleton.json` (pending_verification), `demo-synthetic-draft.json`.
