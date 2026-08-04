from app.config.settings import get_settings

settings = get_settings()

_langfuse_client = None
if settings.observability_enabled:
    try:
        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception:
        _langfuse_client = None


def log_trace(trace_data: dict):
    """
    Sends a trace to Langfuse if configured. Never raises — observability
    failures must not break the actual chat request.
    """
    if _langfuse_client is None:
        return
    try:
        _langfuse_client.trace(
            name="llm_chat_request",
            input=trace_data.get("query"),
            output=trace_data.get("response"),
            metadata={
                k: v for k, v in trace_data.items()
                if k not in ("query", "response")
            },
        )
    except Exception as e:
        print(f"[observability] failed to log trace: {e}")
