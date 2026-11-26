"""Saved views (reporting-personalization Part E).

Proves, against the served API:
* POST creates {name, report_key, filters} (REPORTS_ROLES, tenant-scoped);
* GET lists only the caller's rows plus shared views their role may open;
* PATCH/DELETE by a non-owner non-admin is 403;
* shared-view publish needs HR/SuperAdmin (Manager/Associate → 403);
* unknown report_key is 422 and writes no row;
* a cross-tenant id reads 404;
* a fresh user lists zero views (the frontend empty-state source).

Run:  python tests/test_report_views.py   (from backend/)
  or: pytest tests/test_report_views.py -q
"""
import datetime
import os
import shutil
import sys
import tempfile
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

DB_DIR = tempfile.mkdtemp(prefix="report_views_suite_")
DB_PATH = os.path.join(DB_DIR, "report_views_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.report_personalization import ReportSavedView  # noqa: E402
from app.models.user import User  # noqa: E402

TENANT_A = "tenant-rpv-a"
TENANT_B = "tenant-rpv-b"
PASSWORD = "ReportViewsPass123"

_RESULT = None


def _run() -> dict:
    global _RESULT
    if _RESULT is not None:
        return _RESULT

    results = {"pass": 0, "fail": 0}
    failures: list[tuple[str, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        if ok:
            results["pass"] += 1
            print(f"  PASS  {name}")
        else:
            results["fail"] += 1
            failures.append((name, detail))
            print(f"  FAIL  {name}  {detail}")

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    dept = Department(name="RPV Ops", code="RPVOPS")
    db.add(dept)
    db.commit()
    db.refresh(dept)
    job = Job(title="RPV Analyst", code="RPVANL", department_id=dept.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    emp = Employee(
        employee_id="RPV-001", first_name="Rpv", last_name="Owner",
        email="rpv-owner@example.com", hire_date=datetime.date(2023, 2, 1),
        job_id=job.id, department_id=dept.id, status="Active",
        tenant_id=TENANT_A,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)

    def _user(username: str, role: str) -> None:
        if db.query(User).filter(User.username == username).first() is None:
            db.add(User(
                username=username, email=f"{username}@example.com",
                hashed_password=get_password_hash(PASSWORD),
                role=role, is_active=True,
                mfa_enabled=role in ("SuperAdmin", "HR"),
            ))
            db.commit()

    _user("rpv_admin", "SuperAdmin")
    _user("rpv_hr", "HR")
    _user("rpv_mgr", "Manager")
    _user("rpv_assoc", "Associate")
    _user("rpv_pay", "PayrollViewer")
    _user("rpv_fresh", "PayrollViewer")
    db.close()

    client = TestClient(app, raise_server_exceptions=False)

    def _headers(username: str, tenant: str = TENANT_A) -> dict:
        token = create_access_token(subject=username, extra_claims={"tenant": tenant})
        return {"Authorization": f"Bearer {token}"}

    H_ADMIN = _headers("rpv_admin")
    H_HR = _headers("rpv_hr")
    H_MGR = _headers("rpv_mgr")
    H_ASSOC = _headers("rpv_assoc")
    H_PAY = _headers("rpv_pay")
    H_FRESH = _headers("rpv_fresh")
    H_FOREIGN = _headers("rpv_admin", TENANT_B)

    def _count_views() -> int:
        s = SessionLocal()
        try:
            return s.query(ReportSavedView).count()
        finally:
            s.close()

    # =======================================================================
    print("\n[VIEWS-1] Creation persists name, key and filters (AC1)")
    # =======================================================================
    before = _count_views()
    r = client.post(
        "/api/v1/report-views", headers=H_HR,
        json={"name": "Q1 joiners", "report_key": "joiners",
              "filters": {"from": "2026-01-01", "to": "2026-03-31"}},
    )
    check("HR creates a view", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    body = r.json()
    check("the key round-trips", body.get("report_key") == "joiners", r.text[:200])
    check("the filters round-trip", body.get("filters", {}).get("from") == "2026-01-01", r.text[:200])
    check("a row was written", _count_views() == before + 1, f"count={_count_views()}")
    V_PERSONAL = body.get("id")

    r = client.get("/api/v1/report-views", headers=H_FRESH)
    check("a user with no own views and no visible shared views lists zero",
          r.json().get("views") == [] and r.json().get("count") == 0, r.text[:200])

    r = client.post(
        "/api/v1/report-views", headers=H_HR,
        json={"name": "Shared leavers", "report_key": "leavers",
              "filters": {}, "visibility": "shared"},
    )
    check("HR publishes a shared view", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    V_SHARED = r.json().get("id")

    # =======================================================================
    print("\n[VIEWS-2] Listing is owner + role-gated shared (AC1)")
    # =======================================================================
    r = client.get("/api/v1/report-views", headers=H_HR)
    ids = [v["id"] for v in r.json().get("views", [])]
    check("owner sees both views", V_PERSONAL in ids and V_SHARED in ids, r.text[:200])

    r = client.get("/api/v1/report-views", headers=H_PAY)
    ids = [v["id"] for v in r.json().get("views", [])]
    check("PayrollViewer sees the shared view", V_SHARED in ids, r.text[:200])
    check("PayrollViewer does not see the personal view", V_PERSONAL not in ids, r.text[:200])

    r = client.get("/api/v1/report-views", headers=H_ASSOC)
    check("Associate list is refused 403", r.status_code == 403, f"got {r.status_code}")

    # =======================================================================
    print("\n[VIEWS-3] Non-owner writes are 403; publish needs HR/SuperAdmin (AC2)")
    # =======================================================================
    r = client.patch(f"/api/v1/report-views/{V_PERSONAL}", headers=H_PAY, json={"name": "hijack"})
    check("non-owner non-admin PATCH is 403", r.status_code == 403, f"got {r.status_code}: {r.text[:200]}")

    r = client.delete(f"/api/v1/report-views/{V_PERSONAL}", headers=H_PAY)
    check("non-owner non-admin DELETE is 403", r.status_code == 403, f"got {r.status_code}: {r.text[:200]}")

    r = client.post(
        "/api/v1/report-views", headers=H_MGR,
        json={"name": "mgr view", "report_key": "joiners", "filters": {}},
    )
    check("Manager create is refused 403", r.status_code == 403, f"got {r.status_code}: {r.text[:200]}")

    r = client.patch(f"/api/v1/report-views/{V_PERSONAL}", headers=H_HR,
                     json={"visibility": "shared"})
    check("HR may publish", r.status_code == 200 and r.json().get("visibility") == "shared", f"got {r.status_code}: {r.text[:200]}")

    # A PayrollViewer-owned personal view cannot be self-published.
    r = client.post(
        "/api/v1/report-views", headers=H_PAY,
        json={"name": "pay view", "report_key": "joiners", "filters": {}},
    )
    V_PAY = r.json().get("id") if r.status_code == 201 else None
    check("PayrollViewer creates a personal view", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    r = client.patch(f"/api/v1/report-views/{V_PAY}", headers=H_PAY, json={"visibility": "shared"})
    check("PayrollViewer publish attempt is 403", r.status_code == 403, f"got {r.status_code}: {r.text[:200]}")

    r = client.delete(f"/api/v1/report-views/{V_PAY}", headers=H_PAY)
    check("owner may delete their own view", r.status_code == 204, f"got {r.status_code}: {r.text[:200]}")
    r = client.get("/api/v1/report-views", headers=H_PAY)
    ids = [v["id"] for v in r.json().get("views", [])]
    check("the deleted view is gone from the list", V_PAY not in ids, r.text[:200])

    # =======================================================================
    print("\n[VIEWS-4] Unknown keys are 422 and write nothing (AC3)")
    # =======================================================================
    before = _count_views()
    r = client.post(
        "/api/v1/report-views", headers=H_HR,
        json={"name": "bogus", "report_key": "turnover-magic", "filters": {}},
    )
    check("unknown report_key is 422", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")
    check("no row was written", _count_views() == before, f"count={_count_views()}")

    # =======================================================================
    print("\n[VIEWS-5] Cross-tenant ids read 404 (AC1)")
    # =======================================================================
    r = client.get(f"/api/v1/report-views/{V_SHARED}", headers=H_FOREIGN)
    check("foreign GET is 404", r.status_code == 404, f"got {r.status_code}: {r.text[:200]}")
    r = client.patch(f"/api/v1/report-views/{V_SHARED}", headers=H_FOREIGN, json={"name": "x"})
    check("foreign PATCH is 404", r.status_code == 404, f"got {r.status_code}: {r.text[:200]}")
    r = client.delete(f"/api/v1/report-views/{V_SHARED}", headers=H_FOREIGN)
    check("foreign DELETE is 404", r.status_code == 404, f"got {r.status_code}: {r.text[:200]}")

    _RESULT = {"pass": results["pass"], "fail": results["fail"], "failures": failures}
    print(f"\nreport_views: {results['pass']} passed, {results['fail']} failed")
    return _RESULT


def test_report_views() -> None:
    result = _run()
    assert result["fail"] == 0, f"failures: {result['failures']}"


if __name__ == "__main__":
    result = _run()
    shutil.rmtree(DB_DIR, ignore_errors=True)
    raise SystemExit(1 if result["fail"] else 0)
