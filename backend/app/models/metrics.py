"""Pydantic models for evaluation metrics and dimensional analysis."""

from pydantic import BaseModel, Field


class OverallMetrics(BaseModel):
    """Overall benchmark performance metrics across an evaluation period."""

    total_count: int = Field(
        description="Total number of evaluated half-hour intervals"
    )
    valid_count: int = Field(
        description="Number of intervals with valid actual and forecast values"
    )
    missing_count: int = Field(
        description="Number of intervals lacking valid forecast or actual values"
    )
    mae: float | None = Field(default=None, description="Mean Absolute Error in MW")
    rmse: float | None = Field(default=None, description="Root Mean Square Error in MW")
    bias: float | None = Field(
        default=None, description="Mean Error (actual - forecast) in MW"
    )
    nmae_pct: float | None = Field(
        default=None, description="Normalised MAE as percentage of mean actual (%)"
    )
    p50: float | None = Field(
        default=None, description="50th percentile (median) of absolute error in MW"
    )
    p90: float | None = Field(
        default=None, description="90th percentile of absolute error in MW"
    )
    p95: float | None = Field(
        default=None, description="95th percentile of absolute error in MW"
    )
    mean_actual: float | None = Field(
        default=None,
        description=(
            "Mean actual average power in MW over a half hour (not energy in MWh)"
        ),
    )
    mean_forecast: float | None = Field(
        default=None,
        description=(
            "Mean forecast average power in MW over a half hour (not energy in MWh)"
        ),
    )


class HourlyMetrics(BaseModel):
    """Forecast performance metrics aggregated by hour of the day (UK local)."""

    hour: int = Field(ge=0, le=23, description="Hour of day (0-23) in UK local time")
    total_count: int = Field(
        description="Total half-hours evaluated in this hour bucket"
    )
    valid_count: int = Field(description="Number of valid forecast-actual pairs")
    missing_count: int = Field(description="Number of missing intervals in this hour")
    mae: float | None = Field(default=None, description="Mean Absolute Error in MW")
    rmse: float | None = Field(default=None, description="Root Mean Square Error in MW")
    bias: float | None = Field(default=None, description="Mean Error in MW")
    p50: float | None = Field(
        default=None, description="50th percentile of absolute error in MW"
    )
    p90: float | None = Field(
        default=None, description="90th percentile of absolute error in MW"
    )
    p95: float | None = Field(
        default=None, description="95th percentile of absolute error in MW"
    )
    mean_actual: float | None = Field(
        default=None,
        description=(
            "Mean actual average power in MW over a half hour (not energy in MWh)"
        ),
    )
    mean_forecast: float | None = Field(
        default=None,
        description=(
            "Mean forecast average power in MW over a half hour (not energy in MWh)"
        ),
    )


class HorizonMetrics(BaseModel):
    """Forecast performance metrics grouped by forecast horizon lead time."""

    bucket: str = Field(
        description="Label identifying the horizon interval (e.g., '0-6h')"
    )
    min_horizon_hours: float | None = Field(
        default=None,
        description="Lower bound of forecast horizon in hours (null if unbounded)",
    )
    max_horizon_hours: float | None = Field(
        default=None,
        description="Upper bound of forecast horizon in hours (null if unbounded)",
    )
    total_count: int = Field(description="Total comparisons evaluated in this bucket")
    valid_count: int = Field(description="Number of valid pairs with complete values")
    missing_count: int = Field(
        description="Number of missing forecasts or actuals in this bucket"
    )
    mae: float | None = Field(default=None, description="Mean Absolute Error in MW")
    rmse: float | None = Field(default=None, description="Root Mean Square Error in MW")
    bias: float | None = Field(default=None, description="Mean Error in MW")
    p50: float | None = Field(
        default=None, description="50th percentile of absolute error in MW"
    )
    p90: float | None = Field(
        default=None, description="90th percentile of absolute error in MW"
    )
    p95: float | None = Field(
        default=None, description="95th percentile of absolute error in MW"
    )
