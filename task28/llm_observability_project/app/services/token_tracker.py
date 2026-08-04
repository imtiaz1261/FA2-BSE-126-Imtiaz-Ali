import tiktoken

_ENCODING = None


def _get_encoding():
    global _ENCODING
    if _ENCODING is None:
        try:
            _ENCODING = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _ENCODING = None
    return _ENCODING


def count_tokens(text: str) -> int:
    """
    Estimated token count via tiktoken's cl100k_base encoding.
    NOTE: this is an ESTIMATE — Groq/Llama models don't use OpenAI's tokenizer,
    so real usage always prefers the provider's returned usage object
    (see llm_service.py). This function is only the documented fallback.
    """
    enc = _get_encoding()
    if enc is None:
        return max(1, len(text) // 4)  # crude fallback if tiktoken is unavailable
    return len(enc.encode(text))
