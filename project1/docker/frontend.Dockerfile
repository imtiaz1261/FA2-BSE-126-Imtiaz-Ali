# ============================================================
# AIHub — Frontend Dockerfile (Streamlit)
# ============================================================
# Single-stage build — Streamlit has no compiled extensions
# that would benefit from a multi-stage approach.
# ============================================================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir streamlit httpx

# Copy the frontend source
COPY frontend/ ./frontend/

# Create non-root user
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Expose the Streamlit default port
EXPOSE 8501

# Streamlit configuration via environment variables.
# These suppress the "Welcome to Streamlit" onboarding screen
# and disable usage telemetry in production.
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "frontend/Home.py"]
