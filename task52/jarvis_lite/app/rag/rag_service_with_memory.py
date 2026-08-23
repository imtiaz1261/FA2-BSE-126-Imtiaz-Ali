"""
Enhanced RAG Service with memory support for multi-turn conversations.

Combines conversation history with document retrieval for context-aware responses.
"""

import logging
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.core.exceptions import GenerationError
from app.embeddings.base import BaseEmbeddingProvider
from app.memory.memory_service import MemoryService
from app.rag.prompt_builder import build_prompt
from app.retriever.retriever import RetrievedChunk, Retriever
from app.vectorstore.base import BaseVectorStore

logger = logging.getLogger(__name__)


class RAGServiceWithMemory:
    """RAG Service enhanced with conversation memory."""

    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        retriever: Optional[Retriever] = None,
        memory_type: str = "buffer",
        max_context: int = 5,
    ) -> None:
        """
        Initialize RAG service with memory.
        
        Args:
            vector_store: Vector store instance
            embedding_provider: Embedding provider instance
            retriever: Retriever instance
            memory_type: "buffer" or "summary"
            max_context: Max messages to keep
        """
        self._retriever = retriever or Retriever(vector_store, embedding_provider)
        self._llm_client: Optional[Any] = None
        self._memory = MemoryService(memory_type=memory_type, max_context=max_context)
        logger.info(f"Initialized RAGServiceWithMemory with {memory_type} memory")

    def _get_llm_client(self) -> Any:
        if self._llm_client is None:
            if settings.EMBEDDING_PROVIDER == "gemini" or settings.GEMINI_API_KEY:
                from app.llm.gemini_llm import GeminiLLMProvider
                self._llm_client = GeminiLLMProvider()
            else:
                from openai import OpenAI
                if not settings.OPENAI_API_KEY:
                    raise GenerationError(
                        "OPENAI_API_KEY is not set — needed for final-answer generation."
                    )
                self._llm_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._llm_client

    def query(self, query: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        """
        Query with memory support.
        
        Returns:
            {answer, sources, retrieved_chunks, memory_context}
        """
        # Add user message to memory
        self._memory.add_user_message(query)
        
        # Retrieve relevant documents
        retrieved = self._retriever.retrieve(query, top_k)

        if not retrieved:
            logger.info("No chunks retrieved for query: %r", query[:80])
            fallback = "I don't have any relevant documents to answer that yet — try uploading some first."
            self._memory.add_assistant_message(fallback)
            return {
                "answer": fallback,
                "sources": [],
                "retrieved_chunks": [],
                "memory_context": self._memory.to_dict(),
            }

        # Build messages with memory context
        memory_messages = self._memory.get_context_for_prompt()
        context_messages = build_prompt(query, retrieved)
        
        # Merge memory context with document context
        # Remove the last user message from context_messages since it's already in memory_messages
        if context_messages and context_messages[-1].get("role") == "user":
            context_messages = context_messages[:-1]
        
        messages = memory_messages + context_messages
        
        answer = self._generate(messages)
        self._memory.add_assistant_message(answer)

        return {
            "answer": answer,
            "sources": self._dedupe_sources(retrieved),
            "retrieved_chunks": [
                {"content": c.content, "metadata": c.metadata, "score": round(c.score, 4)} for c in retrieved
            ],
            "memory_context": self._memory.to_dict(),
        }

    def _generate(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_llm_client()
        
        try:
            # Check if using Gemini or OpenAI
            if hasattr(client, 'generate'):  # Gemini provider
                return client.generate(messages)
            else:  # OpenAI client
                from openai import APIError, AuthenticationError
                try:
                    response = client.chat.completions.create(
                        model=settings.OPENAI_CHAT_MODEL,
                        temperature=settings.LLM_TEMPERATURE,
                        messages=messages,
                    )
                except AuthenticationError as exc:
                    raise GenerationError("OpenAI rejected the API key. Check OPENAI_API_KEY.") from exc
                except APIError as exc:
                    logger.exception("LLM generation call failed")
                    raise GenerationError(f"Answer generation failed: {exc}") from exc
                return response.choices[0].message.content or ""
        except GenerationError:
            raise
        except Exception as exc:
            logger.exception("LLM generation call failed")
            raise GenerationError(f"Answer generation failed: {exc}") from exc

    @staticmethod
    def _dedupe_sources(chunks: List[RetrievedChunk]) -> List[Dict[str, Any]]:
        seen = set()
        sources: List[Dict[str, Any]] = []
        for chunk in chunks:
            name = chunk.metadata.get("document_name", "unknown")
            page = chunk.metadata.get("page")
            key = (name, page)
            if key in seen:
                continue
            seen.add(key)
            sources.append({"document_name": name, "page": page, "chunk_id": chunk.metadata.get("chunk_id")})
        return sources

    def clear_memory(self) -> None:
        """Clear conversation memory."""
        self._memory.clear()
        logger.info("Cleared conversation memory")

    def get_memory_summary(self) -> Optional[str]:
        """Get memory summary."""
        return self._memory.get_summary()

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get full conversation history."""
        return self._memory.get_context_for_prompt()
