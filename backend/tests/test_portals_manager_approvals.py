"""Manager portal approve/reject contract (portals-completion slice 2).

Verifies every backend endpoint the ManagerHome inline-approval inbox depends
on is registered with the expected method + path. Pure route-contract test —
no DB, no migrations, no backend changes.

Documents: timesheet REJECT is INCOMPLETE — backend exposes only
POST /time/timesheets/{id}/approve (time_attendance.py), no reject route,
so the portal offers Approve-only for timesheets.

Run: pytest tests/test_portals_manager_approvals.py (from backend/)
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
    leave,
    performance,
    scheduling,
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
    (leave.router, "/leave"),
    (time_attendance.router, "/time"),
    (scheduling.router, "/scheduling"),
    (performance.router, "/performance"),
)


def _assert(method: str, path: str) -> None:
    assert (method, path) in ROUTES, f"missing backend route {method} {path}"


def test_leave_approve_reject_routes_exist():
    _assert("POST", "/leave/requests/{request_id}/approve")
    _assert("POST", "/leave/requests/{request_id}/reject")


def test_timesheet_approve_route_exists():
    _assert("POST", "/time/timesheets/{timesheet_id}/approve")


def test_timesheet_reject_route_absent_incomplete():
    """INCOMPLETE by contract §5: no backend reject route — do not invent."""
    assert ("POST", "/time/timesheets/{timesheet_id}/reject") not in ROUTES


def test_swap_approve_reject_routes_exist():
    _assert("POST", "/scheduling/swaps/{swap_id}/approve")
    _assert("POST", "/scheduling/swaps/{swap_id}/reject")


def test_manager_inbox_list_routes_exist():
    _assert("GET", "/leave/requests")
    _assert("GET", "/time/timesheets")
    _assert("GET", "/scheduling/swaps")
    _assert("GET", "/performance/goals")
    _assert("GET", "/performance/reviews")
    _assert("GET", "/time/today")
