# ==============================================================================
# Stage 1: Build stage (compile wheels and prepare isolated virtual environment)
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy package metadata and source code for installation
COPY pyproject.toml README.md ./
COPY app ./app

# Install project dependencies and local package
RUN pip install --upgrade pip setuptools wheel && \
    pip install .

# ==============================================================================
# Stage 2: Production runtime stage
# ==============================================================================
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DATA_DIR="/app/data"

# Create a dedicated unprivileged user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -M appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy committed data snapshot (actuals.parquet and forecasts.parquet) into image
COPY --chown=appuser:appgroup data /app/data

# Copy backend application source
COPY --chown=appuser:appgroup app /app/app

# Set appropriate directory ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose backend service port
EXPOSE 8000

# Container healthcheck querying the /api/v1/health endpoint using standard library urllib
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').getcode() == 200 else 1)"

# Start FastAPI application with uvicorn bound to all network interfaces
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
