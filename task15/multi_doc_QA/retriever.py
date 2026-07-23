"""
retriever.py
------------
Retriever construction and manual similarity-search helper.

The retriever is the component that, given a user's query, converts
it into an embedding and finds the Top-K most similar chunks stored
in the vector database. LangChain's `VectorStore.as_retriever()`
gives us a standard `Retriever` interface that plugs directly into a
RetrievalQA chain.
"""

from typing import List

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_core.retrievers import BaseRetriever

from config import TOP_K
from utils import get_logger

logger = get_logger(__name__)


def get_retriever(vector_store: VectorStore, top_k: int = TOP_K) -> BaseRetriever:
    """
    Build a retriever from a vector store using similarity search.

    Parameters
    ----------
    vector_store : VectorStore
    top_k : int
        Number of most relevant chunks to retrieve per query.

    Returns
    -------
    BaseRetriever
    """
    logger.info("Creating retriever with top_k=%d", top_k)
    return vector_store.as_retriever(search_type="similarity", search_kwargs={"k": top_k})


def retrieve_context(vector_store: VectorStore, query: str, top_k: int = TOP_K) -> List[Document]:
    """
    Directly run a similarity search for a query and return the raw
    matched chunks (useful for debugging / displaying retrieved context
    to the user, independent of the QA chain).
    """
    logger.info("Running similarity search for query: %r (top_k=%d)", query, top_k)
    results = vector_store.similarity_search(query, k=top_k)
    logger.info("Retrieved %d chunk(s).", len(results))
    return results