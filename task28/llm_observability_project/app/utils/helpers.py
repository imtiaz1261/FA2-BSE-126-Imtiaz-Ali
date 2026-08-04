import hashlib


def hash_text(text: str, length: int = 16) -> str:
    """Short, stable hash used for query fingerprinting in metrics."""
    return hashlib.sha256(text.encode()).hexdigest()[:length]
