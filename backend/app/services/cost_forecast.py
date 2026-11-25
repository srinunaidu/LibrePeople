"""Labour cost forecasting (AN-04).

Converts a ForecastRun's demand series into a labour cost forecast:
forecast hours × hourly rate, grouped by month, location, and role.

Everything is an explicit assumption. The hourly rates come from the
caller (request body), matched to the demand series by role title, role
code, or a "default" catch-all. A rate that is missing entirely is a 422,
never an implicit zero. The rule-pack-sourced rates and employer
contribution math are deliberate future scope: every output carries the
label STATUTORY_LABEL — **"excludes statutory on-costs"** — in every
response and export.

Results are stored and versioned: each POST creates the next version of
the run's cost forecast (1, 2, ...), keeping every earlier version intact
for auditability. Rows are traceable to the run id, the rates used, and
an input hash of both.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.tenancy import tenant_column_criterion, tenant_id_for, tenant_matches
from app.models.forecasting import CostForecast, CostForecastRow, ForecastResult, ForecastRun
from app.services.forecast_bridge import get_forecast_run_metadata

#: The label that must appear on every output column, API response, and CSV export.
STATUTORY_LABEL = "excludes statutory on-costs"


class CostForecastError(Exception):
    """Raised when a cost forecast cannot be computed from its inputs."""


def _scoped_run(db: Session, forecast_run_id: int) -> ForecastRun | None:
    """Load one forecast run visible to the request tenant, else ``None``.

    A row from another tenant reads as missing, so it can never be
    costed, listed or exported through this helper.
    """
    run = db.query(ForecastRun).filter(ForecastRun.id == forecast_run_id).first()
    if run is None:
        return None
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(
        getattr(run, "tenant_id", None), tenant_id
    ):
        return None
    return run


def _as_date(value) -> date:
    """Normalise a stored forecast_date to a date.

    The column is ``DateTime(timezone=True)``, but runs are created from
    plain dates, so a SQLite round-trip can hand back a datetime — and
    `datetime` does not compare with `date` in Python. Normalise here.
    """
    if isinstance(value, datetime):
        return value.date()
    return value


def _rate_for(rate_map: dict[str, float], *, role: Optional[str], role_code: Optional[str]) -> float:
    """Look up the hourly rate for a demand group.

    Matching order: exact role code (case-insensitive), exact role title
    (case-insensitive), the "default" catch-all. A role with no rate and
    no default is a caller error — surfaced, never silently zeroed.
    """
    candidates = []
    if role_code:
        candidates.append(str(role_code))
    if role:
        candidates.append(str(role))

    lowered = {str(k).strip().lower(): k for k in rate_map}
    for candidate in candidates:
        key = lowered.get(candidate.lower())
        if key is not None:
            return float(rate_map[key])

    default_key = lowered.get("default")
    if default_key is not None:
        return float(rate_map[default_key])

    raise CostForecastError(
        "no hourly rate provided for role "
        f"{candidates[0] if candidates else '<no role run>'} (and no 'default' rate)"
    )


def _input_hash(rate_map: dict[str, float], results: list[ForecastResult]) -> str:
    """Stable hash of the exact inputs: run results rows + the rate map."""
    h = hashlib.sha256()
    h.update(json.dumps(sorted(rate_map.items()), sort_keys=True).encode("utf-8"))
    for r in sorted(results, key=lambda r: (_as_date(r.forecast_date), r.series_key)):
        h.update(
            f"|{r.forecast_run_id}|{r.series_key}|{r.horizon_step}|"
            f"{_as_date(r.forecast_date).isoformat()}|{r.predicted_value}".encode("utf-8")
        )
    return h.hexdigest()


def forecast_cost(
    db: Session,
    forecast_run_id: int,
    *,
    hourly_costs: dict[str, float],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    created_by: Optional[int] = None,
) -> dict:
    """Compute, store (as a new version), and return a cost forecast.

    The run's demand series (via the AN-02 bridge) is grouped by
    month × location × role, multiplied by the given hourly rate per
    group, and persisted as version ``max(existing) + 1``.

    Returns the response payload dict; every part carries
    STATUTORY_LABEL.
    """
    if not hourly_costs:
        raise CostForecastError("hourly_costs cannot be empty")

    run = _scoped_run(db, forecast_run_id)
    if not run:
        raise CostForecastError(f"Forecast run {forecast_run_id} not found")

    # The run's results must exist — money cannot appear from nothing.
    results = (
        db.query(ForecastResult)
        .filter(ForecastResult.forecast_run_id == forecast_run_id)
        .order_by(ForecastResult.forecast_date)
        .all()
    )
    if not results:
        raise CostForecastError(
            f"Forecast run {forecast_run_id} has no forecast results to cost"
        )

    # Metadata for location/role labels (AN-02 bridge does the resolution).
    try:
        metadata = get_forecast_run_metadata(db, forecast_run_id)
    except Exception as exc:  # noqa: BLE001 - bridge raises bare RuntimeError too
        raise CostForecastError(str(exc)) from exc

    # Resolve labels once — result rows only carry the numeric series key.
    location_id = metadata.get("location_id")
    location_code = metadata.get("location_code")
    role_id = metadata.get("role_id")
    role = metadata.get("role")
    role_code = metadata.get("role_code")

    if start_date:
        results = [r for r in results if _as_date(r.forecast_date) >= start_date]
    if end_date:
        results = [r for r in results if _as_date(r.forecast_date) <= end_date]
    if not results:
        raise CostForecastError(
            f"Forecast run {forecast_run_id} has no results in {start_date}..{end_date}"
        )

    # Group demand by month. The run is single-series (one location/role),
    # so the grouping key identity comes from the run's metadata.
    hours_by_month: dict[str, float] = defaultdict(float)
    for r in results:
        # predicted_value is hours per day for demand runs (AN-01 series).
        hours_by_month[_as_date(r.forecast_date).strftime("%Y-%m")] += float(r.predicted_value)

    rate = _rate_for(hourly_costs, role=role, role_code=role_code)

    rows: list[dict] = []
    for period in sorted(hours_by_month):
        hours = round(hours_by_month[period], 4)
        rows.append(
            {
                "period": period,
                "location_id": location_id,
                "location_code": location_code,
                "role_id": role_id,
                "role": role,
                "role_code": role_code,
                "hours": hours,
                "hourly_cost": round(rate, 4),
                "cost": round(hours * rate, 4),
            }
        )

    total_cost = round(sum(row["cost"] for row in rows), 4)
    total_hours = round(sum(row["hours"] for row in rows), 4)

    # Version: the next number for this run.
    current_max = (
        db.query(CostForecast.version)
        .filter(CostForecast.forecast_run_id == forecast_run_id)
        .order_by(CostForecast.version.desc())
        .first()
    )
    version = (current_max[0] if current_max else 0) + 1

    db_forecast = CostForecast(
        forecast_run_id=forecast_run_id,
        tenant_id=getattr(run, "tenant_id", None) or tenant_id_for(db),
        version=version,
        start_date=start_date,
        end_date=end_date,
        hourly_costs=json.dumps(hourly_costs, sort_keys=True),
        input_hash=_input_hash(hourly_costs, results),
        excludes_statutory=True,
        created_by=created_by,
    )
    db.add(db_forecast)
    db.flush()

    for row in rows:
        db.add(CostForecastRow(cost_forecast_id=db_forecast.id, tenant_id=getattr(db_forecast, "tenant_id", None), **row))

    db.commit()
    db.refresh(db_forecast)

    return {
        "id": db_forecast.id,
        "forecast_run_id": forecast_run_id,
        "version": version,
        "label": STATUTORY_LABEL,
        "message": f"Labor cost forecast v{version} for run {forecast_run_id}",
        "cost_basis": STATUTORY_LABEL,
        "hourly_costs": hourly_costs,
        "input_hash": db_forecast.input_hash,
        "location_id": location_id,
        "location_code": location_code,
        "role_id": role_id,
        "role": role,
        "role_code": role_code,
        "start_date": start_date,
        "end_date": end_date,
        "periods": len(rows),
        "total_hours": total_hours,
        "total_cost": total_cost,
        "rows": rows,
        "created_at": db_forecast.created_at,
    }


def list_cost_forecasts(db: Session, forecast_run_id: int) -> list[dict]:
    """List every stored version of a run's cost forecast, newest first."""
    run = _scoped_run(db, forecast_run_id)
    if not run:
        raise CostForecastError(f"Forecast run {forecast_run_id} not found")

    out: list[dict] = []
    forecasts = (
        db.query(CostForecast)
        .filter(CostForecast.forecast_run_id == forecast_run_id)
        .order_by(CostForecast.version.desc())
        .all()
    )
    for f in forecasts:
        rows = f.rows
        out.append(
            {
                "id": f.id,
                "forecast_run_id": f.forecast_run_id,
                "version": f.version,
                "label": STATUTORY_LABEL,
                "cost_basis": STATUTORY_LABEL,
                "hourly_costs": json.loads(f.hourly_costs),
                "input_hash": f.input_hash,
                "start_date": _as_date(f.start_date) if f.start_date else None,
                "end_date": _as_date(f.end_date) if f.end_date else None,
                "periods": len(rows),
                "total_hours": round(sum(float(r.hours) for r in rows), 4),
                "total_cost": round(sum(float(r.cost) for r in rows), 4),
                "created_at": f.created_at,
            }
        )
    return out


def get_cost_forecast(db: Session, forecast_run_id: int, version: int) -> Optional[dict]:
    """Get one stored version with its full rows."""
    run = _scoped_run(db, forecast_run_id)
    if not run:
        raise CostForecastError(f"Forecast run {forecast_run_id} not found")

    f = (
        db.query(CostForecast)
        .filter(CostForecast.forecast_run_id == forecast_run_id, CostForecast.version == version)
        .first()
    )
    if not f:
        return None

    rows = [
        {
            "period": r.period,
            "location_id": r.location_id,
            "location_code": r.location_code,
            "role_id": r.role_id,
            "role": r.role,
            "role_code": r.role_code,
            "hours": float(r.hours),
            "hourly_cost": float(r.hourly_cost),
            "cost": float(r.cost),
        }
        for r in sorted(f.rows, key=lambda r: r.period)
    ]
    return {
        "id": f.id,
        "forecast_run_id": f.forecast_run_id,
        "version": f.version,
        "label": STATUTORY_LABEL,
        "cost_basis": STATUTORY_LABEL,
        "hourly_costs": json.loads(f.hourly_costs),
        "input_hash": f.input_hash,
        "location_id": rows[0]["location_id"] if rows else None,
        "location_code": rows[0]["location_code"] if rows else None,
        "role_id": rows[0]["role_id"] if rows else None,
        "role": rows[0]["role"] if rows else None,
        "role_code": rows[0]["role_code"] if rows else None,
        "start_date": _as_date(f.start_date) if f.start_date else None,
        "end_date": _as_date(f.end_date) if f.end_date else None,
        "periods": len(rows),
        "total_hours": round(sum(r["hours"] for r in rows), 4),
        "total_cost": round(sum(r["cost"] for r in rows), 4),
        "rows": rows,
        "created_at": f.created_at,
    }
