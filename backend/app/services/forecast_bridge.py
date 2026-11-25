"""Forecast-to-demand bridge.

Connects the forecasting engine (AN-01) to the scheduler (SC-01) by converting
ForecastRun results into the DemandPoint format the solver expects.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.tenancy import tenant_id_for, tenant_matches
from app.models.forecasting import ForecastResult, ForecastRun
from app.models.core_hr import Location
from app.models.job import Job
from app.services.demand import DemandPoint


class ForecastBridgeError(Exception):
    """Raised when a forecast cannot be converted to demand series."""


def _scoped_run(db: Session, forecast_run_id: int) -> ForecastRun | None:
    """Load one forecast run visible to the request tenant, else ``None``."""
    run = db.query(ForecastRun).filter(ForecastRun.id == forecast_run_id).first()
    if run is None:
        return None
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(
        getattr(run, "tenant_id", None), tenant_id
    ):
        return None
    return run


def forecast_to_demand_series(
    db: Session,
    forecast_run_id: int,
    *,
    location_id: Optional[int] = None,
    role: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[DemandPoint]:
    """Convert a ForecastRun's results into a demand series for the scheduler.

    Parameters
    ----------
    db:
        Database session.
    forecast_run_id:
        The ForecastRun to read results from.
    location_id:
        Optional location filter. If not provided, uses the run's location_id.
    role:
        Optional role filter (job title or code). If not provided, uses the run's role_id.
    start_date:
        Optional start date filter (inclusive).
    end_date:
        Optional end date filter (inclusive).

    Returns
    -------
    list[DemandPoint]
        Demand series formatted for the scheduler, with confidence bands as metadata.

    Raises
    ------
    ForecastBridgeError
        If the forecast run doesn't exist or has no results.
    """
    run = _scoped_run(db, forecast_run_id)
    if not run:
        raise ForecastBridgeError(f"Forecast run {forecast_run_id} not found")

    # Resolve location
    effective_location_id = location_id or getattr(run, "location_id", None)
    location_code = None
    if effective_location_id:
        loc = db.query(Location).filter(Location.id == effective_location_id).first()
        if loc:
            location_code = loc.code

    # Resolve role
    effective_role = role
    role_id = None
    role_label = None
    role_code = None
    if hasattr(run, "role_id") and run.role_id and not role:
        role_id = run.role_id
        job = db.query(Job).filter(Job.id == role_id).first()
        if job:
            role_label = job.title
            role_code = job.code
    elif isinstance(role, str) and role:
        job = db.query(Job).filter((Job.title == role) | (Job.code == role)).first()
        if job:
            effective_role = job.title
            role_id = job.id
            role_label = job.title
            role_code = job.code

    # Build query for results
    query = db.query(ForecastResult).filter(
        ForecastResult.forecast_run_id == forecast_run_id
    )

    if start_date:
        query = query.filter(ForecastResult.forecast_date >= start_date)
    if end_date:
        query = query.filter(ForecastResult.forecast_date <= end_date)

    results = query.order_by(ForecastResult.horizon_step).all()

    if not results:
        raise ForecastBridgeError(f"Forecast run {forecast_run_id} has no results in the requested range")

    # Convert to DemandPoint format
    demand_points = []
    for r in results:
        demand_points.append(
            DemandPoint(
                date=r.forecast_date,
                value=float(r.predicted_value),
                location_id=effective_location_id,
                location_code=location_code,
                role_id=role_id,
                role=role_label,
                role_code=role_code,
                actual_hours=0.0,
                leave_hours=0.0,
                scheduled_hours=0.0,
                source="forecast",
                lower_bound=float(r.lower_bound) if r.lower_bound is not None else None,
                upper_bound=float(r.upper_bound) if r.upper_bound is not None else None,
                forecast_run_id=forecast_run_id,
            )
        )

    return demand_points


def get_forecast_run_metadata(db: Session, forecast_run_id: int) -> dict:
    """Get metadata about a forecast run for the scheduler.

    Returns a dict with run metadata including location, role, method, accuracy, etc.
    """
    run = _scoped_run(db, forecast_run_id)
    if not run:
        raise ForecastBridgeError(f"Forecast run {forecast_run_id} not found")

    location_code = None
    if hasattr(run, "location_id") and run.location_id:
        loc = db.query(Location).filter(Location.id == run.location_id).first()
        if loc:
            location_code = loc.code

    role_label = None
    role_code = None
    if hasattr(run, "role_id") and run.role_id:
        job = db.query(Job).filter(Job.id == run.role_id).first()
        if job:
            role_label = job.title
            role_code = job.code

    return {
        "forecast_run_id": run.id,
        "name": run.name,
        "description": run.description,
        "location_id": getattr(run, "location_id", None),
        "location_code": location_code,
        "role_id": getattr(run, "role_id", None),
        "role": role_label,
        "role_code": role_code,
        "horizon_days": run.horizon_days,
        "method": run.method,
        "data_start_date": run.data_start_date,
        "data_end_date": run.data_end_date,
        "backtest_mape": float(run.backtest_mape) if run.backtest_mape is not None else None,
        "backtest_mase": float(run.backtest_mase) if run.backtest_mase is not None else None,
        "backtest_holdout_days": run.backtest_holdout_days,
        "status": run.status,
        "created_at": run.created_at,
        "finished_at": run.finished_at,
    }
