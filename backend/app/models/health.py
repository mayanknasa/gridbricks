"""Health and status models."""

from datetime import datetime

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """Pydantic model for API health status response."""

    status: str = Field(description="Service status indicator")
    timestamp: datetime = Field(description="UTC timestamp of the status check")
    version: str = Field(description="API service version")


class MessageResponse(BaseModel):
    """Pydantic model for simple informational responses."""

    message: str = Field(description="Informational status message")
