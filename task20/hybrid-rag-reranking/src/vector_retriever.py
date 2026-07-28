"""src/vector_retriever.py — Dense, semantic retrieval using FAISS +
HuggingFace sentence embeddings.

Unlike BM25's literal keyword matching, vector search embeds both the
query and every document into the same numeric "meaning space," then
finds documents whose vectors are closest to the query's vector. This
lets it match a query like "global warming" to a document that only
says "climate change" — they land near each other in meaning-space even
though they share no exact words, which is precisely what BM25 misses.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from src.bm25_retriever import RetrievedDocument


class VectorRetriever:
    """Wraps a FAISS vector store with document ID tracking and a
    consistent RetrievedDocument output format, matching BM25Retriever's
    interface so both can be used interchangeably by the hybrid fusion
    logic."""

    def __init__(self, embedding_model_name: str) -> None:
        self._embedding_model_name = embedding_model_name
        self._embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
        self._vector_store: FAISS | None = None

    def build_index(self, documents: dict[str, str]) -> None:
        """Builds the FAISS index from a {doc_id: text} mapping."""
        if not documents:
            raise ValueError("Cannot build a vector index from an empty document set.")

        langchain_docs = [
            Document(page_content=text, metadata={"doc_id": doc_id})
            for doc_id, text in documents.items()
        ]
        self._vector_store = FAISS.from_documents(langchain_docs, self._embeddings)

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        """Returns the top_k documents ranked by embedding similarity,
        highest first.

        FAISS's similarity_search_with_score returns L2 distance (lower
        is better), so we convert it to a similarity score (higher is
        better) for consistency with BM25's scoring direction — this
        matters a lot for the hybrid fusion step, which assumes "higher
        score = more relevant" from both retrievers.
        """
        if self._vector_store is None:
            raise RuntimeError("Index not built yet. Call build_index() first.")

        results_with_scores = self._vector_store.similarity_search_with_score(
            query, k=top_k
        )

        retrieved = []
        for doc, distance in results_with_scores:
            similarity = 1.0 / (1.0 + distance)  # convert distance -> similarity, higher=better
            retrieved.append(
                RetrievedDocument(
                    doc_id=doc.metadata["doc_id"],
                    text=doc.page_content,
                    score=similarity,
                    source="vector",
                )
            )
        return retrieved

    def save(self, path: Path) -> None:
        if self._vector_store is None:
            raise RuntimeError("Nothing to save — build the index first.")
        path.mkdir(parents=True, exist_ok=True)
        self._vector_store.save_local(str(path))

    def load(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(
                f"Vector index not found at '{path}'. Run ingest.py first."
            )
        self._vector_store = FAISS.load_local(
            str(path), self._embeddings, allow_dangerous_deserialization=True
        )
