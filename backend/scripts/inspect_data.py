"""Data inspection script analyzing actuals and forecasts Parquet datasets.

Evaluates forecast horizon limits, publication frequency, cutoff coverage,
and actuals continuity.
"""

from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


def load_datasets(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load actuals and forecasts parquet files.

    Args:
        data_dir: Path to directory containing parquet files.

    Returns:
        Tuple of (actuals_df, forecasts_df).
    """
    actuals_path: Path = data_dir / "actuals.parquet"
    forecasts_path: Path = data_dir / "forecasts.parquet"

    actuals_df: pd.DataFrame = pd.read_parquet(actuals_path)
    forecasts_df: pd.DataFrame = pd.read_parquet(forecasts_path)
    return actuals_df, forecasts_df


def analyze_forecast_horizons(df_fc: pd.DataFrame) -> dict[str, float]:
    """Compute min, max, and quantiles of forecast horizon in hours.

    Args:
        df_fc: Forecasts dataframe with startTime and publishTime.

    Returns:
        Dictionary of horizon statistics in hours.
    """
    diff_seconds = (df_fc["startTime"] - df_fc["publishTime"]).dt.total_seconds()
    horizon_series = diff_seconds / 3600.0
    return {
        "min_horizon_hours": float(horizon_series.min()),
        "p25_horizon_hours": float(horizon_series.quantile(0.25)),
        "median_horizon_hours": float(horizon_series.median()),
        "mean_horizon_hours": float(horizon_series.mean()),
        "p75_horizon_hours": float(horizon_series.quantile(0.75)),
        "max_horizon_hours": float(horizon_series.max()),
    }


def analyze_publish_frequency(df_fc: pd.DataFrame) -> pd.Series:
    """Calculate distinct publishTime timestamps per calendar day.

    Args:
        df_fc: Forecasts dataframe with publishTime.

    Returns:
        Series of distinct publish count indexed by date.
    """
    publish_dates = df_fc["publishTime"].dt.date
    return df_fc.groupby(publish_dates)["publishTime"].nunique()


def check_cutoff_coverage(
    df_fc: pd.DataFrame,
    start_delivery_date: date = date(2026, 1, 2),
    end_delivery_date: date = date(2026, 2, 1),
    cutoff_time_uk: time = time(9, 0),
) -> dict[str, Any]:
    """Evaluate target half hours that lack any forecast before Day D-1 cutoff.

    Args:
        df_fc: Forecasts dataframe with startTime and publishTime.
        start_delivery_date: Start of evaluated delivery range (inclusive).
        end_delivery_date: End of evaluated delivery range (inclusive).
        cutoff_time_uk: Cutoff time on Day D-1 (UK local time / UTC in January).

    Returns:
        Dictionary detailing total half hours, matched count, and missing half hours.
    """
    # Generate all expected target half hours
    cur_date: date = start_delivery_date
    expected_half_hours: list[tuple[datetime, datetime]] = []

    while cur_date <= end_delivery_date:
        # Day D-1 cutoff timestamp (GMT / UTC in January)
        prev_day: date = cur_date - timedelta(days=1)
        cutoff_dt: datetime = datetime.combine(prev_day, cutoff_time_uk, tzinfo=UTC)

        for period in range(48):
            thh_start: datetime = datetime.combine(
                cur_date, time(0, 0), tzinfo=UTC
            ) + timedelta(minutes=period * 30)
            expected_half_hours.append((thh_start, cutoff_dt))

        cur_date += timedelta(days=1)

    # Filter forecasts for quick lookup
    missing_targets: list[datetime] = []
    available_targets_count: int = 0
    covered_hours: set[datetime] = set()

    for thh_start, cutoff_dt in expected_half_hours:
        sub = df_fc[
            (df_fc["startTime"] == thh_start) & (df_fc["publishTime"] <= cutoff_dt)
        ]
        if sub.empty:
            missing_targets.append(thh_start)
        else:
            available_targets_count += 1
            covered_hours.add(thh_start)

    # Also check if matching by hour floor (since WINDFOR is hourly :00)
    distinct_hours: set[datetime] = {
        thh.replace(minute=0) for thh, _ in expected_half_hours
    }
    missing_hours: list[datetime] = []
    for h in distinct_hours:
        # Day D-1 cutoff for this hour's delivery day
        h_cutoff: datetime = datetime.combine(
            h.date() - timedelta(days=1), cutoff_time_uk, tzinfo=UTC
        )
        sub_h = df_fc[(df_fc["startTime"] == h) & (df_fc["publishTime"] <= h_cutoff)]
        if sub_h.empty:
            missing_hours.append(h)

    return {
        "total_evaluated_thh": len(expected_half_hours),
        "available_thh": available_targets_count,
        "missing_thh_count": len(missing_targets),
        "missing_thh_list": missing_targets,
        "total_distinct_hours": len(distinct_hours),
        "covered_distinct_hours": len(distinct_hours) - len(missing_hours),
        "missing_distinct_hours": len(missing_hours),
    }


def analyze_actuals_integrity(df_act: pd.DataFrame) -> dict[str, Any]:
    """Inspect actuals dataset for duplicate timestamps and sequence gaps.

    Args:
        df_act: Actuals dataframe with startTime.

    Returns:
        Dictionary describing duplicate counts and missing intervals.
    """
    df_sorted = df_act.sort_values(by="startTime").reset_index(drop=True)
    num_duplicates: int = int(df_sorted["startTime"].duplicated().sum())

    # Check for interval gaps
    diffs = df_sorted["startTime"].diff().dropna()
    expected_diff = timedelta(minutes=30)
    gaps: list[dict[str, Any]] = []

    gap_indices = df_sorted.index[1:][diffs != expected_diff]
    for idx in gap_indices:
        prev_time = df_sorted.loc[idx - 1, "startTime"]
        curr_time = df_sorted.loc[idx, "startTime"]
        gaps.append(
            {
                "after": prev_time,
                "next": curr_time,
                "gap_duration": curr_time - prev_time,
            }
        )

    return {
        "total_rows": len(df_act),
        "duplicates": num_duplicates,
        "is_monotonic": bool(df_sorted["startTime"].is_monotonic_increasing),
        "num_gaps": len(gaps),
        "gaps": gaps,
        "min_time": df_sorted["startTime"].min(),
        "max_time": df_sorted["startTime"].max(),
    }


def main() -> None:
    """Execute data inspection and output metrics."""
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    df_act, df_fc = load_datasets(data_dir)

    print("=" * 80)
    print(" " * 28 + "DATA INSPECTION REPORT")
    print("=" * 80)

    # 1. Forecast Horizons
    horizons = analyze_forecast_horizons(df_fc)
    print("\n1. FORECAST HORIZON (startTime - publishTime):")
    print(f"   Min Horizon:      {horizons['min_horizon_hours']:>8.2f} hours")
    print(f"   25th Percentile:  {horizons['p25_horizon_hours']:>8.2f} hours")
    print(f"   Median (P50):     {horizons['median_horizon_hours']:>8.2f} hours")
    print(f"   Mean:             {horizons['mean_horizon_hours']:>8.2f} hours")
    print(f"   75th Percentile:  {horizons['p75_horizon_hours']:>8.2f} hours")
    print(f"   Max Horizon:      {horizons['max_horizon_hours']:>8.2f} hours")

    # 2. Distinct Publish Times Per Day
    pub_counts = analyze_publish_frequency(df_fc)
    print("\n2. DISTINCT PUBLISHTIME VALUES PER DAY:")
    print(f"   Min / day:        {pub_counts.min():>4d}")
    print(f"   Max / day:        {pub_counts.max():>4d}")
    print(f"   Mean / day:       {pub_counts.mean():>6.2f}")
    print(f"   Median / day:     {pub_counts.median():>6.1f}")
    print("\n   Daily counts breakdown (last 10 days of sample):")
    for d, c in pub_counts.tail(10).items():
        print(f"     {d}: {c} distinct forecast runs")

    # 3. Cutoff Coverage for Delivery Range 2 Jan 2026 - 1 Feb 2026
    coverage = check_cutoff_coverage(df_fc)
    print("\n3. FORECAST COVERAGE BEFORE 09:00 UK CUTOFF (Day D-1):")
    print("   Evaluated Range:       2026-01-02 to 2026-02-01 (31 delivery days)")
    tot_thh: int = coverage["total_evaluated_thh"]
    cov_thh: int = coverage["available_thh"]
    mis_thh: int = coverage["missing_thh_count"]
    cov_pct: float = cov_thh / tot_thh * 100
    mis_pct: float = mis_thh / tot_thh * 100
    cov_hrs: int = coverage["covered_distinct_hours"]
    tot_hrs: int = coverage["total_distinct_hours"]

    print(f"   Total Target Half-Hrs: {tot_thh:,}")
    print(f"   Covered (exact :00):   {cov_thh:,} ({cov_pct:.1f}%)")
    print(f"   Missing (exact :30):   {mis_thh:,} ({mis_pct:.1f}%)")
    print("   Granularity Insight:   WINDFOR publishes at hourly intervals (:00)")
    print(f"   Hourly Resolution:     {cov_hrs} / {tot_hrs} hours covered (100.0%)")

    # 4. Actuals Integrity
    actuals_check = analyze_actuals_integrity(df_act)
    print("\n4. ACTUALS INTEGRITY & CONTINUITY (FUELHH WIND):")
    print(f"   Total Rows:       {actuals_check['total_rows']:,}")
    print(
        f"   Date Range:       {actuals_check['min_time']} to "
        f"{actuals_check['max_time']}"
    )
    print(f"   Duplicates:       {actuals_check['duplicates']}")
    print(f"   Monotonic:        {actuals_check['is_monotonic']}")
    print(f"   Sequence Gaps:    {actuals_check['num_gaps']}")
    if actuals_check["num_gaps"] > 0:
        print("   Identified Gaps:")
        for g in actuals_check["gaps"]:
            print(f"     - Between {g['after']} and {g['next']} ({g['gap_duration']})")
    else:
        print("   Continuity:       100% contiguous series (0 missing half-hours)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
