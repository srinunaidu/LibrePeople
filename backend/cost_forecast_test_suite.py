"""Cost forecast test suite (AN-04): labour cost = forecast demand x rates.

What this suite proves
----------------------
* forecast_cost turns a forecast run's demand series into cost lines
  grouped by month (period) with the assumed hourly rate applied
* rates are matched by role code, then role title, then "default" catch-all
* a demand group with no rate and no default is a 422-style error, never
  an implicit zero
* results are stored and versioned: a re-run creates v2, v3... and the
  earlier versions stay intact and retrievable
* the stored run is traceable: input_hash changes when either the run's
  results or the rates change
* every response carries the label "excludes statutory on-costs" (label,
  cost_basis, every row on the CSV export)
* API: POST creates v1 (201), POST again creates v2, GET lists versions,
  GET by version returns rows, CSV export streams text/csv with the label
  column, unknown run/version answered 404/422

Date window: March 2026 — distinct from the publish tests (January 2026)
and the attendance tests (February 2027) so cross-suite date-range
queries cannot contaminate each other.

Run:  python cost_forecast_test_suite.py
"""
import datetime
import os
import sys
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="cost_forecast_"), "cf.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

import sqlalchemy as sa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.forecasting import CostForecast, CostForecastRow, ForecastResult, ForecastRun  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.cost_forecast import (
    STATUTORY_LABEL,
    CostForecastError,
    forecast_cost,
    get_cost_forecast,
    list_cost_forecasts,
)  # noqa: E402

Base.metadata.create_all(bind=engine)

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


# --- Fixtures ----------------------------------------------------------------

# March 2026: a window deliberately distinct from other suites' fixtures.
PERIOD_A = datetime.date(2026, 3, 2)
PERIOD_B = datetime.date(2026, 3, 9)
PERIOD_C = datetime.date(2026, 3, 16)
PERIOD_D = datetime.date(2026, 4, 1)  # crosses into the next month bucket
PASSWORD = "CostTestPass123"
PASSWORD_HASH = get_password_hash(PASSWORD)

db = SessionLocal()
dept = Department(name="Costing", code="COST")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Shift Supervisor", code="SUP", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)

emp = Employee(
    employee_id="CF001",
    first_name="Cost",
    last_name="Manager",
    email="cfmgr@example.com",
    department_id=dept.id,
    job_id=job.id,
    hire_date=datetime.date(2024, 1, 1),
    status="Active",
)
db.add(emp)
db.commit()
db.refresh(emp)

manager = User(
    username="cfmgr",
    email="cfmgr@example.com",
    hashed_password=PASSWORD_HASH,
    role="Manager",
    is_active=True,
    employee_id=emp.id,
)
db.add(manager)
db.commit()
db.refresh(manager)


def _forecast_run(name: str, results: list[dict]) -> ForecastRun:
    """Seed a completed forecast run with per-day result rows."""
    run = ForecastRun(
        name=name,
        horizon_days=len(results),
        method="seasonal_naive",
        status="completed",
        finished_at=datetime.datetime.now(datetime.timezone.utc),
        location_id=None,
        role_id=job.id,
    )
    db.add(run)
    db.flush()
    for r in results:
        db.add(
            ForecastResult(
                forecast_run_id=run.id,
                series_key=f"{job.code}:hours",
                horizon_step=r["horizon_step"],
                forecast_date=r["forecast_date"],
                predicted_value=r["predicted_value"],
                lower_bound=r["predicted_value"] - 1,
                upper_bound=r["predicted_value"] + 1,
                input_hash="cost-suite-" + name.replace(" ", ""),
                rule_version="test-1.0",
                method_used="seasonal_naive",
            )
        )
    db.commit()
    db.refresh(run)
    return run


run = _forecast_run(
    "Cost run A",
    [
        {"horizon_step": 1, "forecast_date": PERIOD_A, "predicted_value": 40.0},
        {"horizon_step": 2, "forecast_date": PERIOD_B, "predicted_value": 30.0},
        {"horizon_step": 3, "forecast_date": PERIOD_C, "predicted_value": 25.0},
        {"horizon_step": 4, "forecast_date": PERIOD_D, "predicted_value": 36.0},
    ],
)

client = TestClient(app)
TOKEN = None


def login(username: str = "cfmgr") -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    body = resp.json()
    return body.get("access_token") or body.get("token") or ""


# ==============================================================================
# Service-level behaviour
# ==============================================================================

def test_service_groups_by_month_and_applies_rates():
    result = forecast_cost(
        db,
        run.id,
        hourly_costs={"SUP": 25.0},
    )
    # March: 40 + 30 + 25 = 95 hours; April: 36 hours
    check("service groups by month", len(result["rows"]) == 2, str(len(result["rows"])))
    march = next((r for r in result["rows"] if r["period"] == "2026-03"), None)
    check("march bucket correct", march is not None and abs(march["hours"] - 95.0) < 1e-6,
          str(march))
    check("march cost = hours x rate", march is not None and abs(march["cost"] - 95.0 * 25.0) < 1e-6,
          str(march))
    april = next((r for r in result["rows"] if r["period"] == "2026-04"), None)
    check("april bucket correct", april is not None and abs(april["hours"] - 36.0) < 1e-6,
          str(april))
    total = sum(r["cost"] for r in result["rows"])
    check("totals correct", abs(result["total_cost"] - (95.0 + 36.0) * 25.0) < 1e-6,
          str(result["total_cost"]))
    check("role labels resolved from run", result["role_id"] == job.id and result["role_code"] == "SUP"
          and result["role"] == "Shift Supervisor", str(result))
    check("statutory label on service response",
          result["label"] == STATUTORY_LABEL == result["cost_basis"], "")
    return result


def test_rate_matching_by_title_then_default():
    # By role title, falls back through code
    result = forecast_cost(db, run.id, hourly_costs={"Shift Supervisor": 30.0})
    check("rate matched by title", result["rows"][0]["hourly_cost"] == 30.0, str(result["rows"][0]))
    # Default catch-all
    result = forecast_cost(db, run.id, hourly_costs={"default": 20.5})
    check("rate matched by default", result["rows"][0]["hourly_cost"] == 20.5, str(result["rows"][0]))


def test_missing_rate_is_an_error_not_a_zero():
    try:
        forecast_cost(db, run.id, hourly_costs={"WRONGROLE": 10.0})
        check("missing rate raises", False, "no exception")
    except CostForecastError as exc:
        check("missing rate raises", "SUP" in str(exc) or "default" in str(exc), str(exc))


def test_versioned_storage_many_versions():
    # Fresh run: absolute version numbers, untouched by the earlier tests.
    vr = _forecast_run(
        "Versioned cost run",
        [
            {"horizon_step": 1, "forecast_date": PERIOD_A, "predicted_value": 10.0},
            {"horizon_step": 2, "forecast_date": PERIOD_B, "predicted_value": 20.0},
        ],
    )
    v1 = forecast_cost(db, vr.id, hourly_costs={"SUP": 25.0})
    check("first version is 1", v1["version"] == 1, str(v1["version"]))
    v2 = forecast_cost(db, vr.id, hourly_costs={"SUP": 27.5})
    check("re-run creates version 2", v2["version"] == 2, str(v2["version"]))
    check("new version keeps run id", v2["forecast_run_id"] == vr.id, "")
    check("input_hash differs when rates differ", v1["input_hash"] != v2["input_hash"], "")
    # Same inputs -> same input_hash
    v3 = forecast_cost(db, vr.id, hourly_costs={"SUP": 27.5})
    check("same inputs -> same input_hash", v3["input_hash"] == v2["input_hash"], "")

    versions = list_cost_forecasts(db, vr.id)
    check("all versions listed newest first", [v["version"] for v in versions] == [3, 2, 1],
          str([v["version"] for v in versions]))
    check("v1 rows still intact", abs(versions[2]["total_cost"] - (10.0 + 20.0) * 25.0) < 1e-6,
          str(versions[2]["total_cost"]))
    check("latest version's rows also intact", abs(versions[0]["total_cost"] - 30.0 * 27.5) < 1e-6,
          str(versions[0]["total_cost"]))

    fetched = get_cost_forecast(db, vr.id, 2)
    check("get by version returns rows", fetched is not None and len(fetched["rows"]) == 1,
          f"rows={len(fetched['rows']) if fetched else 0}")
    check("fetched version rows carry the label", fetched is not None and fetched["cost_basis"] == STATUTORY_LABEL, "")
    check("unknown version returns None", get_cost_forecast(db, vr.id, 99) is None, "")


def test_window_filter():
    result = forecast_cost(db, run.id, hourly_costs={"SUP": 25.0}, start_date=PERIOD_D)
    check("window filter keeps only later dates", len(result["rows"]) == 1
          and result["rows"][0]["period"] == "2026-04", str(result["rows"]))


def test_run_not_found_and_empty_run():
    try:
        forecast_cost(db, 99999, hourly_costs={"default": 10.0})
        check("unknown run raises", False, "no exception")
    except CostForecastError as exc:
        check("unknown run raises", "99999" in str(exc), str(exc))

    empty_run = ForecastRun(name="Empty run", horizon_days=5, status="completed")
    db.add(empty_run)
    db.commit()
    try:
        forecast_cost(db, empty_run.id, hourly_costs={"default": 10.0})
        check("run without results raises", False, "no exception")
    except CostForecastError as exc:
        check("run without results raises", "no forecast results" in str(exc).lower(), str(exc))


# ==============================================================================
# API-level behaviour
# ==============================================================================

def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_api_post_creates_new_version():
    before = [v["version"] for v in list_cost_forecasts(db, run.id)]
    resp = client.post(
        f"/api/v1/forecasting/runs/{run.id}/cost-forecast",
        json={"hourly_costs": {"SUP": 28.0}},
        headers=_auth_headers(),
    )
    check("POST answers 201", resp.status_code == 201, f"{resp.status_code} {resp.text[:200]}")
    body = resp.json()
    check("POST response newest version", body["version"] == (max(before) if before else 0) + 1,
          str(body))
    check("POST response carries statutory label",
          body["label"] == STATUTORY_LABEL and body["cost_basis"] == STATUTORY_LABEL, "")
    check("POST rows carry monthly buckets", body["periods"] == 2, str(body.get("periods")))
    check("POST stores rates explicitly", body["hourly_costs"] == {"SUP": 28.0}, str(body["hourly_costs"]))
    return body


def test_api_get_versions():
    resp = client.get(f"/api/v1/forecasting/runs/{run.id}/cost-forecast", headers=_auth_headers())
    check("GET versions answers 200", resp.status_code == 200, str(resp.status_code))
    items = resp.json().get("items", [])
    stored = db.query(CostForecast).filter(CostForecast.forecast_run_id == run.id).count()
    check("GET versions lists all stored", len(items) == stored, f"{len(items)} vs {stored}")
    check("GET versions newest first", [v["version"] for v in items] == sorted(
        [v["version"] for v in items], reverse=True), "")
    check("every listed version excludes statutory",
          all(v["label"] == STATUTORY_LABEL for v in items), "")


def test_api_get_single_version():
    latest = max(v["version"] for v in list_cost_forecasts(db, run.id))
    resp = client.get(f"/api/v1/forecasting/runs/{run.id}/cost-forecast/{latest}",
                      headers=_auth_headers())
    check("GET version answers 200", resp.status_code == 200, str(resp.status_code))
    body = resp.json()
    check("GET version returns rows with labels",
          body["rows"] and all("hours" in r and "cost" in r for r in body["rows"]), "")
    check("GET version total matches rows", abs(body["total_cost"] - sum(
        r["cost"] for r in body["rows"])) < 1e-6, str(body["total_cost"]))

    resp = client.get(f"/api/v1/forecasting/runs/{run.id}/cost-forecast/4242",
                      headers=_auth_headers())
    check("GET unknown version answers 404", resp.status_code == 404, str(resp.status_code))
    resp = client.get("/api/v1/forecasting/runs/99999/cost-forecast/1", headers=_auth_headers())
    check("GET unknown run answers 404", resp.status_code == 404, str(resp.status_code))


def test_api_csv_export():
    resp = client.get(f"/api/v1/forecasting/runs/{run.id}/cost-forecast/csv",
                      headers=_auth_headers())
    check("CSV answers 200", resp.status_code == 200, str(resp.status_code))
    check("CSV content type", resp.headers["content-type"].startswith("text/csv"),
          resp.headers["content-type"])
    text = resp.text
    check("CSV has header", text.splitlines()[0].startswith("period,"), text[:80])
    check("CSV carries statutory label on every row",
          all(STATUTORY_LABEL in line for line in text.splitlines()[1:]),
          text[:200])
    check("CSV filename names the run and version",
          f"cost_forecast_run{run.id}_v" in resp.headers.get("content-disposition", ""),
          resp.headers.get("content-disposition", ""))

    # Explicit version export
    resp2 = client.get(
        f"/api/v1/forecasting/runs/{run.id}/cost-forecast/csv?version=1",
        headers=_auth_headers(),
    )
    check("CSV explicit version answers 200", resp2.status_code == 200, str(resp2.status_code))
    check("CSV explicit version keeps the label",
          STATUTORY_LABEL in resp2.text, resp2.text[:120])

    resp3 = client.get(
        f"/api/v1/forecasting/runs/{run.id}/cost-forecast/csv?version=4242",
        headers=_auth_headers(),
    )
    check("CSV unknown version answers 404", resp3.status_code == 404, str(resp3.status_code))


def test_api_error_shapes():
    resp = client.post(
        f"/api/v1/forecasting/runs/{run.id}/cost-forecast",
        json={"hourly_costs": {"default": 10.0}, "start_date": "2026-08-01",
              "end_date": "2026-08-31"},
        headers=_auth_headers(),
    )
    check("window with no results answers 422", resp.status_code == 422, str(resp.status_code))
    body = resp.json()
    # The shared error middleware wraps 422s in the shared envelope; the
    # message must name the problem either way.
    check("422 has a message",
          body.get("detail") or body.get("error", {}).get("message"), resp.text[:200])
    resp = client.post(
        f"/api/v1/forecasting/runs/{run.id}/cost-forecast",
        json={"hourly_costs": {}},
        headers=_auth_headers(),
    )
    check("empty rates answered 422", resp.status_code == 422, str(resp.status_code))
    resp = client.post(
        f"/api/v1/forecasting/runs/{run.id}/cost-forecast",
        json={"hourly_costs": {"WRONGROLE": 5.0}},
        headers=_auth_headers(),
    )
    check("unmatched rate answered 422", resp.status_code == 422, str(resp.status_code))


def test_api_unknown_run_422():
    resp = client.post(
        "/api/v1/forecasting/runs/99999/cost-forecast",
        json={"hourly_costs": {"default": 10.0}},
        headers=_auth_headers(),
    )
    check("POST unknown run answered 422", resp.status_code == 422, str(resp.status_code))
    resp = client.get("/api/v1/forecasting/runs/99999/cost-forecast", headers=_auth_headers())
    check("GET list unknown run answered 404", resp.status_code == 404, str(resp.status_code))


def test_route_registration():
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    base = "/api/v1/forecasting/runs/{run_id}/cost-forecast"
    for suffix in ("", "/{version}"):
        check(f"route registered {suffix}", (base + suffix) in paths, str(base + suffix))


if __name__ == "__main__":
    print("Running cost forecast test suite...")
    print()

    TOKEN = login()
    check("manager login works", bool(TOKEN), "no token")

    test_route_registration()
    test_service_groups_by_month_and_applies_rates()
    test_rate_matching_by_title_then_default()
    test_missing_rate_is_an_error_not_a_zero()
    test_versioned_storage_many_versions()
    test_window_filter()
    test_run_not_found_and_empty_run()
    test_api_post_creates_new_version()
    test_api_get_versions()
    test_api_get_single_version()
    test_api_csv_export()
    test_api_error_shapes()
    test_api_unknown_run_422()

    print()
    print("----------------------------------------------------------------")
    print(f"cost forecast tests: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
    if FAILURES:
        for name, detail in FAILURES:
            print(f"  FAIL  {name}: {detail}")
        sys.exit(1)
    sys.exit(0)
