"""Elexon BMRS data ingestion script for FUELHH actuals and WINDFOR forecasts.

Downloads January 2026 data with a historical buffer, filters, normalizes UTC
timestamps, and persists cleanly formatted Parquet files.
"""

import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

BASE_URL: str = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
DEFAULT_TIMEOUT: float = 60.0
MAX_RETRIES: int = 5
INITIAL_DELAY: float = 1.0
BACKOFF_FACTOR: float = 2.0


def fetch_with_retry(
    client: httpx.Client,
    endpoint: str,
    params: dict[str, Any],
    max_retries: int = MAX_RETRIES,
    initial_delay: float = INITIAL_DELAY,
    backoff_factor: float = BACKOFF_FACTOR,
) -> list[dict[str, Any]]:
    """Execute GET request with exponential backoff retry on transient errors.

    Args:
        client: Pre-configured httpx Client instance.
        endpoint: API dataset path (e.g., 'FUELHH/stream' or 'WINDFOR/stream').
        params: URL query parameters.
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial sleep duration in seconds before first retry.
        backoff_factor: Multiplier for subsequent backoff intervals.

    Returns:
        List of deserialized JSON dictionary records.

    Raises:
        httpx.HTTPStatusError: If max retries are exceeded with HTTP error.
        httpx.RequestError: If max retries are exceeded with network failure.
    """
    url: str = f"{BASE_URL}/{endpoint}"
    delay: float = initial_delay

    for attempt in range(1, max_retries + 1):
        try:
            response: httpx.Response = client.get(url, params=params)
            response.raise_for_status()
            data: Any = response.json()
            if isinstance(data, list):
                return data
            if (
                isinstance(data, dict)
                and "data" in data
                and isinstance(data["data"], list)
            ):
                return data["data"]
            return []
        except (httpx.HTTPStatusError, httpx.RequestError) as err:
            if attempt == max_retries:
                print(f"[ERROR] Max retries ({max_retries}) reached for {url}: {err}")
                raise
            # Check for 429 Retry-After header if available
            wait_time: float = delay
            if (
                isinstance(err, httpx.HTTPStatusError)
                and err.response.status_code == 429
            ):
                retry_after: str | None = err.response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait_time = max(float(retry_after), wait_time)

            print(
                f"[WARN] Attempt {attempt}/{max_retries} failed for {endpoint} "
                f"({err}). Retrying in {wait_time:.1f}s..."
            )
            time.sleep(wait_time)
            delay *= backoff_factor

    return []


def generate_date_chunks(
    start_date: date,
    end_date: date,
    chunk_days: int = 7,
) -> list[tuple[date, date]]:
    """Generate sequential inclusive date intervals of chunk_days size.

    Args:
        start_date: Start date of the overall interval (inclusive).
        end_date: End date of the overall interval (inclusive).
        chunk_days: Maximum number of days per chunk.

    Returns:
        List of (chunk_start, chunk_end) date tuples.
    """
    chunks: list[tuple[date, date]] = []
    current_start: date = start_date

    while current_start <= end_date:
        current_end: date = min(
            current_start + timedelta(days=chunk_days - 1), end_date
        )
        chunks.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)

    return chunks


def fetch_fuelhh_actuals(
    client: httpx.Client,
    start_date: date,
    end_date: date,
    chunk_days: int = 7,
) -> pd.DataFrame:
    """Fetch FUELHH outturn records chunked by settlement date and filter to WIND.

    Args:
        client: Pre-configured httpx Client instance.
        start_date: Starting settlement date.
        end_date: Ending settlement date.
        chunk_days: Chunk span in days for each API request.

    Returns:
        DataFrame with columns ['startTime', 'publishTime', 'generation'] in UTC.
    """
    chunks: list[tuple[date, date]] = generate_date_chunks(
        start_date=start_date,
        end_date=end_date,
        chunk_days=chunk_days,
    )
    all_records: list[dict[str, Any]] = []

    print(
        f"[INFO] Fetching FUELHH actuals from {start_date} to {end_date} in "
        f"{len(chunks)} chunks..."
    )

    for chunk_start, chunk_end in chunks:
        params: dict[str, Any] = {
            "settlementDateFrom": chunk_start.isoformat(),
            "settlementDateTo": chunk_end.isoformat(),
            "fuelType": "WIND",
        }
        records = fetch_with_retry(client, "FUELHH/stream", params=params)
        all_records.extend(records)
        print(f"  - Chunk {chunk_start} to {chunk_end}: {len(records)} records")

    if not all_records:
        return pd.DataFrame(columns=["startTime", "publishTime", "generation"])

    df: pd.DataFrame = pd.DataFrame(all_records)

    # Double check fuelType filtering in python
    if "fuelType" in df.columns:
        df = df[df["fuelType"] == "WIND"].copy()

    # Parse and enforce timezone-aware UTC datetime
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")

    # Keep only requested fields
    df = df[["startTime", "publishTime", "generation"]].dropna(
        subset=["startTime", "generation"]
    )

    # Deduplicate by target settlement start time, keeping latest published record
    df = df.sort_values(by=["startTime", "publishTime"]).drop_duplicates(
        subset=["startTime"], keep="last"
    )
    df = df.reset_index(drop=True)
    return df


def fetch_windfor_forecasts(
    client: httpx.Client,
    publish_start: datetime,
    publish_end: datetime,
    chunk_days: int = 7,
) -> pd.DataFrame:
    """Fetch WINDFOR forecast records chunked by publishDateTime.

    Args:
        client: Pre-configured httpx Client instance.
        publish_start: Earliest publication timestamp to retrieve.
        publish_end: Latest publication timestamp to retrieve.
        chunk_days: Chunk span in days for each API request.

    Returns:
        DataFrame with columns ['startTime', 'publishTime', 'generation'] in UTC.
    """
    all_records: list[dict[str, Any]] = []
    current_start: datetime = publish_start

    total_chunks: int = max(1, (publish_end - publish_start).days // chunk_days + 1)
    print(
        f"[INFO] Fetching WINDFOR forecasts published {publish_start.date()} to "
        f"{publish_end.date()} (~{total_chunks} chunks)..."
    )

    while current_start < publish_end:
        current_end: datetime = min(
            current_start + timedelta(days=chunk_days), publish_end
        )
        params: dict[str, Any] = {
            "publishDateTimeFrom": current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": current_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        records = fetch_with_retry(client, "WINDFOR/stream", params=params)
        all_records.extend(records)
        print(
            f"  - Chunk published {current_start.strftime('%Y-%m-%d %H:%M')} to "
            f"{current_end.strftime('%Y-%m-%d %H:%M')}: {len(records)} records"
        )
        current_start = current_end

    if not all_records:
        return pd.DataFrame(columns=["startTime", "publishTime", "generation"])

    df: pd.DataFrame = pd.DataFrame(all_records)

    # Parse and enforce timezone-aware UTC datetime
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")

    # Keep only requested fields
    df = df[["startTime", "publishTime", "generation"]].dropna(
        subset=["startTime", "publishTime", "generation"]
    )

    # Deduplicate identical publishTime and startTime
    df = df.drop_duplicates(subset=["startTime", "publishTime"]).reset_index(drop=True)
    df = df.sort_values(by=["startTime", "publishTime"]).reset_index(drop=True)
    return df


def display_summary(actuals_df: pd.DataFrame, forecasts_df: pd.DataFrame) -> None:
    """Print structured summary of downloaded data metrics and distributions.

    Args:
        actuals_df: Cleaned actual generation DataFrame.
        forecasts_df: Cleaned forecast generation DataFrame.
    """
    print("\n" + "=" * 80)
    print(" " * 24 + "ELEXON BMRS INGESTION SUMMARY")
    print("=" * 80)

    # Actuals Summary
    print("\n--- ACTUAL OUTTURN (FUELHH: fuelType=WIND) ---")
    print(f"Total Rows:              {len(actuals_df):,}")
    if not actuals_df.empty:
        start_min: pd.Timestamp = actuals_df["startTime"].min()
        start_max: pd.Timestamp = actuals_df["startTime"].max()
        gen_min: float = float(actuals_df["generation"].min())
        gen_max: float = float(actuals_df["generation"].max())
        gen_mean: float = float(actuals_df["generation"].mean())

        print(f"Delivery Range (UTC):    {start_min}  -->  {start_max}")
        print(
            f"Generation (MW):         Min = {gen_min:,.1f} | Max = {gen_max:,.1f} | "
            f"Mean = {gen_mean:,.1f}"
        )

    # Forecasts Summary
    print("\n--- FORECAST GENERATION (WINDFOR) ---")
    print(f"Total Rows:              {len(forecasts_df):,}")
    if not forecasts_df.empty:
        pub_min: pd.Timestamp = forecasts_df["publishTime"].min()
        pub_max: pd.Timestamp = forecasts_df["publishTime"].max()
        target_min: pd.Timestamp = forecasts_df["startTime"].min()
        target_max: pd.Timestamp = forecasts_df["startTime"].max()
        distinct_half_hours: int = int(forecasts_df["startTime"].nunique())

        print(f"Publish Range (UTC):     {pub_min}  -->  {pub_max}")
        print(f"Target Range (UTC):      {target_min}  -->  {target_max}")
        print(f"Unique Target Half-Hrs:  {distinct_half_hours:,}")

        # Forecasts per target half-hour distribution
        counts_per_thh = forecasts_df.groupby("startTime")["publishTime"].count()
        f_min: int = int(counts_per_thh.min())
        f_p25: float = float(counts_per_thh.quantile(0.25))
        f_median: float = float(counts_per_thh.median())
        f_p75: float = float(counts_per_thh.quantile(0.75))
        f_p90: float = float(counts_per_thh.quantile(0.90))
        f_max: int = int(counts_per_thh.max())
        f_mean: float = float(counts_per_thh.mean())

        print("\n--- NUMBER OF FORECASTS PER TARGET HALF-HOUR (startTime) ---")
        print(f"Min:                     {f_min}")
        print(f"25th Percentile:         {f_p25:.1f}")
        print(f"Median (P50):            {f_median:.1f}")
        print(f"75th Percentile:         {f_p75:.1f}")
        print(f"90th Percentile:         {f_p90:.1f}")
        print(f"Max:                     {f_max}")
        print(f"Mean:                    {f_mean:.2f}")

    print("=" * 80 + "\n")


def main() -> None:
    """Orchestrate data fetching, parsing, validation, and storage."""
    # Ensure backend/data directory exists
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    actuals_path: Path = data_dir / "actuals.parquet"
    forecasts_path: Path = data_dir / "forecasts.parquet"

    # Define date windows
    # Actuals: 1 Jan 2026 to 2 Feb 2026 (covers all January delivery days plus buffers)
    actuals_start: date = date(2026, 1, 1)
    actuals_end: date = date(2026, 2, 2)

    # Forecasts: Published between 25 Dec 2025 and 2 Feb 2026 (7-day buffer)
    forecasts_pub_start: datetime = datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC)
    forecasts_pub_end: datetime = datetime(2026, 2, 3, 0, 0, 0, tzinfo=UTC)

    with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        # 1. Ingest FUELHH Actuals
        actuals_df: pd.DataFrame = fetch_fuelhh_actuals(
            client=client,
            start_date=actuals_start,
            end_date=actuals_end,
            chunk_days=7,
        )
        actuals_df.to_parquet(actuals_path, index=False)
        print(f"[SUCCESS] Saved actuals to {actuals_path} ({len(actuals_df):,} rows)")

        # 2. Ingest WINDFOR Forecasts
        forecasts_df: pd.DataFrame = fetch_windfor_forecasts(
            client=client,
            publish_start=forecasts_pub_start,
            publish_end=forecasts_pub_end,
            chunk_days=7,
        )
        forecasts_df.to_parquet(forecasts_path, index=False)
        print(
            f"[SUCCESS] Saved forecasts: {forecasts_path.name} "
            f"({len(forecasts_df):,} rows)"
        )

    # 3. Print Statistical Summary
    display_summary(actuals_df=actuals_df, forecasts_df=forecasts_df)


if __name__ == "__main__":
    main()
