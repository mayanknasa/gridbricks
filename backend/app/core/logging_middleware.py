"""Structured JSON logging middleware for FastAPI requests."""

import json
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("gridbricks.access")


def setup_access_logging() -> None:
    """Configure stdout console handler for structured JSON access logging."""
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware capturing request ID, latency, and emitting structured JSON logs."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process incoming request, measure latency, and log structured JSON."""
        request_id: str = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time: float = time.perf_counter()
        status_code: int = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            raise
        finally:
            duration_ms: float = (time.perf_counter() - start_time) * 1000.0
            log_payload = {
                "timestamp": datetime.now(UTC).isoformat(),
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            }
            logger.info(json.dumps(log_payload))
