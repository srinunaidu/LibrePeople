# API Inventory — LibrePeople (`/api/v1`)

Source: `backend/app/api/v1/endpoints/*.py` at `216e869`, plus `backend/app/api/v1/api.py` (router prefixes), `backend/app/api/deps.py` (role sets), `docs/API_CONTRACT.md` (contract baseline).
Secrets: repo-root `API.md` is **untracked** (`git ls-files` has no entry) and was **not read**; no values are quoted here. Recommend keeping it untracked/ignored and rotating any live tokens that were ever committed.
Runner for backend suites: `ci/run_backend_tests.sh` (standalone `python backend/<name>.py` scripts, not pytest). Frontend: `*.test.*` colocated suites.

## Counts

- **387 routes across 33 modules** (full-path dedupe; `test_assets.py` in `endpoints/` has 0 routes — see discrepancy D-01).
- `docs/API_CONTRACT.md` documents ~90 endpoints (Phases 1–7); **all are implemented, none missing**.
- ~297 implemented routes are outside the contract (whole modules: auth extensions, core-hr, payroll, ess, expenses, assets, forecasting, platform, compliance, import-export, data-quality, client-onboarding, admin/*, break-glass, plus Phase 1–7 extras).
- Frontend (`frontend/src/lib`, `pages`): 78 distinct API paths, **0 mismatches** vs backend (incl. `POST /public/contact` via `public_router`).

## Cross-cutting rules (apply to every row below)

| Concern | Behaviour |
|---|---|
| Base path | `/api/v1`; auth `Authorization: Bearer <JWT>` except login/register/public-contact |
| Role sets (`app/api/deps.py`) | `ADMIN`=SuperAdmin,HR · `MANAGER`=+Manager · `WORKFORCE`=+Associate · `REPORTS`=SuperAdmin,HR,PayrollViewer · `ALL`=+PayrollViewer · `ASSOCIATE`=(Associate) |
| Password gate | `get_current_active_user`: `must_change_password` accounts may only read own profile, change password, sign out |
| MFA | mandatory for admin roles; enforced per-endpoint via `require_mfa` |
| Refresh | `POST /auth/refresh` rotates; reuse of rotated token revokes whole family (`reuse_detected`); logout revokes |
| Tenant isolation | JWT `tenant` claim → request context var; conflicting `X-Tenant-Id`/param → `422/403 tenant_mismatch`; unresolvable → refuse; legacy `default` slug fallback; employee rows filtered via `apply_visibility` + `tenant_matches` |
| Error envelope | `{code, message, retryable, request_id}` via `ApiError` + `http_exception_handler` (bare `HTTPException` also wrapped); tech detail stays in redacted server logs |
| Storage | `STORAGE_BACKEND=local` (`/tmp/karmathy-storage`) or `s3` (R2: endpoint/bucket/keys); offer letters, onboarding docs, expense receipts, import CSVs |
| Public (no auth) | `POST /auth/login`, `POST /auth/register`, `GET /onboarding-portal/clients/by-slug/{slug}`, `POST /public/contact` (rate-limited) |

## admin_audit — 1 routes (models: user)
_Suites: `admin_audit_test_suite, audit_chain_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/admin/audit/verify` | `ADMIN_ROLES` | `AuditVerification` |

## admin_jobs — 4 routes (models: user)
_Suites: `admin_jobs_test_suite, job_worker_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/admin/jobs` | `ADMIN_ROLES` | `PaginatedJobs` |
| GET | `/admin/jobs/{job_id}` | `ADMIN_ROLES` | `JobOut` |
| POST | `/admin/jobs/{job_id}/retry` | `ADMIN_ROLES` | `JobOut` |
| POST | `/admin/jobs/{job_id}/discard` | `ADMIN_ROLES` | `JobOut` |

## admin_status — 1 routes (models: user)
_Suites: `admin_status_test_suite, ops_model_test_suite, startup_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/admin/status` | `via get_db,require_superadmin` | `AdminStatus` |

## applications — 4 routes (models: user)
_Suites: `talent_test_suite, smoke_test_phase2`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/applications/` | `ADMIN_ROLES` | `list[ApplicationOut]` |
| POST | `/applications/` | `ADMIN_ROLES` | `ApplicationOut` |
| GET | `/applications/{application_id}` | `ADMIN_ROLES` | `ApplicationOut` |
| PUT | `/applications/{application_id}` | `ADMIN_ROLES` | `ApplicationOut` |

## assets — 13 routes (models: assets, user)
_Suites: `none found (storage backend: r2_storage_test_suite)`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/assets` | `WORKFORCE_ROLES` | `list[AssetOut]` |
| POST | `/assets` | `ADMIN_ROLES` | `AssetOut` |
| GET | `/assets/assignments` | `WORKFORCE_ROLES` | `list[AssetAssignmentOut]` |
| POST | `/assets/assignments/{assignment_id}/ack` | `WORKFORCE_ROLES` | `—` |
| GET | `/assets/clearance/{employee_id}` | `MANAGER_ROLES` | `—` |
| GET | `/assets/{asset_id}` | `WORKFORCE_ROLES` | `AssetOut` |
| PATCH | `/assets/{asset_id}` | `ADMIN_ROLES` | `AssetOut` |
| POST | `/assets/{asset_id}/assign` | `ADMIN_ROLES` | `AssetAssignmentOut` |
| POST | `/assets/{asset_id}/transfer` | `ADMIN_ROLES` | `AssetAssignmentOut` |
| POST | `/assets/{asset_id}/return` | `ADMIN_ROLES` | `AssetAssignmentOut` |
| POST | `/assets/{asset_id}/maintenance/start` | `ADMIN_ROLES` | `—` |
| POST | `/assets/{asset_id}/maintenance/complete` | `ADMIN_ROLES` | `—` |
| POST | `/assets/{asset_id}/retire` | `ADMIN_ROLES` | `AssetOut` |

## auth — 16 routes (models: refresh_token, user)
_Suites: `mfa_test_suite, admin_mfa_reset_test_suite, lp_phase2_item10_mfa_test_suite, reset_admin_password_test_suite, security_test_suite, stepup_rate_limit_test_suite, superadmin_write_gate_test_suite, smoke_test`._

| Method | Route | Auth | Response |
|---|---|---|---|
| POST | `/auth/login` | `via get_db` | `LoginResponse` |
| POST | `/auth/register` | `via get_db` | `UserOut` |
| POST | `/auth/refresh` | `via get_db` | `—` |
| POST | `/auth/logout` | `ALL_ROLES` | `—` |
| GET | `/auth/me` | `ALL_ROLES` | `UserOut` |
| GET | `/auth/mfa/status` | `ALL_ROLES` | `MFAStatusResponse` |
| POST | `/auth/mfa/enroll` | `ALL_ROLES` | `MFAEnrollResponse` |
| POST | `/auth/mfa/confirm` | `ALL_ROLES` | `—` |
| POST | `/auth/mfa/disable` | `ALL_ROLES` | `—` |
| POST | `/auth/mfa/reset` | `"SuperAdmin"` | `—` |
| POST | `/auth/password` | `ALL_ROLES` | `—` |
| POST | `/auth/users/{user_id}/password` | `ADMIN_ROLES` | `—` |
| PATCH | `/auth/users/{user_id}` | `ADMIN_ROLES` | `UserOut` |
| GET | `/auth/users` | `ADMIN_ROLES` | `list[UserOut]` |
| POST | `/auth/users` | `ADMIN_ROLES` | `UserOut` |
| POST | `/auth/impersonate` | `"SuperAdmin"` | `ImpersonateResponse` |

## benefits — 9 routes (models: benefits, user)
_Suites: `none found`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/benefits/benefit-plans` | `ALL_ROLES` | `list[BenefitPlanOut]` |
| POST | `/benefits/benefit-plans` | `ADMIN_ROLES` | `BenefitPlanOut` |
| GET | `/benefits/benefit-enrollments` | `WORKFORCE_ROLES` | `list[BenefitEnrollmentOut]` |
| POST | `/benefits/benefit-enrollments` | `ADMIN_ROLES` | `BenefitEnrollmentOut` |
| GET | `/benefits/life-events` | `WORKFORCE_ROLES` | `list[LifeEventOut]` |
| POST | `/benefits/life-events` | `WORKFORCE_ROLES` | `LifeEventOut` |
| GET | `/benefits/leaves-of-absence` | `WORKFORCE_ROLES` | `list[LeaveOfAbsenceOut]` |
| POST | `/benefits/leaves-of-absence` | `WORKFORCE_ROLES` | `LeaveOfAbsenceOut` |
| PUT | `/benefits/leaves-of-absence/{loa_id}/approve` | `ADMIN_ROLES` | `LeaveOfAbsenceOut` |

## break_glass — 3 routes (models: break_glass, user)
_Suites: `none found`._

| Method | Route | Auth | Response |
|---|---|---|---|
| POST | `/break-glass/access` | `"SuperAdmin"` | `—` |
| GET | `/break-glass/grants` | `"SuperAdmin"` | `—` |
| DELETE | `/break-glass/grants/{grant_id}` | `"SuperAdmin"` | `—` |

## candidates — 4 routes (models: user)
_Suites: `talent_test_suite, smoke_test_phase2`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/candidates/` | `ADMIN_ROLES` | `list[CandidateOut]` |
| POST | `/candidates/` | `ADMIN_ROLES` | `CandidateOut` |
| GET | `/candidates/{candidate_id}` | `ADMIN_ROLES` | `CandidateOut` |
| PUT | `/candidates/{candidate_id}` | `ADMIN_ROLES` | `CandidateOut` |

## client_onboarding — 32 routes (models: client_onboarding, user)
_Suites: `smoke_test_client_onboarding, migration_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/onboarding-portal/clients/by-slug/{slug}` | `via get_db` | `—` |
| GET | `/onboarding-portal/clients` | `"SuperAdmin"` | `list[ClientOut]` |
| POST | `/onboarding-portal/clients` | `"SuperAdmin"` | `ClientOut` |
| GET | `/onboarding-portal/clients/{client_id}` | `"SuperAdmin"` | `ClientOut` |
| PUT | `/onboarding-portal/clients/{client_id}` | `"SuperAdmin"` | `ClientOut` |
| DELETE | `/onboarding-portal/clients/{client_id}` | `"SuperAdmin"` | `—` |
| GET | `/onboarding-portal/tenants` | `"SuperAdmin"` | `list[ClientOut]` |
| GET | `/onboarding-portal/tenants/{client_id}` | `"SuperAdmin"` | `ClientOut` |
| PATCH | `/onboarding-portal/tenants/{client_id}` | `"SuperAdmin"` | `ClientOut` |
| POST | `/onboarding-portal/tenants/{client_id}/provision` | `"SuperAdmin"` | `—` |
| POST | `/onboarding-portal/tenants/{client_id}/suspend` | `"SuperAdmin", "HR"` | `—` |
| POST | `/onboarding-portal/tenants/{client_id}/reactivate` | `"SuperAdmin", "HR"` | `—` |
| POST | `/onboarding-portal/tenants/{client_id}/read-only` | `"SuperAdmin"` | `—` |
| POST | `/onboarding-portal/tenants/{client_id}/deprovision` | `"SuperAdmin"` | `—` |
| POST | `/onboarding-portal/tenants/{client_id}/archive` | `"SuperAdmin"` | `—` |
| GET | `/onboarding-portal/clients/{client_id}/settings` | `"SuperAdmin"` | `list[ClientSettingOut]` |
| PUT | `/onboarding-portal/clients/{client_id}/settings/{key}` | `"SuperAdmin"` | `ClientSettingOut` |
| GET | `/onboarding-portal/clients/{client_id}/feature-flags` | `"SuperAdmin"` | `list[FeatureFlagOut]` |
| PUT | `/onboarding-portal/clients/{client_id}/feature-flags/{key}` | `"SuperAdmin"` | `FeatureFlagOut` |
| GET | `/onboarding-portal/clients/{client_id}/integrations` | `"SuperAdmin"` | `list[IntegrationOut]` |
| POST | `/onboarding-portal/clients/{client_id}/integrations` | `"SuperAdmin"` | `IntegrationOut` |
| PUT | `/onboarding-portal/clients/{client_id}/integrations/{integration_id}` | `"SuperAdmin"` | `IntegrationOut` |
| DELETE | `/onboarding-portal/clients/{client_id}/integrations/{integration_id}` | `"SuperAdmin"` | `—` |
| POST | `/onboarding-portal/clients/{client_id}/integrations/{integration_id}/test` | `"SuperAdmin"` | `IntegrationOut` |
| GET | `/onboarding-portal/clients/{client_id}/migrations` | `"SuperAdmin"` | `list[MigrationJobOut]` |
| POST | `/onboarding-portal/clients/{client_id}/migrations` | `"SuperAdmin"` | `MigrationJobOut` |
| POST | `/onboarding-portal/clients/{client_id}/migrations/{job_id}/run` | `"SuperAdmin"` | `MigrationJobOut` |
| POST | `/onboarding-portal/clients/{client_id}/migrations/{job_id}/cancel` | `"SuperAdmin"` | `MigrationJobOut` |
| GET | `/onboarding-portal/clients/{client_id}/onboarding` | `"SuperAdmin"` | `OnboardingProgress` |
| POST | `/onboarding-portal/clients/{client_id}/onboarding/steps` | `"SuperAdmin"` | `OnboardingStepOut` |
| POST | `/onboarding-portal/clients/{client_id}/onboarding/steps/{step_id}/complete` | `"SuperAdmin"` | `OnboardingStepOut` |
| GET | `/onboarding-portal/docs/migration-api` | `"SuperAdmin"` | `—` |

## compliance — 13 routes (models: compliance, user)
_Suites: `none found`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/compliance/compliance-rules` | `ADMIN_ROLES` | `list[ComplianceRuleOut]` |
| POST | `/compliance/compliance-rules` | `ADMIN_ROLES` | `ComplianceRuleOut` |
| GET | `/compliance/compliance-violations` | `WORKFORCE_ROLES` | `list[ComplianceViolationOut]` |
| POST | `/compliance/compliance-violations` | `ADMIN_ROLES` | `ComplianceViolationOut` |
| PUT | `/compliance/compliance-violations/{violation_id}/resolve` | `ADMIN_ROLES` | `ComplianceViolationOut` |
| GET | `/compliance/headcount-plans` | `ADMIN_ROLES` | `list[HeadcountPlanOut]` |
| POST | `/compliance/headcount-plans` | `ADMIN_ROLES` | `HeadcountPlanOut` |
| GET | `/compliance/scenarios` | `MANAGER_ROLES` | `list[ScenarioOut]` |
| POST | `/compliance/scenarios` | `ADMIN_ROLES` | `ScenarioOut` |
| GET | `/compliance/report-definitions` | `ADMIN_ROLES` | `list[ReportDefinitionOut]` |
| POST | `/compliance/report-definitions` | `ADMIN_ROLES` | `ReportDefinitionOut` |
| GET | `/compliance/saved-reports` | `ADMIN_ROLES` | `list[SavedReportOut]` |
| POST | `/compliance/saved-reports` | `ADMIN_ROLES` | `SavedReportOut` |

## core_hr — 30 routes (models: core_hr, department, job, learning, user)
_Suites: `legal_entity_test_suite, hr_helpdesk_test_suite, public_contact_test_suite, custom_fields_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/core-hr/locations` | `ALL_ROLES` | `list[LocationOut]` |
| POST | `/core-hr/locations` | `ADMIN_ROLES` | `LocationOut` |
| GET | `/core-hr/locations/{location_id}` | `ALL_ROLES` | `LocationOut` |
| PATCH | `/core-hr/locations/{location_id}` | `ADMIN_ROLES` | `LocationOut` |
| DELETE | `/core-hr/locations/{location_id}` | `ADMIN_ROLES` | `—` |
| GET | `/core-hr/cost-centers` | `ALL_ROLES` | `list[CostCenterOut]` |
| POST | `/core-hr/cost-centers` | `ADMIN_ROLES` | `CostCenterOut` |
| GET | `/core-hr/cost-centers/{cost_center_id}` | `ALL_ROLES` | `CostCenterOut` |
| PATCH | `/core-hr/cost-centers/{cost_center_id}` | `ADMIN_ROLES` | `CostCenterOut` |
| DELETE | `/core-hr/cost-centers/{cost_center_id}` | `ADMIN_ROLES` | `—` |
| GET | `/core-hr/legal-entities` | `ALL_ROLES` | `list[LegalEntityOut]` |
| POST | `/core-hr/legal-entities` | `ADMIN_ROLES` | `LegalEntityOut` |
| GET | `/core-hr/legal-entities/{legal_entity_id}` | `ALL_ROLES` | `LegalEntityOut` |
| PATCH | `/core-hr/legal-entities/{legal_entity_id}` | `ADMIN_ROLES` | `LegalEntityOut` |
| DELETE | `/core-hr/legal-entities/{legal_entity_id}` | `ADMIN_ROLES` | `—` |
| GET | `/core-hr/positions` | `ALL_ROLES` | `list[PositionOut]` |
| POST | `/core-hr/positions` | `ADMIN_ROLES` | `PositionOut` |
| GET | `/core-hr/positions/{position_id}` | `ALL_ROLES` | `PositionOut` |
| PATCH | `/core-hr/positions/{position_id}` | `ADMIN_ROLES` | `PositionOut` |
| DELETE | `/core-hr/positions/{position_id}` | `ADMIN_ROLES` | `—` |
| GET | `/core-hr/employee-documents` | `WORKFORCE_ROLES` | `list[EmployeeDocumentOut]` |
| POST | `/core-hr/employee-documents` | `ADMIN_ROLES` | `EmployeeDocumentOut` |
| GET | `/core-hr/employee-documents/{document_id}/versions` | `WORKFORCE_ROLES` | `—` |
| POST | `/core-hr/employee-documents/{document_id}/versions` | `ADMIN_ROLES` | `—` |
| POST | `/core-hr/employee-documents/{document_id}/ack` | `WORKFORCE_ROLES` | `—` |
| GET | `/core-hr/cases` | `WORKFORCE_ROLES` | `list[HRCaseOut]` |
| POST | `/core-hr/cases` | `WORKFORCE_ROLES` | `HRCaseOut` |
| PUT | `/core-hr/cases/{case_id}` | `ADMIN_ROLES` | `HRCaseOut` |
| POST | `/core-hr/cases/{case_id}/comments` | `WORKFORCE_ROLES` | `CaseCommentOut` |
| GET | `/core-hr/cases/{case_id}/comments` | `WORKFORCE_ROLES` | `list[CaseCommentOut]` |

## data_quality — 3 routes (models: user)
_Suites: `data_quality_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/data-quality/checks` | `ADMIN_ROLES` | `—` |
| GET | `/data-quality/issues` | `ADMIN_ROLES` | `—` |
| POST | `/data-quality/scan` | `ADMIN_ROLES` | `—` |

## departments — 5 routes (models: compliance, core_hr, department, employee, job, recruiting, user)
_Suites: `master_data_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/departments/` | `ALL_ROLES` | `list[DepartmentOut]` |
| POST | `/departments/` | `ADMIN_ROLES` | `DepartmentOut` |
| GET | `/departments/{department_id}` | `ALL_ROLES` | `DepartmentOut` |
| PATCH | `/departments/{department_id}` | `ADMIN_ROLES` | `DepartmentOut` |
| DELETE | `/departments/{department_id}` | `ADMIN_ROLES` | `—` |

## employees — 6 routes (models: core_hr, department, employee, job, user)
_Suites: `employees_test_suite, employment_history_test_suite, visibility_test_suite, cross_tenant_test_suite, smoke_test`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/employees/` | `ALL_ROLES` | `EmployeePage` |
| POST | `/employees/` | `ADMIN_ROLES` | `EmployeeOut` |
| GET | `/employees/{employee_id}` | `ALL_ROLES` | `EmployeeOut` |
| PATCH | `/employees/{employee_id}` | `ADMIN_ROLES` | `EmployeeOut` |
| PUT | `/employees/{employee_id}` | `ADMIN_ROLES` | `EmployeeOut` |
| GET | `/employees/{employee_id}/history` | `ALL_ROLES` | `list[EmployeeHistoryOut]` |

## ess_hr — 24 routes (models: compliance, department, employee, ess_hr, job, performance, user)
_Suites: `ess_hub_test_suite, notification_centre/delivery/email_provider suites`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/ess/ess/profile/{employee_id}` | `ASSOCIATE_ROLES` | `ESSProfileOut` |
| POST | `/ess/ess/profile` | `ASSOCIATE_ROLES` | `ESSProfileOut` |
| PUT | `/ess/ess/profile/{employee_id}` | `ASSOCIATE_ROLES` | `ESSProfileOut` |
| GET | `/ess/notifications` | `ASSOCIATE_ROLES` | `list[NotificationOut]` |
| GET | `/ess/notifications/unread-count` | `ASSOCIATE_ROLES` | `—` |
| GET | `/ess/notifications/preferences` | `ASSOCIATE_ROLES` | `—` |
| PUT | `/ess/notifications/preferences` | `ASSOCIATE_ROLES` | `—` |
| POST | `/ess/notifications` | `ADMIN_ROLES` | `NotificationOut` |
| PUT | `/ess/notifications/{notification_id}/read` | `ASSOCIATE_ROLES` | `NotificationOut` |
| GET | `/ess/employee-files` | `ASSOCIATE_ROLES` | `list[EmployeeFileOut]` |
| POST | `/ess/employee-files` | `ADMIN_ROLES` | `EmployeeFileOut` |
| GET | `/ess/announcements` | `ASSOCIATE_ROLES` | `list[AnnouncementOut]` |
| POST | `/ess/announcements` | `ADMIN_ROLES` | `AnnouncementOut` |
| PUT | `/ess/announcements/{announcement_id}/publish` | `ADMIN_ROLES` | `AnnouncementOut` |
| GET | `/ess/directory` | `ASSOCIATE_ROLES` | `list[DirectoryEntryOut]` |
| POST | `/ess/directory/sync` | `ADMIN_ROLES` | `—` |
| GET | `/ess/org-chart` | `ASSOCIATE_ROLES` | `list[OrgNodeOut]` |
| POST | `/ess/org-chart/rebuild` | `ADMIN_ROLES` | `—` |
| GET | `/ess/goal-alignments` | `ASSOCIATE_ROLES` | `list[GoalAlignmentOut]` |
| POST | `/ess/goal-alignments` | `MANAGER_ROLES` | `GoalAlignmentOut` |
| GET | `/ess/continuous-feedback` | `ASSOCIATE_ROLES` | `list[ContinuousFeedbackOut]` |
| POST | `/ess/continuous-feedback` | `ASSOCIATE_ROLES` | `ContinuousFeedbackOut` |
| GET | `/ess/compliance-checks` | `ADMIN_ROLES` | `list[ComplianceCheckOut]` |
| POST | `/ess/compliance-checks/run` | `ADMIN_ROLES` | `—` |

## expenses — 16 routes (models: employee, expenses, user)
_File upload: receipt UploadFile._
_Suites: `expenses_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/expenses/categories` | `ALL_ROLES` | `list[ExpenseCategoryOut]` |
| POST | `/expenses/categories` | `ADMIN_ROLES` | `ExpenseCategoryOut` |
| GET | `/expenses/categories/{category_id}` | `ALL_ROLES` | `ExpenseCategoryOut` |
| PATCH | `/expenses/categories/{category_id}` | `ADMIN_ROLES` | `ExpenseCategoryOut` |
| GET | `/expenses/claims` | `WORKFORCE_ROLES` | `list[ExpenseClaimOut]` |
| POST | `/expenses/claims` | `WORKFORCE_ROLES` | `ExpenseClaimOut` |
| GET | `/expenses/claims/{claim_id}` | `WORKFORCE_ROLES` | `ExpenseClaimOut` |
| PATCH | `/expenses/claims/{claim_id}` | `WORKFORCE_ROLES` | `ExpenseClaimOut` |
| POST | `/expenses/claims/{claim_id}/submit` | `WORKFORCE_ROLES` | `ExpenseClaimOut` |
| POST | `/expenses/claims/{claim_id}/l1-approve` | `MANAGER_ROLES` | `ExpenseClaimOut` |
| POST | `/expenses/claims/{claim_id}/approve` | `ADMIN_ROLES` | `ExpenseClaimOut` |
| POST | `/expenses/claims/{claim_id}/reject` | `MANAGER_ROLES` | `ExpenseClaimOut` |
| POST | `/expenses/claims/{claim_id}/rework` | `WORKFORCE_ROLES` | `ExpenseClaimOut` |
| POST | `/expenses/claims/{claim_id}/mark-paid` | `ADMIN_ROLES` | `ExpenseClaimOut` |
| POST | `/expenses/claims/{claim_id}/receipts` | `WORKFORCE_ROLES` | `ExpenseReceiptOut` |
| GET | `/expenses/claims/{claim_id}/receipts` | `WORKFORCE_ROLES` | `list[ExpenseReceiptOut]` |

## filings — 1 routes (models: employee, payroll, user)
_Suites: `none found`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/reports/filings/{filing_type}` | `REPORTS_ROLES` | `—` |

## forecasting — 21 routes (models: forecasting, user)
_File upload: driver/demand CSV UploadFile._
_Suites: `forecasting_tenant_isolation_test_suite, cost_forecast_test_suite, accuracy_test_suite, scenario_builder_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| POST | `/forecasting/runs` | `MANAGER_ROLES` | `ForecastRunOut` |
| GET | `/forecasting/runs` | `MANAGER_ROLES` | `list[ForecastRunOut]` |
| GET | `/forecasting/runs/{run_id}` | `MANAGER_ROLES` | `ForecastRunOut` |
| GET | `/forecasting/runs/{run_id}/results` | `MANAGER_ROLES` | `—` |
| GET | `/forecasting/runs/{run_id}/demand-series` | `MANAGER_ROLES` | `—` |
| POST | `/forecasting/drivers` | `MANAGER_ROLES` | `—` |
| POST | `/forecasting/drivers/import` | `MANAGER_ROLES` | `—` |
| POST | `/forecasting/demand/series` | `MANAGER_ROLES` | `—` |
| POST | `/forecasting/scenarios` | `MANAGER_ROLES` | `ScenarioOut` |
| GET | `/forecasting/scenarios` | `MANAGER_ROLES` | `PaginatedScenarios` |
| GET | `/forecasting/scenarios/{scenario_id}` | `MANAGER_ROLES` | `ScenarioOut` |
| POST | `/forecasting/scenarios/compare` | `MANAGER_ROLES` | `ScenarioComparison` |
| GET | `/forecasting/scenarios/{scenario_id}/versions` | `MANAGER_ROLES` | `ScenarioVersionList` |
| POST | `/forecasting/scenarios/{scenario_id}/versions` | `MANAGER_ROLES` | `ScenarioOut` |
| POST | `/forecasting/scenarios/{scenario_id}/fork` | `MANAGER_ROLES` | `ScenarioOut` |
| POST | `/forecasting/runs/{run_id}/cost-forecast` | `MANAGER_ROLES` | `—` |
| GET | `/forecasting/runs/{run_id}/cost-forecast` | `MANAGER_ROLES` | `CostForecastVersionSummaryList` |
| GET | `/forecasting/runs/{run_id}/cost-forecast/csv` | `MANAGER_ROLES` | `None` |
| GET | `/forecasting/runs/{run_id}/cost-forecast/{version}` | `MANAGER_ROLES` | `CostForecastOut` |
| POST | `/forecasting/accuracy/sync` | `MANAGER_ROLES` | `—` |
| GET | `/forecasting/accuracy` | `MANAGER_ROLES` | `PaginatedForecastAccuracy` |

## import_export — 10 routes (models: user)
_File upload: import CSV UploadFile._
_Suites: `import_test_suite, job_worker_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/import-export/export/{entity}` | `via get_db,get_current_admin_user` | `—` |
| GET | `/import-export/template/{entity}` | `via get_current_admin_user` | `—` |
| GET | `/import-export/columns/{entity}` | `via get_current_admin_user` | `—` |
| POST | `/import-export/import/{entity}` | `via get_db,get_current_admin_user` | `—` |
| POST | `/import-export/import/{entity}/dry-run` | `via get_db,get_current_admin_user` | `—` |
| POST | `/import-export/import/{entity}/commit` | `via get_db,get_current_admin_user` | `—` |
| POST | `/import-export/import/{entity}/cancel` | `via get_db,get_current_admin_user` | `—` |
| GET | `/import-export/import/{entity}/progress/{job_id}` | `via get_db,get_current_admin_user` | `—` |
| GET | `/import-export/import/{entity}/row-errors` | `via get_db,get_current_admin_user` | `—` |
| GET | `/import-export/entities` | `via get_current_admin_user` | `—` |

## integrations_platform — 12 routes (models: integrations_platform, user)
_Suites: `none found`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/platform/sso-configs` | `"SuperAdmin"` | `list[SSOConfigOut]` |
| POST | `/platform/sso-configs` | `"SuperAdmin"` | `SSOConfigOut` |
| GET | `/platform/webhooks` | `"SuperAdmin"` | `list[WebhookOut]` |
| POST | `/platform/webhooks` | `"SuperAdmin"` | `WebhookOut` |
| GET | `/platform/webhooks/{webhook_id}/deliveries` | `"SuperAdmin"` | `list[WebhookDeliveryOut]` |
| POST | `/platform/webhooks/{webhook_id}/deliver` | `"SuperAdmin"` | `WebhookDeliveryOut` |
| GET | `/platform/background-checks` | `ADMIN_ROLES` | `list[BackgroundCheckOut]` |
| POST | `/platform/background-checks` | `ADMIN_ROLES` | `BackgroundCheckOut` |
| PUT | `/platform/background-checks/{check_id}/complete` | `ADMIN_ROLES` | `BackgroundCheckOut` |
| GET | `/platform/e-signatures` | `ADMIN_ROLES` | `list[ESignatureOut]` |
| POST | `/platform/e-signatures` | `ADMIN_ROLES` | `ESignatureOut` |
| PUT | `/platform/e-signatures/{sig_id}/sign` | `ADMIN_ROLES` | `ESignatureOut` |

## jobs — 5 routes (models: core_hr, department, employee, job, performance, recruiting, user)
_Suites: `jobs_test_suite, master_data_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/jobs/` | `ALL_ROLES` | `list[JobOut]` |
| POST | `/jobs/` | `ADMIN_ROLES` | `JobOut` |
| GET | `/jobs/{job_id}` | `ALL_ROLES` | `JobOut` |
| PATCH | `/jobs/{job_id}` | `ADMIN_ROLES` | `JobOut` |
| DELETE | `/jobs/{job_id}` | `ADMIN_ROLES` | `—` |

## learning — 12 routes (models: learning, user)
_Suites: `none found`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/learning/courses` | `ALL_ROLES` | `list[CourseOut]` |
| POST | `/learning/courses` | `ADMIN_ROLES` | `CourseOut` |
| GET | `/learning/course-enrollments` | `WORKFORCE_ROLES` | `list[CourseEnrollmentOut]` |
| POST | `/learning/course-enrollments` | `WORKFORCE_ROLES` | `CourseEnrollmentOut` |
| PUT | `/learning/course-enrollments/{enrollment_id}/complete` | `WORKFORCE_ROLES` | `CourseEnrollmentOut` |
| GET | `/learning/certifications` | `WORKFORCE_ROLES` | `list[CertificationOut]` |
| POST | `/learning/certifications` | `WORKFORCE_ROLES` | `CertificationOut` |
| GET | `/learning/talent-pools` | `MANAGER_ROLES` | `list[TalentPoolOut]` |
| POST | `/learning/talent-pools` | `ADMIN_ROLES` | `TalentPoolOut` |
| POST | `/learning/talent-pool-members` | `ADMIN_ROLES` | `TalentPoolMemberOut` |
| GET | `/learning/succession-plans` | `MANAGER_ROLES` | `list[SuccessionPlanOut]` |
| POST | `/learning/succession-plans` | `ADMIN_ROLES` | `SuccessionPlanOut` |

## leave — 13 routes (models: leave, user)
_Suites: `leave_test_suite, smoke_test_phases_3_7`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/leave/types` | `ALL_ROLES` | `list[LeaveTypeOut]` |
| POST | `/leave/types` | `ADMIN_ROLES` | `LeaveTypeOut` |
| PUT | `/leave/types/{leave_type_id}` | `ADMIN_ROLES` | `LeaveTypeOut` |
| GET | `/leave/balances` | `WORKFORCE_ROLES` | `list[LeaveBalanceOut]` |
| GET | `/leave/balances/{employee_id}/ledger` | `WORKFORCE_ROLES` | `list[LeaveLedgerEntryOut]` |
| GET | `/leave/reconciliation` | `MANAGER_ROLES` | `LeaveReconciliationOut` |
| GET | `/leave/payroll-input` | `REPORTS_ROLES` | `LeavePayrollInputOut` |
| POST | `/leave/entitlements` | `ADMIN_ROLES` | `—` |
| GET | `/leave/requests` | `WORKFORCE_ROLES` | `list[LeaveRequestOut]` |
| POST | `/leave/requests` | `WORKFORCE_ROLES` | `LeaveRequestOut` |
| POST | `/leave/requests/{request_id}/approve` | `MANAGER_ROLES` | `LeaveRequestOut` |
| POST | `/leave/requests/{request_id}/reject` | `MANAGER_ROLES` | `LeaveRequestOut` |
| POST | `/leave/requests/{request_id}/cancel` | `WORKFORCE_ROLES` | `LeaveRequestOut` |

## offboarding — 11 routes (models: employee, offboarding, user)
_Suites: `lifecycle_test_suite, smoke_test_phases_3_7`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/offboarding/tasks` | `ADMIN_ROLES` | `list[OffboardingTaskOut]` |
| POST | `/offboarding/tasks` | `ADMIN_ROLES` | `OffboardingTaskOut` |
| PUT | `/offboarding/tasks/{task_id}` | `ADMIN_ROLES` | `OffboardingTaskOut` |
| GET | `/offboarding/terminations` | `WORKFORCE_ROLES` | `list[TerminationOut]` |
| GET | `/offboarding/terminations/{termination_id}` | `WORKFORCE_ROLES` | `TerminationOut` |
| POST | `/offboarding/terminations` | `ADMIN_ROLES` | `TerminationOut` |
| PUT | `/offboarding/terminations/{termination_id}` | `ADMIN_ROLES` | `TerminationOut` |
| POST | `/offboarding/terminations/{termination_id}/complete` | `ADMIN_ROLES` | `TerminationOut` |
| POST | `/offboarding/terminations/{termination_id}/cancel` | `ADMIN_ROLES` | `TerminationOut` |
| GET | `/offboarding/terminations/{termination_id}/progress` | `WORKFORCE_ROLES` | `—` |
| PUT | `/offboarding/items/{item_id}` | `ADMIN_ROLES` | `OffboardingItemOut` |

## offers — 7 routes (models: department, employee, onboarding, recruiting, user)
_Suites: `talent_test_suite, hire_test_suite, smoke_test_phase2`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/offers/` | `ADMIN_ROLES` | `list[OfferOut]` |
| POST | `/offers/` | `ADMIN_ROLES` | `OfferOut` |
| GET | `/offers/{offer_id}` | `ADMIN_ROLES` | `OfferOut` |
| PUT | `/offers/{offer_id}` | `ADMIN_ROLES` | `OfferOut` |
| POST | `/offers/{offer_id}/letter` | `ADMIN_ROLES` | `OfferOut` |
| POST | `/offers/{offer_id}/accept` | `ADMIN_ROLES` | `OfferOut` |
| POST | `/offers/{offer_id}/hire` | `ADMIN_ROLES` | `HireResult` |

## onboarding — 12 routes (models: user)
_File upload: document UploadFile._
_Suites: `onboarding_test_suite, smoke_test_phase2`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/onboarding/presets` | `ADMIN_ROLES` | `list[PresetSummaryOut]` |
| GET | `/onboarding/presets/{preset_id}` | `ADMIN_ROLES` | `PresetDetailOut` |
| GET | `/onboarding/presets/{preset_id}/diff` | `ADMIN_ROLES` | `PresetDifferenceOut` |
| GET | `/onboarding/readiness` | `ADMIN_ROLES` | `ReadinessOut` |
| GET | `/onboarding/{employee_id}/summary` | `ALL_ROLES` | `OnboardingSummary` |
| POST | `/onboarding/{employee_id}/checklist` | `ADMIN_ROLES` | `—` |
| GET | `/onboarding/{employee_id}/tasks` | `ALL_ROLES` | `list[OnboardingTaskOut]` |
| POST | `/onboarding/tasks` | `ADMIN_ROLES` | `OnboardingTaskOut` |
| PUT | `/onboarding/tasks/{task_id}` | `ADMIN_ROLES` | `OnboardingTaskOut` |
| GET | `/onboarding/{employee_id}/documents` | `ALL_ROLES` | `list[OnboardingDocumentOut]` |
| POST | `/onboarding/{employee_id}/documents` | `ADMIN_ROLES` | `—` |
| PUT | `/onboarding/documents/{document_id}` | `ADMIN_ROLES` | `OnboardingDocumentOut` |

## payroll — 22 routes (models: audit, employee, leave, payroll, time_attendance, user)
_Suites: `payroll_test_suite, payroll_execution_test_suite, payroll_pipeline_test_suite, payroll_framework_restart_test_suite, payroll_golden_p5_test_suite, india_payroll_test_suite, india_payroll_final_test_suite`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/payroll/periods` | `REPORTS_ROLES` | `list[PayrollPeriodOut]` |
| POST | `/payroll/periods` | `ADMIN_ROLES` | `PayrollPeriodOut` |
| GET | `/payroll/components` | `REPORTS_ROLES` | `list[PayComponentOut]` |
| POST | `/payroll/components` | `ADMIN_ROLES` | `PayComponentOut` |
| GET | `/payroll/pay-profiles` | `ALL_ROLES` | `list[EmployeePayProfileOut]` |
| GET | `/payroll/pay-profiles/{employee_id}` | `ALL_ROLES` | `EmployeePayProfileOut` |
| POST | `/payroll/pay-profiles` | `ADMIN_ROLES` | `EmployeePayProfileOut` |
| GET | `/payroll/runs` | `REPORTS_ROLES` | `list[PayRunOut]` |
| GET | `/payroll/runs/{run_id}` | `REPORTS_ROLES` | `PayRunOut` |
| POST | `/payroll/runs` | `ADMIN_ROLES` | `PayRunOut` |
| POST | `/payroll/runs/{run_id}/approve` | `ADMIN_ROLES` | `PayRunOut` |
| POST | `/payroll/runs/{run_id}/finalize` | `ADMIN_ROLES` | `PayRunOut` |
| POST | `/payroll/runs/{run_id}/payment-file` | `ADMIN_ROLES` | `—` |
| POST | `/payroll/runs/{run_id}/process` | `ADMIN_ROLES` | `PayRunOut` |
| GET | `/payroll/runs/{run_id}/fnf` | `?` | `—` |
| POST | `/payroll/runs/{run_id}/fnf` | `REPORTS_ROLES` | `—` |
| GET | `/payroll/runs/{run_id}/reconciliation` | `REPORTS_ROLES` | `—` |
| GET | `/payroll/runs/{run_id}/history` | `REPORTS_ROLES` | `—` |
| GET | `/payroll/payslips` | `ALL_ROLES` | `list[PaySlipOut]` |
| GET | `/payroll/payslips/{slip_id}` | `ALL_ROLES` | `PaySlipOut` |
| GET | `/payroll/payslips/{slip_id}/pdf` | `ALL_ROLES` | `—` |
| POST | `/payroll/payslips` | `ADMIN_ROLES` | `PaySlipOut` |

## performance — 15 routes (models: performance, user)
_Suites: `none found`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/performance/goals` | `WORKFORCE_ROLES` | `list[GoalOut]` |
| POST | `/performance/goals` | `MANAGER_ROLES` | `GoalOut` |
| PUT | `/performance/goals/{goal_id}` | `MANAGER_ROLES` | `GoalOut` |
| GET | `/performance/reviews` | `WORKFORCE_ROLES` | `list[PerformanceReviewOut]` |
| POST | `/performance/reviews` | `MANAGER_ROLES` | `PerformanceReviewOut` |
| PUT | `/performance/reviews/{review_id}` | `MANAGER_ROLES` | `PerformanceReviewOut` |
| POST | `/performance/reviews/{review_id}/finalize` | `MANAGER_ROLES` | `PerformanceReviewOut` |
| GET | `/performance/feedback` | `WORKFORCE_ROLES` | `list[ReviewFeedbackOut]` |
| POST | `/performance/feedback` | `WORKFORCE_ROLES` | `ReviewFeedbackOut` |
| GET | `/performance/compensation-bands` | `ADMIN_ROLES` | `list[CompensationBandOut]` |
| POST | `/performance/compensation-bands` | `ADMIN_ROLES` | `CompensationBandOut` |
| GET | `/performance/merit-cycles` | `ADMIN_ROLES` | `list[MeritCycleOut]` |
| POST | `/performance/merit-cycles` | `ADMIN_ROLES` | `MeritCycleOut` |
| GET | `/performance/merit-allocations` | `ADMIN_ROLES` | `list[MeritAllocationOut]` |
| POST | `/performance/merit-allocations` | `ADMIN_ROLES` | `MeritAllocationOut` |

## reports — 14 routes (models: employee, payroll, user)
_Suites: `reports_slice_test_suite, metrics_test_suite, audit_test_suite, audit_chain_test_suite, smoke_test_phases_3_7`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/reports/dashboard` | `REPORTS_ROLES` | `—` |
| GET | `/reports/headcount` | `REPORTS_ROLES` | `—` |
| GET | `/reports/leave` | `REPORTS_ROLES` | `—` |
| GET | `/reports/labor-cost` | `REPORTS_ROLES` | `—` |
| GET | `/reports/attendance` | `MANAGER_ROLES` | `—` |
| GET | `/reports/audit` | `ADMIN_ROLES` | `list[AuditLogOut]` |
| GET | `/reports/metrics/catalogue` | `ALL_ROLES` | `—` |
| GET | `/reports/metrics/{key}` | `ALL_ROLES` | `—` |
| GET | `/reports/metrics` | `ALL_ROLES` | `—` |
| GET | `/reports/joiners` | `WORKFORCE_REPORT_ROLES` | `—` |
| GET | `/reports/leavers` | `WORKFORCE_REPORT_ROLES` | `—` |
| GET | `/reports/attrition` | `WORKFORCE_REPORT_ROLES` | `—` |
| GET | `/reports/payroll-summary` | `REPORTS_ROLES` | `—` |
| GET | `/reports/payroll` | `REPORTS_ROLES` | `—` |

## requisitions — 4 routes (models: user)
_Suites: `talent_test_suite, smoke_test_phase2`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/requisitions/` | `ADMIN_ROLES` | `list[RequisitionOut]` |
| POST | `/requisitions/` | `ADMIN_ROLES` | `RequisitionOut` |
| GET | `/requisitions/{requisition_id}` | `ADMIN_ROLES` | `RequisitionOut` |
| PUT | `/requisitions/{requisition_id}` | `ADMIN_ROLES` | `RequisitionOut` |

## scheduling — 24 routes (models: scheduling, time_attendance, user)
_Suites: `scheduling_test_suite, smoke_test_phases_3_7`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/scheduling/shift-templates` | `ALL_ROLES` | `list[ShiftTemplateOut]` |
| POST | `/scheduling/shift-templates` | `ADMIN_ROLES` | `ShiftTemplateOut` |
| PUT | `/scheduling/shift-templates/{template_id}` | `ADMIN_ROLES` | `ShiftTemplateOut` |
| GET | `/scheduling/roster` | `WORKFORCE_ROLES` | `list[RosterEntryOut]` |
| GET | `/scheduling/roster/{entry_id}` | `WORKFORCE_ROLES` | `RosterEntryOut` |
| POST | `/scheduling/roster` | `ADMIN_ROLES` | `RosterEntryOut` |
| POST | `/scheduling/roster/generate` | `ADMIN_ROLES` | `list[RosterEntryOut]` |
| PUT | `/scheduling/roster/{entry_id}` | `ADMIN_ROLES` | `RosterEntryOut` |
| POST | `/scheduling/rosters/generate` | `MANAGER_ROLES` | `RosterGenerateResponse` |
| GET | `/scheduling/availability` | `WORKFORCE_ROLES` | `AvailabilityResponse` |
| GET | `/scheduling/rosters/draft/{draft_id}` | `MANAGER_ROLES` | `RosterDraftOut` |
| POST | `/scheduling/rosters/draft/{draft_id}/adjust` | `MANAGER_ROLES` | `AdjustmentResponse` |
| POST | `/scheduling/rosters/publish` | `MANAGER_ROLES` | `RosterVersionOut` |
| GET | `/scheduling/rosters/versions` | `WORKFORCE_ROLES` | `dict` |
| GET | `/scheduling/rosters/versions/{version_id}` | `WORKFORCE_ROLES` | `RosterVersionDetailOut` |
| GET | `/scheduling/rosters/versions/{version_id}/compare` | `WORKFORCE_ROLES` | `VersionCompareResponse` |
| POST | `/scheduling/rosters/versions/{version_id}/draft` | `MANAGER_ROLES` | `CreateDraftFromVersionResponse` |
| GET | `/scheduling/swaps` | `WORKFORCE_ROLES` | `list[SwapOut]` |
| POST | `/scheduling/swaps` | `WORKFORCE_ROLES` | `SwapOut` |
| POST | `/scheduling/swaps/{swap_id}/approve` | `MANAGER_ROLES` | `SwapOut` |
| POST | `/scheduling/swaps/{swap_id}/reject` | `MANAGER_ROLES` | `SwapOut` |
| GET | `/scheduling/rosters/{version_id}/attendance` | `WORKFORCE_ROLES` | `RosterAttendanceResponse` |
| POST | `/scheduling/rosters/{version_id}/attendance/auto-create` | `MANAGER_ROLES` | `AutoCreateAttendanceResponse` |
| GET | `/scheduling/rosters/{version_id}/attendance/deviations` | `WORKFORCE_ROLES` | `DeviationsResponse` |

## time_attendance — 20 routes (models: time_attendance, user)
_Suites: `time_corrections_test_suite, payroll_pipeline_test_suite, smoke_test_phases_3_7`._

| Method | Route | Auth | Response |
|---|---|---|---|
| GET | `/time/entries` | `WORKFORCE_ROLES` | `list[TimeEntryOut]` |
| GET | `/time/entries/{entry_id}` | `WORKFORCE_ROLES` | `TimeEntryOut` |
| POST | `/time/clock-in` | `WORKFORCE_ROLES` | `TimeEntryOut` |
| POST | `/time/clock-out` | `WORKFORCE_ROLES` | `TimeEntryOut` |
| GET | `/time/today` | `WORKFORCE_ROLES` | `—` |
| POST | `/time/entries` | `ADMIN_ROLES` | `TimeEntryOut` |
| PUT | `/time/entries/{entry_id}` | `ADMIN_ROLES` | `TimeEntryOut` |
| DELETE | `/time/entries/{entry_id}` | `ADMIN_ROLES` | `—` |
| GET | `/time/timesheets` | `WORKFORCE_ROLES` | `list[TimesheetOut]` |
| GET | `/time/timesheets/{timesheet_id}` | `WORKFORCE_ROLES` | `TimesheetOut` |
| POST | `/time/timesheets/generate` | `ADMIN_ROLES` | `TimesheetOut` |
| POST | `/time/timesheets/{timesheet_id}/submit` | `WORKFORCE_ROLES` | `TimesheetOut` |
| POST | `/time/timesheets/{timesheet_id}/approve` | `MANAGER_ROLES` | `TimesheetOut` |
| POST | `/time/corrections` | `WORKFORCE_ROLES` | `TimeCorrectionOut` |
| GET | `/time/corrections` | `WORKFORCE_ROLES` | `list[TimeCorrectionOut]` |
| POST | `/time/corrections/{correction_id}/approve` | `MANAGER_ROLES` | `TimeCorrectionOut` |
| POST | `/time/corrections/{correction_id}/reject` | `MANAGER_ROLES` | `TimeCorrectionOut` |
| POST | `/time/period-locks/lock` | `ADMIN_ROLES` | `PeriodLockOut` |
| POST | `/time/period-locks/reopen` | `ADMIN_ROLES` | `PeriodLockOut` |
| GET | `/time/period-locks/status` | `WORKFORCE_ROLES` | `PeriodStatusOut` |
