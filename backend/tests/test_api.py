"""API integration tests for v1 endpoints using FastAPI TestClient."""

import logging
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.api import (
    CompareResponse,
    ForecastResponse,
    HorizonMetricsResponse,
    HourlyMetricsResponse,
    OverallMetricsResponse,
)
from app.models.health import HealthStatus


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Fixture providing initialized FastAPI TestClient with loaded datasets."""
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# 1. /api/v1/health
# ---------------------------------------------------------------------------


def test_v1_health_success(client: TestClient) -> None:
    """Verify /api/v1/health returns 200 with valid HealthStatus schema."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    model = HealthStatus(**data)
    assert model.status == "ok"
    assert model.version is not None
    assert model.timestamp.tzinfo is not None
    assert "X-Request-ID" in response.headers


# ---------------------------------------------------------------------------
# 2. /api/v1/forecast
# ---------------------------------------------------------------------------


def test_v1_forecast_default_params_success(client: TestClient) -> None:
    """Verify /api/v1/forecast returns 200 with default parameters."""
    response = client.get("/api/v1/forecast")
    assert response.status_code == 200
    data = response.json()
    model = ForecastResponse(**data)

    assert model.delivery_date == date(2026, 1, 2)
    assert model.cutoff == "09:00"
    assert model.total_periods == 48
    assert len(model.data) == 48

    first_item = model.data[0]
    assert first_item.start_time.tzinfo is not None
    assert not first_item.is_missing
    assert not first_item.is_derived
    assert first_item.forecast_type == "published"
    assert first_item.generation is not None

    # For intermediate :30 periods, verify step-hold derivation
    second_item = model.data[1]
    assert not second_item.is_missing
    assert second_item.is_derived
    assert second_item.forecast_type == "step_hold"
    assert second_item.generation == first_item.generation


def test_v1_forecast_custom_params_success(client: TestClient) -> None:
    """Verify /api/v1/forecast with custom delivery date and cutoff."""
    response = client.get("/api/v1/forecast?delivery_date=2026-01-15&cutoff=12:00")
    assert response.status_code == 200
    model = ForecastResponse(**response.json())
    assert model.delivery_date == date(2026, 1, 15)
    assert model.cutoff == "12:00"
    assert model.total_periods == 48


def test_v1_forecast_date_outside_range_fails(client: TestClient) -> None:
    """Verify 400 Bad Request when delivery_date is outside January 2026 range."""
    # Past boundary
    response_past = client.get("/api/v1/forecast?delivery_date=2025-12-31")
    assert response_past.status_code == 400
    err_msg_past = response_past.json()["detail"]
    assert "outside available January 2026 data range" in err_msg_past

    # Future boundary
    response_future = client.get("/api/v1/forecast?delivery_date=2026-02-15")
    assert response_future.status_code == 400
    err_msg_future = response_future.json()["detail"]
    assert "outside available January 2026 data range" in err_msg_future


def test_v1_forecast_invalid_cutoff_fails(client: TestClient) -> None:
    """Verify 400 Bad Request for malformed cutoff strings."""
    # Invalid hour
    resp_hour = client.get("/api/v1/forecast?delivery_date=2026-01-10&cutoff=25:00")
    assert resp_hour.status_code == 400
    assert "Invalid cutoff time" in resp_hour.json()["detail"]

    # Invalid minute
    resp_min = client.get("/api/v1/forecast?delivery_date=2026-01-10&cutoff=09:65")
    assert resp_min.status_code == 400
    assert "Invalid cutoff time" in resp_min.json()["detail"]

    # Non-time string
    resp_str = client.get("/api/v1/forecast?delivery_date=2026-01-10&cutoff=noon")
    assert resp_str.status_code == 400
    assert "Invalid cutoff time" in resp_str.json()["detail"]


# ---------------------------------------------------------------------------
# 3. /api/v1/compare
# ---------------------------------------------------------------------------


def test_v1_compare_success(client: TestClient) -> None:
    """Verify /api/v1/compare returns valid comparisons per half hour."""
    response = client.get(
        "/api/v1/compare?start=2026-01-05&end=2026-01-06&cutoff=09:00"
    )
    assert response.status_code == 200
    data = response.json()
    model = CompareResponse(**data)

    assert model.start_date == date(2026, 1, 5)
    assert model.end_date == date(2026, 1, 6)
    assert model.cutoff == "09:00"
    assert model.total_periods == 96  # 2 days * 48
    assert len(model.data) == 96

    # Verify error formula actual - forecast for valid records
    for item in model.data:
        if not item.is_missing and item.forecast_generation is not None:
            assert item.actual_generation is not None
            expected_error = item.actual_generation - item.forecast_generation
            assert item.error == pytest.approx(expected_error, abs=1e-3)
            assert item.abs_error == pytest.approx(abs(expected_error), abs=1e-3)


def test_v1_compare_start_after_end_fails(client: TestClient) -> None:
    """Verify 400 Bad Request when start date is after end date."""
    response = client.get(
        "/api/v1/compare?start=2026-01-20&end=2026-01-10&cutoff=09:00"
    )
    assert response.status_code == 400
    err_detail = response.json()["detail"]
    assert "start date (2026-01-20) cannot be after end date" in err_detail


def test_v1_compare_dates_outside_range_fails(client: TestClient) -> None:
    """Verify 400 Bad Request when dates are outside available range."""
    response = client.get(
        "/api/v1/compare?start=2025-12-25&end=2026-01-05&cutoff=09:00"
    )
    assert response.status_code == 400
    assert "outside available January 2026 data range" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 4. /api/v1/metrics
# ---------------------------------------------------------------------------


def test_v1_metrics_success(client: TestClient) -> None:
    """Verify /api/v1/metrics computes overall MAE, RMSE, Bias, and percentiles."""
    response = client.get(
        "/api/v1/metrics?start=2026-01-02&end=2026-01-31&cutoff=09:00"
    )
    assert response.status_code == 200
    model = OverallMetricsResponse(**response.json())

    assert model.start_date == date(2026, 1, 2)
    assert model.end_date == date(2026, 1, 31)
    assert model.cutoff == "09:00"
    assert model.metrics.total_count == 30 * 48  # 1440
    assert model.metrics.valid_count > 0
    assert model.metrics.mae is not None
    assert model.metrics.mae > 0.0
    assert model.metrics.rmse is not None
    assert model.metrics.rmse >= model.metrics.mae
    assert model.metrics.nmae_pct is not None
    assert model.metrics.nmae_pct > 0.0
    assert model.metrics.p50 is not None
    assert model.metrics.p90 is not None
    assert model.metrics.p95 is not None
    assert model.metrics.p50 <= model.metrics.p90 <= model.metrics.p95


def test_v1_metrics_validation_errors(client: TestClient) -> None:
    """Verify 400 Bad Request for invalid metrics inputs."""
    # Invalid cutoff
    resp_cut = client.get("/api/v1/metrics?cutoff=bad")
    assert resp_cut.status_code == 400

    # Start date out of bounds
    resp_start = client.get("/api/v1/metrics?start=2025-01-01")
    assert resp_start.status_code == 400

    # Inverted date range
    resp_invert = client.get("/api/v1/metrics?start=2026-01-20&end=2026-01-10")
    assert resp_invert.status_code == 400


# ---------------------------------------------------------------------------
# 5. /api/v1/metrics/by_hour
# ---------------------------------------------------------------------------


def test_v1_metrics_by_hour_success(client: TestClient) -> None:
    """Verify /api/v1/metrics/by_hour returns 24 hourly breakdowns."""
    response = client.get(
        "/api/v1/metrics/by_hour?start=2026-01-02&end=2026-01-10&cutoff=09:00"
    )
    assert response.status_code == 200
    model = HourlyMetricsResponse(**response.json())

    assert len(model.data) == 24
    hours = [item.hour for item in model.data]
    assert hours == list(range(24))

    for item in model.data:
        assert item.total_count > 0
        if item.valid_count > 0:
            assert item.mae is not None
            assert item.rmse is not None


# ---------------------------------------------------------------------------
# 6. /api/v1/metrics/by_horizon
# ---------------------------------------------------------------------------


def test_v1_metrics_by_horizon_success(client: TestClient) -> None:
    """Verify /api/v1/metrics/by_horizon returns lead-time bucketed metrics."""
    response = client.get("/api/v1/metrics/by_horizon?start=2026-01-02&end=2026-01-10")
    assert response.status_code == 200
    model = HorizonMetricsResponse(**response.json())

    assert len(model.data) > 0
    bucket_labels = [item.bucket for item in model.data]
    assert "<0h" in bucket_labels
    assert "0-6h" in bucket_labels
    assert "12-24h" in bucket_labels
    assert "24-36h" in bucket_labels

    # Horizon buckets evaluate all available forecasts
    total_evals = sum(item.total_count for item in model.data)
    assert total_evals > 0


# ---------------------------------------------------------------------------
# 7. Structured JSON Logging & Request ID Middleware
# ---------------------------------------------------------------------------


def test_structured_logging_and_request_id(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify structured JSON logging and X-Request-ID propagation."""
    custom_request_id: str = "custom-test-req-id-12345"

    with caplog.at_level(logging.INFO, logger="gridbricks.access"):
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": custom_request_id},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_request_id

    # Check captured log contains structured JSON with request_id and duration_ms
    access_logs = [
        rec.message for rec in caplog.records if rec.name == "gridbricks.access"
    ]
    assert len(access_logs) >= 1
    latest_log = access_logs[-1]
    assert custom_request_id in latest_log
    assert '"duration_ms"' in latest_log
    assert '"status_code": 200' in latest_log
    assert '"path": "/api/v1/health"' in latest_log


# ---------------------------------------------------------------------------
# 8. CORS Middleware Configuration for Vercel Domains
# ---------------------------------------------------------------------------


def test_cors_vercel_origin_allowed(client: TestClient) -> None:
    """Verify that requests from a Vercel domain receive CORS allow headers."""
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "https://gridbricks.vercel.app"},
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "https://gridbricks.vercel.app"
    )


def test_cors_vercel_preview_domain_allowed(client: TestClient) -> None:
    """Verify that Vercel preview deployment URLs match cors_origin_regex."""
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "https://gridbricks-git-feature-preview.vercel.app"},
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "https://gridbricks-git-feature-preview.vercel.app"
    )


def test_cors_unauthorized_origin_blocked(client: TestClient) -> None:
    """Verify that requests from untrusted external origins are not granted CORS."""
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "https://malicious-external-site.com"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_options_request(client: TestClient) -> None:
    """Verify CORS preflight OPTIONS request returns 200 and allowed methods."""
    response = client.options(
        "/api/v1/forecast",
        headers={
            "Origin": "https://gridbricks.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "https://gridbricks.vercel.app"
    )
    assert "GET" in response.headers.get("access-control-allow-methods", "")


def test_openapi_schema_by_horizon_and_metrics(client: TestClient) -> None:
    """Verify OpenAPI schema reflects removal of cutoff from by_horizon and nmae_pct."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    # Verify by_horizon parameters do not contain 'cutoff'
    by_horizon_path = schema["paths"]["/api/v1/metrics/by_horizon"]["get"]
    param_names = [p["name"] for p in by_horizon_path["parameters"]]
    assert "start" in param_names
    assert "end" in param_names
    assert "cutoff" not in param_names

    # Verify HorizonMetricsResponse does not have cutoff in properties
    horizon_schema = schema["components"]["schemas"]["HorizonMetricsResponse"]
    assert "cutoff" not in horizon_schema.get("properties", {})

    # Verify OverallMetrics schema has nmae_pct
    overall_schema = schema["components"]["schemas"]["OverallMetrics"]
    assert "nmae_pct" in overall_schema.get("properties", {})


