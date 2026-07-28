"""src/rag_chain.py — Generates a grounded answer from reranked document
context, using Groq's free hosted LLM.

Mirrors the grounding-prompt approach from the Week 2 RAG project: the
LLM is explicitly instructed to answer ONLY from the provided context,
and to say so plainly if the answer isn't there — this is what prevents
the "generation" half of RAG from just making things up regardless of
what was actually retrieved.
"""

from __future__ import annotations

from openai import OpenAI

from src.bm25_retriever import RetrievedDocument

ANSWER_PROMPT_TEMPLATE = """You are a helpful assistant that answers questions \
using ONLY the context below. Do not use outside knowledge, and do not guess.

If the answer cannot be found in the context, respond with exactly:
"I couldn't find the answer in the provided documents."

Context:
{context}

Question: {question}

Answer:"""


def build_context(documents: list[RetrievedDocument]) -> str:
    """Concatenates reranked documents into a single context block,
    each labeled with its source doc_id so the answer can be traced
    back to a specific document."""
    blocks = [f"[{doc.doc_id}]\n{doc.text}" for doc in documents]
    return "\n\n".join(blocks)


def generate_answer(
    client: OpenAI,
    model_name: str,
    query: str,
    documents: list[RetrievedDocument],
) -> str:
    """Sends the query + retrieved context to the LLM and returns the
    generated answer."""
    if not documents:
        return "I couldn't find the answer in the provided documents."

    context = build_context(documents)
    prompt = ANSWER_PROMPT_TEMPLATE.format(context=context, question=query)

    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content.strip()
