"""
keyword_search.py
--------------------
A traditional TF-IDF based keyword search baseline, used purely to
demonstrate (bonus feature) how semantic search differs from classic
keyword matching. Semantic search can find conceptually related
documents even when they don't share exact words with the query;
keyword search cannot.
"""

from __future__ import annotations

from typing import List, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .preprocessing import normalize_for_keyword_search


class KeywordSearchEngine:
    """Simple TF-IDF + cosine-similarity keyword search engine."""

    def __init__(self):
        self._vectorizer = TfidfVectorizer()
        self._matrix = None
        self._metadatas: List[Dict[str, Any]] = []

    def fit(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        normalized = [normalize_for_keyword_search(t) for t in texts]
        self._matrix = self._vectorizer.fit_transform(normalized)
        self._metadatas = metadatas

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self._matrix is None:
            raise RuntimeError("KeywordSearchEngine.fit() must be called before search().")

        query_norm = normalize_for_keyword_search(query)
        query_vec = self._vectorizer.transform([query_norm])
        scores = cosine_similarity(query_vec, self._matrix)[0]

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue
            results.append({"score": float(scores[idx]), "metadata": self._metadatas[idx]})
        return results
