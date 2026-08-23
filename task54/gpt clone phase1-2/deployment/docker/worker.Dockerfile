# Worker Dockerfile - RAG/Agent background job processor
# Separate from API for independent scaling

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

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache /wheels/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application code
COPY backend/ /app/

# Set permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port for metrics only (not for service)
EXPOSE 8001

# No typical health check for workers - they're managed by job queue
# But provide a metrics endpoint for monitoring

CMD ["python", "-m", "app.worker.main"]
