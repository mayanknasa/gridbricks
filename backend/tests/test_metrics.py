"""Unit tests for metrics calculation service.

Tests verify hand-calculated metrics (MAE, RMSE, Bias, nMAE, Percentiles),
missing value counting, and edge cases (empty input, all-missing forecasts,
single row).
"""

import math
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from app.models.metrics import HorizonMetrics, HourlyMetrics, OverallMetrics
from app.services.metrics import (
    calculate_horizon_metrics,
    calculate_hourly_metrics,
    calculate_overall_metrics,
    join_forecasts_with_actuals,
)


def test_overall_metrics_hand_calculated() -> None:
    """Verify overall metrics against hand-calculated values.

    Data:
      - Row 1: Actual = 100.0, Forecast = 80.0  -> Error = +20.0, Abs = 20.0
      - Row 2: Actual = 200.0, Forecast = 220.0 -> Error = -20.0, Abs = 20.0
      - Row 3: Actual = 150.0, Forecast = 110.0 -> Error = +40.0, Abs = 40.0
      - Row 4: Actual = 250.0, Forecast = 290.0 -> Error = -40.0, Abs = 40.0
    Expected Hand Calculations:
      - Count: total = 4, valid = 4, missing = 0
      - Errors: [+20, -20, +40, -40]
      - Bias: (20 - 20 + 40 - 40) / 4 = 0.0 MW
      - MAE: (20 + 20 + 40 + 40) / 4 = 120 / 4 = 30.0 MW
      - RMSE: sqrt((400 + 400 + 1600 + 1600) / 4) = sqrt(1000) = 31.6227766...
      - Mean Actual: (100 + 200 + 150 + 250) / 4 = 175.0 MW
      - Mean Forecast: (80 + 220 + 110 + 290) / 4 = 175.0 MW
      - nMAE: (30.0 / 175.0) * 100 = 17.142857... %
      - P50 (median of [20, 20, 40, 40]): 30.0 MW
      - P90: 40.0 MW
      - P95: 40.0 MW
    """
    times = [
        datetime(2026, 1, 2, 0, 0, tzinfo=UTC),
        datetime(2026, 1, 2, 0, 30, tzinfo=UTC),
        datetime(2026, 1, 2, 1, 0, tzinfo=UTC),
        datetime(2026, 1, 2, 1, 30, tzinfo=UTC),
    ]

    selected_fc = pd.DataFrame(
        {
            "startTime": times,
            "generation": [80.0, 220.0, 110.0, 290.0],
        }
    )
    actuals = pd.DataFrame(
        {
            "startTime": times,
            "generation": [100.0, 200.0, 150.0, 250.0],
        }
    )

    joined = join_forecasts_with_actuals(selected_fc, actuals)
    metrics: OverallMetrics = calculate_overall_metrics(joined)

    assert metrics.total_count == 4
    assert metrics.valid_count == 4
    assert metrics.missing_count == 0

    assert metrics.bias == 0.0
    assert metrics.mae == 30.0
    assert metrics.rmse is not None
    assert math.isclose(metrics.rmse, math.sqrt(1000.0), rel_tol=1e-6)

    assert metrics.mean_actual == 175.0
    assert metrics.mean_forecast == 175.0
    assert metrics.nmae_pct is not None
    assert math.isclose(metrics.nmae_pct, (30.0 / 175.0) * 100.0, rel_tol=1e-6)

    assert metrics.p50 == 30.0
    assert metrics.p90 == 40.0
    assert metrics.p95 == 40.0


def test_edge_case_single_row() -> None:
    """Verify single row edge case metrics.

    Data:
      - 1 row: Actual = 120.0, Forecast = 100.0
    Expected:
      - total = 1, valid = 1, missing = 0
      - Error = 120 - 100 = 20.0
      - MAE = 20.0
      - RMSE = 20.0
      - Bias = 20.0
      - nMAE = (20.0 / 120.0) * 100 = 16.666667 %
      - P50 = 20.0, P90 = 20.0, P95 = 20.0
    """
    t = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    selected_fc = pd.DataFrame({"startTime": [t], "generation": [100.0]})
    actuals = pd.DataFrame({"startTime": [t], "generation": [120.0]})

    joined = join_forecasts_with_actuals(selected_fc, actuals)
    metrics: OverallMetrics = calculate_overall_metrics(joined)

    assert metrics.total_count == 1
    assert metrics.valid_count == 1
    assert metrics.missing_count == 0

    assert metrics.mae == 20.0
    assert metrics.rmse == 20.0
    assert metrics.bias == 20.0
    assert metrics.mean_actual == 120.0
    assert metrics.mean_forecast == 100.0

    assert metrics.nmae_pct is not None
    assert math.isclose(metrics.nmae_pct, (20.0 / 120.0) * 100.0, rel_tol=1e-6)
    assert metrics.p50 == 20.0
    assert metrics.p90 == 20.0
    assert metrics.p95 == 20.0


def test_edge_case_all_missing_forecasts() -> None:
    """Verify metrics when all forecasts are missing (NaN).

    Setup:
      - 2 target half-hours with actual generation, but null forecasts.
    Expected:
      - total = 2, valid = 0, missing = 2
      - All metric values are None.
    """
    times = [
        datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        datetime(2026, 1, 2, 8, 30, tzinfo=UTC),
    ]
    selected_fc = pd.DataFrame(
        {
            "startTime": times,
            "generation": [np.nan, np.nan],
        }
    )
    actuals = pd.DataFrame(
        {
            "startTime": times,
            "generation": [150.0, 250.0],
        }
    )

    joined = join_forecasts_with_actuals(selected_fc, actuals)
    metrics: OverallMetrics = calculate_overall_metrics(joined)

    assert metrics.total_count == 2
    assert metrics.valid_count == 0
    assert metrics.missing_count == 2

    assert metrics.mae is None
    assert metrics.rmse is None
    assert metrics.bias is None
    assert metrics.nmae_pct is None
    assert metrics.p50 is None
    assert metrics.p90 is None
    assert metrics.p95 is None


def test_edge_case_empty_input() -> None:
    """Verify metrics calculation on empty DataFrames (0 rows)."""
    empty_fc = pd.DataFrame(columns=["startTime", "generation"])
    empty_act = pd.DataFrame(columns=["startTime", "generation"])

    joined = join_forecasts_with_actuals(empty_fc, empty_act)
    overall: OverallMetrics = calculate_overall_metrics(joined)

    assert overall.total_count == 0
    assert overall.valid_count == 0
    assert overall.missing_count == 0
    assert overall.mae is None

    hourly = calculate_hourly_metrics(joined)
    assert len(hourly) == 24
    assert all(h.total_count == 0 for h in hourly)
    assert all(h.missing_count == 0 for h in hourly)
    assert all(h.mae is None for h in hourly)

    horizon = calculate_horizon_metrics(empty_fc, empty_act)
    assert len(horizon) > 0
    assert all(b.total_count == 0 for b in horizon)
    assert all(b.missing_count == 0 for b in horizon)
    assert all(b.mae is None for b in horizon)


def test_hourly_metrics_hand_calculated() -> None:
    """Verify hourly breakdown metrics against hand-calculated values.

    Data:
      - Hour 0 (00:00, 00:30 UTC / UK):
        - 00:00: Actual = 100.0, Forecast = 80.0  -> Error = +20.0
        - 00:30: Actual = 200.0, Forecast = 160.0 -> Error = +40.0
        Expected Hour 0: total=2, valid=2, missing=0, MAE=30.0, Bias=30.0
      - Hour 1 (01:00, 01:30 UTC / UK):
        - 01:00: Actual = 150.0, Forecast = NaN   -> Missing!
        - 01:30: Actual = 150.0, Forecast = 150.0 -> Error = 0.0
        Expected Hour 1: total=2, valid=1, missing=1, MAE=0.0, Bias=0.0
      - Hours 2-23: total=0, valid=0, missing=0, metrics=None
    """
    times = [
        datetime(2026, 1, 2, 0, 0, tzinfo=UTC),
        datetime(2026, 1, 2, 0, 30, tzinfo=UTC),
        datetime(2026, 1, 2, 1, 0, tzinfo=UTC),
        datetime(2026, 1, 2, 1, 30, tzinfo=UTC),
    ]

    selected_fc = pd.DataFrame(
        {
            "startTime": times,
            "generation": [80.0, 160.0, np.nan, 150.0],
        }
    )
    actuals = pd.DataFrame(
        {
            "startTime": times,
            "generation": [100.0, 200.0, 150.0, 150.0],
        }
    )

    joined = join_forecasts_with_actuals(selected_fc, actuals)
    hourly: list[HourlyMetrics] = calculate_hourly_metrics(joined)

    assert len(hourly) == 24

    # Hour 0
    h0 = hourly[0]
    assert h0.hour == 0
    assert h0.total_count == 2
    assert h0.valid_count == 2
    assert h0.missing_count == 0
    assert h0.mae == 30.0
    assert h0.bias == 30.0
    assert h0.rmse is not None
    assert math.isclose(h0.rmse, math.sqrt(1000.0), rel_tol=1e-6)

    # Hour 1
    h1 = hourly[1]
    assert h1.hour == 1
    assert h1.total_count == 2
    assert h1.valid_count == 1
    assert h1.missing_count == 1
    assert h1.mae == 0.0
    assert h1.bias == 0.0
    assert h1.rmse == 0.0

    # Hours 2-23 are empty but present
    for h in hourly[2:]:
        assert h.total_count == 0
        assert h.valid_count == 0
        assert h.missing_count == 0
        assert h.mae is None


def test_horizon_metrics_hand_calculated() -> None:
    """Verify metrics by forecast horizon bucket using all forecasts.

    Setup:
      - Forecast 1: publish 00:00, start 03:00 -> horizon = 3.0h (bucket "0-6h")
        Forecast = 100.0, Actual = 130.0 -> Error = +30.0
      - Forecast 2: publish 00:00, start 10:00 -> horizon = 10.0h (bucket "6-12h")
        Forecast = 200.0, Actual = 160.0 -> Error = -40.0
      - Forecast 3: publish 00:00, start 20:00 -> horizon = 20.0h (bucket "12-24h")
        Forecast = 300.0, Actual = NaN (missing actual) -> Missing!
    Expected:
      - Bucket "0-6h": total=1, valid=1, missing=0, MAE=30.0, Bias=+30.0, RMSE=30.0
      - Bucket "6-12h": total=1, valid=1, missing=0, MAE=40.0, Bias=-40.0, RMSE=40.0
      - Bucket "12-24h": total=1, valid=0, missing=1, metrics=None
    """
    pub = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 3, 0, tzinfo=UTC)  # 3.0h horizon
    t2 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)  # 10.0h horizon
    t3 = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)  # 20.0h horizon

    all_forecasts = pd.DataFrame(
        [
            {"startTime": t1, "publishTime": pub, "generation": 100.0},
            {"startTime": t2, "publishTime": pub, "generation": 200.0},
            {"startTime": t3, "publishTime": pub, "generation": 300.0},
        ]
    )

    actuals = pd.DataFrame(
        [
            {"startTime": t1, "generation": 130.0},
            {"startTime": t2, "generation": 160.0},
            {"startTime": t3, "generation": np.nan},  # Missing actual
        ]
    )

    horizon_results: list[HorizonMetrics] = calculate_horizon_metrics(
        all_forecasts, actuals
    )

    lookup: dict[str, HorizonMetrics] = {b.bucket: b for b in horizon_results}

    b_0_6 = lookup["0-6h"]
    assert b_0_6.total_count == 1
    assert b_0_6.valid_count == 1
    assert b_0_6.missing_count == 0
    assert b_0_6.mae == 30.0
    assert b_0_6.bias == 30.0
    assert b_0_6.rmse == 30.0
    assert b_0_6.p50 == 30.0

    b_6_12 = lookup["6-12h"]
    assert b_6_12.total_count == 1
    assert b_6_12.valid_count == 1
    assert b_6_12.missing_count == 0
    assert b_6_12.mae == 40.0
    assert b_6_12.bias == -40.0
    assert b_6_12.rmse == 40.0
    assert b_6_12.p50 == 40.0

    b_12_24 = lookup["12-24h"]
    assert b_12_24.total_count == 1
    assert b_12_24.valid_count == 0
    assert b_12_24.missing_count == 1
    assert b_12_24.mae is None

    b_24_36 = lookup["24-36h"]
    assert b_24_36.total_count == 0
    assert b_24_36.valid_count == 0
    assert b_24_36.missing_count == 0
    assert b_24_36.mae is None
