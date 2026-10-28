"""API router definitions."""

from fastapi import APIRouter

from app.core.config import settings
from app.models.health import HealthStatus
from app.services.health import get_health_status

router: APIRouter = APIRouter()


@router.get("/health", response_model=HealthStatus, summary="System Health Check")
def health_check() -> HealthStatus:
    """Return system operational status and UTC timestamp."""
    return get_health_status(version=settings.app_version)
