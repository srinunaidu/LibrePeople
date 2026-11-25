# Karmathy — API Contract

Base path: `/api/v1` · Auth: `Authorization: Bearer <JWT>` (except `/auth/*`, `/health`).

Legend: **A** = SuperAdmin/HR · **U** = any authenticated user.

## Auth
| Method | Path | Access | Notes |
|--------|------|--------|-------|
| POST | `/auth/login` | — | JSON `{username, password}` → `{access_token, token_type, role, username}` |
| POST | `/auth/register` | — | JSON `UserCreate` → `UserOut` |

## Employees (Phase 1)
| Method | Path | Access |
|--------|------|--------|
| GET | `/employees/` | U |
| POST | `/employees/` | A |
| GET | `/employees/{id}` | U |
| PUT | `/employees/{id}` | A |

## Departments / Jobs (Phase 1)
| Method | Path | Access |
|--------|------|--------|
| GET/POST | `/departments/` | U / A |
| GET/POST | `/jobs/` | U / A |

## Requisitions (Phase 2)
| Method | Path | Access |
|--------|------|--------|
| GET | `/requisitions/?status=` | U |
| POST | `/requisitions/` | A |
| GET/PUT | `/requisitions/{id}` | U / A |

## Candidates (Phase 2)
| Method | Path | Access |
|--------|------|--------|
| GET | `/candidates/?status=` | U |
| POST | `/candidates/` | A |
| GET/PUT | `/candidates/{id}` | U / A |

## Applications (Phase 2)
| Method | Path | Access |
|--------|------|--------|
| GET | `/applications/?requisition_id=&candidate_id=` | U |
| POST | `/applications/` | A |
| GET/PUT | `/applications/{id}` | U / A |

## Offers (Phase 2)
| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/offers/?status=` | U | |
| POST | `/offers/` | A | |
| GET/PUT | `/offers/{id}` | U / A | |
| POST | `/offers/{id}/letter` | A | Generates PDF, stores it, sets status `Sent` |
| POST | `/offers/{id}/accept` | A | Sets offer/application/candidate to Offer/Accepted |
| POST | `/offers/{id}/hire` | A | Body `HireRequest` → creates Employee + onboarding checklist (`HireResult`) |

## Onboarding (Phase 2)
| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/onboarding/{employee_id}/summary` | U | progress % + doc count |
| POST | `/onboarding/{employee_id}/checklist` | A | create default checklist |
| GET | `/onboarding/{employee_id}/tasks` | U | |
| POST | `/onboarding/tasks` | A | |
| PUT | `/onboarding/tasks/{task_id}` | A | |
| GET | `/onboarding/{employee_id}/documents` | U | |
| POST | `/onboarding/{employee_id}/documents` | A | multipart: `document_type`, `file` |
| PUT | `/onboarding/documents/{document_id}` | A | verify/reject |

## Time & Attendance (Phase 3)
| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/time/entries?employee_id=&start=&end=` | U | |
| POST | `/time/clock-in` | U | body `{employee_id, work_date?, source?, notes?}` |
| POST | `/time/clock-out` | U | body `{employee_id, notes?}` |
| GET | `/time/today` | U | attendance summary for today |
| POST | `/time/entries` | A | manual entry |
| PUT | `/time/entries/{id}` | A | |
| DELETE | `/time/entries/{id}` | A | |
| GET | `/time/timesheets?employee_id=` | U | |
| POST | `/time/timesheets/generate` | A | body `{employee_id, period_start, period_end}` |
| POST | `/time/timesheets/{id}/submit` | U | |
| POST | `/time/timesheets/{id}/approve` | A | |

## Scheduling (Phase 4)
| Method | Path | Access |
|--------|------|--------|
| GET | `/scheduling/shift-templates?active_only=` | U |
| POST | `/scheduling/shift-templates` | A |
| PUT | `/scheduling/shift-templates/{id}` | A |
| GET | `/scheduling/roster?employee_id=&start=&end=` | U |
| POST | `/scheduling/roster` | A |
| POST | `/scheduling/roster/generate` | A |
| PUT | `/scheduling/roster/{id}` | A |
| GET | `/scheduling/swaps?status=` | U |
| POST | `/scheduling/swaps` | U |
| POST | `/scheduling/swaps/{id}/approve` | A |
| POST | `/scheduling/swaps/{id}/reject` | A |

## Leave (Phase 5)
| Method | Path | Access |
|--------|------|--------|
| GET | `/leave/types?active_only=` | U |
| POST | `/leave/types` | A |
| PUT | `/leave/types/{id}` | A |
| GET | `/leave/balances?employee_id=&year=` | U |
| POST | `/leave/entitlements` | A |
| GET | `/leave/requests?employee_id=&status=` | U |
| POST | `/leave/requests` | U |
| POST | `/leave/requests/{id}/approve` | A |
| POST | `/leave/requests/{id}/reject` | A |
| POST | `/leave/requests/{id}/cancel` | U |

## Offboarding (Phase 6)
| Method | Path | Access |
|--------|------|--------|
| GET | `/offboarding/tasks?active_only=` | U |
| POST | `/offboarding/tasks` | A |
| PUT | `/offboarding/tasks/{id}` | A |
| GET | `/offboarding/terminations?status=` | U |
| GET | `/offboarding/terminations/{id}` | U |
| POST | `/offboarding/terminations` | A |
| PUT | `/offboarding/terminations/{id}` | A |
| POST | `/offboarding/terminations/{id}/complete` | A |
| POST | `/offboarding/terminations/{id}/cancel` | A |
| GET | `/offboarding/terminations/{id}/progress` | U |
| PUT | `/offboarding/items/{id}` | A |

## Reports (Phase 7)
| Method | Path | Access |
|--------|------|--------|
| GET | `/reports/dashboard` | U |
| GET | `/reports/headcount` | U |
| GET | `/reports/leave` | U |
| GET | `/reports/labor-cost` | U |
| GET | `/reports/attendance?day=` | U |
| GET | `/reports/audit?limit=` | U |

## Status enums
- **Requisition**: Draft, Open, OnHold, Closed
- **Candidate / Application**: Applied, Screening, Interview, Offer, Hired, Rejected
- **Offer**: Draft, Sent, Accepted, Declined, Expired
- **Onboarding task**: Pending, InProgress, Completed
- **Onboarding document**: Pending, Verified, Rejected
- **Time entry**: Draft, Approved
- **Timesheet**: Draft, Submitted, Approved
- **Roster entry**: Scheduled, Confirmed, Absent, Cancelled
- **Shift swap**: Pending, Approved, Rejected
- **Leave request**: Pending, Approved, Rejected, Cancelled
- **Termination**: Initiated, In Progress, Completed, Cancelled
