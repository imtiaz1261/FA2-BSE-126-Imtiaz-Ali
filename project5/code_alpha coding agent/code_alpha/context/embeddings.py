import hashlib
import math
import re
from typing import Protocol

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class Embedder(Protocol):
    dim: int
    def embed(self, text: str) -> list[float]: ...


class HashEmbedder:
    """Deterministic, dependency-free embedding via the hashing trick.
    Swap this for a real code-tuned model (e.g. text-embedding-3-small,
    or a local code embedding model) behind the same `.embed()` interface
    — nothing else in the pipeline needs to change.
    """

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            return vec
        for tok in tokens:
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
