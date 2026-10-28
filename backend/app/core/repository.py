"""Data repository for cached read-only access to Parquet datasets."""

from datetime import date
from pathlib import Path
from typing import ClassVar, Final
from zoneinfo import ZoneInfo

import pandas as pd

from app.core.config import settings

UK_TZ: Final[ZoneInfo] = ZoneInfo("Europe/London")


class DataFileNotFoundError(FileNotFoundError):
    """Raised when a required data file is missing from the data directory."""

    pass


class DataSchemaValidationError(ValueError):
    """Raised when a data file does not conform to the expected schema."""

    pass


class DataRepository:
    """Repository managing validated read-only access to actuals and forecasts.

    Loads and validates Parquet files once at startup, caching them in memory
    for fast access across API requests.
    """

    _instance: ClassVar["DataRepository | None"] = None

    REQUIRED_ACTUALS_COLUMNS: ClassVar[set[str]] = {"startTime", "generation"}
    REQUIRED_FORECASTS_COLUMNS: ClassVar[set[str]] = {
        "startTime",
        "publishTime",
        "generation",
    }

    def __init__(self, data_dir: Path | None = None) -> None:
        """Initialize repository pointing to target data directory.

        Args:
            data_dir: Path to folder containing actuals.parquet and
                forecasts.parquet. Defaults to settings.data_dir.
        """
        self.data_dir: Path = data_dir if data_dir is not None else settings.data_dir
        self.actuals_path: Path = self.data_dir / "actuals.parquet"
        self.forecasts_path: Path = self.data_dir / "forecasts.parquet"

        self._actuals_df: pd.DataFrame | None = None
        self._forecasts_df: pd.DataFrame | None = None
        self._is_loaded: bool = False

    @property
    def is_loaded(self) -> bool:
        """Return True if both datasets have been successfully loaded and validated."""
        return self._is_loaded

    @property
    def actuals_count(self) -> int:
        """Return total row count of cached actuals."""
        if self._actuals_df is None:
            self.load()
        assert self._actuals_df is not None
        return len(self._actuals_df)

    @property
    def forecasts_count(self) -> int:
        """Return total row count of cached forecasts."""
        if self._forecasts_df is None:
            self.load()
        assert self._forecasts_df is not None
        return len(self._forecasts_df)

    def check_files_exist(self) -> None:
        """Verify presence of required Parquet files; raise clear error if missing."""
        if not self.data_dir.exists():
            raise DataFileNotFoundError(
                f"Data directory '{self.data_dir}' does not exist. "
                "Please run 'python backend/scripts/fetch_data.py' to download data."
            )

        if not self.actuals_path.is_file():
            raise DataFileNotFoundError(
                f"Required dataset 'actuals.parquet' was not found at "
                f"'{self.actuals_path}'. "
                "Please run 'python backend/scripts/fetch_data.py' to download data."
            )

        if not self.forecasts_path.is_file():
            raise DataFileNotFoundError(
                f"Required dataset 'forecasts.parquet' was not found at "
                f"'{self.forecasts_path}'. "
                "Please run 'python backend/scripts/fetch_data.py' to download data."
            )

    def _validate_actuals_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate required columns and types for actual outturn dataset."""
        missing = self.REQUIRED_ACTUALS_COLUMNS - set(df.columns)
        if missing:
            raise DataSchemaValidationError(
                f"Dataset '{self.actuals_path.name}' is missing required columns: "
                f"{sorted(missing)}. Found: {list(df.columns)}"
            )

        validated: pd.DataFrame = df.copy()
        try:
            validated["startTime"] = pd.to_datetime(validated["startTime"], utc=True)
        except Exception as e:
            raise DataSchemaValidationError(
                f"Failed to parse 'startTime' column as UTC datetimes in "
                f"{self.actuals_path.name}: {e}"
            ) from e

        if not pd.api.types.is_numeric_dtype(validated["generation"]):
            raise DataSchemaValidationError(
                f"Column 'generation' in {self.actuals_path.name} must be numeric, "
                f"got {validated['generation'].dtype}"
            )

        return validated

    def _validate_forecasts_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate required columns and types for wind forecasts dataset."""
        missing = self.REQUIRED_FORECASTS_COLUMNS - set(df.columns)
        if missing:
            raise DataSchemaValidationError(
                f"Dataset '{self.forecasts_path.name}' is missing required columns: "
                f"{sorted(missing)}. Found: {list(df.columns)}"
            )

        validated: pd.DataFrame = df.copy()
        try:
            validated["startTime"] = pd.to_datetime(validated["startTime"], utc=True)
            validated["publishTime"] = pd.to_datetime(
                validated["publishTime"], utc=True
            )
        except Exception as e:
            raise DataSchemaValidationError(
                f"Failed to parse datetime columns in {self.forecasts_path.name}: {e}"
            ) from e

        if not pd.api.types.is_numeric_dtype(validated["generation"]):
            raise DataSchemaValidationError(
                f"Column 'generation' in {self.forecasts_path.name} must be numeric, "
                f"got {validated['generation'].dtype}"
            )

        return validated

    def load(self) -> None:
        """Load and validate both Parquet datasets once into memory."""
        self.check_files_exist()

        try:
            raw_actuals = pd.read_parquet(self.actuals_path)
            self._actuals_df = self._validate_actuals_schema(raw_actuals)
        except (DataSchemaValidationError, DataFileNotFoundError):
            raise
        except Exception as e:
            raise DataSchemaValidationError(
                f"Failed reading parquet file '{self.actuals_path}': {e}"
            ) from e

        try:
            raw_forecasts = pd.read_parquet(self.forecasts_path)
            self._forecasts_df = self._validate_forecasts_schema(raw_forecasts)
        except (DataSchemaValidationError, DataFileNotFoundError):
            raise
        except Exception as e:
            raise DataSchemaValidationError(
                f"Failed reading parquet file '{self.forecasts_path}': {e}"
            ) from e

        self._is_loaded = True

    def get_actuals(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        copy: bool = True,
    ) -> pd.DataFrame:
        """Return read-only access to cached actuals dataset.

        Filters by delivery date range first on UK local time, copying only
        the filtered slice to avoid full dataframe memory duplication.

        Args:
            start_date: Optional start delivery date to filter by (inclusive).
            end_date: Optional end delivery date to filter by (inclusive).
            copy: If True (default), returns a defensive copy of the slice to
                prevent external mutations of repository state.

        Returns:
            DataFrame containing validated actual outturn average power in MW
            over a half hour (not energy in MWh).
        """
        if self._actuals_df is None:
            self.load()
        assert self._actuals_df is not None

        df = self._actuals_df
        if start_date is not None or end_date is not None:
            delivery_dates = df["startTime"].dt.tz_convert(UK_TZ).dt.date
            mask = pd.Series(True, index=df.index)
            if start_date is not None:
                mask &= delivery_dates >= start_date
            if end_date is not None:
                mask &= delivery_dates <= end_date
            df = df[mask]

        return df.copy() if copy else df

    def get_forecasts(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        copy: bool = True,
    ) -> pd.DataFrame:
        """Return read-only access to cached forecasts dataset.

        Filters by delivery date range first on UK local time, copying only
        the filtered slice to avoid full dataframe memory duplication.

        Args:
            start_date: Optional start delivery date to filter by (inclusive).
            end_date: Optional end delivery date to filter by (inclusive).
            copy: If True (default), returns a defensive copy of the slice to
                prevent external mutations of repository state.

        Returns:
            DataFrame containing validated wind forecast average power in MW
            over a half hour (not energy in MWh).
        """
        if self._forecasts_df is None:
            self.load()
        assert self._forecasts_df is not None

        df = self._forecasts_df
        if start_date is not None or end_date is not None:
            delivery_dates = df["startTime"].dt.tz_convert(UK_TZ).dt.date
            mask = pd.Series(True, index=df.index)
            if start_date is not None:
                mask &= delivery_dates >= start_date
            if end_date is not None:
                mask &= delivery_dates <= end_date
            df = df[mask]

        return df.copy() if copy else df

    @classmethod
    def get_instance(cls, data_dir: Path | None = None) -> "DataRepository":
        """Get or create singleton DataRepository instance."""
        needs_new_instance = cls._instance is None or (
            data_dir is not None and cls._instance.data_dir != data_dir
        )
        if needs_new_instance:
            cls._instance = cls(data_dir=data_dir)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (useful between isolated test runs)."""
        cls._instance = None
