"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.api.v1.endpoints import router as v1_router
from app.core.config import settings
from app.core.logging_middleware import (
    StructuredLoggingMiddleware,
    setup_access_logging,
)
from app.core.repository import DataRepository
from app.models.health import MessageResponse

setup_access_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Execute startup checks to ensure required datasets exist and are valid."""
    DataRepository.get_instance().load()
    yield


app: FastAPI = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "GB National Wind Generation Forecast Analysis & Benchmark API. "
        "Evaluates day-ahead forecasts against actual outturn generation."
    ),
    lifespan=lifespan,
)

app.add_middleware(StructuredLoggingMiddleware)

# Configure CORS restricted to configured Vercel domain and preview URLs
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Map parameter validation failures to clear 400 Bad Request responses."""
    errors = exc.errors()
    first_err = errors[0] if errors else {}
    loc = " -> ".join(str(elem) for elem in first_err.get("loc", []))
    msg = first_err.get("msg", "Invalid parameter")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": f"Validation error at '{loc}': {msg}"},
    )


app.include_router(api_router, prefix=settings.api_prefix, tags=["general"])
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])


@app.get("/", response_model=MessageResponse, summary="Root status", tags=["general"])
def root() -> MessageResponse:
    """Return welcome message from the backend API."""
    return MessageResponse(message="Gridbricks Backend API is running")
