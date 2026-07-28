"""src/bm25_retriever.py — Sparse, keyword-based retrieval using BM25.

BM25 scores documents by term overlap with the query, weighted by term
rarity (rare, distinctive words matter more than common ones) and
normalized for document length. It excels at exact keyword/term matches
("reusable rocket", "dietary fiber") but has no notion of meaning — it
won't connect a query about "global warming" to a document that only
says "climate change" unless both phrasings share literal words.
"""

from __future__ import annotations

import pickle
import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi


@dataclass
class RetrievedDocument:
    """A single retrieved document with its score and source metadata.
    Shared across all retriever types so downstream code (fusion,
    reranking, evaluation) works identically regardless of which
    retriever produced the result.
    """

    doc_id: str
    text: str
    score: float
    source: str  # "bm25", "vector", "hybrid", or "reranked"


def tokenize(text: str) -> list[str]:
    """Simple, dependency-free tokenizer: lowercase, strip punctuation,
    split on whitespace. BM25 only needs token overlap counting, not a
    linguistically sophisticated tokenizer."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text.split()


class BM25Retriever:
    """Wraps rank_bm25's BM25Okapi with document ID tracking and a
    consistent RetrievedDocument output format."""

    def __init__(self) -> None:
        self._bm25: BM25Okapi | None = None
        self._doc_ids: list[str] = []
        self._doc_texts: list[str] = []

    def build_index(self, documents: dict[str, str]) -> None:
        """Builds the BM25 index from a {doc_id: text} mapping.

        Raises ValueError on an empty document set rather than silently
        building a useless index — an empty vector database / index is
        one of the required error-handling cases for retrieval systems.
        """
        if not documents:
            raise ValueError("Cannot build a BM25 index from an empty document set.")

        self._doc_ids = list(documents.keys())
        self._doc_texts = list(documents.values())
        tokenized_corpus = [tokenize(text) for text in self._doc_texts]
        self._bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        """Returns the top_k documents ranked by BM25 score, highest first."""
        if self._bm25 is None:
            raise RuntimeError("Index not built yet. Call build_index() first.")

        tokenized_query = tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        ranked_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]

        return [
            RetrievedDocument(
                doc_id=self._doc_ids[i],
                text=self._doc_texts[i],
                score=float(scores[i]),
                source="bm25",
            )
            for i in ranked_indices
        ]

    def save(self, path: Path) -> None:
        """Persists the index to disk so it doesn't need rebuilding
        every run."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "bm25": self._bm25,
                    "doc_ids": self._doc_ids,
                    "doc_texts": self._doc_texts,
                },
                f,
            )

    @classmethod
    def load(cls, path: Path) -> "BM25Retriever":
        """Loads a previously saved index from disk."""
        if not path.exists():
            raise FileNotFoundError(
                f"BM25 index not found at '{path}'. Run ingest.py first."
            )
        with open(path, "rb") as f:
            data = pickle.load(f)

        retriever = cls()
        retriever._bm25 = data["bm25"]
        retriever._doc_ids = data["doc_ids"]
        retriever._doc_texts = data["doc_texts"]
        return retriever
