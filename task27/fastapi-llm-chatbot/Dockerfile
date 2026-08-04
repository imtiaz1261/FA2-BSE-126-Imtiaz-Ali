# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr,
# which keeps logs flowing immediately (important for container logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so Docker can cache this layer whenever only
# application code (not requirements.txt) changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY app ./app
COPY run.py .

# Create a non-root user and switch to it.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Docker-level health check. Uses Python's stdlib so no extra packages
# (like curl) are needed in the final image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,os,sys; \
    port=os.environ.get('PORT','8000'); \
    sys.exit(0) if urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3).status == 200 else sys.exit(1)"

# Production server: Gunicorn managing Uvicorn workers.
# PORT is read at runtime so this same image works on Railway/Render, which
# inject their own PORT value, as well as locally/EC2 where PORT=8000.
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:${PORT:-8000} --access-logfile - --error-logfile -"]
