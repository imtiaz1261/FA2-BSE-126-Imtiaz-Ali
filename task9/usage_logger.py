"""
Production-style token/cost usage logger for LLM API calls.

Wraps any OpenAI-compatible client (OpenAI, Groq, Azure OpenAI, etc.) so
that every request's input/output tokens, cost, and latency are logged
automatically — to a local rotating file, to AWS CloudWatch Logs, or both
at once — without changing how you call the API.

Design:
- `UsageRecord`      — one structured log entry per request
- `LogBackend`        — interface all backends implement (`.log(record)`)
- `FileLogBackend`    — writes JSON-lines to a local file with automatic
                         rotation (won't grow forever)
- `CloudWatchLogBackend` — streams the same records to an AWS CloudWatch
                         Logs group/stream (requires boto3 + AWS credentials)
- `TrackedLLMClient`  — wraps `client.chat.completions.create(...)`,
                         measures latency, extracts token usage, computes
                         cost, and dispatches a UsageRecord to every
                         configured backend — even on errors, so failed
                         (but billed) requests are still audited.
"""

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional


# ---------------------------------------------------------------------------
# Pricing table — $ per 1,000 tokens: (input_price, output_price)
# Groq's current hosted open-weight models are free ($0). Edit/add rows as
# needed, or load this from a config file / env var in a real deployment.
# ---------------------------------------------------------------------------
PRICING = {
    "llama-3.3-70b-versatile": (0.0, 0.0),
    "llama-3.1-8b-instant": (0.0, 0.0),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
}
DEFAULT_PRICING = (0.0, 0.0)


@dataclass
class UsageRecord:
    request_id: str
    timestamp: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    status: str                 # "success" or "error"
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
class LogBackend:
    """Interface every logging backend must implement."""

    def log(self, record: UsageRecord) -> None:
        raise NotImplementedError


class FileLogBackend(LogBackend):
    """Writes one JSON object per line to a local file, with automatic
    rotation so the log doesn't grow unbounded in a long-running service."""

    def __init__(
        self,
        path: str = "usage_log.jsonl",
        max_bytes: int = 5 * 1024 * 1024,  # 5 MB per file
        backup_count: int = 5,             # keep 5 rotated files
    ):
        self._lock = threading.Lock()
        self._logger = logging.getLogger(f"usage_logger.file.{id(self)}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(handler)

    def log(self, record: UsageRecord) -> None:
        with self._lock:
            self._logger.info(json.dumps(asdict(record)))


class CloudWatchLogBackend(LogBackend):
    """Streams usage records to AWS CloudWatch Logs.

    Requires `boto3` and valid AWS credentials (via environment variables,
    an AWS profile, or an IAM role if running on AWS infrastructure).
    Creates the log group/stream automatically if they don't exist yet.
    """

    def __init__(self, log_group: str, log_stream: str, region_name: Optional[str] = None):
        try:
            import boto3
        except ImportError as e:
            raise ImportError(
                "boto3 is required for CloudWatchLogBackend. Install it with: "
                "pip install boto3"
            ) from e

        self._client = boto3.client("logs", region_name=region_name)
        self._log_group = log_group
        self._log_stream = log_stream
        self._sequence_token = None
        self._lock = threading.Lock()
        self._ensure_group_and_stream()

    def _ensure_group_and_stream(self) -> None:
        try:
            self._client.create_log_group(logGroupName=self._log_group)
        except self._client.exceptions.ResourceAlreadyExistsException:
            pass
        try:
            self._client.create_log_stream(
                logGroupName=self._log_group, logStreamName=self._log_stream
            )
        except self._client.exceptions.ResourceAlreadyExistsException:
            pass

    def log(self, record: UsageRecord) -> None:
        with self._lock:
            event = {
                "logGroupName": self._log_group,
                "logStreamName": self._log_stream,
                "logEvents": [
                    {
                        "timestamp": int(time.time() * 1000),
                        "message": json.dumps(asdict(record)),
                    }
                ],
            }
            if self._sequence_token:
                event["sequenceToken"] = self._sequence_token

            response = self._client.put_log_events(**event)
            self._sequence_token = response.get("nextSequenceToken")


# ---------------------------------------------------------------------------
# The wrapper itself
# ---------------------------------------------------------------------------
class TrackedLLMClient:
    """Wraps an OpenAI-compatible client so every chat completion request
    is automatically logged for cost auditing — including failed requests.

    Usage:
        raw_client = OpenAI(api_key=..., base_url=...)
        client = TrackedLLMClient(raw_client, backends=[FileLogBackend()])
        response = client.chat_completion(model="...", messages=[...])
    """

    def __init__(self, client, backends: list[LogBackend], pricing: Optional[dict] = None):
        if not backends:
            raise ValueError("At least one LogBackend is required.")
        self._client = client
        self._backends = backends
        self._pricing = pricing or PRICING

    def chat_completion(self, model: str, messages: list[dict], **kwargs):
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        try:
            response = self._client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            record = UsageRecord(
                request_id=request_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                model=model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
                latency_ms=round(latency_ms, 2),
                status="error",
                error=str(e),
            )
            self._dispatch(record)
            raise  # re-raise so the caller's error handling still runs

        latency_ms = (time.perf_counter() - start) * 1000
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) if usage else 0

        input_price, output_price = self._pricing.get(model, DEFAULT_PRICING)
        cost = (prompt_tokens / 1000) * input_price + (completion_tokens / 1000) * output_price

        record = UsageRecord(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=round(cost, 6),
            latency_ms=round(latency_ms, 2),
            status="success",
        )
        self._dispatch(record)
        return response

    def _dispatch(self, record: UsageRecord) -> None:
        for backend in self._backends:
            try:
                backend.log(record)
            except Exception as log_error:
                # Logging must never crash the actual application request.
                print(f"[usage_logger] WARNING: failed to write log ({backend.__class__.__name__}): {log_error}")


def backends_from_env() -> list[LogBackend]:
    """Convenience factory: choose backends based on environment variables,
    so the same code works locally and in production without edits.

    LOG_BACKEND=file        -> FileLogBackend only (default)
    LOG_BACKEND=cloudwatch  -> CloudWatchLogBackend only
    LOG_BACKEND=both        -> both backends active at once
    """
    choice = os.environ.get("LOG_BACKEND", "file").lower()
    backends: list[LogBackend] = []

    if choice in ("file", "both"):
        backends.append(FileLogBackend(path=os.environ.get("USAGE_LOG_PATH", "usage_log.jsonl")))

    if choice in ("cloudwatch", "both"):
        backends.append(
            CloudWatchLogBackend(
                log_group=os.environ.get("CLOUDWATCH_LOG_GROUP", "/llm/usage"),
                log_stream=os.environ.get("CLOUDWATCH_LOG_STREAM", "requests"),
                region_name=os.environ.get("AWS_REGION"),
            )
        )

    return backends