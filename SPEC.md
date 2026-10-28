# Technical Specification: GB Wind Generation Forecast Analysis & Benchmark

## 1. Executive Summary & Objective

This project provides an automated, reproducible benchmark of Great Britain (GB) national wind generation forecasts against actual metered generation. It simulates the operational perspective of an energy trader or portfolio manager making day-ahead power purchase decisions.

The application calculates standard forecast performance metrics, analyzes error profiles across diurnal cycles and forecast horizons, and presents results through an interactive web interface.

---

## 2. Scope & Delivery Timeline

- **Decision Horizon**: Day-ahead purchase decisions made on Day $D - 1$ for power delivered across the 48 half-hourly settlement periods of Day $D$.
- **Default Baseline Period**:
  - **Purchase Decision Window**: 1 January 2026 to 31 January 2026.
  - **Delivery Days**: 2 January 2026 to 1 February 2026 (inclusive).
- **Configurability**:
  - The delivery date range (`startDate` to `endDate`) must be fully configurable via both the backend REST API query parameters and frontend UI date pickers.
  - Defaulting to `2026-01-02` through `2026-02-01` when unspecified.

---

## 3. Data Sources

The system integrates exclusively with Elexon Insights Solution (BMRS) APIs:

1. **Actual Outturn Generation**:
   - **Dataset**: `FUELHH` (Half-Hourly Generation by Fuel Type).
   - **Filter**: Strictly filtered where `fuelType == "WIND"`.
   - **Data Granularity**: Half-hourly settlement periods (MW average generation).
2. **Forecast Wind Generation**:
   - **Dataset**: `WINDFOR` (Wind Generation Forecast).
   - **Filter/Scope**: National aggregated wind generation forecasts.
   - **Fields Used**: `startTime`, `publishTime`, `generation` (MW).
3. **Exclusion Constraint**:
   - Strictly `FUELHH` and `WINDFOR`. No third-party weather data or external price models will be used.

---

## 4. Forecast Selection Logic ("Latest Available Forecast")

For each target half-hour (delivery interval) on delivery day $D$:

1. **Cutoff Rule**:
   - Let target half-hour have delivery date $D$ and start time $T_{\text{start}}$.
   - The decision cutoff timestamp $T_{\text{cutoff}}$ is established on day $D - 1$.
   - **Default Cutoff Time**: `09:00` UK local time on Day $D - 1$.
   - **Cutoff Configurability**: The cutoff time (e.g., `09:00`, `12:00`, `17:00`) must be adjustable via API query parameters and selectable via a UI control.
2. **Selection Criterion**:
   - Identify all forecast records in `WINDFOR` where:
     - Target delivery interval matches the target half-hour (`startTime == target_start_time`).
     - Publication time satisfies: $\text{publishTime} \le T_{\text{cutoff}}$.
   - Select the single record with the **maximum (greatest)** $\text{publishTime}$ satisfying this condition.
3. **Timezone Policy**:
   - All internal comparisons and storage are executed in timezone-aware UTC.
   - The user-facing cutoff input (e.g. `09:00 UK time`) is translated to UTC based on the prevailing UK local time (GMT = UTC+0 in January; BST = UTC+1 during summer).
4. **Resolution Matching Policy (Hourly Block Step-Hold)**:
   - **Empirical Market Context**: Elexon `WINDFOR` broadcasts national forecasts as hourly average MW blocks (`:00` start times only), whereas GB physical imbalance settlement and `FUELHH` actuals operate on half-hourly settlement periods (`:00` and `:30`).
   - **Hourly Block Semantics**: An hourly forecast for clock hour $H$ represents the continuous expected rate of generation covering both constituent settlement periods: Period 1 ($H:00 - H:30$) and Period 2 ($H:30 - (H+1):00$).
   - **Step-Hold Algorithm**:
     - For each target delivery half-hour $T$:
       - If a direct published forecast exists where $\text{publishTime} \le T_{\text{cutoff}}$, it is selected directly with `is_derived = False` and `forecast_type = 'published'`.
       - If no direct forecast exists and $T$ occurs at minute `:30`: it inherits the latest forecast $\le T_{\text{cutoff}}$ of the preceding `:00` settlement period ($T - 30\text{min}$) belonging to that clock hour block, annotated with `is_derived = True` and `forecast_type = 'step_hold'`.
       - If the preceding `:00` period itself has no valid forecast $\le T_{\text{cutoff}}$, both `:00` and `:30` remain missing (`is_missing = True`, `is_derived = False`, `forecast_type = 'missing'`).
     - Directly published `:30` forecasts (if ever present in future Elexon releases) strictly take precedence over step-hold.
     - Step-hold can be optionally disabled via `step_hold: bool = False` in service invocations to inspect raw published coverage.
   - **API Schema Contract**:
     - `ForecastItem` and `CompareItem` models return `isDerived: bool` and `forecastType: "published" | "step_hold" | "missing"`.
   - **UI Presentation & Labeling**:
     - Decision profile line chart displays distinct visual markers: solid cyan dots for published `:00` forecasts, and violet filled dots for step-hold derived `:30` forecasts.
     - Interactive tooltips explicitly indicate data provenance: `Forecast Source: Published WINDFOR Run` vs `Forecast Source: Step-Hold Derived (:00 Block)`.
     - Cutoff Coverage KPI card displays `{validCount} / 48` with breakdown `{publishedCount} published (:00) + {derivedCount} step-hold (:30)`.
     - An informational banner on the Decision page details the step-hold methodology to provide transparency to energy traders and portfolio managers.

---

## 5. Error Definition & Performance Metrics

### 5.1 Error Definition

For each target settlement period $i$:

$$\text{Error}_i = \text{Actual}_i - \text{Forecast}_i$$

- **Positive Error ($\text{Error}_i > 0$)**: Actual generation exceeded forecast (under-forecast; excess physical supply).
- **Negative Error ($\text{Error}_i < 0$)**: Actual generation fell short of forecast (over-forecast; physical shortfall).

### 5.2 Core Benchmark Metrics

Across $N$ evaluated half-hourly intervals:

1. **Mean Absolute Error (MAE)**:
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^{N} |\text{Error}_i| \quad (\text{MW})$$

2. **Root Mean Square Error (RMSE)**:
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (\text{Error}_i)^2} \quad (\text{MW})$$

3. **Bias (Mean Error)**:
   $$\text{Bias} = \frac{1}{N} \sum_{i=1}^{N} \text{Error}_i \quad (\text{MW})$$

4. **Normalised MAE (nMAE)**:
   $$\text{nMAE} = \frac{\text{MAE}}{\overline{\text{Actual}}} = \frac{\frac{1}{N} \sum_{i=1}^{N} |\text{Error}_i|}{\frac{1}{N} \sum_{i=1}^{N} \text{Actual}_i} \times 100\%$$
   *(Evaluated as a percentage of average actual wind generation over the period).*

5. **Absolute Error Percentiles**:
   - **P50 (Median Absolute Error)**: 50th percentile of $|\text{Error}_i|$.
   - **P90**: 90th percentile of $|\text{Error}_i|$.
   - **P95**: 95th percentile of $|\text{Error}_i|$.

---

## 6. Extended Dimensional Analysis

To provide actionable trading and forecasting insights, the backend calculates and the frontend displays:

1. **Error Profile by Hour of Day**:
   - Grouping errors into 24 hour buckets (00:00 to 23:00 UK local time).
   - Metrics per hour: MAE, Bias, RMSE, and median actual vs. forecast.
   - Identifies diurnal forecast drift (e.g., morning ramp-up vs. evening peak).

2. **Error Profile by Forecast Horizon**:
   - Forecast Horizon definition:
     $$\text{Horizon (hours)} = \frac{\text{startTime} - \text{publishTime}}{3600 \text{ seconds}}$$
   - Evaluates forecast degradation as the time between forecast publication and physical power delivery increases.
   - Grouped into hourly or bucketed horizon ranges to visualize horizon-dependent variance.

---

## 7. Architectural Requirements

- **Backend Architecture**:
  - Python 3.12, FastAPI, pandas, pytest, ruff.
  - Strict type hints throughout; no untyped functions.
  - Every API endpoint returns a strongly-validated Pydantic model.
  - Core data transformation and metric calculations are isolated in small, pure service functions with full unit test coverage.
- **Frontend Architecture**:
  - Vite, React, strict TypeScript.
  - Interactive parameter controls: Date Range Picker, Cutoff Time Selector.
  - Responsive visual dashboard displaying KPI summary cards, time series comparison charts, hour-of-day error bar/line charts, and forecast horizon distribution plots.

---

## 8. Open Questions & Risks

### 8.1 Open Questions
1. **Missing or Delayed Forecasts**:
   - If no forecast was published prior to the Day $D - 1$ cutoff for a specific half-hour, how should the interval be treated? (e.g., fallback to the previous available forecast run, mark interval as missing, or exclude from aggregate error metrics?).
2. **Cutoff vs. Publication Latency**:
   - `publishTime` represents the generation timestamp recorded by the forecasting vendor/Elexon. Does market availability match `publishTime`, or is there ingestion latency that should be accommodated?
3. **Handling of Balancing Mechanism (BM) Curtailment**:
   - `FUELHH` reflects actual metered outturn, which may be lowered by National Grid ESO wind curtailment / Bid-Offer Acceptances (BOAs). Does the forecast benchmark evaluate unconstrained potential or actual metered volume? (Per scope: pure `FUELHH` metered wind is used).
4. **Data Caching & Rate Limits**:
   - Elexon API response sizes for full months of half-hourly data: Should data be persistently cached locally (e.g., parquet or SQLite) to avoid hitting Elexon rate limits and improve dashboard response times?

### 8.2 Risks & Mitigation
1. **API Rate Limiting / Timeout on Bulk Ingestion**:
   - *Risk*: Fetching full month intervals of `WINDFOR` and `FUELHH` simultaneously may trigger rate limits or client timeouts.
   - *Mitigation*: Implement chunked fetching, resilient retry with exponential backoff, and local caching.
2. **Schema Drift / Inconsistent Elexon Column Names**:
   - *Risk*: Differences in field naming between BMRS legacy and Elexon Insights API (e.g., `settlementDate` vs `startTime`, `quantity` vs `generation`).
   - *Mitigation*: Fetch and inspect real sample payloads directly from the live API before locking schema mappings; write schema validation unit tests.
3. **Daylight Saving Time Transitions**:
   - *Risk*: Non-48 settlement period days (46 or 50 periods) during clock changes.
   - *Mitigation*: Internal calculations strictly use UTC timestamps; settlement period indices are preserved without assuming a fixed 48 periods per calendar day when custom date ranges cross DST.

---

## 9. Data Observations

Empirical analysis of the ingested January 2026 datasets ([actuals.parquet](file:///c:/Users/mayan/OneDrive/Desktop/Gridbricks%20Assignment/backend/data/actuals.parquet) and [forecasts.parquet](file:///c:/Users/mayan/OneDrive/Desktop/Gridbricks%20Assignment/backend/data/forecasts.parquet)) generated using [inspect_data.py](file:///c:/Users/mayan/OneDrive/Desktop/Gridbricks%20Assignment/backend/scripts/inspect_data.py):

### 9.1 Forecast Horizon Range
- **Minimum Forecast Horizon**: **-25.50 hours**
- **Maximum Forecast Horizon**: **+66.50 hours**
- **Horizon Distribution**:
  - 25th percentile: `3.50` hours
  - Median (P50): `21.50` hours
  - Mean: `21.50` hours
  - 75th percentile: `39.50` hours
- **Context**: The negative minimum horizon reflects retrospective/nowcast data included in each publication run (historical points for the preceding ~25 hours relative to `publishTime`). The forward forecast horizon spans up to 66.5 hours ahead (~2.75 days).

### 9.2 Publication Frequency (`publishTime`)
- **Cadence**: Exactly **8 distinct publication runs per day** across every single day in the dataset (mean = 8.0, min = 8, max = 8).
- **Publication Times**: Published roughly every 3 hours at consistent intervals: `02:30`, `04:30`, `07:30`, `09:30`, `11:30` (or `12:25`), `15:30`, `18:30`, and `22:30` UTC.
- **Run Scope**: Each publication batch contains 73 hourly projection points.

### 9.3 Forecast Availability at Day D-1 09:00 UK Cutoff
- **Evaluated Scope**: 2 January 2026 to 1 February 2026 (31 delivery days $\times$ 48 settlement periods = 1,488 target half-hours).
- **Key Empirical Discovery (Temporal Granularity)**:
  - `WINDFOR` forecasts in Elexon are published at **hourly resolution** (`:00` start times only; 0 points at `:30`).
  - `FUELHH` actuals are recorded at **half-hourly resolution** (`:00` and `:30`).
- **Availability Findings**:
  - **Raw Exact Match**: **744 half-hours covered (50.0%)** and **744 half-hours missing (50.0%)**, with missing intervals consisting exclusively of half-hour `:30` timestamps.
  - **Hourly Resolution Match**: **744 / 744 hours covered (100.0%)**. For every delivery day, the `07:30` UTC run on Day $D-1$ (the latest run prior to the `09:00` cutoff) reliably provides forecasts for all 24 hours of Day $D$.
- **Architectural Resolution**: Formally implemented the **Hourly Block Step-Hold (Carry-Forward)** policy in `forecast_selection.py`. Each `:30` settlement period inherits the `:00` forecast of its clock hour with explicit source attribution (`is_derived = True`, `forecast_type = 'step_hold'`). Direct `:30` forecasts take precedence if published, and periods remain missing if `:00` is missing. This provides 100% complete 48-period day-ahead scheduling with transparent UI labeling.

### 9.4 Actuals Continuity & Data Integrity (`FUELHH` Wind)
- **Dataset Size**: 1,584 rows covering 1 January 2026 00:00:00 UTC through 2 February 2026 23:30:00 UTC (33 full delivery days $\times$ 48 settlement periods).
- **Duplicates**: **0 duplicate timestamps** (`startTime` is strictly unique).
- **Sequence Continuity**: **0 sequence gaps**; exactly 30 minutes between every consecutive record across the entire 33-day span (100% complete time series).
- **Outturn Range**: Min = `1,695.0 MW`, Max = `17,805.0 MW`, Mean = `11,437.6 MW`.

