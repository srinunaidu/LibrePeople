# Contract: Cross-tenant negative tests

**Feature ID:** karmathy-qa-07-cross-tenant
**Contract path:** spec/features/karmathy-qa-07-cross-tenant/contract.md
**Tier:** Tier 2 (new behavior, multiple files, tests required)

## Acceptance Criteria (numbered)

**AC-01** Create two tenants (Tenant A and Tenant B) with separate employees.
**AC-02** Tenant A cannot access Tenant B's employee records through any API endpoint (403/404).
**AC-03** Tenant A cannot access Tenant B's leave requests, payroll runs, timesheets, or any employee-scoped data.
**AC-04** Tenant A cannot access Tenant B's data through search, exports, reports, or files.
**AC-05** Tenant A cannot access Tenant B's data through background jobs.
**AC-06** Cross-tenant tests automated — run as part of CI test suite.
**AC-07** All cross-tenant tests produce pass/fail results; zero false positives.
**AC-08** Test results documented and verifiable.

## Test Plan

1. `cd /Users/srinivas/LLM/Workforce/Karmathy/backend && ci/run_backend_tests.sh` — must pass all cross-tenant negative tests.
2. The suite creates two separate SQLite databases (one per tenant) and two app instances, one per database, simulating the schema-per-customer tenancy model (docs/TARGET_ARCHITECTURE.md).
3. Each check prints `PASS` or `FAIL`; the suite exits non-zero on any failure.

## Scope confirmations

**Tenancy model:** The codebase has no `tenant_id` column; isolation is by separate database per customer. This suite validates that boundary: each tenant's database contains only its own data, and cross-tenant access via the API returns 404 (record not present in this database).

**Resources covered:** employees, leave requests and balances, payroll runs and pay profiles, roster entries and time entries, search, CSV exports, headcount/leave/labor-cost reports, stored files, background job queue.

## Open Decisions (for lead/human)

None. The contract is self-contained.
