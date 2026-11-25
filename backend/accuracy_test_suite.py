"""Accuracy test suite (AN-06): forecast accuracy tracking with confidence.

What this suite proves
----------------------
* compute_error is the hand-checkable math: MAPE (fraction) over the
  pairs whose actual is not zero, MAE and bias over every compared
  pair, bias = forecast - actual (positive = over-predicted), sample
  size = comparable pairs
* confidence thresholds are explicit: `ok` at or under the review
  threshold, `review` at or under the degraded threshold, `degraded`
  over it; an uncomputable MAPE is never `ok` — it is `review`
* record_forecast_accuracy compares each completed run's forecast
  hours with the actual hours the demand layer measures for the same
  window (leave hours are supply-side and are excluded), one row per
  (run, month period, location, role)
* re-running a window REPLACES the rows it computes — never stacked
* the list endpoint is paged, filters by window / location / role /
  model version / run and recomputes the confidence status per
  request thresholds
* role gating: Manager allowed, Associate refused with the shared
  error envelope; every sync writes an audit row in the same flow
* the 0019 migration round-trips: upgrade creates the table,
  re-upgrade is a no-op, downgrade drops it, re-downgrade is a no-op

Date window: July-August 2026 — distinct from the publish tests
(January 2026), the attendance tests (February 2027), the SC-06 tests
(April 2026) and the cost-forecast tests (March 2026), so cross-suite
date-range queries cannot contaminate each other.

Run:  python accuracy_test_suite.py
"""
import datetime
import os
import sys
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="accuracy_"), "acc.db")
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
from app.models.audit import AuditLog  # noqa: E402
from app.models.core_hr import Location, Position  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.leave import LeaveRequest, LeaveType  # noqa: E402
from app.models.time_attendance import TimeEntry  # noqa: E402
from app.models.scheduling import RosterEntry  # noqa: E402  registers roster tables
from app.models.user import User  # noqa: E402
from app.models.forecasting import (  # noqa: E402
    ForecastAccuracyRecord,
    ForecastResult,
    ForecastRun,
)
from app.services.forecast_accuracy import (  # noqa: E402
    DEFAULT_DEGRADED_THRESHOLD,
    DEFAULT_REVIEW_THRESHOLD,
    AccuracyError,
    _validate_thresholds,
    compute_error,
    list_forecast_accuracy,
    record_forecast_accuracy,
    status_for_mape,
)

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

# July-August 2026: a window deliberately distinct from other suites.
W_START = datetime.date(2026, 7, 1)
W_END = datetime.date(2026, 8, 31)
D_J1 = datetime.date(2026, 7, 6)   # Mon
D_J2 = datetime.date(2026, 7, 7)
D_J3 = datetime.date(2026, 7, 8)
D_J4 = datetime.date(2026, 7, 9)   # measured zero
D_J5 = datetime.date(2026, 7, 10)  # measured zero
D_A1 = datetime.date(2026, 8, 3)
PASSWORD = "AccTestPass123"
PASSWORD_HASH = get_password_hash(PASSWORD)

db = SessionLocal()
dept = Department(name="Accuracy", code="ACC")
db.add(dept)
db.commit()
db.refresh(dept)
loc = Location(name="Main Site", code="MAIN")
db.add(loc)
db.commit()
db.refresh(loc)
job = Job(title="Shift Supervisor", code="SUP", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)
pos = Position(code="POS-ACC", title="Supervisor (Main)", job_id=job.id,
               department_id=dept.id, location_id=loc.id)
db.add(pos)
db.commit()
db.refresh(pos)

emp = Employee(
    employee_id="ACC001",
    first_name="Acc",
    last_name="Manager",
    email="accmgr@example.com",
    department_id=dept.id,
    job_id=job.id,
    hire_date=datetime.date(2024, 1, 1),
    status="Active",
)
db.add(emp)
db.commit()
db.refresh(emp)

# users.employee_id is UNIQUE: each account gets its own employee row.
emp_crc = Employee(
    employee_id="ACC002",
    first_name="Acc",
    last_name="Associate",
    email="accass@example.com",
    department_id=dept.id,
    job_id=job.id,
    hire_date=datetime.date(2024, 1, 1),
    status="Active",
)
db.add(emp_crc)
db.commit()
db.refresh(emp_crc)

manager = User(
    username="accmgr",
    email="accmgr@example.com",
    hashed_password=PASSWORD_HASH,
    role="Manager",
    is_active=True,
    employee_id=emp.id,
)
associate = User(
    username="accass",
    email="accass@example.com",
    hashed_password=PASSWORD_HASH,
    role="Associate",
    is_active=True,
    employee_id=emp_crc.id,
)
db.add_all([manager, associate])
db.commit()
db.refresh(manager)

# Approved actuals. Jul 9 / Jul 10 get no entry: measured zero.
for d, h in [(D_J1, 110.0), (D_J2, 100.0), (D_J3, 80.0), (D_A1, 60.0)]:
    db.add(TimeEntry(employee_id=emp.id, work_date=d, worked_hours=h, status="Approved"))

# An approved leave INSIDE the window: leave is supply-side. It must
# NOT move the actual hours the accuracy is judged against.
leave_type = LeaveType(name="Test Leave", code="TESTLV")
db.add(leave_type)
db.commit()
db.refresh(leave_type)
db.add(LeaveRequest(
    employee_id=emp.id,
    leave_type_id=leave_type.id,
    start_date=datetime.date(2026, 7, 12),
    end_date=datetime.date(2026, 7, 13),
    working_days=2.0,
    reason="accuracy fixture leave",
    status="Approved",
))
db.commit()


def _forecast_run(name: str, rule_version: str, results: list[dict],
                  location_id=None, role_id=None) -> ForecastRun:
    """Seed a completed forecast run with per-day result rows."""
    run = ForecastRun(
        name=name,
        horizon_days=len(results),
        method="seasonal_naive",
        status="completed",
        finished_at=datetime.datetime(2026, 9, 1),
        location_id=location_id,
        role_id=role_id,
    )
    db.add(run)
    db.flush()
    for i, r in enumerate(results, start=1):
        db.add(
            ForecastResult(
                forecast_run_id=run.id,
                series_key=f"{job.code}:hours:{r['forecast_date']}",
                horizon_step=i,
                forecast_date=r["forecast_date"],
                predicted_value=r["predicted_value"],
                lower_bound=r["predicted_value"] - 1,
                upper_bound=r["predicted_value"] + 1,
                input_hash="acc-suite-" + name.replace(" ", ""),
                rule_version=rule_version,
                method_used="seasonal_naive",
            )
        )
    db.commit()
    db.refresh(run)
    return run


# Run A: role-scoped. Five July days + one August day.
#   July forecast total 500 (100+120+80+90+110); actuals 110/100/80/0/0.
#   Run A August: forecast 50, actual 60.
run_a = _forecast_run(
    "Run A",
    "test-1.0",
    [
        {"forecast_date": D_J1, "predicted_value": 100.0},
        {"forecast_date": D_J2, "predicted_value": 120.0},
        {"forecast_date": D_J3, "predicted_value": 80.0},
        {"forecast_date": D_J4, "predicted_value": 90.0},
        {"forecast_date": D_J5, "predicted_value": 110.0},
        {"forecast_date": D_A1, "predicted_value": 50.0},
    ],
    location_id=None,
    role_id=job.id,
)

# Run B: location-scoped. One July day: forecast 40 against actual 110.
run_b = _forecast_run(
    "Run B",
    "test-2.0",
    [{"forecast_date": D_J1, "predicted_value": 40.0}],
    location_id=loc.id,
    role_id=None,
)

client = TestClient(app)


def login(username: str = "accmgr") -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    body = resp.json()
    return body.get("access_token") or body.get("token") or ""


# ==============================================================================
# Service-level behaviour
# ==============================================================================

def test_compute_error_hand_computed():
    forecast = {D_J1: 100.0, D_J2: 120.0, D_J3: 80.0, D_J4: 90.0, D_J5: 110.0}
    actual = {D_J1: 110.0, D_J2: 100.0, D_J3: 80.0, D_J4: 0.0, D_J5: 0.0}
    m = compute_error(forecast, actual)
    # MAPE over the three non-zero-actual pairs: (10/110 + 20/100 + 0/80)/3
    expected_mape = round((10.0 / 110.0 + 20.0 / 100.0 + 0.0) / 3.0, 6)
    check("mape is a fraction over non-zero actuals", abs(m["mape"] - expected_mape) < 1e-9,
          f"got {m['mape']} want {expected_mape}")
    check("mae over every pair", abs(m["mae"] - 46.0) < 1e-9, str(m["mae"]))
    check("bias = forecast - actual (over-predicted positive)",
          abs(m["bias"] - 42.0) < 1e-9, str(m["bias"]))
    check("sample size counts comparable pairs", m["sample_size"] == 5, str(m["sample_size"]))
    check("totals carried", abs(m["forecast_total"] - 500.0) < 1e-6
          and abs(m["actual_total"] - 290.0) < 1e-6, str(m))

    # A both-zero day is skipped, not compared.
    m2 = compute_error({D_J1: 0.0, D_J2: 10.0}, {D_J1: 0.0, D_J2: 8.0})
    check("both-zero day skipped", m2["sample_size"] == 1, str(m2))

    # Every actual zero: MAPE uncomputable, never a fake pass.
    m3 = compute_error({D_J1: 90.0}, {D_J1: 0.0})
    check("zero-actual-only window has no mape", m3["mape"] is None, str(m3))
    check("zero-actual-only mape flagged review", status_for_mape(m3["mape"]) == "review", "")


def test_status_thresholds():
    check("ok at review threshold", status_for_mape(0.10) == "ok", "")
    check("review between thresholds", status_for_mape(0.15) == "review", "")
    check("degraded over degraded threshold", status_for_mape(0.30) == "degraded", "")
    check("boundary at degraded threshold is review", status_for_mape(0.25) == "review", "")
    check("thresholds are explicit constants",
          DEFAULT_REVIEW_THRESHOLD == 0.10 and DEFAULT_DEGRADED_THRESHOLD == 0.25, "")
    try:
        _validate_thresholds(0.3, 0.2)
        check("inverted thresholds rejected", False, "no exception")
    except AccuracyError:
        check("inverted thresholds rejected", True, "")


def test_sync_records_hand_computed_rows():
    result = record_forecast_accuracy(
        db, start_date=W_START, end_date=W_END
    )
    check("first sync replaces nothing", result["replaced"] == 0, str(result["replaced"]))
    check("three rows recorded (A-Jul, A-Aug, B-Jul)", len(result["records"]) == 3,
          str([r["period"] for r in result["records"]]))

    july_a = next(r for r in result["records"]
                  if r["period"] == "2026-07" and r["forecast_run_id"] == run_a.id)
    aug_a = next(r for r in result["records"]
                 if r["period"] == "2026-08" and r["forecast_run_id"] == run_a.id)
    july_b = next(r for r in result["records"]
                  if r["period"] == "2026-07" and r["forecast_run_id"] == run_b.id)

    check("A july forecast hours", abs(july_a["forecast_hours"] - 500.0) < 1e-6,
          str(july_a["forecast_hours"]))
    check("A july actual hours (leave excluded)",
          abs(july_a["actual_hours"] - 290.0) < 1e-6, str(july_a["actual_hours"]))
    check("A july mape hand-computed",
          abs(july_a["mape"] - round((10.0 / 110.0 + 0.2) / 3.0, 6)) < 1e-9, str(july_a["mape"]))
    check("A july mae", abs(july_a["mae"] - 46.0) < 1e-6, str(july_a["mae"]))
    check("A july bias", abs(july_a["bias"] - 42.0) < 1e-6, str(july_a["bias"]))
    check("A july sample size", july_a["sample_size"] == 5, str(july_a["sample_size"]))
    check("A july status ok under defaults", july_a["status"] == "ok", str(july_a["status"]))
    check("A july model version from run results", july_a["model_version"] == "test-1.0", "")
    check("A july method used", july_a["method_used"] == "seasonal_naive", "")

    check("A august bucket separate", abs(aug_a["forecast_hours"] - 50.0) < 1e-6
          and abs(aug_a["actual_hours"] - 60.0) < 1e-6, str(aug_a))
    check("A august mape 10/60", abs(aug_a["mape"] - round(10.0 / 60.0, 6)) < 1e-9,
          str(aug_a["mape"]))
    check("A august bias negative (under-predicted)",
          abs(aug_a["bias"] - (-10.0)) < 1e-6, str(aug_a["bias"]))
    check("A august status review under defaults", aug_a["status"] == "review", "")

    check("B july scoped to location", july_b["location_id"] == loc.id
          and july_b["role_id"] is None, str(july_b))
    check("B july mape 70/110", abs(july_b["mape"] - round(70.0 / 110.0, 6)) < 1e-9,
          str(july_b["mape"]))
    check("B july status degraded under defaults", july_b["status"] == "degraded", "")
    check("B july model version", july_b["model_version"] == "test-2.0", "")

    stored = db.query(ForecastAccuracyRecord).count()
    check("rows stored exactly as computed", stored == 3, str(stored))


def test_rerun_replaces_not_duplicates():
    first_count = db.query(ForecastAccuracyRecord).count()
    result = record_forecast_accuracy(db, start_date=W_START, end_date=W_END)
    second_count = db.query(ForecastAccuracyRecord).count()
    check("re-run replaces every computed row", result["replaced"] == 3,
          str(result["replaced"]))
    check("re-run stores no duplicates", second_count == first_count,
          f"{first_count} -> {second_count}")
    # and once more through a NARROWED window: the untouched month stays
    res2 = record_forecast_accuracy(db, start_date=datetime.date(2026, 8, 1), end_date=W_END)
    check("narrow re-run replaces only its month", res2["replaced"] == 1
          and res2["replaced"] == len(res2["records"]), f"replaced={res2['replaced']}")
    check("untouched month survives",
          db.query(ForecastAccuracyRecord).filter(
              ForecastAccuracyRecord.period == "2026-07").count() == 2, "")


def test_list_filters_and_ordering():
    res = list_forecast_accuracy(db)
    check("list finds all three", res["total"] == 3, str(res["total"]))
    check("list is paged shape", set(res) == {"items", "total", "page", "page_size"}, "")
    ids = [p["id"] for p in res["items"]]
    check("newest first (last inserted first)", ids == sorted(ids, reverse=True), str(ids))
    fields = set(res["items"][0])
    check("row carries period/run/version/metrics/status",
          {"period", "forecast_run_id", "model_version", "mape", "mae", "bias",
           "sample_size", "status", "measured_at"} <= fields, str(fields))

    check("filter by model version",
          list_forecast_accuracy(db, model_version="test-1.0")["total"] == 2, "")
    check("filter by run",
          list_forecast_accuracy(db, run_id=run_a.id)["total"] == 2, "")
    check("filter by location",
          list_forecast_accuracy(db, location_id=loc.id)["total"] == 1, "")
    check("filter by window start",
          list_forecast_accuracy(db, start_date=datetime.date(2026, 8, 1))["total"] == 1, "")
    check("filter by window end",
          list_forecast_accuracy(db, end_date=datetime.date(2026, 7, 31))["total"] == 2, "")
    check("filter by unknown version",
          list_forecast_accuracy(db, model_version="no-such")["total"] == 0, "")
    paged = list_forecast_accuracy(db, page=1, page_size=2)
    check("pagination limits items",
          len(paged["items"]) == 2 and paged["total"] == 3, str(paged["total"]))


def test_threshold_recompute_on_read():
    stricter = list_forecast_accuracy(db, review_threshold=0.05, degraded_threshold=0.25)
    by_key = {(p["forecast_run_id"], p["period"]): p for p in stricter["items"]}
    check("stricter review threshold demotes A july to review",
          by_key[(run_a.id, "2026-07")]["status"] == "review",
          str(by_key[(run_a.id, "2026-07")]["status"]))
    check("degraded row stays degraded",
          by_key[(run_b.id, "2026-07")]["status"] == "degraded", "")
    harshest = list_forecast_accuracy(db, review_threshold=0.05, degraded_threshold=0.09)
    by_key2 = {(p["forecast_run_id"], p["period"]): p for p in harshest["items"]}
    check("hardest thresholds demote A july to degraded",
          by_key2[(run_a.id, "2026-07")]["status"] == "degraded", "")
    flagged = list_forecast_accuracy(db, status="review",
                                     review_threshold=0.05, degraded_threshold=0.25)
    check("computed status filter works",
          {p["forecast_run_id"] for p in flagged["items"]} == {run_a.id},
          str([p["forecast_run_id"] for p in flagged["items"]]))


# ==============================================================================
# API behaviour
# ==============================================================================

def test_api_sync_and_history():
    resp = client.post(
        "/api/v1/forecasting/accuracy/sync",
        json={"start_date": W_START.isoformat(), "end_date": W_END.isoformat()},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    check("sync responds 200", resp.status_code == 200, f"{resp.status_code} {resp.text[:300]}")
    body = resp.json()
    check("sync reports thresholds", body.get("review_threshold") == 0.10
          and body.get("degraded_threshold") == 0.25, str(body.get("review_threshold")))
    check("sync replaced the three rows", body.get("replaced") == 3, str(body.get("replaced")))
    check("sync returns records", len(body.get("records", [])) == 3, "")
    check("sync records carry database ids",
          all(isinstance(r.get("id"), int) for r in body.get("records", [])),
          str(body.get("records", [])[:1]))

    before = db.query(ForecastAccuracyRecord).count()
    resp2 = client.post(
        "/api/v1/forecasting/accuracy/sync",
        json={"start_date": W_START.isoformat(), "end_date": W_END.isoformat()},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    after = db.query(ForecastAccuracyRecord).count()
    check("api re-run stacks nothing", resp2.status_code == 200 and before == after,
          f"{before} -> {after}")

    hist = client.get(
        "/api/v1/forecasting/accuracy",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    check("history responds 200", hist.status_code == 200, str(hist.status_code))
    hbody = hist.json()
    check("history total", hbody.get("total") == 3, str(hbody.get("total")))
    check("history page envelope",
          {"items", "total", "page", "page_size"} <= set(hbody), str(set(hbody)))
    item = hbody["items"][0]
    check("history item shape",
          all(k in item for k in ("period", "forecast_run_id", "model_version",
                                  "mape", "mae", "bias", "sample_size", "status")), str(item))

    filtered = client.get(
        "/api/v1/forecasting/accuracy",
        params={"model_version": "test-1.0"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    check("history filters by model version", filtered.json().get("total") == 2, "")
    recomputed = client.get(
        "/api/v1/forecasting/accuracy",
        params={"review_threshold": 0.05},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    statuses = {(i["forecast_run_id"], i["period"]): i["status"] for i in recomputed.json()["items"]}
    check("history recomputes status per request",
          statuses[(run_a.id, "2026-07")] == "review", str(statuses))

    audit_rows = db.query(AuditLog).filter(
        AuditLog.action == "sync_forecast_accuracy").count()
    check("sync writes an audit row", audit_rows >= 1, str(audit_rows))


def test_api_validation():
    inverted = client.post(
        "/api/v1/forecasting/accuracy/sync",
        json={"start_date": W_START.isoformat(), "end_date": W_END.isoformat(),
              "review_threshold": 0.3, "degraded_threshold": 0.2},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    check("inverted thresholds 422", inverted.status_code == 422, str(inverted.status_code))
    backwards = client.post(
        "/api/v1/forecasting/accuracy/sync",
        json={"start_date": W_END.isoformat(), "end_date": W_START.isoformat()},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    check("inverted window 422", backwards.status_code == 422, str(backwards.status_code))


def test_role_gating():
    assoc = login("accass")
    check("associate login works", bool(assoc), "no token")
    denied_get = client.get(
        "/api/v1/forecasting/accuracy",
        headers={"Authorization": f"Bearer {assoc}"},
    )
    check("associate denied on history", denied_get.status_code == 403,
          str(denied_get.status_code))
    check("history refusal uses the shared envelope",
          denied_get.json().get("error", {}).get("code") == "forbidden",
          str(denied_get.json())[:200])
    denied_post = client.post(
        "/api/v1/forecasting/accuracy/sync",
        json={"start_date": W_START.isoformat(), "end_date": W_END.isoformat()},
        headers={"Authorization": f"Bearer {assoc}"},
    )
    check("associate denied on sync", denied_post.status_code == 403,
          str(denied_post.status_code))
    check("sync refusal uses the shared envelope",
          denied_post.json().get("error", {}).get("code") == "forbidden",
          str(denied_post.json())[:200])
    unauth = client.get("/api/v1/forecasting/accuracy")
    check("unauthenticated refused", unauth.status_code == 401, str(unauth.status_code))


def test_route_registration():
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    check("route registered /api/v1/forecasting/accuracy",
          "/api/v1/forecasting/accuracy" in paths, "")
    check("route registered /api/v1/forecasting/accuracy/sync",
          "/api/v1/forecasting/accuracy/sync" in paths, "")


def test_migration_round_trip():
    """The 0019 revision upgrades and downgrades cleanly and idempotently."""
    import importlib.util

    path = os.path.join(os.path.dirname(__file__), "migrations", "versions",
                        "0019_forecast_accuracy.py")
    spec = importlib.util.spec_from_file_location("mig_0019", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read()
    check("down_revision is a module constant",
          "PREVIOUS_REVISION = " in source and 'down_revision = PREVIOUS_REVISION' in source, "")
    check("revision chain follows 0018_scenario_versions", module.PREVIOUS_REVISION == "0018_scenario_versions", "")

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    mig_path = os.path.join(tempfile.mkdtemp(prefix="acc_mig_"), "mig.db")
    mig_engine = sa.create_engine(f"sqlite:///{mig_path}")
    try:
        with mig_engine.begin() as conn:
            context = MigrationContext.configure(conn)
            with Operations.context(context):
                module.upgrade()
        inspector = sa.inspect(mig_engine)
        check("upgrade creates the table",
              "forecast_accuracy_records" in inspector.get_table_names(), "")
        cols = {c["name"] for c in inspector.get_columns("forecast_accuracy_records")}
        expected = {"id", "forecast_run_id", "model_version", "method_used", "period",
                    "location_id", "role_id", "forecast_hours", "actual_hours",
                    "mape", "mae", "bias", "sample_size", "status", "measured_at"}
        check("table carries every accuracy column", expected <= cols,
              f"missing {expected - cols}")
        with mig_engine.begin() as conn:
            context = MigrationContext.configure(conn)
            with Operations.context(context):
                module.upgrade()
        check("re-upgrade is a no-op", True, "")
        with mig_engine.begin() as conn:
            context = MigrationContext.configure(conn)
            with Operations.context(context):
                module.downgrade()
        inspector = sa.inspect(mig_engine)
        check("downgrade drops the table",
              "forecast_accuracy_records" not in inspector.get_table_names(), "")
        with mig_engine.begin() as conn:
            context = MigrationContext.configure(conn)
            with Operations.context(context):
                module.downgrade()
        check("re-downgrade is a no-op", True, "")
    finally:
        mig_engine.dispose()


if __name__ == "__main__":
    print("Running accuracy test suite...")
    print()

    TOKEN = login()
    check("manager login works", bool(TOKEN), "no token")

    test_route_registration()
    test_compute_error_hand_computed()
    test_status_thresholds()
    test_sync_records_hand_computed_rows()
    test_rerun_replaces_not_duplicates()
    test_list_filters_and_ordering()
    test_threshold_recompute_on_read()
    test_api_sync_and_history()
    test_api_validation()
    test_role_gating()
    test_migration_round_trip()

    print()
    print("----------------------------------------------------------------")
    print(f"accuracy tests: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
    if FAILURES:
        for name, detail in FAILURES:
            print(f"  FAIL  {name}: {detail}")
        sys.exit(1)
    sys.exit(0)
