"""Forecasting models.

Represents demand forecasts and their associated metadata for auditability
and traceability. Each forecast run produces per-series results with full
traceability back to inputs, methods, and accuracy metrics.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy import DateTime, Date, ForeignKey, Identity, Index, Integer, Numeric, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ForecastRun(Base):
    """A forecasting run with full traceability metadata.

    Each run produces forecasts for one or more series over a horizon.
    All inputs, methods, and accuracy metrics are recorded for auditability.
    """

    __tablename__ = "forecast_runs"
    __table_args__ = (Index("ix_forecast_runs_tenant_id_id", "tenant_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Location and role this forecast is for (links to scheduler)
    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Forecast horizon (number of periods ahead)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    # Method used: seasonal_naive, holt_winters, auto
    method: Mapped[str] = mapped_column(String(50), nullable=False, default="auto")

    # Data window used for training
    data_start_date: Mapped[Optional[date]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    data_end_date: Mapped[Optional[date]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Backtest results (MAPE, MASE)
    backtest_mape: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 4), nullable=True
    )
    backtest_mase: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 4), nullable=True
    )
    backtest_holdout_days: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    # Overall status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, running, completed, failed

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # When the run finished. The column is `finished_at`, matching the
    # migration that creates this table.
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    results: Mapped[list["ForecastResult"]] = relationship(
        "ForecastResult", back_populates="run", cascade="all, delete-orphan"
    )
    scenarios: Mapped[list["ForecastScenario"]] = relationship(
        "ForecastScenario", back_populates="base_run", cascade="all, delete-orphan"
    )


class ForecastResult(Base):
    """A single forecast result for one series at one horizon step.

    Carries full traceability: the input hash identifies the exact data used,
    and the rule_version identifies the forecasting rule version applied.
    """

    __tablename__ = "forecast_results"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    forecast_run_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Series identifier (e.g., "retail:departments:OPS:employees")
    series_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # Forecast horizon (1 = next day, 2 = next two days, etc.)
    horizon_step: Mapped[int] = mapped_column(Integer, nullable=False)

    # Forecast target date
    forecast_date: Mapped[date] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Predicted value
    predicted_value: Mapped[float] = mapped_column(
        Numeric(14, 4), nullable=False
    )

    # Lower/upper confidence bounds (95% confidence interval)
    lower_bound: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    upper_bound: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 4), nullable=True
    )

    # Input hash for traceability - hash of all input data used
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Rule version used for this forecast
    rule_version: Mapped[str] = mapped_column(String(60), nullable=False)

    # Method actually used (may differ from run-level method if auto-selected)
    method_used: Mapped[str] = mapped_column(String(50), nullable=False)

    # Data window used for this specific forecast
    data_start_date: Mapped[Optional[date]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    data_end_date: Mapped[Optional[date]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    run: Mapped["ForecastRun"] = relationship(
        "ForecastRun", back_populates="results"
    )

    __table_args__ = (
        Index("ix_forecast_results_tenant_id_id", "tenant_id", "id"),
        # Unique constraint: one result per run/series/horizon
        sa.UniqueConstraint(
            "forecast_run_id", "series_key", "horizon_step",
            name="uq_forecast_run_series_horizon",
        ),
    )


class ForecastModelVersion(Base):
    """Records forecasting model versions for traceability.

    Each time the forecasting algorithm or hyperparameters change, a new
    version is recorded. This allows reproducibility and auditing of which
    model version produced which results.
    """

    __tablename__ = "forecast_model_versions"
    __table_args__ = (Index("ix_forecast_model_versions_tenant_id_id", "tenant_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    version: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ForecastScenario(Base):
    """A what-if scenario built on top of a base forecast run.

    Each scenario carries explicit, named assumptions that are always shown
    and never applied silently. The scenario references a base ForecastRun
    and produces a variant forecast with the same metadata structure.
    """

    __tablename__ = "forecast_scenarios"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_run_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Assumptions as JSON array: [{"key": "demand_multiplier", "value": 1.1, "unit": "ratio", "note": "Holiday surge"}, ...]
    assumptions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # --- Versioning (AN-05) ---------------------------------------------- #
    # 1 = the first version of this scenario. Editing a scenario stores a
    # NEW row with version_no + 1 under the same root; the old version stays
    # intact and stays comparable.
    version_no: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    # The lineage root: the id of the first version of this scenario. A
    # freshly created scenario points at itself (set after the first flush).
    root_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("forecast_scenarios.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # created | edited | forked - how this version came into existence.
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="created", server_default="created"
    )
    # For forks only: the exact scenario version whose assumptions were copied.
    forked_from_scenario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("forecast_scenarios.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    base_run: Mapped["ForecastRun"] = relationship(
        "ForecastRun", back_populates="scenarios"
    )
    results: Mapped[list["ForecastScenarioResult"]] = relationship(
        "ForecastScenarioResult", back_populates="scenario", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_forecast_scenarios_tenant_id_id", "tenant_id", "id"),
        sa.UniqueConstraint(
            "root_id", "version_no",
            name="uq_forecast_scenario_root_version",
        ),
    )


class ForecastScenarioResult(Base):
    """A single forecast scenario result for one series at one horizon step.

    Mirrors ForecastResult structure but belongs to a scenario instead of a base run.
    """

    __tablename__ = "forecast_scenario_results"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Series identifier (e.g., "retail:departments:OPS:employees")
    series_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # Forecast horizon (1 = next day, 2 = next two days, etc.)
    horizon_step: Mapped[int] = mapped_column(Integer, nullable=False)

    # Forecast target date
    forecast_date: Mapped[date] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Predicted value (after assumptions applied)
    predicted_value: Mapped[float] = mapped_column(
        Numeric(14, 4), nullable=False
    )

    # Lower/upper confidence bounds (95% confidence interval)
    lower_bound: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    upper_bound: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 4), nullable=True
    )

    # Input hash for traceability - hash of all input data + assumptions used
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Rule version used for this forecast
    rule_version: Mapped[str] = mapped_column(String(60), nullable=False)

    # Method actually used (may differ from run-level method if auto-selected)
    method_used: Mapped[str] = mapped_column(String(50), nullable=False)

    # Data window used for this specific forecast
    data_start_date: Mapped[Optional[date]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    data_end_date: Mapped[Optional[date]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    scenario: Mapped["ForecastScenario"] = relationship(
        "ForecastScenario", back_populates="results"
    )

    __table_args__ = (
        Index("ix_forecast_scenario_results_tenant_id_id", "tenant_id", "id"),
        # Unique constraint: one result per scenario/series/horizon
        sa.UniqueConstraint(
            "scenario_id", "series_key", "horizon_step",
            name="uq_forecast_scenario_series_horizon",
        ),
    )


class CostForecast(Base):
    """A stored, versioned labour cost forecast (AN-04).

    Built from a ForecastRun's demand series multiplied by the hourly rates
    supplied in the request. Every row is traceable to the run, the rates
    and the input hash; every response and export carries the label
    "excludes statutory on-costs" — employer contributions and statutory
    on-costs are NOT included.

    A re-run of the same run id creates a new version (1, 2, 3...); the
    previous versions stay intact for auditability.
    """

    __tablename__ = "forecast_costs"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    forecast_run_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 1 = first forecast of this run; each POST creates the next version.
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Costed window (subset of the run's horizon; defaults to the full run).
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # The hourly rates used, as JSON: {"role title or code": rate, "default": rate}
    hourly_costs: Mapped[str] = mapped_column(Text, nullable=False)

    # Traceability: hash of the run's results + the rates used.
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Always true; kept as an explicit column so the label is queryable.
    excludes_statutory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    rows: Mapped[list["CostForecastRow"]] = relationship(
        "CostForecastRow", back_populates="cost_forecast", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_forecast_costs_tenant_id_id", "tenant_id", "id"),
        sa.UniqueConstraint(
            "forecast_run_id", "version",
            name="uq_forecast_cost_run_version",
        ),
    )


class CostForecastRow(Base):
    """One cost line of a stored cost forecast.

    Aggregates the run's demand for one month × location × role at the
    assumption rate. The statutory label is carried on every row of every
    response and CSV export.
    """

    __tablename__ = "forecast_cost_rows"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    cost_forecast_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_costs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Month bucket, "YYYY-MM", of the demand dates.
    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)

    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    location_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    role_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Forecast demand hours for this month/location/role, and the rate applied.
    hours: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    hourly_cost: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    cost: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)

    # Relationship
    cost_forecast: Mapped["CostForecast"] = relationship(
        "CostForecast", back_populates="rows"
    )

    __table_args__ = (
        Index("ix_forecast_cost_rows_tenant_id_id", "tenant_id", "id"),
        sa.UniqueConstraint(
            "cost_forecast_id", "period", "location_id", "role_id",
            name="uq_forecast_cost_row",
        ),
    )


class ForecastAccuracyRecord(Base):
    """One forecast-vs-actual accuracy record (AN-06).

    Produced by the accuracy sync: for one forecast run, one month
    period, one location and one role, the run's forecast hours for the
    window are compared with the actual hours measured for the same
    dates. The row carries the error metrics (MAPE, MAE, bias), the
    number of day-pairs the metrics were computed from, and a
    confidence status computed from the MAPE against explicit
    thresholds: "ok" (at or under the review threshold), "review"
    (over review, at or under degraded), "degraded" (over degraded). A
    row with a MAPE that cannot be computed (every pair's actual is
    zero) is flagged "review" — an accuracy that cannot be verified is
    not an accuracy that passed.

    MAPE is a fraction (0.10 == 10 %). Bias is forecast minus actual:
    positive means the forecast over-predicted demand.

    Re-running the sync for a window replaces the rows it computes
    (delete-then-insert per (run, period, location, role) key), so a
    window re-measured never stacks duplicates — the unique constraint
    makes that a database guarantee as well.
    """

    __tablename__ = "forecast_accuracy_records"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    forecast_run_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The model version (rule_version) and the method that produced the
    # forecast values being judged.
    model_version: Mapped[str] = mapped_column(String(60), nullable=False)
    method_used: Mapped[str] = mapped_column(String(50), nullable=False)

    # Month bucket, "YYYY-MM", of the comparison dates.
    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)

    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Totals for this run/period/location/role, in hours.
    forecast_hours: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    actual_hours: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)

    # Error metrics over the day-pairs of the period.
    mape: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    mae: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    bias: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # ok | review | degraded — computed from MAPE against the thresholds
    # in force at sync time; the list endpoint recomputes it per request.
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # When the comparison was made.
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_forecast_accuracy_records_tenant_id_id", "tenant_id", "id"),
        sa.UniqueConstraint(
            "forecast_run_id", "period", "location_id", "role_id",
            name="uq_forecast_accuracy_row",
        ),
    )
