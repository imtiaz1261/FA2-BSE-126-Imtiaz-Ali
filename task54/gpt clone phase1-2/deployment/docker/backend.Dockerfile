# Backend Dockerfile - Production-ready FastAPI application
# Multi-stage build with security hardening

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .

# Build wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install Python dependencies from wheels
RUN pip install --no-cache /wheels/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application code
COPY backend/ /app/

# Set permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with gunicorn for production
CMD ["gunicorn", \
     "--workers=4", \
     "--worker-class=uvicorn.workers.UvicornWorker", \
     "--bind=0.0.0.0:8000", \
     "--access-logfile=-", \
     "--error-logfile=-", \
     "--timeout=120", \
     "--keep-alive=5", \
     "--max-requests=1000", \
     "--max-requests-jitter=100", \
     "app.main:app"]
