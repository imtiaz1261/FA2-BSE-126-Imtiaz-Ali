from dataclasses import dataclass
from typing import Protocol

# --- Schema for the production backend (pgvector) --------------------------
# Scoped per repository via repo_id, so one Postgres instance can serve
# many indexed repos without cross-contamination in similarity search.
PGVECTOR_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS repositories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    root_path   TEXT NOT NULL UNIQUE,
    last_indexed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS code_chunks (
    id          TEXT PRIMARY KEY,          -- "<file>::<symbol>:<line>"
    repo_id     UUID REFERENCES repositories(id) ON DELETE CASCADE,
    file        TEXT NOT NULL,
    symbol_name TEXT NOT NULL,
    kind        TEXT NOT NULL,             -- function | class | file
    start_line  INT NOT NULL,
    end_line    INT NOT NULL,
    text        TEXT NOT NULL,
    embedding   VECTOR(256) NOT NULL
);
CREATE INDEX IF NOT EXISTS code_chunks_embedding_idx
    ON code_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX IF NOT EXISTS code_chunks_repo_idx ON code_chunks (repo_id);

CREATE TABLE IF NOT EXISTS symbols (
    id          SERIAL PRIMARY KEY,
    repo_id     UUID REFERENCES repositories(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL,
    file        TEXT NOT NULL,
    start_line  INT NOT NULL,
    end_line    INT NOT NULL,
    calls       TEXT[] DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS symbols_name_idx ON symbols (repo_id, name);

CREATE TABLE IF NOT EXISTS file_dependencies (
    repo_id     UUID REFERENCES repositories(id) ON DELETE CASCADE,
    file        TEXT NOT NULL,
    imports     TEXT NOT NULL,             -- resolved repo-local file, or raw module name
    PRIMARY KEY (repo_id, file, imports)
);
"""


@dataclass
class SearchHit:
    chunk_id: str
    score: float
    metadata: dict


class VectorStore(Protocol):
    def upsert(self, chunk_id: str, vector: list[float], metadata: dict) -> None: ...
    def delete_by_file(self, file: str) -> None: ...
    def search(self, vector: list[float], top_k: int) -> list[SearchHit]: ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot  # vectors are already L2-normalized by the embedder


class InMemoryVectorStore:
    """Drop-in for local dev / tests. Swap for a pgvector-backed store in
    production using PGVECTOR_SCHEMA_SQL above — same upsert/search interface."""

    def __init__(self):
        self._rows: dict[str, tuple[list[float], dict]] = {}

    def upsert(self, chunk_id: str, vector: list[float], metadata: dict) -> None:
        self._rows[chunk_id] = (vector, metadata)

    def delete_by_file(self, file: str) -> None:
        for cid in [k for k, (_, meta) in self._rows.items() if meta.get("file") == file]:
            del self._rows[cid]

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchHit]:
        scored = [
            SearchHit(chunk_id=cid, score=_cosine(vector, vec), metadata=meta)
            for cid, (vec, meta) in self._rows.items()
        ]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]
