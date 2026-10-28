"""Unit tests for the DataRepository service and schema validation."""

from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest

from app.core.repository import (
    DataFileNotFoundError,
    DataRepository,
    DataSchemaValidationError,
)


@pytest.fixture
def sample_actuals_df() -> pd.DataFrame:
    """Fixture providing valid actual outturn records."""
    return pd.DataFrame(
        {
            "startTime": [
                datetime(2026, 1, 2, 0, 0, tzinfo=UTC),
                datetime(2026, 1, 2, 0, 30, tzinfo=UTC),
            ],
            "publishTime": [
                datetime(2026, 1, 2, 0, 30, tzinfo=UTC),
                datetime(2026, 1, 2, 1, 0, tzinfo=UTC),
            ],
            "generation": [12000.0, 12500.0],
        }
    )


@pytest.fixture
def sample_forecasts_df() -> pd.DataFrame:
    """Fixture providing valid wind forecast records."""
    return pd.DataFrame(
        {
            "startTime": [
                datetime(2026, 1, 2, 0, 0, tzinfo=UTC),
                datetime(2026, 1, 2, 1, 0, tzinfo=UTC),
            ],
            "publishTime": [
                datetime(2026, 1, 1, 8, 30, tzinfo=UTC),
                datetime(2026, 1, 1, 8, 30, tzinfo=UTC),
            ],
            "generation": [11500.0, 11800.0],
        }
    )


def test_repository_load_and_read_only_accessors(
    tmp_path: Path,
    sample_actuals_df: pd.DataFrame,
    sample_forecasts_df: pd.DataFrame,
) -> None:
    """Verify repository loading, counts, and read-only accessor outputs."""
    sample_actuals_df.to_parquet(tmp_path / "actuals.parquet", index=False)
    sample_forecasts_df.to_parquet(tmp_path / "forecasts.parquet", index=False)

    repo = DataRepository(data_dir=tmp_path)
    assert not repo.is_loaded

    repo.load()
    assert repo.is_loaded
    assert repo.actuals_count == 2
    assert repo.forecasts_count == 2

    act_copy = repo.get_actuals()
    fc_copy = repo.get_forecasts()

    assert len(act_copy) == 2
    assert len(fc_copy) == 2
    assert list(act_copy["generation"]) == [12000.0, 12500.0]
    assert list(fc_copy["generation"]) == [11500.0, 11800.0]


def test_repository_fails_when_actuals_missing(
    tmp_path: Path,
    sample_forecasts_df: pd.DataFrame,
) -> None:
    """Verify clear error message when actuals.parquet is missing."""
    sample_forecasts_df.to_parquet(tmp_path / "forecasts.parquet", index=False)

    repo = DataRepository(data_dir=tmp_path)
    with pytest.raises(DataFileNotFoundError, match="actuals.parquet"):
        repo.load()


def test_repository_fails_when_forecasts_missing(
    tmp_path: Path,
    sample_actuals_df: pd.DataFrame,
) -> None:
    """Verify clear error message when forecasts.parquet is missing."""
    sample_actuals_df.to_parquet(tmp_path / "actuals.parquet", index=False)

    repo = DataRepository(data_dir=tmp_path)
    with pytest.raises(DataFileNotFoundError, match="forecasts.parquet"):
        repo.load()


def test_repository_fails_when_directory_does_not_exist(tmp_path: Path) -> None:
    """Verify clear error message when the data directory itself is absent."""
    non_existent = tmp_path / "missing_dir"
    repo = DataRepository(data_dir=non_existent)

    with pytest.raises(DataFileNotFoundError, match="does not exist"):
        repo.load()


def test_repository_schema_validation_missing_columns(
    tmp_path: Path,
    sample_forecasts_df: pd.DataFrame,
) -> None:
    """Verify schema validation error when required columns are absent."""
    invalid_actuals = pd.DataFrame(
        {
            "startTime": [datetime(2026, 1, 2, 0, 0, tzinfo=UTC)],
            # 'generation' column intentionally missing
        }
    )
    invalid_actuals.to_parquet(tmp_path / "actuals.parquet", index=False)
    sample_forecasts_df.to_parquet(tmp_path / "forecasts.parquet", index=False)

    repo = DataRepository(data_dir=tmp_path)
    with pytest.raises(DataSchemaValidationError, match="missing required columns"):
        repo.load()


def test_repository_schema_validation_non_numeric_generation(
    tmp_path: Path,
    sample_forecasts_df: pd.DataFrame,
) -> None:
    """Verify schema validation error when generation is not numeric."""
    invalid_actuals = pd.DataFrame(
        {
            "startTime": [datetime(2026, 1, 2, 0, 0, tzinfo=UTC)],
            "generation": ["not-a-number"],
        }
    )
    invalid_actuals.to_parquet(tmp_path / "actuals.parquet", index=False)
    sample_forecasts_df.to_parquet(tmp_path / "forecasts.parquet", index=False)

    repo = DataRepository(data_dir=tmp_path)
    with pytest.raises(DataSchemaValidationError, match="must be numeric"):
        repo.load()


def test_repository_defensive_copy_immutability(
    tmp_path: Path,
    sample_actuals_df: pd.DataFrame,
    sample_forecasts_df: pd.DataFrame,
) -> None:
    """Verify that mutating a returned dataframe copy does not alter state."""
    sample_actuals_df.to_parquet(tmp_path / "actuals.parquet", index=False)
    sample_forecasts_df.to_parquet(tmp_path / "forecasts.parquet", index=False)

    repo = DataRepository(data_dir=tmp_path)
    repo.load()

    first_view = repo.get_actuals()
    # Mutate the copy
    first_view["generation"] = 0.0

    # Fresh copy should remain uncorrupted
    fresh_view = repo.get_actuals()
    assert list(fresh_view["generation"]) == [12000.0, 12500.0]


def test_repository_date_range_filtering_and_slice_copy(tmp_path: Path) -> None:
    """Verify repository date range filtering and copy of the filtered slice only."""
    multi_day_actuals = pd.DataFrame(
        {
            "startTime": [
                datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
                datetime(2026, 1, 3, 12, 0, tzinfo=UTC),
                datetime(2026, 1, 4, 12, 0, tzinfo=UTC),
            ],
            "generation": [1000.0, 2000.0, 3000.0, 4000.0],
        }
    )
    multi_day_forecasts = pd.DataFrame(
        {
            "startTime": [
                datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
                datetime(2026, 1, 3, 12, 0, tzinfo=UTC),
                datetime(2026, 1, 4, 12, 0, tzinfo=UTC),
            ],
            "publishTime": [
                datetime(2025, 12, 31, 8, 0, tzinfo=UTC),
                datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
                datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
                datetime(2026, 1, 3, 8, 0, tzinfo=UTC),
            ],
            "generation": [1100.0, 2100.0, 3100.0, 4100.0],
        }
    )
    multi_day_actuals.to_parquet(tmp_path / "actuals.parquet", index=False)
    multi_day_forecasts.to_parquet(tmp_path / "forecasts.parquet", index=False)

    repo = DataRepository(data_dir=tmp_path)
    repo.load()

    # Total rows in full dataset is 4
    assert repo.actuals_count == 4
    assert repo.forecasts_count == 4

    # Filter single day (2026-01-02)
    act_slice = repo.get_actuals(
        start_date=date(2026, 1, 2), end_date=date(2026, 1, 2)
    )
    fc_slice = repo.get_forecasts(
        start_date=date(2026, 1, 2), end_date=date(2026, 1, 2)
    )

    assert len(act_slice) == 1
    assert len(fc_slice) == 1
    assert act_slice["generation"].iloc[0] == 2000.0
    assert fc_slice["generation"].iloc[0] == 2100.0

    # Mutate slice to verify copy behaviour
    act_slice["generation"] = -999.0
    fc_slice["generation"] = -999.0

    # Fresh slice is uncorrupted
    fresh_act = repo.get_actuals(
        start_date=date(2026, 1, 2), end_date=date(2026, 1, 2)
    )
    assert fresh_act["generation"].iloc[0] == 2000.0

    # Multi-day range (2026-01-02 to 2026-01-03)
    range_act = repo.get_actuals(
        start_date=date(2026, 1, 2), end_date=date(2026, 1, 3)
    )
    assert len(range_act) == 2
    assert list(range_act["generation"]) == [2000.0, 3000.0]

