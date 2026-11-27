#!/usr/bin/env bash
#
# Run every backend test suite in a clean state.
#
# Each suite builds its own SQLite database, so the previous run's rows never
# leak into the next one. A suite that fails stops the run: a partial pass is
# not a pass.
#
# Usage:
#   ci/run_backend_tests.sh            # run everything
#   ci/run_backend_tests.sh security   # run suites whose name contains "security"
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
PYTHON="${PYTHON:-${REPO_ROOT}/.venv/bin/python}"

if [ ! -x "${PYTHON}" ]; then
  PYTHON="$(command -v python3 || command -v python)"
fi

if [ -z "${PYTHON}" ]; then
  echo "run_backend_tests: no Python interpreter found" >&2
  exit 2
fi

# A local, non-production secret key. The application refuses to start with a
# short one, and this key is only ever used against a throwaway SQLite file.
export SECRET_KEY="${SECRET_KEY:-local-test-secret-key-not-for-production-0123456789}"
export BACKEND_CORS_ORIGINS=""
export ALLOW_SELF_REGISTRATION="false"
export LOG_LEVEL="CRITICAL"
export MIGRATE_ON_STARTUP="false"

# The suites that are run, in order. The migration suite is first because it
# is the fastest way to notice that the schema and the models have diverged.
SUITES=(
  startup_test_suite
  migration_test_suite
  security_test_suite
  security_headers_test_suite
  error_transparency_test_suite
  visibility_test_suite
  ops_model_test_suite
  mfa_test_suite
  audit_test_suite
  audit_chain_test_suite
  jobs_test_suite
  job_worker_test_suite
  retention_test_suite
  streaming_parse_test_suite
  master_data_test_suite
  legal_entity_test_suite
  custom_fields_test_suite
  metrics_test_suite
  reports_slice_test_suite
  data_quality_test_suite
  import_test_suite
  hire_test_suite
  payroll_test_suite
  payroll_execution_test_suite
  payroll_pipeline_test_suite
  india_payroll_test_suite
  india_payroll_final_test_suite
  payroll_framework_restart_test_suite
  payroll_golden_p5_test_suite
  leave_test_suite
  time_corrections_test_suite
  expenses_test_suite
  ess_hub_test_suite
  notification_centre_test_suite
  notification_delivery_test_suite
  notification_email_provider_test_suite
  reset_admin_password_test_suite
  container_ci_security_test_suite
  lp_phase2_access_test_suite
  superadmin_write_gate_test_suite
  schema_drift_test_suite
  schema_alignment_test_suite
  smoke_test_phases_3_7
  smoke_test_client_onboarding
  smoke_test_all_phases
  onboarding_test_suite
  scheduling_test_suite
  cost_forecast_test_suite
  scenario_builder_test_suite
  accuracy_test_suite
  admin_jobs_test_suite
  admin_audit_test_suite
  cross_tenant_test_suite
  employees_test_suite
  employment_history_test_suite
  lifecycle_test_suite
  talent_test_suite
  lp_doc_002_test_suite
  update_system_test_suite
)

# Guard: rule_packs/in-standard.json must be a symlink to backend source or byte-identical.
# Prevents drift between the resolver-visible copy and the source of truth.
if [ ! -L "${REPO_ROOT}/rule_packs/in-standard.json" ] && ! cmp -s "${REPO_ROOT}/rule_packs/in-standard.json" "${REPO_ROOT}/backend/rule_packs/in-standard.json"; then
  echo "CI guard: rule_packs/in-standard.json is not a symlink and differs from backend/rule_packs/in-standard.json (sha mismatch — drift)" >&2
  exit 1
fi

FILTER="${1:-}"
FAILED=()
PASSED=()

cd "${BACKEND_DIR}" || exit 2

for suite in "${SUITES[@]}"; do
  if [ -n "${FILTER}" ] && [[ "${suite}" != *"${FILTER}"* ]]; then
    continue
  fi
  if [ ! -f "${suite}.py" ]; then
    echo "  SKIP  ${suite} (not present)"
    continue
  fi

  # Each suite owns a database file; remove it so the run starts clean.
  rm -f ./*.db "${suite}.db" 2>/dev/null

  output="$("${PYTHON}" "${suite}.py" 2>&1)"
  status=$?

  summary="$(printf '%s\n' "${output}" | grep -Eo '[0-9]+ passed, [0-9]+ failed' | tail -1)"
  if [ -z "${summary}" ]; then
    summary="$(printf '%s\n' "${output}" | grep -cE '^  FAIL' | sed 's/^/failures: /')"
  fi

  if [ ${status} -eq 0 ]; then
    printf '  PASS  %-30s %s\n' "${suite}" "${summary}"
    PASSED+=("${suite}")
  else
    printf '  FAIL  %-30s %s\n' "${suite}" "${summary}"
    FAILED+=("${suite}")
    printf '%s\n' "${output}" | tail -25
  fi
done

# The Oracle round trip.
#
# The SQLite suites above cannot see the failures that stop the migration
# chain on Oracle: SQLite allows two indexes over one column list, folds
# every identifier the same way and has no reserved words. The chain has to
# be applied to a real Oracle database before a release.
#
# It needs the Autonomous Database wallet and a scratch schema, so it is
# not part of the ordinary pull-request gate. It runs when ORACLE_ROUNDTRIP
# is set to 1 and the Oracle environment is present; the Release Manager
# decides where that happens (a scheduled job, a release check, or the
# documented command in the release procedure).
if [ "${ORACLE_ROUNDTRIP:-0}" = "1" ]; then
  echo
  echo "  RUN   oracle migration round trip"
  if "${REPO_ROOT}/ci/oracle_migration_roundtrip.sh" \
       --i-know-this-is-a-scratch-schema; then
    printf '  PASS  %-30s %s\n' "oracle_migration_roundtrip" "3 cycles"
    PASSED+=("oracle_migration_roundtrip")
  else
    printf '  FAIL  %-30s %s\n' "oracle_migration_roundtrip" "see the output above"
    FAILED+=("oracle_migration_roundtrip")
  fi
fi

# The container installs backend/requirements.txt and nothing else. An import
# that is not declared there passes every suite and fails the deploy.
if ! "$PYTHON" "$REPO_ROOT/ci/check_requirements.py"; then
  FAILED+=("requirements")
fi

echo
echo "----------------------------------------------------------------"
echo "backend suites: ${#PASSED[@]} passed, ${#FAILED[@]} failed"
if [ ${#FAILED[@]} -gt 0 ]; then
  echo "failed: ${FAILED[*]}"
  exit 1
fi
exit 0
