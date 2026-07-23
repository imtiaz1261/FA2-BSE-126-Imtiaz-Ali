"""
qa_chain.py
-----------
RetrievalQA Chain.

Wires the retriever together with an LLM using a strict prompt that
forces the model to answer *only* from the retrieved context, and to
return a fixed fallback sentence when the answer isn't present. This
is the core of "Retrieval-Augmented Generation": the LLM never answers
from its own general knowledge -- only from what was retrieved.

Two LLM providers are supported:
  - "openai" (default): requires OPENAI_API_KEY
  - "ollama": local LLM via Ollama (no API key, needs Ollama running)
"""

from typing import Dict, List

from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

from config import (
    LLM_PROVIDER,
    OPENAI_CHAT_MODEL,
    OPENAI_API_KEY,
    OLLAMA_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_TEMPERATURE,
    NO_ANSWER_MESSAGE,
)
from utils import get_logger

logger = get_logger(__name__)


class QAChainError(Exception):
    """Raised when the QA chain / underlying LLM cannot be initialized."""


# --------------------------------------------------------------------------
# Prompt: the single most important piece of "grounding" in this project.
# It explicitly forbids the model from using outside knowledge and gives
# it the exact fallback sentence to use when the context is insufficient.
# --------------------------------------------------------------------------
QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template=(
        "You are a helpful assistant that answers questions using ONLY the "
        "context provided below, which was extracted from the user's own "
        "documents. Do not use any outside knowledge and do not make "
        "anything up.\n\n"
        "If the context does not contain enough information to answer the "
        "question, respond with exactly this sentence and nothing else:\n"
        f'"{NO_ANSWER_MESSAGE}"\n\n'
        "----------------\n"
        "Context:\n{context}\n"
        "----------------\n\n"
        "Question: {question}\n\n"
        "Answer:"
    ),
)


def _get_llm():
    """Instantiate the configured chat LLM."""
    provider = (LLM_PROVIDER or "").lower()

    if provider == "groq":
        if not GROQ_API_KEY:
            raise QAChainError(
                "LLM_PROVIDER is set to 'groq' but GROQ_API_KEY is missing from "
                "your .env file. Get a free key at https://console.groq.com/keys "
                "and add it as GROQ_API_KEY=... in .env."
            )
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise QAChainError(
                "langchain-groq is not installed. Run: pip install langchain-groq"
            ) from exc

        logger.info("Using Groq chat model: %s", GROQ_MODEL)
        return ChatGroq(
            model=GROQ_MODEL, temperature=LLM_TEMPERATURE, api_key=GROQ_API_KEY
        )

    elif provider == "openai":
        if not OPENAI_API_KEY:
            raise QAChainError(
                "LLM_PROVIDER is set to 'openai' but OPENAI_API_KEY is missing "
                "from your .env file. Either add a key or set LLM_PROVIDER=groq "
                "or LLM_PROVIDER=ollama instead."
            )
        from langchain_openai import ChatOpenAI

        logger.info("Using OpenAI chat model: %s", OPENAI_CHAT_MODEL)
        return ChatOpenAI(
            model=OPENAI_CHAT_MODEL, temperature=LLM_TEMPERATURE, api_key=OPENAI_API_KEY
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama

        logger.info("Using local Ollama chat model: %s", OLLAMA_MODEL)
        return ChatOllama(model=OLLAMA_MODEL, temperature=LLM_TEMPERATURE)

    else:
        raise QAChainError(
            f"Unknown LLM_PROVIDER '{provider}'. Use 'groq', 'openai', or 'ollama'."
        )


def _format_context(docs: List[Document]) -> str:
    """Concatenate retrieved chunks into a single context string, each
    one labeled with its source so the model (and prompt) can, in
    principle, reason about provenance."""
    parts = []
    for doc in docs:
        label = doc.metadata.get("file_name", "unknown source")
        if "page" in doc.metadata:
            label += f", page {doc.metadata['page']}"
        elif "paragraph" in doc.metadata:
            label += f", paragraph {doc.metadata['paragraph']}"
        parts.append(f"[{label}]\n{doc.page_content}")
    return "\n\n".join(parts)


def build_qa_chain(retriever: BaseRetriever):
    """
    Build a Runnable QA chain: query -> retrieve -> prompt -> LLM -> answer.

    Returns
    -------
    Runnable
        Invoke with a plain question string: chain.invoke("What is X?")
        Returns a dict: {"answer": str, "source_documents": List[Document]}
    """
    llm = _get_llm()

    def _run(question: str) -> Dict:
        docs = retriever.invoke(question)
        context = _format_context(docs)
        prompt_value = QA_PROMPT.format(context=context, question=question)
        answer = (llm | StrOutputParser()).invoke(prompt_value)
        return {"answer": answer.strip(), "source_documents": docs}

    return RunnableLambda(_run)


def answer_question(qa_chain, question: str) -> Dict:
    """
    Run the QA chain for a single question and log the outcome.

    Returns
    -------
    dict with keys: "answer", "source_documents"
    """
    logger.info("Answering question: %r", question)
    result = qa_chain.invoke(question)
    logger.info("Answer generated (%d source chunk(s) used).", len(result["source_documents"]))
    return result