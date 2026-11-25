# Reports Module — Karmathy HCM

**Version:** 0.1 (Draft)
**Last Updated:** 2026-10-21
**Owner:** Payroll & Rules Agent

---

## 1. Overview

The Reports module provides **operational** and **compliance** reports for payroll, workforce, and regulatory purposes. All reports are:
- **Audit-logged** — every generation recorded
- **Background jobs** — large reports run asynchronously
- **Exportable** — CSV (streaming) and PDF
- **Rule-pack aware** — compliance reports driven by verified rule packs

---

## 2. Report Categories

### 2.1 Operational Reports

| Report ID | Name | Description | Parameters |
|-----------|------|-------------|------------|
| `payroll_register` | Payroll Register | All payslips for a run with earnings/deductions breakdown | `pay_run_id` |
| `cost_centre_summary` | Cost Centre Summary | Gross/net/employer cost by department/cost centre | `period_start`, `period_end`, `group_by` |
| `tax_liability` | Tax Liability | Employee/employer tax by jurisdiction | `period_start`, `period_end`, `jurisdiction` |
| `social_insurance_summary` | Social Insurance Summary | EE/ER contributions by component | `period_start`, `period_end` |
| `leave_liability` | Leave Liability | Accrued but untaken leave by type | `as_of_date` |
| `overtime_analysis` | Overtime Analysis | Overtime hours and cost by employee/department | `period_start`, `period_end` |
| `headcount` | Headcount | Active employees by department/status | `as_of_date` |
| `turnover` | Turnover | Joiners/leavers by period | `period_start`, `period_end` |
| `absence` | Absence | Leave days taken by type/department | `period_start`, `period_end` |
| `labor_cost` | Labor Cost | Total compensation cost (gross + ER contributions) | `period_start`, `period_end` |

### 2.2 Compliance Reports

| Report ID | Name | Description | Rule Pack Dependency |
|-----------|------|-------------|---------------------|
| `working_time_violations` | Working-Time Violations | Employees exceeding weekly/daily limits, insufficient rest | `working_time_limits`, `overtime` thresholds |
| `pay_floor_breaches` | Pay-Floor Breaches | Employees below minimum wage | `thresholds.minimum_wage_amount/unit` |
| `expiring_eligibility` | Expiring Eligibility | Work visas, right-to-work docs expiring soon | — (document expiry) |
| `overdue_certifications` | Overdue Certifications | Mandatory training/certs past due | — (certification expiry) |
| `retention_status` | Retention Status | Documents past retention period | — (retention schedule) |
| `erasure_log` | Erasure Log | Data erasure requests and completion status | — (GDPR/CCPA) |
| `audit_chain_status` | Audit Chain Status | Hash chain verification of audit log | — (audit log integrity) |
| `statutory_filing_calendar` | Statutory Filing Calendar | Upcoming filing deadlines | `reporting_obligations` |

---

## 3. Report Execution

### 3.1 API Endpoints

```
GET  /reports/operational/{report_id}     # Synchronous (small reports)
POST /reports/operational/{report_id}     # Async job (large reports)
GET  /reports/compliance/{report_id}      # Synchronous
POST /reports/compliance/{report_id}      # Async job
GET  /reports/jobs/{job_id}               # Job status
GET  /reports/jobs/{job_id}/download      # Download result
```

### 3.2 Request Parameters

```json
{
  "period_start": "2026-01-01",
  "period_end": "2026-01-31",
  "jurisdiction": "IN",
  "department_id": 5,
  "format": "csv",  // or "pdf"
  "filters": { "employee_status": "Active" }
}
```

### 3.3 Response (Async)

```json
{
  "job_id": "uuid",
  "status": "queued",
  "created_at": "2026-10-21T10:00:00Z",
  "estimated_completion": "2026-10-21T10:02:00Z"
}
```

### 3.4 Job Status

| Status | Meaning |
|--------|---------|
| `queued` | Waiting for worker |
| `running` | Generating report |
| `completed` | Ready for download |
| `failed` | Error (check `error_message`) |

---

## 4. Export Formats

### 4.1 CSV (Streaming)

- **Memory efficient** — streams row by row
- **No headers in stream** — header row first, then data
- **Decimal as strings** — `"12345.67"` not `12345.67`
- **UTF-8** with BOM for Excel compatibility

### 4.2 PDF

- **Formatted** — tables, headers, footers
- **Watermark** — "Configurable Calculation — Rule Pack: {pack_id} v{version} ({status})"
- **Page numbers** — "Page X of Y"
- **Generated via** `weasyprint` or `reportlab`

### 4.3 File Naming

```
{report_id}_{period_start}_{period_end}_{timestamp}.{csv|pdf}
Example: payroll_register_2026-01-01_2026-01-31_20261021T100000Z.csv
```

---

## 5. Compliance Report Details

### 5.1 Working-Time Violations

**Source:** Rule pack `working_time_limits` and `overtime` thresholds.

**Checks:**
| Check | Threshold Source | Severity |
|-------|------------------|----------|
| Weekly hours > max | `working_time_limits.max_weekly_hours` | Block |
| Daily rest < min | `working_time_limits.min_daily_rest_hours` | Block |
| Consecutive days > max | `working_time_limits.max_consecutive_days` | Flag |
| Night hours > max | `working_time_limits.max_night_work_hours` | Block |
| Rest between shifts < min | `working_time_limits.min_rest_between_shifts_hours` | Block |
| Daily OT threshold exceeded | `overtime.daily_threshold_hours` | Flag |
| Weekly OT threshold exceeded | `overtime.weekly_threshold_hours` | Flag |
| Daily OT cap exceeded | `overtime.daily_cap_hours` | Block |

**Output:** Employee, date, rule_id, actual vs limit, severity.

### 5.2 Pay-Floor Breaches

**Source:** Rule pack `thresholds.minimum_wage_amount` and `minimum_wage_unit`.

**Calculation:**
- Convert employee gross for period to same unit as minimum wage
- Compare: `hourly_gross < minimum_wage` → breach

**Output:** Employee, period, gross, calculated hourly/daily/monthly, minimum wage, breach amount.

### 5.3 Statutory Filing Calendar

**Source:** Rule pack `reporting_obligations`.

**Fields:** `code`, `name`, `frequency`, `deadline_rule`, `authority`, `next_due_date`, `status` (upcoming/overdue/completed).

**Example:**
```json
{
  "code": "PF_MONTHLY",
  "name": "EPF Monthly Return",
  "frequency": "monthly",
  "deadline_rule": "15th of following month",
  "authority": "EPFO",
  "next_due_date": "2026-11-15",
  "status": "upcoming"
}
```

---

## 6. Reconciliation Report

**Special report** — runs automatically on every pay run completion.

### 6.1 Structure

See `backend/app/rules/reconciliation.py`:
- `PayRunReconciliation` — run-level totals and status
- `PayslipReconciliation` — per-payslip verification
- `ReconciliationLine` — per-line traceability

### 6.2 Verification

```python
recon = build_reconciliation(...)
ok = recon.verify_all()  # True/False
errors = recon.errors    # List of mismatch descriptions
```

### 6.3 Export

```python
csv_detail = export_reconciliation_csv(recon)      # Line-by-line
csv_summary = export_reconciliation_summary_csv(recon)  # Run-level
```

---

## 7. Audit Logging

Every report generation creates an audit log entry:

```json
{
  "event_type": "report.generated",
  "actor_id": 123,
  "resource_type": "Report",
  "resource_id": "payroll_register",
  "details": {
    "pay_run_id": 456,
    "format": "csv",
    "row_count": 150,
    "job_id": "uuid"
  }
}
```

---

## 8. Background Job Integration

### 8.1 Job Queue (Platform-Security)

Reports use the job queue from `backend/app/jobs/`:

```python
from app.jobs.queue import enqueue_job

job_id = enqueue_job(
    handler="generate_report",
    payload={
        "report_id": "payroll_register",
        "parameters": {"pay_run_id": 456, "format": "csv"},
        "requested_by": user_id,
    },
    priority="normal",
)
```

### 8.2 Job Handler

```python
# In backend/app/jobs/handlers.py
async def handle_generate_report(payload: dict):
    report_id = payload["report_id"]
    params = payload["parameters"]
    format = params.pop("format", "csv")

    # Generate
    if format == "csv":
        content = generate_csv_report(report_id, params)
    else:
        content = generate_pdf_report(report_id, params)

    # Store in object storage (OCI/local)
    file_id = storage.put(f"reports/{report_id}_{job_id}.{format}", content)

    # Update job record with file_id
    update_job_result(job_id, {"file_id": file_id, "status": "completed"})

    # Audit log
    record_audit(...)
```

---

## 9. Visibility & Access Control

| Role | Operational Reports | Compliance Reports | Reconciliation |
|------|---------------------|-------------------|----------------|
| SuperAdmin | ✅ All | ✅ All | ✅ All |
| PayrollAdmin | ✅ All | ✅ All | ✅ All |
| PayrollViewer | ✅ Read | ✅ Read | ✅ Read |
| Manager | ✅ Team only | ✅ Team only | ❌ |
| Employee | ❌ | ❌ | ❌ |

**Team-only** = filtered by `apply_visibility` on employee_id.

---

## 10. Scheduled Reports

### 10.1 Compliance Calendar

- Runs daily at 06:00 (configurable)
- Generates `statutory_filing_calendar` for next 30 days
- Creates notifications for `upcoming` (7 days) and `overdue` filings

### 10.2 Monthly Pack

- Runs 1st of month for prior month
- Generates: `payroll_register`, `cost_centre_summary`, `tax_liability`, `social_insurance_summary`
- Emails to PayrollAdmin distribution list

---

## 11. API Contracts

### 11.1 Report Definition (OpenAPI)

See `contracts/openapi/reports.yaml` (to be created).

### 11.2 Report Event

```yaml
# contracts/events/reports.yaml
events:
  report.generated:
    description: "A report was generated"
    payload:
      report_id: string
      format: string
      parameters: object
      row_count: integer
      job_id: string/null
```

---

## 12. Implementation Status

| Report | Backend | API | UI | Background Job | Tests |
|--------|---------|-----|----|----------------|-------|
| Payroll Register | ⏳ | ⏳ | ⏳ | ⏳ | ❌ |
| Cost Centre Summary | ⏳ | ⏳ | ⏳ | ⏳ | ❌ |
| Tax Liability | ⏳ | ⏳ | ⏳ | ⏳ | ❌ |
| Social Insurance Summary | ⏳ | ⏳ | ⏳ | ⏳ | ❌ |
| Leave Liability | ⏳ | ⏳ | ⏳ | ⏳ | ❌ |
| Overtime Analysis | ⏳ | ⏳ | ⏳ | ⏳ | ❌ |
| Working-Time Violations | ⏳ | ⏳ | ⏳ | ⏳ | ❌ |
| Pay-Floor Breaches | ⏳ | ⏳ | ⏳ | ⏳ | ❌ |
| Statutory Filing Calendar | ⏳ | ⏳ | ⏳ | ⏳ | ❌ |
| Reconciliation | ✅ | ⏳ | ⏳ | ⏳ | ✅ |

---

## 13. Dependencies

| Dependency | Provider | Status |
|------------|----------|--------|
| Workforce Core (leave, time, overtime) | Workforce Core agent | Not connected |
| Data Import (base data) | Data & Import agent | Schema ready |
| Platform Security (audit, jobs, encryption) | Platform & Security agent | Partial |
| Rule Packs (compliance thresholds) | Payroll & Rules agent | Schema ready |

---

## 14. Future Work

- [ ] Implement all operational reports with CSV/PDF export
- [ ] Implement compliance reports driven by rule pack
- [ ] Background job queue integration
- [ ] Scheduled report generation (cron-like)
- [ ] Report subscriptions (email/Slack)
- [ ] Custom report builder (drag-drop)
- [ ] Dashboard widgets from report data
- [ ] Statutory filing export templates per jurisdiction
- [ ] Audit chain verification report

---

## 15. References

- `docs/PAYROLL.md` — Payroll module overview
- `docs/RULE_PACKS.md` — Rule pack structure (drives compliance reports)
- `backend/app/rules/reconciliation.py` — Reconciliation structure
- `contracts/events/payroll_runs.yaml` — Pay run events
- `backend/app/crud/crud_reports.py` — Report CRUD (to be created)
- `agents/payroll-rules/STATE.md` — Current agent state