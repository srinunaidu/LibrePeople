"""ESS hub portal contract (portals-completion slice 1).

Verifies every backend endpoint the Associate portal journeys depend on is
registered with the expected method + path. Pure route-contract test — no DB,
no migrations, no backend changes.

Journeys: clock in/out, leave request + balances, payslips, onboarding tasks,
ESS profile/files/notifications/directory/org-chart.

Run: pytest tests/test_ess_hub_suite.py (from backend/)
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "local-test-secret-key-not-for-production-0123456789")
os.environ.setdefault("FIELD_ENCRYPTION_KEYS", "lp-test-key:local-test-field-encryption-secret-0123456789")
os.environ.setdefault("FIELD_ENCRYPTION_ACTIVE_KEY_ID", "lp-test-key")

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from fastapi.routing import APIRouter  # noqa: E402

from app.api.v1.endpoints import (  # noqa: E402
    ess_hr,
    leave,
    onboarding,
    payroll,
    time_attendance,
)


def _routes(*routers: tuple[APIRouter, str]) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for router, prefix in routers:
        for route in router.routes:
            path = prefix + getattr(route, "path", "")
            for method in getattr(route, "methods", set()) or set():
                out.add((method, path))
    return out


ROUTES = _routes(
    (ess_hr.router, "/ess"),
    (leave.router, "/leave"),
    (time_attendance.router, "/time"),
    (payroll.router, "/payroll"),
    (onboarding.router, "/onboarding"),
)


def _assert(method: str, path: str) -> None:
    assert (method, path) in ROUTES, f"missing backend route {method} {path}"


def test_clock_journey_routes_exist():
    _assert("POST", "/time/clock-in")
    _assert("POST", "/time/clock-out")
    _assert("GET", "/time/today")


def test_leave_request_balances_routes_exist():
    _assert("GET", "/leave/types")
    _assert("GET", "/leave/balances")
    _assert("POST", "/leave/requests")
    _assert("GET", "/leave/requests")


def test_payslip_routes_exist():
    _assert("GET", "/payroll/payslips")


def test_onboarding_tasks_routes_exist():
    # AssociateHome loads per-employee tasks for the "My tasks" card.
    assert any(
        m == "GET" and p.startswith("/onboarding/") for m, p in ROUTES
    ), "missing GET /onboarding/... tasks route"


def test_ess_hub_section_routes_exist():
    _assert("GET", "/ess/ess/profile/{employee_id}")
    _assert("POST", "/ess/ess/profile")
    _assert("GET", "/ess/notifications")
    _assert("PUT", "/ess/notifications/{notification_id}/read")
    _assert("GET", "/ess/employee-files")
    _assert("GET", "/ess/directory")
    _assert("GET", "/ess/org-chart")
    _assert("GET", "/ess/announcements")
    _assert("GET", "/ess/continuous-feedback")
