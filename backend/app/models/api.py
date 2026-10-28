"""API request and response Pydantic models for v1 endpoints."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.metrics import HorizonMetrics, HourlyMetrics, OverallMetrics


class ForecastItem(BaseModel):
    """Half-hourly forecast record for a target settlement period."""

    model_config = ConfigDict(populate_by_name=True)

    start_time: datetime = Field(
        alias="startTime", description="Target settlement period start time (UTC)"
    )
    publish_time: datetime | None = Field(
        default=None,
        alias="publishTime",
        description="UTC timestamp of the selected forecast publication run",
    )
    generation: float | None = Field(
        default=None,
        description=(
            "Forecasted average power in MW over the half hour (not energy in MWh)"
        ),
    )
    is_missing: bool = Field(
        alias="isMissing",
        description="True if no valid forecast was published prior to cutoff",
    )
    is_derived: bool = Field(
        default=False,
        alias="isDerived",
        description="True if forecast was derived via hourly step-hold from :00",
    )
    forecast_type: str = Field(
        default="published",
        alias="forecastType",
        description="Forecast source type: 'published', 'step_hold', or 'missing'",
    )


class ForecastResponse(BaseModel):
    """Response payload for day-ahead forecast selection."""

    model_config = ConfigDict(populate_by_name=True)

    delivery_date: date = Field(
        alias="deliveryDate", description="Target delivery date"
    )
    cutoff: str = Field(description="Decision cutoff time in UK local time (HH:MM)")
    total_periods: int = Field(
        alias="totalPeriods", description="Total half-hour settlement periods"
    )
    data: list[ForecastItem] = Field(
        description="List of selected forecasts for each half hour"
    )


class CompareItem(BaseModel):
    """Comparison of forecast vs actual outturn for a target half hour."""

    model_config = ConfigDict(populate_by_name=True)

    start_time: datetime = Field(
        alias="startTime", description="Target settlement period start time (UTC)"
    )
    publish_time: datetime | None = Field(
        default=None,
        alias="publishTime",
        description="UTC publication timestamp of selected forecast",
    )
    forecast_generation: float | None = Field(
        default=None,
        alias="forecastGeneration",
        description=(
            "Forecasted average power in MW over the half hour (not energy in MWh)"
        ),
    )
    actual_generation: float | None = Field(
        default=None,
        alias="actualGeneration",
        description=(
            "Actual outturn average power in MW over the half hour (not energy in MWh)"
        ),
    )
    error: float | None = Field(
        default=None, description="Forecast error in MW (actual - forecast)"
    )
    abs_error: float | None = Field(
        default=None, alias="absError", description="Absolute error in MW"
    )
    is_missing: bool = Field(
        alias="isMissing",
        description="True if either forecast or actual outturn was missing",
    )
    is_derived: bool = Field(
        default=False,
        alias="isDerived",
        description="True if forecast was derived via hourly step-hold from :00",
    )
    forecast_type: str = Field(
        default="published",
        alias="forecastType",
        description="Forecast source type: 'published', 'step_hold', or 'missing'",
    )


class CompareResponse(BaseModel):
    """Response payload for forecast vs actual outturn comparison."""

    model_config = ConfigDict(populate_by_name=True)

    start_date: date = Field(
        alias="startDate", description="Start delivery date (inclusive)"
    )
    end_date: date = Field(alias="endDate", description="End delivery date (inclusive)")
    cutoff: str = Field(description="Decision cutoff time in UK local time (HH:MM)")
    total_periods: int = Field(
        alias="totalPeriods", description="Total half-hour intervals evaluated"
    )
    data: list[CompareItem] = Field(
        description="List of comparison records per half hour"
    )


class OverallMetricsResponse(BaseModel):
    """Response payload for overall evaluation metrics."""

    model_config = ConfigDict(populate_by_name=True)

    start_date: date = Field(
        alias="startDate", description="Start delivery date (inclusive)"
    )
    end_date: date = Field(alias="endDate", description="End delivery date (inclusive)")
    cutoff: str = Field(description="Decision cutoff time in UK local time (HH:MM)")
    metrics: OverallMetrics = Field(description="Overall benchmark performance metrics")


class HourlyMetricsResponse(BaseModel):
    """Response payload for diurnal error breakdown by hour of day."""

    model_config = ConfigDict(populate_by_name=True)

    start_date: date = Field(
        alias="startDate", description="Start delivery date (inclusive)"
    )
    end_date: date = Field(alias="endDate", description="End delivery date (inclusive)")
    cutoff: str = Field(description="Decision cutoff time in UK local time (HH:MM)")
    data: list[HourlyMetrics] = Field(
        description="24 hourly metric entries (0-23 UK local time)"
    )


class HorizonMetricsResponse(BaseModel):
    """Response payload for error breakdown across forecast horizon buckets."""

    model_config = ConfigDict(populate_by_name=True)

    start_date: date = Field(
        alias="startDate", description="Start delivery date (inclusive)"
    )
    end_date: date = Field(alias="endDate", description="End delivery date (inclusive)")
    data: list[HorizonMetrics] = Field(
        description="Performance metrics bucketed by lead time horizon"
    )
