"""Forecast selection service module.

Filters wind generation forecasts to identify the latest published forecast
at or prior to a day-ahead decision cutoff time for each target half hour.
"""

from datetime import UTC, date, datetime, time, timedelta
from typing import Final
from zoneinfo import ZoneInfo

import pandas as pd

UK_TZ: Final[ZoneInfo] = ZoneInfo("Europe/London")


def calculate_cutoff_timestamp(
    delivery_date: date,
    cutoff_time: time = time(9, 0),
) -> datetime:
    """Calculate the UTC cutoff timestamp on the day prior to delivery (Day D-1).

    Interprets cutoff_time in UK local time (handling GMT/BST dynamically)
    and converts to timezone-aware UTC.

    Args:
        delivery_date: Target delivery date (Day D).
        cutoff_time: Time of day in UK local time (default: 09:00).

    Returns:
        Timezone-aware UTC datetime for the decision cutoff.
    """
    decision_date: date = delivery_date - timedelta(days=1)
    local_cutoff: datetime = datetime.combine(decision_date, cutoff_time, tzinfo=UK_TZ)
    return local_cutoff.astimezone(UTC)


def generate_target_half_hours_grid(
    start_date: date,
    end_date: date,
    cutoff_time: time = time(9, 0),
) -> pd.DataFrame:
    """Generate the complete half-hourly target grid for a delivery date range.

    Produces exactly 48 half-hour settlement periods per calendar day,
    annotated with the applicable Day D-1 UTC cutoff timestamp.

    Note:
        Assumes a 48 period day and is valid for January only (does not
        account for daylight saving clock change 46- or 50-period days).

    Args:
        start_date: First delivery date (inclusive).
        end_date: Final delivery date (inclusive).
        cutoff_time: Time of day in UK local time on Day D-1.

    Returns:
        DataFrame with columns ['startTime', 'deliveryDate', 'cutoffTime'].
    """
    rows: list[dict[str, datetime | date]] = []
    current_date: date = start_date

    while current_date <= end_date:
        cutoff_utc: datetime = calculate_cutoff_timestamp(
            delivery_date=current_date,
            cutoff_time=cutoff_time,
        )
        local_day_start: datetime = datetime.combine(
            current_date, time(0, 0), tzinfo=UK_TZ
        )
        utc_day_start: datetime = local_day_start.astimezone(UTC)
        for period in range(48):
            target_start: datetime = utc_day_start + timedelta(minutes=period * 30)
            rows.append(
                {
                    "startTime": target_start,
                    "deliveryDate": current_date,
                    "cutoffTime": cutoff_utc,
                }
            )
        current_date += timedelta(days=1)

    grid_df = pd.DataFrame(rows)
    grid_df["startTime"] = pd.to_datetime(grid_df["startTime"], utc=True)
    grid_df["cutoffTime"] = pd.to_datetime(grid_df["cutoffTime"], utc=True)
    return grid_df


def select_latest_forecasts(
    forecasts_df: pd.DataFrame,
    start_date: date,
    end_date: date,
    cutoff_time: time = time(9, 0),
    step_hold: bool = True,
) -> pd.DataFrame:
    """Select the latest published forecast at or before cutoff for each half-hour.

    For every target half-hour across the delivery date range, selects the
    forecast record matching startTime with the maximum publishTime <= cutoff.
    When step_hold is True (default), intermediate :30 settlement periods with
    no direct forecast inherit the preceding :00 forecast of that clock hour
    with is_derived=True and forecast_type='step_hold'.
    Missing intervals are preserved with a null forecast, is_missing=True,
    is_derived=False, and forecast_type='missing'.

    Args:
        forecasts_df: DataFrame containing at least ['startTime', 'publishTime',
            'generation'].
        start_date: Start delivery date (inclusive).
        end_date: End delivery date (inclusive).
        cutoff_time: Cutoff time in UK local time on Day D-1 (default: 09:00).
        step_hold: If True (default), carry forward the preceding :00 forecast
            to the :30 interval within the same hour block if :30 is missing.

    Returns:
        DataFrame containing columns:
          - startTime (datetime64[us, UTC]): target delivery start time
          - publishTime (datetime64[us, UTC]): timestamp of selected forecast run
          - generation (float): forecasted average power in MW over the half hour
            (or NaN), not energy in MWh
          - is_missing (bool): True if no forecast (direct or derived) is available
          - is_derived (bool): True if derived via hourly step-hold from :00
          - forecast_type (str): 'published', 'step_hold', or 'missing'
    """
    grid_df: pd.DataFrame = generate_target_half_hours_grid(
        start_date=start_date,
        end_date=end_date,
        cutoff_time=cutoff_time,
    )

    if forecasts_df.empty:
        grid_df["publishTime"] = pd.NaT
        grid_df["generation"] = float("nan")
        grid_df["is_missing"] = True
        grid_df["is_derived"] = False
        grid_df["forecast_type"] = "missing"
        return grid_df[
            [
                "startTime",
                "publishTime",
                "generation",
                "is_missing",
                "is_derived",
                "forecast_type",
            ]
        ]

    df: pd.DataFrame = forecasts_df.copy()
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")

    # Map cutoff time for each forecast record based on Europe/London delivery date
    df["deliveryDate"] = df["startTime"].dt.tz_convert(UK_TZ).dt.date
    cutoffs_lookup: dict[date, datetime] = {
        d: calculate_cutoff_timestamp(d, cutoff_time)
        for d in grid_df["deliveryDate"].unique()
    }
    df["cutoffTime"] = df["deliveryDate"].map(cutoffs_lookup)

    # Filter: must have valid cutoff mapping and publishTime <= cutoffTime
    eligible = df[
        df["cutoffTime"].notna() & (df["publishTime"] <= df["cutoffTime"])
    ].copy()

    if not eligible.empty:
        # Sort ascending so the last record per startTime is the latest published
        eligible = eligible.sort_values(by=["startTime", "publishTime"])
        latest_forecasts = eligible.groupby("startTime", as_index=False).last()[
            ["startTime", "publishTime", "generation"]
        ]
        latest_forecasts["is_derived"] = False
        latest_forecasts["forecast_type"] = "published"
    else:
        latest_forecasts = pd.DataFrame(
            columns=[
                "startTime",
                "publishTime",
                "generation",
                "is_derived",
                "forecast_type",
            ]
        )

    # Left join to preserve every target half-hour in the grid
    result: pd.DataFrame = pd.merge(
        grid_df[["startTime"]],
        latest_forecasts,
        on="startTime",
        how="left",
    )

    is_missing = result["generation"].isna()
    result["is_missing"] = is_missing
    result["is_derived"] = result["is_derived"].fillna(False).astype(bool)
    result.loc[is_missing, "forecast_type"] = "missing"
    result.loc[~is_missing, "forecast_type"] = result.loc[
        ~is_missing, "forecast_type"
    ].fillna("published")

    # Hourly Block Step-Hold: carry forward the :00 forecast to the :30 interval
    if step_hold:
        h00 = result[result["startTime"].dt.minute == 0].copy()
        h00 = h00[~h00["is_missing"]].copy()
        if not h00.empty:
            h00["target_30"] = h00["startTime"] + pd.Timedelta(minutes=30)
            h00_lookup = h00.set_index("target_30")

            mask_derive = (
                (result["startTime"].dt.minute == 30)
                & result["is_missing"]
                & result["startTime"].isin(h00_lookup.index)
            )
            if mask_derive.any():
                target_times = result.loc[mask_derive, "startTime"]
                result.loc[mask_derive, "generation"] = target_times.map(
                    h00_lookup["generation"]
                ).astype(float)
                result.loc[mask_derive, "publishTime"] = pd.to_datetime(
                    target_times.map(h00_lookup["publishTime"]), utc=True
                )
                result.loc[mask_derive, "is_derived"] = True
                result.loc[mask_derive, "forecast_type"] = "step_hold"
                result.loc[mask_derive, "is_missing"] = False

    return result[
        [
            "startTime",
            "publishTime",
            "generation",
            "is_missing",
            "is_derived",
            "forecast_type",
        ]
    ]
