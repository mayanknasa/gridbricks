"""Metrics service for evaluating forecast errors against actual outturn.

Implements pure functions for calculating MAE, RMSE, Bias, Normalised MAE,
and error percentiles overall, by hour of day (UK local), and by forecast horizon.
"""

import math
from typing import Final
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.models.metrics import HorizonMetrics, HourlyMetrics, OverallMetrics

UK_TZ: Final[ZoneInfo] = ZoneInfo("Europe/London")

DEFAULT_HORIZON_BUCKETS: Final[list[tuple[float, float, str]]] = [
    (-math.inf, 0.0, "<0h"),
    (0.0, 6.0, "0-6h"),
    (6.0, 12.0, "6-12h"),
    (12.0, 24.0, "12-24h"),
    (24.0, 36.0, "24-36h"),
    (36.0, 48.0, "36-48h"),
    (48.0, math.inf, ">48h"),
]


def join_forecasts_with_actuals(
    selected_forecasts_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
) -> pd.DataFrame:
    """Join selected forecasts with actuals on startTime and compute error.

    Error formula: error = actual_generation - forecast_generation.

    Args:
        selected_forecasts_df: DataFrame containing at least ['startTime',
            'generation'] where generation is average power in MW over a half hour.
        actuals_df: DataFrame containing at least ['startTime', 'generation']
            where generation is average power in MW over a half hour.

    Returns:
        DataFrame containing ['startTime', 'publishTime', 'forecast_generation',
        'actual_generation', 'error', 'abs_error'].
    """
    if selected_forecasts_df.empty:
        return pd.DataFrame(
            columns=[
                "startTime",
                "publishTime",
                "forecast_generation",
                "actual_generation",
                "error",
                "abs_error",
            ]
        )

    fc: pd.DataFrame = selected_forecasts_df.copy()
    fc["startTime"] = pd.to_datetime(fc["startTime"], utc=True)
    fc["generation"] = pd.to_numeric(fc["generation"], errors="coerce")
    fc = fc.rename(columns={"generation": "forecast_generation"})

    if "publishTime" in fc.columns:
        fc["publishTime"] = pd.to_datetime(fc["publishTime"], utc=True)
    else:
        fc["publishTime"] = pd.NaT

    if actuals_df.empty:
        fc["actual_generation"] = float("nan")
        fc["error"] = float("nan")
        fc["abs_error"] = float("nan")
        cols = [
            "startTime",
            "publishTime",
            "forecast_generation",
            "actual_generation",
            "error",
            "abs_error",
        ]
        extra_cols = [c for c in ["is_derived", "forecast_type"] if c in fc.columns]
        return fc[cols + extra_cols]

    act: pd.DataFrame = actuals_df[["startTime", "generation"]].copy()
    act["startTime"] = pd.to_datetime(act["startTime"], utc=True)
    act["generation"] = pd.to_numeric(act["generation"], errors="coerce")
    act = act.rename(columns={"generation": "actual_generation"})

    # Deduplicate actuals by startTime if duplicate records exist
    act = act.drop_duplicates(subset=["startTime"]).reset_index(drop=True)

    joined: pd.DataFrame = pd.merge(fc, act, on="startTime", how="left")
    joined["error"] = joined["actual_generation"] - joined["forecast_generation"]
    joined["abs_error"] = joined["error"].abs()

    cols = [
        "startTime",
        "publishTime",
        "forecast_generation",
        "actual_generation",
        "error",
        "abs_error",
    ]
    extra_cols = [c for c in ["is_derived", "forecast_type"] if c in joined.columns]
    return joined[cols + extra_cols].reset_index(drop=True)


def calculate_overall_metrics(joined_df: pd.DataFrame) -> OverallMetrics:
    """Compute overall summary metrics across evaluated half-hourly intervals.

    Args:
        joined_df: Output DataFrame from join_forecasts_with_actuals.

    Returns:
        OverallMetrics Pydantic model populated with counts, MAE, RMSE,
        bias, nMAE, and percentiles.
    """
    total_count: int = len(joined_df)
    if total_count == 0:
        return OverallMetrics(
            total_count=0,
            valid_count=0,
            missing_count=0,
        )

    valid_df: pd.DataFrame = joined_df.dropna(subset=["error"]).copy()
    valid_count: int = len(valid_df)
    missing_count: int = total_count - valid_count

    if valid_count == 0:
        return OverallMetrics(
            total_count=total_count,
            valid_count=0,
            missing_count=missing_count,
        )

    errors: pd.Series = valid_df["error"]
    abs_errors: pd.Series = valid_df["abs_error"]
    actuals: pd.Series = valid_df["actual_generation"]
    forecasts: pd.Series = valid_df["forecast_generation"]

    mae: float = float(abs_errors.mean())
    rmse: float = float(np.sqrt((errors**2).mean()))
    bias: float = float(errors.mean())
    mean_actual: float = float(actuals.mean())
    mean_forecast: float = float(forecasts.mean())

    nmae_pct: float | None = None
    if mean_actual != 0.0:
        nmae_pct = float((mae / mean_actual) * 100.0)

    p50: float = float(np.percentile(abs_errors, 50))
    p90: float = float(np.percentile(abs_errors, 90))
    p95: float = float(np.percentile(abs_errors, 95))

    return OverallMetrics(
        total_count=total_count,
        valid_count=valid_count,
        missing_count=missing_count,
        mae=mae,
        rmse=rmse,
        bias=bias,
        nmae_pct=nmae_pct,
        p50=p50,
        p90=p90,
        p95=p95,
        mean_actual=mean_actual,
        mean_forecast=mean_forecast,
    )


def calculate_hourly_metrics(joined_df: pd.DataFrame) -> list[HourlyMetrics]:
    """Calculate error metrics aggregated by hour of the day in UK local time.

    Converts startTime to Europe/London timezone to ensure daylight saving
    and diurnal cycles are correctly aligned.

    Args:
        joined_df: Joined DataFrame containing startTime, error, abs_error.

    Returns:
        List of 24 HourlyMetrics models (for hours 0 through 23).
    """
    hourly_results: list[HourlyMetrics] = []

    if joined_df.empty:
        for h in range(24):
            hourly_results.append(
                HourlyMetrics(
                    hour=h,
                    total_count=0,
                    valid_count=0,
                    missing_count=0,
                )
            )
        return hourly_results

    df: pd.DataFrame = joined_df.copy()
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["uk_hour"] = df["startTime"].dt.tz_convert(UK_TZ).dt.hour

    for h in range(24):
        hour_df: pd.DataFrame = df[df["uk_hour"] == h]
        h_total: int = len(hour_df)
        valid_df: pd.DataFrame = hour_df.dropna(subset=["error"])
        h_valid: int = len(valid_df)
        h_missing: int = h_total - h_valid

        if h_valid == 0:
            hourly_results.append(
                HourlyMetrics(
                    hour=h,
                    total_count=h_total,
                    valid_count=0,
                    missing_count=h_missing,
                )
            )
            continue

        errors: pd.Series = valid_df["error"]
        abs_errors: pd.Series = valid_df["abs_error"]
        mae: float = float(abs_errors.mean())
        rmse: float = float(np.sqrt((errors**2).mean()))
        bias: float = float(errors.mean())
        p50: float = float(np.percentile(abs_errors, 50))
        p90: float = float(np.percentile(abs_errors, 90))
        p95: float = float(np.percentile(abs_errors, 95))
        mean_act: float = float(valid_df["actual_generation"].mean())
        mean_fc: float = float(valid_df["forecast_generation"].mean())

        hourly_results.append(
            HourlyMetrics(
                hour=h,
                total_count=h_total,
                valid_count=h_valid,
                missing_count=h_missing,
                mae=mae,
                rmse=rmse,
                bias=bias,
                p50=p50,
                p90=p90,
                p95=p95,
                mean_actual=mean_act,
                mean_forecast=mean_fc,
            )
        )

    return hourly_results


def calculate_horizon_metrics(
    all_forecasts_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
    buckets: list[tuple[float, float, str]] | None = None,
) -> list[HorizonMetrics]:
    """Calculate error metrics by forecast horizon using all available forecasts.

    Forecast horizon = (startTime - publishTime) in hours.

    Args:
        all_forecasts_df: Forecasts DataFrame with ['startTime', 'publishTime',
            'generation'] where generation is average power in MW over a half hour.
        actuals_df: Actuals DataFrame with ['startTime', 'generation'] where
            generation is average power in MW over a half hour.
        buckets: List of (min_hours, max_hours, label) tuples. Defaults to
            DEFAULT_HORIZON_BUCKETS.

    Returns:
        List of HorizonMetrics models for each horizon bin.
    """
    horizon_buckets = buckets if buckets is not None else DEFAULT_HORIZON_BUCKETS
    results: list[HorizonMetrics] = []

    if all_forecasts_df.empty:
        for low, high, label in horizon_buckets:
            min_h = None if math.isinf(low) else low
            max_h = None if math.isinf(high) else high
            results.append(
                HorizonMetrics(
                    bucket=label,
                    min_horizon_hours=min_h,
                    max_horizon_hours=max_h,
                    total_count=0,
                    valid_count=0,
                    missing_count=0,
                )
            )
        return results

    fc: pd.DataFrame = all_forecasts_df.copy()
    fc["startTime"] = pd.to_datetime(fc["startTime"], utc=True)
    fc["publishTime"] = pd.to_datetime(fc["publishTime"], utc=True)
    fc["forecast_generation"] = pd.to_numeric(fc["generation"], errors="coerce")

    # Filter out records where publishTime or startTime is missing
    fc = fc.dropna(subset=["startTime", "publishTime"])
    fc["horizon_hours"] = (
        fc["startTime"] - fc["publishTime"]
    ).dt.total_seconds() / 3600.0

    act: pd.DataFrame = actuals_df[["startTime", "generation"]].copy()
    act["startTime"] = pd.to_datetime(act["startTime"], utc=True)
    act["actual_generation"] = pd.to_numeric(act["generation"], errors="coerce")
    act = act.drop_duplicates(subset=["startTime"])

    # Left join to preserve all forecasts
    merged: pd.DataFrame = pd.merge(fc, act, on="startTime", how="left")
    merged["error"] = merged["actual_generation"] - merged["forecast_generation"]
    merged["abs_error"] = merged["error"].abs()

    for low, high, label in horizon_buckets:
        if math.isinf(high):
            mask = merged["horizon_hours"] >= low
        else:
            mask = (merged["horizon_hours"] >= low) & (merged["horizon_hours"] < high)

        min_h = None if math.isinf(low) else low
        max_h = None if math.isinf(high) else high

        bucket_df: pd.DataFrame = merged[mask]
        b_total: int = len(bucket_df)
        valid_df: pd.DataFrame = bucket_df.dropna(subset=["error"])
        b_valid: int = len(valid_df)
        b_missing: int = b_total - b_valid

        if b_valid == 0:
            results.append(
                HorizonMetrics(
                    bucket=label,
                    min_horizon_hours=min_h,
                    max_horizon_hours=max_h,
                    total_count=b_total,
                    valid_count=0,
                    missing_count=b_missing,
                )
            )
            continue

        errors: pd.Series = valid_df["error"]
        abs_errors: pd.Series = valid_df["abs_error"]

        mae: float = float(abs_errors.mean())
        rmse: float = float(np.sqrt((errors**2).mean()))
        bias: float = float(errors.mean())
        p50: float = float(np.percentile(abs_errors, 50))
        p90: float = float(np.percentile(abs_errors, 90))
        p95: float = float(np.percentile(abs_errors, 95))

        results.append(
            HorizonMetrics(
                bucket=label,
                min_horizon_hours=min_h,
                max_horizon_hours=max_h,
                total_count=b_total,
                valid_count=b_valid,
                missing_count=b_missing,
                mae=mae,
                rmse=rmse,
                bias=bias,
                p50=p50,
                p90=p90,
                p95=p95,
            )
        )

    return results
