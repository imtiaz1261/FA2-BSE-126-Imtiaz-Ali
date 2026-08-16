"""
semantic_search.py
-------------------
A meaning-based (semantic) search engine for a CSV dataset of text
(e.g., 100 product descriptions), instead of plain keyword matching.

Two backends are supported:

1. "lsa"  (default, works fully OFFLINE)
   TF-IDF vectors are reduced with Truncated SVD (Latent Semantic
   Analysis). This groups words that tend to appear in similar
   contexts into shared latent "concepts", so a query like
   "shoes for jogging" can match a product described as
   "lightweight running sneakers" even though they share almost no
   exact words.

2. "embeddings" (optional, needs internet once to download a model)
   Uses the `sentence-transformers` library to compute deep neural
   sentence embeddings (all-MiniLM-L6-v2). This gives noticeably
   better semantic understanding than LSA, at the cost of a one-time
   model download (~90MB) and a heavier dependency.
   Install with:  pip install sentence-transformers
   Then run search_cli.py / app.py with --backend embeddings

Usage:
    from semantic_search import SemanticSearchEngine
    engine = SemanticSearchEngine.from_csv("data/products.csv")
    results = engine.search("warm jacket for cold weather", top_k=5)
"""

from __future__ import annotations

import csv
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class SearchResult:
    row: Dict[str, str]
    score: float


class SemanticSearchEngine:
    def __init__(self, backend: str = "lsa", n_components: int = 100):
        """
        backend: "lsa" (offline, default) or "embeddings" (needs
                 sentence-transformers + internet on first run).
        n_components: number of latent semantic dimensions for LSA.
        """
        self.backend = backend
        self.n_components = n_components
        self.records: List[Dict[str, str]] = []
        self.fields_for_text: List[str] = []
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._svd: Optional[TruncatedSVD] = None
        self._doc_vectors: Optional[np.ndarray] = None
        self._st_model = None  # sentence-transformers model, lazy-loaded

    # ------------------------------------------------------------------ #
    # Loading data
    # ------------------------------------------------------------------ #
    @classmethod
    def from_csv(
        cls,
        csv_path: str,
        text_fields: Optional[List[str]] = None,
        backend: str = "lsa",
        n_components: int = 100,
    ) -> "SemanticSearchEngine":
        """
        Build the engine directly from a CSV file.

        text_fields: which CSV columns to combine into the searchable
                     text for each row. Defaults to every column that
                     is not obviously an id, or to all columns if none
                     look textual.
        """
        engine = cls(backend=backend, n_components=n_components)
        rows = engine._read_csv(csv_path)
        if not rows:
            raise ValueError(f"No rows found in {csv_path}")

        if text_fields is None:
            text_fields = [
                c for c in rows[0].keys() if c.lower() not in ("id",)
            ]

        engine.records = rows
        engine.fields_for_text = text_fields
        engine._build_index()
        return engine

    @staticmethod
    def _read_csv(csv_path: str) -> List[Dict[str, str]]:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [dict(row) for row in reader]

    def _row_to_text(self, row: Dict[str, str]) -> str:
        return " . ".join(str(row.get(f, "")) for f in self.fields_for_text)

    # ------------------------------------------------------------------ #
    # Index building
    # ------------------------------------------------------------------ #
    def _build_index(self) -> None:
        texts = [self._row_to_text(r) for r in self.records]

        if self.backend == "embeddings":
            self._build_embedding_index(texts)
        else:
            self._build_lsa_index(texts)

    def _build_lsa_index(self, texts: List[str]) -> None:
        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.9,
            sublinear_tf=True,
        )
        tfidf = self._vectorizer.fit_transform(texts)

        # n_components can't exceed min(n_samples, n_features) - 1
        max_components = min(tfidf.shape) - 1
        n_components = max(2, min(self.n_components, max_components))
        self._svd = TruncatedSVD(n_components=n_components, random_state=42)
        reduced = self._svd.fit_transform(tfidf)
        self._doc_vectors = normalize(reduced)

    def _build_embedding_index(self, texts: List[str]) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "backend='embeddings' requires: pip install sentence-transformers"
            ) from e
        self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
        vectors = self._st_model.encode(texts, normalize_embeddings=True)
        self._doc_vectors = np.array(vectors)

    # ------------------------------------------------------------------ #
    # Querying
    # ------------------------------------------------------------------ #
    def _embed_query(self, query: str) -> np.ndarray:
        if self.backend == "embeddings":
            vec = self._st_model.encode([query], normalize_embeddings=True)
            return np.array(vec)
        else:
            tfidf_vec = self._vectorizer.transform([query])
            reduced = self._svd.transform(tfidf_vec)
            return normalize(reduced)

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[SearchResult]:
        """
        Return the top_k most semantically similar records to `query`.

        filters: optional exact-match filters on record fields, e.g.
                 {"category": "Electronics"}
        """
        if not query or not query.strip():
            return []

        query_vec = self._embed_query(query)
        sims = cosine_similarity(query_vec, self._doc_vectors)[0]

        order = np.argsort(-sims)
        results: List[SearchResult] = []
        for idx in order:
            if len(results) >= top_k:
                break
            score = float(sims[idx])
            if score < min_score:
                continue
            row = self.records[idx]
            if filters and not all(
                str(row.get(k, "")).lower() == str(v).lower()
                for k, v in filters.items()
            ):
                continue
            results.append(SearchResult(row=row, score=score))
        return results

    # ------------------------------------------------------------------ #
    # Persistence (avoid recomputing the index every run)
    # ------------------------------------------------------------------ #
    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: str) -> "SemanticSearchEngine":
        with open(path, "rb") as f:
            return pickle.load(f)


if __name__ == "__main__":
    # Quick smoke test
    engine = SemanticSearchEngine.from_csv(
        str(Path(__file__).parent / "data" / "products.csv")
    )
    for q in ["shoes for jogging", "something to keep me warm in winter", "healthy snack"]:
        print(f"\nQuery: {q}")
        for r in engine.search(q, top_k=3):
            print(f"  [{r.score:.3f}] {r.row['name']} — {r.row['description'][:70]}...")
