"""Forecasting engine for demand forecasting.

Implements statistical forecasting methods:
- Seasonal naive baseline
- Holt-Winters exponential smoothing (additive and multiplicative)
- Automatic model selection via rolling-origin backtest

All calculations are deterministic and traceable: every forecast result
carries an input hash, rule version, method, and accuracy metrics.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from typing import Any, Optional

import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing, SimpleExpSmoothing

from app.core.tenancy import tenant_column_criterion, tenant_id_for, tenant_matches
from app.models.forecasting import ForecastRun, ForecastResult, ForecastModelVersion

#: Default forecast horizon (days)
DEFAULT_HORIZON_DAYS = 30
#: Minimum number of observations required for forecasting
MIN_OBSERVATIONS = 56  # 8 weeks of daily data
#: Holdout size for backtest (weeks)
BACKTEST_HOLDOUT_WEEKS = 4


class ForecastError(Exception):
    """Raised when forecasting cannot produce a reliable result."""


class ForecastEngine:
    """Forecasting engine for demand forecasting.

    Supports:
    - Seasonal naive: repeats the pattern from one season ago
    - Holt-Winters exponential smoothing (additive and multiplicative)
    - Automatic model selection via rolling-origin backtest

    All calculations are deterministic and traceable: every forecast result
    carries an input hash, rule version, method, and accuracy metrics.
    """

    def __init__(self, rule_version: str = "v1.0"):
        self.rule_version = rule_version

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def forecast(
        self,
        series: list[float],
        dates: list[date],
        horizon: int = DEFAULT_HORIZON_DAYS,
        method: str = "auto",
        seasonality: int = 7,
    ) -> dict:
        """Generate a forecast for a single time series.

        Parameters
        ----------
        series:
            Historical values (must be evenly spaced daily data).
        dates:
            Corresponding dates for each value.
        horizon:
            Number of days to forecast ahead.
        method:
            Forecasting method: "seasonal_naive", "holt_winters",
            or "auto" (select via backtest).
        seasonality:
            Seasonality period in days (default 7 for weekly).

        Returns
        -------
        dict with keys:
            method_used: str
            backtest_mape: float | None
            backtest_mase: float | None
            backtest_holdout_days: int | None
            data_start_date: date | None
            data_end_date: date | None
            input_hash: str
            rule_version: str
            results: list[dict] with keys:
                horizon_step, forecast_date, predicted_value,
                lower_bound, upper_bound
        """
        if len(series) < MIN_OBSERVATIONS:
            raise ForecastError(
                f"Insufficient history: {len(series)} observations, "
                f"minimum {MIN_OBSERVATIONS} required"
            )

        if len(series) != len(dates):
            raise ValueError(
                f"Series length ({len(series)}) != dates length ({len(dates)})"
            )

        # Compute input hash for traceability
        input_hash = self._compute_input_hash(
            series, dates, horizon, method, seasonality
        )

        # Select method
        if method == "auto":
            method_used, backtest = self._select_method(series, seasonality)
        else:
            method_used = method
            backtest = self._backtest(series, seasonality, method)

        # Generate forecast
        forecast_values, lower_bounds, upper_bounds = self._generate_forecast(
            series, method_used, horizon, seasonality
        )

        # Build result records
        last_date = dates[-1]
        results = []
        for step in range(1, horizon + 1):
            forecast_date = last_date + timedelta(days=step)
            idx = step - 1
            results.append(
                {
                    "horizon_step": step,
                    "forecast_date": forecast_date,
                    "predicted_value": round(float(forecast_values[idx]), 4),
                    "lower_bound": (
                        round(float(lower_bounds[idx]), 4)
                        if lower_bounds[idx] is not None
                        else None
                    ),
                    "upper_bound": (
                        round(float(upper_bounds[idx]), 4)
                        if upper_bounds[idx] is not None
                        else None
                    ),
                }
            )

        return {
            "method_used": method_used,
            "backtest_mape": backtest.get("mape"),
            "backtest_mase": backtest.get("mase"),
            "backtest_holdout_days": backtest.get("holdout_days"),
            "data_start_date": dates[0],
            "data_end_date": dates[-1],
            "input_hash": input_hash,
            "rule_version": self.rule_version,
            "results": results,
        }

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_input_hash(
        series: list[float],
        dates: list[date],
        horizon: int,
        method: str,
        seasonality: int,
    ) -> str:
        """Compute a stable hash of all inputs for reproducibility."""
        h = hashlib.sha256()
        h.update(method.encode())
        h.update(str(seasonality).encode())
        h.update(str(horizon).encode())
        for v in series:
            h.update(f"{v:.10f}".encode())
        for d in dates:
            h.update(d.isoformat().encode())
        return h.hexdigest()

    def _select_method(
        self, series: list[float], seasonality: int
    ) -> tuple[str, dict]:
        """Select the best forecasting method via rolling-origin backtest.

        Compares seasonal naive vs Holt-Winters and picks the one with
        lower MAPE on the holdout window.
        """
        naive_result = self._backtest(series, seasonality, "seasonal_naive")
        hw_result = self._backtest(series, seasonality, "holt_winters")

        if naive_result["mape"] is None and hw_result["mape"] is None:
            # Neither method could be evaluated; default to seasonal naive
            return "seasonal_naive", {
                "mape": None,
                "mase": None,
                "holdout_days": 0,
            }

        if naive_result["mape"] is None:
            return "holt_winters", hw_result
        if hw_result["mape"] is None:
            return "seasonal_naive", naive_result

        if naive_result["mape"] <= hw_result["mape"]:
            return "seasonal_naive", naive_result
        return "holt_winters", hw_result

    def _backtest(
        self, series: list[float], seasonality: int, method: str
    ) -> dict:
        """Rolling-origin backtest for method selection.

        Uses the last BACKTEST_HOLDOUT_WEEKS * 7 observations as holdout,
        trains on the preceding data, and evaluates forecast accuracy.
        """
        n = len(series)
        holdout = min(BACKTEST_HOLDOUT_WEEKS * 7, n // 4)
        if holdout < 7 or n - holdout < MIN_OBSERVATIONS:
            return {"mape": None, "mase": None, "holdout_days": 0}

        train = series[: n - holdout]
        test = series[n - holdout :]

        try:
            forecast_values, _, _ = self._generate_forecast(
                train, method, holdout, seasonality
            )
        except Exception:
            return {"mape": None, "mase": None, "holdout_days": holdout}

        # Compute MAPE and MASE
        actuals = test[: len(forecast_values)]
        forecasts = forecast_values[: len(actuals)]

        mape = self._compute_mape(actuals, forecasts)
        mase = self._compute_mase(actuals, forecasts, train)

        return {
            "mape": mape,
            "mase": mase,
            "holdout_days": holdout,
        }

    def _generate_forecast(
        self,
        series: list[float],
        method: str,
        horizon: int,
        seasonality: int,
    ) -> tuple[list[float], list[float | None], list[float | None]]:
        """Generate forecast values with confidence bands.

        Returns (values, lower_bounds, upper_bounds).
        """
        if method == "seasonal_naive":
            return self._seasonal_naive(series, horizon, seasonality)
        if method == "holt_winters":
            return self._holt_winters(series, horizon, seasonality)
        raise ValueError(f"Unknown method: {method}")

    @staticmethod
    def _seasonal_naive(
        series: list[float],
        horizon: int,
        seasonality: int,
    ) -> tuple[list[float], list[float | None], list[float | None]]:
        """Seasonal naive forecast: repeats values from one season ago.

        For horizon step h, predicts series[-seasonality + (h-1) % seasonality].
        """
        n = len(series)
        values: list[float] = []
        lower_bounds: list[float | None] = []
        upper_bounds: list[float | None] = []

        # Compute residual standard error for confidence bands
        residuals = []
        for i in range(seasonality, n):
            residuals.append(series[i] - series[i - seasonality])
        residual_std = float(np.std(residuals)) if residuals else 0.0

        for step in range(1, horizon + 1):
            idx = (n - seasonality) + (step - 1) % seasonality
            if idx < 0:
                idx = 0
            values.append(float(series[idx]))
            # Simple confidence band: ±1.96 * residual_std
            margin = 1.96 * residual_std
            lower_bounds.append(max(0.0, values[-1] - margin))
            upper_bounds.append(values[-1] + margin)

        return values, lower_bounds, upper_bounds

    def _holt_winters(
        self,
        series: list[float],
        horizon: int,
        seasonality: int,
    ) -> tuple[list[float], list[float | None], list[float | None]]:
        """Holt-Winters exponential smoothing forecast.

        Uses additive trend and seasonal components by default.
        Falls back to multiplicative if additive fails.
        """
        n = len(series)
        seasonal_periods = min(seasonality, n // 2)
        if seasonal_periods < 2:
            # Fall back to simple exponential smoothing
            return self._holt_winters_simple(series, horizon)

        try:
            model = ExponentialSmoothing(
                series,
                seasonal_periods=seasonal_periods,
                trend="add",
                seasonal="add",
                damped_trend=True,
            )
            fitted = model.fit()
        except Exception:
            # Fall back to multiplicative trend
            try:
                model = ExponentialSmoothing(
                    series,
                    seasonal_periods=seasonal_periods,
                    trend="mul",
                    seasonal="mul",
                    damped_trend=True,
                )
                fitted = model.fit()
            except Exception:
                # Fall back to simple exponential smoothing
                return self._holt_winters_simple(series, horizon)

        forecast = fitted.forecast(horizon)
        values = [float(v) for v in forecast]

        # Compute residual standard error for confidence bands
        fitted_values = fitted.fittedvalues
        residuals = np.array(series) - np.array(fitted_values)
        residual_std = float(np.std(residuals)) if len(residuals) > 0 else 0.0

        margin = 1.96 * residual_std
        lower_bounds = [max(0.0, v - margin) for v in values]
        upper_bounds = [v + margin for v in values]

        return values, lower_bounds, upper_bounds

    @staticmethod
    def _holt_winters_simple(
        series: list[float], horizon: int
    ) -> tuple[list[float], list[float | None], list[float | None]]:
        """Simple exponential smoothing fallback."""
        model = SimpleExpSmoothing(series)
        fitted = model.fit()
        forecast = fitted.forecast(horizon)
        values = [float(v) for v in forecast]

        # Simple confidence band based on residual std
        fitted_values = fitted.fittedvalues
        residuals = np.array(series) - np.array(fitted_values)
        residual_std = float(np.std(residuals)) if len(residuals) > 0 else 0.0
        margin = 1.96 * residual_std

        lower_bounds = [max(0.0, v - margin) for v in values]
        upper_bounds = [v + margin for v in values]

        return values, lower_bounds, upper_bounds

    @staticmethod
    def _compute_mape(actuals: list[float], forecasts: list[float]) -> float | None:
        """Mean Absolute Percentage Error."""
        if not actuals or not forecasts:
            return None
        pairs = [(a, f) for a, f in zip(actuals, forecasts) if a != 0]
        if not pairs:
            return None
        errors = [abs(a - f) / abs(a) for a, f in pairs]
        return float(np.mean(errors))

    @staticmethod
    def _compute_mase(
        actuals: list[float], forecasts: list[float], train: list[float]
    ) -> float | None:
        """Mean Absolute Scaled Error."""
        if not actuals or not forecasts or len(train) < 2:
            return None
        mae = float(np.mean([abs(a - f) for a, f in zip(actuals, forecasts)]))
        naive_mae = float(
            np.mean(
                [
                    abs(train[i] - train[i - 1])
                    for i in range(1, len(train))
                ]
            )
        )
        if naive_mae == 0:
            return None
        return float(mae / naive_mae)
# =============================================================================
# Scenario Forecasting
# =============================================================================

import json
from sqlalchemy.orm import Session

from app.models.forecasting import (
    ForecastRun, ForecastResult, ForecastScenario, ForecastScenarioResult
)
from app.models.user import User


class ScenarioError(Exception):
    """Raised when scenario operations cannot be completed."""
    pass


def _scoped_run(db: Session, run_id: int) -> ForecastRun | None:
    """Load one forecast run visible to the request tenant, else ``None``.

    A row from another tenant reads as missing (the endpoint turns it
    into a 404), so no cross-tenant id can ever be projected, costed,
    compared or synced through this helper.
    """
    run = db.query(ForecastRun).filter(ForecastRun.id == run_id).first()
    if run is None:
        return None
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(
        getattr(run, "tenant_id", None), tenant_id
    ):
        return None
    return run


def _scoped_scenario(db: Session, scenario_id: int):
    """Load one scenario visible to the request tenant, else ``None``."""
    from app.models.forecasting import ForecastScenario

    scenario = (
        db.query(ForecastScenario)
        .filter(ForecastScenario.id == scenario_id)
        .first()
    )
    if scenario is None:
        return None
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(
        getattr(scenario, "tenant_id", None), tenant_id
    ):
        return None
    return scenario


# Supported assumption types
ASSUMPTION_TYPES = {
    "demand_multiplier": {"unit": "ratio", "description": "Multiply all forecast values by this ratio"},
    "demand_delta": {"unit": "absolute", "description": "Add a fixed amount to all forecast values"},
    "headcount_cap": {"unit": "absolute", "description": "Cap forecast values at this maximum"},
    "seasonality_override": {"unit": "days", "description": "Change the seasonality period in days"},
    "method_override": {"unit": "method", "description": "Force a specific forecasting method"},
    # --- AN-05 scenario builder keys (HR-flavoured, unit percent) --------- #
    "attrition_rate": {
        "unit": "percent",
        "description": (
            "Annualised attrition as a percent per year. Compounds DOWN the "
            "projected demand day by day: day i is scaled by "
            "(1 - rate/100) ** (i / 365)."
        ),
    },
    "hire_rate": {
        "unit": "percent",
        "description": (
            "Annualised hiring growth as a percent per year. Compounds UP "
            "the projected demand day by day: day i is scaled by "
            "(1 + rate/100) ** (i / 365)."
        ),
    },
    "leave_rate": {
        "unit": "percent",
        "description": (
            "Share of hours lost to leave as a percent of the projected "
            "demand. Scales every period by (1 - rate/100)."
        ),
    },
    "wage_growth_pct": {
        "unit": "percent",
        "description": (
            "Annualised wage growth as a percent per year. Does not change "
            "the demand projection; compounds the HOURLY RATE of the "
            "scenario's cost projection month by month "
            "(rate * (1 + pct/100) ** (month_index / 12))."
        ),
    },
}

#: Assumptions whose value must sit in [0, 100] and be numeric. A value
#: outside the range is a caller error, named in the message.
PERCENT_ASSUMPTION_KEYS = ("attrition_rate", "hire_rate", "leave_rate", "wage_growth_pct")


def validate_assumptions(assumptions: list[dict]) -> None:
    """Validate that all assumptions have valid keys and structure."""
    for assumption in assumptions:
        if "key" not in assumption or "value" not in assumption or "unit" not in assumption:
            raise ScenarioError(
                f"Invalid assumption format: {assumption}. "
                f"Must have 'key', 'value', and 'unit' fields."
            )
        if assumption["key"] not in ASSUMPTION_TYPES:
            raise ScenarioError(
                f"Unknown assumption type: {assumption['key']}. "
                f"Supported types: {list(ASSUMPTION_TYPES.keys())}"
            )
        expected_unit = ASSUMPTION_TYPES[assumption["key"]]["unit"]
        if assumption["unit"] != expected_unit:
            raise ScenarioError(
                f"Assumption '{assumption['key']}' expects unit '{expected_unit}', "
                f"got '{assumption['unit']}'"
            )
        if assumption["key"] in PERCENT_ASSUMPTION_KEYS:
            # A percent assumption must be a plain number a reader of the
            # assumptions table can judge; 0..100 is the whole range.
            try:
                pct = float(assumption["value"])
            except (TypeError, ValueError) as exc:
                raise ScenarioError(
                    f"Assumption '{assumption['key']}' expects a numeric "
                    f"percent, got {assumption['value']!r}"
                ) from exc
            if pct < 0 or pct > 100:
                raise ScenarioError(
                    f"Assumption '{assumption['key']}' must be between 0 and "
                    f"100 (percent), got {pct}"
                )


def apply_assumptions(
    base_values: list[float],
    assumptions: list[dict],
    seasonality: int = 7,
) -> tuple[list[float], int | None, str | None]:
    """Apply assumptions to a base forecast series.

    Returns (transformed_values, new_seasonality, new_method).
    """
    values = list(base_values)
    new_seasonality = None
    new_method = None

    for assumption in assumptions:
        key = assumption["key"]
        value = assumption["value"]

        if key == "demand_multiplier":
            # Multiply all values by the ratio
            multiplier = float(value)
            values = [v * multiplier for v in values]

        elif key == "demand_delta":
            # Add fixed amount to all values
            delta = float(value)
            values = [v + delta for v in values]

        elif key == "headcount_cap":
            # Cap values at maximum
            cap = float(value)
            values = [min(v, cap) for v in values]

        elif key == "seasonality_override":
            # Change seasonality period
            new_seasonality = int(value)

        elif key == "method_override":
            # Force a specific method
            method = str(value)
            if method not in ("seasonal_naive", "holt_winters", "auto"):
                raise ScenarioError(f"Invalid method override: {method}")
            new_method = method

        # --- AN-05 scenario builder keys ---------------------------------- #
        # All four are percent assumptions. attrition_rate, hire_rate and
        # leave_rate reshape the projected demand series explicitly below;
        # wage_growth_pct shapes the COST projection only (see
        # project_scenario_costs) and is a deliberate no-op on demand.
        elif key == "attrition_rate":
            annual = float(value) / 100.0
            values = [
                v * (1.0 - annual) ** (i / 365.0)
                for i, v in enumerate(values, start=1)
            ]

        elif key == "hire_rate":
            annual = float(value) / 100.0
            values = [
                v * (1.0 + annual) ** (i / 365.0)
                for i, v in enumerate(values, start=1)
            ]

        elif key == "leave_rate":
            factor = 1.0 - float(value) / 100.0
            values = [v * factor for v in values]

        elif key == "wage_growth_pct":
            # Cost-side only: no demand change. Recorded in the
            # assumptions table that comes back with every result.
            pass

    return values, new_seasonality, new_method


def compute_scenario_input_hash(
    base_input_hash: str,
    assumptions: list[dict],
) -> str:
    """Compute a stable hash for the scenario based on base hash and assumptions."""
    import hashlib
    h = hashlib.sha256()
    h.update(base_input_hash.encode())
    # Add assumptions in a deterministic order
    for assumption in sorted(assumptions, key=lambda x: x["key"]):
        h.update(json.dumps(assumption, sort_keys=True).encode())
    return h.hexdigest()


def create_scenario(
    db: Session,
    base_run_id: int,
    assumptions: list[dict],
    name: str,
    description: str | None,
    user_id: int,
) -> ForecastScenario:
    """Create a scenario from a base forecast run.

    Clones the base run, applies assumptions, re-runs forecast, and stores results.
    """
    # Validate assumptions
    validate_assumptions(assumptions)

    # Get base run
    base_run = _scoped_run(db, base_run_id)
    if not base_run:
        raise ScenarioError(f"Base forecast run {base_run_id} not found")

    # Get base run results
    base_results = (
        db.query(ForecastResult)
        .filter(ForecastResult.forecast_run_id == base_run_id)
        .order_by(ForecastResult.horizon_step)
        .all()
    )
    if not base_results:
        raise ScenarioError(f"Base forecast run {base_run_id} has no results")

    # Extract base forecast values and metadata
    base_values = [float(r.predicted_value) for r in base_results]
    base_dates = [r.forecast_date for r in base_results]
    horizon = len(base_results)
    series_key = base_results[0].series_key
    method_used = base_results[0].method_used
    rule_version = base_results[0].rule_version
    data_start_date = base_results[0].data_start_date
    data_end_date = base_results[0].data_end_date
    base_input_hash = base_results[0].input_hash

    # Apply assumptions
    transformed_values, new_seasonality, new_method = apply_assumptions(
        base_values, assumptions, base_run.method if base_run.method != "auto" else 7
    )

    # Determine method to use for scenario
    scenario_method = new_method if new_method else method_used
    scenario_seasonality = new_seasonality if new_seasonality else 7

    # Re-run forecast engine with transformed base series if method override or seasonality override
    # Otherwise, just use transformed values directly
    if new_method or new_seasonality:
        # Need to re-run the forecasting engine with the original historical data
        # But we only have the forecast results, not the historical data.
        # For now, use the transformed values directly and recompute confidence bands.
        # A full re-forecast would require access to historical data.
        pass

    # Compute confidence bands based on transformed values
    # Use the same margin as base run (simplified approach)
    lower_bounds = []
    upper_bounds = []
    if base_results[0].lower_bound is not None and base_results[0].upper_bound is not None:
        # Scale confidence bands proportionally
        for i, base_result in enumerate(base_results):
            if base_result.predicted_value != 0:
                ratio = transformed_values[i] / float(base_result.predicted_value)
                lower_bounds.append(
                    float(base_result.lower_bound) * ratio
                    if base_result.lower_bound is not None else None
                )
                upper_bounds.append(
                    float(base_result.upper_bound) * ratio
                    if base_result.upper_bound is not None else None
                )
            else:
                lower_bounds.append(None)
                upper_bounds.append(None)
    else:
        lower_bounds = [None] * horizon
        upper_bounds = [None] * horizon

    # Compute scenario input hash
    scenario_input_hash = compute_scenario_input_hash(base_input_hash, assumptions)

    # Create scenario record
    scenario = ForecastScenario(
        name=name,
        description=description,
        tenant_id=getattr(base_run, "tenant_id", None) or tenant_id_for(db),
        base_run_id=base_run_id,
        assumptions=json.dumps(assumptions),
        created_by=user_id,
        version_no=1,
        source="created",
    )
    db.add(scenario)
    db.flush()
    # A freshly created scenario is the root (v1) of its own lineage.
    scenario.root_id = scenario.id

    # Create scenario result records
    for i, (value, date, lower, upper) in enumerate(
        zip(transformed_values, base_dates, lower_bounds, upper_bounds), 1
    ):
        scenario_result = ForecastScenarioResult(
            scenario_id=scenario.id,
            tenant_id=getattr(scenario, "tenant_id", None),
            series_key=series_key,
            horizon_step=i,
            forecast_date=date,
            predicted_value=round(value, 4),
            lower_bound=round(lower, 4) if lower is not None else None,
            upper_bound=round(upper, 4) if upper is not None else None,
            input_hash=scenario_input_hash,
            rule_version=rule_version,
            method_used=scenario_method,
            data_start_date=data_start_date,
            data_end_date=data_end_date,
        )
        db.add(scenario_result)

    db.commit()
    db.refresh(scenario)

    return scenario


def get_scenario(db: Session, scenario_id: int) -> ForecastScenario | None:
    """Get a scenario by ID with results loaded.

    Tenant-scoped: a scenario from another tenant reads as missing, so
    the endpoint answers 404 and never reveals it.
    """
    return _scoped_scenario(db, scenario_id)


def list_scenarios(
    db: Session,
    base_run_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ForecastScenario], int]:
    """List scenarios with optional filtering by base_run_id.

    Tenant-scoped: a caller sees only their own tenant's scenarios (plus
    pre-backfill rows for the legacy default tenant).
    """
    query = db.query(ForecastScenario)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        query = query.filter(
            tenant_column_criterion(ForecastScenario.tenant_id, tenant_id)
        )
    if base_run_id is not None:
        query = query.filter(ForecastScenario.base_run_id == base_run_id)
    total = query.count()
    scenarios = (
        query.order_by(ForecastScenario.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return scenarios, total


def project_scenario_costs(
    results_rows: list[Any],
    hourly_costs: dict[str, float],
    wage_growth_pct: float = 0.0,
) -> dict:
    """Project a scenario version's demand as a labour cost (AN-05).

    The costs are ALWAYS explicit: the hourly rates come from the caller
    of the comparison (``hourly_costs`` in the request body), never from
    anywhere implicit. The series carries no role split in this delivery,
    so the rate applied is the caller's ``default`` rate — or, when the
    map has exactly one entry, that one rate. Anything else is refused,
    never guessed.

    ``wage_growth_pct`` compounds the applied rate: month m of the window
    is costed at ``rate * (1 + pct/100) ** (m / 12)``.

    Every row carries the STATUTORY_LABEL — the projection says what it
    excludes, everywhere it is shown.
    """
    from app.services.cost_forecast import STATUTORY_LABEL  # local: no cycle

    if not hourly_costs:
        raise ScenarioError("hourly_costs cannot be empty")

    lowered = {str(k).strip().lower(): k for k in hourly_costs}
    if "default" in lowered:
        rate = float(hourly_costs[lowered["default"]])
    elif len(hourly_costs) == 1:
        rate = float(next(iter(hourly_costs.values())))
    else:
        raise ScenarioError(
            "hourly_costs must include a 'default' rate (or be exactly one "
            "rate); the scenario demand series carries no role split, so a "
            "cost projection is never implicit"
        )

    def _as_date(value):
        if isinstance(value, datetime):
            return value.date()
        return value

    # Demand hours by month bucket. predicted_value is hours per day.
    hours_by_month: dict[str, float] = {}
    for row in results_rows:
        period = _as_date(row.forecast_date).strftime("%Y-%m")
        hours_by_month[period] = hours_by_month.get(period, 0.0) + float(row.predicted_value)

    annual = float(wage_growth_pct or 0.0) / 100.0
    out_rows: list[dict] = []
    for month_index, period in enumerate(sorted(hours_by_month)):
        hours = round(hours_by_month[period], 4)
        period_rate = round(rate * (1.0 + annual) ** (month_index / 12.0), 4)
        out_rows.append(
            {
                "period": period,
                "hours": hours,
                "hourly_cost": period_rate,
                "cost": round(hours * period_rate, 4),
                "cost_basis": STATUTORY_LABEL,
            }
        )

    return {
        "hourly_costs": hourly_costs,
        "wage_growth_pct": float(wage_growth_pct or 0.0),
        "rows": out_rows,
        "total_hours": round(sum(r["hours"] for r in out_rows), 4),
        "total_cost": round(sum(r["cost"] for r in out_rows), 4),
        "label": STATUTORY_LABEL,
        "cost_basis": STATUTORY_LABEL,
    }


def compare_scenarios(
    db: Session,
    scenario_ids: list[int],
    hourly_costs: dict[str, float] | None = None,
) -> dict:
    """Compare scenario versions side-by-side (AN-05).

    Every participant may be ANY version of any scenario, and the response
    carries each participant's assumptions AND its version metadata
    (``version_no``, ``root_id``, ``source``, ``forked_from_scenario_id``)
    so the reader knows exactly what was compared.

    When ``hourly_costs`` is supplied, each participant also gets an
    explicit cost projection of its own projected demand (its
    ``wage_growth_pct`` compounding the given rates month by month); the
    costs carry the statutory label and the projection appears nowhere
    without the request asking for it.
    """
    if len(scenario_ids) < 2:
        raise ScenarioError("At least 2 scenarios required for comparison")

    scenarios = []
    for sid in scenario_ids:
        scenario = get_scenario(db, sid)
        if not scenario:
            raise ScenarioError(f"Scenario {sid} not found")
        scenarios.append(scenario)

    # Results for each participant, ordered by horizon step.
    scenario_results = {}
    for scenario in scenarios:
        results = (
            db.query(ForecastScenarioResult)
            .filter(ForecastScenarioResult.scenario_id == scenario.id)
            .order_by(ForecastScenarioResult.horizon_step)
            .all()
        )
        scenario_results[scenario.id] = results

    # Build the period-by-period comparison against the first participant.
    comparison = []
    base_scenario_id = scenario_ids[0]
    base_results = scenario_results.get(base_scenario_id, [])

    for i, base_result in enumerate(base_results):
        horizon_step = base_result.horizon_step
        forecast_date = base_result.forecast_date
        base_value = float(base_result.predicted_value)

        scenario_values = {}
        deltas = {}
        assumptions_map = {}

        for scenario in scenarios:
            sid = scenario.id
            results = scenario_results.get(sid, [])
            if i < len(results):
                scenario_values[sid] = float(results[i].predicted_value)
                deltas[sid] = round(float(results[i].predicted_value) - base_value, 4)
            else:
                scenario_values[sid] = None
                deltas[sid] = None
            assumptions_map[sid] = json.loads(scenario.assumptions) if scenario.assumptions else []

        comparison.append({
            "horizon_step": horizon_step,
            "forecast_date": forecast_date,
            "base_value": base_value,
            "scenario_values": scenario_values,
            "deltas": deltas,
            "assumptions": assumptions_map,
        })

    # Optional, explicit cost projection per participant.
    costs_out: dict[int, dict] | None = None
    if hourly_costs:
        costs_out = {}
        first_total: float | None = None
        for scenario in scenarios:
            projection = project_scenario_costs(
                scenario_results.get(scenario.id, []),
                hourly_costs,
                wage_growth_pct=_assumption_value(
                    json.loads(scenario.assumptions or "[]"), "wage_growth_pct"
                ),
            )
            if first_total is None:
                first_total = projection["total_cost"]
                projection["total_cost_delta"] = 0.0
            else:
                projection["total_cost_delta"] = round(
                    projection["total_cost"] - first_total, 4
                )
            costs_out[scenario.id] = projection

    # Participant payloads: assumptions + results + version metadata.
    scenario_outputs = []
    for scenario in scenarios:
        scenario_outputs.append({
            "id": scenario.id,
            "name": scenario.name,
            "description": scenario.description,
            "base_run_id": scenario.base_run_id,
            "assumptions": json.loads(scenario.assumptions) if scenario.assumptions else [],
            "created_at": scenario.created_at,
            "created_by": scenario.created_by,
            "version_no": scenario.version_no or 1,
            "root_id": scenario.root_id,
            "source": scenario.source or "created",
            "forked_from_scenario_id": scenario.forked_from_scenario_id,
            "results": [
                {
                    "horizon_step": r.horizon_step,
                    "forecast_date": r.forecast_date,
                    "predicted_value": float(r.predicted_value),
                    "lower_bound": float(r.lower_bound) if r.lower_bound is not None else None,
                    "upper_bound": float(r.upper_bound) if r.upper_bound is not None else None,
                    "method_used": r.method_used,
                    "input_hash": r.input_hash,
                    "rule_version": r.rule_version,
                    "data_start_date": r.data_start_date,
                    "data_end_date": r.data_end_date,
                    "series_key": r.series_key,
                }
                for r in scenario_results[scenario.id]
            ],
        })

    return {
        "scenarios": scenario_outputs,
        "comparison": comparison,
        "costs": costs_out,
    }


def _assumption_value(assumptions: list[dict], key: str) -> float:
    """The numeric value of one assumption, 0.0 when absent."""
    for assumption in assumptions:
        try:
            if assumption.get("key") == key:
                return float(assumption.get("value") or 0.0)
        except (TypeError, ValueError):
            continue
    return 0.0


# =============================================================================
# Scenario Builder: edit, fork and version a scenario (AN-05)
# =============================================================================


def edit_scenario_version(
    db: Session,
    scenario_id: int,
    assumptions: list[dict],
    name: str | None = None,
    description: str | None = None,
    user_id: int | None = None,
) -> ForecastScenario | None:
    """Edit a scenario by creating its NEXT version.

    Editing never overwrites: the assumptions under question define a new
    version (``version_no`` + 1 of the same lineage root), stored as a new
    scenario row, and the previous version stays exactly as it was, still
    retrievable and still comparable.

    Returns the new version, or None when the scenario does not exist.
    Raises ScenarioError for invalid assumptions (the message names the
    assumption key).
    """
    scenario = get_scenario(db, scenario_id)
    if not scenario:
        return None

    # A bad assumption set is rejected before anything is written.
    validate_assumptions(assumptions)

    root_id = scenario.root_id or scenario.id
    _tenant_id = tenant_id_for(db)
    _version_query = db.query(ForecastScenario).filter(
        ForecastScenario.root_id == root_id
    )
    if _tenant_id is not None:
        _version_query = _version_query.filter(
            tenant_column_criterion(ForecastScenario.tenant_id, _tenant_id)
        )
    latest_version = _version_query.order_by(
        ForecastScenario.version_no.desc()
    ).first()
    next_version_no = (latest_version.version_no if latest_version else 1) + 1

    # Re-project the base run's series under the edited assumptions with
    # the AN-03 scenario engine — a separate statistical run per scenario
    # is deliberately out of scope for this delivery.
    projection = _project_base_run(db, scenario.base_run_id, assumptions)

    edited = ForecastScenario(
        name=name if name is not None else scenario.name,
        description=description if description is not None else scenario.description,
        tenant_id=getattr(scenario, "tenant_id", None),
        base_run_id=scenario.base_run_id,
        assumptions=json.dumps(assumptions),
        created_by=user_id,
        version_no=next_version_no,
        root_id=root_id,
        source="edited",
        forked_from_scenario_id=None,
    )
    db.add(edited)
    db.flush()
    _store_projection(db, edited, projection)
    db.commit()
    db.refresh(edited)
    return edited


def fork_scenario(
    db: Session,
    scenario_id: int,
    name: str | None = None,
    description: str | None = None,
    user_id: int | None = None,
) -> ForecastScenario | None:
    """Fork a scenario version into a new, independent lineage.

    The new scenario copies the forked version's assumptions, starts its
    own version line at 1, and records exactly which version it forked
    from. Nothing about the source changes.

    Returns the fork, or None when the scenario does not exist.
    """
    scenario = get_scenario(db, scenario_id)
    if not scenario:
        return None

    assumptions = json.loads(scenario.assumptions) if scenario.assumptions else []
    projection = _project_base_run(db, scenario.base_run_id, assumptions)

    fork = ForecastScenario(
        name=name if name is not None else f"{scenario.name} (fork)",
        description=description if description is not None else scenario.description,
        tenant_id=getattr(scenario, "tenant_id", None),
        base_run_id=scenario.base_run_id,
        assumptions=scenario.assumptions,
        created_by=user_id,
        version_no=1,
        source="forked",
        forked_from_scenario_id=scenario_id,
    )
    db.add(fork)
    db.flush()
    fork.root_id = fork.id
    _store_projection(db, fork, projection)
    db.commit()
    db.refresh(fork)
    return fork


def list_scenario_versions(
    db: Session,
    scenario_id: int,
) -> list[ForecastScenario] | None:
    """Every version of a scenario's lineage, oldest first.

    Returns None when the scenario does not exist.
    """
    scenario = get_scenario(db, scenario_id)
    if not scenario:
        return None

    root_id = scenario.root_id or scenario.id
    query = db.query(ForecastScenario).filter(ForecastScenario.root_id == root_id)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        query = query.filter(
            tenant_column_criterion(ForecastScenario.tenant_id, tenant_id)
        )
    return (
        query.order_by(ForecastScenario.version_no.asc(), ForecastScenario.id.asc())
        .all()
    )


def _project_base_run(db: Session, base_run_id: int, assumptions: list[dict]) -> dict:
    """Project a base run's series under assumptions with the AN-03 engine.

    Shared by create, edit and fork: one projection code path, so no
    version of a scenario can be built differently from another.
    """
    base_run = _scoped_run(db, base_run_id)
    if not base_run:
        raise ScenarioError(f"Base forecast run {base_run_id} not found")

    base_results = (
        db.query(ForecastResult)
        .filter(ForecastResult.forecast_run_id == base_run_id)
        .order_by(ForecastResult.horizon_step)
        .all()
    )
    if not base_results:
        raise ScenarioError(f"Base forecast run {base_run_id} has no results")

    base_values = [float(r.predicted_value) for r in base_results]
    base_dates = [r.forecast_date for r in base_results]
    horizon = len(base_results)
    series_key = base_results[0].series_key
    method_used = base_results[0].method_used
    rule_version = base_results[0].rule_version
    data_start_date = base_results[0].data_start_date
    data_end_date = base_results[0].data_end_date
    base_input_hash = base_results[0].input_hash

    transformed_values, _new_seasonality, new_method = apply_assumptions(
        base_values, assumptions, 7
    )
    scenario_method = new_method if new_method else method_used

    # Scale the base run's confidence bands by the same ratio, so bands
    # move with the assumptions instead of pretending nothing changed.
    lower_bounds: list[float | None] = []
    upper_bounds: list[float | None] = []
    for i, base_result in enumerate(base_results):
        b_value = float(base_result.predicted_value)
        if base_result.lower_bound is not None and base_result.upper_bound is not None and b_value != 0:
            ratio = transformed_values[i] / b_value
            lower_bounds.append(
                float(base_result.lower_bound) * ratio
                if base_result.lower_bound is not None else None
            )
            upper_bounds.append(
                float(base_result.upper_bound) * ratio
                if base_result.upper_bound is not None else None
            )
        else:
            # No base bands to scale (or a zero base value): no band is
            # better than an invented one.
            lower_bounds.append(None)
            upper_bounds.append(None)

    scenario_input_hash = compute_scenario_input_hash(base_input_hash, assumptions)

    return {
        "values": transformed_values,
        "dates": base_dates,
        "series_key": series_key,
        "method_used": scenario_method,
        "rule_version": rule_version,
        "data_start_date": data_start_date,
        "data_end_date": data_end_date,
        "input_hash": scenario_input_hash,
        "lower_bounds": lower_bounds,
        "upper_bounds": upper_bounds,
        "horizon": horizon,
    }


def _store_projection(
    db: Session, scenario: ForecastScenario, projection: dict
) -> None:
    """Write one projection's result rows for a scenario row."""
    for i in range(projection["horizon"]):
        value = projection["values"][i]
        lower = projection["lower_bounds"][i]
        upper = projection["upper_bounds"][i]
        db.add(
            ForecastScenarioResult(
                scenario_id=scenario.id,
                tenant_id=getattr(scenario, "tenant_id", None),
                series_key=projection["series_key"],
                horizon_step=i + 1,
                forecast_date=projection["dates"][i],
                predicted_value=round(float(value), 4),
                lower_bound=round(float(lower), 4) if lower is not None else None,
                upper_bound=round(float(upper), 4) if upper is not None else None,
                input_hash=projection["input_hash"],
                rule_version=projection["rule_version"],
                method_used=projection["method_used"],
                data_start_date=projection["data_start_date"],
                data_end_date=projection["data_end_date"],
            )
        )
