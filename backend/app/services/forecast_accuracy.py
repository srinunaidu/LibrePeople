"""Forecast accuracy tracking (AN-06).

The feedback loop for the forecast: after a payroll period has closed,
the forecast hours that a run predicted for that window are compared
with the actual hours the same window measured, and the error is
recorded per (run, month period, location, role) row — MAPE, MAE and
bias — together with a confidence status computed from the MAPE
against explicit thresholds.

The actual hours come from the demand layer: `build_demand_series`
already puts `actual_hours` on every point (approved time entries),
so the comparison uses that instead of re-deriving hours from the raw
tables. Leave hours are deliberately NOT part of it: leave is a supply
side effect, not demand that materialised.

Metrics, exactly:

* A pair is one (date, location, role) where the run has forecast
  results AND the window was measured. A day the window covers has a
  measurement even when nothing was worked (measured zero), but a day
  where BOTH sides are zero is skipped: there is nothing to compare.
* ``mape`` = mean of |forecast - actual| / |actual| over the pairs
  whose actual is not zero. It is a fraction: 0.10 is 10 %. When every
  pair's actual is zero the MAPE cannot be computed and is ``None``.
* ``mae``  = mean of |forecast - actual| over all pairs, in hours.
* ``bias`` = mean of (forecast - actual) over all pairs: positive
  means the forecast over-predicted demand.
* ``sample_size`` = the number of pairs the metrics were computed from.

Confidence status (explicit, configurable thresholds):

* MAPH <= review_threshold   -> "ok"
* MAPE <= degraded_threshold -> "review"
* otherwise                  -> "degraded"
* an uncomputable MAPE is never "ok": it is flagged "review"

Re-running the sync for a window REPLACES the rows it computes
(delete-then-insert per (run, period, location, role) key), so a
re-measured window never stacks duplicates. The unique constraint on
``forecast_accuracy_records`` makes that a database guarantee.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.tenancy import tenant_column_criterion, tenant_id_for, tenant_matches
from app.models.forecasting import (
    ForecastAccuracyRecord,
    ForecastResult,
    ForecastRun,
)
from app.services.demand import build_demand_series

#: Confidence thresholds. MAPE is a fraction, so 0.10 is 10 %.
DEFAULT_REVIEW_THRESHOLD = 0.10
DEFAULT_DEGRADED_THRESHOLD = 0.25

STATUS_OK = "ok"
STATUS_REVIEW = "review"
STATUS_DEGRADED = "degraded"


class AccuracyError(Exception):
    """A validation failure of an accuracy request (surfaced as 422)."""


def _scoped_run(db: Session, run_id: int) -> ForecastRun | None:
    """Load one forecast run visible to the request tenant, else ``None``."""
    run = db.query(ForecastRun).filter(ForecastRun.id == run_id).first()
    if run is None:
        return None
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(
        getattr(run, "tenant_id", None), tenant_id
    ):
        return None
    return run


def status_for_mape(
    mape: Optional[float],
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
    degraded_threshold: float = DEFAULT_DEGRADED_THRESHOLD,
) -> str:
    """The confidence status of one accuracy row, from its MAPE."""
    if mape is None:
        return STATUS_REVIEW
    if mape <= review_threshold:
        return STATUS_OK
    if mape <= degraded_threshold:
        return STATUS_REVIEW
    return STATUS_DEGRADED


def compute_error(
    forecast_by_date: dict[date, float],
    actual_by_date: dict[date, float],
) -> dict[str, Any]:
    """Compare forecast hours with actual hours, day by day.

    Both maps are keyed by date. Only the dates present in BOTH maps
    are compared — "both sides exist". A pair where both sides are
    exactly zero is skipped: an empty day predicts nothing and
    measured nothing. Zero-actual days with a forecast are real pairs
    (they count in MAE, bias and sample size); they are excluded from
    the MAPE because a ratio against zero is undefined.
    """
    pairs = sorted(set(forecast_by_date) & set(actual_by_date))
    sample: list[tuple[float, float]] = []
    for d in pairs:
        f = float(forecast_by_date[d])
        a = float(actual_by_date[d])
        if f == 0.0 and a == 0.0:
            continue
        sample.append((f, a))

    n = len(sample)
    if n == 0:
        return {
            "mape": None,
            "mae": 0.0,
            "bias": 0.0,
            "sample_size": 0,
            "forecast_total": 0.0,
            "actual_total": 0.0,
        }

    mape_terms = [abs(f - a) / abs(a) for f, a in sample if a != 0.0]
    mape = round(sum(mape_terms) / len(mape_terms), 6) if mape_terms else None
    mae = round(sum(abs(f - a) for f, a in sample) / n, 4)
    bias = round(sum(f - a for f, a in sample) / n, 4)
    return {
        "mape": mape,
        "mae": mae,
        "bias": bias,
        "sample_size": n,
        "forecast_total": round(sum(f for f, _ in sample), 4),
        "actual_total": round(sum(a for _, a in sample), 4),
    }


def _period_of(day: date) -> str:
    """The month bucket of a date, "YYYY-MM"."""
    return f"{day.year:04d}-{day.month:02d}"


def _validate_thresholds(
    review_threshold: float, degraded_threshold: float
) -> None:
    if review_threshold < 0 or degraded_threshold < 0:
        raise AccuracyError("thresholds must not be negative")
    if degraded_threshold < review_threshold:
        raise AccuracyError(
            "degraded_threshold must be at or above review_threshold"
        )


def _validate_window(
    start_date: date,
    end_date: date,
    review_threshold: float,
    degraded_threshold: float,
) -> None:
    if end_date < start_date:
        raise AccuracyError("end_date must not be earlier than start_date")
    _validate_thresholds(review_threshold, degraded_threshold)


def _series_value(group_results: list[dict[str, Any]], key: str) -> Any:
    """First row's attribute, from results ordered by date then horizon."""
    ordered = sorted(
        group_results, key=lambda r: (r["forecast_date"], r["horizon_step"])
    )
    return ordered[0][key]


def record_forecast_accuracy(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    location_id: Optional[int] = None,
    role_id: Optional[int] = None,
    run_id: Optional[int] = None,
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
    degraded_threshold: float = DEFAULT_DEGRADED_THRESHOLD,
    measured_at: Optional[datetime] = None,
    include_leave: bool = True,
    include_roster: bool = True,
) -> dict[str, Any]:
    """Compare every completed forecast run's window with the actuals.

    For the window ``start_date..end_date`` (inclusive), each completed
    run that has forecast results in the window is grouped into
    (run, location, role) series; each series is compared with the
    actual hours `build_demand_series` measures for the same window
    and same scope; each month bucket of the comparison becomes one
    ``forecast_accuracy_records`` row (MAPE / MAE / bias / sample
    size / confidence status).

    Rows the sync computes REPLACE the stored rows for their
    (run, period, location, role) key; nothing is stacked twice.

    Returns a summary: the window, the thresholds applied, how many
    stored rows were replaced and the records as written.
    """
    _validate_window(start_date, end_date, review_threshold, degraded_threshold)

    # Tenant scope: a caller syncs only their own tenant's runs. An explicit
    # run_id from another tenant reads as missing — the sync then measures
    # nothing, so no foreign row can be created or replaced.
    tenant_id = tenant_id_for(db)
    if run_id is not None and _scoped_run(db, run_id) is None:
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "review_threshold": review_threshold,
            "degraded_threshold": degraded_threshold,
            "replaced": 0,
            "records": [],
        }

    # The bounds are widened here and then narrowed exactly in Python
    # below: forecast_date is a DATETIME column, so on SQLite the values
    # sort as strings and an inclusive ``<= end_date`` bound would miss
    # everything stored with a time part (and miss date-only storage in
    # other spots). A ``< end_date + 1 day`` upper bound is safe for
    # both storage styles; every engine that compares dates natively
    # (Oracle) is unaffected either way.
    result_rows = (
        db.query(ForecastResult, ForecastRun)
        .join(ForecastRun, ForecastResult.forecast_run_id == ForecastRun.id)
        .filter(
            ForecastRun.status == "completed",
            ForecastResult.forecast_date >= start_date,
            ForecastResult.forecast_date < end_date + timedelta(days=1),
        )
    )
    if tenant_id is not None:
        result_rows = result_rows.filter(
            tenant_column_criterion(ForecastRun.tenant_id, tenant_id)
        )
    if run_id is not None:
        result_rows = result_rows.filter(ForecastRun.id == run_id)
    if location_id is not None:
        result_rows = result_rows.filter(ForecastRun.location_id == location_id)
    if role_id is not None:
        result_rows = result_rows.filter(ForecastRun.role_id == role_id)

    groups: dict[tuple[int, Optional[int], Optional[int]], dict[str, Any]] = {}
    run_tenants: dict[int, str | None] = {}
    for result, run in result_rows.all():
        # Normalise the comparison key from the column type: a DATETIME
        # column returns datetime objects, the demand layer's points are
        # plain dates, and the two must meet on equal keys.
        day = result.forecast_date
        if isinstance(day, datetime):
            day = day.date()
        if not start_date <= day <= end_date:
            continue  # outside the widened SQL bound, e.g. time-part rows
        key = (run.id, run.location_id, run.role_id)
        run_tenants.setdefault(run.id, getattr(run, "tenant_id", None))
        g = groups.setdefault(
            key,
            {
                "run_id": run.id,
                "location_id": run.location_id,
                "role_id": run.role_id,
                "forecast": {},
                "results": [],
            },
        )
        g["forecast"][day] = g["forecast"].get(day, 0.0) + float(
            result.predicted_value or 0.0
        )
        g["results"].append(
            {
                "forecast_date": day,
                "horizon_step": result.horizon_step,
                "rule_version": result.rule_version,
                "method_used": result.method_used,
            }
        )

    measured_at = measured_at or datetime.now(timezone.utc)

    replaced = 0
    written: list[ForecastAccuracyRecord] = []
    for key in sorted(
        groups, key=lambda k: (k[0], k[1] is not None, k[1] or 0, k[2] is not None, k[2] or 0)
    ):
        g = groups[key]
        run_id_g, loc_id_g, role_id_g = g["run_id"], g["location_id"], g["role_id"]

        actual_series = build_demand_series(
            db,
            start_date=start_date,
            end_date=end_date,
            location_id=loc_id_g,
            role=role_id_g if role_id_g is not None else None,
            include_time_entries=True,
            include_leave=include_leave,
            include_roster=include_roster,
        )
        actual_by_date = {p.date: float(p.actual_hours or 0.0) for p in actual_series}

        # Bucket the comparable day pairs by month. compute_error does
        # the both-sides-exist / both-zero-skip logic pair by pair.
        by_month: dict[str, list[tuple[float, float]]] = {}
        for d in sorted(set(g["forecast"]) & set(actual_by_date)):
            f = float(g["forecast"][d])
            a = float(actual_by_date[d])
            if f == 0.0 and a == 0.0:
                continue
            by_month.setdefault(_period_of(d), []).append((f, a))

        model_version = _series_value(g["results"], "rule_version")
        method_used = _series_value(g["results"], "method_used")

        for period in sorted(by_month):
            day_forecasts = {
                d: float(g["forecast"][d])
                for d in g["forecast"]
                if _period_of(d) == period
            }
            day_actuals = {
                d: float(actual_by_date[d])
                for d in actual_by_date
                if _period_of(d) == period
            }
            metrics = compute_error(day_forecasts, day_actuals)
            if metrics["sample_size"] == 0:
                continue

            status = status_for_mape(
                metrics["mape"], review_threshold, degraded_threshold
            )

            existing = (
                db.query(ForecastAccuracyRecord)
                .filter(
                    ForecastAccuracyRecord.forecast_run_id == run_id_g,
                    ForecastAccuracyRecord.period == period,
                    ForecastAccuracyRecord.location_id.is_(None)
                    if loc_id_g is None
                    else ForecastAccuracyRecord.location_id == loc_id_g,
                    ForecastAccuracyRecord.role_id.is_(None)
                    if role_id_g is None
                    else ForecastAccuracyRecord.role_id == role_id_g,
                )
                .delete(synchronize_session=False)
            )
            replaced += int(existing or 0)

            row = ForecastAccuracyRecord(
                forecast_run_id=run_id_g,
                tenant_id=run_tenants.get(run_id_g) or tenant_id_for(db),
                model_version=model_version,
                method_used=method_used,
                period=period,
                location_id=loc_id_g,
                role_id=role_id_g,
                forecast_hours=metrics["forecast_total"],
                actual_hours=metrics["actual_total"],
                mape=metrics["mape"],
                mae=metrics["mae"],
                bias=metrics["bias"],
                sample_size=metrics["sample_size"],
                status=status,
                measured_at=measured_at,
            )
            db.add(row)
            written.append(row)

    db.commit()

    # Payloads are built AFTER the commit, from the persisted rows: a
    # record without its primary key is not a record a reader can act
    # on, and the ids must be the ones the database assigned.
    records = [
        row_payload(r, review_threshold, degraded_threshold) for r in written
    ]

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "review_threshold": review_threshold,
        "degraded_threshold": degraded_threshold,
        "replaced": replaced,
        "records": records,
    }


def row_payload(
    row: ForecastAccuracyRecord,
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
    degraded_threshold: float = DEFAULT_DEGRADED_THRESHOLD,
) -> dict[str, Any]:
    """One accuracy row as a serialisable dict, status recomputed."""
    mape = float(row.mape) if row.mape is not None else None
    return {
        "id": row.id,
        "forecast_run_id": row.forecast_run_id,
        "model_version": row.model_version,
        "method_used": row.method_used,
        "period": row.period,
        "location_id": row.location_id,
        "role_id": row.role_id,
        "forecast_hours": float(row.forecast_hours),
        "actual_hours": float(row.actual_hours),
        "mape": mape,
        "mae": float(row.mae),
        "bias": float(row.bias),
        "sample_size": int(row.sample_size),
        "status": status_for_mape(mape, review_threshold, degraded_threshold),
        "measured_at": row.measured_at.isoformat() if row.measured_at else None,
    }


def list_forecast_accuracy(
    db: Session,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    location_id: Optional[int] = None,
    role_id: Optional[int] = None,
    model_version: Optional[str] = None,
    status: Optional[str] = None,
    run_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
    degraded_threshold: float = DEFAULT_DEGRADED_THRESHOLD,
) -> dict[str, Any]:
    """Accuracy rows over time, newest first, paged.

    The status of every returned row is RECOMPUTED from its stored
    MAPE against the thresholds of this request, so the same row can
    be read under different thresholds without re-syncing. The
    ``status`` filter is applied against that computed status.
    """
    _validate_thresholds(review_threshold, degraded_threshold)
    if start_date is not None and end_date is not None and end_date < start_date:
        raise AccuracyError("end_date must not be earlier than start_date")

    q = db.query(ForecastAccuracyRecord)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        q = q.filter(
            tenant_column_criterion(ForecastAccuracyRecord.tenant_id, tenant_id)
        )
    if start_date is not None:
        q = q.filter(ForecastAccuracyRecord.period >= _period_of(start_date))
    if end_date is not None:
        q = q.filter(ForecastAccuracyRecord.period <= _period_of(end_date))
    if location_id is not None:
        q = q.filter(ForecastAccuracyRecord.location_id == location_id)
    if role_id is not None:
        q = q.filter(ForecastAccuracyRecord.role_id == role_id)
    if model_version:
        q = q.filter(ForecastAccuracyRecord.model_version == model_version)
    if run_id is not None:
        q = q.filter(ForecastAccuracyRecord.forecast_run_id == run_id)

    rows = q.order_by(
        ForecastAccuracyRecord.measured_at.desc(), ForecastAccuracyRecord.id.desc()
    ).all()

    payloads = [row_payload(r, review_threshold, degraded_threshold) for r in rows]
    if status:
        payloads = [p for p in payloads if p["status"] == status]

    total = len(payloads)
    page_items = payloads[(page - 1) * page_size : (page - 1) * page_size + page_size]
    return {"items": page_items, "total": total, "page": page, "page_size": page_size}


#: The scheduled-comparison callable: a window between two dates, run
#: after a payroll period closes. Same behaviour as
#: record_forecast_accuracy; a separate name keeps the call site in
#: the payroll flow readable.
sync_forecast_accuracy_window = record_forecast_accuracy
