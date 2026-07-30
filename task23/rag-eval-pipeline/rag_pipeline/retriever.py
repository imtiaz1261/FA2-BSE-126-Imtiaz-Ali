"""
Retriever component of the RAG pipeline.

Three backends are supported behind one interface:

  - "openai_faiss": FAISS + LangChain's OpenAIEmbeddings. Requires OPENAI_API_KEY.
  - "hf_faiss": FAISS + local sentence-transformers embeddings (no API key,
    no network call). Used with the Groq LLM backend, since Groq only serves
    chat completions and has no embeddings endpoint of its own.
  - "tfidf": dependency-light fallback used for local development, CI, and
    fully offline demos. Pure scikit-learn.

Swapping backends never changes the interface the rest of the pipeline sees
(`Retriever.retrieve(query, k) -> list[str]`), so the evaluator and chatbot
code is identical regardless of which backend is active.
"""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rag_pipeline.knowledge_base import Document, get_documents
from utils.logger import get_logger

logger = get_logger(__name__)


class Retriever:
    """Retrieves the top-k most relevant document chunks for a query."""

    def __init__(self, backend: str = "tfidf", documents: list[Document] | None = None):
        self.backend = backend
        self.documents = documents if documents is not None else get_documents()
        self._texts = [d.text for d in self.documents]

        if backend == "tfidf":
            self._vectorizer = TfidfVectorizer(stop_words="english")
            self._matrix = self._vectorizer.fit_transform(self._texts)
        elif backend == "openai_faiss":
            self._init_openai_faiss()
        elif backend == "hf_faiss":
            self._init_hf_faiss()
        else:
            raise ValueError(f"Unknown retriever backend: {backend}")

        logger.info("Retriever initialized with backend='%s' (%d docs)", backend, len(self.documents))

    def _init_openai_faiss(self) -> None:
        """Lazily import heavy/optional deps only when this backend is selected."""
        from langchain_community.vectorstores import FAISS
        from langchain_openai import OpenAIEmbeddings

        from config.settings import settings

        embeddings = OpenAIEmbeddings(
            model=settings.embedding_model, openai_api_key=settings.openai_api_key
        )
        self._faiss_store = FAISS.from_texts(
            texts=self._texts,
            embedding=embeddings,
            metadatas=[{"doc_id": d.doc_id} for d in self.documents],
        )

    def _init_hf_faiss(self) -> None:
        """FAISS vector store backed by local sentence-transformers embeddings.

        Used with the Groq LLM backend: Groq serves chat completions only, no
        embeddings endpoint, so embeddings run locally instead — no API key
        or network call needed for this half of the pipeline.
        """
        from langchain_community.vectorstores import FAISS
        from langchain_huggingface import HuggingFaceEmbeddings

        from config.settings import settings

        embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        self._faiss_store = FAISS.from_texts(
            texts=self._texts,
            embedding=embeddings,
            metadatas=[{"doc_id": d.doc_id} for d in self.documents],
        )

    def retrieve(self, query: str, k: int = 3) -> list[str]:
        """Return the top-k most relevant document chunks for `query`."""
        if self.backend == "tfidf":
            return self._retrieve_tfidf(query, k)
        # Both "openai_faiss" and "hf_faiss" share identical retrieval logic —
        # they only differ in which embedding model built self._faiss_store.
        return self._retrieve_faiss(query, k)

    def _retrieve_faiss(self, query: str, k: int) -> list[str]:
        results = self._faiss_store.similarity_search(query, k=k)
        return [r.page_content for r in results]

    def _retrieve_tfidf(self, query: str, k: int) -> list[str]:
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()
        top_indices = scores.argsort()[::-1][:k]
        # Filter out zero-similarity matches (nothing relevant found at all)
        return [self._texts[i] for i in top_indices if scores[i] > 0.0]
