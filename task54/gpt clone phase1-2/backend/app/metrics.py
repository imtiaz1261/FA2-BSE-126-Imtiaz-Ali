"""
Prometheus metrics for monitoring application performance and behavior.

Metrics exported:
- Request count and latency
- Error rates
- Worker job metrics
- Database metrics
- Cache hit rates
"""

import logging
from time import time

from prometheus_client import Counter, Gauge, Histogram, Summary

logger = logging.getLogger(__name__)


# ============================================================================
# Request Metrics
# ============================================================================

http_requests_total = Counter(
    name="http_requests_total",
    documentation="Total HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    name="http_request_duration_seconds",
    documentation="HTTP request latency in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

http_requests_in_progress = Gauge(
    name="http_requests_in_progress",
    documentation="HTTP requests in progress",
    labelnames=["method", "endpoint"],
)


# ============================================================================
# Error Metrics
# ============================================================================

http_errors_total = Counter(
    name="http_errors_total",
    documentation="Total HTTP errors",
    labelnames=["method", "endpoint", "error_type"],
)

exceptions_total = Counter(
    name="exceptions_total",
    documentation="Total exceptions",
    labelnames=["exception_type", "handler"],
)


# ============================================================================
# Authentication Metrics
# ============================================================================

login_attempts_total = Counter(
    name="login_attempts_total",
    documentation="Total login attempts",
    labelnames=["result"],  # success, failure
)

token_validations_total = Counter(
    name="token_validations_total",
    documentation="Total token validations",
    labelnames=["result"],  # valid, invalid, expired
)


# ============================================================================
# Database Metrics
# ============================================================================

database_query_duration_seconds = Histogram(
    name="database_query_duration_seconds",
    documentation="Database query latency in seconds",
    labelnames=["operation", "table"],
    buckets=(0.001, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

database_connections_total = Gauge(
    name="database_connections_total",
    documentation="Active database connections",
)


# ============================================================================
# Cache Metrics
# ============================================================================

cache_hits_total = Counter(
    name="cache_hits_total",
    documentation="Cache hits",
    labelnames=["cache_type"],
)

cache_misses_total = Counter(
    name="cache_misses_total",
    documentation="Cache misses",
    labelnames=["cache_type"],
)


# ============================================================================
# RAG/Worker Metrics
# ============================================================================

document_ingestion_total = Counter(
    name="document_ingestion_total",
    documentation="Total documents ingested",
    labelnames=["status"],  # success, failure
)

embeddings_generated_total = Counter(
    name="embeddings_generated_total",
    documentation="Total embeddings generated",
    labelnames=["model"],
)

worker_jobs_total = Counter(
    name="worker_jobs_total",
    documentation="Total worker jobs processed",
    labelnames=["job_type", "status"],  # success, failure, timeout
)

worker_jobs_duration_seconds = Histogram(
    name="worker_jobs_duration_seconds",
    documentation="Worker job duration in seconds",
    labelnames=["job_type"],
    buckets=(1, 5, 10, 30, 60, 300, 600),
)

worker_queue_depth = Gauge(
    name="worker_queue_depth",
    documentation="Current worker queue depth",
    labelnames=["queue_type"],
)


# ============================================================================
# Chat Metrics
# ============================================================================

chat_messages_total = Counter(
    name="chat_messages_total",
    documentation="Total chat messages",
    labelnames=["type"],  # user, assistant
)

chat_tokens_total = Counter(
    name="chat_tokens_total",
    documentation="Total tokens used",
    labelnames=["model", "type"],  # input, output
)

chat_latency_seconds = Histogram(
    name="chat_latency_seconds",
    documentation="Chat response latency in seconds",
    labelnames=["model"],
    buckets=(1, 2, 5, 10, 30, 60),
)


# ============================================================================
# Billing Metrics
# ============================================================================

subscription_count = Gauge(
    name="subscription_count",
    documentation="Active subscriptions",
    labelnames=["plan"],  # free, plus, pro
)

revenue_total = Counter(
    name="revenue_total",
    documentation="Total revenue",
    labelnames=["plan", "currency"],
)


# ============================================================================
# Usage Metrics
# ============================================================================

active_users = Gauge(
    name="active_users",
    documentation="Active users",
    labelnames=["time_window"],  # 1h, 24h, 30d
)

daily_active_users = Gauge(
    name="daily_active_users",
    documentation="Daily active users",
)

monthly_active_users = Gauge(
    name="monthly_active_users",
    documentation="Monthly active users",
)


# ============================================================================
# Memory Extraction Metrics
# ============================================================================

memory_extractions_total = Counter(
    name="memory_extractions_total",
    documentation="Total memory extractions",
    labelnames=["status"],  # success, failure
)

memory_retrieval_duration_seconds = Histogram(
    name="memory_retrieval_duration_seconds",
    documentation="Memory retrieval latency in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
)


# ============================================================================
# Health & Availability
# ============================================================================

service_up = Gauge(
    name="service_up",
    documentation="Service availability (1 = up, 0 = down)",
    labelnames=["service"],  # backend, worker, database, redis
)

dependency_health = Gauge(
    name="dependency_health",
    documentation="Dependency health status",
    labelnames=["dependency"],  # database, redis, s3, stripe
)


# ============================================================================
# Middleware for automatic metrics collection
# ============================================================================


class MetricsMiddleware:
    """ASGI middleware for automatic Prometheus metrics collection."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request info
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "")

        # Clean path for label (avoid high cardinality)
        endpoint = self._clean_endpoint(path)

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Measure request duration
        start_time = time()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Record metrics when response starts
                status_code = message["status"]
                http_requests_total.labels(
                    method=method, endpoint=endpoint, status_code=status_code
                ).inc()

                # Record error if applicable
                if status_code >= 400:
                    error_type = f"{status_code}"
                    http_errors_total.labels(
                        method=method, endpoint=endpoint, error_type=error_type
                    ).inc()

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Record duration
            duration = time() - start_time
            http_request_duration_seconds.labels(
                method=method, endpoint=endpoint
            ).observe(duration)

            # Decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

    @staticmethod
    def _clean_endpoint(path: str) -> str:
        """Clean path to avoid high cardinality labels."""
        # Replace numeric IDs with placeholder
        import re

        # Replace UUID, numeric IDs with placeholders
        cleaned = re.sub(r"/[a-f0-9-]{36}", "/{uuid}", path)
        cleaned = re.sub(r"/\d+", "/{id}", cleaned)

        return cleaned[:100]  # Limit to 100 chars
