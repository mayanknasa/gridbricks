# Gridbricks Wind Generation Forecast Evaluation & Decision Platform

[![CI](https://github.com/OWNER/REPOSITORY/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPOSITORY/actions/workflows/ci.yml)

An end-to-end power trading analytics and decision support platform that evaluates Great Britain national wind generation forecasts against actual settlement outturn for January 2026. The platform enables power buyers and traders to establish optimal day-ahead physical procurement schedules and calculate data-driven risk buffers to avoid costly Balancing Mechanism (BM) cashout penalties.

---

## Live Application

- **Frontend Application**: [https://gridbricks-wind-forecast.vercel.app](https://gridbricks-wind-forecast.vercel.app) *(Placeholder — deploy via Vercel)*
- **Backend API Service**: [https://gridbricks-backend.onrender.com](https://gridbricks-backend.onrender.com) *(Placeholder — deploy via Render)*
- **Interactive OpenAPI Documentation**: [https://gridbricks-backend.onrender.com/docs](https://gridbricks-backend.onrender.com/docs)

---

## Repository Structure

```text
.
├── .dockerignore                            # Root Docker ignore rules for build caches and environments
├── .gitignore                               # Git ignore patterns for dependencies, venv, and caches
├── AGENTS.md                                # Standing architectural rules, type safety, and development constraints
├── README.md                                # Comprehensive project documentation and operational manual
├── SPEC.md                                  # Technical specification and empirical data observations
├── docker-compose.yml                       # Multi-container orchestration for backend and frontend services
├── render.yaml                              # Infrastructure-as-code Blueprint for Render deployment
├── .github/                                 # GitHub Actions continuous integration workflows
│   └── workflows/
│       └── ci.yml                           # CI workflow running linters, type checks, tests, and Docker builds
├── backend/                                 # FastAPI Python 3.12 backend service
│   ├── .dockerignore                        # Backend Docker build exclusion rules
│   ├── Dockerfile                           # Multi-stage Python 3.12-slim Dockerfile with non-root user and healthcheck
│   ├── Procfile                             # Process declaration for Heroku and Render deployments
│   ├── README.md                            # Backend component overview
│   ├── pyproject.toml                       # Python package dependencies (FastAPI, pandas, pyarrow) and tool configs
│   ├── runtime.txt                          # Python version specification (3.12.9) for cloud buildpacks
│   ├── app/                                 # Application source code
│   │   ├── __init__.py                      # Package initialization
│   │   ├── main.py                          # FastAPI app entrypoint, lifespan startup checks, CORS, and logging
│   │   ├── api/                             # API routing layer
│   │   │   ├── __init__.py                  # API router package initialization
│   │   │   ├── routes.py                    # Root and general system health routes
│   │   │   └── v1/                          # Version 1 API endpoints
│   │   │       ├── __init__.py              # V1 package initialization
│   │   │       └── endpoints.py             # Endpoints: /health, /forecast, /compare, and /metrics variants
│   │   ├── core/                            # Core infrastructure and runtime configuration
│   │   │   ├── __init__.py                  # Core package initialization
│   │   │   ├── config.py                    # Environment settings (PORT, DATA_DIR, CORS origins)
│   │   │   ├── logging_middleware.py        # Structured JSON access logging with X-Request-ID propagation
│   │   │   └── repository.py                # Thread-safe in-memory singleton data repository with schema checks
│   │   ├── models/                          # Pydantic validation and serialization models
│   │   │   ├── __init__.py                  # Models package initialization
│   │   │   ├── api.py                       # Request and response models for forecast, compare, and metrics
│   │   │   ├── health.py                    # Health check and status response models
│   │   │   └── metrics.py                   # Data models for statistical calculations
│   │   └── services/                        # Pure business and data logic engines
│   │       ├── __init__.py                  # Services package initialization
│   │       ├── forecast_selection.py        # Pure function selecting latest forecasts prior to Day D-1 cutoff
│   │       ├── health.py                    # Health check service evaluator
│   │       └── metrics.py                   # Vectorized calculations for MAE, RMSE, Bias, nMAE, P90, and horizons
│   ├── data/                                # Committed January 2026 data snapshots
│   │   ├── actuals.parquet                  # Cleaned half-hourly actual wind generation outturn (FUELHH stream)
│   │   └── forecasts.parquet                # Cleaned published wind forecasts with lead-time horizons (WINDFOR)
│   ├── scripts/                             # Offline ingestion and inspection utilities
│   │   ├── fetch_data.py                    # Resilient Elexon BMRS API downloader with exponential backoff
│   │   └── inspect_data.py                  # Statistical data profiling script for horizon and gap analysis
│   └── tests/                               # Comprehensive Pytest test suite (38 tests)
│       ├── __init__.py                      # Tests package initialization
│       ├── test_api.py                      # Integration tests for all endpoints, validation, request IDs, and CORS
│       ├── test_forecast_selection.py       # Unit tests for cutoff boundary conditions and missing periods
│       ├── test_health.py                   # Unit and integration tests for health monitoring
│       ├── test_metrics.py                  # Unit tests verifying hand-calculated metrics against edge cases
│       └── test_repository.py               # Unit tests verifying parquet schema enforcement and immutability
└── frontend/                                # React 19 + TypeScript + Vite frontend application
    ├── .dockerignore                        # Frontend Docker build exclusion rules
    ├── .gitignore                           # Git ignore patterns for node_modules and build artifacts
    ├── .oxlintrc.json                       # Oxlint linter configuration
    ├── Dockerfile                           # Multi-stage Dockerfile building static assets and serving via Nginx
    ├── README.md                            # Frontend overview and script documentation
    ├── index.html                           # Single-page application HTML entrypoint
    ├── nginx.conf.template                  # Nginx template enabling dynamic ${BACKEND_URL} proxying and SPA rewrites
    ├── package-lock.json                    # Deterministic NPM dependency lockfile
    ├── package.json                         # NPM package scripts and dependencies (React 19, TanStack Query, Recharts)
    ├── tsconfig.app.json                    # Strict TypeScript compiler options for frontend application code
    ├── tsconfig.json                        # Root TypeScript project references configuration
    ├── tsconfig.node.json                   # TypeScript compiler options for Vite tooling
    ├── vercel.json                          # Vercel deployment rewrites for client-side React Router navigation
    ├── vite.config.ts                       # Vite configuration, dev proxy, and Vitest test runner setup
    ├── public/                              # Static public assets
    └── src/                                 # Frontend application source code
        ├── App.css                          # Layout shell and structural styles
        ├── App.tsx                          # App root with navigation header and routing
        ├── index.css                        # Design system with dark theme, glassmorphic cards, and typography
        ├── main.tsx                         # React DOM mount point with QueryClientProvider
        ├── api/                             # Network API client
        │   ├── client.ts                    # Typed fetch wrapper with error normalization and query serialization
        │   └── client.test.ts               # Unit tests for ApiError, status codes, and error detail handling
        ├── components/                      # Reusable user interface components
        │   ├── common/EmptyState.tsx        # Reusable empty data state component
        │   ├── common/ErrorState.tsx        # Reusable error alert with retry button
        │   ├── common/LoadingState.tsx      # Reusable loading spinner with skeleton preview
        │   └── layout/Navigation.tsx        # Responsive navigation bar with live backend health indicator
        ├── context/                         # Global filter state store
        │   ├── FilterContext.tsx            # React Context Provider managing date range and cutoff state
        │   ├── FilterContext.test.tsx       # Unit tests for default filter values, actions, and resets
        │   ├── filterState.ts               # Filter state interface definitions and default values
        │   ├── index.ts                     # Context barrel export
        │   └── useFilters.ts                # Custom hook for consuming filter context safely
        ├── hooks/                           # TanStack Query data fetching hooks
        │   └── useQueries.ts                # Cached query hooks for health, forecast, compare, and metric views
        ├── pages/                           # Application route views
        │   ├── AccuracyPage.tsx             # Benchmark view with KPI cards, brush chart, histogram, and diurnal bars
        │   ├── DecisionPage.tsx             # Day-ahead view with 48-period curve, buyer summary, and P90 table
        │   └── DecisionPage.test.tsx        # Component tests for loading, error, empty, and loaded page states
        ├── test/                            # Test configuration
        │   └── setup.ts                     # Vitest test setup registering @testing-library/jest-dom matchers
        └── types/                           # Strict TypeScript data types
            └── api.ts                       # TypeScript interfaces mirroring FastAPI Pydantic response models
```

---

## How to Run with Docker

The entire platform runs in isolated containers via Docker Compose with non-root security and automated service discovery.

```bash
# 1. Build container images from scratch without cache
docker compose build --no-cache

# 2. Launch backend and frontend services in detached mode
docker compose up -d

# 3. Verify container status and healthchecks
docker compose ps
```

### Endpoints
- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000) or [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### Container Logs & Teardown
```bash
# View backend structured JSON logs
docker compose logs -f backend

# View frontend Nginx reverse proxy logs
docker compose logs -f frontend

# Stop and remove containers and network
docker compose down
```

---

## How to Run without Docker

### Prerequisites
- **Python 3.12+**
- **Node.js 20+** (tested on Node v22 and v24) and **npm**

### 1. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install the backend package in editable mode
pip install -e ".[dev]"

# Start the development server
uvicorn app.main:app --reload --port 8000
```
*The backend starts at `http://localhost:8000` and serves the committed Parquet dataset from `backend/data/`.*

### 2. Frontend Setup

```bash
# Navigate to the frontend directory
cd frontend

# Install exact dependencies
npm install

# Start the Vite development server
npm run dev
```
*The frontend dashboard starts at `http://localhost:5173` with automatic proxying of `/api` requests to `http://localhost:8000`.*

---

## How to Run Tests

### Backend Test Suite & Linting

```bash
# From the repository root or backend directory:
pytest -v

# Run the Ruff linter:
ruff check backend
```
- **38 tests** cover:
  - Unit calculations for MAE, RMSE, Bias, nMAE, and percentiles against hand-calculated datasets.
  - Cutoff boundary conditions (exact cutoff match, 1-minute post-cutoff exclusion, multiple days).
  - Schema validation, data immutability, and missing file exception handling in `DataRepository`.
  - Integration tests for all `/api/v1` routes, structured JSON logging, and Vercel domain CORS policies.

### Frontend Test Suite, Typecheck & Linting

```bash
# From the frontend directory:
cd frontend

# Run Vitest test suite:
npm test

# Run strict TypeScript compiler verification:
npm run typecheck

# Run the Oxlint linter:
npm run lint

# Run Vite production bundle build:
npm run build
```
- **15 tests** cover:
  - `apiClient` error handling, HTTP 400 detail extraction, 500 fallback, and query serialization.
  - `FilterContext` state store mutations (`setDeliveryDate`, `setCutoff`, `setDateRange`, `resetFilters`).
  - `DecisionPage` UI rendering across **Loading**, **Error** (with interactive retry), **Empty**, and **Loaded** dashboard states.

---

## How the Forecast Selection and Metrics Work

### 1. Pure Day-Ahead Forecast Selection Logic
The selection engine is implemented as a pure function in [`forecast_selection.py`](file:///c:/Users/mayan/OneDrive/Desktop/Gridbricks%20Assignment/backend/app/services/forecast_selection.py):
- **Input**: Delivery date range $[D_{\text{start}}, D_{\text{end}}]$ and a UK local cutoff time of day applied to Day $D-1$ (e.g., `09:00` UK).
- **Timezone Awareness**: The cutoff time on Day $D-1$ is resolved in the `Europe/London` timezone (accounting for GMT vs. BST) and converted into a timezone-aware UTC cutoff timestamp.
- **Selection Criterion**: For each target half-hour period on delivery date $D$, the algorithm identifies all published forecasts where $\text{publishTime} \le \text{cutoff}_{\text{UTC}}$ and selects the record with the latest publication timestamp ($\max(\text{publishTime})$).
- **Settlement Period Preservation**: Elexon `WINDFOR` broadcasts national wind forecasts at hourly intervals (`:00`). The intermediate half-hour settlement periods (`:30`) are preserved with `isMissing=True` and `generation=None`. All 48 settlement periods per day are strictly returned; no periods are dropped.

### 2. Statistical Metrics Engine
Implemented in [`metrics.py`](file:///c:/Users/mayan/OneDrive/Desktop/Gridbricks%20Assignment/backend/app/services/metrics.py), metrics are computed on the joined dataset:
$$\text{Error} = \text{Actual} - \text{Forecast}$$
*(A negative error indicates the forecast over-predicted actual wind generation; a positive error indicates under-prediction).*

- **Mean Absolute Error (MAE)**: Average magnitude of forecast deviations in MW:
  $$\text{MAE} = \frac{1}{N}\sum_{i=1}^N |\text{Actual}_i - \text{Forecast}_i|$$
- **Root Mean Squared Error (RMSE)**: Penalizes large volatile forecast errors:
  $$\text{RMSE} = \sqrt{\frac{1}{N}\sum_{i=1}^N (\text{Actual}_i - \text{Forecast}_i)^2}$$
- **Bias (Mean Signed Error)**: Indicates persistent directional skew:
  $$\text{Bias} = \frac{1}{N}\sum_{i=1}^N (\text{Actual}_i - \text{Forecast}_i)$$
- **Normalized MAE Percentage (nMAE %)**: Scale-independent error relative to actual production:
  $$\text{nMAE} = \frac{\text{MAE}}{\overline{\text{Actual}}} \times 100\%$$
- **Percentiles (P50, P90, P95)**: Computed from empirical absolute error distributions $|\text{Error}|$.
- **Diurnal Profile (By Hour of Day)**: Groups errors by UK local hour of day ($0$ to $23$) to uncover time-of-day accuracy patterns (e.g., afternoon thermal effects vs. nighttime baseline wind).
- **Lead-Time Horizon Bucketing**: Evaluates all historical forecast runs categorized into horizons ($\Delta t = \text{startTime} - \text{publishTime}$): `<0h`, `0-6h`, `6-12h`, `12-24h`, `24-36h`, `36-48h`, and `>48h`.

### 3. Power Buyer Buffer Recommendations
For each hour of the delivery day, the platform recommends a physical hedge volume:
$$\text{Hedged Volume} = \max(0, \overline{\text{Forecast}}_{\text{hour}} - \text{P90 Buffer}_{\text{hour}})$$
By contracting the hedged volume rather than 100% of the raw forecast, a power buyer maintains 90% statistical confidence that delivered generation will satisfy or exceed contracted commitments, mitigating exposure to punitive Balancing Mechanism shortfall cashout prices.

---

## Assumptions and Decisions

1. **Internal UTC, Local UK Display**: All timestamps are parsed, validated, stored, and computed internally as timezone-aware UTC. Timestamps and cutoffs are converted to `Europe/London` strictly for boundary resolution and UI presentation.
2. **Elexon Feed Granularity**: The verified Elexon BMRS `WINDFOR` feed only publishes forecasts on the hour (`:00`). Rather than interpolating fabricated values, intermediate `:30` settlement periods are explicitly flagged as missing (`isMissing=True`), maintaining strict fidelity to actual market data.
3. **Zero Request-Time External Calls**: To ensure high availability and sub-millisecond API response times, the backend does not make outbound network requests to Elexon at runtime. The committed January 2026 dataset is loaded and validated into memory once during server lifespan startup.
4. **Strict Type Safety**: All Python code includes full type hints, Pydantic models validate every request/response, and TypeScript is configured in strict mode across the frontend with zero `any` types.
5. **CORS Security**: CORS in the backend is restricted to the deployed Vercel domain and preview URL pattern (`r"^https://.*\.vercel\.app$"`), protecting production endpoints from unauthorized third-party origins.

---

## Limitations and Next Steps

- **Dataset Scope**: Currently operates on the validated January 2026 historical benchmark dataset. *Next step: Implement an automated cron worker to poll Elexon BMRS daily for continuous live ingestion.*
- **Half-Hour Interpolation**: Settlement periods on the half-hour (`:30`) currently appear as missing in compliance with `WINDFOR` hourly granularity. *Next step: Provide an optional user-selected linear interpolation toggle for traders requiring contiguous 48-period curves.*
- **Financial Imbalance Pricing**: Current buffers evaluate physical MW errors. *Next step: Ingest Elexon System Buy Price (SBP) and System Sell Price (SSP) streams to calculate the exact £ financial cost of imbalance exposure.*
- **Zonal / Regional Breakdown**: The platform currently analyzes national aggregate wind outturn. *Next step: Incorporate DNO and regional substation telemetry for transmission vs. distribution connected assets.*

---

## AI Usage

Antigravity was used for scaffolding, boilerplate and test drafting while design decisions and verification were done by me.
