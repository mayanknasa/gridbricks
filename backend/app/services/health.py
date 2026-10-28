"""Health check service logic."""

from datetime import UTC, datetime

from app.models.health import HealthStatus


def get_health_status(version: str) -> HealthStatus:
    """Generate the current health status with a timezone-aware UTC timestamp.

    Args:
        version: The current application version string.

    Returns:
        HealthStatus model populated with UTC timestamp and status.
    """
    return HealthStatus(
        status="ok",
        timestamp=datetime.now(UTC),
        version=version,
    )
