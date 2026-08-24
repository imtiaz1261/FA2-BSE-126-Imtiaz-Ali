FROM python:3.11-slim

# Create app directory
WORKDIR /app

# System deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry or pip requirements
# Prefer requirements.txt if present
COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/

# Expose port for FastAPI
EXPOSE 8000

# Default environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run with Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
