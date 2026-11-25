"""Forecasting API endpoints.

Provides demand forecasting endpoints that use the statistical forecasting
engine (statsmodels Holt-Winters + seasonal naive). All calculations are
traceable via input hash and rule version.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import MANAGER_ROLES, get_db, require_roles, tenant_id_for
from app.core.audit import record_audit
from app.core.master_data import load_or_404
from app.core.tenancy import tenant_column_criterion, tenant_matches
from app.models.forecasting import ForecastRun, ForecastResult
from app.models.user import User
from app.schemas.forecasting import (
    ForecastCreate,
    ForecastRunOut,
    ForecastResultOut,
)
from app.services.forecasting import ForecastEngine, ForecastError
from app.services.demand import build_demand_series
from app.services.demand_importer import parse_driver_csv, DriverCSVError
from app.services.forecast_bridge import forecast_to_demand_series, get_forecast_run_metadata, ForecastBridgeError

router = APIRouter()


def _load_run(db: Session, run_id: int) -> ForecastRun:
    """Load one forecast run, refusing another tenant's row fail-closed."""
    run = load_or_404(db, ForecastRun, run_id, "ForecastRun")
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(
        getattr(run, "tenant_id", None), tenant_id
    ):
        raise HTTPException(status_code=404, detail="Forecast run not found")
    return run


def _load_scenario(db: Session, scenario_id: int) -> ForecastScenario:
    """Load one scenario, refusing another tenant's row fail-closed."""
    from app.models.forecasting import ForecastScenario as _Scenario

    scenario = load_or_404(db, _Scenario, scenario_id, "Scenario")
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(
        getattr(scenario, "tenant_id", None), tenant_id
    ):
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


def _foreign_run(db: Session, run_id: int) -> bool:
    """True when the run exists but belongs to another tenant.

    A missing run falls through to the service layer, which keeps its
    existing answer (422 for creates, 404 for reads, empty for lists):
    only a row that exists and is foreign is refused here with 404, so
    no cross-tenant id can be used and no existing behaviour changes.
    """
    run = db.get(ForecastRun, run_id)
    if run is None:
        return False
    tenant_id = tenant_id_for(db)
    return tenant_id is not None and not tenant_matches(
        getattr(run, "tenant_id", None), tenant_id
    )


def _foreign_scenario(db: Session, scenario_id: int) -> bool:
    """True when the scenario exists but belongs to another tenant."""
    from app.models.forecasting import ForecastScenario as _Scenario

    scenario = db.get(_Scenario, scenario_id)
    if scenario is None:
        return False
    tenant_id = tenant_id_for(db)
    return tenant_id is not None and not tenant_matches(
        getattr(scenario, "tenant_id", None), tenant_id
    )


def _reject_foreign_run(db: Session, run_id: int) -> None:
    if _foreign_run(db, run_id):
        raise HTTPException(status_code=404, detail="Forecast run not found")


def _reject_foreign_scenario(db: Session, scenario_id: int) -> None:
    if _foreign_scenario(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")


class DemandSeriesRequest(BaseModel):
    """Request to build a demand series from records."""
    start_date: date
    end_date: date
    location_id: Optional[int] = None
    role: Optional[str] = None
    job_id: Optional[int] = None
    include_time_entries: bool = True
    include_leave: bool = True
    include_roster: bool = True


@router.post("/runs", response_model=ForecastRunOut, status_code=201, operation_id="forecastingCreateRun")
def create_forecast_run(
    payload: ForecastCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Create and run a demand forecast.

    Accepts a time series and generates forecasts using statistical methods.
    Returns full results including method used, backtest accuracy, and
    per-period predictions with confidence bands.

    If the series has insufficient history (< 8 weeks of daily data),
    returns insufficient_history flag with baseline fallback.
    """
    series_data = payload.series_data
    if not series_data:
        raise HTTPException(
            status_code=422, detail="series_data cannot be empty"
        )

    # Extract series values and dates
    dates = [d.date for d in series_data]
    values = [d.value for d in series_data]

    engine = ForecastEngine()
    try:
        result = engine.forecast(
            series=values,
            dates=dates,
            horizon=payload.horizon_days,
            method=payload.method or "auto",
            seasonality=payload.seasonality or 7,
        )
    except ForecastError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    # Create the forecast run record
    tenant_id = tenant_id_for(db)
    db_run = ForecastRun(
        name=payload.name or f"Forecast {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        description=payload.description,
        tenant_id=tenant_id,
        horizon_days=payload.horizon_days,
        method=payload.method or "auto",
        data_start_date=dates[0],
        data_end_date=dates[-1],
        backtest_mape=result["backtest_mape"],
        backtest_mase=result["backtest_mase"],
        backtest_holdout_days=result["backtest_holdout_days"],
        status="completed",
        finished_at=datetime.utcnow(),
        location_id=payload.location_id,
        role_id=payload.role_id,
    )
    db.add(db_run)
    db.flush()

    # Create result rows
    for r in result["results"]:
        db_result = ForecastResult(
            forecast_run_id=db_run.id,
            tenant_id=getattr(db_run, "tenant_id", None),
            series_key=payload.series_selector or "default",
            horizon_step=r["horizon_step"],
            forecast_date=r["forecast_date"],
            predicted_value=r["predicted_value"],
            lower_bound=r["lower_bound"],
            upper_bound=r["upper_bound"],
            input_hash=result["input_hash"],
            rule_version=result["rule_version"],
            method_used=result["method_used"],
            data_start_date=result["data_start_date"],
            data_end_date=result["data_end_date"],
        )
        db.add(db_result)

    db.commit()
    db.refresh(db_run)

    record_audit(db, current_user, "create_forecast_run", "ForecastRun", db_run.id)
    return db_run


@router.get("/runs", response_model=list[ForecastRunOut], operation_id="forecastingListRuns")
def list_forecast_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
    limit: int = 50,
):
    """List forecast runs, most recent first."""
    query = db.query(ForecastRun)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        query = query.filter(
            tenant_column_criterion(ForecastRun.tenant_id, tenant_id)
        )
    runs = (
        query
        .order_by(ForecastRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return runs


@router.get("/runs/{run_id}", response_model=ForecastRunOut, operation_id="forecastingGetRun")
def get_forecast_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Get a specific forecast run with all results."""
    return _load_run(db, run_id)


@router.get(
    "/runs/{run_id}/results",
    response_model=list[ForecastResultOut], operation_id="forecastingListForecastingrunsresults")
def get_forecast_results(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Get all forecast results for a run."""
    _load_run(db, run_id)
    results = (
        db.query(ForecastResult)
        .filter(ForecastResult.forecast_run_id == run_id)
        .order_by(ForecastResult.horizon_step)
        .all()
    )
    return results


@router.get(
    "/runs/{run_id}/demand-series",
    response_model=dict, operation_id="forecastingGetDemandSeries")
def get_forecast_demand_series(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
    location_id: Optional[int] = Query(None, description="Override location filter"),
    role: Optional[str] = Query(None, description="Override role filter (title or code)"),
    start_date: Optional[date] = Query(None, description="Start date filter (inclusive)"),
    end_date: Optional[date] = Query(None, description="End date filter (inclusive)"),
):
    """Get demand series from a forecast run formatted for the scheduler.

    Returns the forecast results as a demand series with the same shape
    as build_demand_series, including confidence bands as metadata.
    """
    try:
        demand_points = forecast_to_demand_series(
            db,
            run_id,
            location_id=location_id,
            role=role,
            start_date=start_date,
            end_date=end_date,
        )
    except ForecastBridgeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    metadata = get_forecast_run_metadata(db, run_id)

    return {
        "forecast_run_id": run_id,
        "metadata": metadata,
        "count": len(demand_points),
        "series": [
            {
                "date": p["date"].isoformat(),
                "value": p["value"],
                "lower_bound": p.get("lower_bound"),
                "upper_bound": p.get("upper_bound"),
                "location_id": p.get("location_id"),
                "location_code": p.get("location_code"),
                "role_id": p.get("role_id"),
                "role": p.get("role"),
                "role_code": p.get("role_code"),
                "source": p.get("source"),
                "forecast_run_id": p.get("forecast_run_id"),
            }
            for p in demand_points
        ],
    }


@router.post("/drivers", status_code=200, operation_id="forecastingImportDriverCSV")
def import_driver_csv_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Validate a driver CSV and return the resulting demand series."""
    try:
        content = file.file.read()
        series = parse_driver_csv(content)
    except DriverCSVError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "count": len(series),
        "series": [
            {
                "date": p["date"].isoformat(),
                "value": p["value"],
                "location_id": p.get("location_id"),
                "location_code": p.get("location_code"),
                "role": p.get("role"),
            }
            for p in series
        ],
    }


@router.post("/drivers/import", status_code=200, operation_id="forecastingImportDriverCSVAlias")
def import_driver_csv_endpoint_alias(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    return import_driver_csv_endpoint(file=file, current_user=current_user)


@router.post("/demand/series", status_code=200, operation_id="forecastingBuildDemandSeries")
def build_demand_series_endpoint(
    payload: DemandSeriesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Build a demand series from the product's own records."""
    series = build_demand_series(
        db,
        start_date=payload.start_date,
        end_date=payload.end_date,
        location_id=payload.location_id,
        role=payload.role,
        job_id=payload.job_id,
        include_time_entries=payload.include_time_entries,
        include_leave=payload.include_leave,
        include_roster=payload.include_roster,
    )
    return {
        "count": len(series),
        "series": [
            {
                "date": p["date"].isoformat(),
                "value": p["value"],
                "actual_hours": p["actual_hours"],
                "leave_hours": p["leave_hours"],
                "scheduled_hours": p["scheduled_hours"],
                "location_id": p.get("location_id"),
                "role": p.get("role"),
            }
            for p in series
        ],
    }


# =============================================================================
# Scenario Endpoints
# =============================================================================

from app.models.forecasting import ForecastScenario
from app.schemas.forecasting import (
    ScenarioCreate,
    ScenarioOut,
    PaginatedScenarios,
    ScenarioComparisonRequest,
    ScenarioComparison,
    ScenarioEditCreate,
    ScenarioForkCreate,
    ScenarioVersionList,
    ScenarioCostProjectionOut,
)
from app.services.forecasting import (
    create_scenario,
    get_scenario,
    list_scenarios,
    compare_scenarios,
    edit_scenario_version,
    fork_scenario,
    list_scenario_versions,
    ScenarioError,
)


@router.post("/scenarios", response_model=ScenarioOut, status_code=201, operation_id="forecastingCreateScenario")
def create_scenario_endpoint(
    payload: ScenarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Create a what-if scenario from a base forecast run.

    The scenario applies explicit, named assumptions to the base forecast
    and produces a variant forecast with the same metadata structure.
    Assumptions are always shown and never applied silently.
    """
    _reject_foreign_run(db, payload.base_run_id)
    try:
        scenario = create_scenario(
            db=db,
            base_run_id=payload.base_run_id,
            assumptions=[a.model_dump() for a in payload.assumptions],
            name=payload.name,
            description=payload.description,
            user_id=current_user.id,
        )
    except ScenarioError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record_audit(db, current_user, "create_forecast_scenario", "ForecastScenario", scenario.id)
    return scenario


@router.get("/scenarios", response_model=PaginatedScenarios, operation_id="forecastingListScenarios")
def list_scenarios_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
    base_run_id: Optional[int] = Query(None, description="Filter by base forecast run ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List forecast scenarios with optional filtering by base run."""
    if base_run_id is not None:
        _reject_foreign_run(db, base_run_id)
    scenarios, total = list_scenarios(db, base_run_id=base_run_id, page=page, page_size=page_size)
    return PaginatedScenarios(
        items=scenarios,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/scenarios/{scenario_id}", response_model=ScenarioOut, operation_id="forecastingGetScenario")
def get_scenario_endpoint(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Get a specific scenario with its results."""
    scenario = get_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.post("/scenarios/compare", response_model=ScenarioComparison, operation_id="forecastingCompareScenarios")
def compare_scenarios_endpoint(
    payload: ScenarioComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Compare multiple scenarios side-by-side.

    Returns period-by-period comparison with deltas against the first scenario.
    All assumptions for each scenario are included in the response.
    """
    for sid in payload.scenario_ids:
        _reject_foreign_scenario(db, sid)
    try:
        comparison = compare_scenarios(
            db, payload.scenario_ids, hourly_costs=payload.hourly_costs
        )
    except ScenarioError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if comparison.get("costs"):
        for sid, projection in comparison["costs"].items():
            projection["scenario_id"] = sid
    return comparison


# =============================================================================
# Scenario Builder: edit, fork and version scenarios (AN-05)
# =============================================================================


@router.get("/scenarios/{scenario_id}/versions", response_model=ScenarioVersionList, operation_id="forecastingListScenarioVersions")
def list_scenario_versions_endpoint(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Every version of a scenario's lineage, oldest first.

    Editing never overwrites: each edit stores a new version under the
    same lineage root and the old version stays retrievable and
    comparable. A scenario that does not exist returns 404.
    """
    versions = list_scenario_versions(db, scenario_id)
    if versions is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return ScenarioVersionList(items=versions)


@router.post("/scenarios/{scenario_id}/versions", response_model=ScenarioOut, status_code=201, operation_id="forecastingEditScenarioVersion")
def edit_scenario_version_endpoint(
    scenario_id: int,
    payload: ScenarioEditCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Edit a scenario by creating its NEXT version.

    The edited assumption set is applied to the scenario's linked base
    projection with the AN-03 assumption engine, named with its version
    number, and stored as a new row under the same lineage root. Every
    assumption key is explicit — an unknown key is a 422 naming the key —
    and the previous versions stay intact and comparable.
    """
    try:
        scenario = edit_scenario_version(
            db=db,
            scenario_id=scenario_id,
            assumptions=[a.model_dump() for a in payload.assumptions],
            name=payload.name,
            description=payload.description,
            user_id=current_user.id,
        )
    except ScenarioError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    record_audit(
        db, current_user, "edit_forecast_scenario_version", "ForecastScenario", scenario.id
    )
    return scenario


@router.post("/scenarios/{scenario_id}/fork", response_model=ScenarioOut, status_code=201, operation_id="forecastingForkScenario")
def fork_scenario_endpoint(
    scenario_id: int,
    payload: ScenarioForkCreate | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Fork a scenario version into a new, independent lineage.

    The fork copies the source version's assumptions, starts its own
    version line at 1, and records exactly which version it forked from.
    Nothing about the source changes.
    """
    try:
        scenario = fork_scenario(
            db=db,
            scenario_id=scenario_id,
            name=payload.name if payload else None,
            description=payload.description if payload else None,
            user_id=current_user.id,
        )
    except ScenarioError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    record_audit(db, current_user, "fork_forecast_scenario", "ForecastScenario", scenario.id)
    return scenario


# =============================================================================
# Cost Forecast Endpoints (AN-04)
# =============================================================================

import csv
from io import StringIO

from fastapi.responses import StreamingResponse

from app.models.forecasting import CostForecast
from app.schemas.forecasting import (
    CostForecastCreate,
    CostForecastOut,
    CostForecastVersionSummaryList,
)
from app.services.cost_forecast import (
    STATUTORY_LABEL,
    CostForecastError,
    forecast_cost,
    get_cost_forecast,
    list_cost_forecasts,
)


@router.post(
    "/runs/{run_id}/cost-forecast",
    response_model=CostForecastOut,
    status_code=201, operation_id="forecastingCreateCostForecast")
def create_cost_forecast(
    run_id: int,
    payload: CostForecastCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Cost a forecast run: forecast demand hours x the hourly rates supplied.

    The rates are explicit assumptions and are returned in the response;
    no rate is ever guessed. Every response, column, and CSV export is
    labelled "excludes statutory on-costs" — employer statutory on-costs
    are NOT included. Each POST stores a new version; earlier versions
    remain intact.
    """
    _reject_foreign_run(db, run_id)
    try:
        result = forecast_cost(
            db,
            run_id,
            hourly_costs=payload.hourly_costs,
            start_date=payload.start_date,
            end_date=payload.end_date,
            created_by=current_user.id,
        )
    except CostForecastError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record_audit(db, current_user, "create_cost_forecast", "CostForecast", result["id"])
    return result


@router.get("/runs/{run_id}/cost-forecast", response_model=CostForecastVersionSummaryList, operation_id="forecastingListCostForecastVersions")
def list_cost_forecasts_endpoint(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """List every stored version of the run's cost forecast, newest first."""
    _load_run(db, run_id)
    try:
        items = list_cost_forecasts(db, run_id)
    except CostForecastError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CostForecastVersionSummaryList(items=items)


@router.get("/runs/{run_id}/cost-forecast/csv", response_model=None, operation_id="forecastingExportCostForecastCSV")
def export_cost_forecast_csv(
    run_id: int,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Download a cost forecast version as CSV.

    The statutory label is carried in the ``cost_basis`` column of every
    row, so the export can never be mistaken for a fully-loaded cost.
    The newest version is exported when no version is given.
    """
    _load_run(db, run_id)
    try:
        cost = (
            get_cost_forecast(db, run_id, version)
            if version is not None
            else _latest_cost_forecast(db, run_id)
        )
    except CostForecastError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if cost is None:
        raise HTTPException(
            status_code=404,
            detail=f"No cost forecast found for run {run_id}"
            + (f" version {version}" if version is not None else ""),
        )

    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["period", "location_id", "location_code", "role_id", "role",
                    "role_code", "hours", "hourly_cost", "cost", "cost_basis"],
    )
    writer.writeheader()
    for row in cost["rows"]:
        writer.writerow({**row, "cost_basis": STATUTORY_LABEL})

    filename = f"cost_forecast_run{run_id}_v{cost['version']}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _latest_cost_forecast(db: Session, forecast_run_id: int) -> Optional[dict]:
    _query = db.query(CostForecast).filter(
        CostForecast.forecast_run_id == forecast_run_id
    )
    _tenant_id = tenant_id_for(db)
    if _tenant_id is not None:
        _query = _query.filter(
            tenant_column_criterion(CostForecast.tenant_id, _tenant_id)
        )
    f = _query.order_by(CostForecast.version.desc()).first()
    if not f:
        return None
    return get_cost_forecast(db, forecast_run_id, f.version)


@router.get("/runs/{run_id}/cost-forecast/{version}", response_model=CostForecastOut, operation_id="forecastingGetCostForecast")
def get_cost_forecast_endpoint(
    run_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Get one stored version of the run's cost forecast with its rows."""
    _load_run(db, run_id)
    try:
        cost = get_cost_forecast(db, run_id, version)
    except CostForecastError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if cost is None:
        raise HTTPException(
            status_code=404,
            detail=f"No cost forecast found for run {run_id} version {version}",
        )
    return cost


# =============================================================================
# Accuracy Endpoints (AN-06)
# =============================================================================

from app.schemas.forecasting import (
    ForecastAccuracyRecordOut,
    ForecastAccuracySyncRequest,
    ForecastAccuracySyncResult,
    PaginatedForecastAccuracy,
)
from app.services.forecast_accuracy import (
    DEFAULT_DEGRADED_THRESHOLD,
    DEFAULT_REVIEW_THRESHOLD,
    AccuracyError,
    list_forecast_accuracy,
    record_forecast_accuracy,
)


@router.post(
    "/accuracy/sync",
    response_model=ForecastAccuracySyncResult,
    status_code=200, operation_id="forecastingSyncAccuracy")
def sync_forecast_accuracy(
    payload: ForecastAccuracySyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """Compare a window's forecast demand with the actual hours measured.

    For every completed forecast run with results inside the window,
    the forecast hours are compared with the actual hours the same
    window measured (from the demand layer), and one
    ``forecast_accuracy_records`` row is written per (run, month
    period, location, role) with MAPE, MAE, bias, the sample size and
    a confidence status computed from the MAPE against the explicit
    thresholds of the request. Re-running a window replaces the rows
    it computes: nothing is stacked twice.

    This is the callable an after-payroll scheduled hook invokes; it
    is exposed as an endpoint so the window can also be run on demand.
    """
    # The audit entry is staged BEFORE the service runs, so the sync's
    # commit carries the rows and the audit in one transaction — an
    # accuracy change without its audit entry must not be possible.
    if payload.run_id is not None:
        _reject_foreign_run(db, payload.run_id)
    record_audit(db, current_user, "sync_forecast_accuracy", "ForecastAccuracyRecord", None)
    try:
        result = record_forecast_accuracy(
            db,
            start_date=payload.start_date,
            end_date=payload.end_date,
            location_id=payload.location_id,
            role_id=payload.role_id,
            run_id=payload.run_id,
            review_threshold=payload.review_threshold,
            degraded_threshold=payload.degraded_threshold,
        )
    except AccuracyError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ForecastAccuracySyncResult(
        start_date=result["start_date"],
        end_date=result["end_date"],
        review_threshold=result["review_threshold"],
        degraded_threshold=result["degraded_threshold"],
        replaced=result["replaced"],
        records=[ForecastAccuracyRecordOut(**r) for r in result["records"]],
    )


@router.get("/accuracy", response_model=PaginatedForecastAccuracy, operation_id="forecastingListAccuracy")
def list_forecast_accuracy_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
    start_date: Optional[date] = Query(None, description="Window start (inclusive)"),
    end_date: Optional[date] = Query(None, description="Window end (inclusive)"),
    location_id: Optional[int] = Query(None, description="Filter by location"),
    role_id: Optional[int] = Query(None, description="Filter by role (job)"),
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    run_id: Optional[int] = Query(None, description="Filter by forecast run"),
    status: Optional[str] = Query(None, description="Filter by computed status"),
    review_threshold: float = Query(DEFAULT_REVIEW_THRESHOLD, ge=0.0, le=1.0),
    degraded_threshold: float = Query(DEFAULT_DEGRADED_THRESHOLD, ge=0.0, le=1.0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Accuracy over time, newest first, paged.

    Every row carries the run and model version it was judged against,
    its MAPE / MAE / bias and sample size, and a confidence status
    (``ok`` | ``review`` | ``degraded``) recomputed for this request
    from the row's stored MAPE against the thresholds given here.
    """
    if degraded_threshold < review_threshold:
        raise HTTPException(
            status_code=422,
            detail="degraded_threshold must be at or above review_threshold",
        )
    if run_id is not None:
        _reject_foreign_run(db, run_id)
    try:
        result = list_forecast_accuracy(
            db,
            start_date=start_date,
            end_date=end_date,
            location_id=location_id,
            role_id=role_id,
            model_version=model_version,
            status=status,
            run_id=run_id,
            page=page,
            page_size=page_size,
            review_threshold=review_threshold,
            degraded_threshold=degraded_threshold,
        )
    except AccuracyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PaginatedForecastAccuracy(
        items=[ForecastAccuracyRecordOut(**p) for p in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
