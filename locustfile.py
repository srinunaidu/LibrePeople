"""
Load smoke harness for Karmathy HCM.

Simulates the critical user journeys against the staging environment:
- Sign in → dashboard → employee list → leave request → sign out
- Payroll run (dry run) → reconciliation view
- Import dry run → commit
- Schedule generation

Run against staging:
    locust -f locustfile.py --host=http://127.0.0.1:8011/api/v1 \
        --users 10 --spawn-rate 1 --run-time 5m --headless

The ramp profile starts at 1 user, ramps to the concurrency where
p95 latency exceeds 2s or error rate exceeds 1%, hold for 5 minutes,
then ramp down.
"""
from __future__ import annotations

import os
import random
import string
import time
from datetime import date, timedelta
from typing import Any

from locust import HttpUser, between, events, task
from locust.env import Environment
from locust.runners import MasterRunner, WorkerRunner


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Staging credentials (seeded by scripts/staging/run.sh)
STAGING_USERNAME = os.environ.get("LOAD_USERNAME", "admin")
STAGING_PASSWORD = os.environ.get("LOAD_PASSWORD", "E2e!Bootstrap#2026")

# Pass/fail criteria
P95_LATENCY_THRESHOLD_MS = 2000  # 2 seconds
ERROR_RATE_THRESHOLD = 0.01  # 1%

# Journey weights (relative frequency)
JOURNEY_WEIGHTS = {
    "signin_dashboard_employee_leave_signout": 40,
    "payroll_dryrun_reconciliation": 20,
    "import_dryrun_commit": 20,
    "schedule_generation": 20,
}

# Global state for pass/fail tracking
class LoadSmokeState:
    """Tracks the load test state for pass/fail determination."""
    def __init__(self):
        self.sustained_concurrency = 0
        self.p95_latencies: dict[str, list[float]] = {}
        self.error_counts: dict[str, int] = {}
        self.request_counts: dict[str, int] = {}
        self.passed = True
        self.failure_reason = ""

    def record_request(self, name: str, response_time: float, success: bool):
        if name not in self.p95_latencies:
            self.p95_latencies[name] = []
            self.error_counts[name] = 0
            self.request_counts[name] = 0
        self.p95_latencies[name].append(response_time)
        self.request_counts[name] += 1
        if not success:
            self.error_counts[name] += 1

    def p95(self, name: str) -> float:
        latencies = self.p95_latencies.get(name, [])
        if not latencies:
            return 0.0
        sorted_latencies = sorted(latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def error_rate(self, name: str) -> float:
        total = self.request_counts.get(name, 0)
        if total == 0:
            return 0.0
        return self.error_counts.get(name, 0) / total

    def check_criteria(self) -> tuple[bool, str]:
        """Check if the pass/fail criteria are met."""
        critical_endpoints = [
            "GET /",  # dashboard (root)
            "GET /employees/",  # employee list
        ]
        for endpoint in critical_endpoints:
            p95 = self.p95(endpoint)
            if p95 > P95_LATENCY_THRESHOLD_MS:
                return False, f"p95 latency for {endpoint} is {p95:.0f}ms (threshold: {P95_LATENCY_THRESHOLD_MS}ms)"
            err_rate = self.error_rate(endpoint)
            if err_rate > ERROR_RATE_THRESHOLD:
                return False, f"error rate for {endpoint} is {err_rate:.2%} (threshold: {ERROR_RATE_THRESHOLD:.2%})"
        return True, ""


load_state = LoadSmokeState()


# ---------------------------------------------------------------------------
# Event hooks for pass/fail tracking
# ---------------------------------------------------------------------------

@events.request.add_listener
def on_request(
    request_type: str,
    name: str,
    response_time: float,
    response_length: int,
    response: Any,
    context: Any,
    exception: BaseException | None,
    **kwargs: Any,
) -> None:
    success = exception is None and (response is None or response.status_code < 400)
    load_state.record_request(name, response_time, success)


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kwargs: Any) -> None:
    """Called when the test stops. Determines pass/fail."""
    if isinstance(environment.runner, (MasterRunner, WorkerRunner)):
        # Only the master process evaluates
        if not isinstance(environment.runner, WorkerRunner):
            passed, reason = load_state.check_criteria()
            load_state.passed = passed
            load_state.failure_reason = reason

            print("\n" + "=" * 70)
            print("LOAD SMOKE RESULT")
            print("=" * 70)
            print(f"Sustained concurrency: {load_state.sustained_concurrency}")
            print()
            print("Per-endpoint p95 latency (ms):")
            for name in sorted(load_state.p95_latencies.keys()):
                p95 = load_state.p95(name)
                err_rate = load_state.error_rate(name)
                count = load_state.request_counts.get(name, 0)
                status = "PASS" if (p95 <= P95_LATENCY_THRESHOLD_MS and err_rate <= ERROR_RATE_THRESHOLD) else "FAIL"
                print(f"  {name:30s}  p95={p95:7.0f}  err={err_rate:6.2%}  n={count:5d}  [{status}]")
            print()
            if passed:
                print("RESULT: PASS")
            else:
                print(f"RESULT: FAIL — {reason}")
            print("=" * 70)

            # Write result to PROGRESS.md
            _write_progress_md()


def _write_progress_md() -> None:
    """Append the load smoke result to agents/PROGRESS.md."""
    progress_path = "agents/PROGRESS.md"
    try:
        with open(progress_path, "a") as f:
            f.write("\n## Load Smoke Result\n\n")
            f.write(f"- **Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **Sustained concurrency**: {load_state.sustained_concurrency}\n")
            f.write(f"- **Pass/Fail**: {'PASS' if load_state.passed else 'FAIL'}\n")
            if load_state.failure_reason:
                f.write(f"- **Failure reason**: {load_state.failure_reason}\n")
            f.write("- **Per-endpoint p95 latency (ms) and error rate**:\n")
            for name in sorted(load_state.p95_latencies.keys()):
                p95 = load_state.p95(name)
                err_rate = load_state.error_rate(name)
                count = load_state.request_counts.get(name, 0)
                f.write(f"  - `{name}`: p95={p95:.0f}ms, err={err_rate:.2%}, n={count}\n")
    except Exception as exc:
        print(f"Warning: could not write to {progress_path}: {exc}")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def random_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def random_email() -> str:
    return f"loadtest.{random_string()}@example.test"


# ---------------------------------------------------------------------------
# User behaviour
# ---------------------------------------------------------------------------

class KarmathyUser(HttpUser):
    """Simulates a user performing critical journeys."""

    # Wait between 1-3 seconds between tasks (think time)
    wait_time = between(1, 3)

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.employee_id: int | None = None
        self._signed_in = False

    def on_start(self) -> None:
        """Sign in when the user starts."""
        self.sign_in()

    def on_stop(self) -> None:
        """Sign out when the user stops."""
        if self._signed_in:
            self.sign_out()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}

    def sign_in(self) -> None:
        """Sign in and store tokens."""
        with self.client.post(
            "/auth/login",
            json={"username": STAGING_USERNAME, "password": STAGING_PASSWORD},
            name="POST /auth/login",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self._signed_in = True
                response.success()
            else:
                response.failure(f"Sign in failed: {response.status_code}")

    def sign_out(self) -> None:
        """Sign out (revoke refresh token)."""
        if self.refresh_token:
            with self.client.post(
                "/auth/logout",
                json={"refresh_token": self.refresh_token},
                headers=self._headers(),
                name="POST /auth/logout",
                catch_response=True,
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Sign out failed: {response.status_code}")
            self._signed_in = False

    # -----------------------------------------------------------------------
    # Journey 1: Sign in → dashboard → employee list → leave request → sign out
    # -----------------------------------------------------------------------
    @task(JOURNEY_WEIGHTS["signin_dashboard_employee_leave_signout"])
    def journey_dashboard_employee_leave(self) -> None:
        """Sign in → dashboard → employee list → leave request → sign out."""
        # Dashboard (root health check)
        with self.client.get("/", name="GET /", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Dashboard failed: {response.status_code}")

        # Employee list
        with self.client.get(
            "/employees/?skip=0&limit=50",
            headers=self._headers(),
            name="GET /employees/",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                employees = response.json()
                if employees:
                    self.employee_id = employees[0].get("id")
                response.success()
            else:
                response.failure(f"Employee list failed: {response.status_code}")

        # Leave types (needed for leave request)
        with self.client.get(
            "/leave/types",
            headers=self._headers(),
            name="GET /leave/types",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                leave_types = response.json()
                if leave_types:
                    self._leave_type_id = leave_types[0].get("id")
                response.success()
            else:
                response.failure(f"Leave types failed: {response.status_code}")

        # Create leave request (if we have employee_id and leave_type_id)
        if hasattr(self, "_leave_type_id") and self.employee_id:
            start_date = date.today() + timedelta(days=random.randint(1, 30))
            end_date = start_date + timedelta(days=random.randint(1, 3))
            with self.client.post(
                "/leave/requests",
                json={
                    "employee_id": self.employee_id,
                    "leave_type_id": self._leave_type_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "reason": "Load test leave request",
                },
                headers=self._headers(),
                name="POST /leave/requests",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 201):
                    response.success()
                else:
                    response.failure(f"Leave request failed: {response.status_code}")

    # -----------------------------------------------------------------------
    # Journey 2: Payroll run (dry run) → reconciliation view
    # -----------------------------------------------------------------------
    @task(JOURNEY_WEIGHTS["payroll_dryrun_reconciliation"])
    def journey_payroll_reconciliation(self) -> None:
        """Payroll run (dry run) → reconciliation view."""
        # List payroll periods
        with self.client.get(
            "/payroll/periods",
            headers=self._headers(),
            name="GET /payroll/periods",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                periods = response.json()
                if periods:
                    self._payroll_period_id = periods[0].get("id")
                response.success()
            else:
                response.failure(f"Payroll periods failed: {response.status_code}")

        # List pay components
        with self.client.get(
            "/payroll/components",
            headers=self._headers(),
            name="GET /payroll/components",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Pay components failed: {response.status_code}")

        # Create a pay run (dry run - just create, don't process)
        if hasattr(self, "_payroll_period_id"):
            with self.client.post(
                "/payroll/runs",
                json={
                    "period_id": self._payroll_period_id,
                    "jurisdiction": "US-CA",
                },
                headers=self._headers(),
                name="POST /payroll/runs",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 201):
                    run = response.json()
                    self._pay_run_id = run.get("id")
                    response.success()
                else:
                    response.failure(f"Create pay run failed: {response.status_code}")

        # View reconciliation
        with self.client.get(
            "/leave/reconciliation",
            headers=self._headers(),
            name="GET /leave/reconciliation",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Reconciliation failed: {response.status_code}")

    # -----------------------------------------------------------------------
    # Journey 3: Import dry run → commit
    # -----------------------------------------------------------------------
    @task(JOURNEY_WEIGHTS["import_dryrun_commit"])
    def journey_import_dryrun_commit(self) -> None:
        """Import dry run → commit."""
        # Get import template for departments
        with self.client.get(
            "/import/template/departments",
            headers=self._headers(),
            name="GET /import/template/departments",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                template = response.text
                response.success()
            else:
                response.failure(f"Import template failed: {response.status_code}")
                return

        # Create a CSV for dry run
        unique_code = f"LOAD-{random_string(8)}"
        csv_content = f"code,name,description\n{unique_code},Load Test Department,Created by load test\n"

        # Dry run
        files = {"file": ("departments.csv", csv_content, "text/csv")}
        with self.client.post(
            "/import/departments?dry_run=true",
            files=files,
            headers=self._headers(),
            name="POST /import/departments (dry_run)",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self._import_token = data.get("confirmation_token")
                response.success()
            else:
                response.failure(f"Import dry run failed: {response.status_code}")
                return

        # Commit the import
        if hasattr(self, "_import_token"):
            with self.client.post(
                f"/import/departments/commit?confirmation_token={self._import_token}",
                headers=self._headers(),
                name="POST /import/departments/commit",
                catch_response=True,
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Import commit failed: {response.status_code}")

    # -----------------------------------------------------------------------
    # Journey 4: Schedule generation
    # -----------------------------------------------------------------------
    @task(JOURNEY_WEIGHTS["schedule_generation"])
    def journey_schedule_generation(self) -> None:
        """Schedule generation."""
        # List shift templates
        with self.client.get(
            "/scheduling/shift-templates",
            headers=self._headers(),
            name="GET /scheduling/shift-templates",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                templates = response.json()
                if templates:
                    self._shift_template_id = templates[0].get("id")
                response.success()
            else:
                response.failure(f"Shift templates failed: {response.status_code}")
                return

        # List employees (need one to generate roster for)
        with self.client.get(
            "/employees/?skip=0&limit=1",
            headers=self._headers(),
            name="GET /employees/ (for roster)",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                employees = response.json()
                if employees:
                    self._roster_employee_id = employees[0].get("id")
                response.success()
            else:
                response.failure(f"Employee list for roster failed: {response.status_code}")
                return

        # Generate roster
        if hasattr(self, "_shift_template_id") and hasattr(self, "_roster_employee_id"):
            start_date = date.today()
            end_date = start_date + timedelta(days=7)
            with self.client.post(
                "/scheduling/roster/generate",
                json={
                    "employee_id": self._roster_employee_id,
                    "shift_template_id": self._shift_template_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                headers=self._headers(),
                name="POST /scheduling/roster/generate",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 201):
                    response.success()
                else:
                    response.failure(f"Roster generation failed: {response.status_code}")

        # List roster
        with self.client.get(
            "/scheduling/roster",
            headers=self._headers(),
            name="GET /scheduling/roster",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Roster list failed: {response.status_code}")


# ---------------------------------------------------------------------------
# Ramp profile shape (for documentation — actual ramp is via Locust CLI)
# ---------------------------------------------------------------------------

"""
Ramp profile (implemented via Locust CLI flags):

Phase 1 - Warm-up (1 minute):
    --users 1 --spawn-rate 1 --run-time 1m

Phase 2 - Ramp up (5 minutes):
    --users 10 --spawn-rate 1 --run-time 5m

Phase 3 - Sustained load (5 minutes):
    --users <sustained> --spawn-rate 0 --run-time 5m
    (sustained = highest concurrency where p95 < 2s and error rate < 1%)

Phase 4 - Ramp down (1 minute):
    --users 1 --spawn-rate 1 --run-time 1m

The ci/load_smoke.sh script implements this by running Locust multiple times
with increasing user counts until the criteria are breached, then holds at
the highest passing concurrency for 5 minutes.
"""


# ---------------------------------------------------------------------------
# Standalone run (for local testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from locust import main as locust_main

    # This allows running `python locustfile.py` for quick smoke tests
    sys.argv = [
        "locust",
        "-f",
        __file__,
        "--host",
        os.environ.get("LOCUST_HOST", "http://127.0.0.1:8011/api/v1"),
        "--users",
        "1",
        "--spawn-rate",
        "1",
        "--run-time",
        "30s",
        "--headless",
    ]
    locust_main()
