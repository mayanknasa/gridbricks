"""API v1 route handlers for forecasts, actuals comparison, and metrics."""

from datetime import date, datetime, time
from typing import Annotated, Final

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings
from app.core.repository import DataRepository
from app.models.api import (
    CompareItem,
    CompareResponse,
    ForecastItem,
    ForecastResponse,
    HorizonMetricsResponse,
    HourlyMetricsResponse,
    OverallMetricsResponse,
)
from app.models.health import HealthStatus
from app.services.forecast_selection import select_latest_forecasts
from app.services.health import get_health_status
from app.services.metrics import (
    calculate_horizon_metrics,
    calculate_hourly_metrics,
    calculate_overall_metrics,
    join_forecasts_with_actuals,
)

DATA_MIN_DATE: Final[date] = date(2026, 1, 1)
DATA_MAX_DATE: Final[date] = date(2026, 2, 2)

router: APIRouter = APIRouter()


def parse_and_validate_cutoff(cutoff_str: str) -> time:
    """Parse and validate decision cutoff time string.

    Args:
        cutoff_str: Cutoff time formatted as 'HH:MM'.

    Returns:
        Validated time object.

    Raises:
        HTTPException: 400 Bad Request if format or values are invalid.
    """
    if not isinstance(cutoff_str, str) or len(cutoff_str) != 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid cutoff time '{cutoff_str}'. "
                "Expected format 'HH:MM' (00:00 to 23:59)."
            ),
        )

    try:
        parsed_dt: datetime = datetime.strptime(cutoff_str, "%H:%M")
        return parsed_dt.time()
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid cutoff time '{cutoff_str}'. "
                "Hours must be between 00 and 23 and minutes between 00 and 59."
            ),
        ) from err


def validate_date_in_range(d: date, field_name: str = "date") -> None:
    """Validate that a date lies within available January 2026 dataset bounds.

    Args:
        d: Date to validate.
        field_name: Parameter name for descriptive error message.

    Raises:
        HTTPException: 400 Bad Request if date is outside available bounds.
    """
    if d < DATA_MIN_DATE or d > DATA_MAX_DATE:
        min_iso = DATA_MIN_DATE.isoformat()
        max_iso = DATA_MAX_DATE.isoformat()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{field_name} ({d.isoformat()}) is outside available January 2026 "
                f"data range ({min_iso} to {max_iso})."
            ),
        )


def validate_date_range(start: date, end: date) -> None:
    """Validate start and end delivery dates.

    Args:
        start: Start delivery date.
        end: End delivery date.

    Raises:
        HTTPException: 400 Bad Request if either date is out of range or start > end.
    """
    validate_date_in_range(start, "start")
    validate_date_in_range(end, "end")
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"start date ({start.isoformat()}) cannot be after end date "
                f"({end.isoformat()})."
            ),
        )


@router.get("/health", response_model=HealthStatus, summary="API v1 Health Check")
def health_check() -> HealthStatus:
    """Return operational health status and timestamp."""
    return get_health_status(version=settings.app_version)


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Selected Day-Ahead Forecast per Half Hour",
)
def get_selected_forecast(
    delivery_date: Annotated[
        date,
        Query(description="Target delivery date (YYYY-MM-DD)"),
    ] = date(2026, 1, 2),
    cutoff: Annotated[
        str,
        Query(description="Decision cutoff time in UK local time (HH:MM)"),
    ] = "09:00",
) -> ForecastResponse:
    """Return selected latest published wind forecast per target half hour.

    Generation values represent average power in MW over a half hour, not energy in MWh.
    Applies the specified cutoff time on Day D-1 in UK local time and selects
    the forecast with the latest publishTime prior to cutoff. Missing periods
    are included with is_missing=True and null generation.
    """
    validate_date_in_range(delivery_date, "delivery_date")
    cutoff_time: time = parse_and_validate_cutoff(cutoff)

    repo: DataRepository = DataRepository.get_instance()
    forecasts_df: pd.DataFrame = repo.get_forecasts(
        start_date=delivery_date, end_date=delivery_date
    )

    selected_df: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=delivery_date,
        end_date=delivery_date,
        cutoff_time=cutoff_time,
    )

    items: list[ForecastItem] = []
    for _, row in selected_df.iterrows():
        pub_val = row["publishTime"]
        pub_time: datetime | None = (
            None if pd.isna(pub_val) else pub_val.to_pydatetime()
        )
        gen_val = row["generation"]
        gen: float | None = None if pd.isna(gen_val) else float(gen_val)

        items.append(
            ForecastItem(
                startTime=row["startTime"].to_pydatetime(),
                publishTime=pub_time,
                generation=gen,
                isMissing=bool(row["is_missing"]),
                isDerived=bool(row.get("is_derived", False)),
                forecastType=str(row.get("forecast_type", "published")),
            )
        )

    return ForecastResponse(
        deliveryDate=delivery_date,
        cutoff=cutoff,
        totalPeriods=len(items),
        data=items,
    )


@router.get(
    "/compare",
    response_model=CompareResponse,
    summary="Compare Selected Forecasts Against Actual Outturn",
)
def get_compare_forecast_and_actuals(
    start: Annotated[
        date,
        Query(description="Start delivery date (YYYY-MM-DD)"),
    ] = date(2026, 1, 2),
    end: Annotated[
        date,
        Query(description="End delivery date (YYYY-MM-DD)"),
    ] = date(2026, 2, 1),
    cutoff: Annotated[
        str,
        Query(description="Decision cutoff time in UK local time (HH:MM)"),
    ] = "09:00",
) -> CompareResponse:
    """Return half-hourly comparison of selected forecast, actuals, and error.

    Generation values represent average power in MW over a half hour, not energy in MWh.
    Error formula: error = actual - forecast (MW).
    """
    validate_date_range(start, end)
    cutoff_time: time = parse_and_validate_cutoff(cutoff)

    repo: DataRepository = DataRepository.get_instance()
    forecasts_df: pd.DataFrame = repo.get_forecasts(start_date=start, end_date=end)
    actuals_df: pd.DataFrame = repo.get_actuals(start_date=start, end_date=end)

    selected_df: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=start,
        end_date=end,
        cutoff_time=cutoff_time,
    )
    joined_df: pd.DataFrame = join_forecasts_with_actuals(
        selected_forecasts_df=selected_df,
        actuals_df=actuals_df,
    )

    items: list[CompareItem] = []
    for _, row in joined_df.iterrows():
        pub_val = row["publishTime"]
        pub_time: datetime | None = (
            None if pd.isna(pub_val) else pub_val.to_pydatetime()
        )

        fc_val = row["forecast_generation"]
        fc_gen: float | None = None if pd.isna(fc_val) else float(fc_val)

        act_val = row["actual_generation"]
        act_gen: float | None = None if pd.isna(act_val) else float(act_val)

        err_val = row["error"]
        err: float | None = None if pd.isna(err_val) else float(err_val)

        abs_err_val = row["abs_error"]
        abs_err: float | None = None if pd.isna(abs_err_val) else float(abs_err_val)

        is_missing: bool = err is None
        is_derived_val: bool = bool(row.get("is_derived", False))
        forecast_type_val: str = str(
            row.get("forecast_type", "missing" if is_missing else "published")
        )

        items.append(
            CompareItem(
                startTime=row["startTime"].to_pydatetime(),
                publishTime=pub_time,
                forecastGeneration=fc_gen,
                actualGeneration=act_gen,
                error=err,
                absError=abs_err,
                isMissing=is_missing,
                isDerived=is_derived_val,
                forecastType=forecast_type_val,
            )
        )

    return CompareResponse(
        startDate=start,
        endDate=end,
        cutoff=cutoff,
        totalPeriods=len(items),
        data=items,
    )


@router.get(
    "/metrics",
    response_model=OverallMetricsResponse,
    summary="Overall Benchmark Performance Metrics",
)
def get_overall_metrics(
    start: Annotated[
        date,
        Query(description="Start delivery date (YYYY-MM-DD)"),
    ] = date(2026, 1, 2),
    end: Annotated[
        date,
        Query(description="End delivery date (YYYY-MM-DD)"),
    ] = date(2026, 2, 1),
    cutoff: Annotated[
        str,
        Query(description="Decision cutoff time in UK local time (HH:MM)"),
    ] = "09:00",
) -> OverallMetricsResponse:
    """Return overall benchmark performance metrics across delivery range.

    Generation values represent average power in MW over a half hour, not energy in MWh.
    """
    validate_date_range(start, end)
    cutoff_time: time = parse_and_validate_cutoff(cutoff)

    repo: DataRepository = DataRepository.get_instance()
    forecasts_df: pd.DataFrame = repo.get_forecasts(start_date=start, end_date=end)
    actuals_df: pd.DataFrame = repo.get_actuals(start_date=start, end_date=end)

    selected_df: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=start,
        end_date=end,
        cutoff_time=cutoff_time,
    )
    joined_df: pd.DataFrame = join_forecasts_with_actuals(
        selected_forecasts_df=selected_df,
        actuals_df=actuals_df,
    )
    metrics = calculate_overall_metrics(joined_df)

    return OverallMetricsResponse(
        startDate=start,
        endDate=end,
        cutoff=cutoff,
        metrics=metrics,
    )


@router.get(
    "/metrics/by_hour",
    response_model=HourlyMetricsResponse,
    summary="Diurnal Error Breakdown by Hour of Day",
)
def get_metrics_by_hour(
    start: Annotated[
        date,
        Query(description="Start delivery date (YYYY-MM-DD)"),
    ] = date(2026, 1, 2),
    end: Annotated[
        date,
        Query(description="End delivery date (YYYY-MM-DD)"),
    ] = date(2026, 2, 1),
    cutoff: Annotated[
        str,
        Query(description="Decision cutoff time in UK local time (HH:MM)"),
    ] = "09:00",
) -> HourlyMetricsResponse:
    """Return 24-hour error profile aggregated by hour of the day in UK local time.

    Generation values represent average power in MW over a half hour, not energy in MWh.
    """
    validate_date_range(start, end)
    cutoff_time: time = parse_and_validate_cutoff(cutoff)

    repo: DataRepository = DataRepository.get_instance()
    forecasts_df: pd.DataFrame = repo.get_forecasts(start_date=start, end_date=end)
    actuals_df: pd.DataFrame = repo.get_actuals(start_date=start, end_date=end)

    selected_df: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=start,
        end_date=end,
        cutoff_time=cutoff_time,
    )
    joined_df: pd.DataFrame = join_forecasts_with_actuals(
        selected_forecasts_df=selected_df,
        actuals_df=actuals_df,
    )
    hourly_data = calculate_hourly_metrics(joined_df)

    return HourlyMetricsResponse(
        startDate=start,
        endDate=end,
        cutoff=cutoff,
        data=hourly_data,
    )


@router.get(
    "/metrics/by_horizon",
    response_model=HorizonMetricsResponse,
    summary="Error Metrics by Forecast Horizon Lead Time",
)
def get_metrics_by_horizon(
    start: Annotated[
        date,
        Query(description="Start delivery date (YYYY-MM-DD)"),
    ] = date(2026, 1, 2),
    end: Annotated[
        date,
        Query(description="End delivery date (YYYY-MM-DD)"),
    ] = date(2026, 2, 1),
) -> HorizonMetricsResponse:
    """Return error metrics bucketed by forecast horizon lead time.

    Generation values represent average power in MW over a half hour, not energy in MWh.
    Evaluates error across all published forecasts for delivery settlement
    periods within the specified delivery range.
    """
    validate_date_range(start, end)

    repo: DataRepository = DataRepository.get_instance()
    forecasts_df: pd.DataFrame = repo.get_forecasts(start_date=start, end_date=end)
    actuals_df: pd.DataFrame = repo.get_actuals(start_date=start, end_date=end)

    horizon_data = calculate_horizon_metrics(
        all_forecasts_df=forecasts_df,
        actuals_df=actuals_df,
    )

    return HorizonMetricsResponse(
        startDate=start,
        endDate=end,
        data=horizon_data,
    )
