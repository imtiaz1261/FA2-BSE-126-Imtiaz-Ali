# ============================================================
# AIHub — Backend Dockerfile (FastAPI + Uvicorn)
# ============================================================
# Multi-stage build:
#   Stage 1 (builder)  — install dependencies into a venv
#   Stage 2 (runtime)  — copy only the venv + app code
#
# Why multi-stage?
#   Keeps the final image lean by excluding build tools (gcc,
#   pip, wheel cache) that are needed to compile packages but
#   not to run them.  Smaller images = faster deploys + less
#   attack surface.
# ============================================================

# ------------------------------------
# Stage 1 — Dependency builder
# ------------------------------------
FROM python:3.11-slim AS builder

# Prevent .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install OS-level build dependencies required by some Python
# packages (psycopg2, argon2-cffi, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements first — Docker layer cache means
# this layer is only rebuilt when requirements.txt changes,
# not every time source code changes.
COPY requirements.txt .

# Create an isolated virtual environment inside the image
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------------------
# Stage 2 — Runtime image
# ------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Runtime OS dependencies only (libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built venv from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application source code
COPY backend/ ./backend/

# Create a non-root user to run the application.
# Running as root inside a container is a security risk.
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Expose the FastAPI port
EXPOSE 8000

# Health check — Docker will mark the container unhealthy if
# the API stops responding, triggering a restart policy.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start Uvicorn with:
#   --host 0.0.0.0     → accept connections from outside the container
#   --workers 1        → single worker for dev; increase for production
#   --reload           → auto-reload on code change (remove in production)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
