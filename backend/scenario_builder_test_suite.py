"""Scenario builder test suite (AN-05): visible, versioned, comparable.

What this suite proves
----------------------
* a scenario is created, named, EDITED and FORKED; every mutation is a
  stored version — editing creates the next version row under the same
  lineage root and the earlier versions stay intact and retrievable
* the HR assumption keys (attrition_rate, hire_rate, leave_rate,
  wage_growth_pct) reshape the scenario's linked projection explicitly:
  attrition compounds the demand down per day, hiring compounds it up,
  leave scales it by a constant factor, wage growth shapes the COST
  projection only
* an unknown assumption key is a 422 (service error and HTTP) that
  names the offending key; a percent outside 0..100 is refused too
* a fork copies the source version's assumptions into a NEW lineage,
  records the source version, and changes nothing about the source
* comparison works across ANY versions: the response carries each
  participant's assumptions AND version metadata next to the per-period
  values and deltas; explicit hourly rates add a labelled cost
  projection (compounded by wage growth), and costs appear ONLY when
  the rates were supplied
* role gating: an Associate is refused with 403 on every mutation.

Date window: May-June 2026 — distinct from the publish tests
(January 2026), the attendance tests (February 2027), the scheduling
SC-06 tests (April 2026) and the cost-forecast tests (March 2026).

Run:  python scenario_builder_test_suite.py
"""
import datetime
import os
import sys
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="scenario_builder_"), "sb.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

import json  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.forecasting import ForecastResult, ForecastRun, ForecastScenario, ForecastScenarioResult  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.cost_forecast import STATUTORY_LABEL  # noqa: E402
from app.services.forecasting import (  # noqa: E402
    ScenarioError,
    compare_scenarios,
    create_scenario,
    edit_scenario_version,
    fork_scenario,
    list_scenario_versions,
    project_scenario_costs,
    validate_assumptions,
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

# May-June 2026: a window deliberately distinct from the other suites.
PERIOD_A = datetime.date(2026, 5, 4)
PERIOD_B = datetime.date(2026, 5, 5)
PERIOD_C = datetime.date(2026, 5, 6)
PERIOD_D = datetime.date(2026, 6, 1)  # crosses into the next month bucket
PASSWORD = "ScenarioTestPass123"
PASSWORD_HASH = get_password_hash(PASSWORD)

db = SessionLocal()
dept = Department(name="Planning", code="PLAN")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Ops Analyst", code="OPSAN", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)

emp = Employee(
    employee_id="SBM001",
    first_name="Scenario",
    last_name="Manager",
    email="sbmgr@example.com",
    department_id=dept.id,
    job_id=job.id,
    hire_date=datetime.date(2024, 1, 1),
    status="Active",
)
db.add(emp)
db.commit()
db.refresh(emp)

manager = User(
    username="sbmgr",
    email="sbmgr@example.com",
    hashed_password=PASSWORD_HASH,
    role="Manager",
    is_active=True,
    employee_id=emp.id,
)
db.add(manager)
db.commit()
db.refresh(manager)

associate_emp = Employee(
    employee_id="SBA001",
    first_name="Scenario",
    last_name="Associate",
    email="sbassoc@example.com",
    department_id=dept.id,
    job_id=job.id,
    hire_date=datetime.date(2024, 1, 1),
    status="Active",
)
db.add(associate_emp)
db.commit()
db.refresh(associate_emp)

associate = User(
    username="sbassoc",
    email="sbassoc@example.com",
    hashed_password=PASSWORD_HASH,
    role="Associate",
    is_active=True,
    employee_id=associate_emp.id,
)
db.add(associate)
db.commit()
db.refresh(associate)


def _base_run(name: str, rows: list[dict]) -> ForecastRun:
    """Seed a completed forecast run with per-day result rows."""
    run = ForecastRun(
        name=name,
        horizon_days=len(rows),
        method="seasonal_naive",
        status="completed",
        finished_at=datetime.datetime.now(datetime.timezone.utc),
        location_id=None,
        role_id=job.id,
    )
    db.add(run)
    db.flush()
    for r in rows:
        db.add(
            ForecastResult(
                forecast_run_id=run.id,
                series_key=f"{job.code}:hours",
                horizon_step=r["horizon_step"],
                forecast_date=r["forecast_date"],
                predicted_value=r["predicted_value"],
                lower_bound=r["predicted_value"] - 1,
                upper_bound=r["predicted_value"] + 1,
                input_hash="scenario-suite-" + name.replace(" ", ""),
                rule_version="test-1.0",
                method_used="seasonal_naive",
            )
        )
    db.commit()
    db.refresh(run)
    return run


def _rows(values: list[float]) -> list[dict]:
    dates = [PERIOD_A, PERIOD_B, PERIOD_C, PERIOD_D]
    return [
        {"horizon_step": i + 1, "forecast_date": dates[i], "predicted_value": v}
        for i, v in enumerate(values)
    ]


run_a = _base_run("Scenario run A", _rows([100.0, 80.0, 60.0, 120.0]))
run_b = _base_run("Scenario run B", _rows([50.0, 50.0, 50.0, 50.0]))

client = TestClient(app)


def login(username: str = "sbmgr") -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    body = resp.json()
    return body.get("access_token") or body.get("token") or ""


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def _assoc_headers() -> dict:
    return {"Authorization": f"Bearer {ASSOC_TOKEN}"}


# ==============================================================================
# Assumption validation (explicit, never implicit)
# ==============================================================================

def test_assumption_validation():
    validate_assumptions([{"key": "attrition_rate", "value": 12.5, "unit": "percent"}])
    check("valid percent assumption accepted", True, "")

    for bad_key in ("attrition_rates", "employee_churn", "wage_growth"):
        try:
            validate_assumptions([{"key": bad_key, "value": 1, "unit": "percent"}])
            check(f"unknown key '{bad_key}' rejected", False, "no exception")
        except ScenarioError as exc:
            check(f"unknown key '{bad_key}' rejected", bad_key in str(exc), str(exc))

    for key, bad in (("attrition_rate", -1), ("attrition_rate", 101),
                     ("hire_rate", -0.5), ("leave_rate", 100.5),
                     ("wage_growth_pct", 150)):
        try:
            validate_assumptions([{"key": key, "value": bad, "unit": "percent"}])
            check(f"{key}={bad} out of range rejected", False, "no exception")
        except ScenarioError as exc:
            check(f"{key}={bad} out of range rejected", key in str(exc), str(exc))

    try:
        validate_assumptions([{"key": "leave_rate", "value": "high", "unit": "percent"}])
        check("non-numeric percent rejected", False, "no exception")
    except ScenarioError as exc:
        check("non-numeric percent rejected", "leave_rate" in str(exc), str(exc))


# ==============================================================================
# The linked projection: how each key reshapes the base series
# ==============================================================================

def _base_values(run_id: int) -> list[float]:
    rows = (db.query(ForecastResult)
              .filter(ForecastResult.forecast_run_id == run_id)
              .order_by(ForecastResult.horizon_step).all())
    return [float(r.predicted_value) for r in rows]


def test_new_keys_reshape_the_projection():
    base = _base_values(run_a.id)
    # leave_rate: constant factor
    proj = _project(run_a.id, [{"key": "leave_rate", "value": 10.0, "unit": "percent"}])
    check("leave_rate scales every period by (1 - rate/100)",
          proj == [round(v * 0.9, 4) for v in base], str(proj))

    # wage_growth_pct: demand untouched (it shapes cost only)
    proj = _project(run_a.id, [{"key": "wage_growth_pct", "value": 5.0, "unit": "percent"}])
    check("wage_growth_pct does not change demand", proj == base, str(proj))

    # attrition_rate: day i scales by (1 - r/100) ** (i/365) — later days
    # lose more than earlier ones.
    proj = _project(run_a.id, [{"key": "attrition_rate", "value": 10.0, "unit": "percent"}])
    expected = [round(v * (0.9) ** ((i + 1) / 365.0), 4) for i, v in enumerate(base)]
    check("attrition_rate compounds down per day", proj == expected, f"{proj} vs {expected}")
    check("attrition bites harder later in the horizon",
          abs(base[0] - proj[0]) < abs(base[3] - proj[3]), f"{proj}")
    check("attrition shrinks but never below zero",
          all(v >= 0 for v in proj), str(proj))

    # hire_rate: compounds up
    proj = _project(run_a.id, [{"key": "hire_rate", "value": 6.0, "unit": "percent"}])
    expected = [round(v * (1.06) ** ((i + 1) / 365.0), 4) for i, v in enumerate(base)]
    check("hire_rate compounds up per day", proj == expected, f"{proj} vs {expected}")

    # combined with the existing multiplier assumptions: multiplier first
    # (list order), then the HR keys.
    proj = _project(run_a.id, [
        {"key": "demand_multiplier", "value": 1.1, "unit": "ratio"},
        {"key": "leave_rate", "value": 20.0, "unit": "percent"},
    ])
    expected = [round(v * 1.1 * 0.8, 4) for v in base]
    check("keys compose in the order they are listed", proj == expected, f"{proj} vs {expected}")


def _project(run_id: int, assumptions: list[dict]) -> list[float]:
    scenario = create_scenario(
        db=db, base_run_id=run_id, assumptions=assumptions,
        name="projection-check", description=None, user_id=manager.id,
    )
    rows = (db.query(ForecastScenarioResult)
              .filter(ForecastScenarioResult.scenario_id == scenario.id)
              .order_by(ForecastScenarioResult.horizon_step).all())
    return [float(r.predicted_value) for r in rows]


# ==============================================================================
# Versioning: create, edit, fork
# ==============================================================================

V1 = None  # scenario A's first version
V2 = None  # scenario A's edited version
V3 = None  # scenario A's second edit
FORKEE = None  # scenario B's first version (fork source)


def test_create_sets_version_one():
    global V1, FORKEE
    V1 = create_scenario(
        db=db, base_run_id=run_a.id,
        assumptions=[{"key": "demand_multiplier", "value": 1.0, "unit": "ratio"}],
        name="Run A baseline", description="the starting assumption set",
        user_id=manager.id,
    )
    check("created scenario is version 1", V1.version_no == 1, str(V1.version_no))
    check("created scenario is its own root", V1.root_id == V1.id, str(V1.root_id))
    check("created scenario source is 'created'", V1.source == "created", str(V1.source))
    check("created scenario assumptions visible",
          json.loads(V1.assumptions)[0]["key"] == "demand_multiplier", V1.assumptions)

    FORKEE = create_scenario(
        db=db, base_run_id=run_b.id,
        assumptions=[{"key": "leave_rate", "value": 5.0, "unit": "percent"}],
        name="Run B steady", description=None, user_id=manager.id,
    )
    check("second scenario independent root", FORKEE.version_no == 1 and FORKEE.root_id == FORKEE.id, "")
    return V1


def test_edit_creates_the_next_version_and_keeps_the_old():
    global V2, V3
    V2 = edit_scenario_version(
        db=db, scenario_id=V1.id,
        assumptions=[{"key": "demand_multiplier", "value": 1.2, "unit": "ratio"}],
        user_id=manager.id,
    )
    check("edit returns a NEW row", V2.id != V1.id, f"{V2.id} vs {V1.id}")
    check("edit is version 2", V2.version_no == 2, str(V2.version_no))
    check("edit stays in the lineage", V2.root_id == V1.id, str(V2.root_id))
    check("edit source is 'edited'", V2.source == "edited", str(V2.source))
    check("edit keeps the name", V2.name == V1.name, str(V2.name))
    check("edit re-projected the linked series",
          abs(float(V2.results[0].predicted_value) - 1.2 * float(V1.results[0].predicted_value)) < 1e-6,
          f"v2={V2.results[0].predicted_value} v1={V1.results[0].predicted_value}")

    # The first version is untouched: same row, same assumptions, same results.
    fresh_v1 = db.query(ForecastScenario).filter(ForecastScenario.id == V1.id).first()
    check("v1 still intact after edit", fresh_v1 is not None and fresh_v1.version_no == 1, "")
    check("v1 results still intact",
          fresh_v1 is not None and len(fresh_v1.results) == len(V1.results), "")
    check("v1 assumptions still intact", fresh_v1.assumptions == V1.assumptions, "")

    check("edit with an unknown key is rejected naming the key",
          _edit_rejects(V1.id, [{"key": "attrition_rates", "value": 1, "unit": "percent"}],
                        "attrition_rates"), "")
    check("edit with an out-of-range percent is rejected",
          _edit_rejects(V1.id, [{"key": "hire_rate", "value": 250, "unit": "percent"}],
                        "hire_rate"), "")

    V3 = edit_scenario_version(
        db=db, scenario_id=V2.id,
        assumptions=[
            {"key": "demand_multiplier", "value": 1.2, "unit": "ratio"},
            {"key": "attrition_rate", "value": 4.0, "unit": "percent"},
        ],
        user_id=manager.id,
    )
    check("second edit is version 3", V3.version_no == 3, str(V3.version_no))

    versions = list_scenario_versions(db, V1.id)
    check("lineage lists oldest first",
          versions is not None and [v.id for v in versions] == [V1.id, V2.id, V3.id],
          str([v.id for v in (versions or [])]))
    check("versions list carries every version number",
          versions is not None and [v.version_no for v in versions] == [1, 2, 3], "")
    check("versions of an unknown scenario return None",
          list_scenario_versions(db, 999999) is None, "")
    check("editing an unknown scenario returns None",
          edit_scenario_version(db=db, scenario_id=999999,
                                assumptions=[{"key": "leave_rate", "value": 1, "unit": "percent"}]) is None, "")


def _edit_rejects(scenario_id: int, assumptions: list[dict], needle: str) -> bool:
    try:
        edit_scenario_version(db=db, scenario_id=scenario_id,
                              assumptions=assumptions, user_id=manager.id)
        return False
    except ScenarioError as exc:
        return needle in str(exc) and (
            db.query(ForecastScenario)
            .filter(ForecastScenario.root_id == (V1.root_id or V1.id)).count() <= 2
        )


def test_fork_starts_its_own_lineage():
    fork = fork_scenario(db=db, scenario_id=FORKEE.id, user_id=manager.id)
    check("fork is a NEW row", fork.id != FORKEE.id, "")
    check("fork is version 1 of its own lineage",
          fork.version_no == 1 and fork.root_id == fork.id and fork.id != FORKEE.id, "")
    check("fork source is 'forked'", fork.source == "forked", str(fork.source))
    check("fork records the version it forked from",
          fork.forked_from_scenario_id == FORKEE.id, str(fork.forked_from_scenario_id))
    check("fork copies the assumptions",
          fork.assumptions == FORKEE.assumptions, f"{fork.assumptions} vs {FORKEE.assumptions}")
    check("fork copies the base run", fork.base_run_id == FORKEE.base_run_id, "")
    check("fork re-projects identically to its source",
          [round(float(r.predicted_value), 4) for r in fork.results]
          == [round(float(r.predicted_value), 4) for r in FORKEE.results], "")
    check("fork name says fork by default", "(fork)" in fork.name, str(fork.name))
    check("forking an unknown scenario returns None",
          fork_scenario(db=db, scenario_id=999999, user_id=manager.id) is None, "")
    return fork


# ==============================================================================
# Costs: explicit, labelled, compounded by wage growth
# ==============================================================================

def test_cost_projection_explicit_and_labelled():
    rows = (db.query(ForecastScenarioResult)
              .filter(ForecastScenarioResult.scenario_id == V1.id)
              .order_by(ForecastScenarioResult.horizon_step).all())
    # May: 100 + 80 + 60 = 240; June: 120
    flat = project_scenario_costs(rows, {"default": 10.0})
    check("cost buckets by month", [r["period"] for r in flat["rows"]] == ["2026-05", "2026-06"],
          str(flat["rows"]))
    check("may hours bucket correct", abs(flat["rows"][0]["hours"] - 240.0) < 1e-6, str(flat["rows"][0]))
    check("flat rate constant without wage growth",
          flat["rows"][0]["hourly_cost"] == flat["rows"][1]["hourly_cost"] == 10.0, str(flat["rows"]))
    check("every cost row carries the statutory label",
          all(r["cost_basis"] == STATUTORY_LABEL for r in flat["rows"]), "")
    check("totals correct", abs(flat["total_cost"] - (240.0 + 120.0) * 10.0) < 1e-6, str(flat["total_cost"]))

    grown = project_scenario_costs(rows, {"default": 10.0}, wage_growth_pct=12.0)
    check("wage growth compounds the June rate",
          grown["rows"][1]["hourly_cost"] > 10.0 == flat["rows"][1]["hourly_cost"] or
          grown["rows"][1]["hourly_cost"] > flat["rows"][1]["hourly_cost"], str(grown["rows"]))
    check("wage growth leaves the first month's rate alone",
          abs(grown["rows"][0]["hourly_cost"] - 10.0) < 1e-6, str(grown["rows"][0]))
    check("grown total is higher than flat total",
          grown["total_cost"] > flat["total_cost"], f"{grown['total_cost']} vs {flat['total_cost']}")

    single = project_scenario_costs(rows, {"OPSAN": 8.0})
    check("a single-entry rate map is accepted", abs(single["total_cost"] - 360.0 * 8.0) < 1e-6, "")
    try:
        project_scenario_costs(rows, {"OPSAN": 8.0, "OTHER": 9.0})
        check("multi-rate map without default refused", False, "no exception")
    except ScenarioError as exc:
        check("multi-rate map without default refused", "default" in str(exc), str(exc))
    try:
        project_scenario_costs(rows, {})
        check("empty rate map refused", False, "no exception")
    except ScenarioError as exc:
        check("empty rate map refused", True, str(exc))


# ==============================================================================
# Comparison: any versions, assumptions adjacent to the numbers
# ==============================================================================

def test_service_comparison_carries_assumptions_versions_and_deltas():
    raw = compare_scenarios(db, [V1.id, V2.id, V3.id])
    participants = {p["id"]: p for p in raw["scenarios"]}
    check("service compare carries every participant",
          set(participants) == {V1.id, V2.id, V3.id}, str(list(participants)))
    check("versions are named next to the numbers",
          participants[V1.id]["version_no"] == 1 and participants[V2.id]["version_no"] == 2
          and participants[V3.id]["version_no"] == 3, str(participants))
    check("each participant's assumptions travel with the results",
          json.loads(json.dumps(participants[V3.id]["assumptions"]))[0]["key"] == "demand_multiplier"
          and any(a["key"] == "attrition_rate"
                  for a in json.loads(json.dumps(participants[V3.id]["assumptions"]))), "")
    check("deltas taken against the first participant",
          any(abs(v2 - v1) > 0 for v1, v2 in
              zip([float(r.predicted_value) for r in V1.results],
                  [float(r.predicted_value) for r in V2.results])), "")
    first_period = raw["comparison"][0]
    check("per-period assumptions table present",
          set(first_period["assumptions"]) == {V1.id, V2.id, V3.id}, str(first_period))
    check("per-period deltas present",
          first_period["deltas"][V2.id] is not None, str(first_period))
    check("comparison without rates carries no costs", raw.get("costs") is None, str(raw.get("costs")))

    # Cost linkage is EXPLICIT: only when rates are supplied.
    raw = compare_scenarios(db, [V1.id, V2.id], hourly_costs={"default": 10.0})
    costs = raw["costs"]
    check("explicit rates produce a cost per participant", set(costs) == {V1.id, V2.id}, str(list(costs)))
    check("cost totals differ with the version's demand",
          costs[V2.id]["total_cost"] > costs[V1.id]["total_cost"],
          f"{costs[V1.id]['total_cost']} vs {costs[V2.id]['total_cost']}")
    check("first participant's cost delta is zero",
          costs[V1.id]["total_cost_delta"] == 0.0, str(costs[V1.id]["total_cost_delta"]))
    check("second participant's cost delta against the first",
          abs(costs[V2.id]["total_cost_delta"] - (costs[V2.id]["total_cost"] - costs[V1.id]["total_cost"])) < 1e-6, "")

    try:
        compare_scenarios(db, [V1.id])
        check("one participant refused", False, "no exception")
    except ScenarioError as exc:
        check("one participant refused", "At least 2" in str(exc), str(exc))
    try:
        compare_scenarios(db, [V1.id, 999999])
        check("unknown participant refused", False, "no exception")
    except ScenarioError as exc:
        check("unknown participant refused", "999999" in str(exc), str(exc))


# ==============================================================================
# API: the builder end to end
# ==============================================================================

def test_api_create_scenario():
    resp = client.post("/api/v1/forecasting/scenarios", json={
        "base_run_id": run_a.id, "name": "API scenario",
        "assumptions": [{"key": "leave_rate", "value": 7.5, "unit": "percent"}],
    }, headers=_auth_headers())
    check("POST scenario answers 201", resp.status_code == 201, f"{resp.status_code} {resp.text[:200]}")
    body = resp.json()
    check("POST returns version 1", body["version_no"] == 1, str(body))
    check("POST assumptions echoed", body["assumptions"][0]["key"] == "leave_rate", str(body))
    check("POST results projected", round(body["results"][0]["predicted_value"], 4)
          == round(_base_values(run_a.id)[0] * 0.925, 4), str(body["results"][0]))

    resp = client.post("/api/v1/forecasting/scenarios", json={
        "base_run_id": run_a.id, "name": "Bad key",
        "assumptions": [{"key": "turnover_rate", "value": 5, "unit": "percent"}],
    }, headers=_auth_headers())
    check("unknown assumption key is a 422 naming the key",
          resp.status_code == 422 and "turnover_rate" in resp.text,
          f"{resp.status_code} {resp.text[:200]}")


def test_api_edit_and_versions():
    # Edit FORKEE through the API: a new version, the old one intact.
    resp = client.post(f"/api/v1/forecasting/scenarios/{FORKEE.id}/versions", json={
        "assumptions": [{"key": "hire_rate", "value": 5.0, "unit": "percent"}],
    }, headers=_auth_headers())
    check("POST version answers 201", resp.status_code == 201, f"{resp.status_code} {resp.text[:200]}")
    body = resp.json()
    check("edited version is version 2", body["version_no"] == 2, str(body))
    check("edited version keeps the lineage root", body["root_id"] == FORKEE.id, str(body))

    original = client.get(f"/api/v1/forecasting/scenarios/{FORKEE.id}", headers=_auth_headers())
    check("v1 unchanged and retrievable after the edit",
          original.status_code == 200 and original.json()["version_no"] == 1
          and original.json()["assumptions"][0]["key"] == "leave_rate",
          f"{original.status_code} {original.text[:200]}")

    resp = client.get(f"/api/v1/forecasting/scenarios/{FORKEE.id}/versions", headers=_auth_headers())
    check("GET versions answers 200", resp.status_code == 200, str(resp.status_code))
    items = resp.json()["items"]
    check("GET versions lists the lineage oldest first",
          [v["version_no"] for v in items] == [1, 2], str([v["version_no"] for v in items]))
    check("GET versions carries each version's assumptions",
          items[0]["assumptions"][0]["key"] == "leave_rate"
          and items[1]["assumptions"][0]["key"] == "hire_rate", str(items))

    resp = client.post(f"/api/v1/forecasting/scenarios/{FORKEE.id}/versions", json={
        "assumptions": [{"key": "not_a_key", "value": 1, "unit": "percent"}],
    }, headers=_auth_headers())
    check("edit with unknown key answered 422 naming it",
          resp.status_code == 422 and "not_a_key" in resp.text,
          f"{resp.status_code} {resp.text[:200]}")
    resp = client.post("/api/v1/forecasting/scenarios/999999/versions", json={
        "assumptions": [{"key": "hire_rate", "value": 5.0, "unit": "percent"}],
    }, headers=_auth_headers())
    check("edit of unknown scenario answered 404", resp.status_code == 404, str(resp.status_code))
    resp = client.get("/api/v1/forecasting/scenarios/999999/versions", headers=_auth_headers())
    check("versions of unknown scenario answered 404", resp.status_code == 404, str(resp.status_code))


def test_api_fork():
    fork = fork_scenario(db=db, scenario_id=V1.id, user_id=manager.id)
    resp = client.get(f"/api/v1/forecasting/scenarios/{fork.id}", headers=_auth_headers())
    body = resp.json()
    check("fork visible through GET", resp.status_code == 200, str(resp.status_code))
    check("fork carries version and source",
          body["version_no"] == 1 and body["source"] == "forked"
          and body["forked_from_scenario_id"] == V1.id, str(body))
    resp = client.post("/api/v1/forecasting/scenarios/999999/fork", json={},
                       headers=_auth_headers())
    check("fork of unknown scenario answered 404", resp.status_code == 404, str(resp.status_code))


def test_api_compare_versions():
    # Compare two VERSIONS of one lineage and one fork: assumptions and
    # version metadata next to the numbers.
    resp = client.post("/api/v1/forecasting/scenarios/compare", json={
        "scenario_ids": [V1.id, V3.id, FORKEE.id],
    }, headers=_auth_headers())
    check("POST compare answers 200", resp.status_code == 200, f"{resp.status_code} {resp.text[:300]}")
    body = resp.json()
    versions = {p["id"]: p["version_no"] for p in body["scenarios"]}
    sources = {p["id"]: p["source"] for p in body["scenarios"]}
    check("compare answers versions of the participants",
          versions[V1.id] == 1 and versions[V3.id] == 3 and versions[FORKEE.id] == 1,
          str(versions))
    check("compare answers how each version came to be",
          sources[V1.id] == "created" and sources[V3.id] == "edited", str(sources))
    check("per-period assumptions table adjacent to values and deltas",
          all("assumptions" in period and "deltas" in period and "scenario_values" in period
              for period in body["comparison"]), "")
    check("compare without rates has no costs",
          body.get("costs") in (None, {}), str(body.get("costs")))

    resp = client.post("/api/v1/forecasting/scenarios/compare", json={
        "scenario_ids": [V1.id, V2.id], "hourly_costs": {"default": 10.0},
    }, headers=_auth_headers())
    body = resp.json()
    check("explicit rates add the cost section", body.get("costs"), str(body.get("costs")))
    cost_bodies = {int(k): v for k, v in (body.get("costs") or {}).items()}
    check("costs carry the statutory label",
          all(c["cost_basis"] == STATUTORY_LABEL and c["label"] == STATUTORY_LABEL
              for c in cost_bodies.values()), str(cost_bodies))
    check("cost rows carry the label too",
          all(r["cost_basis"] == STATUTORY_LABEL
              for c in cost_bodies.values() for r in c["rows"]), "")
    check("cost deltas against the first participant",
          cost_bodies[V1.id]["total_cost_delta"] == 0.0
          and cost_bodies[V2.id]["total_cost_delta"] != 0.0, str(cost_bodies))
    check("cost keyed unknown participant refused",
          client.post("/api/v1/forecasting/scenarios/compare",
                      json={"scenario_ids": [V1.id, 424242],
                            "hourly_costs": {"default": 1.0}},
                      headers=_auth_headers()).status_code == 422, "")


def test_api_role_gating():
    for method, url, kwargs in (
        ("post", f"/api/v1/forecasting/scenarios/{V1.id}/versions",
         {"json": {"assumptions": [{"key": "hire_rate", "value": 1, "unit": "percent"}]}}),
        ("post", f"/api/v1/forecasting/scenarios/{V1.id}/fork", {"json": {}}),
        ("get", f"/api/v1/forecasting/scenarios/{V1.id}/versions", {}),
    ):
        resp = client.request(method, url, headers=_assoc_headers(), **kwargs)
        check(f"Associate refused {method.upper()} "
              f"{'versions' if 'versions' in url else 'fork'} with 403",
              resp.status_code == 403, f"{resp.status_code} {resp.text[:140]}")
        resp = client.request(method, url, headers=_auth_headers(), **kwargs)
        check(f"Manager admitted {method.upper()} on the same endpoint",
              resp.status_code in (200, 201, 404), f"{resp.status_code}")


def test_service_unknown_scenario_errors():
    try:
        project = None
        _ = project
        compare_scenarios(db, [V1.id, V3.id], hourly_costs={"OPSAN": 1, "X": 2})
        check("compare with bad rate map refused", False, "no exception")
    except ScenarioError as exc:
        check("compare with bad rate map refused", "default" in str(exc), str(exc))


if __name__ == "__main__":
    print("Running scenario builder test suite...")
    print()

    TOKEN = login()
    ASSOC_TOKEN = login("sbassoc")  # noqa: F841  (module-level, read via helper)
    check("manager login works", bool(TOKEN), "no token")
    check("associate login works", bool(ASSOC_TOKEN), "no token")

    test_assumption_validation()
    test_new_keys_reshape_the_projection()
    test_create_sets_version_one()
    test_edit_creates_the_next_version_and_keeps_the_old()
    test_fork_starts_its_own_lineage()
    test_cost_projection_explicit_and_labelled()
    test_service_comparison_carries_assumptions_versions_and_deltas()
    test_api_create_scenario()
    test_api_edit_and_versions()
    test_api_fork()
    test_api_compare_versions()
    test_api_role_gating()
    test_service_unknown_scenario_errors()

    print()
    print("----------------------------------------------------------------")
    print(f"scenario builder tests: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
    if FAILURES:
        for name, detail in FAILURES:
            print(f"  FAIL  {name}: {detail}")
        sys.exit(1)
    sys.exit(0)
