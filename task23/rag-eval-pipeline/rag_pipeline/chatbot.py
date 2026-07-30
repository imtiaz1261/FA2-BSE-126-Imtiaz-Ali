"""
Answer-generation component of the RAG pipeline being evaluated.

Like the retriever, this supports several backends behind one interface:

  - "openai": production path. Uses LangChain's ChatOpenAI with a standard
    RAG prompt (context + question -> grounded answer). Requires
    OPENAI_API_KEY.
  - "groq": production path using Groq's free, fast LLM hosting. Groq's API
    is OpenAI-compatible, so this also goes through ChatOpenAI, just pointed
    at Groq's base URL with a Groq model name and GROQ_API_KEY. Since Groq
    has no embeddings endpoint, this backend pairs with the retriever's
    "hf_faiss" (local embeddings) backend rather than "openai_faiss".
  - "extractive": dependency-light fallback for offline development/demo.
    Composes an answer directly from the retrieved context using simple
    sentence-overlap scoring — no LLM call. This intentionally produces
    lower-quality answers; it exists so the evaluation pipeline itself can be
    exercised and demoed without API access, not as a substitute for a real
    chatbot in production.
"""

from __future__ import annotations

import re

from rag_pipeline.retriever import Retriever
from utils.logger import get_logger

logger = get_logger(__name__)

_RAG_PROMPT_TEMPLATE = """You are a helpful assistant answering questions about Nimbus Cloud.
Use ONLY the context below to answer. If the answer is not contained in the
context, say you don't have that information — do not make anything up.

Context:
{context}

Question: {question}

Answer:"""


class RAGChatbot:
    """The RAG chatbot under evaluation: retrieve() then generate()."""

    _RETRIEVER_BACKEND_FOR = {
        "extractive": "tfidf",
        "groq": "hf_faiss",
        "openai": "openai_faiss",
    }

    def __init__(self, backend: str = "extractive", retriever: Retriever | None = None):
        self.backend = backend
        self.retriever = retriever or Retriever(
            backend=self._RETRIEVER_BACKEND_FOR.get(backend, "tfidf")
        )
        if backend == "openai":
            self._init_openai()
        elif backend == "groq":
            self._init_groq()
        logger.info("RAGChatbot initialized with backend='%s'", backend)

    def _init_openai(self) -> None:
        from langchain_openai import ChatOpenAI

        from config.settings import settings

        self._llm = ChatOpenAI(
            model=settings.openai_model, api_key=settings.openai_api_key, temperature=0
        )

    def _init_groq(self) -> None:
        """Groq's API is OpenAI-compatible, so ChatOpenAI works here too —
        just pointed at Groq's base_url with a Groq API key and model name."""
        from langchain_openai import ChatOpenAI

        from config.settings import settings

        self._llm = ChatOpenAI(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            temperature=0,
        )

    def answer(self, question: str, k: int = 3) -> tuple[str, list[str]]:
        """
        Run the full retrieve -> generate flow.

        Returns:
            (generated_answer, retrieved_context_chunks)
        """
        context_chunks = self.retriever.retrieve(question, k=k)

        if self.backend in ("openai", "groq"):
            generated = self._generate_llm(question, context_chunks)
        else:
            generated = self._generate_extractive(question, context_chunks)

        return generated, context_chunks

    def _generate_llm(self, question: str, context_chunks: list[str]) -> str:
        prompt = _RAG_PROMPT_TEMPLATE.format(
            context="\n".join(f"- {c}" for c in context_chunks) or "(no context found)",
            question=question,
        )
        response = self._llm.invoke(prompt)
        return response.content.strip()

    def _generate_extractive(self, question: str, context_chunks: list[str]) -> str:
        """Offline fallback: no context found -> honest 'I don't know'; otherwise
        return the most relevant sentence(s) from the retrieved context."""
        if not context_chunks:
            return "I don't have information about that in my knowledge base."

        question_terms = set(re.findall(r"\w+", question.lower()))
        best_sentence, best_overlap = "", -1
        for chunk in context_chunks:
            for sentence in re.split(r"(?<=[.!?])\s+", chunk):
                sentence_terms = set(re.findall(r"\w+", sentence.lower()))
                overlap = len(question_terms & sentence_terms)
                if overlap > best_overlap:
                    best_overlap, best_sentence = overlap, sentence

        return best_sentence.strip() or context_chunks[0]
