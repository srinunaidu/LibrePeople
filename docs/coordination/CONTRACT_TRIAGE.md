# Contract Triage — SUP-02

**Date:** 2026-10-23  **Owner:** super (Release Manager)

Triages the 202 endpoints that the application served but the contract did not
declare (see `contracts/openapi/_undeclared.md` before this change). Each endpoint
is now declared in the owning lane's fragment with `x-lifecycle: planned`, pending
owning-lane review and promotion to `released` with test evidence.

## Decision legend

- **Declare (planned)** — endpoint served; declared in the owning fragment as `planned`.
- **Promote to released** — endpoint served and stable; promoted to `released`.
- **Delete** — dead code; route removed.

## Summary by domain

| Domain (prefix) | Endpoints | Owner lane | Decision |
|---|---:|---|---|
| `applications` | 4 | platform-security | Declare (planned) |
| `auth` | 2 | platform-security | Declare (planned) |
| `benefits` | 9 | workforce-core | Declare (planned) |
| `candidates` | 4 | workforce-core | Declare (planned) |
| `compliance` | 13 | payroll-rules | Declare (planned) |
| `core-hr` | 13 | workforce-core | Declare (planned) |
| `data-quality` | 3 | qa-validation | Declare (planned) |
| `departments` | 3 | workforce-core | Declare (planned) |
| `employees` | 1 | workforce-core | Declare (planned) |
| `ess` | 21 | workforce-core | Declare (planned) |
| `forecasting` | 1 | planning | Declare (planned) |
| `jobs` | 3 | workforce-core | Declare (planned) |
| `learning` | 12 | workforce-core | Declare (planned) |
| `leave` | 3 | workforce-core | Declare (planned) |
| `offboarding` | 11 | workforce-core | Declare (planned) |
| `offers` | 7 | workforce-core | Declare (planned) |
| `onboarding` | 8 | onboarding-config | Declare (planned) |
| `onboarding-portal` | 23 | onboarding-config | Declare (planned) |
| `payroll` | 8 | payroll-rules | Declare (planned) |
| `performance` | 15 | workforce-core | Declare (planned) |
| `platform` | 12 | platform-security | Declare (planned) |
| `reports` | 9 | payroll-rules | Declare (planned) |
| `requisitions` | 4 | workforce-core | Declare (planned) |
| `scheduling` | 6 | planning | Declare (planned) |
| `time` | 7 | workforce-core | Declare (planned) |
| **Total** | **202** | | |

## Full triage table

| # | Method | Endpoint | Owner lane | Decision | Date |
|---:|---|---|---|---|---|
| 1 | GET | `/applications` | platform-security | Declare (planned) | 2026-10-23 |
| 2 | POST | `/applications` | platform-security | Declare (planned) | 2026-10-23 |
| 3 | GET | `/applications/{application_id}` | platform-security | Declare (planned) | 2026-10-23 |
| 4 | PUT | `/applications/{application_id}` | platform-security | Declare (planned) | 2026-10-23 |
| 5 | GET | `/auth/mfa/status` | platform-security | Declare (planned) | 2026-10-23 |
| 6 | POST | `/auth/register` | platform-security | Declare (planned) | 2026-10-23 |
| 7 | GET | `/benefits/benefit-enrollments` | workforce-core | Declare (planned) | 2026-10-23 |
| 8 | POST | `/benefits/benefit-enrollments` | workforce-core | Declare (planned) | 2026-10-23 |
| 9 | GET | `/benefits/benefit-plans` | workforce-core | Declare (planned) | 2026-10-23 |
| 10 | POST | `/benefits/benefit-plans` | workforce-core | Declare (planned) | 2026-10-23 |
| 11 | GET | `/benefits/leaves-of-absence` | workforce-core | Declare (planned) | 2026-10-23 |
| 12 | POST | `/benefits/leaves-of-absence` | workforce-core | Declare (planned) | 2026-10-23 |
| 13 | PUT | `/benefits/leaves-of-absence/{loa_id}/approve` | workforce-core | Declare (planned) | 2026-10-23 |
| 14 | GET | `/benefits/life-events` | workforce-core | Declare (planned) | 2026-10-23 |
| 15 | POST | `/benefits/life-events` | workforce-core | Declare (planned) | 2026-10-23 |
| 16 | GET | `/candidates` | workforce-core | Declare (planned) | 2026-10-23 |
| 17 | POST | `/candidates` | workforce-core | Declare (planned) | 2026-10-23 |
| 18 | GET | `/candidates/{candidate_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 19 | PUT | `/candidates/{candidate_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 20 | GET | `/compliance/compliance-rules` | payroll-rules | Declare (planned) | 2026-10-23 |
| 21 | POST | `/compliance/compliance-rules` | payroll-rules | Declare (planned) | 2026-10-23 |
| 22 | GET | `/compliance/compliance-violations` | payroll-rules | Declare (planned) | 2026-10-23 |
| 23 | POST | `/compliance/compliance-violations` | payroll-rules | Declare (planned) | 2026-10-23 |
| 24 | PUT | `/compliance/compliance-violations/{violation_id}/resolve` | payroll-rules | Declare (planned) | 2026-10-23 |
| 25 | GET | `/compliance/headcount-plans` | payroll-rules | Declare (planned) | 2026-10-23 |
| 26 | POST | `/compliance/headcount-plans` | payroll-rules | Declare (planned) | 2026-10-23 |
| 27 | GET | `/compliance/report-definitions` | payroll-rules | Declare (planned) | 2026-10-23 |
| 28 | POST | `/compliance/report-definitions` | payroll-rules | Declare (planned) | 2026-10-23 |
| 29 | GET | `/compliance/saved-reports` | payroll-rules | Declare (planned) | 2026-10-23 |
| 30 | POST | `/compliance/saved-reports` | payroll-rules | Declare (planned) | 2026-10-23 |
| 31 | GET | `/compliance/scenarios` | payroll-rules | Declare (planned) | 2026-10-23 |
| 32 | POST | `/compliance/scenarios` | payroll-rules | Declare (planned) | 2026-10-23 |
| 33 | GET | `/core-hr/cases` | workforce-core | Declare (planned) | 2026-10-23 |
| 34 | POST | `/core-hr/cases` | workforce-core | Declare (planned) | 2026-10-23 |
| 35 | PUT | `/core-hr/cases/{case_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 36 | GET | `/core-hr/cases/{case_id}/comments` | workforce-core | Declare (planned) | 2026-10-23 |
| 37 | POST | `/core-hr/cases/{case_id}/comments` | workforce-core | Declare (planned) | 2026-10-23 |
| 38 | GET | `/core-hr/cost-centers` | workforce-core | Declare (planned) | 2026-10-23 |
| 39 | POST | `/core-hr/cost-centers` | workforce-core | Declare (planned) | 2026-10-23 |
| 40 | GET | `/core-hr/employee-documents` | workforce-core | Declare (planned) | 2026-10-23 |
| 41 | POST | `/core-hr/employee-documents` | workforce-core | Declare (planned) | 2026-10-23 |
| 42 | GET | `/core-hr/locations` | workforce-core | Declare (planned) | 2026-10-23 |
| 43 | POST | `/core-hr/locations` | workforce-core | Declare (planned) | 2026-10-23 |
| 44 | GET | `/core-hr/positions` | workforce-core | Declare (planned) | 2026-10-23 |
| 45 | POST | `/core-hr/positions` | workforce-core | Declare (planned) | 2026-10-23 |
| 46 | GET | `/data-quality/checks` | qa-validation | Declare (planned) | 2026-10-23 |
| 47 | GET | `/data-quality/issues` | qa-validation | Declare (planned) | 2026-10-23 |
| 48 | POST | `/data-quality/scan` | qa-validation | Declare (planned) | 2026-10-23 |
| 49 | GET | `/departments` | workforce-core | Declare (planned) | 2026-10-23 |
| 50 | POST | `/departments` | workforce-core | Declare (planned) | 2026-10-23 |
| 51 | GET | `/departments/{department_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 52 | PUT | `/employees/{employee_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 53 | GET | `/ess/announcements` | workforce-core | Declare (planned) | 2026-10-23 |
| 54 | POST | `/ess/announcements` | workforce-core | Declare (planned) | 2026-10-23 |
| 55 | PUT | `/ess/announcements/{announcement_id}/publish` | workforce-core | Declare (planned) | 2026-10-23 |
| 56 | GET | `/ess/compliance-checks` | workforce-core | Declare (planned) | 2026-10-23 |
| 57 | POST | `/ess/compliance-checks/run` | workforce-core | Declare (planned) | 2026-10-23 |
| 58 | GET | `/ess/continuous-feedback` | workforce-core | Declare (planned) | 2026-10-23 |
| 59 | POST | `/ess/continuous-feedback` | workforce-core | Declare (planned) | 2026-10-23 |
| 60 | GET | `/ess/directory` | workforce-core | Declare (planned) | 2026-10-23 |
| 61 | POST | `/ess/directory/sync` | workforce-core | Declare (planned) | 2026-10-23 |
| 62 | GET | `/ess/employee-files` | workforce-core | Declare (planned) | 2026-10-23 |
| 63 | POST | `/ess/employee-files` | workforce-core | Declare (planned) | 2026-10-23 |
| 64 | POST | `/ess/ess/profile` | workforce-core | Declare (planned) | 2026-10-23 |
| 65 | GET | `/ess/ess/profile/{employee_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 66 | PUT | `/ess/ess/profile/{employee_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 67 | GET | `/ess/goal-alignments` | workforce-core | Declare (planned) | 2026-10-23 |
| 68 | POST | `/ess/goal-alignments` | workforce-core | Declare (planned) | 2026-10-23 |
| 69 | GET | `/ess/notifications` | workforce-core | Declare (planned) | 2026-10-23 |
| 70 | POST | `/ess/notifications` | workforce-core | Declare (planned) | 2026-10-23 |
| 71 | PUT | `/ess/notifications/{notification_id}/read` | workforce-core | Declare (planned) | 2026-10-23 |
| 72 | GET | `/ess/org-chart` | workforce-core | Declare (planned) | 2026-10-23 |
| 73 | POST | `/ess/org-chart/rebuild` | workforce-core | Declare (planned) | 2026-10-23 |
| 74 | GET | `/forecasting/runs/{run_id}/results` | planning | Declare (planned) | 2026-10-23 |
| 75 | GET | `/jobs` | workforce-core | Declare (planned) | 2026-10-23 |
| 76 | POST | `/jobs` | workforce-core | Declare (planned) | 2026-10-23 |
| 77 | GET | `/jobs/{job_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 78 | GET | `/learning/certifications` | workforce-core | Declare (planned) | 2026-10-23 |
| 79 | POST | `/learning/certifications` | workforce-core | Declare (planned) | 2026-10-23 |
| 80 | GET | `/learning/course-enrollments` | workforce-core | Declare (planned) | 2026-10-23 |
| 81 | POST | `/learning/course-enrollments` | workforce-core | Declare (planned) | 2026-10-23 |
| 82 | PUT | `/learning/course-enrollments/{enrollment_id}/complete` | workforce-core | Declare (planned) | 2026-10-23 |
| 83 | GET | `/learning/courses` | workforce-core | Declare (planned) | 2026-10-23 |
| 84 | POST | `/learning/courses` | workforce-core | Declare (planned) | 2026-10-23 |
| 85 | GET | `/learning/succession-plans` | workforce-core | Declare (planned) | 2026-10-23 |
| 86 | POST | `/learning/succession-plans` | workforce-core | Declare (planned) | 2026-10-23 |
| 87 | POST | `/learning/talent-pool-members` | workforce-core | Declare (planned) | 2026-10-23 |
| 88 | GET | `/learning/talent-pools` | workforce-core | Declare (planned) | 2026-10-23 |
| 89 | POST | `/learning/talent-pools` | workforce-core | Declare (planned) | 2026-10-23 |
| 90 | POST | `/leave/entitlements` | workforce-core | Declare (planned) | 2026-10-23 |
| 91 | POST | `/leave/types` | workforce-core | Declare (planned) | 2026-10-23 |
| 92 | PUT | `/leave/types/{leave_type_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 93 | PUT | `/offboarding/items/{item_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 94 | GET | `/offboarding/tasks` | workforce-core | Declare (planned) | 2026-10-23 |
| 95 | POST | `/offboarding/tasks` | workforce-core | Declare (planned) | 2026-10-23 |
| 96 | PUT | `/offboarding/tasks/{task_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 97 | GET | `/offboarding/terminations` | workforce-core | Declare (planned) | 2026-10-23 |
| 98 | POST | `/offboarding/terminations` | workforce-core | Declare (planned) | 2026-10-23 |
| 99 | GET | `/offboarding/terminations/{termination_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 100 | PUT | `/offboarding/terminations/{termination_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 101 | POST | `/offboarding/terminations/{termination_id}/cancel` | workforce-core | Declare (planned) | 2026-10-23 |
| 102 | POST | `/offboarding/terminations/{termination_id}/complete` | workforce-core | Declare (planned) | 2026-10-23 |
| 103 | GET | `/offboarding/terminations/{termination_id}/progress` | workforce-core | Declare (planned) | 2026-10-23 |
| 104 | GET | `/offers` | workforce-core | Declare (planned) | 2026-10-23 |
| 105 | POST | `/offers` | workforce-core | Declare (planned) | 2026-10-23 |
| 106 | GET | `/offers/{offer_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 107 | PUT | `/offers/{offer_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 108 | POST | `/offers/{offer_id}/accept` | workforce-core | Declare (planned) | 2026-10-23 |
| 109 | POST | `/offers/{offer_id}/hire` | workforce-core | Declare (planned) | 2026-10-23 |
| 110 | POST | `/offers/{offer_id}/letter` | workforce-core | Declare (planned) | 2026-10-23 |
| 111 | GET | `/onboarding-portal/clients` | onboarding-config | Declare (planned) | 2026-10-23 |
| 112 | POST | `/onboarding-portal/clients` | onboarding-config | Declare (planned) | 2026-10-23 |
| 113 | GET | `/onboarding-portal/clients/by-slug/{slug}` | onboarding-config | Declare (planned) | 2026-10-23 |
| 114 | DELETE | `/onboarding-portal/clients/{client_id}` | onboarding-config | Declare (planned) | 2026-10-23 |
| 115 | GET | `/onboarding-portal/clients/{client_id}` | onboarding-config | Declare (planned) | 2026-10-23 |
| 116 | PUT | `/onboarding-portal/clients/{client_id}` | onboarding-config | Declare (planned) | 2026-10-23 |
| 117 | GET | `/onboarding-portal/clients/{client_id}/feature-flags` | onboarding-config | Declare (planned) | 2026-10-23 |
| 118 | PUT | `/onboarding-portal/clients/{client_id}/feature-flags/{key}` | onboarding-config | Declare (planned) | 2026-10-23 |
| 119 | GET | `/onboarding-portal/clients/{client_id}/integrations` | onboarding-config | Declare (planned) | 2026-10-23 |
| 120 | POST | `/onboarding-portal/clients/{client_id}/integrations` | onboarding-config | Declare (planned) | 2026-10-23 |
| 121 | DELETE | `/onboarding-portal/clients/{client_id}/integrations/{integration_id}` | onboarding-config | Declare (planned) | 2026-10-23 |
| 122 | PUT | `/onboarding-portal/clients/{client_id}/integrations/{integration_id}` | onboarding-config | Declare (planned) | 2026-10-23 |
| 123 | POST | `/onboarding-portal/clients/{client_id}/integrations/{integration_id}/test` | onboarding-config | Declare (planned) | 2026-10-23 |
| 124 | GET | `/onboarding-portal/clients/{client_id}/migrations` | onboarding-config | Declare (planned) | 2026-10-23 |
| 125 | POST | `/onboarding-portal/clients/{client_id}/migrations` | onboarding-config | Declare (planned) | 2026-10-23 |
| 126 | POST | `/onboarding-portal/clients/{client_id}/migrations/{job_id}/cancel` | onboarding-config | Declare (planned) | 2026-10-23 |
| 127 | POST | `/onboarding-portal/clients/{client_id}/migrations/{job_id}/run` | onboarding-config | Declare (planned) | 2026-10-23 |
| 128 | GET | `/onboarding-portal/clients/{client_id}/onboarding` | onboarding-config | Declare (planned) | 2026-10-23 |
| 129 | POST | `/onboarding-portal/clients/{client_id}/onboarding/steps` | onboarding-config | Declare (planned) | 2026-10-23 |
| 130 | POST | `/onboarding-portal/clients/{client_id}/onboarding/steps/{step_id}/complete` | onboarding-config | Declare (planned) | 2026-10-23 |
| 131 | GET | `/onboarding-portal/clients/{client_id}/settings` | onboarding-config | Declare (planned) | 2026-10-23 |
| 132 | PUT | `/onboarding-portal/clients/{client_id}/settings/{key}` | onboarding-config | Declare (planned) | 2026-10-23 |
| 133 | GET | `/onboarding-portal/docs/migration-api` | onboarding-config | Declare (planned) | 2026-10-23 |
| 134 | PUT | `/onboarding/documents/{document_id}` | onboarding-config | Declare (planned) | 2026-10-23 |
| 135 | POST | `/onboarding/tasks` | onboarding-config | Declare (planned) | 2026-10-23 |
| 136 | PUT | `/onboarding/tasks/{task_id}` | onboarding-config | Declare (planned) | 2026-10-23 |
| 137 | POST | `/onboarding/{employee_id}/checklist` | onboarding-config | Declare (planned) | 2026-10-23 |
| 138 | GET | `/onboarding/{employee_id}/documents` | onboarding-config | Declare (planned) | 2026-10-23 |
| 139 | POST | `/onboarding/{employee_id}/documents` | onboarding-config | Declare (planned) | 2026-10-23 |
| 140 | GET | `/onboarding/{employee_id}/summary` | onboarding-config | Declare (planned) | 2026-10-23 |
| 141 | GET | `/onboarding/{employee_id}/tasks` | onboarding-config | Declare (planned) | 2026-10-23 |
| 142 | GET | `/payroll/components` | payroll-rules | Declare (planned) | 2026-10-23 |
| 143 | POST | `/payroll/components` | payroll-rules | Declare (planned) | 2026-10-23 |
| 144 | POST | `/payroll/pay-profiles` | payroll-rules | Declare (planned) | 2026-10-23 |
| 145 | GET | `/payroll/pay-profiles/{employee_id}` | payroll-rules | Declare (planned) | 2026-10-23 |
| 146 | POST | `/payroll/payslips` | payroll-rules | Declare (planned) | 2026-10-23 |
| 147 | GET | `/payroll/periods` | payroll-rules | Declare (planned) | 2026-10-23 |
| 148 | POST | `/payroll/periods` | payroll-rules | Declare (planned) | 2026-10-23 |
| 149 | POST | `/payroll/runs/{run_id}/finalize` | payroll-rules | Declare (planned) | 2026-10-23 |
| 150 | GET | `/performance/compensation-bands` | workforce-core | Declare (planned) | 2026-10-23 |
| 151 | POST | `/performance/compensation-bands` | workforce-core | Declare (planned) | 2026-10-23 |
| 152 | GET | `/performance/feedback` | workforce-core | Declare (planned) | 2026-10-23 |
| 153 | POST | `/performance/feedback` | workforce-core | Declare (planned) | 2026-10-23 |
| 154 | GET | `/performance/goals` | workforce-core | Declare (planned) | 2026-10-23 |
| 155 | POST | `/performance/goals` | workforce-core | Declare (planned) | 2026-10-23 |
| 156 | PUT | `/performance/goals/{goal_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 157 | GET | `/performance/merit-allocations` | workforce-core | Declare (planned) | 2026-10-23 |
| 158 | POST | `/performance/merit-allocations` | workforce-core | Declare (planned) | 2026-10-23 |
| 159 | GET | `/performance/merit-cycles` | workforce-core | Declare (planned) | 2026-10-23 |
| 160 | POST | `/performance/merit-cycles` | workforce-core | Declare (planned) | 2026-10-23 |
| 161 | GET | `/performance/reviews` | workforce-core | Declare (planned) | 2026-10-23 |
| 162 | POST | `/performance/reviews` | workforce-core | Declare (planned) | 2026-10-23 |
| 163 | PUT | `/performance/reviews/{review_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 164 | POST | `/performance/reviews/{review_id}/finalize` | workforce-core | Declare (planned) | 2026-10-23 |
| 165 | GET | `/platform/background-checks` | platform-security | Declare (planned) | 2026-10-23 |
| 166 | POST | `/platform/background-checks` | platform-security | Declare (planned) | 2026-10-23 |
| 167 | PUT | `/platform/background-checks/{check_id}/complete` | platform-security | Declare (planned) | 2026-10-23 |
| 168 | GET | `/platform/e-signatures` | platform-security | Declare (planned) | 2026-10-23 |
| 169 | POST | `/platform/e-signatures` | platform-security | Declare (planned) | 2026-10-23 |
| 170 | PUT | `/platform/e-signatures/{sig_id}/sign` | platform-security | Declare (planned) | 2026-10-23 |
| 171 | GET | `/platform/sso-configs` | platform-security | Declare (planned) | 2026-10-23 |
| 172 | POST | `/platform/sso-configs` | platform-security | Declare (planned) | 2026-10-23 |
| 173 | GET | `/platform/webhooks` | platform-security | Declare (planned) | 2026-10-23 |
| 174 | POST | `/platform/webhooks` | platform-security | Declare (planned) | 2026-10-23 |
| 175 | POST | `/platform/webhooks/{webhook_id}/deliver` | platform-security | Declare (planned) | 2026-10-23 |
| 176 | GET | `/platform/webhooks/{webhook_id}/deliveries` | platform-security | Declare (planned) | 2026-10-23 |
| 177 | GET | `/reports/attendance` | payroll-rules | Declare (planned) | 2026-10-23 |
| 178 | GET | `/reports/audit` | payroll-rules | Declare (planned) | 2026-10-23 |
| 179 | GET | `/reports/dashboard` | payroll-rules | Declare (planned) | 2026-10-23 |
| 180 | GET | `/reports/headcount` | payroll-rules | Declare (planned) | 2026-10-23 |
| 181 | GET | `/reports/labor-cost` | payroll-rules | Declare (planned) | 2026-10-23 |
| 182 | GET | `/reports/leave` | payroll-rules | Declare (planned) | 2026-10-23 |
| 183 | GET | `/reports/metrics` | payroll-rules | Declare (planned) | 2026-10-23 |
| 184 | GET | `/reports/metrics/catalogue` | payroll-rules | Declare (planned) | 2026-10-23 |
| 185 | GET | `/reports/metrics/{key}` | payroll-rules | Declare (planned) | 2026-10-23 |
| 186 | GET | `/requisitions` | workforce-core | Declare (planned) | 2026-10-23 |
| 187 | POST | `/requisitions` | workforce-core | Declare (planned) | 2026-10-23 |
| 188 | GET | `/requisitions/{requisition_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 189 | PUT | `/requisitions/{requisition_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 190 | POST | `/scheduling/roster` | planning | Declare (planned) | 2026-10-23 |
| 191 | GET | `/scheduling/roster/{entry_id}` | planning | Declare (planned) | 2026-10-23 |
| 192 | PUT | `/scheduling/roster/{entry_id}` | planning | Declare (planned) | 2026-10-23 |
| 193 | PUT | `/scheduling/shift-templates/{template_id}` | planning | Declare (planned) | 2026-10-23 |
| 194 | GET | `/scheduling/swaps` | planning | Declare (planned) | 2026-10-23 |
| 195 | POST | `/scheduling/swaps/{swap_id}/reject` | planning | Declare (planned) | 2026-10-23 |
| 196 | POST | `/time/entries` | workforce-core | Declare (planned) | 2026-10-23 |
| 197 | DELETE | `/time/entries/{entry_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 198 | GET | `/time/entries/{entry_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 199 | PUT | `/time/entries/{entry_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 200 | POST | `/time/timesheets/generate` | workforce-core | Declare (planned) | 2026-10-23 |
| 201 | GET | `/time/timesheets/{timesheet_id}` | workforce-core | Declare (planned) | 2026-10-23 |
| 202 | GET | `/time/today` | workforce-core | Declare (planned) | 2026-10-23 |

## Import fragment (DEC-003)

- Entity-based routes under `/import-export/*` are the synchronous import and were
  promoted to `x-lifecycle: released` (DI-01/DI-03 closed).
- Upload-based routes under `/imports/*` remain `x-lifecycle: planned` for the
  asynchronous, job-backed import.

## Import error codes

- `ledger_reduction_refused` and `ledger_no_movement` are in `contracts/errors.md`
  (§3.5) and the row-level import codes are documented in §3.10 and in
  `contracts/openapi/_components.yaml` (`ImportRowErrorCode`).
