"""Top-level RAG pipeline: retrieve -> build prompt -> generate -> cite.

This is the class future phases (FastAPI routes, the agent, voice)
call into — nothing outside this file talks to the LLM for answer
generation, so provider/model changes stay contained here.
"""

import logging
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.core.exceptions import GenerationError
from app.embeddings.base import BaseEmbeddingProvider
from app.rag.prompt_builder import build_prompt
from app.retriever.retriever import RetrievedChunk, Retriever
from app.vectorstore.base import BaseVectorStore

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        retriever: Optional[Retriever] = None,
    ) -> None:
        self._retriever = retriever or Retriever(vector_store, embedding_provider)
        self._llm_client: Optional[Any] = None

    def _get_llm_client(self) -> Any:
        if self._llm_client is None:
            if settings.EMBEDDING_PROVIDER == "gemini" or settings.GEMINI_API_KEY:
                from app.llm.gemini_llm import GeminiLLMProvider
                self._llm_client = GeminiLLMProvider()
            else:
                from openai import OpenAI
                if not settings.OPENAI_API_KEY:
                    raise GenerationError(
                        "OPENAI_API_KEY is not set — needed for final-answer generation "
                        "even when embeddings use the huggingface provider."
                    )
                self._llm_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._llm_client

    def query(self, query: str, top_k: Optional[int] = None, use_llm_fallback: bool = True) -> Dict[str, Any]:
        """Runs the full pipeline and returns `{answer, sources, retrieved_chunks}`.
        
        Args:
            query: User's question
            top_k: Number of top results to retrieve
            use_llm_fallback: If True, use LLM to answer when no documents found
        """
        retrieved = self._retriever.retrieve(query, top_k)

        if not retrieved:
            logger.info("No chunks retrieved for query: %r", query[:80])
            
            # If LLM fallback enabled, use LLM to answer the question
            if use_llm_fallback:
                logger.info("Using LLM fallback for query: %r", query[:80])
                try:
                    answer = self._generate_llm_fallback(query)
                    return {
                        "answer": answer,
                        "sources": [],
                        "retrieved_chunks": [],
                        "source_type": "llm_fallback",  # Indicate this came from LLM, not documents
                    }
                except Exception as e:
                    logger.warning(f"LLM fallback failed: {e}")
                    return {
                        "answer": f"I couldn't find relevant documents or generate an answer. Error: {e}",
                        "sources": [],
                        "retrieved_chunks": [],
                        "source_type": "none",
                    }
            
            return {
                "answer": "I don't have any relevant documents to answer that yet — try uploading some first.",
                "sources": [],
                "retrieved_chunks": [],
                "source_type": "none",
            }

        messages = build_prompt(query, retrieved)
        answer = self._generate(messages)

        return {
            "answer": answer,
            "sources": self._dedupe_sources(retrieved),
            "retrieved_chunks": [
                {"content": c.content, "metadata": c.metadata, "score": round(c.score, 4)} for c in retrieved
            ],
            "source_type": "documents",  # Indicate this came from documents
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

    def _generate_llm_fallback(self, query: str) -> str:
        """Generate answer using LLM when no documents found (fallback).
        
        This is called when document search returns no results.
        Uses Gemini (reliable), then falls back to Groq if needed.
        
        Args:
            query: User's question
            
        Returns:
            LLM-generated answer
        """
        try:
            # Try Gemini first (more reliable)
            if settings.GEMINI_API_KEY:
                logger.info("Using Gemini LLM fallback")
                from app.llm.gemini_llm import GeminiLLMProvider
                llm = GeminiLLMProvider()
                messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant. Answer the user's question accurately and concisely. Since no documents are available, provide a general knowledge answer."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ]
                return llm.generate(messages)
            
            # Fallback to Groq if Gemini not available
            if settings.GROQ_API_KEY:
                logger.info("Using Groq LLM fallback (Gemini not available)")
                from app.llm.groq_llm import GroqLLMProvider
                llm = GroqLLMProvider()
                system_prompt = (
                    "You are a helpful AI assistant. Answer the user's question accurately and concisely. "
                    "Since no documents are available, provide a general knowledge answer."
                )
                return llm.generate_simple(query, system_prompt)
            
            # If neither API key available, raise error
            raise GenerationError(
                "No LLM API key configured. Set GEMINI_API_KEY or GROQ_API_KEY in .env"
            )
        
        except GenerationError:
            raise
        except Exception as exc:
            logger.exception(f"LLM fallback generation failed: {exc}")
            raise GenerationError(f"LLM fallback failed: {exc}") from exc

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
