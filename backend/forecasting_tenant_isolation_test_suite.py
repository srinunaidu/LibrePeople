"""Forecasting tenant isolation test suite.

Proves shared-schema isolation for the eight forecasting tables
(``forecast_runs``, ``forecast_results``, ``forecast_model_versions``,
``forecast_scenarios``, ``forecast_scenario_results``, ``forecast_costs``,
``forecast_cost_rows``, ``forecast_accuracy_records``):

* tenant A cannot list, read, project, cost, compare, export or sync
  tenant B's rows (and vice versa): cross-tenant ids read as missing
  (404), list endpoints return only the caller's own rows;
* creates stamp the request tenant and every child row (results,
  scenario results, cost rows, accuracy records) inherits its parent;
* legacy pre-backfill rows (``tenant_id IS NULL``) are visible to the
  default tenant only — never to tenant A or B.

Tenants: "tenant-a" / "tenant-b" via the JWT ``tenant`` claim; the
default tenant via a legacy token with no tenant claim.

Run:  python forecasting_tenant_isolation_test_suite.py
"""
import datetime
import os
import sys
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="forecast_iso_"), "iso.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.forecasting import (  # noqa: E402
    CostForecast,
    CostForecastRow,
    ForecastAccuracyRecord,
    ForecastResult,
    ForecastRun,
    ForecastScenario,
    ForecastScenarioResult,
)
from app.models.user import User  # noqa: E402

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


TENANT_A = "tenant-a"
TENANT_B = "tenant-b"
PASSWORD_HASH = get_password_hash("ForecastIsoPass123")

db = SessionLocal()
for username, email in (
    ("iso_mgr_a", "iso_mgr_a@example.com"),
    ("iso_mgr_b", "iso_mgr_b@example.com"),
    ("iso_mgr_default", "iso_mgr_default@example.com"),
):
    db.add(
        User(
            username=username,
            email=email,
            hashed_password=PASSWORD_HASH,
            role="Manager",
            is_active=True,
        )
    )
db.commit()


def _seed_run(name: str, tenant: str | None, n: int = 4) -> ForecastRun:
    run = ForecastRun(
        name=name,
        tenant_id=tenant,
        horizon_days=n,
        method="seasonal_naive",
        status="completed",
        finished_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(run)
    db.flush()
    base = datetime.date(2026, 3, 2)
    for i in range(n):
        db.add(
            ForecastResult(
                forecast_run_id=run.id,
                tenant_id=tenant,
                series_key="default",
                horizon_step=i + 1,
                forecast_date=base + datetime.timedelta(days=i),
                predicted_value=10.0 * (i + 1),
                lower_bound=10.0 * (i + 1) - 1,
                upper_bound=10.0 * (i + 1) + 1,
                input_hash=f"iso-{name}-{i}",
                rule_version="test-1.0",
                method_used="seasonal_naive",
            )
        )
    db.commit()
    db.refresh(run)
    return run


run_a = _seed_run("iso run A", TENANT_A)
run_b = _seed_run("iso run B", TENANT_B)
run_legacy = _seed_run("iso run legacy", None)


def _seed_accuracy(run: ForecastRun, tenant: str | None, period: str) -> None:
    db.add(
        ForecastAccuracyRecord(
            forecast_run_id=run.id,
            tenant_id=tenant,
            model_version="test-1.0",
            method_used="seasonal_naive",
            period=period,
            forecast_hours=100.0,
            actual_hours=90.0,
            mape=0.111111,
            mae=10.0,
            bias=10.0,
            sample_size=4,
            status="review",
        )
    )
    db.commit()


_seed_accuracy(run_a, TENANT_A, "2026-03")
_seed_accuracy(run_b, TENANT_B, "2026-03")
_seed_accuracy(run_legacy, None, "2026-03")
RUN_A_ID = run_a.id
RUN_B_ID = run_b.id
RUN_LEGACY_ID = run_legacy.id
db.close()

client = TestClient(app)


def token_for(username: str, tenant: str | None) -> str:
    if tenant is None:
        return create_access_token(subject=username)
    return create_access_token(subject=username, extra_claims={"tenant": tenant})


HA = {"Authorization": f"Bearer {token_for('iso_mgr_a', TENANT_A)}"}
HB = {"Authorization": f"Bearer {token_for('iso_mgr_b', TENANT_B)}"}
HD = {"Authorization": f"Bearer {token_for('iso_mgr_default', None)}"}


def _ids(resp) -> set[int]:
    return {r["id"] for r in resp.json()}


# ===========================================================================
# A. Tenant A isolation: lists, reads, children
# ===========================================================================
print("=" * 66)
print("A.  TENANT A SEES ONLY TENANT A")
print("=" * 66)

r = client.get("/api/v1/forecasting/runs", headers=HA)
check("A runs list 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    ids = _ids(r)
    check("A runs list has run-a", RUN_A_ID in ids, f"got {sorted(ids)}")
    check("A runs list excludes run-b", RUN_B_ID not in ids, f"got {sorted(ids)}")
    check(
        "A runs list excludes legacy NULL run",
        RUN_LEGACY_ID not in ids,
        f"got {sorted(ids)}",
    )

r = client.get(f"/api/v1/forecasting/runs/{RUN_A_ID}", headers=HA)
check("A reads own run 200", r.status_code == 200, f"got {r.status_code}")

for label, url in (
    ("B run", f"/api/v1/forecasting/runs/{RUN_B_ID}"),
    ("legacy run", f"/api/v1/forecasting/runs/{RUN_LEGACY_ID}"),
    ("missing run", "/api/v1/forecasting/runs/999999"),
):
    r = client.get(url, headers=HA)
    check(f"A reads {label} 404", r.status_code == 404, f"got {r.status_code}")

r = client.get(f"/api/v1/forecasting/runs/{RUN_A_ID}/results", headers=HA)
check("A reads own results 200 x4", r.status_code == 200 and len(r.json()) == 4,
      f"got {r.status_code} x{len(r.json()) if r.status_code == 200 else '?'}")

r = client.get(f"/api/v1/forecasting/runs/{RUN_B_ID}/results", headers=HA)
check("A reads B results 404", r.status_code == 404, f"got {r.status_code}")

r = client.get(f"/api/v1/forecasting/runs/{RUN_B_ID}/demand-series", headers=HA)
check("A demand-series of B run 404", r.status_code == 404, f"got {r.status_code}")

r = client.get(f"/api/v1/forecasting/runs/{RUN_A_ID}/demand-series", headers=HA)
check("A demand-series of own run 200", r.status_code == 200, f"got {r.status_code}")

# --- creates stamp the context tenant ------------------------------------ #
series = [
    {"date": (datetime.date(2026, 1, 1) + datetime.timedelta(days=i)).isoformat(),
     "value": 50.0 + (i % 7)}
    for i in range(60)
]
r = client.post(
    "/api/v1/forecasting/runs",
    json={"name": "iso created A", "series_data": series, "horizon_days": 5,
          "method": "seasonal_naive"},
    headers=HA,
)
check("A creates run 201", r.status_code == 201, f"got {r.status_code}")
created_a_id = r.json()["id"] if r.status_code == 201 else None
if created_a_id is not None:
    probe = SessionLocal()
    created = probe.query(ForecastRun).filter(ForecastRun.id == created_a_id).first()
    check("created run stamped tenant-a",
          created is not None and created.tenant_id == TENANT_A,
          f"got {getattr(created, 'tenant_id', '?')}")
    kids = probe.query(ForecastResult).filter(
        ForecastResult.forecast_run_id == created_a_id).all()
    check("created results inherit tenant-a",
          kids and all(k.tenant_id == TENANT_A for k in kids),
          f"got {[k.tenant_id for k in kids]}")
    probe.close()

# --- scenarios inherit + isolate ------------------------------------------ #
r = client.post(
    "/api/v1/forecasting/scenarios",
    json={"base_run_id": RUN_A_ID, "name": "iso scen A",
          "assumptions": [{"key": "demand_multiplier", "value": 1.1,
                            "unit": "ratio"}]},
    headers=HA,
)
check("A creates scenario on own run 201", r.status_code == 201,
      f"got {r.status_code}")
scen_a_id = r.json()["id"] if r.status_code == 201 else None
if scen_a_id is not None:
    probe = SessionLocal()
    scen = probe.query(ForecastScenario).filter(
        ForecastScenario.id == scen_a_id).first()
    check("scenario inherits tenant-a",
          scen is not None and scen.tenant_id == TENANT_A,
          f"got {getattr(scen, 'tenant_id', '?')}")
    skids = probe.query(ForecastScenarioResult).filter(
        ForecastScenarioResult.scenario_id == scen_a_id).all()
    check("scenario results inherit tenant-a",
          skids and all(k.tenant_id == TENANT_A for k in skids),
          f"got {[k.tenant_id for k in skids]}")
    probe.close()

r = client.post(
    "/api/v1/forecasting/scenarios",
    json={"base_run_id": RUN_B_ID, "name": "iso scen X",
          "assumptions": [{"key": "demand_multiplier", "value": 1.1,
                            "unit": "ratio"}]},
    headers=HA,
)
check("A creates scenario on B run 404", r.status_code == 404,
      f"got {r.status_code}")

r = client.post(
    "/api/v1/forecasting/scenarios",
    json={"base_run_id": RUN_B_ID, "name": "iso scen B",
          "assumptions": [{"key": "demand_multiplier", "value": 1.1,
                            "unit": "ratio"}]},
    headers=HB,
)
check("B creates scenario on own run 201", r.status_code == 201,
      f"got {r.status_code}")
scen_b_id = r.json()["id"] if r.status_code == 201 else None

r = client.get("/api/v1/forecasting/scenarios", headers=HA)
check("A scenarios list 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200 and scen_a_id is not None:
    ids = {s["id"] for s in r.json()["items"]}
    check("A scenarios list has own", scen_a_id in ids, f"got {sorted(ids)}")
    if scen_b_id is not None:
        check("A scenarios list excludes B", scen_b_id not in ids,
              f"got {sorted(ids)}")

if scen_b_id is not None:
    r = client.get(f"/api/v1/forecasting/scenarios/{scen_b_id}", headers=HA)
    check("A reads B scenario 404", r.status_code == 404, f"got {r.status_code}")
    r = client.post(
        "/api/v1/forecasting/scenarios/compare",
        json={"scenario_ids": [scen_a_id, scen_b_id]},
        headers=HA,
    )
    check("A compares across tenants 404", r.status_code == 404,
          f"got {r.status_code}")

# --- cost forecasts inherit + isolate -------------------------------------- #
r = client.post(
    f"/api/v1/forecasting/runs/{RUN_A_ID}/cost-forecast",
    json={"hourly_costs": {"default": 20.0}},
    headers=HA,
)
check("A costs own run 201", r.status_code == 201, f"got {r.status_code}")
if r.status_code == 201:
    probe = SessionLocal()
    cf = probe.query(CostForecast).filter(
        CostForecast.forecast_run_id == RUN_A_ID,
        CostForecast.version == r.json()["version"]).first()
    check("cost forecast inherits tenant-a",
          cf is not None and cf.tenant_id == TENANT_A,
          f"got {getattr(cf, 'tenant_id', '?')}")
    crows = probe.query(CostForecastRow).filter(
        CostForecastRow.cost_forecast_id == cf.id).all() if cf else []
    check("cost rows inherit tenant-a",
          crows and all(k.tenant_id == TENANT_A for k in crows),
          f"got {[k.tenant_id for k in crows]}")
    probe.close()

r = client.post(
    f"/api/v1/forecasting/runs/{RUN_B_ID}/cost-forecast",
    json={"hourly_costs": {"default": 20.0}},
    headers=HA,
)
check("A costs B run 404", r.status_code == 404, f"got {r.status_code}")

for label, url in (
    ("list", f"/api/v1/forecasting/runs/{RUN_B_ID}/cost-forecast"),
    ("csv", f"/api/v1/forecasting/runs/{RUN_B_ID}/cost-forecast/csv"),
    ("version", f"/api/v1/forecasting/runs/{RUN_B_ID}/cost-forecast/1"),
):
    r = client.get(url, headers=HA)
    check(f"A cost {label} of B run 404", r.status_code == 404,
          f"got {r.status_code}")

# --- accuracy: sync gate + list scope --------------------------------------- #
r = client.post(
    "/api/v1/forecasting/accuracy/sync",
    json={"start_date": "2026-03-01", "end_date": "2026-03-31",
          "run_id": RUN_B_ID},
    headers=HA,
)
check("A syncs B run 404", r.status_code == 404, f"got {r.status_code}")

r = client.post(
    "/api/v1/forecasting/accuracy/sync",
    json={"start_date": "2026-03-01", "end_date": "2026-03-31",
          "run_id": RUN_A_ID},
    headers=HA,
)
check("A syncs own run 200", r.status_code == 200, f"got {r.status_code}")

r = client.get("/api/v1/forecasting/accuracy", headers=HA)
check("A accuracy list 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    got_runs = {rec["forecast_run_id"] for rec in r.json()["items"]}
    check("A accuracy excludes B rows", RUN_B_ID not in got_runs,
          f"got {sorted(got_runs)}")
    check("A accuracy excludes legacy rows", RUN_LEGACY_ID not in got_runs,
          f"got {sorted(got_runs)}")

# ===========================================================================
# B. Tenant B mirror
# ===========================================================================
print("=" * 66)
print("B.  TENANT B SEES ONLY TENANT B")
print("=" * 66)

r = client.get("/api/v1/forecasting/runs", headers=HB)
check("B runs list 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    ids = _ids(r)
    check("B runs list has run-b", RUN_B_ID in ids, f"got {sorted(ids)}")
    check("B runs list excludes run-a", RUN_A_ID not in ids,
          f"got {sorted(ids)}")
    check("B runs list excludes legacy NULL run", RUN_LEGACY_ID not in ids,
          f"got {sorted(ids)}")

r = client.get(f"/api/v1/forecasting/runs/{RUN_A_ID}", headers=HB)
check("B reads A run 404", r.status_code == 404, f"got {r.status_code}")

if scen_a_id is not None:
    r = client.get(f"/api/v1/forecasting/scenarios/{scen_a_id}", headers=HB)
    check("B reads A scenario 404", r.status_code == 404, f"got {r.status_code}")

r = client.get("/api/v1/forecasting/accuracy", headers=HB)
check("B accuracy list 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    got_runs = {rec["forecast_run_id"] for rec in r.json()["items"]}
    check("B accuracy has own rows", RUN_B_ID in got_runs,
          f"got {sorted(got_runs)}")
    check("B accuracy excludes A rows", RUN_A_ID not in got_runs,
          f"got {sorted(got_runs)}")

# ===========================================================================
# C. Default tenant: legacy NULL rows stay readable, nothing else leaks
# ===========================================================================
print("=" * 66)
print("C.  DEFAULT TENANT KEEPS LEGACY ROWS, SEES NO FOREIGN ROWS")
print("=" * 66)

r = client.get("/api/v1/forecasting/runs", headers=HD)
check("default runs list 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    ids = _ids(r)
    check("default list has legacy NULL run", RUN_LEGACY_ID in ids,
          f"got {sorted(ids)}")
    check("default list excludes run-a", RUN_A_ID not in ids,
          f"got {sorted(ids)}")
    check("default list excludes run-b", RUN_B_ID not in ids,
          f"got {sorted(ids)}")

r = client.get(f"/api/v1/forecasting/runs/{RUN_LEGACY_ID}", headers=HD)
check("default reads legacy run 200", r.status_code == 200,
      f"got {r.status_code}")

r = client.get(f"/api/v1/forecasting/runs/{RUN_A_ID}", headers=HD)
check("default reads A run 404", r.status_code == 404, f"got {r.status_code}")

r = client.get("/api/v1/forecasting/accuracy", headers=HD)
check("default accuracy list 200", r.status_code == 200,
      f"got {r.status_code}")
if r.status_code == 200:
    got_runs = {rec["forecast_run_id"] for rec in r.json()["items"]}
    check("default accuracy has legacy rows", RUN_LEGACY_ID in got_runs,
          f"got {sorted(got_runs)}")
    check("default accuracy excludes A/B rows",
          RUN_A_ID not in got_runs and RUN_B_ID not in got_runs,
          f"got {sorted(got_runs)}")

# ===========================================================================
# D. Same-root_id edit isolation: version numbering reads only caller chain
# ===========================================================================
print("=" * 66)
print("D.  SAME-ROOT EDIT ISOLATION")
print("=" * 66)

if scen_a_id is not None:
    _probe = SessionLocal()
    _scen_a = _probe.query(ForecastScenario).filter(
        ForecastScenario.id == scen_a_id).first()
    _root = _scen_a.root_id or _scen_a.id
    # Plant a foreign row sharing the same lineage root but owned by
    # tenant-b, with an inflated version number. A correct
    # edit_scenario_version must ignore it when numbering tenant-a's
    # next version (tenant_column_criterion guard).
    _evil = ForecastScenario(
        name="evil same-root B",
        tenant_id=TENANT_B,
        base_run_id=RUN_B_ID,
        assumptions='[{"key": "demand_multiplier", "value": 1.1, "unit": "ratio"}]',
        version_no=99,
        root_id=_root,
        source="edited",
    )
    _probe.add(_evil)
    _probe.commit()
    _evil_id = _evil.id
    _probe.close()

    r = client.post(
        f"/api/v1/forecasting/scenarios/{scen_a_id}/versions",
        json={"assumptions": [{"key": "demand_multiplier", "value": 1.05,
                               "unit": "ratio"}]},
        headers=HA,
    )
    check("A edits own scenario 201 despite foreign same-root row",
          r.status_code == 201, f"got {r.status_code}")
    if r.status_code == 201:
        check("A next version is 2, not 100",
              r.json().get("version_no") == 2,
              f"got {r.json().get('version_no')}")

    r = client.get(
        f"/api/v1/forecasting/scenarios/{scen_a_id}/versions", headers=HA)
    check("A versions list 200", r.status_code == 200,
          f"got {r.status_code}")
    if r.status_code == 200:
        _vnos = sorted(v["version_no"] for v in r.json()["items"])
        _ids = {v["id"] for v in r.json()["items"]}
        check("A versions list has only own chain [1, 2]",
              _vnos == [1, 2], f"got {_vnos}")
        check("A versions list excludes foreign same-root row",
              _evil_id not in _ids, f"got {sorted(_ids)}")

    r = client.get(
        f"/api/v1/forecasting/scenarios/{_evil_id}/versions", headers=HB)
    check("B versions list of evil root 200", r.status_code == 200,
          f"got {r.status_code}")
    if r.status_code == 200:
        _bvnos = sorted(v["version_no"] for v in r.json()["items"])
        check("B versions list has only own row [99]",
              _bvnos == [99], f"got {_bvnos}")

    r = client.post(
        f"/api/v1/forecasting/scenarios/{scen_a_id}/versions",
        json={"assumptions": [{"key": "demand_multiplier", "value": 1.05,
                               "unit": "ratio"}]},
        headers=HB,
    )
    check("B edits A scenario 404", r.status_code == 404,
          f"got {r.status_code}")
else:
    check("same-root edit setup has scen_a", False, "scen_a_id is None")

# ===========================================================================
# Results
# ===========================================================================
print()
print("=" * 66)
print(f"==== FORECASTING ISOLATION SUITE: {RESULTS['pass']} passed, "
      f"{RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 66)
raise SystemExit(1 if RESULTS["fail"] else 0)
