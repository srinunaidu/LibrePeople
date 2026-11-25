#!/usr/bin/env bash
#
# Load smoke harness runner for Karmathy HCM.
#
# Runs the Locust harness against the staging environment with a ramp profile
# that finds the maximum sustained concurrency where:
#   - p95 latency on dashboard and employee list < 2s
#   - error rate < 1%
#
# Usage:
#   ci/load_smoke.sh                    # run full ramp profile
#   ci/load_smoke.sh --quick            # single run at 5 users for 30s
#   ci/load_smoke.sh --concurrency 10   # single run at specified concurrency
#
# Exits 0 on PASS, non-zero on FAIL.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCUSTFILE="${REPO_ROOT}/locustfile.py"
PROGRESS_MD="${REPO_ROOT}/agents/PROGRESS.md"

# Staging environment (started by scripts/staging/run.sh)
STAGING_API_URL="${STAGING_API_URL:-http://127.0.0.1:8011/api/v1}"
LOAD_USERNAME="${LOAD_USERNAME:-admin}"
LOAD_PASSWORD="${LOAD_PASSWORD:-E2e!Bootstrap#2026}"

# Pass/fail criteria
P95_THRESHOLD_MS=2000
ERROR_RATE_THRESHOLD=0.01

# Ramp profile parameters
WARMUP_USERS=1
WARMUP_DURATION="1m"
RAMP_START_USERS=1
RAMP_MAX_USERS=20
RAMP_STEP=2
RAMP_STEP_DURATION="2m"
SUSTAIN_DURATION="5m"
COOLDOWN_USERS=1
COOLDOWN_DURATION="30s"

QUICK_MODE=false
SINGLE_CONCURRENCY=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --concurrency)
            SINGLE_CONCURRENCY="$2"
            shift 2
            ;;
        --host)
            STAGING_API_URL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
    esac
done

# Check locustfile exists
if [[ ! -f "${LOCUSTFILE}" ]]; then
    echo "locustfile.py not found at ${LOCUSTFILE}" >&2
    exit 2
fi

# Install locust if not present
if ! command -v locust >/dev/null 2>&1; then
    echo "Installing locust..."
    pip install locust==2.15.1
fi

# Function to run a single locust test and extract metrics
run_locust_test() {
    local users="$1"
    local spawn_rate="$2"
    local duration="$3"
    local label="$4"

    echo "=== ${label}: ${users} users, spawn rate ${spawn_rate}/s, duration ${duration} ==="

    # Run locust headless, capture output
    local output
    output=$(cd "${REPO_ROOT}" && \
        LOAD_USERNAME="${LOAD_USERNAME}" \
        LOAD_PASSWORD="${LOAD_PASSWORD}" \
        locust -f "${LOCUSTFILE}" \
            --host="${STAGING_API_URL}" \
            --users="${users}" \
            --spawn-rate="${spawn_rate}" \
            --run-time="${duration}" \
            --headless \
            --only-summary 2>&1)

    echo "${output}"

    # Parse the output for p95 and error rate
    # Locust output format varies; we parse the summary table
    local p95_dashboard=0
    p95_dashboard=$(echo "${output}" | grep -E "GET /[[:space:]]" | head -1 | awk '{print $6}' | sed 's/[^0-9.]//g')
    local p95_employees=0
    p95_employees=$(echo "${output}" | grep -E "GET /employees/" | head -1 | awk '{print $6}' | sed 's/[^0-9.]//g')
    local error_rate=0
    error_rate=$(echo "${output}" | grep -E "Failures:" | head -1 | awk '{print $2}' | sed 's/[^0-9.]//g')
    if [[ -z "${error_rate}" ]]; then error_rate=0; fi

    # Also try to get from the summary stats if available
    if [[ "${p95_dashboard}" == "0" ]]; then
        p95_dashboard=$(echo "${output}" | awk '/GET \// {p95=$6} END {print p95}' | sed 's/[^0-9.]//g')
    fi

    echo "  Parsed: dashboard p95=${p95_dashboard}ms, employees p95=${p95_employees}ms, error_rate=${error_rate}%"

    # Return values via global vars
    LOCUST_P95_DASHBOARD="${p95_dashboard:-0}"
    LOCUST_P95_EMPLOYEES="${p95_employees:-0}"
    LOCUST_ERROR_RATE="${error_rate:-0}"
    LOCUST_OUTPUT="${output}"
}

# Quick mode: single run at 5 users for 30s
if [[ "${QUICK_MODE}" == "true" ]]; then
    echo "Quick mode: 5 users for 30s"
    run_locust_test 5 1 "30s" "Quick smoke test"
    # Simple pass/fail
    if (( $(echo "${LOCUST_P95_DASHBOARD} < ${P95_THRESHOLD_MS}" | bc -l) )) && \
       (( $(echo "${LOCUST_P95_EMPLOYEES} < ${P95_THRESHOLD_MS}" | bc -l) )) && \
       (( $(echo "${LOCUST_ERROR_RATE} < ${ERROR_RATE_THRESHOLD} * 100" | bc -l) )); then
        echo "QUICK TEST: PASS"
        exit 0
    else
        echo "QUICK TEST: FAIL"
        exit 1
    fi
fi

# Single concurrency mode
if [[ "${SINGLE_CONCURRENCY}" -gt 0 ]]; then
    echo "Single concurrency mode: ${SINGLE_CONCURRENCY} users for 5m"
    run_locust_test "${SINGLE_CONCURRENCY}" 1 "5m" "Sustained load test"
    if (( $(echo "${LOCUST_P95_DASHBOARD} < ${P95_THRESHOLD_MS}" | bc -l) )) && \
       (( $(echo "${LOCUST_P95_EMPLOYEES} < ${P95_THRESHOLD_MS}" | bc -l) )) && \
       (( $(echo "${LOCUST_ERROR_RATE} < ${ERROR_RATE_THRESHOLD} * 100" | bc -l) )); then
        echo "SUSTAINED TEST: PASS"
        exit 0
    else
        echo "SUSTAINED TEST: FAIL"
        exit 1
    fi
fi

# Full ramp profile
echo "Starting full load smoke ramp profile..."
echo "Staging API: ${STAGING_API_URL}"

# Phase 1: Warm-up
echo
echo ">>> Phase 1: Warm-up (${WARMUP_USERS} user for ${WARMUP_DURATION})"
run_locust_test "${WARMUP_USERS}" 1 "${WARMUP_DURATION}" "Warm-up"

# Phase 2: Ramp up to find breaking point
echo
echo ">>> Phase 2: Ramp up (finding sustained concurrency)"
SUSTAINED_CONCURRENCY=0
LAST_PASSING_USERS=0

for (( users=RAMP_START_USERS; users<=RAMP_MAX_USERS; users+=RAMP_STEP )); do
    echo
    echo "--- Testing ${users} users ---"
    run_locust_test "${users}" 1 "${RAMP_STEP_DURATION}" "Ramp step ${users}"

    # Check criteria
    pass_dashboard=0
    pass_employees=0
    pass_error=0

    if (( $(echo "${LOCUST_P95_DASHBOARD} < ${P95_THRESHOLD_MS}" | bc -l) )); then
        pass_dashboard=1
    fi
    if (( $(echo "${LOCUST_P95_EMPLOYEES} < ${P95_THRESHOLD_MS}" | bc -l) )); then
        pass_employees=1
    fi
    if (( $(echo "${LOCUST_ERROR_RATE} < ${ERROR_RATE_THRESHOLD} * 100" | bc -l) )); then
        pass_error=1
    fi

    if [[ ${pass_dashboard} -eq 1 && ${pass_employees} -eq 1 && ${pass_error} -eq 1 ]]; then
        echo "  -> PASS at ${users} users"
        LAST_PASSING_USERS="${users}"
        SUSTAINED_CONCURRENCY="${users}"
    else
        echo "  -> FAIL at ${users} users (dashboard_p95_ok=${pass_dashboard}, employees_p95_ok=${pass_employees}, error_ok=${pass_error})"
        break
    fi
done

if [[ ${SUSTAINED_CONCURRENCY} -eq 0 ]]; then
    echo "FAIL: Even 1 user exceeds thresholds"
    exit 1
fi

echo
echo ">>> Maximum passing concurrency: ${SUSTAINED_CONCURRENCY} users"

# Phase 3: Sustained load at maximum passing concurrency
echo
echo ">>> Phase 3: Sustained load (${SUSTAINED_CONCURRENCY} users for ${SUSTAIN_DURATION})"
run_locust_test "${SUSTAINED_CONCURRENCY}" 0 "${SUSTAIN_DURATION}" "Sustained load"

# Check sustained criteria
pass_dashboard=0
pass_employees=0
pass_error=0

if (( $(echo "${LOCUST_P95_DASHBOARD} < ${P95_THRESHOLD_MS}" | bc -l) )); then
    pass_dashboard=1
fi
if (( $(echo "${LOCUST_P95_EMPLOYEES} < ${P95_THRESHOLD_MS}" | bc -l) )); then
    pass_employees=1
fi
if (( $(echo "${LOCUST_ERROR_RATE} < ${ERROR_RATE_THRESHOLD} * 100" | bc -l) )); then
    pass_error=1
fi

# Phase 4: Cool down
echo
echo ">>> Phase 4: Cool down (${COOLDOWN_USERS} user for ${COOLDOWN_DURATION})"
run_locust_test "${COOLDOWN_USERS}" 1 "${COOLDOWN_DURATION}" "Cool down"

# Final result
echo
echo "=========================================="
echo "LOAD SMOKE FINAL RESULT"
echo "=========================================="
echo "Sustained concurrency: ${SUSTAINED_CONCURRENCY}"
echo "Dashboard p95: ${LOCUST_P95_DASHBOARD}ms (threshold: ${P95_THRESHOLD_MS}ms) [$( [[ ${pass_dashboard} -eq 1 ]] && echo PASS || echo FAIL )]"
echo "Employees p95: ${LOCUST_P95_EMPLOYEES}ms (threshold: ${P95_THRESHOLD_MS}ms) [$( [[ ${pass_employees} -eq 1 ]] && echo PASS || echo FAIL )]"
echo "Error rate: ${LOCUST_ERROR_RATE}% (threshold: $(echo "${ERROR_RATE_THRESHOLD} * 100" | bc -l)%) [$( [[ ${pass_error} -eq 1 ]] && echo PASS || echo FAIL )]"

if [[ ${pass_dashboard} -eq 1 && ${pass_employees} -eq 1 && ${pass_error} -eq 1 ]]; then
    echo "RESULT: PASS"
    exit 0
else
    echo "RESULT: FAIL"
    exit 1
fi
