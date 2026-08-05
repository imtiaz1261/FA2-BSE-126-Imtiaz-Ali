"""
Langfuse observability service — Phase 17.

Provides a thin, safe wrapper around the Langfuse Python SDK so that:
  - Tracing is completely optional (degrades gracefully when keys are absent)
  - Every LLM call, RAG retrieval, and Agent run is recorded as a
    structured trace with generations, spans, token counts and cost estimates
  - A single `get_langfuse()` singleton is reused across requests

Usage pattern
-------------
    from app.services.langfuse_service import get_langfuse, create_trace

    lf = get_langfuse()          # None when not configured
    trace = create_trace(lf, name="chat", user_id=str(uid), metadata={...})
    gen = start_generation(trace, name="llm-reply", model="gpt-4o-mini",
                           input_messages=[...])
    ...
    finish_generation(gen, output="assistant reply", usage={...})
    flush(lf)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton initialisation
# ---------------------------------------------------------------------------

_langfuse_client = None
_init_attempted = False


def get_langfuse():
    """
    Return the Langfuse client singleton, or None if tracing is disabled
    (missing keys) or the package is unavailable.
    """
    global _langfuse_client, _init_attempted
    if _init_attempted:
        return _langfuse_client

    _init_attempted = True

    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.info("Langfuse tracing disabled — LANGFUSE_PUBLIC_KEY/SECRET_KEY not set.")
        return None

    try:
        from langfuse import Langfuse  # lazy import

        _langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        logger.info("Langfuse tracing enabled (host: %s)", settings.LANGFUSE_HOST)
    except ImportError:
        logger.warning("langfuse package not installed — tracing disabled.")
    except Exception as exc:
        logger.warning("Langfuse initialisation failed: %s", exc)

    return _langfuse_client


# ---------------------------------------------------------------------------
# Trace helpers
# ---------------------------------------------------------------------------


def create_trace(
    lf,
    name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
):
    """Create a new Langfuse trace and return it (or None if lf is None)."""
    if lf is None:
        return None
    try:
        return lf.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags or [],
        )
    except Exception as exc:
        logger.debug("Langfuse create_trace failed: %s", exc)
        return None


def start_generation(
    trace,
    name: str,
    model: str,
    input_messages: List[Dict],
    metadata: Optional[Dict] = None,
):
    """Start a generation span on a trace."""
    if trace is None:
        return None
    try:
        return trace.generation(
            name=name,
            model=model,
            input=input_messages,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.debug("Langfuse start_generation failed: %s", exc)
        return None


def finish_generation(
    generation,
    output: str,
    usage: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
):
    """End a generation span with the output and token usage."""
    if generation is None:
        return
    try:
        kwargs: Dict[str, Any] = {"output": output}
        if usage:
            kwargs["usage"] = usage
        if metadata:
            kwargs["metadata"] = metadata
        generation.end(**kwargs)
    except Exception as exc:
        logger.debug("Langfuse finish_generation failed: %s", exc)


def start_span(trace, name: str, metadata: Optional[Dict] = None):
    """Start a generic span (e.g. for RAG retrieval, agent steps)."""
    if trace is None:
        return None
    try:
        return trace.span(name=name, metadata=metadata or {})
    except Exception as exc:
        logger.debug("Langfuse start_span failed: %s", exc)
        return None


def finish_span(span, output: Optional[str] = None, metadata: Optional[Dict] = None):
    """End a span."""
    if span is None:
        return
    try:
        kwargs: Dict[str, Any] = {}
        if output is not None:
            kwargs["output"] = output
        if metadata:
            kwargs["metadata"] = metadata
        span.end(**kwargs)
    except Exception as exc:
        logger.debug("Langfuse finish_span failed: %s", exc)


def score_trace(trace, name: str, value: float, comment: str = ""):
    """Attach a numeric score to a trace (e.g. relevance, user rating)."""
    if trace is None:
        return
    try:
        trace.score(name=name, value=value, comment=comment)
    except Exception as exc:
        logger.debug("Langfuse score_trace failed: %s", exc)


def flush(lf):
    """Flush pending events to the Langfuse backend (call at end of request)."""
    if lf is None:
        return
    try:
        lf.flush()
    except Exception as exc:
        logger.debug("Langfuse flush failed: %s", exc)
