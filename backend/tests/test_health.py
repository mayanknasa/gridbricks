"""Unit and integration tests for health endpoints and services."""

from datetime import UTC

from fastapi.testclient import TestClient

from app.main import app
from app.models.health import HealthStatus, MessageResponse
from app.services.health import get_health_status


def test_get_health_status_unit() -> None:
    """Verify health service returns valid model and timezone-aware UTC datetime."""
    version_str: str = "0.1.0"
    result: HealthStatus = get_health_status(version=version_str)

    assert isinstance(result, HealthStatus)
    assert result.status == "ok"
    assert result.version == version_str
    assert result.timestamp.tzinfo is not None
    assert result.timestamp.tzinfo == UTC


def test_root_endpoint_integration() -> None:
    """Verify root endpoint response and schema compliance."""
    client: TestClient = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    model = MessageResponse(**response.json())
    assert "Gridbricks" in model.message


def test_health_endpoint_integration() -> None:
    """Verify /api/health endpoint response and schema compliance."""
    client: TestClient = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    model = HealthStatus(**response.json())
    assert model.status == "ok"
    assert model.version == "0.1.0"
    assert model.timestamp.tzinfo is not None
