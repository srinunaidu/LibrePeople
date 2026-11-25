# E-UX-02 — Admin console honest-feedback slice 2

> Worktree: `/Users/srinivas/LLM/Workforce/lp-slice2-admin` · Branch: `slice2-admin-feedback` · Base: `9dd0bfb`
> Scope: `frontend/src/pages/admin/*.tsx` except `UserAdmin.tsx` (slice-1 frozen),
> `frontend/src/lib/bulk-admin.ts` (new), `frontend/src/lib/feedback-slice2.test.ts` (new), this doc.
> Zero of the 16 E-UX-01 frozen files touched (verified: `git diff --name-only` ∩ frozen list = ∅).

## What changed (101 admin pages)

### 1. Honest Alert feedback (slice-1 pattern, all pages)
- Every `toast.success` / `toast.error` (181 + 2 occurrences) replaced with
  `<Alert tone="success">` (role=status) / `<Alert tone="error">` (role=alert)
  rendered from `notice` / `actionError` state. Sonner imports removed.
- Mutation failures feed a dedicated `actionError` channel via
  `errorMessage(e, …)` (raw backend detail); the load-failure `error` /
  `RetryableAlert` channel is reserved for reads (slice-1 Platform contract).
- Success notices are set **after** `await load()` so the load reset cannot
  wipe them; unverified "— audit row (AD-07) written" claims stripped from all
  success messages (the UI cannot confirm audit writes from the response).
- `alert()` fake-success buttons removed (ExitInterviews, InterviewScheduling).

### 2. API-enforced authz reflected in UI
Backend gates verified by reading `client_onboarding.py`, `admin_jobs.py`,
`ess_hr.py`, `payroll.py`, `deps.py`:
- `GET/PUT /clients/:id/settings`, `GET/PUT /clients/:id/feature-flags`,
  `/clients/:id/integrations*`, `/clients/:id/onboarding*` →
  `require_roles("SuperAdmin")`. The ~90 config pages previously claimed
  `["SuperAdmin","HR"]` write access and let HR hit guaranteed 403s on load.
  Now: `canWrite = user?.role === "SuperAdmin"`, load skipped for other roles,
  and a permission-denied `EmptyState` ("Not visible for your role") renders.
- Kept `ADMIN_ROLES` (SuperAdmin+HR) where the backend allows it: OrgChart
  rebuild (`ess_hr.py`), retention job ledgers + retry/discard (`admin_jobs.py`),
  BankExport payment-file (`payroll.py`), DataQuality, ComplianceCenter,
  IntegrationsHub checks/e-signatures (already correctly gated).
- Route-level `ProtectedRoute roles` in `App.tsx` still admits HR (App.tsx is
  outside this slice's exclusive set) — the page-level gate reflects the API.
  **For architect:** consider tightening admin route roles in a later slice.

### 3. Dead endpoints / fake actions removed or rewired (design gaps for architect)
| Page | Former action | Problem | Resolution |
|---|---|---|---|
| CandidateStages, RequisitionStages, TenStepJourney | `POST …/onboarding/steps/advance\|reset` | endpoint does not exist | persist stage/pool/journey config via real `PUT …/feature-flags/{key}` |
| ExportErasure | `POST /admin/jobs/erasure-trigger` | endpoint does not exist | real `POST /admin/jobs/{id}/retry\|discard` actions + confirm step |
| ExitInterviews | `alert('Erasure job triggered…')` | no API call at all | removed; ledger + Refresh |
| BankExport | `POST /admin/bank/export` | endpoint does not exist | card removed; real payment-file download kept |
| InterviewScheduling | `alert('Interview scheduled…')` | no API call at all | real `PUT …/feature-flags/interview_type` |
| WorkflowApproval | `GET …/onboarding/steps` (404), create payload `{name, required_approval, status}` (422 vs schema) | wrong endpoint + schema | `GET …/onboarding` → `steps[]`; create `{key,title,owner,order_index}` per `OnboardingStepCreate`; real `POST …/steps/{id}/complete` action; swallowed `catch {}` + `console.log` removed |
| AnnouncementsDirectory | hardcoded seed array; `POST {announcements:[…]}` to flags collection; "New announcement/Content..." placeholder | fabricated data + invalid write | real form (title/content), persists JSON in `announcements` feature flag; empty state |
| PolicySearch | "Search policies" only saved a query; "Citation results" never populated | no search endpoint exists | honest config page: save default policy query; fake results card removed |
| HistoricalRecord | random `REC-…` id; note discarded on save ("retained locally" was false) | fabricated id + no persistence | operator-entered record id + note persisted via settings keys |
| IntegrationCredentials | created rows with `endpoint: "https://placeholder"` | placeholder data | optional real endpoint input; nothing fabricated sent |
| ManagerAssignments | hardcoded "John Doe/Jane Smith…" manager options; department select not persisted | fabricated people + dead control | options from `listEmployees()`; department persisted (`default_manager_department`) |
| SavedViews | claimed `g d`/`g m`/`g p→Profile` shortcuts; view/keyboard controls not editable | wrong shortcut claims + dead form | list mirrors `WorkspaceRail.GOTO_AREAS` + `lib/keyboard.ts`; editable select + checkbox persisted |
| LearningPaths, TrainingAssignments | "Enroll" sets a tenant-wide flag | misleading verb | relabelled "Save enrollment flag", editable checkbox, honest notice |
| TemplatesDraftsPublish, DemandStaffing | "Publish template" saves a default setting | misleading verb | relabelled "Save default template" |

**Backend gaps reported, not fixed (out of scope):** no erasure-trigger, no
`/admin/bank/export`, no policy-search, no PY-05 historical-record endpoint.

### 4. Fabricated activity/metrics removed (35 cards)
Static tables presenting invented records (names, dates, counts, statuses)
were deleted; pages keep their real config + real ledgers. Removed cards:
AttendancePolicies "Missed punches", BankExportIntegration "Export history",
CompetencyCalibration "Competency matrix", CoverageGaps "Coverage gaps",
CrossMidnightOvertime "Overtime summary", DemandForecasting "Forecast summary"
(invented 2%/3% growth projections), DocumentClassification "results",
EarningsDeductions "summary", EmployerContributions "Claims summary",
EquipmentAccess "assignments", ExternalIntegration "Integration status",
ForecastException "exceptions", FunnelAnalytics "Funnel metrics",
HardConstraints "violations", HiringPlans "scenarios", ImprovementPlans
"Active improvement plans", InformationCollection "Collection items",
JurisdictionRules "Jurisdiction rules" (replaced by the **persisted** config
row), LeaveToPayroll "mapping", MentoringDevelopment "Mentorship pairs",
ModelVersioning "Model accuracy", OfferApprovals "Pending offers", PaySchedule
"Pay components", ProbationTracking "tracking", PromotionReadiness "readiness",
RehireHandling "dashboard", RenewalReminders "Upcoming renewals",
ResumableChecklists "Preboarding tasks", SalaryRevisions "history",
ScheduledReporting "Scheduled reports", ShiftBasedAttendance "Published
schedules", SkillGaps "gaps", SuccessionPlanning "pool", TeamAvailability
"availability", TimesheetLock "summary", TransferPromotion "Recent transfers".
Static *reference* lists (predefined options, lifecycle stage references,
MobileInteraction/SwapsReplacements pattern tables) were kept — they are
labelled as predefined, not records.

### 5. Bulk honesty
`lib/bulk-admin.ts` — `summarizeBulkAdmin(ids, results, verbPast, noun)` mirrors
frozen slice-1 `summarizeBulk`, widened to `string | number` ids (module keys,
job uuids). ModuleEntitlements save now uses `Promise.allSettled` per module +
per-key failure detail + re-read of server truth (was: sequential loop that
reported total failure after partial writes).

### 6. States, persistence, a11y, responsive
- Loading (`LoadingRegion`/skeletons), empty (`EmptyState`/empty rows),
  error (`RetryableAlert` for reads, `Alert tone="error"` for actions),
  success (`Alert tone="success"`), permission-denied (`EmptyState` gate) on
  every page.
- All config persists server-side (settings/feature-flags) → survives refresh
  and re-login; no local-only "saved" claims remain.
- 26 pages that returned bare fragments now render inside `Layout` (nav shell,
  responsive container, shortcut registration).
- OrgChart employee list: clickable divs → keyboard-focusable buttons with
  `aria-pressed`; empty state added. Form labels tied to inputs (`htmlFor`)
  on rewritten pages; tables have `caption sr-only` / `scope="col"`.
- Dead-link check: `npm run check:routes` → all internal links resolve
  (incl. JurisdictionRules → `/admin/compliance`).

## Tests (regression)
`frontend/src/lib/feedback-slice2.test.ts` — 552 tests:
- `summarizeBulkAdmin` unit tests (all/partial/total failure, string ids).
- Per-page (101 pages × 4): Alert success + error channel, no toast/sonner/
  `alert()`, mutation catch never feeds load-error channel, no dead endpoints/
  audit claims/placeholder values, Layout wrapper.
- Authz: every settings/flags/integrations page gates SuperAdmin + permission
  state; ADMIN_ROLES kept where the backend allows HR.
- Real-data rewires (bulk allSettled, workflow schema, announcements JSON,
  employee-master managers, persisted notes, stage flags, retry/discard…).
- All 35 fabricated cards asserted gone; fabricated names asserted gone.
- Slice-1 frozen shape re-asserted (UserAdmin no sonner, bulk.ts intact).

## Verification (exact results)
- `vitest run src/lib/feedback-slice2.test.ts src/lib/feedback-slice1.test.ts` → **572/572 passed** (552 slice-2 + 20 slice-1).
- `vitest run` (full frontend suite) → **699/699 passed, 14 files**.
- `tsc --noEmit` → exit 0.
- `npm run build` (vite) → ✓ built in 3.30s.
- `npm run check:routes` → ✓ 247 routes, no dead links.
- `npm run check:api-paths` → ✓.
- Scope: 101 modified files, all under `frontend/src/pages/admin/`; 2 new
  exclusive lib files; frozen-16 intersection **empty**; no backend/payroll/
  auth files touched. No push.
- Review fix round: nested `roles/RoleManagement.tsx` and
  `cleanup/TenantCleanup.tsx` (outside the top-level test glob) migrated to the
  same Alert success/error pattern — toast-placeholder comments removed;
  `bulk-admin.ts` trailing newline added; test-count breakdown corrected above.

## Contract deviations
- None in file scope. Two judgement calls recorded for the validator:
  1. HR read access to ~90 config pages was removed (page gate) because the
     backend returns 403 for HR on those reads — UI now mirrors the API rather
     than showing a guaranteed error. Route roles in App.tsx left untouched
     (outside exclusive set).
  2. Fabricated cards were deleted rather than replaced with new backend
     integrations — no design work was invented; missing endpoints are
     reported above for the architect.