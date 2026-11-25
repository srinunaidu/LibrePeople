"""Forecasting API schemas.

Defines Pydantic models for forecast request/response serialization.
"""
from __future__ import annotations

import json

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ForecastDataPoint(BaseModel):
    """A single data point in a time series."""
    date: date
    value: float


class ForecastCreate(BaseModel):
    """Request to create a forecast run."""
    name: str | None = None
    description: str | None = None
    series_data: list[ForecastDataPoint]
    horizon_days: int = 30
    method: str | None = "auto"  # "seasonal_naive", "holt_winters", "auto"
    seasonality: int = 7
    series_selector: str | None = "default"
    location_id: int | None = None
    role_id: int | None = None


class ForecastResultOut(BaseModel):
    """A single forecast result."""
    horizon_step: int
    forecast_date: date
    predicted_value: float
    lower_bound: float | None = None
    upper_bound: float | None = None
    method_used: str | None = None
    input_hash: str | None = None
    rule_version: str | None = None
    data_start_date: date | None = None
    data_end_date: date | None = None
    series_key: str | None = None

    class Config:
        from_attributes = True


class ForecastRunOut(BaseModel):
    """A forecast run with its results."""
    id: int
    name: str
    description: str | None = None
    status: str
    horizon_days: int
    method: str
    data_start_date: date | None = None
    data_end_date: date | None = None
    backtest_mape: float | None = None
    backtest_mase: float | None = None
    backtest_holdout_days: int | None = None
    created_at: datetime
    finished_at: datetime | None = None
    results: list[ForecastResultOut] = []
    location_id: int | None = None
    role_id: int | None = None

    class Config:
        from_attributes = True


# --- Scenario schemas ---

class ScenarioAssumption(BaseModel):
    """A single assumption in a scenario."""
    key: str = Field(
        ...,
        description=(
            "Assumption type: demand_multiplier, demand_delta, headcount_cap, "
            "seasonality_override, method_override, attrition_rate, hire_rate, "
            "leave_rate, wage_growth_pct. An unknown key is a 422 naming the key."
        ),
    )
    value: float | str = Field(..., description="Assumption value (ratio for multiplier, absolute for delta/cap, string for method_override)")
    unit: str = Field(..., description="Unit: ratio, absolute, days, method")
    note: str | None = Field(None, description="Human-readable explanation of this assumption")


class ScenarioCreate(BaseModel):
    """Request to create a scenario from a base forecast run."""
    base_run_id: int = Field(..., description="The forecast run this scenario is based on")
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    assumptions: list[ScenarioAssumption] = Field(..., min_length=1, description="Named assumptions to apply")


class ScenarioAssumptionOut(ScenarioAssumption):
    """Assumption as returned in responses."""
    pass


class ScenarioResultOut(BaseModel):
    """A single scenario forecast result."""
    horizon_step: int
    forecast_date: date
    predicted_value: float
    lower_bound: float | None = None
    upper_bound: float | None = None
    method_used: str | None = None
    input_hash: str | None = None
    rule_version: str | None = None
    data_start_date: date | None = None
    data_end_date: date | None = None
    series_key: str | None = None

    class Config:
        from_attributes = True


class ScenarioOut(BaseModel):
    """A forecast scenario with its results.

    ``version_no``/``root_id``/``source`` carry the AN-05 versioning: an
    edit creates a NEW scenario row under the same ``root_id`` with the
    next ``version_no``; the old version stays intact and comparable.
    """
    id: int
    name: str
    description: str | None = None
    base_run_id: int
    assumptions: list[ScenarioAssumptionOut]
    created_at: datetime
    created_by: int | None = None
    # AN-05 versioning
    version_no: int = 1
    root_id: int | None = None
    source: str = "created"
    forked_from_scenario_id: int | None = None
    results: list[ScenarioResultOut] = []

    class Config:
        from_attributes = True

    @field_validator("assumptions", mode="before", check_fields=False)
    @classmethod
    def _parse_assumptions_json(cls, value):
        """The ORM column stores the assumption list as a JSON string.

        A scenario response must carry the list itself — returning the
        raw string would make every scenario payload unreadable. (The
        security matrix only ever probed unknown ids, so this never
        surfaced until the AN-05 suite called a real endpoint.)
        """
        if isinstance(value, str):
            return json.loads(value or "[]")
        return value


# --- Scenario builder: edit, fork, versions (AN-05) -------------------------

class ScenarioEditCreate(BaseModel):
    """Request to edit a scenario. Editing stores a NEW version; the
    previous versions stay intact and comparable."""
    assumptions: list[ScenarioAssumption] = Field(
        ..., min_length=1, description="The full, edited assumption set"
    )
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None


class ScenarioForkCreate(BaseModel):
    """Request to fork a scenario version into a new independent lineage."""
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None


class ScenarioVersionSummaryOut(BaseModel):
    """One version of a scenario lineage (results on the scenario itself)."""
    id: int
    name: str
    description: str | None = None
    base_run_id: int
    assumptions: list[ScenarioAssumptionOut]
    version_no: int = 1
    root_id: int | None = None
    source: str = "created"
    forked_from_scenario_id: int | None = None
    created_at: datetime
    created_by: int | None = None
    results: list[ScenarioResultOut] = []

    class Config:
        from_attributes = True

    @field_validator("assumptions", mode="before", check_fields=False)
    @classmethod
    def _parse_assumptions_json(cls, value):
        """Same as ScenarioOut: the ORM column stores JSON as a string."""
        if isinstance(value, str):
            return json.loads(value or "[]")
        return value


class ScenarioVersionList(BaseModel):
    """All versions of a scenario's lineage, oldest first."""
    items: list[ScenarioVersionSummaryOut]


class PaginatedScenarios(BaseModel):
    """Paginated list of scenarios."""
    items: list[ScenarioOut]
    total: int
    page: int
    page_size: int


# --- Comparison schemas ---

class ComparisonPeriod(BaseModel):
    """A single period in a scenario comparison."""
    horizon_step: int
    forecast_date: date
    base_value: float | None = None
    scenario_values: dict[int, float]  # scenario_id -> predicted_value
    deltas: dict[int, float]  # scenario_id -> delta from first scenario
    assumptions: dict[int, list[ScenarioAssumptionOut]]  # scenario_id -> assumptions


class ScenarioComparisonRequest(BaseModel):
    """Request to compare scenarios — any mix of scenarios and versions."""
    scenario_ids: list[int] = Field(..., min_length=2, description="IDs of scenarios to compare (each id may be any version)")
    hourly_costs: dict[str, float] | None = Field(
        None,
        description=(
            "Optional explicit hourly rates for a cost projection per "
            "participant. Must include a 'default' rate (or be exactly one "
            "rate). Costs appear ONLY when the caller supplies them; each "
            "row is labelled 'excludes statutory on-costs'."
        ),
    )


class ScenarioCostRowOut(BaseModel):
    """One cost line of a participant's cost projection: hours x rate."""
    period: str = Field(..., description="Month bucket, YYYY-MM")
    hours: float
    hourly_cost: float
    cost: float
    cost_basis: str = "excludes statutory on-costs"


class ScenarioCostProjectionOut(BaseModel):
    """A participant's explicit cost projection of its projected demand."""
    scenario_id: int
    hourly_costs: dict[str, float]
    wage_growth_pct: float
    rows: list[ScenarioCostRowOut]
    total_hours: float
    total_cost: float
    total_cost_delta: float | None = None
    label: str = "excludes statutory on-costs"
    cost_basis: str = "excludes statutory on-costs"


class ScenarioComparison(BaseModel):
    """Side-by-side comparison of scenarios and versions.

    Every participant's assumptions sit next to the numbers; ``costs`` is
    present (keyed by participant scenario id) only when the caller
    supplied explicit hourly rates.
    """
    scenarios: list[ScenarioOut]
    comparison: list[ComparisonPeriod]
    costs: dict[int, ScenarioCostProjectionOut] | None = None


# --- Cost forecast schemas (AN-04) ---

class CostForecastCreate(BaseModel):
    """Request to cost a forecast run. Rates are explicit assumptions."""
    hourly_costs: dict[str, float] = Field(
        ...,
        description=(
            "Hourly rate per role title or role code (case-insensitive), "
            "with a 'default' catch-all. A demand group with no matching "
            "rate and no default is a 422 — rates are never implicit."
        ),
    )
    start_date: date | None = Field(None, description="Cost only results from this date (inclusive)")
    end_date: date | None = Field(None, description="Cost only results up to this date (inclusive)")


class CostForecastRowOut(BaseModel):
    """One cost line: month × location × role."""
    period: str = Field(..., description="Month bucket, YYYY-MM")
    location_id: int | None = None
    location_code: str | None = None
    role_id: int | None = None
    role: str | None = None
    role_code: str | None = None
    hours: float
    hourly_cost: float
    cost: float


class CostForecastVersionSummary(BaseModel):
    """Stored cost forecast version metadata (rows omitted)."""
    id: int
    forecast_run_id: int
    version: int
    label: str = "excludes statutory on-costs"
    cost_basis: str = "excludes statutory on-costs"
    hourly_costs: dict[str, float]
    input_hash: str
    start_date: date | None = None
    end_date: date | None = None
    periods: int
    total_hours: float
    total_cost: float
    created_at: datetime


class CostForecastVersionSummaryList(BaseModel):
    """All stored versions of a run's cost forecast, newest first."""
    items: list[CostForecastVersionSummary]


class CostForecastOut(CostForecastVersionSummary):
    """A stored cost forecast with its full rows."""
    message: str | None = None
    location_id: int | None = None
    location_code: str | None = None
    role_id: int | None = None
    role: str | None = None
    role_code: str | None = None
    rows: list[CostForecastRowOut] = []


# --- Accuracy schemas (AN-06) ---

class ForecastAccuracySyncRequest(BaseModel):
    """Request to compare a window's forecasts with its actuals.

    The thresholds are explicit: ``review_threshold`` is the MAPE at or
    under which a row is ``ok``; ``degraded_threshold`` is the MAPE at
    or under which it is ``review``; over it, ``degraded``. MAPE is a
    fraction (0.10 == 10 %).
    """
    start_date: date
    end_date: date
    location_id: int | None = None
    role_id: int | None = None
    run_id: int | None = None
    review_threshold: float = Field(0.10, ge=0.0, le=1.0)
    degraded_threshold: float = Field(0.25, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _thresholds_ordered(self) -> "ForecastAccuracySyncRequest":
        if self.degraded_threshold < self.review_threshold:
            raise ValueError(
                "degraded_threshold must be at or above review_threshold"
            )
        return self


class ForecastAccuracyRecordOut(BaseModel):
    """One forecast-vs-actual accuracy row.

    ``status`` is the confidence indicator, recomputed for every read
    from the row's stored MAPE against the thresholds of the request.
    """
    id: int
    forecast_run_id: int
    model_version: str
    method_used: str
    period: str
    location_id: int | None = None
    role_id: int | None = None
    forecast_hours: float
    actual_hours: float
    mape: float | None = None
    mae: float
    bias: float
    sample_size: int
    status: str
    measured_at: datetime | None = None

    # "model_version" is a business term (the forecasting model version),
    # not a pydantic namespace; silence the protected-prefix warning.
    model_config = {"protected_namespaces": ()}


class ForecastAccuracySyncResult(BaseModel):
    """The result of one accuracy sync run."""
    start_date: str
    end_date: str
    review_threshold: float
    degraded_threshold: float
    replaced: int
    records: list[ForecastAccuracyRecordOut]


class PaginatedForecastAccuracy(BaseModel):
    """Paginated accuracy history, newest first."""
    items: list[ForecastAccuracyRecordOut]
    total: int
    page: int
    page_size: int
