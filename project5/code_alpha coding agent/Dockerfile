# Dockerfile for Code Alpha CLI & API

FROM python:3.10-slim

LABEL maintainer="Code Alpha"
LABEL description="Autonomous Code Generation Agent - CLI & API"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -e . && \
    pip install -r requirements_cli_api.txt

# Create non-root user
RUN useradd -m -u 1000 codealpha && \
    chown -R codealpha:codealpha /app

USER codealpha

# Expose API port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command - API server
CMD ["codealpha", "api", "--start"]

# Alternative entry point - CLI
# docker run codealpha run "your-prompt"

# Build:
# docker build -t codealpha:latest .

# Run API server:
# docker run -p 8000:8000 -v $(pwd):/workspace codealpha

# Run CLI:
# docker run -v $(pwd):/workspace codealpha run "Generate tests"
