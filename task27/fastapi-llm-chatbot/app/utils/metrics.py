"""
Prometheus-compatible metrics.

Exposes counters/histograms for HTTP requests and LLM calls. These are
in-process metrics (fine for a single container); if you scale to multiple
replicas, scrape each instance separately or push to a shared backend.
"""

import time

from prometheus_client import Counter, Histogram

START_TIME = time.time()

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["provider", "status"],
)

LLM_REQUEST_DURATION_SECONDS = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["provider"],
)

LLM_ERRORS_TOTAL = Counter(
    "llm_errors_total",
    "Total LLM errors",
    ["provider", "error_type"],
)


def uptime_seconds() -> float:
    return time.time() - START_TIME
