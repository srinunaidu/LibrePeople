# Known Test Failures (pre-existing, zero regressions)

Source: `ci/run_backend_tests.sh` full run on head `6d025bc`: **50 passed, 8 failed
(EXIT 1)**. Each failing suite was re-run on a clean `51affcc` worktree; every
count and first-failure line below is byte-identical on base. Classification:
all 8 **PRE-EXISTING**. None blocks the cloud testing env.

Green gates (head): migration 67/0, security 2162/0, leave 100/0.

| suite | base count | head count | first-failure line | classification | blocks cloud testing? |
|---|---|---|---|---|---|
| security_headers_test_suite | failures: 0 (import-time) | failures: 0 (import-time) | `RuntimeError: Production refuses to start with BACKEND_CORS_ORIGINS unset or wildcard (got []).` (`app/core/config.py` validate) | PRE-EXISTING | no — harness/env: suite imports app without test CORS origins |
| import_test_suite | 616 passed, 1 failed | 616 passed, 1 failed | `the generated schema document is up to date with the models: run: python scripts/generate_db_schema.py` | PRE-EXISTING | no — stale generated schema doc, models unaffected |
| india_payroll_test_suite | 113 passed, 1 failed | 113 passed, 1 failed | `the head revision is 0032_india_aadhaar_encryption (head after slice 6): head=0048_mfa_secret_envelope` | PRE-EXISTING | no — stale head assertion; chain itself green (migration 67/0) |
| payroll_framework_restart_test_suite | 56 passed, 1 failed | 56 passed, 1 failed | `US 2026-10-01 still resolves verified (other lane untouched) status=absent` | PRE-EXISTING | no — US-lane absence after us-standard pack removal (ADR-003); India lane green |
| reset_admin_password_test_suite | 35 passed, 9 failed | 35 passed, 9 failed | `in production it refuses to overwrite a credential in normal use: exit=1 ... BACKEND_CORS_ORIGINS unset or wildcard` | PRE-EXISTING | no — needs prod env (CORS origins + acknowledgements); also asserts hostname-specific audit `deployment=Srinivass-MacBook-Pro.local`, not hostname-independent |
| scheduling_test_suite | failures: 1 | failures: 1 | `FAIL ortools cp_model imports ortools missing: No module named 'ortools'` → `RuntimeError: ortools is not available` | PRE-EXISTING | no — missing optional solver dep on scratch host; install ortools to enable |
| cost_forecast_test_suite | 53 passed, 2 failed | 53 passed, 2 failed | `route registered : /api/v1/forecasting/runs/{run_id}/cost-forecast` (and `/{version}` variant) | PRE-EXISTING | no — cost-forecast routes not registered; fix = route registration (owner prioritization) |
| accuracy_test_suite | 82 passed, 2 failed | 82 passed, 2 failed | `route registered /api/v1/forecasting/accuracy: ` (and `/sync` variant) | PRE-EXISTING | no — accuracy routes not registered; fix = route registration (owner prioritization) |

Notes:

- The 8 failing-suite files are unchanged between `51affcc` and `6d025bc`
  (`git diff` empty); failures reproduce identically on both.
- reset_admin additionally needs hostname-independent assertions before it can
  pass on any machine.
- Owner action (only if prioritized): register cost/accuracy routes, fix
  reset-admin prod-env handling; scheduling needs ortools installed.
