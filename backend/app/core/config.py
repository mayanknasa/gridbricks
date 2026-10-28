import os
from pathlib import Path

from pydantic import BaseModel, Field


def parse_allowed_origins() -> list[str]:
    """Parse allowed CORS origins from environment variables."""
    raw = (
        os.getenv("ALLOWED_ORIGINS")
        or os.getenv("FRONTEND_URL")
        or os.getenv("VERCEL_URL")
    )
    if raw:
        origins: list[str] = []
        for item in raw.split(","):
            cleaned = item.strip().rstrip("/")
            if cleaned:
                if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
                    cleaned = f"https://{cleaned}"
                origins.append(cleaned)
        return origins

    # Default to standard local development origins
    return [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]


class Settings(BaseModel):
    """Application settings and configuration."""

    app_name: str = "Gridbricks Assignment API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    data_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv(
                "DATA_DIR",
                str(Path(__file__).resolve().parent.parent.parent / "data"),
            )
        )
    )
    allowed_origins: list[str] = Field(default_factory=parse_allowed_origins)
    cors_origin_regex: str | None = Field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGIN_REGEX",
            r"^https://.*\.vercel\.app$",
        )
    )


settings: Settings = Settings()
