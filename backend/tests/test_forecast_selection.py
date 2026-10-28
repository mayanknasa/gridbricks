"""Unit tests for day-ahead forecast selection service.

Tests verify cutoff boundary conditions, latest publishTime selection,
missing forecast handling, hourly block step-hold (:30 derivation),
precedence of direct :30 forecasts, and multi-day date range support.
"""

from datetime import UTC, date, datetime, time

import numpy as np
import pandas as pd

from app.services.forecast_selection import select_latest_forecasts


def test_normal_selection() -> None:
    """Verify selecting the latest forecast published at or before the cutoff.

    Setup:
      - Delivery day: 2026-01-02
      - Cutoff on Day D-1 (2026-01-01): 09:00 UTC
      - Target: 2026-01-02 12:00:00 UTC
      - Forecast 1: published 2026-01-01 06:00 UTC, gen = 1000.0 MW
      - Forecast 2: published 2026-01-01 08:30 UTC, gen = 1250.0 MW
    Expected:
      - Forecast 2 is selected (generation = 1250.0 MW, is_missing = False).
      - is_derived = False, forecast_type = 'published'.
    """
    delivery_date: date = date(2026, 1, 2)
    target_thh: datetime = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)

    forecasts_df: pd.DataFrame = pd.DataFrame(
        [
            {
                "startTime": target_thh,
                "publishTime": datetime(2026, 1, 1, 6, 0, tzinfo=UTC),
                "generation": 1000.0,
            },
            {
                "startTime": target_thh,
                "publishTime": datetime(2026, 1, 1, 8, 30, tzinfo=UTC),
                "generation": 1250.0,
            },
        ]
    )

    result: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=delivery_date,
        end_date=delivery_date,
        cutoff_time=time(9, 0),
    )

    assert len(result) == 48

    selected_row = result[result["startTime"] == target_thh].iloc[0]
    assert selected_row["publishTime"] == datetime(2026, 1, 1, 8, 30, tzinfo=UTC)
    assert selected_row["generation"] == 1250.0
    assert not selected_row["is_missing"]
    assert not selected_row["is_derived"]
    assert selected_row["forecast_type"] == "published"


def test_forecast_published_exactly_at_cutoff() -> None:
    """Verify that a forecast published exactly at the 09:00:00 cutoff is included.

    Setup:
      - Delivery day: 2026-01-02
      - Cutoff on Day D-1: 2026-01-01 09:00:00 UTC
      - Target: 2026-01-02 14:00:00 UTC
      - Forecast 1: published 2026-01-01 08:00:00 UTC, gen = 800.0 MW
      - Forecast 2: published 2026-01-01 09:00:00 UTC (exact cutoff), gen = 950.0 MW
    Expected:
      - Forecast 2 is selected (generation = 950.0 MW, is_missing = False).
      - is_derived = False, forecast_type = 'published'.
    """
    delivery_date: date = date(2026, 1, 2)
    target_thh: datetime = datetime(2026, 1, 2, 14, 0, tzinfo=UTC)

    forecasts_df: pd.DataFrame = pd.DataFrame(
        [
            {
                "startTime": target_thh,
                "publishTime": datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC),
                "generation": 800.0,
            },
            {
                "startTime": target_thh,
                "publishTime": datetime(2026, 1, 1, 9, 0, 0, tzinfo=UTC),
                "generation": 950.0,
            },
        ]
    )

    result: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=delivery_date,
        end_date=delivery_date,
        cutoff_time=time(9, 0),
    )

    selected_row = result[result["startTime"] == target_thh].iloc[0]
    assert selected_row["publishTime"] == datetime(2026, 1, 1, 9, 0, 0, tzinfo=UTC)
    assert selected_row["generation"] == 950.0
    assert not selected_row["is_missing"]
    assert not selected_row["is_derived"]
    assert selected_row["forecast_type"] == "published"


def test_forecast_published_one_minute_after_cutoff_is_ignored() -> None:
    """Verify that a forecast published 1 minute after cutoff (09:01:00) is ignored.

    Setup:
      - Delivery day: 2026-01-02
      - Cutoff on Day D-1: 2026-01-01 09:00:00 UTC
      - Target: 2026-01-02 15:00:00 UTC
      - Forecast 1: published 2026-01-01 08:59:00 UTC, gen = 1100.0 MW
      - Forecast 2: published 2026-01-01 09:01:00 UTC (past cutoff), gen = 9999.0 MW
    Expected:
      - Forecast 2 is ignored; Forecast 1 is selected (gen = 1100.0 MW).
      - is_derived = False, forecast_type = 'published'.
    """
    delivery_date: date = date(2026, 1, 2)
    target_thh: datetime = datetime(2026, 1, 2, 15, 0, tzinfo=UTC)

    forecasts_df: pd.DataFrame = pd.DataFrame(
        [
            {
                "startTime": target_thh,
                "publishTime": datetime(2026, 1, 1, 8, 59, 0, tzinfo=UTC),
                "generation": 1100.0,
            },
            {
                "startTime": target_thh,
                "publishTime": datetime(2026, 1, 1, 9, 1, 0, tzinfo=UTC),
                "generation": 9999.0,
            },
        ]
    )

    result: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=delivery_date,
        end_date=delivery_date,
        cutoff_time=time(9, 0),
    )

    selected_row = result[result["startTime"] == target_thh].iloc[0]
    assert selected_row["publishTime"] == datetime(2026, 1, 1, 8, 59, 0, tzinfo=UTC)
    assert selected_row["generation"] == 1100.0
    assert not selected_row["is_missing"]
    assert not selected_row["is_derived"]
    assert selected_row["forecast_type"] == "published"


def test_half_hour_with_no_valid_forecast_step_hold_disabled() -> None:
    """Verify missing forecast handling when step_hold is explicitly disabled.

    Setup:
      - Delivery day: 2026-01-02
      - Cutoff on Day D-1: 2026-01-01 09:00:00 UTC
      - Target A (10:00 UTC): forecast before cutoff (08:00 UTC, 1500.0 MW)
      - Target B (10:30 UTC): ONLY forecast after cutoff (10:00 UTC, 1800.0 MW)
      - Target C (11:00 UTC): has no forecast records at all
    Expected:
      - Output contains 48 rows (never drops missing half-hours).
      - Target A: generation = 1500.0 MW, is_missing = False,
        forecast_type = 'published'.
      - Target B: generation is NaN, publishTime is NaT, is_missing = True,
        is_derived = False, forecast_type = 'missing'.
      - Target C: generation is NaN, publishTime is NaT, is_missing = True,
        is_derived = False, forecast_type = 'missing'.
    """
    delivery_date: date = date(2026, 1, 2)
    target_a: datetime = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
    target_b: datetime = datetime(2026, 1, 2, 10, 30, tzinfo=UTC)
    target_c: datetime = datetime(2026, 1, 2, 11, 0, tzinfo=UTC)

    forecasts_df: pd.DataFrame = pd.DataFrame(
        [
            {
                "startTime": target_a,
                "publishTime": datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC),
                "generation": 1500.0,
            },
            {
                "startTime": target_b,
                "publishTime": datetime(
                    2026, 1, 1, 10, 0, 0, tzinfo=UTC
                ),  # After cutoff
                "generation": 1800.0,
            },
        ]
    )

    result: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=delivery_date,
        end_date=delivery_date,
        cutoff_time=time(9, 0),
        step_hold=False,
    )

    # Never drop any half hour
    assert len(result) == 48

    # Target A has valid forecast
    row_a = result[result["startTime"] == target_a].iloc[0]
    assert row_a["generation"] == 1500.0
    assert row_a["publishTime"] == datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC)
    assert not row_a["is_missing"]
    assert not row_a["is_derived"]
    assert row_a["forecast_type"] == "published"

    # Target B was only published after cutoff -> missing when step_hold=False
    row_b = result[result["startTime"] == target_b].iloc[0]
    assert np.isnan(row_b["generation"])
    assert pd.isna(row_b["publishTime"])
    assert row_b["is_missing"]
    assert not row_b["is_derived"]
    assert row_b["forecast_type"] == "missing"

    # Target C has no forecast records at all -> missing
    row_c = result[result["startTime"] == target_c].iloc[0]
    assert np.isnan(row_c["generation"])
    assert pd.isna(row_c["publishTime"])
    assert row_c["is_missing"]
    assert not row_c["is_derived"]
    assert row_c["forecast_type"] == "missing"


def test_step_hold_derives_30_minute_forecast_from_preceding_hour() -> None:
    """Verify that :30 period inherits :00 forecast with explicit attribution.

    Setup:
      - Delivery day: 2026-01-02
      - Cutoff on Day D-1: 2026-01-01 09:00:00 UTC
      - 14:00 UTC: published at 08:00 UTC with generation = 2500.0 MW
      - 14:30 UTC: has no published forecast
    Expected:
      - 14:00 UTC: generation = 2500.0 MW, is_missing = False,
        is_derived = False, forecast_type = 'published'.
      - 14:30 UTC: generation = 2500.0 MW, publishTime = 2026-01-01 08:00:00 UTC,
        is_missing = False, is_derived = True, forecast_type = 'step_hold'.
    """
    delivery_date: date = date(2026, 1, 2)
    target_1400: datetime = datetime(2026, 1, 2, 14, 0, tzinfo=UTC)
    target_1430: datetime = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)

    forecasts_df: pd.DataFrame = pd.DataFrame(
        [
            {
                "startTime": target_1400,
                "publishTime": datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC),
                "generation": 2500.0,
            },
        ]
    )

    result: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=delivery_date,
        end_date=delivery_date,
        cutoff_time=time(9, 0),
        step_hold=True,
    )

    # 14:00 (Published)
    row_1400 = result[result["startTime"] == target_1400].iloc[0]
    assert row_1400["generation"] == 2500.0
    assert row_1400["publishTime"] == datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC)
    assert not row_1400["is_missing"]
    assert not row_1400["is_derived"]
    assert row_1400["forecast_type"] == "published"

    # 14:30 (Step-Hold Derived)
    row_1430 = result[result["startTime"] == target_1430].iloc[0]
    assert row_1430["generation"] == 2500.0
    assert row_1430["publishTime"] == datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC)
    assert not row_1430["is_missing"]
    assert row_1430["is_derived"]
    assert row_1430["forecast_type"] == "step_hold"


def test_direct_30_minute_forecast_takes_precedence_over_step_hold() -> None:
    """Verify that a directly published :30 forecast overrides step-hold inheritance.

    Setup:
      - Delivery day: 2026-01-02
      - Cutoff on Day D-1: 2026-01-01 09:00:00 UTC
      - 14:00 UTC: published at 08:00 UTC with gen = 2000.0 MW
      - 14:30 UTC: directly published at 08:15 UTC with gen = 2200.0 MW
    Expected:
      - 14:30 UTC retains its own published generation = 2200.0 MW.
      - is_missing = False, is_derived = False, forecast_type = 'published'.
    """
    delivery_date: date = date(2026, 1, 2)
    target_1400: datetime = datetime(2026, 1, 2, 14, 0, tzinfo=UTC)
    target_1430: datetime = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)

    forecasts_df: pd.DataFrame = pd.DataFrame(
        [
            {
                "startTime": target_1400,
                "publishTime": datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC),
                "generation": 2000.0,
            },
            {
                "startTime": target_1430,
                "publishTime": datetime(2026, 1, 1, 8, 15, 0, tzinfo=UTC),
                "generation": 2200.0,
            },
        ]
    )

    result: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=delivery_date,
        end_date=delivery_date,
        cutoff_time=time(9, 0),
        step_hold=True,
    )

    row_1430 = result[result["startTime"] == target_1430].iloc[0]
    assert row_1430["generation"] == 2200.0
    assert row_1430["publishTime"] == datetime(2026, 1, 1, 8, 15, 0, tzinfo=UTC)
    assert not row_1430["is_missing"]
    assert not row_1430["is_derived"]
    assert row_1430["forecast_type"] == "published"


def test_step_hold_remains_missing_when_preceding_hour_is_missing() -> None:
    """Verify that :30 remains missing if :00 had no forecast at or before cutoff.

    Setup:
      - Delivery day: 2026-01-02
      - Cutoff on Day D-1: 2026-01-01 09:00:00 UTC
      - 16:00 UTC: published at 10:00 UTC (after cutoff -> missing)
      - 16:30 UTC: no forecast
    Expected:
      - 16:00 UTC: is_missing = True, is_derived = False, forecast_type = 'missing'.
      - 16:30 UTC: is_missing = True, is_derived = False, forecast_type = 'missing'.
    """
    delivery_date: date = date(2026, 1, 2)
    target_1600: datetime = datetime(2026, 1, 2, 16, 0, tzinfo=UTC)
    target_1630: datetime = datetime(2026, 1, 2, 16, 30, tzinfo=UTC)

    forecasts_df: pd.DataFrame = pd.DataFrame(
        [
            {
                "startTime": target_1600,
                "publishTime": datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC),
                "generation": 3000.0,
            },
        ]
    )

    result: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=delivery_date,
        end_date=delivery_date,
        cutoff_time=time(9, 0),
        step_hold=True,
    )

    row_1600 = result[result["startTime"] == target_1600].iloc[0]
    assert row_1600["is_missing"]
    assert not row_1600["is_derived"]
    assert row_1600["forecast_type"] == "missing"

    row_1630 = result[result["startTime"] == target_1630].iloc[0]
    assert row_1630["is_missing"]
    assert not row_1630["is_derived"]
    assert row_1630["forecast_type"] == "missing"


def test_multiple_delivery_days() -> None:
    """Verify correct cutoff application across multiple distinct delivery days.

    Setup:
      - Delivery range: 2026-01-02 to 2026-01-04 (3 days -> 144 half-hours)
      - Day 1 (2026-01-02): Cutoff 2026-01-01 09:00 UTC
        - Forecast for 12:00 UTC published 2026-01-01 07:00 UTC (1200.0 MW)
      - Day 2 (2026-01-03): Cutoff 2026-01-02 09:00 UTC
        - Forecast for 12:00 UTC published 2026-01-02 08:00 UTC (2400.0 MW)
      - Day 3 (2026-01-04): Cutoff 2026-01-03 09:00 UTC
        - Forecast for 12:00 UTC published 2026-01-03 08:30 UTC (3600.0 MW)
    Expected:
      - Total length is exactly 144 rows.
      - With step_hold=False: 141 missing rows (only 3 rows populated).
      - With step_hold=True: 138 missing rows (3 published + 3 derived = 6 rows).
    """
    start_date: date = date(2026, 1, 2)
    end_date: date = date(2026, 1, 4)

    target_day1: datetime = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    target_day2: datetime = datetime(2026, 1, 3, 12, 0, tzinfo=UTC)
    target_day3: datetime = datetime(2026, 1, 4, 12, 0, tzinfo=UTC)

    forecasts_df: pd.DataFrame = pd.DataFrame(
        [
            {
                "startTime": target_day1,
                "publishTime": datetime(2026, 1, 1, 7, 0, tzinfo=UTC),
                "generation": 1200.0,
            },
            {
                # Published after Day 1 cutoff, but valid for Day 2 cutoff!
                "startTime": target_day2,
                "publishTime": datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
                "generation": 2400.0,
            },
            {
                # Valid for Day 3 cutoff
                "startTime": target_day3,
                "publishTime": datetime(2026, 1, 3, 8, 30, tzinfo=UTC),
                "generation": 3600.0,
            },
        ]
    )

    # Test with step_hold=False
    result_raw: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=start_date,
        end_date=end_date,
        cutoff_time=time(9, 0),
        step_hold=False,
    )
    assert len(result_raw) == 144
    assert result_raw["is_missing"].sum() == 141

    # Test with step_hold=True (default)
    result: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=start_date,
        end_date=end_date,
        cutoff_time=time(9, 0),
        step_hold=True,
    )
    assert len(result) == 144
    assert result["is_missing"].sum() == 138

    row1 = result[result["startTime"] == target_day1].iloc[0]
    assert row1["generation"] == 1200.0
    assert not row1["is_missing"]
    assert not row1["is_derived"]
    assert row1["forecast_type"] == "published"

    row2 = result[result["startTime"] == target_day2].iloc[0]
    assert row2["generation"] == 2400.0
    assert not row2["is_missing"]
    assert not row2["is_derived"]
    assert row2["forecast_type"] == "published"

    row3 = result[result["startTime"] == target_day3].iloc[0]
    assert row3["generation"] == 3600.0
    assert not row3["is_missing"]
    assert not row3["is_derived"]
    assert row3["forecast_type"] == "published"

    # Verify that 12:30 on day 1 was derived
    target_day1_30: datetime = datetime(2026, 1, 2, 12, 30, tzinfo=UTC)
    row1_30 = result[result["startTime"] == target_day1_30].iloc[0]
    assert row1_30["generation"] == 1200.0
    assert not row1_30["is_missing"]
    assert row1_30["is_derived"]
    assert row1_30["forecast_type"] == "step_hold"


def test_summer_bst_date_first_settlement_period_at_2300_utc_previous_day() -> None:
    """Verify deliveryDate extraction during British Summer Time (BST, UTC+1).

    In British Summer Time (BST = UTC+1), settlement period 1 of delivery day D
    begins at 00:00 BST, which corresponds to 23:00 UTC on day D-1.

    Setup:
      - Delivery day: 2026-07-01 (BST, UTC+1).
      - First settlement period (00:00 BST): 2026-06-30 23:00:00 UTC.
      - Day D-1 cutoff: 09:00 BST on 2026-06-30 -> 2026-06-30 08:00:00 UTC.
      - Forecast 1 for 23:00 UTC published 2026-06-30 07:30:00 UTC (1500.0 MW).
      - Forecast 2 for 23:00 UTC published 2026-06-30 08:30:00 UTC (1800.0 MW,
        after cutoff).

    Expected:
      - The delivery date in Europe/London is 2026-07-01, not 2026-06-30.
      - Target grid begins at 2026-06-30 23:00:00 UTC.
      - Forecast 1 is selected prior to cutoff (1500.0 MW, is_missing = False).
      - Forecast 2 after cutoff is correctly ignored.
    """
    delivery_date: date = date(2026, 7, 1)
    sp1_utc: datetime = datetime(2026, 6, 30, 23, 0, 0, tzinfo=UTC)

    forecasts_df: pd.DataFrame = pd.DataFrame(
        [
            {
                "startTime": sp1_utc,
                "publishTime": datetime(2026, 6, 30, 7, 30, 0, tzinfo=UTC),
                "generation": 1500.0,
            },
            {
                # Published after 09:00 BST cutoff (08:00 UTC)
                "startTime": sp1_utc,
                "publishTime": datetime(2026, 6, 30, 8, 30, 0, tzinfo=UTC),
                "generation": 1800.0,
            },
        ]
    )

    result: pd.DataFrame = select_latest_forecasts(
        forecasts_df=forecasts_df,
        start_date=delivery_date,
        end_date=delivery_date,
        cutoff_time=time(9, 0),
        step_hold=False,
    )

    assert len(result) == 48
    first_period = result.iloc[0]
    assert first_period["startTime"] == sp1_utc
    assert first_period["publishTime"] == datetime(2026, 6, 30, 7, 30, 0, tzinfo=UTC)
    assert first_period["generation"] == 1500.0
    assert not first_period["is_missing"]
    assert not first_period["is_derived"]
    assert first_period["forecast_type"] == "published"

